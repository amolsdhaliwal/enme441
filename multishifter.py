# stepper_class_shiftregister_multiprocessing.py

import time
import multiprocessing
from shifter import Shifter


class Stepper:

    num_steppers = 0
    shifter_outputs = 0

    # 8-coil half-step sequence (confirmed correct for 28BYJ-48 → Qa,Qb,Qc,Qd order)
    seq = [0b0001, 0b0011, 0b0010, 0b0110,
           0b0100, 0b1100, 0b1000, 0b1001]

    delay = 2400
    steps_per_degree = 4096 / 360.0

    def __init__(self, shifter, lock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)
        self.step_state = 0

        # motor 0 = bits 0–3, motor 1 = bits 4–7, motor 2 = bits 8–11 ...
        self.shifter_bit_start = 4 * Stepper.num_steppers

        self.lock = lock
        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)

    def __step(self, direction):

        # advance through sequence
        self.step_state = (self.step_state + direction) % 8

        # create mask for *only this motor's 4 bits*
        mask = (0b1111 << self.shifter_bit_start)

        # ✅ CLEAR this motor's 4 bits
        Stepper.shifter_outputs &= ~mask

        # ✅ SET this motor's new 4-bit pattern
        Stepper.shifter_outputs |= (Stepper.seq[self.step_state] << self.shifter_bit_start)

        # send to shift register
        self.s.shiftByte(Stepper.shifter_outputs)

        # update shared angle with thread safety
        with self.angle.get_lock():
            self.angle.value = (self.angle.value + direction / Stepper.steps_per_degree) % 360

    def __rotate(self, delta):
        self.lock.acquire()

        steps = int(abs(delta) * Stepper.steps_per_degree)
        direction = self.__sgn(delta)

        for _ in range(steps):
            self.__step(direction)
            time.sleep(Stepper.delay / 1e6)

        self.lock.release()

    def rotate(self, delta):
        # Launch motor movement in its own process
        time.sleep(0.1)  # small delay helps processes start cleanly
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def goAngle(self, angle):
        angle %= 360
        current = self.angle.value

        # shortest path
        delta = (angle - current) % 360
        if delta > 180:
            delta -= 360

        time.sleep(0.1)  # small delay helps processes start cleanly
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0.0


# Example Usage:
if __name__ == "__main__":

    s = Shifter(data=16, latch=20, clock=21)
    
    # ✅ FIX: Create SEPARATE locks for each motor
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(s, lock1)  # m1 gets lock1
    m2 = Stepper(s, lock2)  # m2 gets lock2

    m1.zero()
    m2.zero()

    # Now both motors can move simultaneously!
    m1.rotate(-90)
    m1.rotate(45)
    m2.rotate(180)
    m2.rotate(-45)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nStopped\n")
