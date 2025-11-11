# order_sweep.py
import time, multiprocessing
from shifter import Shifter
from multishifter import Stepper

if __name__ == "__main__":
    s = Shifter(data=16, latch=20, clock=21)
    lock = multiprocessing.Lock()

    # Motor on upper nibble (bits 4..7), same nibble as your '<<4' single-motor test
    print("Trying order (0,1,2,3) on nibble=1...")
    m = Stepper(s, lock, nibble=1, order=(0,1,2,3))
    m.rotate(90)
    time.sleep(3)

    print("Trying order (1,3,2,0) on nibble=1...")
    m = Stepper(s, lock, nibble=1, order=(1,3,2,0))
    m.rotate(90)

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
