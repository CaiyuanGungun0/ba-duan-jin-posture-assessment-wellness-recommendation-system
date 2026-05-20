"""Baseline real-world accuracy evaluation via webcam.

How to use
----------
1. Run the script. 
2. Perform each Ba-Duan-Jin action in front of the camera.
3. While doing an action, hold the corresponding number key (1-8) to label it.
4. Release the key when you stop doing that action.
5. Press Q when done — a per-action accuracy table is printed.

Controls
--------
  1-8  : press once to START labeling that action
  0    : press to STOP labeling (or press the same number again)
  Q    : quit and show results
"""
from __future__ import annotations

from collections import deque, defaultdict
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

try:
    from .pose_model import PredictionSmoother, load_action_model
    from .posture_score import landmarks_to_array
except ImportError:
    from pose_model import PredictionSmoother, load_action_model
    from posture_score import landmarks_to_array

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POSE_MODEL = PROJECT_ROOT / "models" / "mediapipe" / "pose_landmarker_full.task"
DEFAULT_ACTION_MODEL = PROJECT_ROOT / "models" / "comparison" / "cnn_model.keras"

_POSE_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,7),(0,4),(4,5),(5,6),(6,8),(9,10),
    (11,12),(11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
    (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    (11,23),(12,24),(23,24),(23,25),(24,26),
    (25,27),(26,28),(27,29),(28,30),(29,31),(30,32),(27,31),(28,32),
]
_MIN_VIS = 0.3


def _draw_skeleton(frame: np.ndarray, landmarks) -> None:
    h, w = frame.shape[:2]
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    vs = [lm.visibility if lm.visibility is not None else 0.0 for lm in landmarks]
    for a, b in _POSE_CONNECTIONS:
        if vs[a] < _MIN_VIS or vs[b] < _MIN_VIS:
            continue
        cv2.line(frame, (int(xs[a]*w), int(ys[a]*h)),
                 (int(xs[b]*w), int(ys[b]*h)), (0, 200, 100), 2, cv2.LINE_AA)
    for i in range(len(landmarks)):
        if vs[i] < _MIN_VIS:
            continue
        cv2.circle(frame, (int(xs[i]*w), int(ys[i]*h)), 4, (255,255,255), -1)
        cv2.circle(frame, (int(xs[i]*w), int(ys[i]*h)), 4, (0,150,255), 1)


def _draw_overlay(
    frame: np.ndarray,
    smoothed_label: str | None,
    smoothed_conf: float,
    raw_conf: float,
    ground_truth: str | None,
    labeled_count: int,
    conf_threshold: float,
) -> None:
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 110), (20, 25, 20), -1)
    cv2.addWeighted(frame, 1.0, frame, 0.0, 0, frame)

    # Predicted action
    if smoothed_label is None:
        pred_text = f"Predicted: uncertain  (raw {raw_conf:.0%} < {conf_threshold:.0%})"
        pred_color = (100, 100, 100)
    else:
        pred_text = f"Predicted: {smoothed_label}  ({smoothed_conf:.0%} vote)"
        pred_color = (60, 210, 120) if smoothed_conf >= 0.7 else (0, 190, 255)
    cv2.putText(frame, pred_text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, pred_color, 2, cv2.LINE_AA)

    # Ground truth
    if ground_truth is not None:
        gt_text = f"Recording: {ground_truth}  [{labeled_count} frames]  (press same key or 0 to stop)"
        gt_color = (0, 220, 255)
    else:
        gt_text = "Press 1-8 to start labeling an action"
        gt_color = (160, 160, 160)
    cv2.putText(frame, gt_text, (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.58, gt_color, 1, cv2.LINE_AA)

    cv2.putText(frame, "Q = quit & show results  |  0 or Space = stop recording", (12, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 120, 120), 1, cv2.LINE_AA)


def _print_results(records: list[tuple[str, str]], labels: list[str]) -> None:
    if not records:
        print("\nNo labeled frames recorded.")
        return

    total = len(records)
    correct = sum(p == g for p, g in records)
    print(f"\n{'='*52}")
    print(f"  Overall accuracy: {correct}/{total} = {correct/total:.1%}")
    print(f"{'='*52}")
    print(f"  {'Action':<14} {'Correct':>8} {'Total':>7} {'Acc':>7}")
    print(f"  {'-'*40}")

    per_action: dict[str, list[bool]] = defaultdict(list)
    for pred, gt in records:
        per_action[gt].append(pred == gt)

    for label in labels:
        results = per_action.get(label, [])
        if not results:
            print(f"  {label:<14} {'—':>8} {'—':>7} {'—':>7}")
        else:
            c = sum(results)
            print(f"  {label:<14} {c:>8} {len(results):>7} {c/len(results):>7.1%}")
    print(f"{'='*52}\n")


def run_evaluation(
    camera_index: int = 0,
    mirror: bool = True,
    pose_model_path: Path = DEFAULT_POSE_MODEL,
    action_model_path: Path = DEFAULT_ACTION_MODEL,
    conf_threshold: float = 0.70,
    smooth_window: int = 7,
) -> None:
    action_model = load_action_model(action_model_path)
    seq_len = action_model.sequence_length
    smoother = PredictionSmoother(threshold=conf_threshold, window=smooth_window)
    landmark_buffer: deque[np.ndarray] = deque(maxlen=seq_len)

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(pose_model_path)),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        output_segmentation_masks=False,
    )

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}.")

    # (predicted_label, ground_truth_label)
    records: list[tuple[str, str]] = []
    labeled_count = 0
    active_gt: str | None = None   # currently active ground truth label (toggle state)

    print("Camera open. Press 1-8 to START labeling an action, press 0 or same key to STOP. Q to finish.")

    with PoseLandmarker.create_from_options(options) as landmarker:
        smoothed_label: str | None = None
        smoothed_conf: float = 0.0
        raw_conf: float = 0.0

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if mirror:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            # Toggle ground truth on/off
            if key == ord("0") or key == ord(" "):
                active_gt = None
            else:
                for n in range(1, 9):
                    if key == ord(str(n)):
                        pressed = f"action{n:02d}"
                        # pressing same key again stops labeling
                        active_gt = None if active_gt == pressed else pressed
                        break

            ground_truth = active_gt

            if result.pose_landmarks:
                lm_list = result.pose_landmarks[0]
                _draw_skeleton(frame, lm_list)
                user_pose = landmarks_to_array(lm_list)
                landmark_buffer.append(user_pose)

                if len(landmark_buffer) == seq_len:
                    window = np.stack(list(landmark_buffer))
                    raw_pred = action_model.predict_window(window)
                    smoothed = smoother.update(raw_pred)
                    smoothed_label = smoothed.label
                    smoothed_conf = smoothed.confidence
                    raw_conf = smoothed.raw_confidence

                    # Record if user is labeling and we have a confident prediction
                    if ground_truth is not None and smoothed_label is not None:
                        records.append((smoothed_label, ground_truth))
                        labeled_count += 1
            else:
                smoother.reset()
                landmark_buffer.clear()
                smoothed_label = None
                smoothed_conf = 0.0
                raw_conf = 0.0

            _draw_overlay(
                frame, smoothed_label, smoothed_conf, raw_conf,
                ground_truth, labeled_count, conf_threshold,
            )
            cv2.imshow("Ba-Duan-Jin Baseline Evaluation - press Q to quit", frame)

    cap.release()
    cv2.destroyAllWindows()
    _print_results(records, action_model.labels)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Real-world baseline accuracy evaluation.")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--conf-threshold", type=float, default=0.70)
    parser.add_argument("--smooth-window", type=int, default=7)
    args = parser.parse_args()
    run_evaluation(
        camera_index=args.camera,
        mirror=not args.no_mirror,
        conf_threshold=args.conf_threshold,
        smooth_window=args.smooth_window,
    )
