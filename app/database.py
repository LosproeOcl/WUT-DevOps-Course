"""SQLite persistence layer for saved reviews (CRUD)."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from .schemas import Review

_ASPECTS = ["food", "service", "price", "ambience"]


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(db_path: str) -> None:
    cols = []
    for a in _ASPECTS:
        cols.append(f"{a}_label TEXT NOT NULL DEFAULT 'neutral'")
        cols.append(f"{a}_confidence REAL NOT NULL DEFAULT 0")
    with _connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reviews ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "text TEXT NOT NULL, "
            "model TEXT NOT NULL, "
            + ", ".join(cols)
            + ", created_at TEXT NOT NULL)"
        )


def _row_to_review(row) -> Review:
    return Review(
        id=row["id"],
        text=row["text"],
        model=row["model"],
        food_label=row["food_label"],
        food_confidence=row["food_confidence"],
        service_label=row["service_label"],
        service_confidence=row["service_confidence"],
        price_label=row["price_label"],
        price_confidence=row["price_confidence"],
        ambience_label=row["ambience_label"],
        ambience_confidence=row["ambience_confidence"],
        created_at=row["created_at"],
    )


def _aspect_values(aspects: list[dict]) -> dict:
    """Convert a list of aspect predictions into label/confidence column values."""
    values: dict[str, object] = {}
    for a in aspects:
        asp = a["aspect"]
        values[f"{asp}_label"] = a["label"] if a["label"] is not None else "neutral"
        values[f"{asp}_confidence"] = a["confidence"] if a["confidence"] is not None else 0.0
    return values


def create_review(db_path: str, text: str, model: str, aspects: list[dict]) -> Review:
    initialize(db_path)
    values = _aspect_values(aspects)
    cols = ["text", "model", "created_at"]
    for a in _ASPECTS:
        cols += [f"{a}_label", f"{a}_confidence"]
    placeholders = ", ".join(["?"] * len(cols))
    now = datetime.now(UTC).isoformat()
    args = [text, model, now]
    for a in _ASPECTS:
        args += [values.get(f"{a}_label", "neutral"), values.get(f"{a}_confidence", 0.0)]
    with _connect(db_path) as conn:
        cur = conn.execute(
            f"INSERT INTO reviews ({', '.join(cols)}) VALUES ({placeholders})", args
        )
        review_id = cur.lastrowid
    return get_review(db_path, review_id)


def list_reviews(db_path: str) -> list[Review]:
    initialize(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
    return [_row_to_review(r) for r in rows]


def get_review(db_path: str, review_id: int) -> Review | None:
    initialize(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    return _row_to_review(row) if row is not None else None


def update_review(db_path: str, review_id: int, text: str, model: str, aspects: list[dict]) -> Review | None:
    initialize(db_path)
    if get_review(db_path, review_id) is None:
        return None
    values = _aspect_values(aspects)
    sets = ["text = ?", "model = ?"]
    args = [text, model]
    for a in _ASPECTS:
        sets += [f"{a}_label = ?", f"{a}_confidence = ?"]
        args += [values.get(f"{a}_label", "neutral"), values.get(f"{a}_confidence", 0.0)]
    args.append(review_id)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE reviews SET {', '.join(sets)} WHERE id = ?", args)
    return get_review(db_path, review_id)


def delete_review(db_path: str, review_id: int) -> bool:
    initialize(db_path)
    if get_review(db_path, review_id) is None:
        return False
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    return True
