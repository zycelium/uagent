from uagent import Agent
import os


class CommandAgent(Agent):
    def __init__(self, name="command", server="localhost", port=1883):
        super().__init__(name, server, port)
        self.commands = {}  # event_topic -> (command_str, reply_topic)
        self.log.info("CommandAgent initialized with name: %s", name)

    def register_command(self, event_topic, command, reply_topic=None):
        """Register a shell command to be executed when event_topic is received"""
        if reply_topic is None:
            reply_topic = f"{event_topic}.reply"
        self.commands[event_topic] = (command, reply_topic)
        self.log.info(
            "Registered command '%s' for event %s -> %s",
            command,
            event_topic,
            reply_topic,
        )

        @self.on_event(event_topic)
        def command_handler(**kwargs):
            cmd = command
            # Replace placeholders in command with event parameters
            for key, value in kwargs.items():
                cmd = cmd.replace(f"{{{key}}}", str(value))

            self.log.info("Executing command: %s", cmd)
            try:
                # Execute command using os.system
                temp_out = "/tmp/cmd.out"
                temp_err = "/tmp/cmd.err"
                self.log.debug("Running: %s >%s 2>%s", cmd, temp_out, temp_err)
                returncode = os.system(f"{cmd} >{temp_out} 2>{temp_err}")

                # Read output from temporary files
                stdout = stderr = ""
                try:
                    with open(temp_out, "r") as f:
                        stdout = f.read()
                except Exception as e:
                    self.log.warning("Failed to read stdout: %s", str(e))

                try:
                    with open(temp_err, "r") as f:
                        stderr = f.read()
                except Exception as e:
                    self.log.warning("Failed to read stderr: %s", str(e))

                # Clean up temp files
                try:
                    os.unlink(temp_out)
                    os.unlink(temp_err)
                except Exception as e:
                    self.log.warning("Failed to cleanup temp files: %s", str(e))

                self.log.debug("Command completed with code %d", returncode)
                if returncode != 0:
                    self.log.warning("Command failed with code %d", returncode)
                    if stderr:
                        self.log.warning("stderr: %s", stderr)

                # Emit reply with command output
                self.emit(
                    reply_topic,
                    command=cmd,
                    stdout=stdout,
                    stderr=stderr,
                    returncode=returncode,
                )
            except Exception as e:
                self.log.error("Command execution failed: %s", str(e))
                self.emit(reply_topic, command=cmd, error=str(e), returncode=-1)


def create_command_agent(commands, **kwargs):
    """Helper function to create and configure a command agent"""
    agent = CommandAgent(**kwargs)
    agent.log.info("Creating command agent with commands: %s", commands)
    for event_topic, command_spec in commands.items():
        if isinstance(command_spec, str):
            agent.register_command(event_topic, command_spec)
        else:
            agent.register_command(event_topic, *command_spec)
    return agent


# Example usage
if __name__ == "__main__":
    # Define commands to register using dot notation
    commands = {
        "system.uptime": "uptime",
        "system.disk": ("df -h", "system.disk.status"),
        "system.process": "ps {pid}",  # Uses parameter from event
    }

    # Create and run agent
    agent = create_command_agent(commands, name="system", server="localhost", port=1883)
    agent.run()
