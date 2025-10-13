import random
import time
from shifter import Shifter  # Import your Shifter class
import RPi.GPIO as GPIO


# a. Instantiate a Shifter object
led_controller = Shifter(23,25,24)

# Initialize the LED position (0-7 represents the 8 LEDs)
position = 4  # Start in the middle

try:
    # b. Random walk loop
    while True:
        # Create byte pattern with only one bit set at current position
        pattern = 1 << position
        
        # Send pattern to shift register
        led_controller.shiftByte(pattern)
        
        # Wait for the time step
        time.sleep(0.05)
        
        # Random walk: move +1 or -1 with equal probability
        step = random.choice([-1, 1])
        new_position = position + step
        
        # Boundary checking: prevent moving beyond edges
        if 0 <= new_position <= 7:
            position = new_position
        # If new_position is out of bounds, position stays the same

except KeyboardInterrupt:
    # Turn off all LEDs when exiting
    led_controller.shiftByte(0)
    GPIO.cleanup()
    
