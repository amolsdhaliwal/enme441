import RPi.GPIO as GPIO
import time
from shifter import Bug

s1 = 16
s2 = 20
s3 = 21

GPIO.setmode(GPIO.BCM)
GPIO.setup(s1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(s2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(s3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

bug = Bug()

prev = GPIO.input(s2)
active = False

try:
    while True:
        power = GPIO.input(s1)
        toggleWrap = GPIO.input(s2)
        boost = GPIO.input(s3)
        if power and not active:
            bug.start()
            active = True
        elif not power and active:
            bug.stop()
            active = False
        if toggleWrap != prev:
            if toggleWrap:
                bug.isWrapOn = not bug.isWrapOn
                time.sleep(.1)
            prev = toggleWrap
        if boost:
            bug.timestep = .1/3
        else:
            bug.timestep = .1
        # time.sleep(0.01)  # Small delay for monitoring loop
        
except KeyboardInterrupt:
    bug.stop()
finally:
    GPIO.cleanup()
