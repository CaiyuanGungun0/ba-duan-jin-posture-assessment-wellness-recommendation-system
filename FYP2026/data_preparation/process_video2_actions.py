"""Extract MediaPipe landmarks from per-action video2 files.

Each file baduanjin_video2_actionN.mp4 is a single continuous recording of one action.
No timestamp segmentation is needed — the whole video is one action, one rep.

Output: data/keypoints/video2_segments_landmarks.csv
        Same column schema as video01_segments_landmarks.csv so that
        prepare_action_csvs.py can merge both sources.

Usage
-----
python data_preparation/process_video2_actions.py
python data_preparation/process_video2_actions.py --overwrite
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2

# Allow importing sibling module video_segment from the same folder
sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_segment import TasksPoseBackend, DEFAULT_POSE_MODEL, landmark_columns  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_VIDEO_DIR = PROJECT_ROOT / "data" / "raw_video"
FRAMES_DIR = PROJECT_ROOT / "data" / "frames" / "video2_actions"
OUTPUT_CSV = PROJECT_ROOT / "data" / "keypoints" / "video2_segments_landmarks.csv"

# video01 has reps 1-3 for most actions; action06 has reps 1-4.
# Assign video02 as the next available rep so there is no overlap.
_VIDEO2_REP: dict[int, int] = {1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 5, 7: 4, 8: 4}

TARGET_FPS = 15.0


def _extract_and_detect(
    action: int,
    video_path: Path,
    frames_dir: Path,
    detector: TasksPoseBackend,
    overwrite: bool,
) -> list[list]:
    """Extract frames + landmarks for one action video. Returns list of CSV rows."""
    rep = _VIDEO2_REP[action]
    segment_label = f"video2_action{action:02d}_rep{rep:02d}"
    seg_frames_dir = frames_dir / f"action{action:02d}" / segment_label

    existing = sorted(seg_frames_dir.glob("*.jpg"))
    if existing and not overwrite:
        print(f"  Frames exist, skipping extraction: {seg_frames_dir}")
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
        print(f"  action{action:02d}: extracted {len(frame_paths)} frames -> {seg_frames_dir}")

    # Run landmark detection on each frame
    rows = []
    detected = 0
    for fi, fp in enumerate(frame_paths):
        img_bgr = cv2.imread(str(fp))
        if img_bgr is None:
            print(f"    Could not read frame: {fp}")
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

    print(f"  action{action:02d}: {detected}/{len(frame_paths)} frames with pose detected")
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

            for action in range(1, 9):
                video_path = RAW_VIDEO_DIR / f"baduanjin_video2_action{action}.mp4"
                if not video_path.exists():
                    print(f"  WARNING: video not found, skipping action{action}: {video_path}")
                    continue
                print(f"Processing action{action:02d} ...")
                rows = _extract_and_detect(action, video_path, FRAMES_DIR, detector, overwrite)
                writer.writerows(rows)
                total_rows += len(rows)
    finally:
        detector.close()

    print(f"\nSaved {total_rows} rows -> {OUTPUT_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract landmarks from video2 per-action files.")
    parser.add_argument("--pose-model", type=Path, default=DEFAULT_POSE_MODEL)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    run(pose_model=args.pose_model, overwrite=args.overwrite)
