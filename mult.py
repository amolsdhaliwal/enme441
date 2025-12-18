import time
import multiprocessing
from shifter import Shifter   # Shifter class
import RPi.GPIO as gpio

gpio.setmode(gpio.BCM)
LED_PIN = 17
gpio.setup(LED_PIN, gpio.OUT)
gpio.output(LED_PIN, 0)

led_state = multiprocessing.Value('i', 0)

def led_on():
    with led_state.get_lock():
        led_state.value = 1
    gpio.output(LED_PIN, 1)

def led_off():
    with led_state.get_lock():
        led_state.value = 0
    gpio.output(LED_PIN, 0)


class Stepper:

    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)
    shifter_lock = multiprocessing.Lock()
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]  # CCW sequence
    delay = 1200     # delay between motor steps [us]
    steps_per_degree = 4096 / 360      # 64:1 stepper

    def __init__(self, shifter, lock):
        self.s = shifter     # shift register
        self.angle = multiprocessing.Value('d', 0.0) 
        self.step_state = 0     # track position in sequence
        self.shifter_bit_start = 4 * Stepper.num_steppers # starting bit position
        self.lock = lock     # multiprocessing lock
        self.active = None      # track current motor process
        Stepper.num_steppers += 1     # increment the instance count

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)
        
    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir, angle):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8    # ensure result stays in [0,7]
        mask = ~(0b1111 << self.shifter_bit_start)    # erase motor bits
        command = Stepper.seq[self.step_state] << self.shifter_bit_start    #  motor command

        with Stepper.shifter_lock:
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command     # replace old command with new command
            self.s.shiftByte(Stepper.shifter_outputs.value)

        angle.value += dir / Stepper.steps_per_degree
        angle.value %= 360

        # Move relative angle from current position:
    def __rotate(self, delta, angle):
        with self.lock:     # wait until lock is available
            numSteps = int(Stepper.steps_per_degree * abs(delta))    # find the right # of steps
            dir = self.__sgn(delta)    # find the direction (+/-1)
            for _ in range(numSteps):    # take the steps
                self.__step(dir, angle)
                time.sleep(Stepper.delay / 1e6)
                
        # Move relative angle from current position:
    def rotate(self, delta):
        # wait for previous move of this motor only
        if self.active is not None and self.active.is_alive():
            self.active.join()

        p = multiprocessing.Process(target=self.__rotate, args=(delta, self.angle))
        p.start()
        self.active = p

        # Move to an absolute angle taking the shortest possible path:
    def goAngle(self, angle):
        delta = angle - self.angle.value
        if delta > 180:    # if going more than 180deg, go the other way
            delta -= 360
        elif delta < -180:
            delta += 360
        self.rotate(delta)

        # Set the motor zero point
    def zero(self):
        self.angle.value = 0

    # wait until current movement is finished
    def wait(self):
        if self.active is not None:
            self.active.join()



# === Example use ===
if __name__ == '__main__':
    s = Shifter(data=16, clock=20, latch=21)

    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    m1.zero()
    m2.zero()

    # Example input sequence
    m1.goAngle(90)
    m2.goAngle(-90)  # starts simultaneously with m1
    m1.wait()
    m2.wait()

    m1.goAngle(-45)
    m2.goAngle(45)
    m1.wait()
    m2.wait()

    m1.goAngle(-135)
    m1.wait()
    m1.goAngle(135)
    m1.wait()
    m1.goAngle(0)
    m1.wait()

    print("Final angles:")
    print("Motor 1:", m1.angle.value)
    print("Motor 2:", m2.angle.value)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nEnd")
