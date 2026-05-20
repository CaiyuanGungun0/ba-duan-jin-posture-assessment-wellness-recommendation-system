"""Model comparison: MLP vs Random Forest vs LinearSVC vs CNN vs LSTM.

All models use the same rep-based train/val split and class weights.
Results saved to models/comparison_results.json.

Usage
-----
python -m pose_module.model_comparison --manifest data/keypoints/action_manifest.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from sklearn.utils.class_weight import compute_class_weight

os_environ_set = False
try:
    import os
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    import tensorflow as tf
    tf.get_logger().setLevel("ERROR")
    import keras
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False

try:
    from .train_pose_model import load_dataset_manifest, _load_by_rep, _build_windows_for_rep
    from .feature_engineering import make_window_features, make_window_features_seq
    from .pose_model import PoseActionModel
    from .augmentation import augment_windows
except ImportError:
    from train_pose_model import load_dataset_manifest, _load_by_rep, _build_windows_for_rep
    from feature_engineering import make_window_features, make_window_features_seq
    from pose_model import PoseActionModel
    from augmentation import augment_windows

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = PROJECT_ROOT / "models" / "comparison_results.json"
MODELS_DIR = PROJECT_ROOT / "models" / "comparison"

FEATURES_PER_FRAME = 107  # 99 xyz + 8 angles


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(
    manifest: dict[str, str],
    sequence_length: int,
    stride: int,
    val_rep: str | int,
    augment: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Return flat (N, T*107) and sequential (N, T, 107) arrays for train/val.

    augment: if True, training windows are tripled with flip + time-stretch.
    """
    labels = sorted(manifest)
    flat_tr, flat_vl, seq_tr, seq_vl = [], [], [], []
    y_tr, y_vl = [], []

    for li, label in enumerate(labels):
        reps = _load_by_rep(manifest[label])
        rep_nums = sorted(reps)
        held = rep_nums[-1] if val_rep == "last" else int(val_rep)

        for rn, kp in reps.items():
            wins = _build_windows_for_rep(kp, sequence_length, stride)
            if not len(wins):
                continue

            if rn == held:
                flat_feats = np.stack([make_window_features(w) for w in wins])
                seq_feats  = np.stack([make_window_features_seq(w) for w in wins])
                tgts = np.full(len(wins), li, dtype=np.int64)
                flat_vl.append(flat_feats); seq_vl.append(seq_feats); y_vl.append(tgts)
            else:
                if augment:
                    wins = augment_windows(wins, flip=True, stretch=True)
                flat_feats = np.stack([make_window_features(w) for w in wins])
                seq_feats  = np.stack([make_window_features_seq(w) for w in wins])
                tgts = np.full(len(wins), li, dtype=np.int64)
                flat_tr.append(flat_feats); seq_tr.append(seq_feats); y_tr.append(tgts)

    return (
        np.concatenate(flat_tr), np.concatenate(y_tr),
        np.concatenate(flat_vl), np.concatenate(y_vl),
        labels,
    ), np.concatenate(seq_tr), np.concatenate(seq_vl)


