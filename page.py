import socket
import threading
import json
import multiprocessing
import time

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter

data = 16
clock = 20
latch = 21
s = Shifter(data, clock, latch)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(s, lock1)    # Azimuth
m2 = Stepper(s, lock2)    # Elevation

TEAM_ID = "19"


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


def serve_web_page():
    while True:
        conn, addr = s.accept()
        msg = conn.recv(4096).decode("utf-8")

        positions_text = ""

        if "POST" in msg:
            data_post = parsePOST(msg)

            if "move" in data_post:
                if "theta" in data_post and data_post["theta"] != "":
                    try:
                        theta_target = float(data_post["theta"])
                        m1.goAngle(theta_target)
                    except Exception as e:
                        print("AZ move error:", e)

                if "z" in data_post and data_post["z"] != "":
                    try:
                        z_target = float(data_post["z"])
                        m2.goAngle(z_target)
                    except Exception as e:
                        print("EL move error:", e)

            if "set_zero" in data_post:
                if data_post["set_zero"] == "az":
                    m1.zero()
                    print("Azimuth zero set")
                elif data_post["set_zero"] == "el":
                    m2.zero()
                    print("Elevation zero set")

            if "led" in data_post and data_post["led"] == "toggle":
                with led_state.get_lock():
                    if led_state.value == 0:
                        led_on()
                    else:
                        led_off()

            # -------------------------
            # LOAD POSITIONS + ROTATE
            # -------------------------
            if "get_positions" in data_post:
                try:
                    # ---- LOCAL JSON ----
                    j = {
                        "turrets": {
                            "1": {"r": 300.0, "theta": 1.5882496193148399},
                            "2": {"r": 300.0, "theta": 5.7246799465414},
                            "3": {"r": 300.0, "theta": 4.572762640225144},
                            "4": {"r": 300.0, "theta": 0.41887902047863906},
                            "5": {"r": 300.0, "theta": 2.356194490192345},  # unique
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

                    if TEAM_ID not in turrets:
                        positions_text = f"Error: TEAM_ID {TEAM_ID} not in positions file."
                    else:
                        our_theta_rad = turrets[TEAM_ID]["theta"]
                        our_theta_deg = round(our_theta_rad * 180.0 / 3.1415926535)

                        result_lines = []
                        result_lines.append(f"Our turret angle (deg): {our_theta_deg}\n")
                        result_lines.append("Computed target angles:\n")

                        # ---- TARGET PROCESSING ----
                        for tid, info in turrets.items():
                            if tid == TEAM_ID:
                                continue

                            target_theta_rad = info["theta"]
                            target_theta_deg = round(target_theta_rad * 180.0 / 3.1415926535)

                            diff = abs(target_theta_deg - our_theta_deg) % 360
                            theta_rot = round((180 - diff) / 2)

                            result_lines.append(
                                f"Turret {tid}: abs={target_theta_deg}°, diff={diff}°, rotate={theta_rot}°"
                            )

                            # ---- AUTOMATIC ROTATION + LASER 3 SEC ----
                            try:
                                # Laser OFF during movement
                                led_off()

                                # Rotate
                                m1.goAngle(theta_rot)

                                # Short pause to ensure movement completes
                                time.sleep(0.5)

                                # Laser ON for 3 sec
                                led_on()
                                time.sleep(3)

                                # Laser OFF before next target
                                led_off()

                            except Exception as e:
                                print("Rotation/laser error:", e)

                        positions_text = "\n".join(result_lines)

                except Exception as e:
                    positions_text = "Error loading file: " + str(e)

        # Respond safely
        try:
            conn.send(b"HTTP/1.1 200 OK\r\n")
            conn.send(b"Content-Type: text/html\r\n")
            conn.send(b"Connection: close\r\n\r\n")
            conn.sendall(web_page(positions_text))
        except BrokenPipeError:
            print("Client disconnected before response was sent")
        finally:
            try:
                conn.close()
            except:
                pass


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 80))
s.listen(3)

t = threading.Thread(target=serve_web_page)
t.daemon = True
t.start()

print("Open page at:  http://<your_pi_ip>/")

while True:
    pass
