from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import mediapipe as mp
import pandas as pd
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "models" / "mediapipe" / "pose_landmarker_full.task"


def _column_names() -> list[str]:
    names: list[str] = []
    for landmark_idx in range(33):
        names.extend(
            [
                f"lm_{landmark_idx}_x",
                f"lm_{landmark_idx}_y",
                f"lm_{landmark_idx}_z",
                f"lm_{landmark_idx}_visibility",
            ]
        )
    return names


def extract_keypoints_from_video(
    video_path: str | Path,
    output_csv: str | Path,
    model_path: str | Path = DEFAULT_MODEL,
) -> int:
    video_path = Path(video_path)
    output_csv = Path(output_csv)
    model_path = Path(model_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Pose model not found: {model_path}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        output_segmentation_masks=False,
    )

    all_frames_data: list[list[float]] = []
    frame_count = 0

    with PoseLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if result.pose_landmarks:
                frame_data: list[float] = []
                for lm in result.pose_landmarks[0]:
                    frame_data.extend(
                        [lm.x, lm.y, lm.z, lm.visibility if lm.visibility is not None else 0.0]
                    )
                all_frames_data.append(frame_data)

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Processed {frame_count} frames from {video_path.name}")

    cap.release()

    df = pd.DataFrame(all_frames_data, columns=_column_names())
    df.to_csv(output_csv, index=False)
    print(f"Saved {len(df)} pose frames to {output_csv}")
    return len(df)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract MediaPipe pose keypoints from a video.")
    parser.add_argument("--video", default="data/baduanjin_video01.mp4")
    parser.add_argument("--output", default="data/keypoints/video01_keypoints.csv")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    extract_keypoints_from_video(args.video, args.output, args.model)
