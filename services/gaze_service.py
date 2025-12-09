"""
Webcam-based gaze tracking service.
Captures eye position, blink, head pose, and distance at 5-10 fps.
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
import sys
import os
from collections import deque
from typing import Optional, Tuple
import psutil
import signal

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.database import insert_gaze_log, init_db


class GazeService:
    """Service for tracking gaze and head pose from webcam."""

    def __init__(self, target_fps: int = 8, enable_preview: bool = False):
        """
        Initialize gaze tracking service.

        Args:
            target_fps: Target frames per second (5-10 recommended)
            enable_preview: Show live video preview window
        """
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.enable_preview = enable_preview

        # Initialize MediaPipe Face Mesh
        self.mp_face = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Video capture
        self.cap = None

        # Blink detection window (rolling average)
        self.ear_window = deque(maxlen=4)

        # Performance monitoring
        self.process = psutil.Process()
        self.last_perf_check = time.time()
        self.frame_count = 0

        # Service state
        self.running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\nReceived shutdown signal, stopping service...")
        self.stop()
        sys.exit(0)

    @staticmethod
    def _dist(pt1: Tuple[int, int], pt2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points."""
        return np.linalg.norm(np.array(pt1) - np.array(pt2))

    def _calculate_head_distance(self, landmarks, frame_width: int) -> float:
        """
        Calculate approximate head distance from camera using face width.
        Smaller face = farther away, larger face = closer.

        Returns normalized distance (0.0 = very far, 1.0 = very close)
        """
        # Use distance between left and right face edges
        left_edge = landmarks.landmark[234]  # Left face edge
        right_edge = landmarks.landmark[454]  # Right face edge

        face_width_px = abs(right_edge.x - left_edge.x) * frame_width

        # Normalize to 0-1 range (typical face width is 150-400 pixels)
        # At normal distance (~60cm), face width is ~200-250px
        normalized_distance = min(1.0, max(0.0, (face_width_px - 100) / 300))

        return normalized_distance

    def _calculate_ear(self, landmarks, frame_shape: Tuple[int, int],
                       eye_indices: dict) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) for blink detection.
        EAR = (average vertical distance) / (horizontal distance)
        """
        h, w = frame_shape[:2]

        def to_px(idx):
            pt = landmarks.landmark[idx]
            return int(pt.x * w), int(pt.y * h)

        top1 = to_px(eye_indices['top1'])
        top2 = to_px(eye_indices['top2'])
        bot1 = to_px(eye_indices['bot1'])
        bot2 = to_px(eye_indices['bot2'])
        left = to_px(eye_indices['left'])
        right = to_px(eye_indices['right'])

        vert = (self._dist(top1, bot1) + self._dist(top2, bot2)) / 2.0
        horiz = self._dist(left, right)

        return vert / (horiz + 1e-6)

    def _process_frame(self, frame) -> Optional[dict]:
        """
        Process a single frame and extract gaze features.

        Returns dict with features or None if no face detected.
        """
        h, w = frame.shape[:2]

        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.mp_face.process(rgb)

        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0]

        def to_px(idx):
            pt = lm.landmark[idx]
            return int(pt.x * w), int(pt.y * h)

        # 1. Gaze feature: eye off-center ratio
        left_pupil_x, _ = to_px(473)
        right_pupil_x, _ = to_px(468)
        eye_center_x = (left_pupil_x + right_pupil_x) / 2
        eye_off_center = abs(eye_center_x - w // 2) / (w // 2)

        # 2. Blink detection using EAR for both eyes
        left_eye_indices = {
            'top1': 159, 'top2': 27,
            'bot1': 145, 'bot2': 23,
            'left': 35, 'right': 133
        }
        right_eye_indices = {
            'top1': 386, 'top2': 257,
            'bot1': 174, 'bot2': 253,
            'left': 362, 'right': 263
        }

        left_ear = self._calculate_ear(lm, frame.shape, left_eye_indices)
        right_ear = self._calculate_ear(lm, frame.shape, right_eye_indices)
        ear_mean = (left_ear + right_ear) / 2.0

        # Smooth blink detection using rolling window
        self.ear_window.append(ear_mean)
        blink_flag = 1 if (len(self.ear_window) == self.ear_window.maxlen and
                          all(e < 0.18 for e in self.ear_window)) else 0

        # 3. Head pitch (up/down nod)
        nose = to_px(1)
        chin = to_px(152)
        dy = chin[1] - nose[1]
        dx = chin[0] - nose[0]
        pitch_rad = math.atan2(dy, dx)
        pitch_deg = math.degrees(pitch_rad) - 90

        # 4. Head yaw (left/right turn)
        left_corner = to_px(35)  # Left eye corner
        right_corner = to_px(263)  # Right eye corner
        yaw_norm = ((left_corner[0] + right_corner[0]) / 2 - w // 2)
        yaw_deg = (yaw_norm / (w // 2)) * 30  # Scale to approx ±30 degrees

        # 5. Head distance (proximity to camera)
        head_distance = self._calculate_head_distance(lm, w)

        return {
            'timestamp': time.time(),
            'eye_off_center': float(eye_off_center),
            'blink': int(blink_flag),
            'head_pitch': float(pitch_deg),
            'head_yaw': float(yaw_deg),
            'head_distance': float(head_distance)
        }

    def _check_performance(self):
        """Monitor and log CPU/memory usage."""
        now = time.time()
        if now - self.last_perf_check >= 10.0:  # Check every 10 seconds
            cpu_percent = self.process.cpu_percent()
            memory_mb = self.process.memory_info().rss / 1024 / 1024

            print(f"[Performance] CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f} MB | "
                  f"FPS: {self.frame_count / 10:.1f}")

            # Warn if exceeding thresholds
            if cpu_percent > 25:
                print(f"WARNING: High CPU usage ({cpu_percent:.1f}%)")
            if memory_mb > 200:
                print(f"WARNING: High memory usage ({memory_mb:.1f} MB)")

            self.last_perf_check = now
            self.frame_count = 0

    def start(self):
        """Start the gaze tracking service."""
        print("Starting gaze tracking service...")
        print(f"Target FPS: {self.target_fps}")
        print(f"Frame interval: {self.frame_interval:.3f}s")

        # Initialize database
        init_db()

        # Open webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open webcam")

        # Set camera to lower resolution for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.running = True
        last_capture_time = 0

        print("Service started. Press Ctrl+C to stop.")

        try:
            while self.running:
                current_time = time.time()

                # Rate limiting to target FPS
                if current_time - last_capture_time < self.frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent busy-waiting
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    print("WARNING: Failed to read frame from webcam")
                    time.sleep(0.1)
                    continue

                # Process frame and extract features
                features = self._process_frame(frame)

                if features:
                    # Log to database
                    insert_gaze_log(
                        timestamp=features['timestamp'],
                        eye_off_center=features['eye_off_center'],
                        blink=features['blink'],
                        head_pitch=features['head_pitch'],
                        head_yaw=features['head_yaw'],
                        head_distance=features['head_distance']
                    )

                    self.frame_count += 1

                # Show preview if enabled
                if self.enable_preview:
                    status_text = "Face Detected" if features else "No Face"
                    cv2.putText(frame, status_text, (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Gaze Service", frame)
                    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                        break

                # Performance monitoring
                self._check_performance()

                last_capture_time = current_time

        except Exception as e:
            print(f"ERROR: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the gaze tracking service."""
        if not self.running:
            return

        print("\nStopping gaze tracking service...")
        self.running = False

        if self.cap:
            self.cap.release()

        if self.enable_preview:
            cv2.destroyAllWindows()

        print("Service stopped successfully")


def main():
    """Run gaze service from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Gaze tracking service')
    parser.add_argument('--fps', type=int, default=8,
                       help='Target frames per second (default: 8)')
    parser.add_argument('--preview', action='store_true',
                       help='Show live preview window')

    args = parser.parse_args()

    service = GazeService(target_fps=args.fps, enable_preview=args.preview)
    service.start()


if __name__ == "__main__":
    main()
