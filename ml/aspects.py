"""Shared aspect definitions: category mapping + bilingual display names.

The four coarse aspects the app reports are:
    food (口味) / service (服务) / price (价格) / ambience (环境)

Fine-grained MAMS categories are merged into these four.
"""
from __future__ import annotations

# Fine-grained category -> coarse aspect
CATEGORY_TO_ASPECT = {
    "food": "food",
    "menu": "food",
    "service": "service",
    "staff": "service",
    "price": "price",
    "ambience": "ambience",
    "place": "ambience",
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
    return CATEGORY_TO_ASPECT.get(category.lower())
