import RPi.GPIO as gpio
import threading
import socket

gpio.setmode(gpio.BCM)

pins = {
    "led1": 14,
    "led2": 15,
    "led3": 18
}

for pin in pins.values():
    gpio.setup(pin, gpio.OUT)

pwms = {led: gpio.PWM(pin, 500) for led, pin in pins.items()}


for pwm in pwms.values():
    pwm.start(0)

brightness = {
    "led1": 0,
    "led2": 0,
    "led3": 0
}

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
        <input type="radio" name="led" value="led1"> LED 1 ({0}%)<br>
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
        if "led" in data_dict.keys():
            selected = data_dict["led"]
            try:
                output = int(data_dict.get("brightness", "0"))
            except ValueError:
                output = 0
            output = max(0, min(100, output))
            brightness[selected] = output
            pwms[selected].ChangeDutyCycle(output)

        conn.send(b'HTTP/1.1 200 OK\r\n')
        conn.send(b'Content-Type: text/html\r\n')
        conn.send(b'Connection: close\r\n\r\n')
        try:
            conn.sendall(web_page())
        except BrokenPipeError:
            pass
        finally:
            conn.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(3)
webpageTread = threading.Thread(target=serve_web_page)
webpageTread.daemon = True
webpageTread.start()


try:
    while True:
        pass
except KeyboardInterrupt:
    pass
finally:
    print('Joining webpageTread')
    webpageTread.join()
    s.close()
    print("Shutting down...")
    for pwm in pwms.values():
        pwm.stop()
    gpio.cleanup()
