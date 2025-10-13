import random
import time
from shifter import Shifter

class Bug:
    def __init__(self, timestep=0.1, x=3, isWrapOn=False):
        self.timestep = timestep
        self.x = x
        self.isWrapOn = isWrapOn
        self.__shifter = Shifter(23, 25, 24)
        self._running = False  # Add flag for control
        
    def start(self):
        self._running = True
        
        while self._running:  # Add this loop!
            # Display current LED position
            pattern = 1 << self.x
            self.__shifter.shiftByte(pattern)
            
            # Wait for timestep
            time.sleep(self.timestep)
            
            # Random walk: move +1 or -1
            step = random.choice([-1, 1])
            new_position = self.x + step
            
            # Handle boundaries based on isWrapOn
            if self.isWrapOn:
                self.x = new_position % 8
            else:
                if 0 <= new_position <= 7:
                    self.x = new_position
                    
    def stop(self):
        self._running = False  # Stop the loop
        self.__shifter.shiftByte(0)
