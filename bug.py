import RPi.GPIO as GPIO
import time
from shifter import Bug  # Import Bug class from your shifter.py file

# Define GPIO pins for switches (change these to match your setup)
S1_PIN = 16  # Bug on/off
S2_PIN = 20  # Toggle wrap
S3_PIN = 21  # Speed control

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(S1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Instantiate Bug with default values
bug = Bug()

# Track previous state of s2 for state change detection
s2_prev_state = GPIO.input(S2_PIN)
bug_is_running = False

print("Bug controller started. Press Ctrl+C to exit.")

try:
    while True:
        # Read switch states
        s1_state = GPIO.input(S1_PIN)
        s2_state = GPIO.input(S2_PIN)
        s3_state = GPIO.input(S3_PIN)
        
        # s1: Turn bug on when HIGH, off when LOW
        if s1_state and not bug_is_running:
            bug.start()
            bug_is_running = True
            print("Bug started")
        elif not s1_state and bug_is_running:
            bug.stop()
            bug_is_running = False
            print("Bug stopped")
        
        # s2: Detect state change to toggle wrapping
        if s2_state != s2_prev_state:
            if s2_state:  # Only toggle on rising edge (button press)
                bug.isWrapOn = not bug.isWrapOn
                print(f"Wrap mode: {'ON' if bug.isWrapOn else 'OFF'}")
                time.sleep(0.05)  # Simple debounce
            s2_prev_state = s2_state
        
        # s3: Speed control (3x faster when on)
        if s3_state:
            bug.timestep = 0.1 / 3  # 3x faster
        else:
            bug.timestep = 0.1  # Normal speed
        
        time.sleep(0.01)  # Small delay for monitoring loop
        
except KeyboardInterrupt:
    print("\nShutting down...")
    bug.stop()
finally:
    GPIO.cleanup()
