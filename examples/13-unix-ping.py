from uagent import Agent
import os
import time

# Configuration
AGENT_NAME = "ping-monitor"
HOST_TO_PING = "google.com"
MQTT_SERVER = "localhost"
MQTT_PORT = 1883
LOG_LEVEL = "INFO"

# Create ping monitoring agent
agent = Agent(name=AGENT_NAME, server=MQTT_SERVER, port=MQTT_PORT, log_level=LOG_LEVEL)


@agent.on_start()
def startup():
    print("Ping monitor starting up...")
    time.sleep(1)  # Brief startup delay


@agent.on_interval(20)  # Run every 60 seconds
def check_ping():
    """Execute ping and emit results"""
    cmd = f"ping -c 4 -W 10 {HOST_TO_PING}"
    print(f"Pinging {HOST_TO_PING}...")

    # Execute ping command
    returncode = os.system(f"{cmd} >/tmp/ping.out 2>/dev/null")

    try:
        with open("/tmp/ping.out", "r") as f:
            output = f.read()

        # Emit results
        if returncode == 0:
            agent.emit(
                "ping.status",
                agent=AGENT_NAME,
                host=HOST_TO_PING,
                status="ok",
                output=output,
            )
        else:
            agent.emit(
                "ping.status",
                agent=AGENT_NAME,
                host=HOST_TO_PING,
                status="error",
                error="Host unreachable",
            )
    except Exception as e:
        agent.emit(
            "ping.status",
            agent=AGENT_NAME,
            host=HOST_TO_PING,
            status="error",
            error=str(e),
        )
    finally:
        try:
            os.unlink("/tmp/ping.out")
        except:
            pass


if __name__ == "__main__":
    try:
        print(f"Starting ping monitor for {HOST_TO_PING}")
        agent.run()
    except KeyboardInterrupt:
        print("Stopping ping monitor...")
        agent.stop()
