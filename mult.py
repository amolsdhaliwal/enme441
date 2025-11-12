import time
import multiprocessing
from shifter import Shifter   # our custom Shifter class

class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers.
    """
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0) # track shift register outputs
    shifter_lock = multiprocessing.Lock() # mutex
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 2000          # delay between motor steps [us]
    steps_per_degree = 1024/360

    def __init__(self, shifter, lock):
        self.s = shifter  # shift register
        self.angle = multiprocessing.Value('d', 0.0) # shared cross-process angle
        self.step_state = 0
        self.shifter_bit_start = 4*Stepper.num_steppers
        self.lock = lock
        Stepper.num_steppers += 1
        self.active_proc = None

    def __sgn(self, x):
        if x == 0: return 0
        else: return int(abs(x)/x)

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state = (self.step_state + dir) % 8
        mask = ~(0b1111 << self.shifter_bit_start) # erase motor bits
        command = Stepper.seq[self.step_state] << self.shifter_bit_start
        with Stepper.shifter_lock:
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command
            self.s.shiftByte(Stepper.shifter_outputs.value)
        with self.angle.get_lock():
            self.angle.value = (self.angle.value + dir/Stepper.steps_per_degree) % 360

    def __rotate(self, delta):
        with self.lock:
            numSteps = int(Stepper.steps_per_degree * abs(delta))
            dir = self.__sgn(delta)
            for s in range(numSteps):
                self.__step(dir)
                time.sleep(Stepper.delay/1e6)

    # Replace your rotate() method:
    def rotate(self, delta):
        if self.active_proc and self.active_proc.is_alive():
            self.active_proc.join()
        self.active_proc = multiprocessing.Process(target=self.__rotate, args=(delta,))
        self.active_proc.start()

    # Move to an absolute angle via shortest path (robust version)
    def goAngle(self, a):
        with self.angle.get_lock():
            curr = self.angle.value
        # Compute shortest path delta (takes care of -180°/+180° wraparound)
        delta = ((a - curr + 180) % 360) - 180
        self.rotate(delta)

    def zero(self):
        # Optionally lock here if you want to be extra robust
        with self.angle.get_lock():
            self.angle.value = 0

# Example usage:
if __name__ == '__main__':
    s = Shifter(data=16, clock=20, latch=21)  # set up Shifter

    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    m1.zero()
    m2.zero()

    m1.goAngle(45)
    m2.goAngle(100)
    m1.goAngle(-45)
    m2.goAngle(0)


    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('\nend')
