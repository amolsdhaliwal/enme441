# stepper_class_shiftregister_multiprocessing.py
#
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
    delay = 1200          # delay between motor steps [us]
    steps_per_degree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter           # shift register
        self.angle = multiprocessing.Value('d', 0.0)
        self.step_state = 0        # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock           # multiprocessing lock

        Stepper.num_steppers += 1   # increment the instance count

    # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]
        mask = ~(0b1111 << self.shifter_bit_start) # erase selected motor bits
        command = Stepper.seq[self.step_state] << self.shifter_bit_start #  motor command
        with Stepper.shifter_lock: # yada
# maybe move mask back here?
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command
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

    # Instantiate 2 Steppers with their own locks:
    # m2 (bits 4-7) must be instantiated *after* m1 (bits 0-3)
    # as per the logic: self.shifter_bit_start = 4*Stepper.num_steppers
    
    # Wait, re-reading your working code:
    # MASK_A = 0b1111 << 4   (bits 4-7)
    # MASK_B = 0b1111         (bits 0-3)
    # This means your "Motor A" uses bits 4-7 and "Motor B" uses bits 0-3.
    
    # In my class code:
    # m1 = Stepper() -> self.shifter_bit_start = 0 (bits 0-3) -> This is Motor B
    # m2 = Stepper() -> self.shifter_bit_start = 4 (bits 4-7) -> This is Motor A
    
    # This is correct. m1 is B, m2 is A.
    
    m1 = Stepper(s, lock1) # Corresponds to Motor B (bits 0-3 / Qe-Qh)
    m2 = Stepper(s, lock2) # Corresponds to Motor A (bits 4-7 / Qa-Qd)


    # LAB 8 (Step 4): Demonstrate the required sequence
    
    # Zero the motors:
    m1.zero()
    m2.zero()

    print("Starting motor commands...")
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)
    print("All commands issued.")
 
    try:
        print("Main process is waiting... (Press Ctrl+C to exit)")
        while True:
            pass
    except KeyboardInterrupt:
        print('\nProgram terminated.')
