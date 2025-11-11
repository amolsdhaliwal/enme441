# multishifter.py
# Stepper control via 74HC595 + ULN2003, multiprocessing, per-motor coil-order mapping

import time
import multiprocessing
from shifter import Shifter

def build_seq(order):
    """
    Build a mapped 8-step half-step sequence for a given (IN1,IN2,IN3,IN4) bit order.
    order is a tuple of 4 unique integers from {0,1,2,3} telling which *bit inside the nibble*
    goes to ULN2003 IN1..IN4, respectively.

    Example: order=(0,1,2,3)  -> nibble bit0->IN1, bit1->IN2, bit2->IN3, bit3->IN4
             order=(1,0,3,2)  -> nibble bit1->IN1, bit0->IN2, bit3->IN3, bit2->IN4
    """
    # baseline half-step (A,B,C,D) in logical order
    base = [0b0001, 0b0011, 0b0010, 0b0110,
            0b0100, 0b1100, 0b1000, 0b1001]

    # map base’s bit positions (A->bit0, B->bit1, C->bit2, D->bit3) into user-specified nibble bits
    mapped = []
    for pattern in base:
        out = 0
        # read logical bits A,B,C,D from pattern, place them into the nibble according to 'order'
        # pattern bit0 -> IN1 -> goes to nibble bit 'order[0]'
        if pattern & 0b0001: out |= (1 << order[0])   # A -> IN1
        if pattern & 0b0010: out |= (1 << order[1])   # B -> IN2
        if pattern & 0b0100: out |= (1 << order[2])   # C -> IN3
        if pattern & 0b1000: out |= (1 << order[3])   # D -> IN4
        mapped.append(out)
    return mapped

class Stepper:
    # class-wide shared state for the shift register
    num_steppers = 0
    shifter_outputs = 0

    # delay between steps [us] and steps/deg for 28BYJ-48
    delay_us = 2000
    steps_per_degree = 4096.0 / 360.0

    def __init__(self, shifter, lock, *, nibble, order=(0,1,2,3)):
        """
        nibble: which 4-bit group on the 74HC595 this motor uses:
                0 -> bits 0..3 (lower nibble), 1 -> bits 4..7 (upper nibble)
        order: tuple describing how nibble bits map to ULN2003 inputs (IN1..IN4)
               order=(bit_for_IN1, bit_for_IN2, bit_for_IN3, bit_for_IN4)
               Each entry is 0..3 (position within the nibble).
        """
        self.s = shifter
        self.lock = lock
        self.angle = multiprocessing.Value('d', 0.0)
        self.step_state = 0

        # nibble start bit
        self.shifter_bit_start = 4 * int(nibble)

        # build per-motor mapped sequence (4-bit patterns already in *nibble* local bit positions 0..3)
        self.seq = build_seq(order)

        # clear this motor’s bits in the shared word & write an initial pattern so ULN2003 isn’t left floating
        mask = (0b1111 << self.shifter_bit_start)
        with self.lock:
            Stepper.shifter_outputs &= ~mask
            Stepper.shifter_outputs |= (self.seq[self.step_state] << self.shifter_bit_start)
            self.s.shiftByte(Stepper.shifter_outputs)

        Stepper.num_steppers += 1

    @staticmethod
    def __sgn(x):
        if x == 0: return 0
        return 1 if x > 0 else -1

    def __step(self, direction):
        # advance through sequence
        self.step_state = (self.step_state + direction) % 8

        mask = (0b1111 << self.shifter_bit_start)
        with self.lock:
            # clear this motor’s bits
            Stepper.shifter_outputs &= ~mask
            # set this motor’s new pattern (already in local nibble bit positions 0..3)
            Stepper.shifter_outputs |= (self.seq[self.step_state] << self.shifter_bit_start)
            # push to hardware
            self.s.shiftByte(Stepper.shifter_outputs)

        # update angle outside the critical section
        self.angle.value = (self.angle.value + direction / Stepper.steps_per_degree) % 360.0

    def __rotate(self, delta):
        steps = int(abs(delta) * Stepper.steps_per_degree)
        direction = Stepper.__sgn(delta)
        for _ in range(steps):
            self.__step(direction)
            time.sleep(Stepper.delay_us / 1e6)

    def rotate(self, delta):
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def goAngle(self, angle):
        target = angle % 360.0
        current = self.angle.value % 360.0
        delta = (target - current) % 360.0
        if delta > 180.0:
            delta -= 360.0
        self.rotate(delta)

    def zero(self):
        self.angle.value = 0.0


# ---------- quick self-test ----------
if __name__ == "__main__":
    s = Shifter(data=16, latch=20, clock=21)
    lock = multiprocessing.Lock()

    # Your single-motor test used '<<4', i.e. *upper nibble*.
    # So m1 is on nibble=1 (bits 4..7). Put m2 on nibble=0 (bits 0..3).
    #
    # Start with the most common ULN2003/28BYJ order:
    #   order = (0,1,2,3) meaning nibble bit0->IN1, bit1->IN2, bit2->IN3, bit3->IN4.
    #
    # If you get buzzing, swap to the second most common: order=(1,3,2,0).
    #
    m1 = Stepper(s, lock, nibble=1, order=(0,1,2,3))
    m2 = Stepper(s, lock, nibble=0, order=(0,1,2,3))

    m1.zero(); m2.zero()

    # Small motions so you can see direction
    m1.rotate(+90)
    m2.rotate(-90)

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopped\n")
