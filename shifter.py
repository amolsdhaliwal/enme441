
import RPi.GPIO as GPIO
import time
import random

GPIO.setmode(GPIO.BCM)
# dataPin, latchPin, clockPin = 23, 24, 25

class Shifter:

  def __init__(self,serialPin, clockPin, latchPin):
      self.serialPin = serialPin
      self.clockPin = clockPin
      self.latchPin = latchPin
      GPIO.setup(serialPin, GPIO.OUT)
      GPIO.setup(latchPin, GPIO.OUT, initial=0) # start latch & clock low
      GPIO.setup(clockPin, GPIO.OUT, initial=0)
        
  def __ping(self,p):
    GPIO.output(p, 1) 
    time.sleep(0)
    GPIO.output(p, 0) 
          
          # public method to send a byte to the shift register
  
  def shiftByte(self, b):
    for i in range(8):
      GPIO.output(self.serialPin, b & (1 << i))
      self.__ping(self.clockPin)  # shift data bit in
    self.__ping(self.latchPin)      # output to LEDs


# pattern = 0b01100110 # pattern to display, pattern now part of shiftbyte call

class Bug:
    def __init__(self, timestep=0.1, x=3, isWrapOn=False):
        self.timestep = timestep
        self.x = x
        self.isWrapOn = isWrapOn
        self.__shifter = Shifter(23, 25, 24)
        self.running = False
        
    def start(self):
        self.running = True
        while self.running:
            pattern = 1 << self.x
            self.__shifter.shiftByte(pattern)
            step = random.choice([-1, 1])
            xnew = self.x + step
            
            if self.isWrapOn:
                # Wrap around
                self.x = xnew % 8
            else:
                # Stay within boundaries
                if 0 <= xnew <= 7:
                    self.x = xnew

            time.sleep(self.timestep)
   
    def stop(self):
        self.running = False
        self.__shifter.shiftByte(0)





"""# this part willnot be in shifter, will be in my other file whch will call shifter
try:
  shiftByte(pattern)
  while 1: pass
except:
  GPIO.cleanup()"""
