from lab6run import Bug

import RPi.GPIO as GPIO

bug = Bug()

try:
    # Start the random walk (this blocks until stopped)
    bug.start()
except KeyboardInterrupt:
    # User pressed Ctrl+C to stop
    bug.stop()
    GPIO.cleanup()
    print("\nStopping bug...")
# finally:
