import RPi.GPIO as GPIO
import math
import time
p = 4 # pick a gpio pin to put here
GPIO.setmode(GPIO.BCM)
GPIO.outout(p, GPIO.HIGH)
pwm=GPIO.PWM(p, 500) # create 500hz pwm object

try:
    pwm.start(0) # start pwm with 0% duty cycle
    while True:
        t = time.time()
        f=0.2 # hz
        B = (math.sin(2 * math.pi * f * t))**2      
        pwm.ChangeDutyCycle(B * 100) # change duty cycle  
except KeyboardInterrupt:
    print("\nExiting")
pwm.stop()
GPIO.cleanup()
