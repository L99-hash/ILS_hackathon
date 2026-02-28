# Camera Capture Triggers - Complete Guide

## Overview

The monitoring system now supports **multiple ways to trigger camera captures**:

1. **Automatic** - Every 10 seconds (configurable)
2. **Telegram** - Send "CAPTURE" command
3. **External API** - For other systems to integrate later
4. **Keyboard** - Press 's' in camera window (existing)

## How It Works

```
┌─────────────────┐
│  Trigger Source │
│  (Telegram,     │
│   API, etc.)    │
└────────┬────────┘
         │
         ▼
   trigger_capture(reason="telegram")
         │
         ▼
  ┌──────────────────┐
  │  Trigger Queue   │
  └──────────────────┘
         │
         ▼
  Monitor loop checks queue
         │
         ▼
  ┌──────────────────┐
  │  Capture Frame   │
  │  Save to disk    │
  │  Send to Telegram│
  └──────────────────┘
```

## 1. Telegram Control (Built-in!)

### Setup

Already configured if you completed Step 5! Uses same Telegram bot.

### Usage

1. **Start monitoring** (via main.py Step 6)
2. **Open Telegram** and find your bot
3. **Send one of these commands**:
   - `CAPTURE`
   - `PHOTO`
   - `SNAP`

4. **Instant response**:
   ```
   Terminal:
   📱 Telegram: Capture request received
   📸 Capture triggered by telegram: monitoring_frames/order_Phase1_20260228_181755_telegram.jpg
      ✓ Image sent to Telegram

   Telegram:
   [You receive the image with caption]
   Phase: SMT
   Reason: telegram
   Time: 18:17:55
   ```

### What Gets Saved

Filename format: `{order_id}_{phase}_{timestamp}_{reason}.jpg`

Example:
```
monitoring_frames/
├── order_Phase1_20260228_181730_auto.jpg      ← Automatic (10s interval)
├── order_Phase1_20260228_181740_auto.jpg      ← Automatic (20s)
├── order_Phase1_20260228_181755_telegram.jpg  ← Telegram command
└── order_Phase1_20260228_181802_api.jpg       ← External API
```

## 2. External API Trigger (For Later Integration)

### Direct Method

If you have access to the monitor object in your code:

```python
from src.monitoring.camera import SimpleLineMonitor

# Your monitoring instance
monitor = SimpleLineMonitor(camera_index=0)

# Trigger a capture
monitor.trigger_capture(reason="my_system")
# Next time the monitor loop runs, it will capture and save
```

### Reasons You Can Use

```python
monitor.trigger_capture(reason="api")          # HTTP API call
monitor.trigger_capture(reason="sensor")       # IoT sensor signal
monitor.trigger_capture(reason="plc")          # PLC/industrial control
monitor.trigger_capture(reason="button")       # Physical button
monitor.trigger_capture(reason="quality_check") # QC inspection
monitor.trigger_capture(reason="alarm")        # Fault alarm
```

The `reason` becomes part of the filename!

### Thread-Safe

The trigger system uses threading locks, so it's safe to call from multiple threads:

```python
import threading

def sensor_thread():
    while True:
        # Wait for sensor signal
        if sensor_triggered():
            monitor.trigger_capture(reason="sensor")
        time.sleep(0.1)

# Run in background
threading.Thread(target=sensor_thread, daemon=True).start()
```

## 3. File-Based Trigger (Simplest)

For systems that can only create files:

```bash
# In another terminal or script:
echo "quality_check" > /tmp/capture_trigger
```

Then add this to your code (see `trigger_api_example.py`):

```python
import os

while monitoring:
    if os.path.exists("/tmp/capture_trigger"):
        with open("/tmp/capture_trigger", 'r') as f:
            reason = f.read().strip()
        monitor.trigger_capture(reason=reason)
        os.remove("/tmp/capture_trigger")
    time.sleep(0.5)
```

## 4. Automatic Interval (Default)

Already built-in! Saves every 10 seconds by default.

**Change interval** in `main.py` line 477:

```python
monitor.monitor_phase(
    phase_name=phase_name,
    order_id=order_id,
    duration_seconds=30,
    save_interval=5  # Change from 10 to 5 seconds
)
```

## Image Delivery

### Saved to Disk

ALL captures are saved to `monitoring_frames/`:

```
monitoring_frames/
└── {order_id}_{phase}_{timestamp}_{reason}.jpg
```

### Sent to Telegram

If triggered by Telegram OR if Telegram is configured:
- Image is sent back to your Telegram chat
- Includes caption with phase, reason, and time
- Happens automatically!

## Complete Example Usage

### Scenario: Production Line with Quality Checkpoints

