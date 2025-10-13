import random
import time
from shifter import Shifter  # Import your Shifter class

class Bug:
    def __init__(self,timestep=.1,x=3,isWrapOn=False):
        self.timestep=timestep
        self.x=x
        self.__shifter=Shifter(23,25,24)
        
    def start(self):
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
                # Wrap around: 0 -> 7 or 7 -> 0
                self.x = new_position % 8
            else:
                # Bounce: stay within 0-7 bounds
                if 0 <= new_position <= 7:
                    self.x = new_position
    def stop(self):           
        self.__shifter.shiftByte(0)  # Turn off all LEDs
