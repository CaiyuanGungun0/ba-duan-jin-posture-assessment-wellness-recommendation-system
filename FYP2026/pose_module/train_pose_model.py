from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .pose_model import PoseActionModel, make_window_features
    from .augmentation import augment_windows
except ImportError:
    from pose_model import PoseActionModel, make_window_features
    from augmentation import augment_windows

LANDMARK_COLS = [f"lm_{i}_{c}" for i in range(33) for c in ("x", "y", "z", "visibility")]

DEFAULT_DATASET = {
    "video01": "data/keypoints/video01_keypoints.csv",
    "video02": "data/keypoints/video02_keypoints.csv",
}


def load_dataset_manifest(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return DEFAULT_DATASET
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    if isinstance(data, list):
        return {str(item["label"]): str(item["keypoints"]) for item in data}
    raise ValueError("Dataset manifest must be a dict or list of {label, keypoints} objects.")


def _load_by_rep(csv_path: str | Path) -> dict[int, np.ndarray]:
    """Load a per-action CSV and return a dict mapping rep → landmark array [F, 33, 4]."""
    df = pd.read_csv(csv_path)

    if "rep" not in df.columns:
        # Legacy CSV with no rep column — treat everything as rep 1
        values = df[LANDMARK_COLS].to_numpy(dtype=np.float32)
        return {1: values.reshape(-1, 33, 4)}

    result: dict[int, np.ndarray] = {}
    for rep, group in df.groupby("rep"):
        values = group[LANDMARK_COLS].to_numpy(dtype=np.float32)
        result[int(rep)] = values.reshape(-1, 33, 4)
    return result


def _build_windows_for_rep(
    keypoints: np.ndarray,
    sequence_length: int,
    stride: int,
) -> np.ndarray:
    """Slide a window across one rep's frames. Never crosses rep boundaries."""
    windows = []
    for start in range(0, len(keypoints) - sequence_length + 1, stride):
        windows.append(keypoints[start: start + sequence_length])
    return np.asarray(windows, dtype=np.float32) if windows else np.empty((0, sequence_length, 33, 4), dtype=np.float32)


def make_features_rep_split(
    manifest: dict[str, str],
    sequence_length: int,
    stride: int,
    val_rep: int | str,
    augment: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Build train/val feature arrays using a rep-based split.

    val_rep: the rep number to hold out, or 'last' to always use the final rep.
    augment: if True, training windows are tripled with horizontal-flip and
             time-stretch copies (validation windows are never augmented).
    Windows never span rep boundaries.
    """
    labels = sorted(manifest)
    x_train, y_train, x_val, y_val = [], [], [], []

    for label_idx, label in enumerate(labels):
        reps_by_num = _load_by_rep(manifest[label])
        rep_nums = sorted(reps_by_num)

        held_out = rep_nums[-1] if val_rep == "last" else int(val_rep)
        if held_out not in rep_nums:
            raise ValueError(f"{label}: rep {held_out} not found; available reps: {rep_nums}")

        train_windows, val_windows = 0, 0
        for rep_num, keypoints in reps_by_num.items():
            windows = _build_windows_for_rep(keypoints, sequence_length, stride)
            if len(windows) == 0:
                print(f"  {label} rep{rep_num}: too short for a single window, skipped")
                continue

            if rep_num == held_out:
                features = np.stack([make_window_features(w) for w in windows])
                targets = np.full(len(features), label_idx, dtype=np.int64)
                x_val.append(features)
                y_val.append(targets)
                val_windows += len(features)
            else:
                if augment:
                    windows = augment_windows(windows, flip=True, stretch=True)
                features = np.stack([make_window_features(w) for w in windows])
                targets = np.full(len(features), label_idx, dtype=np.int64)
                x_train.append(features)
                y_train.append(targets)
                train_windows += len(features)

        aug_note = " (aug x3)" if augment else ""
        print(f"{label}: train={train_windows}{aug_note} windows (reps {[r for r in rep_nums if r != held_out]}), "
              f"val={val_windows} windows (rep {held_out})")

    if not x_train or not x_val:
        raise ValueError("Train or val set is empty. Check sequence_length vs available frames.")

    return (
        np.concatenate(x_train),
        np.concatenate(y_train),
        np.concatenate(x_val),
        np.concatenate(y_val),
        labels,
    )


def one_hot(y: np.ndarray, class_count: int) -> np.ndarray:
    encoded = np.zeros((len(y), class_count), dtype=np.float32)
    encoded[np.arange(len(y)), y] = 1.0
    return encoded


def accuracy(probs: np.ndarray, y: np.ndarray) -> float:
    return float((np.argmax(probs, axis=1) == y).mean())


def train_mlp(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    labels: list[str],
    sequence_length: int,
    hidden_size: int,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
) -> tuple[PoseActionModel, dict]:
    rng = np.random.default_rng(seed)
    mean = x_train.mean(axis=0, keepdims=True)
    std = x_train.std(axis=0, keepdims=True) + 1e-6
    x_train_n = (x_train - mean) / std
    x_val_n = (x_val - mean) / std

    input_size = x_train_n.shape[1]
    class_count = len(labels)
    w1 = rng.normal(0.0, np.sqrt(2.0 / input_size), (input_size, hidden_size)).astype(np.float32)
    b1 = np.zeros(hidden_size, dtype=np.float32)
    w2 = rng.normal(0.0, np.sqrt(2.0 / hidden_size), (hidden_size, class_count)).astype(np.float32)
    b2 = np.zeros(class_count, dtype=np.float32)

    y_oh = one_hot(y_train, class_count)

    for epoch in range(1, epochs + 1):
        idx = rng.permutation(len(x_train_n))
        epoch_loss = 0.0

        for start in range(0, len(idx), batch_size):
            xb = x_train_n[idx[start: start + batch_size]]
            yb = y_oh[idx[start: start + batch_size]]

            z1 = xb @ w1 + b1
            h = np.maximum(0.0, z1)
            logits = h @ w2 + b2
            logits -= logits.max(axis=1, keepdims=True)
            exp = np.exp(logits)
            probs = exp / exp.sum(axis=1, keepdims=True)

            loss = -np.sum(yb * np.log(probs + 1e-8)) / len(xb)
            epoch_loss += float(loss) * len(xb)

            dl = (probs - yb) / len(xb)
            w2 -= learning_rate * (h.T @ dl)
            b2 -= learning_rate * dl.sum(axis=0)
            dh = dl @ w2.T
            dz1 = dh * (z1 > 0)
            w1 -= learning_rate * (xb.T @ dz1)
            b1 -= learning_rate * dz1.sum(axis=0)

        model = PoseActionModel(labels, mean, std, w1, b1, w2, b2, sequence_length)
        train_acc = accuracy(model.predict_proba(x_train), y_train)
        val_acc = accuracy(model.predict_proba(x_val), y_val)
        print(f"epoch {epoch:03d} | loss {epoch_loss / len(x_train_n):.4f} "
              f"| train_acc {train_acc:.3f} | val_acc {val_acc:.3f}")

    model = PoseActionModel(labels, mean, std, w1, b1, w2, b2, sequence_length)
    metrics = {
        "train_accuracy": round(accuracy(model.predict_proba(x_train), y_train), 4),
        "val_accuracy": round(accuracy(model.predict_proba(x_val), y_val), 4),
        "train_windows": int(len(y_train)),
        "val_windows": int(len(y_val)),
        "classes": int(len(labels)),
        "val_split": "rep-based",
    }
    return model, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a pose action classifier from keypoint CSV files.")
    parser.add_argument("--manifest", help="JSON mapping label names to keypoint CSV files.")
    parser.add_argument("--output", default="models/pose/pose_action_model.npz")
    parser.add_argument("--metrics-output", default="models/pose/pose_action_metrics.json")
    parser.add_argument("--sequence-length", type=int, default=30)
    parser.add_argument("--stride", type=int, default=10)
    parser.add_argument("--val-rep", default="last",
                        help="Rep number to hold out for validation, or 'last' (default).")
    parser.add_argument("--augment", action="store_true",
                        help="Triple training data with flip + time-stretch augmentation.")
    parser.add_argument("--hidden-size", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_dataset_manifest(args.manifest)
    if len(manifest) < 2:
        raise ValueError("Training needs at least two labeled classes.")

    val_rep = args.val_rep if args.val_rep == "last" else int(args.val_rep)

    x_train, y_train, x_val, y_val, labels = make_features_rep_split(
        manifest=manifest,
        sequence_length=args.sequence_length,
        stride=args.stride,
        val_rep=val_rep,
        augment=args.augment,
    )

    print(f"\nTrain: {len(y_train)} windows | Val: {len(y_val)} windows | Classes: {len(labels)}\n")

    model, metrics = train_mlp(
        x_train=x_train,
        y_train=y_train,
        x_val=x_val,
        y_val=y_val,
        labels=labels,
        sequence_length=args.sequence_length,
        hidden_size=args.hidden_size,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )

    model.save(args.output)
    metrics_path = Path(args.metrics_output)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps({"labels": labels, **metrics}, indent=2), encoding="utf-8")
    print(f"\nSaved model    -> {args.output}")
    print(f"Saved metrics  -> {metrics_path}")


if __name__ == "__main__":
    main()
