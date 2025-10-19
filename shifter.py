import threading
import RPi.GPIO as GPIO
import time
import random

GPIO.setmode(GPIO.BCM)

class Shifter:
    def __init__(self, serialPin, clockPin, latchPin):
        self.serialPin = serialPin
        self.clockPin = clockPin
        self.latchPin = latchPin
        GPIO.setup(serialPin, GPIO.OUT)
        GPIO.setup(latchPin, GPIO.OUT, initial=0)
        GPIO.setup(clockPin, GPIO.OUT, initial=0)

    def __ping(self, p):
        GPIO.output(p, 1)
        time.sleep(0)
        GPIO.output(p, 0)

    def shiftByte(self, b):
        for i in range(8):
            GPIO.output(self.serialPin, b & (1 << i))
            self.__ping(self.clockPin)
        self.__ping(self.latchPin)


class Bug:
    def __init__(self, timestep=0.1, x=3, isWrapOn=False):
        self.timestep = timestep
        self.x = x
        self.isWrapOn = isWrapOn
        self.__shifter = Shifter(23, 25, 24)
        self.running = False
        self.thread = None

    def _run(self):
        while self.running:
            pattern = 1 << self.x
            self.__shifter.shiftByte(pattern)
            step = random.choice([-1, 1])
            xnew = self.x + step

            if self.isWrapOn:
                self.x = xnew % 8
            else:
                if 0 <= xnew <= 7:
                    self.x = xnew

            time.sleep(self.timestep)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.__shifter.shiftByte(0)
