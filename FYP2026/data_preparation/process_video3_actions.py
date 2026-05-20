"""Extract MediaPipe landmarks from the real-world video3 per-action files.

File mapping  (baduanjin_video_action*.mp4  ->  action, rep)
----------------------------------------------------------------
baduanjin_video_action1.mp4        action 1  rep 5
baduanjin_video_action2.mp4        action 2  rep 5
baduanjin_video_action3.mp4        action 3  rep 5
baduanjin_video_action4.mp4        action 4  rep 5
baduanjin_video_action5.mp4        action 5  rep 5
baduanjin_video_action6.mp4        action 6  rep 6
baduanjin_video_action6_rep2.mp4   action 6  rep 7   (extra rep)
baduanjin_video_action7.mp4        action 7  rep 5
baduanjin_video_action8.mp4        action 8  rep 5
baduanjin_video_action8_rep2.mp4   action 8  rep 6   (extra rep)

Existing reps after video01 + video2:
  actions 1-5, 7: reps 1-4
  action 6:       reps 1-5
  action 8:       reps 1-4

Output: data/keypoints/video3_segments_landmarks.csv

Usage
-----
python data_preparation/process_video3_actions.py
python data_preparation/process_video3_actions.py --overwrite
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
FRAMES_DIR = PROJECT_ROOT / "data" / "frames" / "video3_actions"
OUTPUT_CSV = PROJECT_ROOT / "data" / "keypoints" / "video3_segments_landmarks.csv"

TARGET_FPS = 15.0

# (filename, action_number, rep_number)
VIDEO3_ENTRIES: list[tuple[str, int, int]] = [
    ("baduanjin_video_action1.mp4",      1, 5),
    ("baduanjin_video_action2.mp4",      2, 5),
    ("baduanjin_video_action3.mp4",      3, 5),
    ("baduanjin_video_action4.mp4",      4, 5),
    ("baduanjin_video_action5.mp4",      5, 5),
    ("baduanjin_video_action6.mp4",      6, 6),
    ("baduanjin_video_action6_rep2.mp4", 6, 7),
    ("baduanjin_video_action7.mp4",      7, 5),
    ("baduanjin_video_action8.mp4",      8, 5),
    ("baduanjin_video_action8_rep2.mp4", 8, 6),
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
    segment_label = f"video3_action{action:02d}_rep{rep:02d}"
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

            for filename, action, rep in VIDEO3_ENTRIES:
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
    parser = argparse.ArgumentParser(description="Extract landmarks from real-world video3 per-action files.")
    parser.add_argument("--pose-model", type=Path, default=DEFAULT_POSE_MODEL)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    run(pose_model=args.pose_model, overwrite=args.overwrite)
