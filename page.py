import socket
import threading
import requests
import json
import multiprocessing

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

### --- Hardware Setup --- ###
DATA = 16
CLOCK = 20
LATCH = 21
sh = Shifter(DATA, CLOCK, LATCH)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(sh, lock1)    # Azimuth
m2 = Stepper(sh, lock2)    # Elevation

POSITIONS_URL = "http://192.168.1.254:8000/positions.json"
TEAM_ID = "1"


### --- HTML Page --- ###
def web_page(az, el, led_is_on, positions=""):
    state_str = "ON" if led_is_on else "OFF"

    html = """
    <html><head><title>Turret Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    html{font-family: Helvetica; text-align:center; margin:0px auto;}
    .button{background:#e7bd3b; color:white; padding:10px 25px;
            border:none; border-radius:4px; font-size:22px;}
    .button2{background:#4286f4;}
    input{font-size:20px;}
    pre{width:80%; margin:auto; text-align:left; border:1px solid #ccc; padding:10px;}
    </style></head><body>

    <h1>Laser Turret Control</h1>

    <h2>Azimuth:</h2>
    <form method="POST">
        <input type="hidden" name="motor" value="az">
        <input type="text" name="angle">
        <button class="button" type="submit">Move</button>
    </form>

    <h2>Elevation:</h2>
    <form method="POST">
        <input type="hidden" name="motor" value="el">
        <input type="text" name="angle">
        <button class="button" type="submit">Move</button>
    </form>

    <h2>LED: """ + state_str + """</h2>
    <form method="POST">
        <button class="button button2" type="submit" name="led" value="toggle">Toggle LED</button>
    </form>

    <h2>positions.json</h2>
    <form method="POST">
        <button class="button" type="submit" name="get_positions" value="1">Load</button>
    </form>

    <pre>""" + positions + """</pre>

    </body></html>
    """

    return html.encode("utf-8")


### --- POST Parsing --- ###
def parsePOST(msg):
    d = {}
    idx = msg.find("\r\n\r\n") + 4
    body = msg[idx:]
    pairs = body.split("&")
    for p in pairs:
        if "=" in p:
            k, v = p.split("=")
            d[k] = v
    return d


### --- Server Logic --- ###
def serve_web_page():
    while True:
        conn, addr = s.accept()
        msg = conn.recv(4096).decode("utf-8")

        positions_text = ""
        if "POST" in msg:
            data = parsePOST(msg)

            # Motor control
            if "motor" in data and "angle" in data:
                try:
                    angle = float(data["angle"])
                    if data["motor"] == "az":
                        m1.goAngle(angle)
                    elif data["motor"] == "el":
                        m2.goAngle(angle)
                except:
                    pass

            # LED toggle
            if "led" in data and data["led"] == "toggle":
                with led_state.get_lock():
                    if led_state.value == 0:
                        led_on()
                    else:
                        led_off()

            # Read positions.json
            if "get_positions" in data:
                try:
                    r = requests.get(POSITIONS_URL, timeout=2)
                    j = r.json()
                    mine = j["turrets"].get(TEAM_ID, "Not found")
                    positions_text = json.dumps(mine, indent=2)
                except:
                    positions_text = "Error loading file"

        # Current states
        az = round(m1.angle.value, 2)
        el = round(m2.angle.value, 2)

        with led_state.get_lock():
            led_is_on = (led_state.value == 1)

        # Respond
        conn.send(b"HTTP/1.1 200 OK\r\n")
        conn.send(b"Content-Type: text/html\r\n")
        conn.send(b"Connection: close\r\n\r\n")
        conn.sendall(web_page(az, el, led_is_on, positions_text))
        conn.close()


### --- Start Web Server --- ###
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 8080))     # <---- NO SUDO REQUIRED
s.listen(3)

t = threading.Thread(target=serve_web_page)
t.daemon = True
t.start()

print("Open page at:  http://<your_pi_ip>:8080")

while True:
    pass
