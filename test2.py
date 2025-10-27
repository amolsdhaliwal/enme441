import RPi.GPIO as gpio
import threading
import socket

# --------------------------
# Raspberry Pi GPIO Setup
# --------------------------
gpio.setmode(gpio.BCM)

# Assign LED pins
led_pins = {
    "led1": 14,
    "led2": 15,
    "led3": 18
}

# Set pins as outputs
for pin in led_pins.values():
    gpio.setup(pin, gpio.OUT)

# Create PWM objects at 1 kHz
pwms = {
    "led1": gpio.PWM(led_pins["led1"], 1000),
    "led2": gpio.PWM(led_pins["led2"], 1000),
    "led3": gpio.PWM(led_pins["led3"], 1000)
}

# Start all PWM at 0% brightness
for pwm in pwms.values():
    pwm.start(0)

# Store brightness states
brightness = {
    "led1": 0,
    "led2": 0,
    "led3": 0
}

# --------------------------
# HTML Page (HTML + JS sliders)
# --------------------------
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

# --------------------------
# Parse POST Form Data
# --------------------------
def parsePOSTdata(data):
    data_dict = {}
    idx = data
