from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from .feature_engineering import make_window_features, make_window_features_seq
except ImportError:
    from feature_engineering import make_window_features, make_window_features_seq


@dataclass(frozen=True)
class PoseModelPrediction:
    label: str
    confidence: float
    probabilities: dict[str, float]


class PoseActionModel:
    """Small MLP classifier trained on MediaPipe pose-keypoint windows."""

    def __init__(
        self,
        labels: list[str],
        mean: np.ndarray,
        std: np.ndarray,
        w1: np.ndarray,
        b1: np.ndarray,
        w2: np.ndarray,
        b2: np.ndarray,
        sequence_length: int,
    ) -> None:
        self.labels = labels
        self.mean = mean
        self.std = std
        self.w1 = w1
        self.b1 = b1
        self.w2 = w2
        self.b2 = b2
        self.sequence_length = sequence_length

    @classmethod
    def load(cls, path: str | Path) -> "PoseActionModel":
        data = np.load(path, allow_pickle=True)
        return cls(
            labels=[str(label) for label in data["labels"]],
            mean=data["mean"],
            std=data["std"],
            w1=data["w1"],
            b1=data["b1"],
            w2=data["w2"],
            b2=data["b2"],
            sequence_length=int(data["sequence_length"]),
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            labels=np.asarray(self.labels),
            mean=self.mean,
            std=self.std,
            w1=self.w1,
            b1=self.b1,
            w2=self.w2,
            b2=self.b2,
            sequence_length=np.asarray(self.sequence_length),
        )

    def predict_window(self, window: np.ndarray) -> PoseModelPrediction:
        features = make_window_features(window).reshape(1, -1)
        probs = self.predict_proba(features)[0]
        index = int(np.argmax(probs))
        return PoseModelPrediction(
            label=self.labels[index],
            confidence=float(probs[index]),
            probabilities={label: float(prob) for label, prob in zip(self.labels, probs)},
        )

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        x = (features - self.mean) / self.std
        hidden = np.maximum(0.0, x @ self.w1 + self.b1)
        logits = hidden @ self.w2 + self.b2
        logits = logits - logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        return exp / exp.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class SmoothedPrediction:
    label: str | None       # None when all recent frames were below confidence threshold
    confidence: float       # fraction of buffer agreeing on this label (0.0 if label is None)
    raw_label: str          # the most recent single-frame prediction
    raw_confidence: float   # the most recent single-frame confidence


class PredictionSmoother:
    """Smooths action classifier output with confidence threshold + majority vote.

    Only predictions whose confidence >= threshold are added to the vote buffer.
    The displayed label is the majority vote across the last *window* qualifying
    predictions, so brief low-confidence flickers are ignored entirely.
    """

    def __init__(self, threshold: float = 0.70, window: int = 7) -> None:
        self.threshold = threshold
        self.window = window
        self._buffer: deque[str] = deque(maxlen=window)

    def update(self, prediction: PoseModelPrediction) -> SmoothedPrediction:
        """Feed one raw prediction and return the smoothed result."""
        if prediction.confidence >= self.threshold:
            self._buffer.append(prediction.label)

        if not self._buffer:
            return SmoothedPrediction(
                label=None,
                confidence=0.0,
                raw_label=prediction.label,
                raw_confidence=prediction.confidence,
            )

        best_label, best_count = Counter(self._buffer).most_common(1)[0]
        return SmoothedPrediction(
            label=best_label,
            confidence=round(best_count / len(self._buffer), 2),
            raw_label=prediction.label,
            raw_confidence=prediction.confidence,
        )

    def reset(self) -> None:
        self._buffer.clear()


# ---------------------------------------------------------------------------
# CNN / LSTM action model (Keras)
# ---------------------------------------------------------------------------

class CNNActionModel:
    """Wraps a saved Keras CNN or LSTM model with the same predict_window interface."""

    def __init__(self, keras_model, labels: list[str], sequence_length: int) -> None:
        self._model = keras_model
        self.labels = labels
        self.sequence_length = sequence_length

    @classmethod
    def load(cls, model_path: str | Path) -> "CNNActionModel":
        import json, os
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        import keras
        model_path = Path(model_path)
        meta_path = model_path.with_suffix(".json")
        if not meta_path.exists():
            raise FileNotFoundError(
                f"Labels sidecar not found: {meta_path}\n"
                "Re-run model_comparison.py to regenerate it."
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        keras_model = keras.models.load_model(str(model_path))
        return cls(keras_model, meta["labels"], meta["sequence_length"])

    def predict_window(self, window: np.ndarray) -> PoseModelPrediction:
        features = make_window_features_seq(window)[np.newaxis]  # (1, T, 107)
        probs = self._model.predict(features, verbose=0)[0]
        index = int(np.argmax(probs))
        return PoseModelPrediction(
            label=self.labels[index],
            confidence=float(probs[index]),
            probabilities={l: float(p) for l, p in zip(self.labels, probs)},
        )


def load_action_model(path: str | Path) -> PoseActionModel | CNNActionModel:
    """Load whichever action model format is at *path* (.npz → MLP, .keras → CNN/LSTM)."""
    path = Path(path)
    if path.suffix == ".npz":
        return PoseActionModel.load(path)
    if path.suffix == ".keras":
        return CNNActionModel.load(path)
    raise ValueError(f"Unsupported model format: {path.suffix}  (expected .npz or .keras)")

