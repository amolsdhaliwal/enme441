# nibble_tester.py
from shifter import Shifter
import time

s = Shifter(data=16, clock=20, latch=21)

cycle = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]
delay = 1200/1e6

def loop_word(word_shifted, steps=512):
    pos = 0
    for i in range(steps):
        pos = (pos + 1) % 8
        s.shiftByte(cycle[pos] << word_shifted)
        time.sleep(delay)

print("Testing upper nibble (bits 4..7) — motor should move if wired there")
loop_word(4, steps=1024)   # upper nibble test

time.sleep(1)
print("Testing lower nibble (bits 0..3) — motor should move if wired there")
loop_word(0, steps=1024)   # lower nibble test

print("Done")
