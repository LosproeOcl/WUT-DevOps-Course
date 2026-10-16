"""Model loading and inference helpers, separated from FastAPI for testability."""
from __future__ import annotations

import os
from functools import lru_cache

import joblib

LABELS = ["negative", "neutral", "positive"]

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_model_path() -> str:
    return os.path.join(_ROOT, "models", "model.joblib")


@lru_cache(maxsize=1)
def load_pipeline(path: str | None = None):
    """Load (and cache) the fitted sklearn pipeline."""
    path = path or default_model_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"model not found: {path}")
    return joblib.load(path)


def make_feature(text: str, term: str) -> str:
    """Mirror the training-time feature: term prepended to the text."""
    return f"{term} {text}"


def predict(text: str, term: str, path: str | None = None) -> dict:
    """Predict the sentiment polarity of `term` within `text`."""
    text = (text or "").strip()
    term = (term or "").strip()
    if not text:
        raise ValueError("text must not be empty")
    if not term:
        raise ValueError("term must not be empty")

    pipeline = load_pipeline(path)
    probs = pipeline.predict_proba([make_feature(text, term)])[0]
    classes = [str(c) for c in pipeline.classes_]
    best = int(probs.argmax())
    return {
        "text": text,
        "term": term,
        "label": classes[best],
        "confidence": round(float(probs[best]), 4),
        "distribution": {c: round(float(p), 4) for c, p in zip(classes, probs)},
    }
