# Future Integrations

This folder contains examples and templates for future system integrations.

## Current Files

### trigger_api_example.py

Examples showing how to trigger camera captures from external systems. This will be useful when integrating:

- **CNN/AI Models**: Trigger captures when anomalies detected
- **Quality Control Systems**: Capture on defect detection
- **IoT Sensors**: Capture on sensor alerts
- **PLCs/Industrial Control**: Capture on production events

## Planned Integrations

### 1. CNN Integration

When you add CNN models for production line analysis:

```python
from src.monitoring.camera import SimpleLineMonitor

# Your CNN model
model = load_cnn_model()

# Monitor instance
monitor = SimpleLineMonitor(camera_index=0)

# In your CNN processing loop:
def process_frame(frame):
    prediction = model.predict(frame)

    if prediction['defect_detected']:
        # Trigger high-res capture for documentation
        monitor.trigger_capture(reason=f"defect_{prediction['type']}")

        # Image automatically saved and sent to Telegram
```

### 2. API Endpoints

Create HTTP endpoints for CNN system to trigger captures:

```python
# See trigger_api_example.py for full Flask example

@app.route('/api/capture', methods=['POST'])
def capture():
    data = request.json
    reason = data.get('reason', 'cnn')
    defect_type = data.get('defect_type', 'unknown')

    monitor.trigger_capture(reason=f"cnn_{defect_type}")

    return jsonify({
        "status": "captured",
        "reason": f"cnn_{defect_type}"
    })
```

### 3. Real-time Analysis Pipeline

```
Camera Frame
    ↓
CNN Model (fast inference)
    ↓
Defect Detected?
    ↓ YES
Trigger High-Quality Capture
    ↓
Save to monitoring_frames/
    ↓
Send to Telegram
    ↓
Log for quality review
```

## Integration Pattern

All future integrations should follow this pattern:

1. **Detect event** (CNN, sensor, etc.)
2. **Call trigger**: `monitor.trigger_capture(reason="your_system")`
3. **Image automatically**:
   - Saved to `monitoring_frames/`
   - Sent to Telegram (if configured)
   - Logged with reason in filename

## File Naming

Captured images follow this pattern:
```
monitoring_frames/
└── {order_id}_{phase}_{timestamp}_{reason}.jpg
```

Examples:
```
order123_SMT_20260228_181755_cnn_defect.jpg
order123_SMT_20260228_181802_cnn_scratch.jpg
order123_Reflow_20260228_181945_sensor_temp.jpg
```

## Trigger Reasons You Might Use

```python
# CNN/AI triggers
monitor.trigger_capture(reason="cnn_defect")
monitor.trigger_capture(reason="cnn_scratch")
monitor.trigger_capture(reason="cnn_misalignment")
monitor.trigger_capture(reason="ai_anomaly")

# Quality control
monitor.trigger_capture(reason="qc_inspection")
monitor.trigger_capture(reason="qc_failed")

# Sensors
monitor.trigger_capture(reason="temp_alarm")
monitor.trigger_capture(reason="vibration_detected")

# Production events
monitor.trigger_capture(reason="phase_start")
monitor.trigger_capture(reason="phase_complete")
monitor.trigger_capture(reason="operator_review")
```

## Next Steps for CNN Integration

1. **Test current trigger system**: Run `python main.py` and test Telegram `CAPTURE`
2. **Review trigger_api_example.py**: See all trigger methods
3. **Design CNN pipeline**: Determine when to trigger captures
4. **Implement integration**: Use `monitor.trigger_capture()` in your CNN code
5. **Test end-to-end**: Verify images are captured, saved, and sent to Telegram

## Documentation

- **Trigger System**: See `CAMERA_TRIGGERS.md` (in this folder)
- **Trigger Examples**: See `trigger_api_example.py` (in this folder)
- **Monitoring Guide**: See `/STEP6_INTEGRATED.md`
- **Camera Setup**: See `/CAMERA_SETUP.md`

## Contact

For questions about integration, refer to the main documentation or check the examples in `trigger_api_example.py`.
