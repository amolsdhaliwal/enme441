import time
import multiprocessing
from shifter import Shifter   # your custom Shifter class



class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers.
    """

    # Class attributes:
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)
    shifter_lock = multiprocessing.Lock()
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]  # CCW sequence
    delay = 2000
    steps_per_degree = 1024 / 360

    def __init__(self, shifter, lock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)   # shared memory object
        self.step_state = 0
        self.shifter_bit_start = 4 * Stepper.num_steppers
        self.lock = lock
        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)

    # accepts angle as parameter so shared Value can be updated
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

    # passes self.angle to __step
    def __rotate(self, delta, angle):
        with self.lock:
            numSteps = int(Stepper.steps_per_degree * abs(delta))
            dir = self.__sgn(delta)
            for _ in range(numSteps):
                self.__step(dir, angle)
                time.sleep(Stepper.delay / 1e6)

    # now waits for process completion so angle updates correctly before next move
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta, self.angle))
        p.start()

    def goAngle(self, angle):
        delta = angle - self.angle.value
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        self.rotate(delta)

    def zero(self):
        self.angle.value = 0


# === Example use ===
if __name__ == '__main__':
    s = Shifter(data=16, clock=20, latch=21)

    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    # Zero the motors
    m1.zero()
    m2.zero()

    # Your exact test sequence
    m1.goAngle(45)
    m1.goAngle(90)
    m1.goAngle(0)


    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nEnd")
