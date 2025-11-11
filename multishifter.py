# stepper_class_shiftregister_multiprocessing.py
#
# Updated Stepper class – supports simultaneous operation
# and absolute-goAngle shortest path logic.

import time
import multiprocessing
from shifter import Shifter


class Stepper:
    """
    Supports operation of any number of stepper motors through
    1 or more shift registers. Allows simultaneous operation by
    preserving each motor's 4 output bits in the shared shift register.
    """

    # Class attributes:
    num_steppers = 0                     # number of Stepper instances
    shifter_outputs = 0                  # global bitfield for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]  # 8-step half-stepping
    delay = 1200                         # microseconds between steps
    steps_per_degree = 4096/360          # 4096 steps per revolution

    def __init__(self, shifter, lock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)  # shared angle for multiprocessing
        self.step_state = 0

        # each motor controls its own 4 bits (Qa-Qd, Qe-Qh, etc.)
        self.shifter_bit_start = 4 * Stepper.num_steppers

        self.lock = lock
        Stepper.num_steppers += 1


    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x)/x)


    # Perform a single step in either direction
    def __step(self, direction):

        # update step position in sequence
        self.step_state = (self.step_state + direction) % 8

        # create a 4-bit mask for THIS motor only
        mask = 0b1111 << self.shifter_bit_start

        # clear only this motor's current bits in global output
        Stepper.shifter_outputs &= ~mask

        # set this motor's new coil pattern
        Stepper.shifter_outputs |= (Stepper.seq[self.step_state] << self.shifter_bit_start)

        # shift out the byte(s) to hardware
        self.s.shiftByte(Stepper.shifter_outputs)

        # update the shared angle
        self.angle.value = (self.angle.value + direction / Stepper.steps_per_degree) % 360


    # internal rotation, runs inside a separate process
    def __rotate(self, delta):
        self.lock.acquire()
        numSteps = int(abs(delta) * Stepper.steps_per_degree)
        direction = self.__sgn(delta)

        for i in range(numSteps):
            self.__step(direction)
            time.sleep(Stepper.delay / 1e6)  # convert usec to seconds

        self.lock.release()


    # launch rotation in a new process
    def rotate(self, delta):
        time.sleep(0.05)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()


    # move to an absolute angle by shortest path
    def goAngle(self, angle):

        # wrap target into [0,360)
        angle %= 360

        # read the current shared angle
        current = self.angle.value

        # shortest signed angle difference
        delta = (angle - current) % 360
        if delta > 180:
            delta -= 360

        # move via rotate in separate process
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()


    # set home position
    def zero(self):
        self.angle.value = 0.0



# --- Example Usage ---
if __name__ == '__main__':

    s = Shifter(data=16, latch=20, clock=21)

    # shared lock for both motors
    lock = multiprocessing.Lock()

    m1 = Stepper(s, lock)
    m2 = Stepper(s, lock)

    m1.zero()
    m2.zero()

    # both can run simultaneously
    m1.rotate(-90)
    m1.rotate(45)
    m2.rotate(180)
    m2.rotate(-45)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nStopped\n")
