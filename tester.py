import multiprocessing
import time
from shifter import Shifter 
from multi import Stepper

s = Shifter(data=16, clock=20, latch=21)  # set up Shifter

# Use multiprocessing.Lock() to prevent motors from trying to 
# execute multiple operations at the same time:
lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

# Instantiate 2 Steppers:
m1 = Stepper(s, lock1) 
m2 = Stepper(s, lock2) 
    
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

    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
try:
    while True:
        pass
except:
    print('\nend')
