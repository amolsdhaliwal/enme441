# simultaneous_alternate_test.py
from shifter import Shifter
import time
import multiprocessing

s = Shifter(data=16, clock=20, latch=21)
cycle = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]

posA = 0  # motor A = upper nibble
posB = 0  # motor B = lower nibble

delay = 1200/1e6

# multiprocessing lock
lock = multiprocessing.Lock()

# initialize outputs
out = (cycle[posA] << 4) | cycle[posB]
s.shiftByte(out)

def stepA():
    global posA, out
    lock.acquire()
    posA = (posA + 1) % 8       # CCW
    out &= ~(0xF << 4)
    out |= (cycle[posA] << 4)
    s.shiftByte(out)
    lock.release()

def stepB():
    global posB, out
    lock.acquire()
    posB = (posB - 1) % 8       # CW
    out &= ~0xF
    out |= cycle[posB]
    s.shiftByte(out)
    lock.release()


try:
    for i in range(1024):
        stepA()
        time.sleep(delay)

        stepB()
        time.sleep(delay)

except KeyboardInterrupt:
    pass
