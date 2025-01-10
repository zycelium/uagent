from uagent import Agent
import time

# Configuration
DASHBOARD_NAME = "ping-dashboard"
MQTT_SERVER = "localhost"
MQTT_PORT = 1883

# Track ping results from different agents
ping_status = {}  # Format: {agent: {host, status, timestamp, output/error}}

# Create dashboard agent
dashboard = Agent(name=DASHBOARD_NAME, server=MQTT_SERVER, port=MQTT_PORT)


def clear_screen():
    """Clear terminal and move cursor to top"""
    print("\033[2J\033[H")


def display_dashboard():
    """Display current ping status for all agents"""
    clear_screen()
    print("Ping Monitor Dashboard")
    print("=" * 50)
    print(f"Tracking {len(ping_status)} agents")
    print("-" * 50)

    current_time = time.time()
    for agent, data in sorted(ping_status.items()):
        age = current_time - data["timestamp"]
        status_color = "\033[92m" if data["status"] == "ok" else "\033[91m"  # Green/Red
        print(f"Agent: {agent}")
        print(f"Host: {data['host']}")
        print(f"Status: {status_color}{data['status']}\033[0m")
        print(f"Last update: {age:.1f} seconds ago")
        if data["status"] == "ok":
            # Show last few lines of ping output
            output_lines = data.get("output", "").splitlines()
            if output_lines:
                print("Latest results:")
                for line in output_lines[-3:]:  # Last 3 lines
                    print(f"  {line}")
        else:
            print(f"Error: {data.get('error', 'Unknown error')}")
        print("-" * 50)


@dashboard.on_start()
def startup():
    print("Ping Dashboard Starting...")
    print("Waiting for ping updates...")
    dashboard.emit("ping.discover")  # Request current status from all agents


@dashboard.on_event("ping.status")
def handle_ping_status(agent, host, status, **kwargs):
    """Handle incoming ping status updates"""
    ping_status[agent] = {
        "host": host,
        "status": status,
        "timestamp": time.time(),
        "output": kwargs.get("output", ""),
        "error": kwargs.get("error", ""),
    }
    display_dashboard()


@dashboard.on_interval(5)
def refresh_display():
    """Periodically refresh the display to update timestamps"""
    if ping_status:
        display_dashboard()


if __name__ == "__main__":
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        dashboard.stop()
