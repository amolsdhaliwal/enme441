# stepper_class_shiftregister_multiprocessing.py
import time
import multiprocessing
from shifter import Shifter

class Stepper:

    # class-wide shared state for the shift register
    num_steppers = 0
    shifter_outputs = 0

    # 8-step half-step sequence (LSB-first per prior code)
    seq = [0b0001, 0b0011, 0b0010, 0b0110,
           0b0100, 0b1100, 0b1000, 0b1001]

    delay = 2500              # microseconds between steps
    steps_per_degree = 4096.0 / 360.0

    def __init__(self, shifter, lock, bit_start=None):
        """
        shifter: Shifter instance
        lock: multiprocessing.Lock() used to protect writes to the hardware
        bit_start: optional explicit starting bit position (0,4,8,...). If omitted,
                   the class auto-assigns 4*Stepper.num_steppers.
        """
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)   # visible to child processes
        self.step_state = 0

        if bit_start is None:
            self.shifter_bit_start = 4 * Stepper.num_steppers
        else:
            self.shifter_bit_start = int(bit_start)

        self.lock = lock
        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)

    def __step(self, direction):
        """
        Take one step in given direction (+1 or -1). The critical section
        (updating the shared shift register word + writing to hardware)
        is protected by the lock, but it's held only briefly here.
        """
        # advance through sequence
        self.step_state = (self.step_state + direction) % 8

        mask = (0b1111 << self.shifter_bit_start)

        # small critical section: update shared outputs and write to hardware
        self.lock.acquire()
        try:
            # clear this motor's bits
            Stepper.shifter_outputs &= ~mask
            # set the new pattern for this motor
            Stepper.shifter_outputs |= (Stepper.seq[self.step_state] << self.shifter_bit_start)
            # push to the shift register
            self.s.shiftByte(Stepper.shifter_outputs)
        finally:
            self.lock.release()

        # update the shared angle (not inside critical section)
        # angle updated as degrees; keep in [0,360)
        self.angle.value = (self.angle.value + direction / Stepper.steps_per_degree) % 360

    def __rotate(self, delta):
        """
        Perform rotation by delta degrees (positive = CCW by convention here).
        This function runs in a separate process.
        """
        steps = int(abs(delta) * Stepper.steps_per_degree)
        direction = self.__sgn(delta)

        for _ in range(steps):
            self.__step(direction)
            time.sleep(Stepper.delay / 1e6)   # convert us to s

    def rotate(self, delta):
        """Launch a process to rotate by delta degrees."""
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def goAngle(self, angle):
        """
        Move to absolute angle 'angle' (degrees) following the shortest path.
        Uses the shared multiprocessing.Value angle for the current position.
        """
        # normalize
        angle = angle % 360.0
        current = self.angle.value % 360.0

        # compute delta by shortest path
        delta = (angle - current) % 360.0
        if delta > 180.0:
            delta -= 360.0

        # spawn process to do actual rotation
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def zero(self):
        """Set current motor position to zero (relative reference)."""
        self.angle.value = 0.0


# Example usage / test
if __name__ == "__main__":
    s = Shifter(data=16, latch=20, clock=21)
    lock = multiprocessing.Lock()

    # If you wired your first motor to the upper nibble (bits 4-7),
    # explicitly set bit_start to 4 for that motor.
    # Example A — motor on upper nibble + another on lower nibble:
    m1 = Stepper(s, lock, bit_start=4)   # motor wired to bits 4..7 (matching stepper_with_shifter.py)
    m2 = Stepper(s, lock, bit_start=0)   # motor wired to bits 0..3

    m1.zero()
    m2.zero()

    # commands from the lab to demonstrate simultaneous operation:
    m1.goAngle(90)
    m1.goAngle(-45)

    m2.goAngle(-90)
    m2.goAngle(45)

    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped\n")
