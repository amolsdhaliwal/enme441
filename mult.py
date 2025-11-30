#LED on GPIO bcm pin 17
import time
import multiprocessing
from shifter import Shifter   # your custom Shifter class
import RPi.GPIO as gpio

gpio.setmode(gpio.BCM)
gpio.setup(17,gpio.OUT)
gpio.output(17,0)

led_state = False

def led_on():
    global led_state
    gpio.output(17, 1)
    led_state = True

def led_off():
    global led_state
    gpio.output(17, 0)
    led_state = False

class Stepper:
    """
    Supports operation of multiple stepper motors using shift registers,
    with multiprocessing for simultaneous control.
    """

    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)
    shifter_lock = multiprocessing.Lock()
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]  # CCW sequence
    delay = 2000
    steps_per_degree = 1024 / 360  # adjust for your motor

    def __init__(self, shifter, lock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)  # shared angle
        self.step_state = 0
        self.shifter_bit_start = 4 * Stepper.num_steppers
        self.lock = lock
        self.active = None  # track current motor process
        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return int(abs(x) / x)

    def __step(self, dir, angle):
        """Perform one microstep."""
        self.step_state += dir
        self.step_state %= 8
        mask = ~(0b1111 << self.shifter_bit_start)
        command = Stepper.seq[self.step_state] << self.shifter_bit_start

        with Stepper.shifter_lock:
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command
            self.s.shiftByte(Stepper.shifter_outputs.value)

        angle.value += dir / Stepper.steps_per_degree
        angle.value %= 360

    def __rotate(self, delta, angle):
        """Rotate motor by delta degrees."""
        with self.lock:
            numSteps = int(Stepper.steps_per_degree * abs(delta))
            dir = self.__sgn(delta)
            for _ in range(numSteps):
                self.__step(dir, angle)
                time.sleep(Stepper.delay / 1e6)

    def rotate(self, delta):
        """Launch rotation in a new process (non-blocking)."""
        # wait for previous move of *this motor* only
        if self.active is not None and self.active.is_alive():
            self.active.join()

        p = multiprocessing.Process(target=self.__rotate, args=(delta, self.angle))
        p.start()
        self.active = p

    def goAngle(self, angle):
        """Move to absolute angle using shortest path."""
        delta = angle - self.angle.value
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        self.rotate(delta)

    def zero(self):
        """Reset motor angle to zero."""
        self.angle.value = 0

    def wait(self):
        """Block until current movement finishes."""
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
