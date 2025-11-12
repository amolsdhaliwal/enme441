import time
import multiprocessing
from shifter import Shifter   # your custom Shifter class

class Stepper:
    """
    Stepper motor class supporting absolute angle moves with multiprocessing.
    Each motor waits for its previous rotation to finish before starting a new move.
    Different motors can spin simultaneously.
    """

    # Class attributes
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)  # shared shift register outputs
    shifter_lock = multiprocessing.Lock()
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]  # CCW sequence
    delay = 2000  # microseconds
    steps_per_degree = 1024 / 360

    def __init__(self, shifter, lock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)  # shared absolute angle
        self.step_state = 0
        self.shifter_bit_start = 4 * Stepper.num_steppers
        self.lock = lock
        self.active = None  # track the current process for this motor
        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)

    def __step(self, dir, angle):
        self.step_state += dir
        self.step_state %= 8
        mask = ~(0b1111 << self.shifter_bit_start)
        command = Stepper.seq[self.step_state] << self.shifter_bit_start

        with Stepper.shifter_lock:
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command
            self.s.shiftByte(Stepper.shifter_outputs.value)

        angle.value += dir / Stepper.steps_per_degree
        angle.value %= 360

    def __rotate(self, delta, angle):
        with self.lock:
            numSteps = int(Stepper.steps_per_degree * abs(delta))
            dir = self.__sgn(delta)
            for _ in range(numSteps):
                self.__step(dir, angle)
                time.sleep(Stepper.delay / 1e6)

    def rotate(self, delta):
        """Start motor rotation in a separate process for this motor."""
        # Wait for previous rotation of this motor to finish
        if self.active is not None:
            self.active.join()

        p = multiprocessing.Process(target=self.__rotate, args=(delta, self.angle))
        p.start()
        self.active = p  # store the process reference

    def goAngle(self, target_angle):
        """Move motor to an absolute angle via the shortest path."""
        delta = target_angle - self.angle.value
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        self.rotate(delta)

    def zero(self):
        self.angle.value = 0


# === Example use ===
if __name__ == '__main__':
    # Initialize your shift register
    s = Shifter(data=16, clock=20, latch=21)

    # Separate locks for each motor
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    # Instantiate two motors
    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    # Zero both motors
    m1.zero()
    m2.zero()

    # Your exact input sequence
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)

