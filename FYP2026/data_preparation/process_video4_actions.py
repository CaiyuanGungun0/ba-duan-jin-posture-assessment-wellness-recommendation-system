"""Extract MediaPipe landmarks from the supplementary video4 files.

These videos add extra real-world reps for the weakest classes identified
in model comparison.

File mapping
------------
baduanjin_video3_action1.mp4   action 1  rep 6
baduanjin_video3_action2.mp4   action 2  rep 6
baduanjin_video3_action3.mp4   action 3  rep 6
baduanjin_video3_action4.mp4   action 4  rep 6
baduanjin_video3_action5.mp4   action 5  rep 6
baduanjin_video3_action7.mp4   action 7  rep 6
baduanjin_video4_action7.mp4   action 7  rep 7
baduanjin_video5_action7.mp4   action 7  rep 8

Rep 5 for both actions already exists (video3 real-world data) and is used
as the --val-rep 5 validation split.  These new reps go into training.

Output: data/keypoints/video4_segments_landmarks.csv

Usage
-----
python data_preparation/process_video4_actions.py
python data_preparation/process_video4_actions.py --overwrite
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_segment import TasksPoseBackend, DEFAULT_POSE_MODEL, landmark_columns  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_VIDEO_DIR = PROJECT_ROOT / "data" / "raw_video"
FRAMES_DIR = PROJECT_ROOT / "data" / "frames" / "video4_actions"
OUTPUT_CSV = PROJECT_ROOT / "data" / "keypoints" / "video4_segments_landmarks.csv"

TARGET_FPS = 15.0

VIDEO4_ENTRIES: list[tuple[str, int, int]] = [
    ("baduanjin_video3_action1.mp4", 1, 6),
    ("baduanjin_video3_action2.mp4", 2, 6),
    ("baduanjin_video3_action3.mp4", 3, 6),
    ("baduanjin_video3_action4.mp4", 4, 6),
    ("baduanjin_video3_action5.mp4", 5, 6),
    ("baduanjin_video3_action7.mp4", 7, 6),
    ("baduanjin_video4_action7.mp4", 7, 7),
    ("baduanjin_video5_action7.mp4", 7, 8),
]


def _extract_and_detect(
    filename: str,
    action: int,
    rep: int,
    video_path: Path,
    frames_dir: Path,
    detector: TasksPoseBackend,
    overwrite: bool,
) -> list[list]:
    segment_label = f"video4_action{action:02d}_rep{rep:02d}"
    seg_frames_dir = frames_dir / f"action{action:02d}" / segment_label

    existing = sorted(seg_frames_dir.glob("*.jpg"))
    if existing and not overwrite:
        print(f"  Frames exist, skipping: {seg_frames_dir}")
        frame_paths = existing
    else:
        if overwrite:
            for f in existing:
                f.unlink()
        seg_frames_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if source_fps <= 0:
            source_fps = TARGET_FPS
        frame_step = max(1, round(source_fps / TARGET_FPS))

        frame_paths = []
        frame_index = 0
        saved_index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % frame_step == 0:
                out_path = seg_frames_dir / f"{segment_label}_frame{saved_index:05d}.jpg"
                cv2.imwrite(str(out_path), frame)
                frame_paths.append(out_path)
                saved_index += 1
            frame_index += 1
        cap.release()
        print(f"  {filename}: extracted {len(frame_paths)} frames -> action{action:02d} rep{rep:02d}")

    rows = []
    detected = 0
    for fi, fp in enumerate(frame_paths):
        img_bgr = cv2.imread(str(fp))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        features = detector.detect(img_rgb)

        row = [action, rep, segment_label, fi, str(fp)]
        if features:
            row.extend([True, *features])
            detected += 1
        else:
            row.extend([False] + [""] * 132)
        rows.append(row)

    print(f"  {filename}: {detected}/{len(frame_paths)} frames with pose detected")
    return rows


def run(
    pose_model: Path = DEFAULT_POSE_MODEL,
    overwrite: bool = False,
) -> None:
    if OUTPUT_CSV.exists() and not overwrite:
        print(f"Output CSV already exists (use --overwrite to regenerate): {OUTPUT_CSV}")
        return

    detector = TasksPoseBackend(model_path=pose_model, min_detection_confidence=0.5)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    header = ["action", "rep", "segment", "frame_index", "frame_path",
              "pose_detected", *landmark_columns()]

    total_rows = 0
    try:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for filename, action, rep in VIDEO4_ENTRIES:
                video_path = RAW_VIDEO_DIR / filename
                if not video_path.exists():
                    print(f"  WARNING: not found, skipping: {video_path}")
                    continue
                rows = _extract_and_detect(filename, action, rep, video_path,
                                           FRAMES_DIR, detector, overwrite)
                writer.writerows(rows)
                total_rows += len(rows)
    finally:
        detector.close()

    print(f"\nSaved {total_rows} rows -> {OUTPUT_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract landmarks from supplementary video4 files.")
    parser.add_argument("--pose-model", type=Path, default=DEFAULT_POSE_MODEL)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    run(pose_model=args.pose_model, overwrite=args.overwrite)
