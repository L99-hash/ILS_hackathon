"""
Simple camera-based production line monitor with Telegram control
"""

import cv2
import time
import os
import json
import requests
import threading
from datetime import datetime


class SimpleLineMonitor:
    """Simple camera-based production line monitor with remote control"""

    def __init__(self, camera_indices=[0], telegram_bot_token=None, telegram_chat_id=None):
        """
        Initialize monitor with single or multiple cameras

        Args:
            camera_indices: Single index (int) or list of indices [0, 1]
            telegram_bot_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
        """
        # Support both single camera and multiple cameras
        if isinstance(camera_indices, int):
            self.camera_indices = [camera_indices]
        else:
            self.camera_indices = camera_indices

        # Dictionary of cameras {index: VideoCapture object}
        self.cameras = {}
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
        """Initialize all cameras"""
        for idx in self.camera_indices:
            print(f"Starting camera {idx}...")
            cap = cv2.VideoCapture(idx)

            if not cap.isOpened():
                print(f"Warning: Failed to open camera {idx}")
                continue

            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"  Camera {idx} started: {width}x{height}")

            self.cameras[idx] = cap

        if not self.cameras:
            raise Exception(f"Failed to open any cameras from {self.camera_indices}")

        print(f"Total cameras active: {len(self.cameras)}")

    def stop_camera(self):
        """Release all cameras"""
        for idx, cap in self.cameras.items():
            cap.release()
            print(f"Camera {idx} stopped")

        cv2.destroyAllWindows()
        self.cameras.clear()

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
        """
        Capture frames from all cameras

        Returns:
            Dictionary {camera_index: frame} or None if all failed
        """
        frames = {}

        for idx, cap in self.cameras.items():
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    frames[idx] = frame

        return frames if frames else None

    def save_frames(self, frames_dict, phase_name, order_id, reason="auto"):
        """
        Save frames from all cameras to disk

        Args:
            frames_dict: Dictionary {camera_index: frame}
            phase_name: Name of current phase
            order_id: Production order ID
            reason: Why frame was captured

        Returns:
            List of saved filenames
        """
        if not frames_dict:
            return []

        # Create monitoring directory
        os.makedirs("monitoring_frames", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []

        for cam_idx, frame in frames_dict.items():
            filename = f"monitoring_frames/{order_id}_{phase_name}_cam{cam_idx}_{timestamp}_{reason}.jpg"
            cv2.imwrite(filename, frame)
            saved_files.append(filename)

        return saved_files

    def send_images_to_telegram(self, image_paths, caption=""):
        """
        Send one or more images to Telegram

        If multiple images, sends as a media group (album)
        If single image, sends as regular photo

        Args:
            image_paths: List of image file paths or single path
            caption: Caption for the images

        Returns:
            True if successful
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("Telegram not configured, skipping image send")
            return False

        # Convert single path to list
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        if not image_paths:
            return False

        try:
            if len(image_paths) == 1:
                # Single image - use sendPhoto
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendPhoto"
                with open(image_paths[0], 'rb') as photo:
                    files = {'photo': photo}
                    data = {
                        'chat_id': self.telegram_chat_id,
                        'caption': caption
                    }
                    response = requests.post(url, files=files, data=data, timeout=10)
                    response.raise_for_status()
                    return True

            else:
                # Multiple images - use sendMediaGroup
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMediaGroup"

                # Build media array
                media = []
                files_dict = {}

                for i, path in enumerate(image_paths):
                    attach_name = f"photo{i}"
                    files_dict[attach_name] = open(path, 'rb')

                    media_item = {
                        'type': 'photo',
                        'media': f'attach://{attach_name}'
                    }

                    # Add caption to first image
                    if i == 0 and caption:
                        media_item['caption'] = caption

                    media.append(media_item)

                data = {
                    'chat_id': self.telegram_chat_id,
                    'media': json.dumps(media)
                }

                try:
                    response = requests.post(url, data=data, files=files_dict, timeout=15)
                    response.raise_for_status()
                    return True
                finally:
                    # Close all file handles
                    for f in files_dict.values():
                        f.close()

        except Exception as e:
            print(f"Failed to send images to Telegram: {e}")
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

    def check_and_process_triggers(self, frames_dict, phase_name, order_id):
        """
        Check if there are any pending capture triggers and process them

        Args:
            frames_dict: Dictionary {camera_index: frame}
            phase_name: Current phase name
            order_id: Production order ID

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
            # Save frames from all cameras
            saved_files = self.save_frames(frames_dict, phase_name, order_id, reason=reason)

            if saved_files:
                print(f"📸 Capture triggered by {reason}:")
                for filepath in saved_files:
                    print(f"   {filepath}")

                # Send to Telegram if configured
                if self.telegram_bot_token and self.telegram_chat_id:
                    num_cams = len(saved_files)
                    caption = f"Phase: {phase_name}\nCameras: {num_cams}\nReason: {reason}\nTime: {datetime.now().strftime('%H:%M:%S')}"

                    if self.send_images_to_telegram(saved_files, caption):
                        print(f"   ✓ {num_cams} image(s) sent to Telegram")
                    else:
                        print(f"   ✗ Failed to send to Telegram")

                processed += 1

        return processed

    def show_frames(self, frames_dict, phase_name, status="Running"):
        """
        Display frames from all cameras with overlays

        Args:
            frames_dict: Dictionary {camera_index: frame}
            phase_name: Current phase name
            status: Status text to display
        """
        if not frames_dict:
            return

        # Add text overlay to each frame
        display_frames = []

        for cam_idx in sorted(frames_dict.keys()):
            frame = frames_dict[cam_idx]
            display_frame = frame.copy()

            # Status text
            text = f"Camera {cam_idx} | Phase: {phase_name} | {status}"
            cv2.putText(display_frame, text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            cv2.putText(display_frame, f"Time: {timestamp}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Instructions (only on first camera)
            if cam_idx == sorted(frames_dict.keys())[0]:
                cv2.putText(display_frame, "Press 'q' to stop monitoring", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            display_frames.append(display_frame)

        if len(display_frames) == 1:
            # Single camera - show as is
            cv2.imshow('Production Line Monitor', display_frames[0])
        else:
            # Multiple cameras - show side by side
            # Resize all frames to the same height before concatenating
            if display_frames:
                # Find the minimum height among all frames
                min_height = min(frame.shape[0] for frame in display_frames)

                # Resize all frames to have the same height
                resized_frames = []
                for frame in display_frames:
                    if frame.shape[0] != min_height:
                        # Calculate new width to maintain aspect ratio
                        aspect_ratio = frame.shape[1] / frame.shape[0]
                        new_width = int(min_height * aspect_ratio)
                        resized = cv2.resize(frame, (new_width, min_height))
                        resized_frames.append(resized)
                    else:
                        resized_frames.append(frame)

                # Stack frames horizontally
                combined = cv2.hconcat(resized_frames)
                cv2.imshow('Production Line Monitor - All Cameras', combined)

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

        if not self.cameras:
            self.start_camera()

        # Start Telegram listener if configured
        self.start_telegram_listener()

        start_time = time.time()
        last_save = 0
        frame_count = 0
        saved_count = 0

        try:
            while True:
                # Capture frames from all cameras
                frames_dict = self.capture_frame()
                if frames_dict is None:
                    print("Failed to capture frames")
                    break

                frame_count += 1
                elapsed = time.time() - start_time

                # Show live view
                self.show_frames(frames_dict, phase_name, f"Running ({elapsed:.0f}s)")

                # Check for external capture triggers (Telegram, API, etc.)
                triggers_processed = self.check_and_process_triggers(frames_dict, phase_name, order_id)
                if triggers_processed > 0:
                    saved_count += triggers_processed

                # Save frames at intervals
                if elapsed - last_save >= save_interval:
                    saved_files = self.save_frames(frames_dict, phase_name, order_id, reason="auto")
                    if saved_files:
                        print(f"[{elapsed:.0f}s] Saved {len(saved_files)} frame(s)")
                        saved_count += len(saved_files)
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
