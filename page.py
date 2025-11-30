import socket
import threading
import requests
import json
import time

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter
import multiprocessing

# === Hardware Setup ===
dataPin, latchPin, clockPin = 16, 21, 20
sh = Shifter(dataPin, latchPin, clockPin)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(sh, lock1)  # azimuth
m2 = Stepper(sh, lock2)  # elevation

POSITIONS_URL = "http://192.168.1.254:8000/positions.json"
TEAM_ID = "1"   # change for your group


# ----------------------------------------------------
#  HTML PAGE
# ----------------------------------------------------
def web_page(az, el, led, positions_text=""):
    html = """
    <html><head><title>Turret Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
    html{font-family: Helvetica; text-align:center;}
    h1{color:#0F3376;}
    .button{background-color:#e7bd3b; border:none; padding:10px 30px;
            color:white; font-size:22px; border-radius:4px; margin:8px;}
    .button2{background-color:#4286f4;}
    input{font-size:20px; padding:6px; margin:6px;}
    pre{text-align:left; border:1px solid #ddd; padding:10px; width:80%; margin:auto;}
    </style>

    </head>
    <body>

    <h1>Laser Turret Control</h1>

    <h2>Current Values</h2>
    <p>Azimuth: <strong>""" + str(az) + """°</strong></p>
    <p>Elevation: <strong>""" + str(el) + """°</strong></p>
    <p>LED State: <strong>""" + ("ON" if led else "OFF") + """</strong></p>

    <h2>Move Motors</h2>

    <form action="/" method="POST">
        <input type="hidden" name="motor" value="az">
        <label>Set Azimuth:
            <input type="number" name="angle" min="-180" max="180" step="1">
        </label>
        <button type="submit" class="button">Move</button>
    </form>

    <form action="/" method="POST">
        <input type="hidden" name="motor" value="el">
        <label>Set Elevation:
            <input type="number" name="angle" min="-90" max="90" step="1">
        </label>
        <button type="submit" class="button">Move</button>
    </form>

    <h2>LED Control</h2>
    <form action="/" method="POST">
        <button class="button button2" type="submit" name="led" value="toggle">
            Toggle LED
        </button>
    </form>

    <h2>Read positions.json</h2>
    <form action="/" method="POST">
        <input type="hidden" name="get_positions" value="1">
        <button type="submit" class="button">Load positions.json</button>
    </form>

    <pre>""" + positions_text + """</pre>

    </body></html>
    """
    return html.encode("utf-8")



# ----------------------------------------------------
#  POST PARSER (matches professor’s format)
# ----------------------------------------------------
def parsePOSTdata(msg):
    data = {}
    idx = msg.find("\r\n\r\n") + 4
    body = msg[idx:]
    pairs = body.split("&")
    for pair in pairs:
        kv = pair.split("=")
        if len(kv) == 2:
            data[kv[0]] = kv[1]
    return data



# ----------------------------------------------------
#  MAIN SERVER THREAD
# ----------------------------------------------------
def serve_web_page():
    while True:
        conn, (client_ip, client_port) = s.accept()
        print(f"\nConnection from {client_ip}:{client_port}")

        request = conn.recv(4096).decode("utf-8")
        print("Request:\n", request)

        # default text
        positions_text = ""

        if "POST" in request:
            data = parsePOSTdata(request)
            print("Parsed:", data)

            # -----------------------------------------------
            # Move motors (non-blocking, multiprocessing!)
            # -----------------------------------------------
            if "motor" in data and "angle" in data:
                try:
                    angle = float(data["angle"].replace("+",""))
                    if data["motor"] == "az":
                        m1.goAngle(angle)
                    elif data["motor"] == "el":
                        m2.goAngle(angle)
                except:
                    print("Invalid angle POST data")

            # -----------------------------------------------
            # LED toggle
            # -----------------------------------------------
            if data.get("led") == "toggle":
                with led_state.get_lock():
                    if led_state.value == 0:
                        led_on()
                    else:
                        led_off()

            # -----------------------------------------------
            # Read positions.json
            # -----------------------------------------------
            if "get_positions" in data:
                try:
                    r = requests.get(POSITIONS_URL, timeout=2)
                    j = r.json()
                    my_pos = j["turrets"].get(TEAM_ID, "Not found")
                    positions_text = json.dumps(my_pos, indent=2)
                except Exception as e:
                    positions_text = "Error: " + str(e)

        # --------------------------------------------
        # Send response
        # --------------------------------------------
        az = round(m1.angle.value, 2)
        el = round(m2.angle.value, 2)

        with led_state.get_lock():
            led = led_state.value

        html = web_page(az, el, led, positions_text)

        conn.send(b"HTTP/1.1 200 OK\r\n")
        conn.send(b"Content-Type: text/html\r\n")
        conn.send(b"Connection: close\r\n\r\n")
        conn.sendall(html)

        conn.close()



# ----------------------------------------------------
#  SERVER INITIALIZATION
# ----------------------------------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 80))   # requires sudo
s.listen(3)

thread = threading.Thread(target=serve_web_page)
thread.daemon = True
thread.start()

print("Webserver running on http://<your-pi-ip>/ ...")

try:
    while True:
        time.sleep(1)
except:
    s.close()
