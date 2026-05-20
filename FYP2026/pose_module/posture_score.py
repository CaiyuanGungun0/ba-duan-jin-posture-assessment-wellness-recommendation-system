from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


LANDMARK_COUNT = 33
VALUES_PER_LANDMARK = 4
MIN_VISIBILITY = 0.35

POSE_REGIONS: dict[str, tuple[int, ...]] = {
    "head": (0, 1, 2, 3, 4, 5, 6, 7, 8),
    "shoulders": (11, 12),
    "arms": (13, 14, 15, 16, 17, 18, 19, 20),
    "torso": (11, 12, 23, 24),
    "hips": (23, 24),
    "legs": (25, 26, 27, 28, 29, 30, 31, 32),
}

ADVICE_BY_REGION = {
    "head": "Keep your head upright and gaze forward.",
    "shoulders": "Relax and level both shoulders.",
    "arms": "Match the reference arm height and keep the elbows controlled.",
    "torso": "Lengthen your spine and avoid leaning too far forward or sideways.",
    "hips": "Keep your hips centered and stable.",
    "legs": "Adjust your stance width and knee bend to match the reference.",
}


@dataclass(frozen=True)
class PoseScore:
    accuracy: float
    mean_distance: float
    region_scores: dict[str, float]
    advice: list[str]
    visible_landmarks: int


def load_reference_keypoints(path: str | Path) -> np.ndarray:
    """Load MediaPipe pose keypoints saved as 33 landmarks x [x, y, z, visibility]."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Reference keypoint file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    numeric_df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    values = numeric_df.to_numpy(dtype=np.float32)

    expected = LANDMARK_COUNT * VALUES_PER_LANDMARK
    if values.ndim != 2 or values.shape[1] < expected:
        raise ValueError(
            f"Expected at least {expected} columns in {csv_path}, found {values.shape[1] if values.ndim == 2 else 0}."
        )
    return values[:, :expected].reshape((-1, LANDMARK_COUNT, VALUES_PER_LANDMARK))


def landmarks_to_array(landmarks: Iterable) -> np.ndarray:
    rows = []
    for landmark in landmarks:
        rows.append([landmark.x, landmark.y, landmark.z,
                     landmark.visibility if landmark.visibility is not None else 0.0])
    arr = np.asarray(rows, dtype=np.float32)
    if arr.shape != (LANDMARK_COUNT, VALUES_PER_LANDMARK):
        raise ValueError(f"Expected {LANDMARK_COUNT} landmarks, found shape {arr.shape}.")
    return arr


def _normalization_scale(points: np.ndarray) -> float:
    left_shoulder = points[11, :2]
    right_shoulder = points[12, :2]
    left_hip = points[23, :2]
    right_hip = points[24, :2]

    shoulder_width = float(np.linalg.norm(left_shoulder - right_shoulder))
    torso_height = float(np.linalg.norm(((left_shoulder + right_shoulder) / 2) - ((left_hip + right_hip) / 2)))
    scale = max(shoulder_width, torso_height, 1e-4)
    return scale


def normalize_pose(points: np.ndarray) -> np.ndarray:
    """Center pose on hips and scale by shoulder/torso size for person-size invariance."""
    normalized = points.copy().astype(np.float32)
    hip_center = (normalized[23, :3] + normalized[24, :3]) / 2
    scale = _normalization_scale(normalized)
    normalized[:, :3] = (normalized[:, :3] - hip_center) / scale
    return normalized


def _score_from_distance(distance: float, tolerance: float) -> float:
    return float(np.clip(100.0 * (1.0 - distance / tolerance), 0.0, 100.0))


def _visible_mask(user_pose: np.ndarray, reference_pose: np.ndarray) -> np.ndarray:
    return (user_pose[:, 3] >= MIN_VISIBILITY) & (reference_pose[:, 3] >= MIN_VISIBILITY)


def compare_pose(
    user_pose: np.ndarray,
    reference_pose: np.ndarray,
    tolerance: float = 0.75,
) -> PoseScore:
    """Compare two MediaPipe poses and return an overall score plus region advice."""
    if user_pose.shape != (LANDMARK_COUNT, VALUES_PER_LANDMARK):
        raise ValueError(f"user_pose must have shape {(LANDMARK_COUNT, VALUES_PER_LANDMARK)}")
    if reference_pose.shape != (LANDMARK_COUNT, VALUES_PER_LANDMARK):
        raise ValueError(f"reference_pose must have shape {(LANDMARK_COUNT, VALUES_PER_LANDMARK)}")

    user_norm = normalize_pose(user_pose)
    ref_norm = normalize_pose(reference_pose)
    visible = _visible_mask(user_pose, reference_pose)

    if int(visible.sum()) < 8:
        return PoseScore(
            accuracy=0.0,
            mean_distance=float("inf"),
            region_scores={},
            advice=["Move fully into the camera frame so your whole body is visible."],
            visible_landmarks=int(visible.sum()),
        )

    distances = np.linalg.norm(user_norm[:, :3] - ref_norm[:, :3], axis=1)
    mean_distance = float(distances[visible].mean())
    accuracy = _score_from_distance(mean_distance, tolerance)

    region_scores: dict[str, float] = {}
    advice: list[str] = []
    for region, indices in POSE_REGIONS.items():
        region_idx = np.asarray(indices, dtype=np.int64)
        region_visible = visible[region_idx]
        if not region_visible.any():
            continue
        region_distance = float(distances[region_idx][region_visible].mean())
        region_score = _score_from_distance(region_distance, tolerance)
        region_scores[region] = round(region_score, 1)
        if region_score < 70:
            advice.append(ADVICE_BY_REGION[region])

    if not advice:
        advice.append("Good alignment. Keep the movement slow, steady, and relaxed.")

    return PoseScore(
        accuracy=round(accuracy, 1),
        mean_distance=round(mean_distance, 4),
        region_scores=region_scores,
        advice=advice[:3],
        visible_landmarks=int(visible.sum()),
    )
