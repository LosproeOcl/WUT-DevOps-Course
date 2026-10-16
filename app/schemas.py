"""Pydantic schemas for the saved-review CRUD feature."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, StringConstraints

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ReviewInput(BaseModel):
    text: NonBlank
    model: str = "tfidf"


class Review(ReviewInput):
    id: int
    food_label: str = "neutral"
    food_confidence: float = 0.0
    service_label: str = "neutral"
    service_confidence: float = 0.0
    price_label: str = "neutral"
    price_confidence: float = 0.0
    ambience_label: str = "neutral"
    ambience_confidence: float = 0.0
    created_at: str = ""
