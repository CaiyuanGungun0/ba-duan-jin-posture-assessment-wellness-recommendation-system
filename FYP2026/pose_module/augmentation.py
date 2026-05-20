"""Landmark-level augmentation for pose windows.

Two augmentations are implemented:

Horizontal flip
    Mirrors the pose left-right by negating the x coordinate (after hip-centering,
    x=0 is the body midline, so negating is a true mirror) and swapping every
    left/right MediaPipe landmark pair.  This doubles the effective training data
    for symmetric exercises and teaches the model that e.g. "left arm up" and
    "right arm up" are both valid instances of the same action.

Time stretch
    Randomly resamples the T-frame window to simulate the performer moving
    faster or slower.  A scale factor in scale_range=(0.7, 1.3) is drawn:
      scale < 1  -> compress  (sample fewer source frames -> fast movement)
      scale > 1  -> stretch   (sample more source frames -> slow movement)
    The result is always resampled back to T frames so the feature shape is
    unchanged.
"""
from __future__ import annotations

import numpy as np

# MediaPipe landmark left/right pairs (a, b) — swap a<->b during horizontal flip
_LR_PAIRS: list[tuple[int, int]] = [
    (1, 4),   # inner eye
    (2, 5),   # eye
    (3, 6),   # outer ear
    (7, 8),   # ear
    (9, 10),  # mouth corner
    (11, 12), # shoulder
    (13, 14), # elbow
    (15, 16), # wrist
    (17, 18), # pinky
    (19, 20), # index
    (21, 22), # thumb
    (23, 24), # hip
    (25, 26), # knee
    (27, 28), # ankle
    (29, 30), # heel
    (31, 32), # foot index
]


def flip_window(window: np.ndarray) -> np.ndarray:
    """Return a horizontally mirrored copy of *window* [T, 33, 4].

    After hip-centering in normalize_pose, x=0 is the body midline, so
    negating x produces a true left-right mirror without re-centering.
    Landmark pairs are swapped so that e.g. index 11 (left shoulder) gets
    the data that was at index 12 (right shoulder) and vice versa.
    """
    flipped = window.copy()
    flipped[:, :, 0] *= -1.0  # negate x for all landmarks
    for a, b in _LR_PAIRS:
        flipped[:, [a, b]] = flipped[:, [b, a]]
    return flipped


def time_stretch_window(
    window: np.ndarray,
    rng: np.random.Generator,
    scale_range: tuple[float, float] = (0.7, 1.3),
) -> np.ndarray:
    """Return a time-stretched copy of *window* [T, 33, 4].

    A random scale in *scale_range* determines how many source frames are
    sampled.  The result is nearest-neighbour resampled back to T frames.
    scale < 1 compresses (fast movement); scale > 1 stretches (slow movement).
    """
    T = len(window)
    scale = float(rng.uniform(scale_range[0], scale_range[1]))
    src_len = max(int(round(T * scale)), 2)

    # Sample src_len evenly spaced indices from the original T frames
    src_indices = np.round(np.linspace(0, T - 1, src_len)).astype(np.int32)
    src_frames = window[src_indices]  # [src_len, 33, 4]

    # Resample src_frames back to T frames
    out_indices = np.round(np.linspace(0, src_len - 1, T)).astype(np.int32)
    return src_frames[out_indices]


def augment_windows(
    windows: np.ndarray,
    flip: bool = True,
    stretch: bool = True,
    seed: int | None = None,
) -> np.ndarray:
    """Return *windows* concatenated with augmented copies.

    With both flip and stretch enabled, output size is 3× the input.
    Augmented windows preserve the same [N, T, 33, 4] layout.
    Only call on TRAINING windows — never on validation windows.
    """
    rng = np.random.default_rng(seed)
    parts = [windows]

    if flip:
        parts.append(np.stack([flip_window(w) for w in windows]))

    if stretch:
        parts.append(np.stack([time_stretch_window(w, rng) for w in windows]))

    return np.concatenate(parts, axis=0)