def class_weights(y: np.ndarray) -> dict[int, float]:
    cw = compute_class_weight("balanced", classes=np.unique(y), y=y)
    return dict(enumerate(cw))


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def per_class_accuracy(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> dict[str, float]:
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
    result = {}
    for i, label in enumerate(labels):
        total = cm[i].sum()
        result[label] = round(float(cm[i, i] / total), 4) if total > 0 else 0.0
    return result


def overall_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return round(float((y_true == y_pred).mean()), 4)


def print_comparison_table(results: list[dict]) -> None:
    labels = list(results[0]["per_class"].keys())
    col_w = 10
    header = f"{'Model':<14}" + "".join(f"{l[-2:]:>{col_w}}" for l in labels) + f"{'Overall':>{col_w}}"
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for r in results:
        row = f"{r['model']:<14}"
        for l in labels:
            acc = r["per_class"].get(l, 0.0)
            row += f"{acc*100:>{col_w}.1f}"
        row += f"{r['overall']*100:>{col_w}.1f}"
        print(row)
    print("=" * len(header))
    print(f"{'':14}" + "".join(f"{l[-2:]:>{col_w}}" for l in labels) + f"{'Overall':>{col_w}}")
    print()


# ---------------------------------------------------------------------------
# MLP (NumPy baseline — same architecture as production model)
# ---------------------------------------------------------------------------

def train_mlp(
    x_tr: np.ndarray, y_tr: np.ndarray,
    x_vl: np.ndarray, y_vl: np.ndarray,
    labels: list[str],
    hidden: int = 256, epochs: int = 50, lr: float = 0.001, seed: int = 42,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    cw = class_weights(y_tr)
    mean = x_tr.mean(0, keepdims=True); std = x_tr.std(0, keepdims=True) + 1e-6
    xn = (x_tr - mean) / std
    nc = len(labels)
    w1 = rng.normal(0, np.sqrt(2 / x_tr.shape[1]), (x_tr.shape[1], hidden)).astype(np.float32)
    b1 = np.zeros(hidden, np.float32)
    w2 = rng.normal(0, np.sqrt(2 / hidden), (hidden, nc)).astype(np.float32)
    b2 = np.zeros(nc, np.float32)

    oh = np.zeros((len(y_tr), nc), np.float32)
    oh[np.arange(len(y_tr)), y_tr] = 1.0
    sample_w = np.array([cw[int(c)] for c in y_tr], dtype=np.float32)

    for _ in range(epochs):
        idx = rng.permutation(len(xn))
        for s in range(0, len(idx), 64):
            bi = idx[s:s+64]
            xb, yb, wb = xn[bi], oh[bi], sample_w[bi]
            z1 = xb @ w1 + b1; h = np.maximum(0, z1)
            lg = h @ w2 + b2; lg -= lg.max(1, keepdims=True)
            ex = np.exp(lg); pr = ex / ex.sum(1, keepdims=True)
            dl = (pr - yb) * wb[:, None] / len(bi)
            w2 -= lr * (h.T @ dl); b2 -= lr * dl.sum(0)
            dh = dl @ w2.T; dz = dh * (z1 > 0)
            w1 -= lr * (xb.T @ dz); b1 -= lr * dz.sum(0)

    xvn = (x_vl - mean) / std
    h = np.maximum(0, xvn @ w1 + b1)
    lg = h @ w2 + b2; lg -= lg.max(1, keepdims=True)
    ex = np.exp(lg)
    return np.argmax(ex / ex.sum(1, keepdims=True), axis=1)


# ---------------------------------------------------------------------------
# Random Forest
# ---------------------------------------------------------------------------

def train_rf(
    x_tr: np.ndarray, y_tr: np.ndarray, x_vl: np.ndarray,
) -> np.ndarray:
    cw = class_weights(y_tr)
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=None, class_weight=cw,
        n_jobs=-1, random_state=42,
    )
    rf.fit(x_tr, y_tr)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(rf, MODELS_DIR / "random_forest.pkl")
    return rf.predict(x_vl)


# ---------------------------------------------------------------------------
# LinearSVC
# ---------------------------------------------------------------------------

def train_svm(
    x_tr: np.ndarray, y_tr: np.ndarray, x_vl: np.ndarray,
) -> np.ndarray:
    scaler = StandardScaler()
    x_tr_s = scaler.fit_transform(x_tr)
    x_vl_s = scaler.transform(x_vl)
    cw = class_weights(y_tr)
    svm = LinearSVC(C=1.0, class_weight=cw, max_iter=5000, random_state=42)
    svm.fit(x_tr_s, y_tr)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump({"scaler": scaler, "svm": svm}, MODELS_DIR / "linear_svc.pkl")
    return svm.predict(x_vl_s)


# ---------------------------------------------------------------------------
# CNN (Keras)
# ---------------------------------------------------------------------------

def train_cnn(
    x_tr: np.ndarray, y_tr: np.ndarray,
    x_vl: np.ndarray, y_vl: np.ndarray,
    labels: list[str], epochs: int = 60,
) -> np.ndarray:
    nc = len(labels)
    cw = class_weights(y_tr)

    inputs = keras.Input(shape=(x_tr.shape[1], FEATURES_PER_FRAME))
    x = keras.layers.Conv1D(64, 3, padding="same", activation="relu")(inputs)
    x = keras.layers.MaxPooling1D(2)(x)
    x = keras.layers.Conv1D(128, 3, padding="same", activation="relu")(x)
    x = keras.layers.GlobalMaxPooling1D()(x)
    x = keras.layers.Dense(64, activation="relu")(x)
    x = keras.layers.Dropout(0.3)(x)
    outputs = keras.layers.Dense(nc, activation="softmax")(x)
    model = keras.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    cb = keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True, monitor="val_accuracy")
    model.fit(
        x_tr, y_tr,
        validation_data=(x_vl, y_vl),
        epochs=epochs, batch_size=32,
        class_weight=cw,
        callbacks=[cb],
        verbose=0,
    )
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(MODELS_DIR / "cnn_model.keras"))
    (MODELS_DIR / "cnn_model.json").write_text(
        json.dumps({"labels": labels, "sequence_length": x_tr.shape[1]}), encoding="utf-8"
    )
    return np.argmax(model.predict(x_vl, verbose=0), axis=1)


