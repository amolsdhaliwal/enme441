# stepper_class_shiftregister_multiprocessing.py
#
# Modified Stepper class for Lab 8
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
    delay = 1200          # delay between motor steps [us]
    steps_per_degree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter           # shift register
        
        # TASK 3 MODIFICATION: Use multiprocessing.Value to share angle across processes
        # 'd' means double (floating point number)
        # The angle is now a shared memory object that can be accessed by multiple processes
        self.angle = multiprocessing.Value('d', 0.0)  # current output shaft angle (shared)
        
        self.step_state = 0        # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock           # multiprocessing lock

        Stepper.num_steppers += 1   # increment the instance count

    # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # TASK 2 MODIFICATION: Fixed bitwise operations for simultaneous motor control
    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]
        
        # MODIFIED BITWISE OPERATIONS:
        # Instead of using |= and &= which affect all bits, we need to:
        # 1. Clear only this motor's 4 bits in the shared output
        # 2. Set only this motor's 4 bits to the new sequence value
        
        # Create a mask for this motor's 4 bits (all 1s in the motor's bit positions)
        motor_mask = 0b1111 << self.shifter_bit_start
        
        # Clear this motor's bits (set them to 0) while preserving other motors' bits
        # Use bitwise AND with the inverse of the mask
        Stepper.shifter_outputs &= ~motor_mask
        
        # Set this motor's bits to the new sequence value
        # Shift the sequence value to the correct position and OR it with the outputs
        Stepper.shifter_outputs |= (Stepper.seq[self.step_state] << self.shifter_bit_start)
        
        # Send the updated byte to the shift register
        self.s.shiftByte(Stepper.shifter_outputs)
        
        # Update the angle - access the .value property of the multiprocessing.Value object
        with self.angle.get_lock():  # Lock ensures thread-safe access to shared value
            self.angle.value += dir/Stepper.steps_per_degree
            self.angle.value %= 360   # limit to [0,359.9+] range

    # Move relative angle from current position:
    def __rotate(self, delta):
        self.lock.acquire()                 # wait until the lock is available
        numSteps = int(Stepper.steps_per_degree * abs(delta))    # find the right # of steps
        dir = self.__sgn(delta)        # find the direction (+/-1)
        for s in range(numSteps):      # take the steps
            self.__step(dir)
            time.sleep(Stepper.delay/1e6)
        self.lock.release()

    # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # TASK 3: Move to an absolute angle taking the shortest possible path:
    def goAngle(self, target_angle):
        """
        Move to an absolute angle (relative to zero) via the shortest path.
        
        Args:
            target_angle: The desired absolute angle (in degrees)
        
        Algorithm:
            1. Calculate the raw difference between target and current angle
            2. Normalize this difference to the range [-180, +180] to find shortest path
            3. Call rotate() with the calculated delta
        """
        # Access the current angle from the multiprocessing.Value object
        current = self.angle.value
        
        # Calculate the raw difference
        delta = target_angle - current
        
        # Normalize to [-180, +180] range for shortest path
        # Example: If current=350° and target=10°
        #   delta = 10 - 350 = -340°
        #   Since delta < -180, we add 360: -340 + 360 = 20°
        #   So we rotate +20° clockwise instead of -340° counter-clockwise
        
        if delta > 180:
            delta -= 360  # If going more than 180° CW, go CCW instead
        elif delta < -180:
            delta += 360  # If going more than 180° CCW, go CW instead
        
        # Use the rotate method to move by the calculated shortest delta
        self.rotate(delta)

    # Set the motor zero point
    def zero(self):
        """Reset the motor's angle to 0 (defines the current position as zero)"""
        # Access the multiprocessing.Value object's value property
        with self.angle.get_lock():
            self.angle.value = 0


# TASK 2 & 4: Example use with simultaneous motor operation

if __name__ == '__main__':

    s = Shifter(data=16, latch=20, clock=21)   # set up Shifter

    # TASK 2: Create separate locks for each motor to enable simultaneous operation
    # Each motor gets its own lock, so they don't block each other
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    # Instantiate 2 Steppers with their own locks
    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    # TASK 4: Demonstration sequence
    # Zero both motors (set current position as 0°)
    m1.zero()
    m2.zero()

    # Execute the required command sequence
    # Because each motor has its own lock, when we call these sequentially,
    # they will execute simultaneously (m1 and m2 run in parallel)
    
    m1.goAngle(90)      # m1: go to 90° from 0°
    m1.goAngle(-45)     # m1: go to -45° from 90° (shortest path)
    
    m2.goAngle(-90)     # m2: go to -90° from 0°
    m2.goAngle(45)      # m2: go to 45° from -90° (shortest path)
    
    m1.goAngle(-135)    # m1: go to -135° from -45°
    m1.goAngle(135)     # m1: go to 135° from -135° (shortest path)
    m1.goAngle(0)       # m1: go back to 0° from 135° (shortest path)

    # While the motors are running in their separate processes, the main
    # code can continue. We'll just wait here.
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('\nend')
