"""Unified model loading and inference for multiple models.

Models:
    tfidf    : TF-IDF + LogisticRegression (models/model.joblib) — default, always available
    bert     : bert-base-chinese (models/bert/) — fine-tuned on GPU
    roberta  : chinese-roberta-wwm-ext (models/roberta/) — fine-tuned on GPU

torch/transformers are imported lazily so the slim runtime image can serve the
TF-IDF model without the (heavy) deep-learning stack.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import joblib

from ml.aspects import ASPECTS, tokenize_zh

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODELS_DIR = os.path.join(_ROOT, "models")

UNCERTAIN_THRESHOLD = 0.55
BERT_MAX_LEN = 128
RATING_MAX_LEN = 384

AVAILABLE_MODELS = [
    {"key": "tfidf", "name": "TF-IDF + LR"},
    {"key": "bert", "name": "BERT (bert-base-chinese)"},
    {"key": "roberta", "name": "RoBERTa (chinese-wwm-ext)"},
]

_MODEL_CONFIGS = {
    "bert": {"state_dict": "bert/bert_absa.pt", "model_dir": "bert"},
    "roberta": {"state_dict": "roberta/roberta3_absa.pt", "model_dir": "roberta"},
}


def default_model_path() -> str:
    return os.path.join(_MODELS_DIR, "model.joblib")


@lru_cache(maxsize=1)
def _load_tfidf():
    path = default_model_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"model not found: {path}")
    return joblib.load(path)


@lru_cache(maxsize=1)
def _load_bert_model(key: str):
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer, BertConfig

    class _BertAbsa(nn.Module):
        def __init__(self, config):
            super().__init__()
            self.bert = AutoModel.from_config(config)
            hidden = self.bert.config.hidden_size
            self.heads = nn.ModuleList([nn.Linear(hidden, 1) for _ in ASPECTS])

        def forward(self, input_ids, attention_mask):
            out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
            cls = out.last_hidden_state[:, 0, :]
            return torch.stack([head(cls).squeeze(-1) for head in self.heads], dim=1)

    cfg = _MODEL_CONFIGS[key]
    model_dir = os.path.join(_MODELS_DIR, cfg["model_dir"])
    state_path = os.path.join(_MODELS_DIR, cfg["state_dict"])
    if not os.path.exists(state_path) or not os.path.exists(model_dir):
        raise FileNotFoundError(f"model '{key}' not downloaded yet")
    data = torch.load(state_path, map_location="cpu", weights_only=False)
    config = BertConfig.from_dict(data["config"])
    model = _BertAbsa(config)
    model.load_state_dict(data["state_dict"])
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    return model, tokenizer


def _result(aspect: str, label: str, confidence: float, distribution: dict) -> dict:
    return {
        "aspect": aspect,
        "label": label,
        "confidence": round(confidence, 4),
        "distribution": {k: round(float(v), 4) for k, v in distribution.items()},
    }


def _predict_tfidf(tokenized: str) -> list[dict]:
    models = _load_tfidf()
    results = []
    for aspect in ASPECTS:
        pipeline = models.get(aspect)
        if pipeline is None:
            results.append(_result(aspect, "neutral", 0.0, {}))
            continue
        probs = pipeline.predict_proba([tokenized])[0]
        classes = [str(c) for c in pipeline.classes_]
        best = int(probs.argmax())
        confidence = float(probs[best])
        label = classes[best] if confidence >= UNCERTAIN_THRESHOLD else "neutral"
        results.append(_result(aspect, label, confidence, dict(zip(classes, probs))))
    return results


def _predict_bert(key: str, text: str) -> list[dict]:
    import torch

    model, tokenizer = _load_bert_model(key)
    enc = tokenizer(text, max_length=BERT_MAX_LEN, truncation=True, padding="max_length", return_tensors="pt")
    with torch.no_grad():
        logits = model(enc["input_ids"], enc["attention_mask"])
        probs = torch.sigmoid(logits)[0]
    results = []
    for j, aspect in enumerate(ASPECTS):
        p = float(probs[j])
        label = "positive" if p >= 0.5 else "negative"
        confidence = max(p, 1.0 - p)
        if confidence < UNCERTAIN_THRESHOLD:
            label = "neutral"
        results.append(_result(aspect, label, confidence, {"negative": 1.0 - p, "positive": p}))
    return results


def predict_aspects(text: str, model_name: str = "tfidf") -> list[dict]:
    """Predict sentiment for all four aspects using the selected model."""
    text = (text or "").strip()
    if not text:
        raise ValueError("text must not be empty")

    if model_name == "tfidf":
        return _predict_tfidf(tokenize_zh(text))
    if model_name in _MODEL_CONFIGS:
        return _predict_bert(model_name, text)
    raise ValueError(f"unknown model: {model_name}")


@lru_cache(maxsize=1)
def _load_rating():
    path = os.path.join(_MODELS_DIR, "rating.joblib")
    if not os.path.exists(path):
        raise FileNotFoundError(f"rating model not found: {path}")
    return joblib.load(path)


def _predict_rating_tfidf(tokenized: str) -> dict:
    pipeline = _load_rating()
    probs = pipeline.predict_proba([tokenized])[0]
    classes = [int(c) for c in pipeline.classes_]
    best = int(probs.argmax())
    return {"star": classes[best], "confidence": round(float(probs[best]), 4)}


@lru_cache(maxsize=1)
def _load_rating_bert():
    import torch
    from torch import nn
    from transformers import AutoConfig, AutoModel, AutoTokenizer

    class _BertRating(nn.Module):
        def __init__(self, config):
            super().__init__()
            self.bert = AutoModel.from_config(config)
            self.head = nn.Linear(self.bert.config.hidden_size, 5)

        def forward(self, input_ids, attention_mask):
            out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
            return self.head(out.last_hidden_state[:, 0, :])

    model_dir = os.path.join(_MODELS_DIR, "rating_bert")
    state_path = os.path.join(model_dir, "rating_bert.pt")
    if not os.path.exists(state_path):
        raise FileNotFoundError(f"rating BERT model not found: {state_path}")
    data = torch.load(state_path, map_location="cpu", weights_only=False)
    config = AutoConfig.from_dict(data["config"])
    model = _BertRating(config)
    model.load_state_dict(data["state_dict"])
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    return model, tokenizer


def _predict_rating_bert(text: str) -> dict:
    import torch

    model, tokenizer = _load_rating_bert()
    enc = tokenizer(text, max_length=RATING_MAX_LEN, truncation=True, padding="max_length", return_tensors="pt")
    with torch.no_grad():
        logits = model(enc["input_ids"], enc["attention_mask"])[0]
    probs = torch.softmax(logits, dim=0)
    star = int(probs.argmax()) + 1
    return {"star": star, "confidence": round(float(probs.max()), 4)}


def predict_rating(text: str) -> dict:
    """Predict the overall star rating (1-5), preferring the fine-tuned BERT."""
    text = (text or "").strip()
    if not text:
        raise ValueError("text must not be empty")

    rating_bert_path = os.path.join(_MODELS_DIR, "rating_bert", "rating_bert.pt")
    if os.path.exists(rating_bert_path):
        try:
            return _predict_rating_bert(text)
        except Exception as exc:  # noqa: BLE001 - fall back to TF-IDF on any error
            logger.warning("rating BERT unavailable, falling back to TF-IDF: %s", exc)
    return _predict_rating_tfidf(tokenize_zh(text))


def explain_aspects(text: str, top_k: int = 5) -> list[dict]:
    """Return the top contributing tokens per aspect (linear SHAP values).

    Uses shap.LinearExplainer on the TF-IDF + LogisticRegression models, which
    yields exact per-token SHAP values (coef * x) for a linear model.
    """
    import numpy as np
    import shap

    text = (text or "").strip()
    if not text:
        raise ValueError("text must not be empty")

    models = _load_tfidf()
    tokenized = tokenize_zh(text)
    results = []
    for aspect in ASPECTS:
        pipeline = models.get(aspect)
        if pipeline is None:
            results.append({"aspect": aspect, "positive": [], "negative": []})
            continue
        tfidf = pipeline.named_steps["tfidf"]
        clf = pipeline.named_steps["clf"]
        names = tfidf.get_feature_names_out()
        X = tfidf.transform([tokenized]).toarray()
        explainer = shap.LinearExplainer(clf, np.zeros((1, X.shape[1])))
        sv = np.asarray(explainer.shap_values(X)).reshape(X.shape[1])
        order = np.argsort(sv)[::-1]
        positive = [(str(names[i]), float(sv[i])) for i in order if sv[i] > 0][:top_k]
        negative = [(str(names[i]), float(sv[i])) for i in order[::-1] if sv[i] < 0][:top_k]
        results.append({"aspect": aspect, "positive": positive, "negative": negative})
    return results
