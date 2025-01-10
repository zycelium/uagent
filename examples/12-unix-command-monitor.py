from uagent import Agent
import time

# Configuration
MONITOR_NAME = "monitor"
SERVER_IP = "localhost"
SERVER_PORT = 1883
CHECK_INTERVAL = 10  # seconds

# Create monitor agent
monitor = Agent(name=MONITOR_NAME, server=SERVER_IP, port=SERVER_PORT)

# Store latest metrics
metrics = {"uptime": "unknown", "disk": "unknown"}


@monitor.on_start()
def startup():
    print("System Monitor Starting...")
    print("Watching system metrics every {} seconds".format(CHECK_INTERVAL))
    print("-" * 50)


@monitor.on_event("system.uptime.reply")
def handle_uptime(**kwargs):
    if kwargs.get("returncode") == 0:
        metrics["uptime"] = kwargs.get("stdout", "").strip()
        display_metrics()


@monitor.on_event("system.disk.status")
def handle_disk(**kwargs):
    if kwargs.get("returncode") == 0:
        metrics["disk"] = kwargs.get("stdout", "").strip()
        display_metrics()


def display_metrics():
    print("\033[2J\033[H")  # Clear screen and move to top
    print("System Monitor Status")
    print("-" * 50)
    print("Uptime:")
    print(metrics["uptime"])
    print("\nDisk Usage:")
    print(metrics["disk"])
    print("-" * 50)


@monitor.on_interval(CHECK_INTERVAL)
def check_metrics():
    # Request system metrics
    monitor.emit("system.uptime")
    monitor.emit("system.disk")


if __name__ == "__main__":
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
