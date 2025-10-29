import RPi.GPIO as gpio
import threading
import socket

gpio.setmode(gpio.BCM)

pins = {
    "led1": 14,
    "led2": 15,
    "led3": 18
}

for pin in pins.values():
    gpio.setup(pin, gpio.OUT)

pwms = {led: gpio.PWM(pin, 500) for led, pin in pins.items()}


for pwm in pwms.values():
    pwm.start(0)

brightness = {
    "led1": 0,
    "led2": 0,
    "led3": 0
}

def web_page():
    html = """
    <html>
    <head>
      <title>LED Brightness Control</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {{ font-family: Helvetica, Arial, sans-serif; margin: 20px; }}
        .row {{ display: flex; align-items: center; gap: 14px; margin: 14px 0; }}
        .label {{ width: 60px; font-weight: 600; }}
        .slider {{ flex: 1; }}
        .value {{ width: 40px; text-align: right; }}
        .card {{ max-width: 420px; border: 2px solid #333; border-radius: 8px; padding: 14px; }}
        h1 {{ font-size: 20px; margin: 0 0 10px 0; color: #0F3376; }}
      </style>
    </head>
    <body>
      <div class="card">
        <h1>LED Sliders</h1>

        <div class="row">
          <div class="label">LED1</div>
          <input class="slider" type="range" id="led1" min="0" max="100" value="{0}">
          <div class="value" id="val-led1">{0}</div>
        </div>

        <div class="row">
          <div class="label">LED2</div>
          <input class="slider" type="range" id="led2" min="0" max="100" value="{1}">
          <div class="value" id="val-led2">{1}</div>
        </div>

        <div class="row">
          <div class="label">LED3</div>
          <input class="slider" type="range" id="led3" min="0" max="100" value="{2}">
          <div class="value" id="val-led3">{2}</div>
        </div>
      </div>

      <script>
        function clamp01(x) {{
          x = parseInt(x) || 0;
          if (x < 0) x = 0;
          if (x > 100) x = 100;
          return x;
        }}

        function sendUpdate(led, value) {{
          const body = "led=" + encodeURIComponent(led) + "&brightness=" + encodeURIComponent(value);
          fetch("/", {{
            method: "POST",
            headers: {{
              "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }},
            body
          }}).catch(() => {{}});
        }}

        function wire(ledId) {{
          const slider = document.getElementById(ledId);
          const out = document.getElementById("val-" + ledId);
          const apply = () => {{
            const v = clamp01(slider.value);
            out.textContent = v;
            sendUpdate(ledId, v);
          }};
          slider.addEventListener("input", apply);
          out.textContent = clamp01(slider.value);
        }}

        ["led1","led2","led3"].forEach(wire);
      </script>
    </body>
    </html>
    """.format(brightness["led1"], brightness["led2"], brightness["led3"])

    return bytes(html, 'utf-8')


def parsePOSTdata(data):
    data_dict = {}
    idx = data.find('\r\n\r\n')+4
    data = data[idx:]
    data_pairs = data.split('&')
    for pair in data_pairs:
        key_val = pair.split('=')
        if len(key_val) == 2:
            data_dict[key_val[0]] = key_val[1]
    return data_dict

def serve_web_page():
    while True:
        print("Waiting for connection...")
        conn, (client_ip, client_port) = s.accept()
        print(f"Connected: {client_ip}:{client_port}")
        client_message = conn.recv(2048).decode('utf-8')
        print(f"Message:\n{client_message}")
        data_dict = parsePOSTdata(client_message)
        if "led" in data_dict.keys():
            selected = data_dict["led"]
            try:
                output = int(data_dict.get("brightness", "0"))
            except ValueError:
                output = 0
            output = max(0, min(100, output))
            brightness[selected] = output
            pwms[selected].ChangeDutyCycle(output)

        conn.send(b'HTTP/1.1 200 OK\r\n')
        conn.send(b'Content-Type: text/html\r\n')
        conn.send(b'Connection: close\r\n\r\n')
        try:
            conn.sendall(web_page())
        except BrokenPipeError:
            pass
        finally:
            conn.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(3)
webpageTread = threading.Thread(target=serve_web_page)
webpageTread.daemon = True
webpageTread.start()


try:
    while True:
        pass
except KeyboardInterrupt:
    pass
finally:
    print('Joining webpageTread')
    webpageTread.join()
    s.close()
    print("Shutting down...")
    for pwm in pwms.values():
        pwm.stop()
    gpio.cleanup()
