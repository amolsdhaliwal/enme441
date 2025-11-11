from shifter import Shifter
import time

s = Shifter(data=16, clock=20, latch=21)

print("\nTEST: LOWER NIBBLE (bits 0–3)")
for pat in [1,2,4,8]:
    s.shiftByte(pat)
    time.sleep(0.4)

time.sleep(1)

print("\nTEST: UPPER NIBBLE (bits 4–7)")
for pat in [1,2,4,8]:
    s.shiftByte(pat << 4)
    time.sleep(0.4)

print("\nDone.\n")
