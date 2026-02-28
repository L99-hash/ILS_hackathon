#!/usr/bin/env python3
"""
Example: Trigger camera capture from external system

This shows how any external system can trigger a camera capture:
- HTTP API endpoint
- IoT sensor
- PLC signal
- Manual script
- etc.
"""

from src.monitoring.camera import SimpleLineMonitor
import time

# Example 1: Direct trigger (if you have access to the monitor object)
def example_direct_trigger():
    """
    If you have direct access to the monitor object,
    you can trigger a capture directly
    """
    monitor = SimpleLineMonitor(camera_index=0)

    # This adds a capture request to the queue
    monitor.trigger_capture(reason="api")
    # or
    monitor.trigger_capture(reason="sensor")
    # or
    monitor.trigger_capture(reason="plc_signal")

    # The next time monitor_phase() checks triggers, it will capture and save


# Example 2: HTTP API endpoint (Flask)
def example_http_api():
    """
    You can create an HTTP API that triggers captures
    This allows ANY system to send HTTP requests to capture images
    """
    from flask import Flask, jsonify

    app = Flask(__name__)

    # Global monitor instance (set when monitoring starts)
    monitor_instance = None

    @app.route('/api/capture', methods=['POST'])
    def trigger_capture():
        """
        POST http://localhost:5000/api/capture
        Body: {"reason": "manual", "phase": "SMT"}
        """
        if monitor_instance:
            reason = request.json.get('reason', 'api')
            monitor_instance.trigger_capture(reason=reason)
            return jsonify({
                "status": "success",
                "message": f"Capture triggered: {reason}"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Monitoring not active"
            }), 503

    @app.route('/api/status', methods=['GET'])
    def get_status():
        """GET http://localhost:5000/api/status"""
        return jsonify({
            "monitoring": monitor_instance is not None,
            "camera": monitor_instance.camera_index if monitor_instance else None
        })

    # Start API server
    # app.run(host='0.0.0.0', port=5000)


# Example 3: File-based trigger (simple polling)
def example_file_trigger(monitor):
    """
    Watch for a trigger file - when it appears, capture an image
    This is useful for simple systems that can just create a file
    """
    import os

    trigger_file = "/tmp/capture_trigger"

    while True:
        if os.path.exists(trigger_file):
            # Read reason from file content (optional)
            try:
                with open(trigger_file, 'r') as f:
                    reason = f.read().strip() or "file_trigger"
            except:
                reason = "file_trigger"

            # Trigger capture
            monitor.trigger_capture(reason=reason)

            # Remove trigger file
            os.remove(trigger_file)

            print(f"Captured from file trigger: {reason}")

        time.sleep(0.5)  # Check every 500ms


# Example 4: Telegram command (already built-in!)
"""
The monitor already listens for Telegram commands.
Just send "CAPTURE" to your Telegram bot and it will:
1. Take a photo immediately
2. Save it with reason="telegram"
3. Send the image back to you via Telegram

No additional code needed!
"""


# Example 5: GPIO/Hardware trigger (Raspberry Pi)
def example_gpio_trigger(monitor):
    """
    Trigger capture when a GPIO pin goes HIGH
    Useful for physical buttons or sensor signals
    """
    try:
        import RPi.GPIO as GPIO

        # Setup GPIO
        BUTTON_PIN = 17
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        print("Waiting for button press...")

        while True:
            # Wait for button press
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)

            # Trigger capture
            monitor.trigger_capture(reason="button")
            print("Button pressed - capture triggered!")

            # Debounce
            time.sleep(0.3)

    except ImportError:
        print("RPi.GPIO not available (not on Raspberry Pi)")


# Example 6: MQTT trigger (IoT integration)
def example_mqtt_trigger(monitor):
    """
    Subscribe to MQTT topic and trigger on messages
    Useful for IoT sensor networks
    """
    try:
        import paho.mqtt.client as mqtt

        def on_message(client, userdata, msg):
            reason = msg.payload.decode() or "mqtt"
            monitor.trigger_capture(reason=reason)
            print(f"MQTT trigger: {reason}")

        client = mqtt.Client()
        client.on_message = on_message
        client.connect("mqtt.example.com", 1883, 60)
        client.subscribe("factory/camera/capture")
        client.loop_forever()

    except ImportError:
        print("paho-mqtt not installed")


if __name__ == "__main__":
    print("=" * 60)
    print("Camera Trigger Examples")
    print("=" * 60)
    print()
    print("This file shows various ways to trigger camera captures:")
    print()
    print("1. Direct trigger - monitor.trigger_capture(reason='api')")
    print("2. HTTP API - POST /api/capture")
    print("3. File-based - touch /tmp/capture_trigger")
    print("4. Telegram - send 'CAPTURE' message (built-in!)")
    print("5. GPIO/Button - physical button press")
    print("6. MQTT - IoT sensor message")
    print()
    print("For Telegram control, it's already built in!")
    print("Just run main.py and send 'CAPTURE' via Telegram.")
    print()