```python
# main.py is running with camera monitoring active

# Automatic captures every 10 seconds
# ✓ order_SMT_20260228_180010_auto.jpg
# ✓ order_SMT_20260228_180020_auto.jpg

# Operator sends "CAPTURE" via Telegram at interesting moment
# ✓ order_SMT_20260228_180025_telegram.jpg
# ✓ Image sent back to Telegram

# Quality control system triggers capture
monitor.trigger_capture(reason="qc_inspection")
# ✓ order_SMT_20260228_180030_qc_inspection.jpg

# Automatic continues
# ✓ order_SMT_20260228_180040_auto.jpg
```

## Integration Examples

### Example 1: HTTP API (Flask)

Create a simple web API:

```python
from flask import Flask, request, jsonify

app = Flask(__name__)
monitor = None  # Set when monitoring starts

@app.route('/api/capture', methods=['POST'])
def capture():
    """POST /api/capture with {"reason": "test"}"""
    reason = request.json.get('reason', 'api')
    monitor.trigger_capture(reason=reason)
    return jsonify({"status": "ok", "reason": reason})

# Start server on port 5000
app.run(host='0.0.0.0', port=5000)
```

Then any system can trigger:
```bash
curl -X POST http://localhost:5000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"reason": "external_system"}'
```

### Example 2: Raspberry Pi Button

Physical button on GPIO pin:

```python
import RPi.GPIO as GPIO

BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

while True:
    GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
    monitor.trigger_capture(reason="button_press")
    time.sleep(0.3)  # Debounce
```

### Example 3: MQTT/IoT Sensor

Subscribe to sensor messages:

```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    reason = msg.payload.decode()
    monitor.trigger_capture(reason=reason)

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt.server.com", 1883)
client.subscribe("factory/quality/capture")
client.loop_forever()
```

## Testing

### Test Telegram Control

1. Run monitoring:
   ```bash
   python main.py
   # Complete Steps 1-5
   # Enable monitoring at Step 6
   ```

2. Open Telegram, send:
   ```
   CAPTURE
   ```

3. Check terminal output:
   ```
   📱 Telegram: Capture request received
   📸 Capture triggered by telegram: monitoring_frames/...
      ✓ Image sent to Telegram
   ```

4. Check Telegram - you should receive the image!

### Test Direct Trigger

```python
from src.monitoring.camera import SimpleLineMonitor

monitor = SimpleLineMonitor(
    camera_index=0,
    telegram_bot_token="your_token",
    telegram_chat_id="your_chat_id"
)

monitor.start_camera()
monitor.start_telegram_listener()

# Trigger from code
monitor.trigger_capture(reason="test")

# Monitor a dummy phase (will check triggers)
monitor.monitor_phase(
    phase_name="Test",
    order_id="test-001",
    duration_seconds=30
)
```

## Troubleshooting

### Telegram Trigger Not Working

1. **Check bot token and chat ID** in `.env`
2. **Verify bot is active**: Send `/start` to bot first
3. **Check terminal**: Should see "Telegram listener started"
4. **Try different commands**: `CAPTURE`, `PHOTO`, `SNAP` all work

### Image Not Sent to Telegram

1. **Check file size**: Telegram has 10MB limit
2. **Check permissions**: Ensure script can read monitoring_frames/
3. **Check network**: Telegram API requires internet

### Captures Not Triggering

1. **Verify monitoring is active**: Camera window should be open
2. **Check trigger queue**: Print `monitor.capture_triggers`
3. **Test manual trigger**: `monitor.trigger_capture(reason="debug")`

## Advanced Usage

### Multiple Trigger Sources

```python
# Start monitoring
monitor.start_camera()
monitor.start_telegram_listener()

# Add API endpoint
def api_trigger():
    monitor.trigger_capture(reason="api")

# Add sensor monitoring
def sensor_monitor():
    if sensor_triggered():
        monitor.trigger_capture(reason="sensor")

# Add file watcher
def file_watcher():
    if os.path.exists("/tmp/capture"):
        monitor.trigger_capture(reason="file")
        os.remove("/tmp/capture")

# All work together!
```

### Custom Reasons for Analysis

Use descriptive reasons to categorize captures:

```python
monitor.trigger_capture(reason="defect_detected")
monitor.trigger_capture(reason="operator_review")
monitor.trigger_capture(reason="shift_handover")
monitor.trigger_capture(reason="audit_requirement")
```

Later, filter by reason:

```bash
ls monitoring_frames/*defect_detected*.jpg
ls monitoring_frames/*audit*.jpg
```

## Benefits

1. **Flexible**: Multiple trigger methods
2. **Thread-safe**: Safe from any context
3. **Documented**: Reason saved in filename
4. **Instant feedback**: Telegram gets image immediately
5. **Extensible**: Easy to add new trigger sources
6. **No configuration needed**: Uses existing Telegram setup

## Next Steps

1. **Test Telegram control**: Send `CAPTURE` during monitoring
2. **Add your trigger**: Use `monitor.trigger_capture(reason="your_system")`
3. **Review captures**: Check `monitoring_frames/` for all images
4. **Integrate external systems**: See `trigger_api_example.py`

For more examples, see: `trigger_api_example.py`
