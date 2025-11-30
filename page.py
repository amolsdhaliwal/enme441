import socket
import threading
import json
import requests
import multiprocessing

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

# -------- Hardware -------------
sh = Shifter(16, 21, 20)
lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(sh, lock1)   # azimuth
m2 = Stepper(sh, lock2)   # elevation

POSITIONS_URL = "http://192.168.1.254:8000/positions.json"
TEAM_ID = "1"


# -------- HTML PAGE -------------
def web_page(az, el, led, pos=""):
    html = f"""
    <html><head><title>Turret</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <body>

    <h1>Laser Turret</h1>

    <h2>Status</h2>
    <p>Azimuth: <b>{az}°</b></p>
    <p>Elevation: <b>{el}°</b></p>
    <p>LED: <b>{"ON" if led else "OFF"}</b></p>

    <h2>Move Motors</h2>

    <form method="POST">
      <input type="hidden" name="motor" value="az">
      <input type="range" min="-180" max="180" name="angle">
      <input type="submit" value="Move">
    </form>

    <form method="POST">
      <input type="hidden" name="motor" value="el">
      <input type="range" min="-90" max="90" name="angle">
      <input type="submit" value="Move">
    </form>

    <h2>LED</h2>
    <form method="POST">
      <input type="hidden" name="led" value="toggle">
      <input type="submit" value="Toggle LED">
    </form>

    <h2>Positions.json</h2>
    <form method="POST">
      <input type="hidden" name="get_positions" value="1">
      <input type="submit" value="Load positions.json">
    </form>

    <pre>{pos}</pre>

    </body></html>
    """
    return html.encode()


# -------- POST PARSER ----------
def parsePOST(msg):
    try:
        body = msg[msg.find("\r\n\r\n")+4:]
        out = {}
        for pair in body.split("&"):
            if "=" in pair:
                k, v = pair.split("=")
                out[k] = v
        return out
    except:
        return {}


# -------- Webserver Thread -------
def serve():
    while True:
        conn, addr = s.accept()
        msg = conn.recv(4096).decode()

        data = {}
        if "POST" in msg:
            data = parsePOST(msg)

        # --- Handle Commands ---
        if "motor" in data and "angle" in data:
            try:
                angle = float(data["angle"])
                if data["motor"] == "az":
                    m1.goAngle(angle)
                else:
                    m2.goAngle(angle)
            except:
                pass

        if "led" in data and data["led"] == "toggle":
            with led_state.get_lock():
                if led_state.value == 0:
                    led_on()
                else:
                    led_off()

        pos = ""
        if "get_positions" in data:
            try:
                r = requests.get(POSITIONS_URL, timeout=2)
                j = r.json()
                pos = json.dumps(j["turrets"].get(TEAM_ID, {}), indent=2)
            except Exception as e:
                pos = str(e)

        # --- Compose Response ---
        az = round(m1.angle.value, 2)
        el = round(m2.angle.value, 2)
        led = bool(led_state.value)

        response = web_page(az, el, led, pos)

        conn.send(b"HTTP/1.1 200 OK\r\n")
        conn.send(b"Content-Type: text/html\r\n\r\n")
        conn.sendall(response)
        conn.close()


# -------- Start Server ----------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 8080))
s.listen(3)

thread = threading.Thread(target=serve, daemon=True)
thread.start()

print("Webserver running on port 8080...")

while True:
    pass
