"""Shared aspect definitions: category mapping + bilingual display names + tokenizer.

The four coarse aspects the app reports are:
    food (口味) / service (服务) / price (价格) / ambience (环境)

The ASAP (Meituan) fine-grained categories are merged into these four.
"""
from __future__ import annotations

# ASAP (Meituan) fine-grained category -> coarse aspect
ASAP_ASPECT_MAP = {
    "Food#Portion": "food",
    "Food#Taste": "food",
    "Food#Appearance": "food",
    "Food#Recommend": "food",
    "Service#Queue": "service",
    "Service#Hospitality": "service",
    "Service#Parking": "service",
    "Service#Timely": "service",
    "Price#Level": "price",
    "Price#Cost_effective": "price",
    "Price#Discount": "price",
    "Ambience#Decoration": "ambience",
    "Ambience#Noise": "ambience",
    "Ambience#Space": "ambience",
    "Ambience#Sanitary": "ambience",
}

ASPECTS = ["food", "service", "price", "ambience"]

ASPECT_NAMES = {
    "food": {"en": "Taste / Food", "zh": "口味"},
    "service": {"en": "Service", "zh": "服务"},
    "price": {"en": "Price", "zh": "价格"},
    "ambience": {"en": "Ambience", "zh": "环境"},
}

LABELS = ["negative", "neutral", "positive"]
BINARY_LABELS = ["negative", "positive"]


def map_category(category: str) -> str | None:
    """Return the coarse aspect for a fine-grained category, or None to drop it."""
    return ASAP_ASPECT_MAP.get(category)


def tokenize_zh(text: str) -> str:
    """Tokenize Chinese text into space-separated characters.

    Character-level segmentation is fast and works well for Chinese sentiment
    classification (small vocabulary, no external dictionary needed).
    """
    return " ".join(str(text))
