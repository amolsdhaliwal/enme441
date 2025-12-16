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
loaded_targets = []   # [(az, el), ...]
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

        <!-- ================= CALIBRATION ================= -->
        <h2>Calibration (Jog Control)</h2>

        <h3>Azimuth</h3>
        <form method="POST">
            <button class="az" name="jog_az" value="-5">-5°</button>
            <button class="az" name="jog_az" value="-1">-1°</button>
            <button class="az" name="jog_az" value="-0.1">-0.1°</button>
            <button class="az" name="jog_az" value="0.1">+0.1°</button>
            <button class="az" name="jog_az" value="1">+1°</button>
            <button class="az" name="jog_az" value="5">+5°</button>
        </form>

        <h3>Elevation</h3>
        <form method="POST">
            <button class="el" name="jog_el" value="-5">-5°</button>
            <button class="el" name="jog_el" value="-1">-1°</button>
            <button class="el" name="jog_el" value="-0.1">-0.1°</button>
            <button class="el" name="jog_el" value="0.1">+0.1°</button>
            <button class="el" name="jog_el" value="1">+1°</button>
            <button class="el" name="jog_el" value="5">+5°</button>
        </form>

        <!-- ================= ZERO ================= -->
        <h2>Set Zero</h2>
        <form method="POST">
            <button class="zero" name="set_zero" value="az">Zero Azimuth</button>
            <button class="zero" name="set_zero" value="el">Zero Elevation</button>
        </form>

        <!-- ================= LASER ================= -->
        <h2>Laser</h2>
        <form method="POST">
            <button class="led" name="led" value="toggle">Toggle Laser</button>
        </form>
        <p>Laser State: <b>{laser_state}</b></p>

        <!-- ================= JSON CONTROL ================= -->
        <h2>JSON Control</h2>
        <form method="POST">
            <button class="load" name="load_json" value="1">Load Positions</button>
            <button class="fire" name="start_firing" value="1">Start Firing</button>
            <button class="stop" name="stop" value="1">STOP</button>
        </form>

        <!-- ================= STATUS ================= -->
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

        time.sleep(0.5)

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

        # ---- Manual move ----
        if "move" in data:
            if data.get("theta"):
                m1.goAngle(float(data["theta"]))
            if data.get("z"):
                m2.goAngle(float(data["z"]))

        # ---- Zeroing ----
        if "set_zero" in data:
            if data["set_zero"] == "az":
                m1.zero()
            elif data["set_zero"] == "el":
                m2.zero()

        # ---- Laser toggle ----
        if data.get("led") == "toggle":
            if led_state.value:
                led_off()
            else:
                led_on()

        # ---- STOP ----
        if "stop" in data:
            stop_firing = True
            led_off()
            status = "Firing stopped."

        # ---- LOAD JSON FROM URL ----
        if "load_json" in data:
            loaded_targets.clear()

            try:
                r = requests.get(POSITIONS_URL, timeout=2)
                j = r.json()

                # ---- OFFLINE TESTING OPTION ----
                """
                j = {
                    "turrets": {
                        "1":  {"r": 300.0, "theta": 1.5882496193148399},
                        "2":  {"r": 300.0, "theta": 5.7246799465414},
                        "3":  {"r": 300.0, "theta": 4.572762640225144},
                        "4":  {"r": 300.0, "theta": 0.41887902047863906},
                        "5":  {"r": 300.0, "theta": 0.017453292519943295},
                        "6":  {"r": 300.0, "theta": 0.6981317007977318},
                        "7":  {"r": 300.0, "theta": 5.794493116621174},
                        "8":  {"r": 300.0, "theta": 3.211405823669566},
                        "9":  {"r": 300.0, "theta": 5.8643062867009474},
                        "10": {"r": 300.0, "theta": 2.007128639793479},
                        "11": {"r": 300.0, "theta": 5.427973973702365},
                        "12": {"r": 300.0, "theta": 0.890117918517108},
                        "13": {"r": 300.0, "theta": 1.4835298641951802},
                        "14": {"r": 300.0, "theta": 3.385938748868999},
                        "15": {"r": 300.0, "theta": 0.7853981633974483},
                        "16": {"r": 300.0, "theta": 3.036872898470133},
                        "17": {"r": 300.0, "theta": 1.2915436464758039},
                        "18": {"r": 300.0, "theta": 1.117010721276371},
                        "19": {"r": 300.0, "theta": 0.017453292519943295},
                        "20": {"r": 300.0, "theta": 5.026548245743669}
                    },
                    "globes": [
                        {"r": 300.0, "theta": 3.385938748868999, "z": 103.0},
                        {"r": 300.0, "theta": 6.19591884457987,  "z": 16.0},
                        {"r": 300.0, "theta": 1.2740903539558606, "z": 172.0},
                        {"r": 300.0, "theta": 0.8203047484373349, "z": 197.0},
                        {"r": 300.0, "theta": 5.654866776461628, "z": 90.0},
                        {"r": 300.0, "theta": 1.0297442586766543, "z": 35.0},
                        {"r": 300.0, "theta": 4.852015320544236, "z": 118.0},
                        {"r": 300.0, "theta": 1.902408884673819, "z": 139.0}
                    ]
                }
                """


                positions_text = json.dumps(j, indent=2)

                our_theta = math.degrees(j["turrets"][TEAM_ID]["theta"])

                # ---- Turrets first ----
                for tid, t in j["turrets"].items():
                    if tid == TEAM_ID:
                        continue

                    diff = abs(math.degrees(t["theta"]) - our_theta) % 360
                    az = round((180 - diff) / 2)

                    loaded_targets.append((az, 0.0))

                # ---- Globes second (UNCHANGED elevation math) ----
                for g in j["globes"]:
                    diff = abs(math.degrees(g["theta"]) - our_theta) % 360
                    az = round((180 - diff) / 2)

                    D = 2 * g["r"] * math.cos(math.radians(az))
                    el = math.degrees(math.atan(g["z"] / D))

                    loaded_targets.append((az, el))

                status = f"Loaded {len(loaded_targets)} targets from URL."

            except Exception as e:
                status = f"Error loading JSON: {e}"

        # ---- START FIRING ----
        if "start_firing" in data and loaded_targets:
            threading.Thread(target=firing_sequence, daemon=True).start()
            status = "Firing sequence started."

        # ---- RESPOND ----
        try:
            conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
            conn.sendall(web_page(status, positions_text))
        except BrokenPipeError:
            pass
        finally:
            conn.close()


threading.Thread(target=serve, daemon=True).start()
print("Open page at http://<pi_ip>/")

while True:
    time.sleep(1)
