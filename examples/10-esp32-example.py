from uagent import Agent
import network
import time

AGENT_NAME = "example"
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


# Create an agent named 'example'
agent = Agent(name=AGENT_NAME, server=SERVER_IP, port=SERVER_PORT, log_level=LOG_LEVEL)

counter = 0


@agent.on_start(timeout=5)
def startup():
    print("Agent is starting up...")
    try:
        connect_wifi()  # Ensure WiFi is connected before proceeding
    except Exception as e:
        print(f"WiFi setup failed: {e}")
        agent.stop()
        return
    # Simulate some startup work
    time.sleep(1)


@agent.on_connect(timeout=5)
def handle_connect():
    print("Connected to MQTT broker")
    # Simulate connection setup
    time.sleep(0.5)


@agent.on_disconnect(timeout=5)
def handle_disconnect():
    print("Disconnected from MQTT broker")


@agent.on_error(OSError)
def handle_network_error(error):
    print(f"Network error occurred: {error}")


@agent.on_error()
def handle_general_error(error):
    print(f"General error occurred: {error}")


@agent.on_stop(timeout=5)
def shutdown():
    print("Agent is shutting down...")
    # Simulate cleanup work
    time.sleep(1)


@agent.on_event("greet")
def greet_the_world():
    print("Hello, World!")
    agent.stop()


@agent.on_interval(2)  # Every 2 seconds
def count_up():
    global counter
    counter += 1
    print(f"Counter: {counter}")
    if counter >= 5:
        agent.stop()


@agent.on_interval(5, timeout=1)  # Every 5 seconds, with 1 second timeout
def slow_task():
    print("Performing slow task...")
    time.sleep(0.5)  # Simulate work
    print("Slow task done")


if __name__ == "__main__":
    try:
        print("Starting agent example...")
        agent.run()
    except KeyboardInterrupt:
        print("Stopping agent...")
        agent.stop()
