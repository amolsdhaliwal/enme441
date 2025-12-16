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
            input[type=range] {{
                width: 70%;
            }}
            input[type=number] {{
                width: 80px;
            }}
        </style>
    </head>

    <body>
        <h1>Laser Turret Control</h1>

        <h2>Calibration</h2>

        <h3>Azimuth</h3>
        <form method="POST">
            <input type="range" name="slider_az" min="0" max="360" step="0.1" value="0" oninput="this.nextElementSibling.value=this.value">
            <input type="number" name="input_az" value="0" step="0.1" oninput="this.previousElementSibling.value=this.value">
            <button type="submit" name="move_az">Move</button>
        </form>

        <h3>Elevation</h3>
        <form method="POST">
            <input type="range" name="slider_el" min="0" max="360" step="0.1" value="0" oninput="this.nextElementSibling.value=this.value">
            <input type="number" name="input_el" value="0" step="0.1" oninput="this.previousElementSibling.value=this.value">
            <button type="submit" name="move_el">Move</button>
        </form>

        <h2>Set Zero</h2>
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
        # Wait until both motors reach their target
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

        # ---- Calibration sliders / inputs ----
        if "move_az" in data:
            if "slider_az" in data:
                m1.goAngle(float(data["slider_az"]))
            elif "input_az" in data:
                m1.goAngle(float(data["input_az"]))

        if "move_el" in data:
            if "slider_el" in data:
                m2.goAngle(float(data["slider_el"]))
            elif "input_el" in data:
                m2.goAngle(float(data["input_el"]))

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

        # ---- LOAD JSON ----
        if "load_json" in data:
            loaded_targets.clear()
            try:
                # --- Main retrieval from URL ---
                r = requests.get(POSITIONS_URL, timeout=2)
                j = r.json()

                # --- Offline JSON fallback for testing ---
                """
                j = {
                    "turrets": {
                        "1": {"r": 182.8, "theta": 5.253441048502932},
                        "2": {"r": 182.8, "theta": 3.5081117965086026},
                        "3": {"r": 182.8, "theta": 1.9198621771937625},
                        "4": {"r": 182.8, "theta": 4.4505895925855405},
                        "5": {"r": 182.8, "theta": 0.4363323129985824},
                        "6": {"r": 182.8, "theta": 2.478367537831948},
                        "7": {"r": 182.8, "theta": 1.6231562043547263},
                        "8": {"r": 182.8, "theta": 5.707226654021458},
                        "9": {"r": 182.8, "theta": 4.153883619746504},
                        "10": {"r": 182.8, "theta": 3.3510321638291125},
                        "11": {"r": 182.8, "theta": 4.71238898038469},
                        "12": {"r": 182.8, "theta": 2.234021442552742},
                        "13": {"r": 182.8, "theta": 2.9670597283903604},
                        "14": {"r": 182.8, "theta": 0.8028514559173915},
                        "15": {"r": 182.8, "theta": 1.239183768915974},
                        "16": {"r": 182.8, "theta": 0.20943951023931953},
                        "17": {"r": 182.8, "theta": 4.886921905584122},
                        "18": {"r": 182.8, "theta": 3.1764992386296798},
                        "19": {"r": 182.8, "theta": 3.9968039870670142},
                        "20": {"r": 182.8, "theta": 6.2482787221397},
                        "21": {"r": 182.8, "theta": 2.8099800957108703},
                        "22": {"r": 182.8, "theta": 3.787364476827695}
                    },
                    "globes": [
                        {"r": 182.8, "theta": 3.05, "z": 162.6},
                        {"r": 182.8, "theta": 1.047, "z": 195.6}
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

                # ---- Globes second ----
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


# -----------------------------
# START SERVER
# -----------------------------
threading.Thread(target=serve, daemon=True).start()
print("Open page at http://<pi_ip>/")

while True:
    time.sleep(1)
