# stepper_class_shiftregister_multiprocessing.py
import time
import multiprocessing
from shifter import Shifter

class Stepper:

    # Track number of motors and shared shift-register byte
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)   # SHARED ACROSS PROCESSES

    # 8-step half-stepping sequence
    seq = [0b0001, 0b0011, 0b0010, 0b0110,
           0b0100, 0b1100, 0b1000, 0b1001]

    delay = 2500    # microseconds per step
    steps_per_degree = 4096.0 / 360.0

    def __init__(self, shifter, lock, bit_start=None):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)   # shared angle
        self.step_state = 2                           # seq index
        self.lock = lock

        # Determine which nibble (0-3 or 4-7) this motor uses
        if bit_start is None:
            self.shifter_bit_start = 4 * Stepper.num_steppers
        else:
            self.shifter_bit_start = int(bit_start)

        # >>> INITIALIZE COIL STATE <<<
        mask = (0b1111 << self.shifter_bit_start)

        with self.lock:
            Stepper.shifter_outputs.value &= ~mask
            Stepper.shifter_outputs.value |= (Stepper.seq[self.step_state] << self.shifter_bit_start)
            self.s.shiftByte(Stepper.shifter_outputs.value)
        # >>> END INITIALIZATION <<<

        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)

    def __step(self, direction):
        self.step_state = (self.step_state + direction) % 8

        mask = (0b1111 << self.shifter_bit_start)

        with self.lock:
            Stepper.shifter_outputs.value &= ~mask
            Stepper.shifter_outputs.value |= (Stepper.seq[self.step_state] << self.shifter_bit_start)
            self.s.shiftByte(Stepper.shifter_outputs.value)

        self.angle.value = (self.angle.value + direction / Stepper.steps_per_degree) % 360

    def __rotate(self, delta):
        steps = int(abs(delta) * Stepper.steps_per_degree)
        direction = self.__sgn(delta)

        for _ in range(steps):
            self.__step(direction)
            time.sleep(Stepper.delay / 1e6)

    def rotate(self, delta):
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def goAngle(self, angle):
        angle %= 360
        current = self.angle.value
        delta = (angle - current) % 360
        if delta > 180:
            delta -= 360
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def zero(self):
        self.angle.value = 0.0


# Test / Example Use
if __name__ == "__main__":
    s = Shifter(data=16, latch=20, clock=21)
    lock = multiprocessing.Lock()

    # Motor 1: upper nibble (matches stepper_with_shifter.py)
    m1 = Stepper(s, lock, bit_start=4)

    # Motor 2: lower nibble
    m2 = Stepper(s, lock, bit_start=0)

    m1.zero()
    m2.zero()

    print("Moving motors...")
    m1.goAngle(90)
    m2.goAngle(-90)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped\n")
