# uAgent

A lightweight implementation of Zycelium Agent in MicroPython.

## Installation

1. Install MicroPython on your device
2. Copy `uagent.py` to your device
3. `import uagent` in your code and create a Zycelium Agent

## Example: ESP32 / LED Toggle

```python
import network
import time
from machine import Pin

from uagent import Agent

# Configuration
AGENT_NAME = "example"
LED_PIN = 2
WIFI_SSID = "WIFI-SSID"
WIFI_PASSWORD = "WIFI-PASSWORD"
SERVER_IP = "192.168.0.100"
SERVER_PORT = 1883
LOG_LEVEL = "INFO"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        # Wait for connection with timeout
        max_wait = 10
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            time.sleep(1)
        if wlan.isconnected():
            print("WiFi connected")
            print("Network config:", wlan.ifconfig())
        else:
            print("WiFi connection failed")
            raise OSError("WiFi connection failed")
    return wlan


agent = Agent(name=AGENT_NAME, server=SERVER_IP, port=SERVER_PORT, log_level=LOG_LEVEL)


@agent.on_start(timeout=10)
def startup():
    try:
        global led
        led = Pin(LED_PIN, Pin.OUT)  # Configure LED pin as output
        connect_wifi()  # Ensure WiFi is connected before proceeding
    except Exception as e:
        print(f"WiFi setup failed: {e}")
        agent.stop()
        return


@agent.on_event("led.toggle")
def toggle_led():
    led.value(not led.value())  # Toggle LED state
    print(f"LED state changed to: {led.value()}")
    agent.emit("led.state", state=led.value())


if __name__ == "__main__":
    try:
        print(f"Starting agent {AGENT_NAME}")
        agent.run()
    except KeyboardInterrupt:
        print("Stopping agent...")
        agent.stop()
```
