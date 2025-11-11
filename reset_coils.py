# reset_coils.py
from shifter import Shifter
import time

s = Shifter(data=16, clock=20, latch=21)

# turn all coils off
s.shiftByte(0x00)
time.sleep(1)

print("Coils reset. Now run your class code again.")
