# single_motor_test.py
import time
from stepper_class_shiftregister_multiprocessing import Stepper, Shifter
from shifter import Shifter
import multiprocessing

s = Shifter(data=16, latch=20, clock=21)
lock = multiprocessing.Lock()

m1 = Stepper(s, lock, bit_start=4)
m1.zero()

# Force single-thread stepping (no new process)
m1._Stepper__rotate(45)
time.sleep(1)
m1._Stepper__rotate(-45)
