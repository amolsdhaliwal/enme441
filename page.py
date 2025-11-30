import socket
import threading
import requests
import json

from mult import Stepper, led_on, led_off, led_state  # import your LED functions
from shifter import Shifter

# === Hardware Setup ===
dataPin, latchPin, clockPin = 16, 21, 20
sh = Shifter(dataPin, latchPin, clockPin)

m1 = Stepper(sh, None)  # azimuth
m2 = Stepper(sh, None)  # elevation

POSITIONS_URL = "http://192.168.1.254:8000/positions.json"
TEAM_ID = "1"   # change this to your team ID


# === HTML Web Page ===
def web_page(az, el, led_state, positions_text=""):
    html = """
    <html><head><title>Turret Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    html{font-family: Helvetica; text-align:center; margin:0px auto;}
    h1{color:#0F3376; padding:2vh;}
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
    <p>LED State: <strong>""" + ("ON" if led_state else "OFF") + """</strong></p>

    <h2>Move Motors</h2>

    <form action="/" method="POST">
        <input type="hidden" name="motor" value="az">
        Set Azimuth (deg): <input type="text" name="angle">
        <button type="submit" class="button">Move</button>
    </form>

    <form action="/" method="POST">
        <input type="hidden" name="motor" value="el">
        Set Elevation (deg): <input type="text" name="angle">
        <button type="submit" class="button">Move</button>
    </form>

    <h2>LED Control</h2>
    <form action="/" method="POST">
        <button class="button" type="submit" name="led" value="on">LED ON</button>
        <button class="button button2" type="submit" name="led" value="off">LED OFF</button>
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


# === Helper: Parse POST exactly like your professor ===
def parsePOSTdata(data):
    data_dict = {}
    idx = data.find("\r\n\r\n") + 4
    body = data[idx:]
    pairs = body.split("&")
    for p in pairs:
        kv = p.split("=")
        if len(kv) == 2:
            data_dict[kv[0]] = kv[1]
    return data_dict


# === Main Server Thread ===
def serve_web_page():
    while True:
        print("Waiting for connection...")
        conn, (client_ip, client_port) = s.accept()
        print(f"Connection from {client_ip}:{client_port}")

        msg = conn.recv(4096).decode("utf-8")
        print("Client message:\n", msg)

        positions_text = ""

        # Parse POST data
        if "POST" in msg:
            data = parsePOSTdata(msg)

            # --- Motor control ---
            if "motor" in data and "angle" in data:
                try:
                    angle = float(data["angle"])
                    if data["motor"] == "az":
                        m1.goAngle(angle)
                    elif data["motor"] == "el":
                        m2.goAngle(angle)
                except:
                    pass

            # --- LED control ---
            if "led" in data:
                if data["led"] == "on":
                    led_on()
                if data["led"] == "off":
                    led_off()

            # --- Load positions.json ---
            if "get_positions" in data:
                try:
                    r = requests.get(POSITIONS_URL, timeout=2)
                    j = r.json()
                    my_pos = j["turrets"].get(TEAM_ID, "Not found")
                    positions_text = json.dumps({"mine": my_pos}, indent=2)
                except Exception as e:
                    positions_text = "Error: " + str(e)

        # Collect updated values
        az = round(m1.angle.value, 2)
        el = round(m2.angle.value, 2)

        # Send HTTP response
        conn.send(b"HTTP/1.1 200 OK\r\n")
        conn.send(b"Content-Type: text/html\r\n")
        conn.send(b"Connection: close\r\n\r\n")
        conn.sendall(web_page(az, el, led_state, positions_text))
        conn.close()


# === Start Server ===
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 80))
s.listen(3)

thread = threading.Thread(target=serve_web_page)
thread.daemon = True
thread.start()

print("Webserver running on port 80...")

try:
    while True:
        pass
except:
    s.close()
