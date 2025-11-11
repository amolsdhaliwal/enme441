# stepper_class_shiftregister_parallel.py
#
# Stepper class with proper parallel operation for Lab 8

import time
import multiprocessing
from shifter import Shifter   # your custom Shifter class

class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers in parallel.
    """

    # Class attributes
    num_steppers = 0
    shifter_outputs = 0
    seq = [0b0001, 0b0011, 0b0010, 0b0110,
           0b0100, 0b1100, 0b1000, 0b1001]  # CCW sequence
    delay = 1200            # us per step
    steps_per_degree = 4096/360  # 4096 steps/rev

    def __init__(self, shifter):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)  # shared double
        self.step_state = 0
        self.shifter_bit_start = 4*Stepper.num_steppers
        self.mask = 0b1111 << self.shifter_bit_start
        self.lock = multiprocessing.Lock()  # each motor has its own lock

        Stepper.num_steppers += 1

    # Sign function
    def __sgn(self, x):
        if x == 0:
            return 0
        else:
            return int(abs(x)/x)

    # Take a single step in direction dir (+1/-1)
    def __step(self, dir):
        self.step_state = (self.step_state + dir) % 8

        # Only lock the critical section
        with self.lock:
            # Clear old bits
            Stepper.shifter_outputs &= ~self.mask
            # Insert new step pattern
            Stepper.shifter_outputs |= (Stepper.seq[self.step_state] << self.shifter_bit_start)
            # Update shift register
            self.s.shiftByte(Stepper.shifter_outputs)

        # Update shared angle
        with self.angle.get_lock():
            self.angle.value += dir / Stepper.steps_per_degree
            self.angle.value %= 360

    # Rotate relative angle delta
    def __rotate(self, delta):
        numSteps = int(Stepper.steps_per_degree * abs(delta))
        dir = self.__sgn(delta)
        for _ in range(numSteps):
            self.__step(dir)
            time.sleep(Stepper.delay / 1e6)

    # Public method to rotate (spawns a process)
    def rotate(self, delta):
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()
        return p  # optionally track the process if needed

    # Move to an absolute angle using shortest path
    def goAngle(self, target):
        target %= 360
        with self.angle.get_lock():
            curr = self.angle.value

        delta = target - curr
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360

        return self.rotate(delta)

    # Set zero point
    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0.0

# Example usage
if __name__ == '__main__':

    s = Shifter(data=16,latch=20,clock=21)   # set up Shifter

    # Use multiprocessing.Lock() to prevent motors from trying to 
    # execute multiple operations at the same time:
    lock = multiprocessing.Lock()

    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock)
    m2 = Stepper(s, lock)

    # Zero the motors:
    m1.zero()
    m2.zero()

    # Move as desired, with eacg step occuring as soon as the previous 
    # step ends:
    m1.rotate(-90)
    m1.rotate(45)
    m1.rotate(-90)
    m1.rotate(45)

    # If separate multiprocessing.lock objects are used, the second motor
    # will run in parallel with the first motor:
    m2.rotate(180)
    m2.rotate(-45)
    m2.rotate(45)
    m2.rotate(-90)
 
    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            pass
    except:
        print('\nend')
