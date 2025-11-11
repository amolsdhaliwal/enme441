# simultaneous_alternate_test_bitwise_fixed.py
from shifter import Shifter
import time
import multiprocessing

s = Shifter(data=16, clock=20, latch=21)

seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]

posA = 0
posB = 0

shifter_outputs = 0

delay = 1200/1e6

lock = multiprocessing.Lock()

MASK_A = 0b1111 << 4      # A uses bits 4–7
MASK_B = 0b1111           # B uses bits 0–3

def stepA():
    global posA, shifter_outputs
    lock.acquire()

    posA = (posA + 1) % 8         # CCW
    # 1) clear old A bits
    shifter_outputs &= ~MASK_A
    # 2) insert new pattern
    shifter_outputs |= (seq[posA] << 4)

    s.shiftByte(shifter_outputs)
    lock.release()

def stepB():
    global posB, shifter_outputs
    lock.acquire()

    posB = (posB - 1) % 8         # CW
    # 1) clear old B bits
    shifter_outputs &= ~MASK_B
    # 2) insert new pattern
    shifter_outputs |= seq[posB]

    s.shiftByte(shifter_outputs)
    lock.release()


try:
    for i in range(1024):
        stepA()
        time.sleep(delay)

        stepB()
        time.sleep(delay)

except KeyboardInterrupt:
    pass
