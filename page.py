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
    az_current = m1.angle.value
    el_current = m2.angle.value

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
                width: 80%;
            }}
            input[type=number] {{
                width: 60px;
                font-size:16px;
            }}
        </style>
    </head>

    <body>
        <h1>Laser Turret Control</h1>

        <!-- ================= CALIBRATION ================= -->
        <h2>Calibration (Sliders & Absolute Input)</h2>

        <h3>Azimuth</h3>
        <input type="range" id="az_slider" min="-5" max="5" step="0.1" value="0">
        <span id="az_display">{az_current:.2f}°</span>
        <form method="POST">
            Absolute: <input type="number" name="az_angle" step="0.1" value="{az_current:.2f}">
            <button type="submit">Go</button>
        </form>
        <script>
            let last_val_az = 0;
            const display_az = document.getElementById('az_display');
            const slider_az = document.getElementById('az_slider');
            slider_az.addEventListener('input', function() {{
                let delta = parseFloat(this.value) - last_val_az;
                last_val_az = parseFloat(this.value);
                display_az.textContent = (parseFloat(display_az.textContent) + delta).toFixed(2) + '°';

                if (Math.abs(delta) < 0.01) return;
                fetch("/", {{
                    method: "POST",
                    body: "az_slider=" + delta,
                    headers: {{ "Content-Type": "application/x-www-form-urlencoded" }}
                }});
            }});
        </script>

        <h3>Elevation</h3>
        <input type="range" id="el_slider" min="-5" max="5" step="0.1" value="0">
        <span id="el_display">{el_current:.2f}°</span>
        <form method="POST">
            Absolute: <input type="number" name="el_angle" step="0.1" value="{el_current:.2f}">
            <button type="submit">Go</button>
        </form>
        <script>
            let last_val_el = 0;
            const display_el = document.getElementById('el_display');
            const slider_el = document.getElementById('el_slider');
            slider_el.addEventListener('input', function() {{
                let delta = parseFloat(this.value) - last_val_el;
                last_val_el = parseFloat(this.value);
                display_el.textContent = (parseFloat(display_el.textContent) + delta).toFixed(2) + '°';

                if (Math.abs(delta) < 0.01) return;
                fetch("/", {{
                    method: "POST",
                    body: "el_slider=" + delta,
                    headers: {{ "Content-Type": "application/x-www-form-urlencoded" }}
                }});
            }});
        </script>

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

        # ---- SLIDER MOVES ----
        if "az_slider" in data:
            m1.rotate(float(data["az_slider"]))
        if "el_slider" in data:
            m2.rotate(float(data["el_slider"]))

        # ---- ABSOLUTE MOVES ----
        if "az_angle" in data:
            m1.goAngle(float(data["az_angle"]))
        if "el_angle" in data:
            m2.goAngle(float(data["el_angle"]))

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
                # Replace with requests.get for real URL
                j = {
                    "turrets": {
                        "1": {"r": 182.8, "theta": 5.253441048502932},
                        "2": {"r": 182.8, "theta": 3.5081117965086026},
                        "3": {"r": 182.8, "theta": 1.9198621771937625}
                    },
                    "globes": [{"r": 182.8, "theta": 3.05, "z": 162.6}]
                }
                positions_text = json.dumps(j, indent=2)

                our_theta = math.degrees(j["turrets"][TEAM_ID]["theta"])
                for tid, t in j["turrets"].items():
                    if tid == TEAM_ID:
                        continue
                    diff = abs(math.degrees(t["theta"]) - our_theta) % 360
                    az = round((180 - diff) / 2)
                    loaded_targets.append((az, 0.0))

                for g in j["globes"]:
                    diff = abs(math.degrees(g["theta"]) - our_theta) % 360
                    az = round((180 - diff) / 2)
                    D = 2 * g["r"] * math.cos(math.radians(az))
                    el = math.degrees(math.atan(g["z"] / D))
                    loaded_targets.append((az, el))

                status = f"Loaded {len(loaded_targets)} targets."

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
