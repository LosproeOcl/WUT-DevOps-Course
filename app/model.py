"""Model loading and inference helpers, separated from FastAPI for testability."""
from __future__ import annotations

import os
from functools import lru_cache

import joblib

from ml.aspects import ASPECTS

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Below this confidence the aspect is reported as "neutral" (uncertain).
UNCERTAIN_THRESHOLD = 0.55


def default_model_path() -> str:
    return os.path.join(_ROOT, "models", "model.joblib")


@lru_cache(maxsize=1)
def load_models(path: str | None = None) -> dict:
    """Load (and cache) the dict of aspect -> fitted pipeline."""
    path = path or default_model_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"model not found: {path}")
    return joblib.load(path)


def predict_aspects(text: str, path: str | None = None) -> list[dict]:
    """Predict sentiment for all four aspects on a single review."""
    text = (text or "").strip()
    if not text:
        raise ValueError("text must not be empty")

    models = load_models(path)
    results: list[dict] = []
    for aspect in ASPECTS:
        pipeline = models.get(aspect)
        if pipeline is None:
            results.append({"aspect": aspect, "label": None, "confidence": None, "distribution": {}})
            continue
        probs = pipeline.predict_proba([text])[0]
        classes = [str(c) for c in pipeline.classes_]
        best = int(probs.argmax())
        confidence = float(probs[best])
        label = classes[best] if confidence >= UNCERTAIN_THRESHOLD else "neutral"
        results.append(
            {
                "aspect": aspect,
                "label": label,
                "confidence": round(confidence, 4),
                "distribution": {c: round(float(p), 4) for c, p in zip(classes, probs)},
            }
        )
    return results
