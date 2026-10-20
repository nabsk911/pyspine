"""Webcam posture monitor.

Tracks the nose and shoulders, learns an upright baseline ('c' to calibrate),
and sends a desktop notification when you slouch for too long.
"""

import json
import subprocess
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = Path("pose_landmarker_lite.task")
BASELINE_PATH = Path("baseline.json")

TOLERANCE = 0.05          # how much closer the nose may get before it counts as slouching
BAD_SECONDS = 10          # how long you must slouch before being notified
NOTIFY_COOLDOWN = 60      # minimum seconds between two notifications
CALIBRATION_SECONDS = 2   # how long the baseline sampling lasts

# MediaPipe pose landmark indices
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12

# On-screen status colors (BGR)
GRAY = (128, 128, 128)
YELLOW = (255, 255, 0)
RED = (0, 0, 255)
GREEN = (0, 200, 0)


def notify(message: str) -> None:
    """Show a desktop notification."""
    subprocess.run(["notify-send", "Slouch Alert!", message], check=False)


def posture_score(landmarks) -> dict:
    """Vertical distance from the nose to the shoulder line (smaller = more slouched)."""
    nose = landmarks[NOSE]
    left_shoulder = landmarks[LEFT_SHOULDER]
    right_shoulder = landmarks[RIGHT_SHOULDER]

    shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
    return {"shoulder_nose": shoulder_y - nose.y}


def is_slouching(score: dict, baseline: dict) -> bool:
    """True if the nose sits more than TOLERANCE closer to the shoulders than in the baseline."""
    return score["shoulder_nose"] < baseline["shoulder_nose"] * (1 - TOLERANCE)


def load_baseline() -> dict | None:
    """Read the saved baseline, or None if there is no usable one."""
    if not BASELINE_PATH.exists():
        return None

    baseline = json.loads(BASELINE_PATH.read_text())
    return baseline if "shoulder_nose" in baseline else None


def save_baseline(samples: list[dict]) -> dict:
    """Average the calibration samples, store them, and return the result."""
    baseline = {key: sum(sample[key] for sample in samples) / len(samples) for key in samples[0]}
    BASELINE_PATH.write_text(json.dumps(baseline))
    return baseline


def draw_status(frame, text: str, color) -> None:
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)


def main():
    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,  # look for a single person
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    baseline = load_baseline()

    camera = cv2.VideoCapture(0)
    started_at = time.time()

    calibration_ends_at = 0.0
    calibration_samples = []
    slouching_since = None
    last_notification = 0.0

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)  # mirror, so moving left looks like moving left

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int((time.time() - started_at) * 1000)
            result = landmarker.detect_for_video(image, timestamp_ms)

            status, color = "No person detected", GRAY

            if result.pose_landmarks:
                score = posture_score(result.pose_landmarks[0])
                now = time.time()

                if now < calibration_ends_at:
                    calibration_samples.append(score)
                    status, color = "Calibrating - sit upright...", YELLOW

                elif calibration_samples:
                    # Calibration just ended: turn the collected samples into a baseline.
                    baseline = save_baseline(calibration_samples)
                    calibration_samples = []
                    print("Baseline saved:", baseline)

                elif baseline is None:
                    status = "Press 'c' to calibrate"

                elif is_slouching(score, baseline):
                    status, color = "SLOUCHING", RED
                    if slouching_since is None:
                        slouching_since = now

                    slouched_long_enough = now - slouching_since >= BAD_SECONDS
                    cooldown_over = now - last_notification >= NOTIFY_COOLDOWN
                    if slouched_long_enough and cooldown_over:
                        notify("Sit up straight! Posture ain't no joke.")
                        last_notification = now

                else:
                    status, color = "Good posture", GREEN
                    slouching_since = None
            else:
                slouching_since = None

            draw_status(frame, status, color)
            cv2.imshow("Posture", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("c"):
                calibration_ends_at = time.time() + CALIBRATION_SECONDS
                calibration_samples = []
    finally:
        camera.release()
        cv2.destroyAllWindows()
        landmarker.close()


if __name__ == "__main__":
    main()
