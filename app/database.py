# -*- coding: utf-8 -*-
"""SQLite persistence layer (integration-test target)."""
import sqlite3

from .schemas import Car, CarInput


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(db_path):
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                color TEXT NOT NULL
            )
            """
        )


def _row_to_car(row):
    return Car(
        id=row["id"],
        make=row["make"],
        model=row["model"],
        year=row["year"],
        color=row["color"],
    )


def create_car(db_path, car_input: CarInput) -> Car:
    initialize(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO cars (make, model, year, color) VALUES (?, ?, ?, ?)",
            (car_input.make, car_input.model, car_input.year, car_input.color),
        )
        car_id = cur.lastrowid
    return get_car(db_path, car_id)


def get_car(db_path, car_id):
    initialize(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, make, model, year, color FROM cars WHERE id = ?",
            (car_id,),
        ).fetchone()
    return _row_to_car(row) if row is not None else None


def list_cars(db_path):
    initialize(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, make, model, year, color FROM cars ORDER BY id"
        ).fetchall()
    return [_row_to_car(r) for r in rows]


def update_car(db_path, car_id, car_input: CarInput) -> Car:
    initialize(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE cars SET make = ?, model = ?, year = ?, color = ? WHERE id = ?",
            (car_input.make, car_input.model, car_input.year, car_input.color, car_id),
        )
    return get_car(db_path, car_id)


def delete_car(db_path, car_id):
    initialize(db_path)
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM cars WHERE id = ?", (car_id,))
