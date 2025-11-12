# Stepper class
#
# Because only one motor action is allowed at a time, multithreading could be
# used instead of multiprocessing. However, the GIL makes the motor process run 
# too slowly on the Pi Zero, so multiprocessing is needed.

import time
import multiprocessing
from shifter import Shifter   # our custom Shifter class

class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers.
  
    A class attribute (shifter_outputs) keeps track of all
    shift register output values for all motors.  In addition to
    simplifying sequential control of multiple motors, this schema also
    makes simultaneous operation of multiple motors possible.
   
    Motor instantiation sequence is inverted from the shift register outputs.
    For example, in the case of 2 motors, the 2nd motor must be connected
    with the first set of shift register outputs (Qa-Qd), and the 1st motor
    with the second set of outputs (Qe-Qh). This is because the MSB of
    the register is associated with Qa, and the LSB with Qh (look at the code
    to see why this makes sense).
 
    An instance attribute (shifter_bit_start) tracks the bit position
    in the shift register where the 4 control bits for each motor
    begin.
    """

    # Class attributes:
    num_steppers = 0      # track number of Steppers instantiated
    shifter_outputs = multiprocessing.Value('i', 0) #track shift register outputs
    shifter_lock = multiprocessing.Lock() # mutex
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 2000          # delay between motor steps [us]
    steps_per_degree = 1024/360    # 1024 steps/rev * 1/360 rev/deg  (bc 1:16 ratio)

    def __init__(self, shifter, lock):
        self.s = shifter           # shift register
        self.angle = multiprocessing.Value('d', 0.0)
        self.step_state = 0        # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock           # multiprocessing lock

        Stepper.num_steppers += 1   # increment the instance count

    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]
        mask = ~(0b1111 << self.shifter_bit_start) # erase selected motor bits
        command = Stepper.seq[self.step_state] << self.shifter_bit_start #  motor command
        with Stepper.shifter_lock: 
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command # replace old command with new command
            self.s.shiftByte(Stepper.shifter_outputs.value)

        self.angle.value += dir/Stepper.steps_per_degree
        self.angle.value = self.angle.value % 360  # limit to [0, 360) range

    # Move relative angle from current position:
    def __rotate(self, delta):
        with self.lock:
            numSteps = int(Stepper.steps_per_degree * abs(delta)) # find the right # of steps
            dir = self.__sgn(delta)        # find the direction (+/-1)
            for s in range(numSteps):      # take the steps
                self.__step(dir)
                time.sleep(Stepper.delay/1e6)

    # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # Move to an absolute angle taking the shortest possible path:
    def goAngle(self, angle): # if going more than 180deg, go the other way
         delta = angle - self.angle.value
         if delta > 180:
             delta -= 360
         elif delta < -180:
             delta += 360
         self.rotate(delta)

    # Set the motor zero point
    def zero(self):
        self.angle.value = 0


# Example use:

if __name__ == '__main__':

    s = Shifter(data=16, clock=20, latch=21)  # set up Shifter

    # Use multiprocessing.Lock() to prevent motors from trying to 
    # execute multiple operations at the same time:
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock1) 
    m2 = Stepper(s, lock2) 
    
    # Zero the motors:
    m1.zero()
    m2.zero()

    # Move as desired, with each step occuring as soon as the previous 
    # step ends:
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)

    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            pass
    except:
        print('\nend')
