# ...existing code...
import time
import multiprocessing
from shifter import Shifter   # our custom Shifter class

class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers.
    ...
    """

    # Class attributes:
    num_steppers = 0      # track number of Steppers instantiated
    shifter_outputs = 0   # track shift register outputs for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 1200          # delay between motor steps [us]
    steps_per_degree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter           # shift register
        # use a multiprocessing.Value so angle is visible/updated across processes
        self.angle = multiprocessing.Value('d', 0.0)
        self.step_state = 0        # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock           # multiprocessing lock (used per-step)
        Stepper.num_steppers += 1   # increment the instance count

    # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]

        # Update only this motor's 4 bits in the shared shifter_outputs atomically
        with self.lock:
            # clear the 4 bits for this motor
            Stepper.shifter_outputs &= ~(0b1111 << self.shifter_bit_start)
            # set the new 4-bit pattern for this motor
            Stepper.shifter_outputs |= (Stepper.seq[self.step_state] << self.shifter_bit_start)
            # write to the hardware once with the combined outputs
            self.s.shiftByte(Stepper.shifter_outputs)

        # update the shared angle value
        with self.angle.get_lock():
            self.angle.value += dir/Stepper.steps_per_degree
            self.angle.value %= 360         # limit to [0,359.9+] range

    # Move relative angle from current position:
    def __rotate(self, delta):
        # Do not lock the whole motion; lock only per-step in __step to allow interleaved motors
        numSteps = int(Stepper.steps_per_degree * abs(delta))    # find the right # of steps
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
    def goAngle(self, angle):
        # Read current angle from shared Value
        with self.angle.get_lock():
            cur = self.angle.value
        # Compute minimal delta in (-180, 180]
        delta = (angle - cur + 180) % 360 - 180
        # If you prefer 180 -> +180 instead of -180, adjust here.
        self.rotate(delta)

    # Set the motor zero point
    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0.0


# Example use:

if __name__ == '__main__':

    s = Shifter(data=16,latch=20,clock=21)   # set up Shifter

    # Use multiprocessing.Lock() to protect each per-step update to shared shifter_outputs
    lock = multiprocessing.Lock()

    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock)
    m2 = Stepper(s, lock)

    # Zero the motors:
    m1.zero()
    m2.zero()

    # Move as desired; because __step locks only for the brief hardware update,
    # m1 and m2 processes can interleave steps and run simultaneously:
    m1.rotate(-90)
    m2.rotate(180)
    m1.rotate(45)
    m2.rotate(-45)

    try:
        while True:
            pass
    except:
        print('\nend')
# ...existing code...
