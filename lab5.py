import RPi.GPIO as GPIO
import math
import time
# callback pin is 21
button=21
p = [4,17,27,22,10,9,11,19,26,13] # gpio pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(p, GPIO.OUT)
pwms = [GPIO.PWM(i, 500) for i in p]   

control=1
def myCallback(pin):
    print("Direction flipped")
    global control
    control *= -1 
    print("flip")
GPIO.add_event_detect(button, GPIO.RISING, callback=myCallback, bouncetime=300)
try:
    for pwm in pwms:
        pwm.start(0)
    while True:
        t = time.time()
        f=0.2 # hz
        for i, pwm in enumerate(pwms):
            phi = control * i * (math.pi / 11)
            B = (math.sin(2 * math.pi * f * t - phi)) ** 2
            pwm.ChangeDutyCycle(B * 100)
except KeyboardInterrupt: # ctrl c
    for pwm in pwms:
        try:
            pwm.stop()
        except:
            pass
    GPIO.cleanup()
