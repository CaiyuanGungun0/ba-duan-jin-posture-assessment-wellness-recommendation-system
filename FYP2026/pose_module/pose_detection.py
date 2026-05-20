from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

try:
    from .posture_score import compare_pose, landmarks_to_array, load_reference_keypoints
    from .pose_model import PredictionSmoother, load_action_model
except ImportError:
    from posture_score import compare_pose, landmarks_to_array, load_reference_keypoints
    from pose_model import PredictionSmoother, load_action_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "models" / "mediapipe" / "pose_landmarker_full.task"
DEFAULT_ACTION_MODEL = PROJECT_ROOT / "models" / "comparison" / "cnn_model.keras"

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

_MIN_VISIBILITY = 0.3


def _draw_pose_landmarks(frame: np.ndarray, landmarks) -> None:
    h, w = frame.shape[:2]
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    vs = [lm.visibility if lm.visibility is not None else 0.0 for lm in landmarks]

    for a, b in _POSE_CONNECTIONS:
        if vs[a] < _MIN_VISIBILITY or vs[b] < _MIN_VISIBILITY:
            continue
        cv2.line(
            frame,
            (int(xs[a] * w), int(ys[a] * h)),
            (int(xs[b] * w), int(ys[b] * h)),
            (0, 200, 100), 2, cv2.LINE_AA,
        )
    for i in range(len(landmarks)):
        if vs[i] < _MIN_VISIBILITY:
            continue
        px, py = int(xs[i] * w), int(ys[i] * h)
        cv2.circle(frame, (px, py), 4, (255, 255, 255), -1)
        cv2.circle(frame, (px, py), 4, (0, 150, 255), 1)


