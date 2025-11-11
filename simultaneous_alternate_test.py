# simultaneous_alternate_test.py
from shifter import Shifter
import time

s = Shifter(data=16, clock=20, latch=21)
cycle = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]

posA = 0  # motor wired to upper nibble (bits 4..7)
posB = 0  # motor wired to lower nibble (bits 0..3)

delay = 1200/1e6

# initialize outputs
out = (cycle[posA] << 4) | (cycle[posB] << 0)
s.shiftByte(out)

try:
    for i in range(1024):  # try a few revolutions' worth of steps
        # step motor A CCW once
        posA = (posA + 1) % 8
        out &= ~(0b1111 << 4)
        out |= (cycle[posA] << 4)
        s.shiftByte(out)
        time.sleep(delay)

        # step motor B CCW once
        posB = (posB + 1) % 8
        out &= ~0b1111
        out |= (cycle[posB] << 0)
        s.shiftByte(out)
        time.sleep(delay)
except KeyboardInterrupt:
    pass
