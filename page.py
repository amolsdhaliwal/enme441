import socket
import threading
import json
import multiprocessing
import time
import math

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

# -----------------------
# HARDWARE SETUP
# -----------------------
data = 16
clock = 20
latch = 21
s = Shifter(data, clock, latch)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(s, lock1)    # Azimuth
m2 = Stepper(s, lock2)    # Elevation

TEAM_ID = "19"

# -----------------------
# GLOBAL STOP FLAG
# -----------------------
stop_fire = multiprocessing.Value('i', 0)

# -----------------------
# WEB PAGE
# -----------------------
def web_page(positions=""):
    html = f"""
    <html><head><title>Turret Control</title></head><body>
    <h1>Laser Turret Control</h1>

    <form method="POST">
        <button type="submit" name="get_positions" value="1">Load</button>
        <button type="submit" name="stop" value="1"
            style="background:red;color:white;margin-left:10px;">
            STOP
        </button>
    </form>

    <pre>{positions}</pre>
    </body></html>
    """
    return html.encode("utf-8")


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


# -----------------------
# MAIN SERVER LOOP
# -----------------------
def serve_web_page():
    while True:
        conn, addr = s.accept()
        msg = conn.recv(4096).decode("utf-8")
        positions_text = ""

        if "POST" in msg:
            data_post = parsePOST(msg)

            # -----------------------
            # STOP BUTTON
            # -----------------------
            if "stop" in data_post:
                stop_fire.value = 1
                with led_state.get_lock():
                    led_off()
                positions_text = "STOPPED firing sequence."

            # -----------------------
            # LOAD & FIRE
            # -----------------------
            if "get_positions" in data_post:
                stop_fire.value = 0

                try:
                    j = {
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

                    our_theta_deg = math.degrees(j["turrets"][TEAM_ID]["theta"])
                    lines = [f"Our turret angle: {round(our_theta_deg,2)}°\n"]

                    # =============================
                    # TURRETS
                    # =============================
                    lines.append("=== TURRET TARGETS ===")

                    for tid, t in j["turrets"].items():
                        if tid == TEAM_ID or stop_fire.value:
                            break

                        target_theta_deg = math.degrees(t["theta"])
                        diff = abs(target_theta_deg - our_theta_deg) % 360
                        theta_rot = (180 - diff) / 2

                        with led_state.get_lock():
                            led_off()

                        m1.goAngle(theta_rot)
                        m2.goAngle(0)

                        time.sleep(0.5)

                        with led_state.get_lock():
                            led_on()
                        time.sleep(3)
                        with led_state.get_lock():
                            led_off()

                        lines.append(f"Turret {tid}: az={round(theta_rot,2)}°, el=0°")

                    # =============================
                    # GLOBES
                    # =============================
                    lines.append("\n=== GLOBE TARGETS ===")

                    for i, g in enumerate(j["globes"], start=1):
                        if stop_fire.value:
                            break

                        target_theta_deg = math.degrees(g["theta"])
                        diff = abs(target_theta_deg - our_theta_deg) % 360
                        theta_rot = (180 - diff) / 2

                        r = g["r"]
                        z = g["z"]
                        D = 2 * r * math.cos(math.radians(theta_rot))
                        theta_z = math.degrees(math.atan(z / D)) if D > 0 else 0

                        with led_state.get_lock():
                            led_off()

                        m1.goAngle(theta_rot)
                        m2.goAngle(theta_z)

                        time.sleep(0.5)

                        with led_state.get_lock():
                            led_on()
                        time.sleep(3)
                        with led_state.get_lock():
                            led_off()

                        lines.append(
                            f"Globe {i}: az={round(theta_rot,2)}°, el={round(theta_z,2)}°"
                        )

                    positions_text = "\n".join(lines)

                except Exception as e:
                    positions_text = f"Error: {e}"

        conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        conn.sendall(web_page(positions_text))
        conn.close()


# -----------------------
# START SERVER
# -----------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 80))
s.listen(3)

t = threading.Thread(target=serve_web_page)
t.daemon = True
t.start()

print("Open page at: http://<your_pi_ip>/")

while True:
    pass
