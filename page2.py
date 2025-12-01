import socket
import threading
import requests
import json
import multiprocessing

from mult import Stepper, led_on, led_off, led_state
from shifter import Shifter


### --- Hardware Setup --- ###
DATA = 16
CLOCK = 20
LATCH = 21
sh = Shifter(DATA, CLOCK, LATCH)

lock1 = multiprocessing.Lock()
lock2 = multiprocessing.Lock()

m1 = Stepper(sh, lock1)    # Azimuth
m2 = Stepper(sh, lock2)    # Elevation

POSITIONS_URL = "http://192.168.1.254:8000/positions.json"
TEAM_ID = "1"


### --- HTML Page --- ###
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
        <label>Azimuth (deg):
            <input type="number" name="az_angle" step="1">
        </label><br>
        <label>Elevation (deg):
            <input type="number" name="el_angle" step="1">
        </label><br><br>
        <button class="button" type="submit" name="move_both" value="1">Move Both</button>
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


### --- POST Parsing --- ###
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


### --- Server Logic --- ###
def serve_web_page():
    while True:
        conn, addr = s.accept()
        msg = conn.recv(4096).decode("utf-8")

        positions_text = ""

        if "POST" in msg:
            data = parsePOST(msg)

            # Move both angles (if requested)
            if "move_both" in data:
                # Azimuth
                if "az_angle" in data and data["az_angle"] != "":
                    try:
                        az_target = float(data["az_angle"])
                        m1.goAngle(az_target)
                    except Exception as e:
                        print("AZ move error:", e)

                # Elevation
                if "el_angle" in data and data["el_angle"] != "":
                    try:
                        el_target = float(data["el_angle"])
                        m2.goAngle(el_target)
                    except Exception as e:
                        print("EL move error:", e)

            # Set zero for a motor
            if "set_zero" in data:
                if data["set_zero"] == "az":
                    m1.zero()
                    print("Azimuth zero set")
                elif data["set_zero"] == "el":
                    m2.zero()
                    print("Elevation zero set")

            # LED toggle
            if "led" in data and data["led"] == "toggle":
                with led_state.get_lock():
                    if led_state.value == 0:
                        led_on()
                    else:
                        led_off()

            # Read positions.json
            if "get_positions" in data:
                try:
                    #r = requests.get(POSITIONS_URL, timeout=2)
                    #j = r.json()
                    # Mock JSON response
                    j = {
                        "turrets": {
                            "1": {"r": 300.0, "theta": 2.580},
                            "2": {"r": 300.0, "theta": 0.661},
                            "3": {"r": 300.0, "theta": 5.152}
                        },
                        "globes": [
                            {"r": 300.0, "theta": 1.015, "z": 20.4},
                            {"r": 300.0, "theta": 4.512, "z": 32.0},
                            {"r": 300.0, "theta": 3.979, "z": 10.8}
                        ]
                    }


                    mine = j["turrets"].get(TEAM_ID, "Not found")
                    positions_text = json.dumps(mine, indent=2)
                except Exception as e:
                    positions_text = "Error loading file: " + str(e)

        # Respond (with BrokenPipe protection)
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


### --- Start Web Server --- ###
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 8080))   # Change to 80 if needed
s.listen(3)

t = threading.Thread(target=serve_web_page)
t.daemon = True
t.start()

print("Open page at:  http://<your_pi_ip>:8080")

while True:
    pass
