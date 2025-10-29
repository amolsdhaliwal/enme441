import RPi.GPIO as gpio
import threading
import socket

# --------------------------
# Raspberry Pi GPIO Setup
# --------------------------
gpio.setmode(gpio.BCM)

# Assign LED pins
led_pins = {
    "led1": 14,
    "led2": 15,
    "led3": 18
}

# Set pins as outputs
for pin in led_pins.values():
    gpio.setup(pin, gpio.OUT)

# Create PWM objects at 1 kHz
pwms = {
    "led1": gpio.PWM(led_pins["led1"], 1000),
    "led2": gpio.PWM(led_pins["led2"], 1000),
    "led3": gpio.PWM(led_pins["led3"], 1000)
}

# Start all PWM at 0% brightness
for pwm in pwms.values():
    pwm.start(0)

# Store brightness states
brightness = {
    "led1": 0,
    "led2": 0,
    "led3": 0
}

# --------------------------
# HTML Page
# --------------------------
def web_page():
    html = """
    <html><head><title>LED Brightness Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
    html{{ font-family: Helvetica; text-align: center; }}
    p{{ font-size: 1.2rem; }}
    </style>
    </head>

    <body>
      <h1>Adjust LED Brightness</h1>
      <form action="/" method="POST">
        <p>Brightness level:</p>
        <input type="range" id="brightness" name="brightness" min="0" max="100" value="0"><br><br>

        <p>Select LED:</p>
        <input type="radio" name="led" value="led1" checked> LED 1 ({0}%)<br>
        <input type="radio" name="led" value="led2"> LED 2 ({1}%)<br>
        <input type="radio" name="led" value="led3"> LED 3 ({2}%)<br><br>

        <input type="submit" value="Change Brightness">
      </form>
    </body>
    </html>
    """.format(brightness["led1"], brightness["led2"], brightness["led3"])

    return bytes(html, 'utf-8')


def parsePOSTdata(data):
    data_dict = {}
    idx = data.find('\r\n\r\n')+4
    data = data[idx:]
    data_pairs = data.split('&')
    for pair in data_pairs:
        key_val = pair.split('=')
        if len(key_val) == 2:
            data_dict[key_val[0]] = key_val[1]
    return data_dict

def serve_web_page():
    while True:
        print("Waiting for connection...")
        conn, (client_ip, client_port) = s.accept()

        print(f"Connected: {client_ip}:{client_port}")

        client_message = conn.recv(2048).decode('utf-8')
        print(f"Message:\n{client_message}")

        data_dict = parsePOSTdata(client_message)

        # Check if a form was submitted
        if "led" in data_dict.keys():
            selected_led = data_dict["led"]
            try:
                new_value = int(data_dict.get("brightness", "0"))
            except ValueError:
                new_value = 0
            new_value = max(0, min(100, new_value))

            # Update stored brightness
            if selected_led in brightness and selected_led in pwms:
                brightness[selected_led] = new_value
                # Apply brightness via PWM
                pwms[selected_led].ChangeDutyCycle(new_value)

        # Build response once, include Content-Length, and send in one call
        conn.send(b'HTTP/1.1 200 OK\r\n')                  # status line
        conn.send(b'Content-Type: text/html\r\n')          # headers
        conn.send(b'Connection: close\r\n\r\n')
        try:
            conn.sendall(web_page())
        except BrokenPipeError:
            # Client closed early; ignore
            pass
        finally:
            conn.close()

# --------------------------
# Setup Socket
# --------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(3)

webpageTread = threading.Thread(target=serve_web_page)
webpageTread.daemon = True
webpageTread.start()

# --------------------------
# Main Loop
# --------------------------
try:
    while True:
        pass
except KeyboardInterrupt:
    # Close socket first to unblock accept(), then join the thread
    print('Joining webpageTread')
    server_thread.join()
    s.close()
    print("Shutting down...")

    # Stop PWM before GPIO cleanup
    for pwm in pwms.values():
        pwm.stop()
    gpio.cleanup()
