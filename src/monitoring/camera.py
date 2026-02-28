"""
Simple camera-based production line monitor with Telegram control
"""

import cv2
import time
import os
import requests
import threading
from datetime import datetime


class SimpleLineMonitor:
    """Simple camera-based production line monitor with remote control"""

    def __init__(self, camera_index=0, telegram_bot_token=None, telegram_chat_id=None):
        self.camera_index = camera_index
        self.camera = None
        self.monitoring = False

        # Telegram integration
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_thread = None
        self.telegram_running = False

        # Trigger system for external capture requests
        self.capture_triggers = []
        self.trigger_lock = threading.Lock()

    def start_camera(self):
        """Initialize camera"""
        print(f"Starting camera {self.camera_index}...")
        self.camera = cv2.VideoCapture(self.camera_index)

        if not self.camera.isOpened():
            raise Exception(f"Failed to open camera {self.camera_index}")

        # Get camera properties
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera started: {width}x{height}")

    def stop_camera(self):
        """Release camera"""
        if self.camera:
            self.camera.release()
            cv2.destroyAllWindows()
            print("Camera stopped")

    def start_telegram_listener(self):
        """Start background thread listening for Telegram commands"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return

        self.telegram_running = True
        self.telegram_thread = threading.Thread(target=self._telegram_listener_loop, daemon=True)
        self.telegram_thread.start()
        print("Telegram listener started - send 'CAPTURE' to take a photo")

    def stop_telegram_listener(self):
        """Stop Telegram listener thread"""
        self.telegram_running = False
        if self.telegram_thread:
            self.telegram_thread.join(timeout=2)

    def _telegram_listener_loop(self):
        """Background thread that listens for Telegram commands"""
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getUpdates"

        # Get current offset to ignore old messages
        try:
            response = requests.get(url, params={"offset": -1}, timeout=10)
            data = response.json()
            if data.get("ok") and data.get("result"):
                last_update_id = data["result"][-1]["update_id"]
            else:
                last_update_id = 0
        except:
            last_update_id = 0

        while self.telegram_running:
            try:
                params = {"offset": last_update_id + 1, "timeout": 5}
                response = requests.get(url, params=params, timeout=10)

                if response.status_code != 200:
                    time.sleep(1)
                    continue

                data = response.json()

                if not data.get("ok"):
                    time.sleep(1)
                    continue

                for update in data.get("result", []):
                    last_update_id = update["update_id"]

                    if "message" in update:
                        msg = update["message"]
                        if str(msg.get("chat", {}).get("id")) == str(self.telegram_chat_id):
                            text = msg.get("text", "").strip().upper()

                            if text == "CAPTURE" or text == "PHOTO" or text == "SNAP":
                                print("\n📱 Telegram: Capture request received")
                                self.trigger_capture(reason="telegram")

            except Exception as e:
                # Silently continue on errors
                time.sleep(1)

    def capture_frame(self):
        """Capture single frame"""
        if not self.camera or not self.camera.isOpened():
            return None

        ret, frame = self.camera.read()
        if ret:
            return frame
        return None

    def save_frame(self, frame, phase_name, order_id, reason="auto"):
        """Save frame to disk"""
        if frame is None:
            return None

        # Create monitoring directory
        os.makedirs("monitoring_frames", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"monitoring_frames/{order_id}_{phase_name}_{timestamp}_{reason}.jpg"

        cv2.imwrite(filename, frame)
        return filename

    def send_image_to_telegram(self, image_path, caption=""):
        """Send an image to Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("Telegram not configured, skipping image send")
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendPhoto"

        try:
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': self.telegram_chat_id,
                    'caption': caption
                }
                response = requests.post(url, files=files, data=data, timeout=10)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Failed to send image to Telegram: {e}")
            return False

    def trigger_capture(self, reason="manual"):
        """
        Trigger an immediate frame capture
        Can be called from Telegram, API, or any external system

        Args:
            reason: Why the capture was triggered (e.g., "telegram", "api", "sensor")

        Returns:
            Path to saved image file
        """
        with self.trigger_lock:
            self.capture_triggers.append(reason)
        return reason

    def check_and_process_triggers(self, frame, phase_name, order_id):
        """
        Check if there are any pending capture triggers and process them

        Returns:
            Number of triggers processed
        """
        triggers_to_process = []

        with self.trigger_lock:
            if self.capture_triggers:
                triggers_to_process = self.capture_triggers.copy()
                self.capture_triggers.clear()

        processed = 0
        for reason in triggers_to_process:
            # Save frame
            filename = self.save_frame(frame, phase_name, order_id, reason=reason)

            if filename:
                print(f"📸 Capture triggered by {reason}: {filename}")

                # Send to Telegram if configured
                if self.telegram_bot_token and self.telegram_chat_id:
                    caption = f"Phase: {phase_name}\nReason: {reason}\nTime: {datetime.now().strftime('%H:%M:%S')}"
                    if self.send_image_to_telegram(filename, caption):
                        print(f"   ✓ Image sent to Telegram")
                    else:
                        print(f"   ✗ Failed to send to Telegram")

                processed += 1

        return processed

    def show_frame(self, frame, phase_name, status="Running"):
        """Display frame with overlay"""
        if frame is None:
            return

        # Add text overlay
        display_frame = frame.copy()

        # Status text
        text = f"Phase: {phase_name} | Status: {status}"
        cv2.putText(display_frame, text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(display_frame, f"Time: {timestamp}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Instructions
        cv2.putText(display_frame, "Press 'q' to stop monitoring", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow('Production Line Monitor', display_frame)

    def monitor_phase(self, phase_name, order_id, duration_seconds=30, save_interval=10):
        """
        Monitor a production phase

        Args:
            phase_name: Name of the phase being monitored
            order_id: Production order ID
            duration_seconds: How long to monitor (or until 'q' pressed)
            save_interval: Save a frame every N seconds
        """
        print(f"\n{'='*60}")
        print(f"MONITORING: {phase_name}")
        print(f"Order: {order_id}")
        print(f"Duration: {duration_seconds}s")
        print(f"{'='*60}\n")

        if not self.camera or not self.camera.isOpened():
            self.start_camera()

        # Start Telegram listener if configured
        self.start_telegram_listener()

        start_time = time.time()
        last_save = 0
        frame_count = 0
        saved_count = 0

        try:
            while True:
                # Capture frame
                frame = self.capture_frame()
                if frame is None:
                    print("Failed to capture frame")
                    break

                frame_count += 1
                elapsed = time.time() - start_time

                # Show live view
                self.show_frame(frame, phase_name, f"Running ({elapsed:.0f}s)")

                # Check for external capture triggers (Telegram, API, etc.)
                triggers_processed = self.check_and_process_triggers(frame, phase_name, order_id)
                if triggers_processed > 0:
                    saved_count += triggers_processed

                # Save frame at intervals
                if elapsed - last_save >= save_interval:
                    saved_file = self.save_frame(frame, phase_name, order_id, reason="auto")
                    if saved_file:
                        print(f"[{elapsed:.0f}s] Saved: {saved_file}")
                        saved_count += 1
                    last_save = elapsed

                # Check for quit or duration exceeded
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nMonitoring stopped by user")
                    break

                if elapsed >= duration_seconds:
                    print(f"\nPhase monitoring complete ({duration_seconds}s)")
                    break

        except KeyboardInterrupt:
            print("\nMonitoring interrupted")

        finally:
            # Stop Telegram listener
            self.stop_telegram_listener()

        print(f"Frames captured: {frame_count}")
        print(f"Frames saved: {saved_count}")


def monitor_production_order(order_id, phases, camera_index=0):
    """
    Monitor all phases of a production order

    Args:
        order_id: Production order ID
        phases: List of phase dictionaries with 'name' and 'duration'
        camera_index: Which camera to use
    """
    print("\n" + "="*80)
    print("STEP 6: PHYSICAL INTEGRATION - PRODUCTION LINE MONITORING")
    print("="*80)
    print(f"\nProduction Order: {order_id}")
    print(f"Camera: {camera_index}")
    print(f"Phases to monitor: {len(phases)}")
    print()

    monitor = SimpleLineMonitor(camera_index=camera_index)

    try:
        monitor.start_camera()

        for i, phase in enumerate(phases, 1):
            phase_name = phase.get('name', f'Phase {i}')
            duration = phase.get('duration', 30)  # Default 30 seconds

            print(f"\n[{i}/{len(phases)}] Starting phase: {phase_name}")

            # Monitor this phase
            monitor.monitor_phase(
                phase_name=phase_name,
                order_id=order_id,
                duration_seconds=duration,
                save_interval=10  # Save frame every 10 seconds
            )

            # Brief pause between phases
            if i < len(phases):
                print("\nPreparing next phase...")
                time.sleep(2)

        print("\n" + "="*80)
        print("ALL PHASES MONITORED")
        print("="*80)
        print(f"\nFrames saved in: monitoring_frames/")
        print()

    finally:
        monitor.stop_camera()
