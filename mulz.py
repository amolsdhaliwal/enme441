# stepper_class_shiftregister_multiprocessing.py
#
# Stepper class
#
# This version uses a shared Manager.Value for shifter_outputs so all processes share the same output state.

import time
import multiprocessing
from shifter import Shifter   # our custom Shifter class

class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers, with multiprocessing support for concurrent motion.
    """

    # --- Shared class attributes across all Stepper processes ---
    manager = multiprocessing.Manager()
    shifter_outputs = manager.Value('i', 0)   # Shared int across processes
    shifter_lock = multiprocessing.Lock()      # Shared mutex for shift register access
    num_steppers = 0                           # Track number of instances
    seq = [0b0001, 0b0011, 0b0010, 0b0110, 0b0100, 0b1100, 0b1000, 0b1001]  # CCW sequence
    delay = 2000                               # delay between steps [μs]
    steps_per_degree = 1024 / 360              # 1024 steps/rev * 1/360 rev/deg (1:16 ratio)

    def __init__(self, shifter, lock):
        self.s = shifter                                   # Shared Shifter object
        self.angle = multiprocessing.Value('d', 0.0)       # Shared angle tracker
        self.step_state = 0                                # Sequence index
        self.shifter_bit_start = 4 * Stepper.num_steppers  # Start bit for motor
        self.lock = lock                                   # Motor-level lock
        Stepper.num_steppers += 1

    # --- Helper functions ---
    def __sgn(self, x):
        if x == 0:
            return 0
        return 1 if x > 0 else -1

    # --- Step function ---
    def __step(self, direction):
        self.step_state = (self.step_state + direction) % 8
        mask = ~(0b1111 << self.shifter_bit_start)                      # Erase bits for this motor
        command = Stepper.seq[self.step_state] << self.shifter_bit_start # New motor command

        # Update the shared output atomically
        with Stepper.shifter_lock:
            Stepper.shifter_outputs.value = (Stepper.shifter_outputs.value & mask) | command
            self.s.shiftByte(Stepper.shifter_outputs.value)

        # Update shared angle
        with self.angle.get_lock():
            self.angle.value = (self.angle.value + direction / Stepper.steps_per_degree) % 360

    # --- Internal rotate function ---
    def __rotate(self, delta):
        with self.lock:  # Prevent multiple commands for same motor
            num_steps = int(Stepper.steps_per_degree * abs(delta))
            direction = self.__sgn(delta)
            for _ in range(num_steps):
                self.__step(direction)
                time.sleep(Stepper.delay / 1e6)

    # --- Public rotate function ---
    def rotate(self, delta):
        # Launch a new process for independent movement
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # --- Move to an absolute angle taking shortest path ---
    def goAngle(self, target_angle):
        delta = target_angle - self.angle.value
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        self.rotate(delta)

    # --- Zero out angle ---
    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0


# --- Example Use ---
if __name__ == '__main__':
    s = Shifter(data=16, clock=20, latch=21)

    # Two independent locks to allow concurrent operation
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    # Create two steppers
    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    # Zero both
    m1.zero()
    m2.zero()

    # Example moves
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)

    # Keep main alive while processes run
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('\nEnd')
