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
    shifter_outputs = 0   # track shift register outputs for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 5000          # delay between motor steps [us]
    steps_per_degree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter           # shift register
        
        # LAB 8 (Step 3b): Use multiprocessing.Value for shared angle
        # 'd' stands for a double-precision float
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

        # LAB 8 (Step 2): Modified bitwise operations for simultaneous control
        # This new logic ensures only the 4 bits for THIS motor are changed,
        # leaving the other motor's bits untouched.
        
        # 1. Create a "clear mask" to zero out this motor's 4 bits
        #    Example (m1, bits 0-3): ~(0b00001111) -> 0b11110000
        #    Example (m2, bits 4-7): ~(0b11110000) -> 0b00001111
        clear_mask = ~(0b1111 << self.shifter_bit_start)
        
        # 2. Create the "set bits" for this motor's new step
        #    Example (m1, seq[1]): 0b0011 << 0 -> 0b00000011
        #    Example (m2, seq[2]): 0b0010 << 4 -> 0b00100000
        set_bits = Stepper.seq[self.step_state] << self.shifter_bit_start
        
        # 3. Apply the masks:
        #    First, zero out this motor's bits: (shifter_outputs & clear_mask)
        #    Then, add this motor's new bits:   ... | set_bits
        Stepper.shifter_outputs = (Stepper.shifter_outputs & clear_mask) | set_bits

        self.s.shiftByte(Stepper.shifter_outputs)
        
        # LAB 8 (Step 3b): Update the .value of the shared angle
        self.angle.value += dir/Stepper.steps_per_degree
        self.angle.value = self.angle.value % 360  # limit to [0, 360) range

    # Move relative angle from current position:
    def __rotate(self, delta):
        # Using a context manager for the lock is cleaner
        with self.lock:
            numSteps = int(Stepper.steps_per_degree * abs(delta)) # find the right # of steps
            dir = self.__sgn(delta)        # find the direction (+/-1)
            for s in range(numSteps):      # take the steps
                self.__step(dir)
                time.sleep(Stepper.delay/1e6)
        # lock is automatically released here

    # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # Move to an absolute angle taking the shortest possible path:
    def goAngle(self, angle):
         # LAB 8 (Step 3a): COMPLETE THIS METHOD
         
         # 1. Calculate the simple difference
         #    (must read from .value of the shared angle)
         delta = angle - self.angle.value
         
         # 2. Normalize the delta to the shortest path [-180, 180]
         #    (delta + 180) % 360 wraps the angle
         #    ... - 180 shifts it back
         delta = (delta + 180) % 360 - 180

         # 3. Call the rotate function with the shortest-path delta
         self.rotate(delta)

    # Set the motor zero point
    def zero(self):
        # LAB 8 (Step 3b): Set the .value of the shared angle
        self.angle.value = 0


# Example use:

if __name__ == '__main__':

    s = Shifter(data=16,latch=20,clock=21)   # set up Shifter

    # LAB 8 (Step 2 & 4): Use *separate* multiprocessing.Lock() objects
    # This is required to allow m1 and m2 to run in parallel.
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    # Instantiate 2 Steppers with their own locks:
    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    # LAB 8 (Step 4): Demonstrate the required sequence
    
    # Zero the motors:
    m1.zero()
    m2.zero()

    # These commands will now run in parallel, with each motor
    # executing its own queue of commands.
    print("Starting motor commands...")
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)
    print("All commands issued.")
 
    # While the motors are running in their separate processes, the main
    # code must stay alive. 
    try:
        print("Main process is waiting... (Press Ctrl+C to exit)")
        while True:
            pass
    except KeyboardInterrupt:
        print('\nProgram terminated.')
