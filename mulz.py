# stepper_class_shiftregister_queue.py
#
# Stepper class using per-motor command queue for parallel motion

import time
import multiprocessing
from shifter import Shifter

class Stepper:
    """
    Stepper motor control using shift registers with multiprocessing queues.
    Each motor has a dedicated process that listens to its queue and moves
    to absolute angles.
    """

    # Class attributes
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)
    shifter_lock = multiprocessing.Lock()
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]
    delay = 2000  # microseconds per step
    steps_per_degree = 1024 / 360  # 1024 steps/rev

    def __init__(self, shifter):
        self.s = shifter
        self.step_state = 0
        self.shifter_bit_start = 4 * Stepper.num_steppers
        self.angle = 0.0  # current absolute angle
        self.queue = multiprocessing.Queue()
        self.lock = multiprocessing.Lock()  # optional for internal thread safety

        # Start the motor process
        self.process = multiprocessing.Process(target=self._motor_loop)
        self.process.daemon = True
        self.process.start()

        Stepper.num_steppers += 1

    # Low-level step
    def _step(self, dir):
        self.step_state = (self.step_state + dir) % 8
        mask = ~(0b1111 << self.shifter_bit_start)
        command = Stepper.seq[self.step_state] << self.shifter_bit_start

        # Ensure only one motor updates the shift register at a time
        with Stepper.shifter_lock:
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command
            self.s.shiftByte(Stepper.shifter_outputs.value)

        self.angle = (self.angle + dir / Stepper.steps_per_degree) % 360

    # Motor process loop
    def _motor_loop(self):
        while True:
            target = self.queue.get()
            if target is None:
                break  # stop signal

            # Compute shortest path delta
            delta = target - self.angle
            if delta > 180:
                delta -= 360
            elif delta < -180:
                delta += 360

            steps = int(abs(delta) * Stepper.steps_per_degree)
            dir = 1 if delta > 0 else -1

            for _ in range(steps):
                self._step(dir)
                time.sleep(Stepper.delay / 1e6)

    # Public method to move to absolute angle
    def goAngle(self, angle):
        self.queue.put(angle)  # non-blocking, motor handles movement

    # Public method to set zero
    def zero(self):
        self.angle = 0.0

    # Stop the motor process cleanly
    def stop(self):
        self.queue.put(None)
        self.process.join()


# Example use:
if __name__ == '__main__':
    s = Shifter(data=16, clock=20, latch=21)

    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    # Zero the motors
    m1.zero()
    m2.zero()

    # step ends:
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)
  # now reliably moves back to zero

    # Keep the script running
    try:
        while True:
            pass
    except:
        print("\nend")
