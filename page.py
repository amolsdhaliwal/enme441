import socket
import threading
import requests
import json
import multiprocessing
import time
import math

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

# -----------------------------
# HARDWARE SETUP
# -----------------------------
data = 16
clock = 20
latch = 21
shifter = Shifter(data, clock, latch)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(shifter, lock1)    # Azimuth
m2 = Stepper(shifter, lock2)    # Elevation

TEAM_ID = "19"
POSITIONS_URL = "http://192.168.1.254:8000/positions.json"

# -----------------------------
# GLOBAL STATE
# -----------------------------
loaded_targets = []
stop_firing = False
positions_text = ""

# -----------------------------
# WEB PAGE
# -----------------------------
def web_page(status="", positions=""):
    laser_state = "ON" if led_state.value else "OFF"

    return f"""
    <html>
    <head>
        <title>Laser Turret Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Helvetica;
                background:#111;
                color:#eee;
                text-align:center;
            }}
            button {{
                font-size:18px;
                padding:10px 18px;
                margin:4px;
                border:none;
                border-radius:4px;
                cursor:pointer;
            }}
            input[type=range] {{
                width:300px;
            }}
            input[type=number] {{
                font-size:16px;
                width:90px;
            }}
            .az {{ background:#3498db; }}
            .el {{ background:#9b59b6; }}
            .zero {{ background:#95a5a6; }}
            .led {{ background:#f1c40f; color:#000; }}
            .load {{ background:#2ecc71; }}
            .fire {{ background:#e67e22; }}
            .stop {{ background:#e74c3c; }}
            pre {{
                width:85%;
                margin:auto;
                background:#222;
                padding:10px;
                text-align:left;
            }}
        </style>
    </head>

    <body>
        <h1>Laser Turret Control</h1>

        <h2>Calibration</h2>

        <h3>Azimuth Jog</h3>
        <form method="POST">
            <input type="range" min="-2" max="2" step="0.05"
                   name="az_slider"
                   oninput="this.form.submit(); this.value=0;">
        </form>

        <form method="POST">
            <input type="number" step="0.1" name="az_goto" placeholder="deg">
            <button class="az">Go</button>
        </form>

        <h3>Elevation Jog</h3>
        <form method="POST">
            <input type="range" min="-2" max="2" step="0.05"
                   name="el_slider"
                   oninput="this.form.submit(); this.value=0;">
        </form>

        <form method="POST">
            <input type="number" step="0.1" name="el_goto" placeholder="deg">
            <button class="el">Go</button>
        </form>

        <h2>Zero</h2>
        <form method="POST">
            <button class="zero" name="set_zero" value="az">Zero Azimuth</button>
            <button class="zero" name="set_zero" value="el">Zero Elevation</button>
        </form>

        <h2>Laser</h2>
        <form method="POST">
            <button class="led" name="led" value="toggle">Toggle Laser</button>
        </form>
        <p>Laser State: <b>{laser_state}</b></p>

        <h2>JSON Control</h2>
        <form method="POST">
            <button class="load" name="load_json" value="1">Load Positions</button>
            <button class="fire" name="start_firing" value="1">Start Firing</button>
            <button class="stop" name="stop" value="1">STOP</button>
        </form>

        <h2>Status</h2>
        <pre>{status}</pre>

        <h2>positions.json</h2>
        <pre>{positions}</pre>

    </body>
    </html>
    """.encode("utf-8")

# -----------------------------
# POST PARSER
# -----------------------------
def parsePOST(msg):
    d = {}
    idx = msg.find("\r\n\r\n")
    if idx == -1:
        return d
    body = msg[idx + 4:]
    for p in body.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            d[k] = v
    return d

# -----------------------------
# FIRING THREAD
# -----------------------------
def firing_sequence():
    global stop_firing
    stop_firing = False

    for az, el in loaded_targets:
        if stop_firing:
            break

        led_off()

        m1.goAngle(az)
        m2.goAngle(el)

        m1.wait()
        m2.wait()

        if stop_firing:
            break

        led_on()
        time.sleep(3)
        led_off()

# -----------------------------
# SERVER LOOP
# -----------------------------
def serve():
    global loaded_targets, stop_firing, positions_text

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 80))
    s.listen(3)

    status = ""

    while True:
        conn, _ = s.accept()
        msg = conn.recv(4096).decode("utf-8")
        data = parsePOST(msg)

        # ---- Slider jogs ----
        if "az_slider" in data:
            m1.rotate(float(data["az_slider"]))

        if "el_slider" in data:
            m2.rotate(float(data["el_slider"]))

        # ---- Typed angle ----
        if "az_goto" in data:
            m1.goAngle(float(data["az_goto"]))

        if "el_goto" in data:
            m2.goAngle(float(data["el_goto"]))

        # ---- Zero ----
        if "set_zero" in data:
            if data["set_zero"] == "az":
                m1.zero()
            elif data["set_zero"] == "el":
                m2.zero()

        # ---- Laser ----
        if data.get("led") == "toggle":
            led_off() if led_state.value else led_on()

        # ---- Stop ----
        if "stop" in data:
            stop_firing = True
            led_off()
            status = "Firing stopped."

        # ---- Start ----
        if "start_firing" in data and loaded_targets:
            threading.Thread(target=firing_sequence, daemon=True).start()
            status = "Firing sequence started."

        conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
        conn.sendall(web_page(status, positions_text))
        conn.close()

threading.Thread(target=serve, daemon=True).start()
print("Open page at http://<pi_ip>/")

while True:
    time.sleep(1)
