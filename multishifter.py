import time
import multiprocessing
from shifter import Shifter   # your custom Shifter class

class Stepper:
    # Class attributes:
    num_steppers = 0      # Track number of Steppers instantiated
    shifter_outputs = 0   # Track shift register outputs for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 1200          # Delay between motor steps [us]
    steps_per_degree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter
        # Use multiprocessing.Value for angle sharing
        self.angle = multiprocessing.Value('d', 0.0) 
        self.step_state = 0
        self.shifter_bit_start = 4 * Stepper.num_steppers  # Starting bit position
        self.lock = lock

        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0: return 0
        else: return int(abs(x)/x)

    def __step(self, dir):
        self.step_state += dir
        self.step_state %= 8
        mask = 0b1111 << self.shifter_bit_start
        seq_value = Stepper.seq[self.step_state] << self.shifter_bit_start

        # Clear only this motor's bits, set new output
        Stepper.shifter_outputs &= ~mask
        Stepper.shifter_outputs |= seq_value
        self.s.shiftByte(Stepper.shifter_outputs)

        # Update shared angle for process sync
        with self.angle.get_lock():
            self.angle.value += dir / Stepper.steps_per_degree
            self.angle.value %= 360

    def __rotate(self, delta):
        self.lock.acquire()  # Prevent shift register collisions
        numSteps = int(Stepper.steps_per_degree * abs(delta))
        dir = self.__sgn(delta)
        for s in range(numSteps):
            self.__step(dir)
            time.sleep(Stepper.delay / 1e6)
        self.lock.release()

    def rotate(self, delta):
        time.sleep(0.1)
        # Spawn parallel process for rotation
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    def goAngle(self, target_angle):
        # Move to absolute angle (modulo 360)
        target_angle = target_angle % 360
        with self.angle.get_lock():
            current = self.angle.value
        # Calculate shortest delta [-180, 180)
        diff = (target_angle - current + 540) % 360 - 180
        self.rotate(diff)

    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0.0

# Example use:
if __name__ == '__main__':
    s = Shifter(data=16, latch=20, clock=21)  # Set up Shifter

    # Use multiprocessing.Lock() to prevent colisions
    lock = multiprocessing.Lock()

    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock)
    m2 = Stepper(s, lock)

    # Zero the motors:
    m1.zero()
    m2.zero()

    # Command sequence: motors should operate simultaneously
    m1.goAngle(90)
    m2.goAngle(-90)
    m1.goAngle(-45)
    m2.goAngle(45)
    m1.goAngle(-135)
    m2.goAngle(135)
    m1.goAngle(0)

    # Keep script running (or add suitable demonstration/exit logic)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('\nend')