def _draw_feedback(
    frame: np.ndarray,
    accuracy: float | None,
    advice: list[str],
    smoothed_label: str | None,
    smoothed_conf: float,
    raw_conf: float,
    conf_threshold: float,
) -> None:
    panel_height = 120
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], panel_height), (22, 31, 28), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Row 1 — pose accuracy
    if accuracy is None:
        score_text = "Accuracy: waiting for pose"
        acc_color = (220, 220, 220)
    else:
        score_text = f"Accuracy: {accuracy:.1f}%"
        acc_color = (60, 210, 120) if accuracy >= 80 else (0, 190, 255) if accuracy >= 60 else (70, 90, 255)
    cv2.putText(frame, score_text, (18, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, acc_color, 2, cv2.LINE_AA)

    # Row 2 — action label with confidence
    if smoothed_label is None:
        action_text = f"Action: uncertain  (conf {raw_conf:.0%} < {conf_threshold:.0%})"
        action_color = (100, 100, 100)
    else:
        action_text = f"Action: {smoothed_label}  ({smoothed_conf:.0%} vote)"
        action_color = (255, 200, 50) if smoothed_conf >= 0.7 else (180, 180, 60)
    cv2.putText(frame, action_text, (18, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.6, action_color, 1, cv2.LINE_AA)

    # Row 3 & 4 — posture advice
    for idx, item in enumerate(advice[:2]):
        cv2.putText(
            frame, item, (18, 76 + idx * 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (245, 245, 245), 1, cv2.LINE_AA,
        )


def _resize_to_height(frame: np.ndarray, height: int) -> np.ndarray:
    ratio = height / frame.shape[0]
    return cv2.resize(frame, (int(frame.shape[1] * ratio), height))


def run_pose_feedback(
    reference_video: str | Path,
    reference_keypoints: str | Path,
    camera_index: int = 0,
    mirror: bool = True,
    model_path: str | Path = DEFAULT_MODEL,
    action_model_path: str | Path = DEFAULT_ACTION_MODEL,
    conf_threshold: float = 0.70,
    smooth_window: int = 7,
) -> None:
    ref_poses = load_reference_keypoints(reference_keypoints)

    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}.")

    video = cv2.VideoCapture(str(reference_video))
    if not video.isOpened():
        camera.release()
        raise RuntimeError(f"Could not open reference video: {reference_video}")

    # Load action classifier if available
    action_model: PoseActionModel | None = None
    action_model_path = Path(action_model_path)
    if action_model_path.exists():
        action_model = load_action_model(action_model_path)
        print(f"Loaded action model: {action_model_path.name}  "
              f"(classes: {action_model.labels})")
    else:
        print(f"Action model not found at {action_model_path} — action label disabled.")

    smoother = PredictionSmoother(threshold=conf_threshold, window=smooth_window)
    # Buffer of landmark frames [33, 4] for the sliding action window
    landmark_buffer: deque[np.ndarray] = deque(
        maxlen=action_model.sequence_length if action_model else 30
    )

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        output_segmentation_masks=False,
    )

    ref_frame_index = 0
    latest_accuracy: float | None = None
    latest_advice: list[str] = ["Move into frame and follow the reference video."]
    smoothed_label: str | None = None
    smoothed_conf: float = 0.0
    raw_conf: float = 0.0

    with PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            ok, camera_frame = camera.read()
            if not ok:
                break

            if mirror:
                camera_frame = cv2.flip(camera_frame, 1)

            ref_ok, ref_frame = video.read()
            if not ref_ok:
                video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ref_frame_index = 0
                ref_ok, ref_frame = video.read()
                if not ref_ok:
                    break

            rgb = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if result.pose_landmarks:
                lm_list = result.pose_landmarks[0]
                _draw_pose_landmarks(camera_frame, lm_list)

                user_pose = landmarks_to_array(lm_list)

                # Pose accuracy vs reference
                reference_pose = ref_poses[ref_frame_index % len(ref_poses)]
                score = compare_pose(user_pose, reference_pose)
                latest_accuracy = score.accuracy
                latest_advice = score.advice

                # Action classification with smoothing
                if action_model is not None:
                    landmark_buffer.append(user_pose)
                    if len(landmark_buffer) == landmark_buffer.maxlen:
                        window = np.stack(list(landmark_buffer))  # [T, 33, 4]
                        raw_pred = action_model.predict_window(window)
                        smoothed = smoother.update(raw_pred)
                        smoothed_label = smoothed.label
                        smoothed_conf = smoothed.confidence
                        raw_conf = smoothed.raw_confidence
            else:
                latest_accuracy = None
                latest_advice = ["No pose detected. Step back and improve lighting."]
                smoother.reset()
                landmark_buffer.clear()
                smoothed_label = None
                smoothed_conf = 0.0
                raw_conf = 0.0

            _draw_feedback(
                camera_frame,
                latest_accuracy,
                latest_advice,
                smoothed_label,
                smoothed_conf,
                raw_conf,
                conf_threshold,
            )

            ref_frame = _resize_to_height(ref_frame, camera_frame.shape[0])
            cv2.putText(
                ref_frame, "Reference", (18, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA,
            )

            combined = np.hstack([camera_frame, ref_frame])
            cv2.imshow("Ba Duan Jin Pose Feedback - press Q to quit", combined)

            ref_frame_index += 1
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

    camera.release()
    video.release()
    cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Realtime Ba Duan Jin posture feedback.")
    parser.add_argument("--reference-video", default="data/raw_video/baduanjin_video01.mp4")
    parser.add_argument("--reference-keypoints", default="data/keypoints/video01_keypoints.csv")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--action-model", default=str(DEFAULT_ACTION_MODEL))
    parser.add_argument("--conf-threshold", type=float, default=0.70,
                        help="Minimum confidence to count a prediction in the vote buffer.")
    parser.add_argument("--smooth-window", type=int, default=7,
                        help="Number of recent high-confidence predictions to majority-vote over.")
    parser.add_argument("--no-mirror", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pose_feedback(
        reference_video=args.reference_video,
        reference_keypoints=args.reference_keypoints,
        camera_index=args.camera,
        mirror=not args.no_mirror,
        model_path=args.model,
        action_model_path=args.action_model,
        conf_threshold=args.conf_threshold,
        smooth_window=args.smooth_window,
    )
