import RPi.GPIO as GPIO
import math
import time
p = [4,17] # gpio pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(p, GPIO.OUT)
pwms = [4,17,27,22,10,9,11,19,26,13]
for i in p:
    pwm=GPIO.PWM(i, 500) # create 500hz pwm object
    pwms.append(pwm)
#pwm=GPIO.PWM(p, 500) # create 500hz pwm object
#pwm2=GPIO.PWM(17, 500)
phi=math.pi/11 # phase shift
try:
    for pwm in pwms:
        pwm.start(0) # start pwm with 0% duty cycle
    #pwm.start(0) # start pwm with 0% duty cycle
    #pwm2.start(0) # start pwm with 0% duty cycle
    while True:
        t = time.time()
        f=0.2 # hz
        '''B = (math.sin(2 * math.pi * f * t))**2      
        B2 = (math.sin((2 * math.pi * f * t)-phi))**2
        pwm.ChangeDutyCycle(B * 100) # change duty cycle  
        pwm2.ChangeDutyCycle((B2) * 100)'''
        for i, pwm in enumerate(pwms):
            phi = i * (math.pi / 11)
            B = (math.sin(2 * math.pi * f * t - phi)) ** 2
            pwm.ChangeDutyCycle(B * 100)
except KeyboardInterrupt:
     for pwm in pwms:
        pwm.stop() # start pwm with 0% duty cycle
        
        GPIO.cleanup()


