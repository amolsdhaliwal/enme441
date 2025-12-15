import socket
import threading
import multiprocessing
import time
import math

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

# ================== HARDWARE ==================
data = 16
clock = 20
latch = 21
sft = Shifter(data, clock, latch)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(sft, lock1)   # Azimuth
m2 = Stepper(sft, lock2)   # Elevation

TEAM_ID = "19"

# ================== GLOBAL STATE ==================
stop_event = threading.Event()
status_lines = []
status_lock = threading.Lock()

current_az = 0.0
current_el = 0.0


# ================== WEB PAGE ==================
def web_page():
    with status_lock:
        log = "\n".join(status_lines[-60:])

    led_txt = "ON" if led_state.value else "OFF"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Laser Turret Control</title>
<style>
body {{
    font-family: Arial;
    background:#111;
    color:#eee;
    padding:20px;
}}
h1 {{ color:#00ffcc; }}
input {{ font-size:18px; width:80px; }}
button {{
    font-size:18px;
    padding:8px 16px;
    margin:4px;
}}
.fire {{ background:#2ecc71; }}
.stop {{ background:#e74c3c; color:white; }}
.laser {{ background:#f1c40f; }}
pre {{
    background:#222;
    padding:12px;
    border-radius:6px;
    max-height:400px;
    overflow-y:auto;
}}
</style>
</head>

<body>
<h1>Laser Turret Control</h1>

<p><b>Azimuth:</b> {current_az:.1f}°</p>
<p><b>Elevation:</b> {current_el:.1f}°</p>
<p><b>Laser:</b> {led_txt}</p>

<hr>

<h2>Manual Control (Calibration)</h2>
<form method="POST">
    Azimuth (deg):
    <input type="number" step="1" name="az">
    Elevation (deg):
    <input type="number" step="1" name="el">
    <br><br>
    <button type="submit" name="move" value="1">Move</button>
    <button type="submit" name="zero" value="az">Zero Azimuth</button>
    <button type="submit" name="zero" value="el">Zero Elevation</button>
</form>

<hr>

<h2>Laser Test</h2>
<form method="POST">
    <button class="laser" type="submit" name="laser" value="on">Laser ON</button>
    <button class="laser" type="submit" name="laser" value="off">Laser OFF</button>
</form>

<hr>

<h2>JSON Control</h2>
<form method="POST">
    <button class="fire" type="submit" name="fire" value="1">Load & Fire JSON</button>
    <button class="stop" type="submit" name="stop" value="1">STOP</button>
</form>

<h2>Status</h2>
<pre>{log}</pre>

</body>
</html>
"""
    return html.encode()


# ================== JSON ==================
def load_json():
    return {
        "turrets": {
            "1": {"r":300.0,"theta":1.5882496193148399},
            "2": {"r":300.0,"theta":5.7246799465414},
            "3": {"r":300.0,"theta":4.572762640225144},
            "4": {"r":300.0,"theta":0.41887902047863906},
            "5": {"r":300.0,"theta":2.356194490192345},
            "6": {"r":300.0,"theta":0.6981317007977318},
            "7": {"r":300.0,"theta":5.794493116621174},
            "8": {"r":300.0,"theta":3.211405823669566},
            "9": {"r":300.0,"theta":5.8643062867009474},
            "10":{"r":300.0,"theta":2.007128639793479},
            "11":{"r":300.0,"theta":5.427973973702365},
            "12":{"r":300.0,"theta":0.890117918517108},
            "13":{"r":300.0,"theta":1.4835298641951802},
            "14":{"r":300.0,"theta":3.385938748868999},
            "15":{"r":300.0,"theta":0.7853981633974483},
            "16":{"r":300.0,"theta":3.036872898470133},
            "17":{"r":300.0,"theta":1.2915436464758039},
            "18":{"r":300.0,"theta":1.117010721276371},
            "19":{"r":300.0,"theta":0.017453292519943295},
            "20":{"r":300.0,"theta":5.026548245743669}
        },
        "globes": [
            {"r":300.0,"theta":3.385938748868999,"z":103.0},
            {"r":300.0,"theta":6.19591884457987,"z":16.0},
            {"r":300.0,"theta":1.2740903539558606,"z":172.0},
            {"r":300.0,"theta":0.8203047484373349,"z":197.0},
            {"r":300.0,"theta":5.654866776461628,"z":90.0},
            {"r":300.0,"theta":1.0297442586766543,"z":35.0},
            {"r":300.0,"theta":4.852015320544236,"z":118.0},
            {"r":300.0,"theta":1.902408884673819,"z":139.0}
        ]
    }


# ================== FIRING THREAD ==================
def fire_json():
    global current_az, current_el

    stop_event.clear()
    j = load_json()

    our_deg = math.degrees(j["turrets"][TEAM_ID]["theta"])

    with status_lock:
        status_lines.append(f"OUR TURRET: {our_deg:.1f}°")
        status_lines.append("---- TURRETS ----")

    for tid, t in j["turrets"].items():
        if tid == TEAM_ID or stop_event.is_set():
            continue

        tgt_deg = math.degrees(t["theta"])
        diff = abs(tgt_deg - our_deg) % 360
        az = (180 - diff) / 2

        with status_lock:
            status_lines.append(f"Turret {tid}: AZ {az:.1f}")

        led_off()
        m1.goAngle(az)
        current_az = az

        time.sleep(0.4)
        led_on()
        time.sleep(3)
        led_off()

    with status_lock:
        status_lines.append("---- GLOBES ----")

    for g in j["globes"]:
        if stop_event.is_set():
            break

        az = math.degrees(g["theta"])
        D = 2 * g["r"] * math.cos(math.radians(az))
        el = math.degrees(math.atan2(g["z"], D))

        with status_lock:
            status_lines.append(f"Globe: AZ {az:.1f} EL {el:.1f}")

        led_off()
        m1.goAngle(az)
        m2.goAngle(el)

        current_az = az
        current_el = el

        time.sleep(0.4)
        led_on()
        time.sleep(3)
        led_off()

    with status_lock:
        status_lines.append("DONE")


# ================== SERVER ==================
def serve():
    s = socket.socket()
    s.bind(("", 80))
    s.listen(3)

    global current_az, current_el

    while True:
        conn, _ = s.accept()
        msg = conn.recv(4096).decode()

        if "POST" in msg:
            if "fire" in msg:
                threading.Thread(target=fire_json, daemon=True).start()

            if "stop" in msg:
                stop_event.set()
                led_off()
                with status_lock:
                    status_lines.append("STOPPED")

            if "laser=on" in msg:
                led_on()

            if "laser=off" in msg:
                led_off()

            if "move" in msg:
                if "az=" in msg:
                    try:
                        az = float(msg.split("az=")[1].split("&")[0])
                        m1.goAngle(az)
                        current_az = az
                    except:
                        pass
                if "el=" in msg:
                    try:
                        el = float(msg.split("el=")[1].split("&")[0])
                        m2.goAngle(el)
                        current_el = el
                    except:
                        pass

            if "zero=az" in msg:
                m1.zero()
                current_az = 0.0

            if "zero=el" in msg:
                m2.zero()
                current_el = 0.0

        conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        conn.sendall(web_page())
        conn.close()


# ================== START ==================
print("Open http://<pi-ip>/")
serve()
