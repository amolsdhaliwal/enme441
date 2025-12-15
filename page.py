import socket
import threading
import json
import multiprocessing
import time
import math

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

# ---------------- HARDWARE SETUP ----------------
data = 16
clock = 20
latch = 21
sft = Shifter(data, clock, latch)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(sft, lock1)   # Azimuth
m2 = Stepper(sft, lock2)   # Elevation

TEAM_ID = "19"

# ---------------- GLOBAL STATE ----------------
stop_event = threading.Event()
status_lines = []
status_lock = threading.Lock()

current_az = 0.0
current_el = 0.0


# ---------------- WEB PAGE ----------------
def web_page():
    with status_lock:
        status_text = "\n".join(status_lines[-50:])

    led_txt = "ON" if led_state.value else "OFF"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Laser Turret Control</title>
        <style>
            body {{
                font-family: Arial;
                background: #111;
                color: #eee;
                padding: 20px;
            }}
            h1 {{ color: #00ffcc; }}
            button {{
                font-size: 18px;
                padding: 10px 20px;
                margin: 6px;
            }}
            .fire {{ background: #2ecc71; }}
            .stop {{ background: #e74c3c; color: white; }}
            pre {{
                background: #222;
                padding: 15px;
                border-radius: 6px;
                max-height: 400px;
                overflow-y: auto;
            }}
        </style>
    </head>

    <body>
        <h1>Laser Turret Control</h1>

        <p><b>Azimuth:</b> {current_az:.1f}°</p>
        <p><b>Elevation:</b> {current_el:.1f}°</p>
        <p><b>Laser:</b> {led_txt}</p>

        <form method="POST">
            <button class="fire" type="submit" name="fire" value="1">
                Load & Fire JSON
            </button>
            <button class="stop" type="submit" name="stop" value="1">
                STOP
            </button>
        </form>

        <h2>Status</h2>
        <pre>{status_text}</pre>
    </body>
    </html>
    """
    return html.encode()


# ---------------- JSON DATA ----------------
def load_json():
    return {
        "turrets": {
            "1": {"r": 300.0, "theta": 1.5882496193148399},
            "2": {"r": 300.0, "theta": 5.7246799465414},
            "3": {"r": 300.0, "theta": 4.572762640225144},
            "4": {"r": 300.0, "theta": 0.41887902047863906},
            "5": {"r": 300.0, "theta": 2.356194490192345},
            "6": {"r": 300.0, "theta": 0.6981317007977318},
            "7": {"r": 300.0, "theta": 5.794493116621174},
            "8": {"r": 300.0, "theta": 3.211405823669566},
            "9": {"r": 300.0, "theta": 5.8643062867009474},
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
            {"r": 300.0, "theta": 6.19591884457987, "z": 16.0},
            {"r": 300.0, "theta": 1.2740903539558606, "z": 172.0},
            {"r": 300.0, "theta": 0.8203047484373349, "z": 197.0},
            {"r": 300.0, "theta": 5.654866776461628, "z": 90.0},
            {"r": 300.0, "theta": 1.0297442586766543, "z": 35.0},
            {"r": 300.0, "theta": 4.852015320544236, "z": 118.0},
            {"r": 300.0, "theta": 1.902408884673819, "z": 139.0}
        ]
    }


# ---------------- FIRING LOGIC ----------------
def fire_json():
    global current_az, current_el

    stop_event.clear()
    j = load_json()
    our_theta = j["turrets"][TEAM_ID]["theta"]
    our_deg = math.degrees(our_theta)

    with status_lock:
        status_lines.append(f"OUR TURRET: {our_deg:.1f}°")
        status_lines.append("---- TURRETS ----")

    # --------- TURRETS ---------
    for tid, info in j["turrets"].items():
        if stop_event.is_set() or tid == TEAM_ID:
            break

        tgt_deg = math.degrees(info["theta"])
        diff = abs(tgt_deg - our_deg) % 360
        theta_rot = (180 - diff) / 2

        with status_lock:
            status_lines.append(f"Turret {tid}: AZ {theta_rot:.1f}°")

        led_off()
        m1.goAngle(theta_rot)
        current_az = theta_rot

        time.sleep(0.5)
        led_on()
        time.sleep(3)
        led_off()

    # --------- GLOBES ---------
    with status_lock:
        status_lines.append("---- GLOBES ----")

    for g in j["globes"]:
        if stop_event.is_set():
            break

        theta_rot = math.degrees(g["theta"])
        z = g["z"]
        r = g["r"]

        D = 2 * r * math.cos(math.radians(theta_rot))
        theta_z = math.degrees(math.atan2(z, D))

        with status_lock:
            status_lines.append(
                f"Globe: AZ {theta_rot:.1f}°, EL {theta_z:.1f}°"
            )

        led_off()
        m1.goAngle(theta_rot)
        m2.goAngle(theta_z)

        current_az = theta_rot
        current_el = theta_z

        time.sleep(0.5)
        led_on()
        time.sleep(3)
        led_off()

    with status_lock:
        status_lines.append("DONE")


# ---------------- SERVER ----------------
def serve():
    s = socket.socket()
    s.bind(("", 80))
    s.listen(3)

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

        conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        conn.sendall(web_page())
        conn.close()


# ---------------- START ----------------
print("Open: http://<pi-ip>/")
serve()
