import RPi.GPIO as GPIO
import math
import time
p = 4 # pick a gpio pin to put here
GPIO.setmode(GPIO.BCM)
GPIO.setup(p, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
pwm=GPIO.PWM(p, 500) # create 500hz pwm object
pwm2=GPIO.PWM(17, 500)
phi=math.pi/11 # phase shift
try:
    pwm.start(0) # start pwm with 0% duty cycle
    pwm2.start(0) # start pwm with 0% duty cycle
    while True:
        t = time.time()
        f=0.2 # hz
        B = (math.sin(2 * math.pi * f * t))**2      
        B2 = (math.sin((2 * math.pi * f * t)-phi))**2
        pwm.ChangeDutyCycle(B * 100) # change duty cycle  
        pwm2.ChangeDutyCycle((B2) * 100)
except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()


