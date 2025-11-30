import multiprocessing

def start_server():
    import socket
    import threading
    import requests
    import json
    import time

    from mult import Stepper, led_on, led_off, led_state
    from shifter import Shifter

    # === Hardware Setup ===
    dataPin, latchPin, clockPin = 16, 21, 20
    sh = Shifter(dataPin, latchPin, clockPin)

    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    m1 = Stepper(sh, lock1)  # azimuth
    m2 = Stepper(sh, lock2)  # elevation

    POSITIONS_URL = "http://192.168.1.254:8000/positions.json"
    TEAM_ID = "1"

    # === HTML PAGE ===
    def web_page(az, el, led, positions_text=""):
        html = """
        <html><head><title>Turret Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        </head><body>

        <h1>Turret Control</h1>

        <p>Azimuth: <b>""" + str(az) + """°</b></p>
        <p>Elevation: <b>""" + str(el) + """°</b></p>
        <p>LED State: <b>""" + ("ON" if led else "OFF") + """</b></p>

        <h2>Move Azimuth</h2>
        <form action="/" method="POST">
            <input type="hidden" name="motor" value="az">
            <input type="number" name="angle">
            <button type="submit">Move</button>
        </form>

        <h2>Move Elevation</h2>
        <form action="/" method="POST">
            <input type="hidden" name="motor" value="el">
            <input type="number" name="angle">
            <button type="submit">Move</button>
        </form>

        <h2>LED</h2>
        <form action="/" method="POST">
            <button type="submit" name="led" value="toggle">Toggle LED</button>
        </form>

        <h2>Positions.json</h2>
        <form action="/" method="POST">
            <button type="submit" name="get_positions" value="1">Load</button>
        </form>

        <pre>""" + positions_text + """</pre>

        </body></html>
        """
        return html.encode()

    # Parse POST
    def parsePOSTdata(msg):
        out = {}
        idx = msg.find("\r\n\r\n") + 4
        body = msg[idx:]
        for pair in body.split("&"):
            if "=" in pair:
                k, v = pair.split("=")
                out[k] = v
        return out

    # Web server thread
    def serve_web_page():
        while True:
            conn, addr = s.accept()
            msg = conn.recv(4096).decode()
            data = parsePOSTdata(msg)
            positions_text = ""

            # === Motor movement ===
            if "motor" in data and "angle" in data:
                angle = float(data["angle"])
                if data["motor"] == "az":
                    m1.goAngle(angle)
                else:
                    m2.goAngle(angle)

            # === LED toggle ===
            if "led" in data:
                with led_state.get_lock():
                    if led_state.value == 0:
                        led_on()
                    else:
                        led_off()

            # === JSON load ===
            if "get_positions" in data:
                try:
                    j = requests.get(POSITIONS_URL).json()
                    my = j["turrets"].get(TEAM_ID, "Not found")
                    positions_text = json.dumps(my, indent=2)
                except:
                    positions_text = "Error loading positions."

            # Updated values
            az = round(m1.angle.value, 2)
            el = round(m2.angle.value, 2)
            led = led_state.value

            conn.send(b"HTTP/1.1 200 OK\r\n")
            conn.send(b"Content-Type: text/html\r\n\r\n")
            conn.sendall(web_page(az, el, led, positions_text))
            conn.close()

    # Start socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 8080))       # <-- use 8080 to avoid permission denied
    s.listen(3)

    threading.Thread(target=serve_web_page, daemon=True).start()
    print("Web server running on port 8080...")

    while True:
        time.sleep(1)


# === REQUIRED MULTIPROCESSING STARTUP ===
if __name__ == "__main__":
    multiprocessing.set_start_method("fork")
    start_server()
