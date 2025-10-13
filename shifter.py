
import RPi.GPIO as GPIO
import time

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





"""# this part willnot be in shifter, will be in my other file whch will call shifter
try:
  shiftByte(pattern)
  while 1: pass
except:
  GPIO.cleanup()"""
