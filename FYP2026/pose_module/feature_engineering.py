from __future__ import annotations

import numpy as np

try:
    from .posture_score import normalize_pose
except ImportError:
    from posture_score import normalize_pose


JOINT_ANGLE_NAMES: list[str] = [
    "left_elbow",    # left shoulder → elbow → wrist
    "right_elbow",
    "left_shoulder", # left hip → shoulder → elbow
    "right_shoulder",
    "left_knee",     # left hip → knee → ankle
    "right_knee",
    "left_hip",      # left shoulder → hip → knee
    "right_hip",
]

# Each tuple is (point_a_idx, vertex_idx, point_b_idx)
_ANGLE_TRIPLES: list[tuple[int, int, int]] = [
    (11, 13, 15),
    (12, 14, 16),
    (23, 11, 13),
    (24, 12, 14),
    (23, 25, 27),
    (24, 26, 28),
    (11, 23, 25),
    (12, 24, 26),
]


def _angle_deg(a: np.ndarray, vertex: np.ndarray, b: np.ndarray) -> float:
    """Angle in degrees at *vertex* between rays vertex→a and vertex→b (uses xyz only)."""
    va = a[:3] - vertex[:3]
    vb = b[:3] - vertex[:3]
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0
    cos_theta = float(np.dot(va, vb) / (norm_a * norm_b))
    return float(np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0))))


def compute_joint_angles(frame: np.ndarray) -> np.ndarray:
    """Return joint angles (degrees) for one pose frame of shape [33, 4].

    Returns an array of shape [8] in the order defined by JOINT_ANGLE_NAMES.
    Angles are computed on raw (un-normalized) coordinates so they reflect true
    3-D joint bend regardless of body position in the frame.
    """
    angles = np.zeros(len(_ANGLE_TRIPLES), dtype=np.float32)
    for i, (ai, vi, bi) in enumerate(_ANGLE_TRIPLES):
        angles[i] = _angle_deg(frame[ai], frame[vi], frame[bi])
    return angles


def make_frame_features(frame: np.ndarray) -> np.ndarray:
    """Per-frame feature vector of shape [107]: 99 normalised xyz + 8 joint angles."""
    normalized_xyz = normalize_pose(frame)[:, :3].reshape(-1)  # (99,)
    angles = compute_joint_angles(frame) / 180.0               # (8,) scaled to [0,1]
    return np.concatenate([normalized_xyz, angles]).astype(np.float32)


def make_window_features_seq(window: np.ndarray) -> np.ndarray:
    """Return shape [T, 107] — preserves time axis for CNN / LSTM input."""
    return np.stack([make_frame_features(frame) for frame in window]).astype(np.float32)


def make_window_features(window: np.ndarray) -> np.ndarray:
    """Flatten [T, 33, 4] window into a 1-D vector of shape [T*107] for MLP/RF/SVM."""
    return make_window_features_seq(window).reshape(-1)
