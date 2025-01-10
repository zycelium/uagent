from umqtt.robust import MQTTClient
import time
import json


class Logger:
    LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

    def __init__(self, name, level="INFO"):
        self.name = name
        level = level.upper()
        self.level = self.LEVELS.get(level, 20)

    def _log(self, level, msg, *args):
        if level >= self.level:
            if args:
                msg = msg % args
            print(f"{time.time():.3f} {self.name} [{level}] {msg}")

    def debug(self, msg, *args):
        self._log(10, msg, *args)

    def info(self, msg, *args):
        self._log(20, msg, *args)

    def warning(self, msg, *args):
        self._log(30, msg, *args)

    def error(self, msg, *args):
        self._log(40, msg, *args)

    def critical(self, msg, *args):
        self._log(50, msg, *args)


class Agent:
    def __init__(self, name, server="localhost", port=1883, log_level="INFO"):
        self.name = name
        self.server = server
        self.port = port
        self.client = None
        self.running = False
        self.log = Logger(name, level=log_level)

        # Handler storage
        self._start_handlers = []
        self._stop_handlers = []
        self._connect_handlers = []
        self._disconnect_handlers = []
        self._error_handlers = []
        self._event_handlers = {}  # topic -> [(handler, timeout), ...]
        self._interval_handlers = []  # [(func, interval, timeout, last_run), ...]
        self._translate_topics = True  # Enable topic translation by default

    def _to_mqtt_topic(self, topic):
        """Convert NATS-style topic to MQTT-style"""
        return topic.replace(".", "/") if self._translate_topics else topic

    def _from_mqtt_topic(self, topic):
        """Convert MQTT-style topic to NATS-style"""
        return topic.replace("/", ".") if self._translate_topics else topic

    def on_start(self, timeout=10):
        def decorator(func):
            self._start_handlers.append((func, timeout))
            return func

        return decorator

    def on_stop(self, timeout=10):
        def decorator(func):
            self._stop_handlers.append((func, timeout))
            return func

        return decorator

    def on_connect(self, timeout=10):
        def decorator(func):
            self._connect_handlers.append((func, timeout))
            return func

        return decorator

    def on_disconnect(self, timeout=10):
        def decorator(func):
            self._disconnect_handlers.append((func, timeout))
            return func

        return decorator

    def on_error(self, exc_type=None, message=None, timeout=10):
        def decorator(func):
            self._error_handlers.append((func, exc_type, message, timeout))
            return func

        return decorator

    def on_event(self, topic, timeout=10):
        def decorator(func):
            if topic not in self._event_handlers:
                self._event_handlers[topic] = []
            self._event_handlers[topic].append((func, timeout))
            if self.client:
                # Subscribe using MQTT style topic
                mqtt_topic = self._to_mqtt_topic(topic)
                self.log.debug("Subscribing to topic: %s (mqtt: %s)", topic, mqtt_topic)
                self.client.subscribe(mqtt_topic.encode())
            return func

        return decorator

    def on_interval(self, interval, timeout=None):
        """
        Execute handler every 'interval' seconds.
        If timeout is None, uses interval as timeout.
        """
        if timeout is None:
            timeout = interval

        def decorator(func):
            self._interval_handlers.append((func, interval, timeout, 0))
            return func

        return decorator

    def emit(self, topic, **kwargs):
        if not self.client:
            err = RuntimeError("Not connected to MQTT broker")
            self.log.error(str(err))
            self._handle_error(err)
            return
        try:
            mqtt_topic = self._to_mqtt_topic(topic)
            payload = json.dumps(kwargs).encode()
            self.log.debug("Emitting to %s (mqtt: %s): %s", topic, mqtt_topic, kwargs)
            self.client.publish(mqtt_topic.encode(), payload)
        except Exception as e:
            self.log.error("Failed to emit event: %s", str(e))
            self._handle_error(e)

    def _mqtt_callback(self, topic, msg):
        mqtt_topic = topic.decode()
        nats_topic = self._from_mqtt_topic(mqtt_topic)
        self.log.debug(
            "Received message on topic: %s (nats: %s)", mqtt_topic, nats_topic
        )
        try:
            payload = json.loads(msg.decode())
            self.log.debug("Decoded payload: %s", payload)
        except Exception as e:
            self.log.warning("Failed to decode payload: %s", str(e))
            payload = {}

        # Find matching topic handlers
        matched = False
        for pattern, handlers in self._event_handlers.items():
            self.log.debug("Checking pattern: %s", pattern)
            if self._topic_matches(pattern, nats_topic):
                matched = True
                self.log.debug("Pattern matched: %s", pattern)
                for handler, timeout in handlers:
                    try:
                        start_time = time.time()
                        self.log.debug("Calling handler: %s", handler.__name__)
                        handler(**payload)
                        if time.time() - start_time > timeout:
                            self.log.warning(
                                "Handler %s exceeded timeout", handler.__name__
                            )
                    except Exception as e:
                        self.log.error(
                            "Handler %s failed: %s", handler.__name__, str(e)
                        )
                        self._handle_error(e)

        if not matched:
            self.log.warning("No handlers matched topic: %s", nats_topic)

    def _topic_matches(self, pattern, topic):
        self.log.debug("Matching topic '%s' against pattern '%s'", topic, pattern)
        # Simple pattern matching supporting * and ** wildcards
        p_parts = pattern.split(".")
        t_parts = topic.split(".")

        if len(p_parts) > len(t_parts) and "**" not in p_parts:
            return False

        for p, t in zip(p_parts, t_parts):
            if p == "*":
                continue
            if p == "**":
                return True
            if p != t:
                return False
        return len(p_parts) == len(t_parts)

    def _execute_handlers(self, handlers, *args):
        for handler_tuple in handlers:
            handler = handler_tuple[0]  # Get the handler function
            timeout = handler_tuple[1]  # Get the timeout value
            try:
                start_time = time.time()
                handler(*args)  # Execute the handler with any additional args
                if time.time() - start_time > timeout:
                    self.log.warning(f"Handler {handler.__name__} exceeded timeout")
            except Exception as e:
                self._handle_error(e)

    def _handle_error(self, error):
        handled = False
        for handler, exc_type, message, timeout in self._error_handlers:
            if exc_type and not isinstance(error, exc_type):
                continue
            if message and str(error) != message:
                continue
            try:
                start_time = time.time()
                handler(error)
                if time.time() - start_time > timeout:
                    print(f"Error handler {handler.__name__} exceeded timeout")
                handled = True
            except Exception as e:
                print(f"Error in error handler: {e}")
        if not handled:
            print(f"Unhandled error: {error}")

    def _check_intervals(self):
        current_time = time.time()
        for i, (handler, interval, timeout, last_run) in enumerate(
            self._interval_handlers
        ):
            if current_time - last_run >= interval:
                try:
                    start_time = time.time()
                    handler()
                    if time.time() - start_time > timeout:
                        print(f"Interval handler {handler.__name__} exceeded timeout")
                except Exception as e:
                    self._handle_error(e)
                finally:
                    # Update last run time
                    self._interval_handlers[i] = (
                        handler,
                        interval,
                        timeout,
                        current_time,
                    )

    def connect(self):
        try:
            self.log.info("Connecting to MQTT broker %s:%s", self.server, self.port)
            self.client = MQTTClient(self.name, self.server, self.port)
            self.client.set_callback(self._mqtt_callback)
            self.client.connect()
            self.log.info("Connected successfully")

            # Subscribe to all event topics
            for topic in self._event_handlers:
                mqtt_topic = self._to_mqtt_topic(topic)
                self.log.debug("Subscribing to topic: %s (mqtt: %s)", topic, mqtt_topic)
                try:
                    self.client.subscribe(mqtt_topic.encode())
                    self.log.info("Subscribed to: %s", topic)
                except Exception as e:
                    self.log.error("Failed to subscribe to %s: %s", topic, str(e))

            self._execute_handlers(self._connect_handlers)
        except Exception as e:
            self.log.error("Connection failed: %s", str(e))
            self._handle_error(e)

    def disconnect(self):
        if self.client:
            try:
                self.log.info("Disconnecting from MQTT broker")
                self.client.disconnect()
                self._execute_handlers(self._disconnect_handlers)
            except Exception as e:
                self.log.error("Disconnect failed: %s", str(e))
                self._handle_error(e)

    def run(self):
        try:
            self.log.info("Starting agent")
            self.running = True
            self._execute_handlers(self._start_handlers)
            self.connect()

            while self.running:
                if self.client:
                    self.client.check_msg()
                self._check_intervals()
                time.sleep(0.1)

        except Exception as e:
            self.log.critical("Agent crashed: %s", str(e))
            self._handle_error(e)
        finally:
            self.log.info("Stopping agent")
            self._execute_handlers(self._stop_handlers)
            self.disconnect()

    def stop(self):
        self.running = False
