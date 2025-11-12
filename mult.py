import time
import multiprocessing
from shifter import Shifter   # custom class

class Stepper:
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0) # shared register output
    shifter_lock = multiprocessing.Lock()
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]
    delay = 2000 # [us]
    steps_per_degree = 1024/360

    def __init__(self, shifter, lock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)  # shared angle
        self.step_state = 0
        self.shifter_bit_start = 4*Stepper.num_steppers
        self.lock = lock
        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0: return 0
        else: return int(abs(x)/x)

    # Modified __step to support concurrent operation
    def __step(self, dir):
        self.step_state = (self.step_state + dir) % 8
        # mask out this motor's bits only
        motor_mask = 0b1111 << self.shifter_bit_start
        with Stepper.shifter_lock:
            # read current value
            reg_val = Stepper.shifter_outputs.value
            # clear this motor's bits, set new value
            reg_val = (reg_val & ~motor_mask) | (Stepper.seq[self.step_state] << self.shifter_bit_start)
            Stepper.shifter_outputs.value = reg_val
            self.s.shiftByte(reg_val)
        # update shared angle value
        with self.angle.get_lock():
            self.angle.value = (self.angle.value + dir / Stepper.steps_per_degree) % 360

    def __rotate(self, delta):
        numSteps = int(Stepper.steps_per_degree * abs(delta))
        dir = self.__sgn(delta)
        for s in range(numSteps):
            self.__step(dir)
            time.sleep(Stepper.delay/1e6)

    # Launches rotation in a separate process; can call this for multiple motors
    def rotate(self, delta):
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # Computes shortest path to target angle and rotates
    def goAngle(self, angle):
        with self.angle.get_lock():
            curr = self.angle.value
        delta = ((angle - curr + 180) % 360) - 180     # maps to (–180,+180]
        self.rotate(delta)

    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0


# Example usage
if __name__ == '__main__':

    s = Shifter(data=16, clock=20, latch=21)  # instantiate the shifter

    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    m1.zero()
    m2.zero()

    # This launches all rotations as simultaneous processes:
    m1.goAngle(45)
    m1.goAngle(90)
    m1.goAngle(0)


    # Main loop continues while motors run
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('\nend')
