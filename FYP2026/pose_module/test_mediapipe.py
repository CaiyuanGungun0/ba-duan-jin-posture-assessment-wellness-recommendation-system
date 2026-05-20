from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "models" / "mediapipe" / "pose_landmarker_full.task"

_POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    (25, 27), (26, 28), (27, 29), (28, 30),
    (29, 31), (30, 32), (27, 31), (28, 32),
]

_MIN_VIS = 0.3


def _draw(frame: np.ndarray, landmarks) -> None:
    h, w = frame.shape[:2]
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    vs = [lm.visibility if lm.visibility is not None else 0.0 for lm in landmarks]

    for a, b in _POSE_CONNECTIONS:
        if vs[a] < _MIN_VIS or vs[b] < _MIN_VIS:
            continue
        cv2.line(
            frame,
            (int(xs[a] * w), int(ys[a] * h)),
            (int(xs[b] * w), int(ys[b] * h)),
            (0, 200, 100), 2, cv2.LINE_AA,
        )

    for i in range(len(landmarks)):
        if vs[i] < _MIN_VIS:
            continue
        px, py = int(xs[i] * w), int(ys[i] * h)
        cv2.circle(frame, (px, py), 4, (255, 255, 255), -1)
        cv2.circle(frame, (px, py), 4, (0, 150, 255), 1)


def main() -> None:
    if not DEFAULT_MODEL.exists():
        raise FileNotFoundError(f"Pose model not found: {DEFAULT_MODEL}")

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(DEFAULT_MODEL)),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Camera is not available. Check permissions or try another camera index.")

    with PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera frame not available")
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if result.pose_landmarks:
                _draw(frame, result.pose_landmarks[0])

            cv2.imshow("MediaPipe Pose Test - press Q to quit", frame)
            key = cv2.waitKey(10) & 0xFF
            if key in (27, ord("q")):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
