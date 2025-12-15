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
# WEB PAGE
# -----------------------
def web_page(positions=""):
    html = """
    <html><head><title>Turret Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    html{font-family: Helvetica; text-align:center; margin:0px auto;}
    .button{background:#e7bd3b; color:white; padding:10px 25px;
            border:none; border-radius:4px; font-size:22px; margin:6px;}
    .button2{background:#4286f4;}
    input{font-size:20px; margin:4px;}
    pre{width:80%; margin:auto; text-align:left; border:1px solid #ccc; padding:10px;}
    </style></head><body>

    <h1>Laser Turret Control</h1>

    <h2>Set Azimuth & Elevation</h2>
    <form method="POST">
        <label>Azimuth (theta) (deg):
            <input type="number" name="theta" step="1">
        </label><br>
        <label>Elevation (z) (deg):
            <input type="number" name="z" step="1">
        </label><br><br>
        <button class="button" type="submit" name="move" value="1">Move</button>
    </form>

    <h2>Set Zero</h2>
    <form method="POST">
        <button class="button" type="submit" name="set_zero" value="az">Set Azimuth Zero</button>
        <button class="button" type="submit" name="set_zero" value="el">Set Elevation Zero</button>
    </form>

    <h2>LED</h2>
    <form method="POST">
        <button class="button button2" type="submit" name="led" value="toggle">
            Toggle LED
        </button>
    </form>

    <h2>positions.json</h2>
    <form method="POST">
        <button class="button" type="submit" name="get_positions" value="1">Load</button>
    </form>

    <pre>""" + positions + """</pre>

    </body></html>
    """
    return html.encode("utf-8")


def parsePOST(msg):
    d = {}
    idx = msg.find("\r\n\r\n")
    if idx == -1:
        return d
    body = msg[idx + 4:]
    pairs = body.split("&")
    for p in pairs:
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
            # MANUAL MOVE
            # -----------------------
            if "move" in data_post:
                if data_post.get("theta", "") != "":
                    m1.goAngle(float(data_post["theta"]))
                if data_post.get("z", "") != "":
                    m2.goAngle(float(data_post["z"]))

            # -----------------------
            # ZEROING
            # -----------------------
            if "set_zero" in data_post:
                if data_post["set_zero"] == "az":
                    m1.zero()
                elif data_post["set_zero"] == "el":
                    m2.zero()

            # -----------------------
            # LED TOGGLE
            # -----------------------
            if data_post.get("led") == "toggle":
                with led_state.get_lock():
                    if led_state.value == 0:
                        led_on()
                    else:
                        led_off()

            # -----------------------
            # LOAD POSITIONS
            # -----------------------
            if "get_positions" in data_post:
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

                    turrets = j["turrets"]
                    our_theta_deg = round(math.degrees(turrets[TEAM_ID]["theta"]))

                    result = [f"Our turret angle: {our_theta_deg}°\n"]

                    for tid, info in turrets.items():
                        if tid == TEAM_ID:
                            continue

                        target_theta_deg = round(math.degrees(info["theta"]))
                        diff = abs(target_theta_deg - our_theta_deg) % 360
                        theta_rot = round((180 - diff) / 2)

                        r = info["r"]
                        z = info.get("z", 0)

                        D = 2 * r * math.cos(math.radians(theta_rot))
                        theta_z = math.degrees(math.atan(z / D)) if D > 0 else 0

                        # ---- MOTION + LASER ----
                        led_off()
                        m1.goAngle(theta_rot)
                        m2.goAngle(theta_z)

                        time.sleep(0.5)
                        led_on()
                        time.sleep(3)
                        led_off()

                        result.append(
                            f"Turret {tid}: rot={theta_rot}°, elev={round(theta_z,2)}°"
                        )

                    positions_text = "\n".join(result)

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