# ---------------------------------------------------------------------------
# LSTM (Keras)
# ---------------------------------------------------------------------------

def train_lstm(
    x_tr: np.ndarray, y_tr: np.ndarray,
    x_vl: np.ndarray, y_vl: np.ndarray,
    labels: list[str], epochs: int = 60,
) -> np.ndarray:
    nc = len(labels)
    cw = class_weights(y_tr)

    inputs = keras.Input(shape=(x_tr.shape[1], FEATURES_PER_FRAME))
    x = keras.layers.LSTM(128, return_sequences=True)(inputs)
    x = keras.layers.Dropout(0.3)(x)
    x = keras.layers.LSTM(64)(x)
    x = keras.layers.Dropout(0.3)(x)
    x = keras.layers.Dense(64, activation="relu")(x)
    outputs = keras.layers.Dense(nc, activation="softmax")(x)
    model = keras.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    cb = keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True, monitor="val_accuracy")
    model.fit(
        x_tr, y_tr,
        validation_data=(x_vl, y_vl),
        epochs=epochs, batch_size=32,
        class_weight=cw,
        callbacks=[cb],
        verbose=0,
    )
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(MODELS_DIR / "lstm_model.keras"))
    (MODELS_DIR / "lstm_model.json").write_text(
        json.dumps({"labels": labels, "sequence_length": x_tr.shape[1]}), encoding="utf-8"
    )
    return np.argmax(model.predict(x_vl, verbose=0), axis=1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_comparison(
    manifest: dict[str, str],
    sequence_length: int = 30,
    stride: int = 10,
    val_rep: str | int = "last",
    augment: bool = False,
) -> None:
    print("Loading data ...")
    (x_flat_tr, y_tr, x_flat_vl, y_vl, labels), x_seq_tr, x_seq_vl = load_data(
        manifest, sequence_length, stride, val_rep, augment=augment
    )
    print(f"Train: {len(y_tr)} windows | Val: {len(y_vl)} windows | Classes: {len(labels)}")
    print(f"Flat features: {x_flat_tr.shape[1]}  |  Seq features: {x_seq_tr.shape[1:]}\n")

    results = []

    def _run(name, fn, *args):
        print(f"Training {name} ...", end=" ", flush=True)
        t0 = time.time()
        preds = fn(*args)
        elapsed = time.time() - t0
        oa = overall_accuracy(y_vl, preds)
        pc = per_class_accuracy(y_vl, preds, labels)
        print(f"done in {elapsed:.1f}s  |  overall acc: {oa*100:.1f}%")
        results.append({"model": name, "overall": oa, "per_class": pc, "train_time_s": round(elapsed, 1)})

    _run("MLP",       train_mlp,  x_flat_tr, y_tr, x_flat_vl, y_vl, labels)
    _run("RF",        train_rf,   x_flat_tr, y_tr, x_flat_vl)
    _run("LinearSVC", train_svm,  x_flat_tr, y_tr, x_flat_vl)

    if KERAS_AVAILABLE:
        _run("CNN",  train_cnn,  x_seq_tr, y_tr, x_seq_vl, y_vl, labels)
        _run("LSTM", train_lstm, x_seq_tr, y_tr, x_seq_vl, y_vl, labels)
    else:
        print("Keras/TensorFlow not available — skipping CNN and LSTM.")

    print_comparison_table(results)

    best = max(results, key=lambda r: r["overall"])
    print(f"Best model: {best['model']}  ({best['overall']*100:.1f}% overall)\n")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "labels": labels,
        "sequence_length": sequence_length,
        "train_windows": int(len(y_tr)),
        "val_windows": int(len(y_vl)),
        "models": results,
        "best_model": best["model"],
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Results saved -> {RESULTS_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare ML models for Ba-Duan-Jin action classification.")
    parser.add_argument("--manifest", default="data/keypoints/action_manifest.json")
    parser.add_argument("--sequence-length", type=int, default=30)
    parser.add_argument("--stride", type=int, default=10)
    parser.add_argument("--val-rep", default="last")
    parser.add_argument("--augment", action="store_true",
                        help="Triple training data with flip + time-stretch augmentation.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    manifest = load_dataset_manifest(args.manifest)
    run_comparison(manifest, args.sequence_length, args.stride, args.val_rep, augment=args.augment)
