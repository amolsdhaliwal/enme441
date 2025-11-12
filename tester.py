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
    
 # Zero the motors:
m1.zero()
m2.zero()

    # Move as desired, with each step occuring as soon as the previous 
    # step ends:
m1.goAngle(90)
#m1.goAngle(0)
#m2.goAngle(45)
#m2.goAngle(90)

    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
try:
    while True:
        pass
except:
    print('\nend')
