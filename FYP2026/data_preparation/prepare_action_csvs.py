"""Merge landmark CSVs from all video sources into one CSV per action for training.

Sources merged (if they exist):
  data/keypoints/video01_segments_landmarks.csv   (3 reps per action)
  data/keypoints/video2_segments_landmarks.csv    (1 extra rep per action)

Run process_video2_actions.py first to generate the video2 CSV.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIDEO1_CSV = PROJECT_ROOT / "data" / "keypoints" / "video01_segments_landmarks.csv"
VIDEO2_CSV = PROJECT_ROOT / "data" / "keypoints" / "video2_segments_landmarks.csv"
VIDEO3_CSV = PROJECT_ROOT / "data" / "keypoints" / "video3_segments_landmarks.csv"
VIDEO4_CSV = PROJECT_ROOT / "data" / "keypoints" / "video4_segments_landmarks.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "keypoints" / "per_action"
MANIFEST_PATH = PROJECT_ROOT / "data" / "keypoints" / "action_manifest.json"

LANDMARK_COLS = [
    f"lm_{i}_{c}" for i in range(33) for c in ("x", "y", "z", "visibility")
]
OUTPUT_COLS = ["rep"] + LANDMARK_COLS


def _load_detected(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    detected = df[df["pose_detected"].astype(str).str.lower() == "true"].copy()
    print(f"  {csv_path.name}: {len(df)} rows, {len(detected)} with pose ({len(detected)/len(df)*100:.1f}%)")
    return detected


def main() -> None:
    sources: list[pd.DataFrame] = []

    print("Loading landmark sources ...")
    sources.append(_load_detected(VIDEO1_CSV))

    if VIDEO2_CSV.exists():
        sources.append(_load_detected(VIDEO2_CSV))
    else:
        print(f"  {VIDEO2_CSV.name}: not found — run process_video2_actions.py to add video2 data")

    if VIDEO3_CSV.exists():
        sources.append(_load_detected(VIDEO3_CSV))
    else:
        print(f"  {VIDEO3_CSV.name}: not found — run process_video3_actions.py to add video3 data")

    if VIDEO4_CSV.exists():
        sources.append(_load_detected(VIDEO4_CSV))
    else:
        print(f"  {VIDEO4_CSV.name}: not found — run process_video4_actions.py to add video4 data")

    detected = pd.concat(sources, ignore_index=True)
    print(f"Combined: {len(detected)} frames with pose detected")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}

    for action in sorted(detected["action"].unique()):
        action_df = detected[detected["action"] == action][OUTPUT_COLS]
        out_path = OUTPUT_DIR / f"action{int(action):02d}_keypoints.csv"
        action_df.to_csv(out_path, index=False)
        label = f"action{int(action):02d}"
        manifest[label] = str(out_path)
        reps = sorted(action_df["rep"].unique())
        print(f"  {label}: {len(action_df)} frames, reps {reps} -> {out_path.name}")

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest saved to {MANIFEST_PATH}")
    print("Tip: use --val-rep last to validate on video2 reps (cross-video), "
          "or --val-rep 3 to validate on video01 last rep only.")


if __name__ == "__main__":
    main()
