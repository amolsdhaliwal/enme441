import socket
import threading
import requests
import json
import multiprocessing
import time
import math

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

data = 16
clock = 20
latch = 21
shifter = Shifter(data, clock, latch)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(shifter, lock1)    # Azimuth (theta)
m2 = Stepper(shifter, lock2)    # Elevation

TEAM_ID = "19"
POSITIONS_URL = "http://192.168.1.254:8000/positions.json"


loaded_targets = []   # [(az, el), ...]
stop_firing = False
positions_text = ""


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
            input[type=number] {{
                width: 80px;
                font-size:16px;
                padding:4px;
            }}
        </style>
    </head>

    <body>
        <h1>Laser Turret Control</h1>

        <h2>Calibration (Absolute & Relative)</h2>

        <h3>Azimuth</h3>
        <form method="POST">
            <button name="jog_az" value="-1">-1°</button>
            <button name="jog_az" value="1">+1°</button>
            <input type="number" step="0.1" name="set_az" value="0">
            <button name="move_az" value="1">Go</button>
        </form>

        <h3>Elevation</h3>
        <form method="POST">
            <button name="jog_el" value="-1">-1°</button>
            <button name="jog_el" value="1">+1°</button>
            <input type="number" step="0.1" name="set_el" value="0">
            <button name="move_el" value="1">Go</button>
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

def parsePOST(msg):
    data_dict = {}
    idx = msg.find("\r\n\r\n")
    if idx == -1:
        return data_dict
    body = msg[idx + 4:]
    for p in body.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            data_dict[k] = v
    return data_dict

def firing_sequence(): # firing operation
    global stop_firing
    stop_firing = False # change state when firing
    for az, el in loaded_targets:
        if stop_firing: # stop if necessary
            break
        led_off()
        m1.goAngle(az)
        m2.goAngle(el)
        m1.wait() # finish motor movements before turning laser
        m2.wait()
        if stop_firing:
            break
        led_on()
        time.sleep(3)
        led_off()


def serve_web_page():
    global loaded_targets, stop_firing, positions_text

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 80))
    s.listen(3)

    status = ""

    while True:
        conn, _ = s.accept()
        msg = conn.recv(4096).decode("utf-8")
        data = parsePOST(msg)
# call for actions based on html input
        if "jog_az" in data: 
            m1.rotate(float(data["jog_az"]))
        if "jog_el" in data:
            m2.rotate(float(data["jog_el"]))

        if "move_az" in data and "set_az" in data:
            m1.goAngle(float(data["set_az"]))
        if "move_el" in data and "set_el" in data:
            m2.goAngle(float(data["set_el"]))

        if "set_zero" in data:
            if data["set_zero"] == "az":
                m1.zero()
            elif data["set_zero"] == "el":
                m2.zero()

        if data.get("led") == "toggle":
            if led_state.value:
                led_off()
            else:
                led_on()

        if "stop" in data:
            stop_firing = True
            led_off()
            status = "Firing stopped."

        if "load_json" in data:
            loaded_targets.clear() # clear old json
            try:
                r = requests.get(POSITIONS_URL, timeout=2)
                j = r.json() 
                
                # offline test for testing
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
                        "19": {"r": 182.8, "theta": 3.9968039870670142}, # us (229)
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

                for tid, t in j["turrets"].items():
                    if tid == TEAM_ID: #skip self
                        continue
                    diff = -(math.degrees(t["theta"]) - our_theta) % 360 # find difference between us and target angle
                    az = round((180 - diff) / 2) # using trig, make isosceles triangle to find the angle needed to reach target
                    loaded_targets.append((az, 0.0)) # elevation angle 0 for all turrets

                for g in j["globes"]:
                    diff = -(math.degrees(g["theta"]) - our_theta) % 360
                    az = round((180 - diff) / 2)
                    D = 2 * g["r"] * math.cos(math.radians(az)) # using angle from isosceles, split into two right triangles to find the direct distance to the globe
                    el = math.degrees(math.atan(g["z"] / D)) # using a right triangle, find angle height using distance and height of glove
                    loaded_targets.append((az, el))

                status = f"Loaded {len(loaded_targets)} targets."

            except Exception as e:
                status = f"Error loading JSON: {e}"

        if "start_firing" in data and loaded_targets:
            threading.Thread(target=firing_sequence, daemon=True).start()
            status = "Firing sequence started."
        try:
            conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
            conn.sendall(web_page(status, positions_text))
        except BrokenPipeError:
            pass
        finally:
            conn.close()

threading.Thread(target=serve_web_page, daemon=True).start()
print("Open page at http://terrapi.local/")

while True:
    time.sleep(1)

