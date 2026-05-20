"""Visualize saved MediaPipe landmarks overlaid on extracted frames.

Reads landmark coordinates directly from the segments CSV — no pose
re-detection required, so it works regardless of MediaPipe version.

Usage
-----
# Save 2 annotated frames per action to data/viz_output/:
python data_preparation/visualize_landmarks.py

# Only action 3, 4 frames each:
python data_preparation/visualize_landmarks.py --action 3 --n 4

# Single frame by its path:
python data_preparation/visualize_landmarks.py --image data/frames/...jpg
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRAMES_DIR = PROJECT_ROOT / "data" / "frames" / "video01_segments"
DEFAULT_LANDMARKS_CSV = PROJECT_ROOT / "data" / "keypoints" / "video01_segments_landmarks.csv"
DEFAULT_SAVE_DIR = PROJECT_ROOT / "data" / "viz_output"

# Standard MediaPipe 33-landmark connections
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    (25, 27), (26, 28), (27, 29), (28, 30),
    (29, 31), (30, 32), (27, 31), (28, 32),
]

LANDMARK_COLS = [
    f"lm_{i}_{c}" for i in range(33) for c in ("x", "y", "z", "visibility")
]

MIN_VISIBILITY = 0.3


def _draw_landmarks(frame: np.ndarray, row: pd.Series) -> np.ndarray:
    out = frame.copy()
    h, w = out.shape[:2]

    # Parse all 33 landmarks from the row
    lm_x = [float(row[f"lm_{i}_x"]) for i in range(33)]
    lm_y = [float(row[f"lm_{i}_y"]) for i in range(33)]
    lm_v = [float(row[f"lm_{i}_visibility"]) for i in range(33)]

    # Draw skeleton connections
    for a, b in POSE_CONNECTIONS:
        if lm_v[a] < MIN_VISIBILITY or lm_v[b] < MIN_VISIBILITY:
            continue
        pt_a = (int(lm_x[a] * w), int(lm_y[a] * h))
        pt_b = (int(lm_x[b] * w), int(lm_y[b] * h))
        cv2.line(out, pt_a, pt_b, (0, 200, 100), 2, cv2.LINE_AA)

    # Draw landmark dots
    for i in range(33):
        if lm_v[i] < MIN_VISIBILITY:
            continue
        px, py = int(lm_x[i] * w), int(lm_y[i] * h)
        cv2.circle(out, (px, py), 4, (255, 255, 255), -1)
        cv2.circle(out, (px, py), 4, (0, 150, 255), 1)

    # Draw hip center (landmarks 23 & 24)
    if lm_v[23] >= MIN_VISIBILITY and lm_v[24] >= MIN_VISIBILITY:
        cx = int((lm_x[23] + lm_x[24]) / 2 * w)
        cy = int((lm_y[23] + lm_y[24]) / 2 * h)
        cv2.circle(out, (cx, cy), 8, (0, 255, 255), -1)
        cv2.putText(out, "hip center", (cx + 10, cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

    # Label
    label = f"action{int(row['action']):02d}  rep{int(row['rep']):02d}  frame{int(row['frame_index']):04d}"
    cv2.putText(out, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(out, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)

    return out


def run_visualization(
    landmarks_csv: Path,
    action: int | None,
    n_per_action: int,
    save_dir: Path,
    image_path: Path | None,
) -> None:
    df = pd.read_csv(landmarks_csv)
    df = df[df["pose_detected"].astype(str).str.lower() == "true"]

    if image_path is not None:
        # Single image: match by frame_path column
        match = df[df["frame_path"].str.endswith(image_path.name, na=False)]
        if match.empty:
            print(f"No landmark row found for {image_path.name}. Showing frame without overlay.")
            frame = cv2.imread(str(image_path))
            if frame is not None:
                _save(frame, image_path.stem, save_dir)
            return
        row = match.iloc[0]
        frame = cv2.imread(str(image_path))
        if frame is None:
            print(f"Could not read image: {image_path}")
            return
        annotated = _draw_landmarks(frame, row)
        _save(annotated, image_path.stem, save_dir)
        return

    actions = sorted(df["action"].unique())
    if action is not None:
        actions = [a for a in actions if int(a) == action]

    save_dir.mkdir(parents=True, exist_ok=True)
    total_saved = 0

    for act in actions:
        act_df = df[df["action"] == act]
        sample_rows = act_df.sample(n=min(n_per_action, len(act_df)), random_state=42)

        for _, row in sample_rows.iterrows():
            frame_path = Path(str(row["frame_path"]))
            if not frame_path.exists():
                print(f"Frame not found: {frame_path}")
                continue
            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue
            annotated = _draw_landmarks(frame, row)
            stem = f"action{int(act):02d}_frame{int(row['frame_index']):04d}"
            _save(annotated, stem, save_dir)
            total_saved += 1

    print(f"Saved {total_saved} annotated images to {save_dir}")


def _save(img: np.ndarray, stem: str, save_dir: Path) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / f"{stem}.jpg"
    cv2.imwrite(str(out_path), img)
    print(f"  Saved: {out_path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize MediaPipe landmarks from the segments CSV.")
    parser.add_argument("--landmarks-csv", type=Path, default=DEFAULT_LANDMARKS_CSV)
    parser.add_argument("--action", type=int, help="Visualize only this action number (1-8).")
    parser.add_argument("--n", type=int, default=2, help="Frames per action to annotate.")
    parser.add_argument("--save-dir", type=Path, default=DEFAULT_SAVE_DIR)
    parser.add_argument("--image", type=Path, help="Annotate a single specific frame.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_visualization(
        landmarks_csv=args.landmarks_csv,
        action=args.action,
        n_per_action=args.n,
        save_dir=args.save_dir,
        image_path=args.image,
    )
