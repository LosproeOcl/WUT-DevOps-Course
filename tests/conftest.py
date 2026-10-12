# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def database_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def client(database_path, monkeypatch):
    monkeypatch.setenv("CARS_DB_PATH", database_path)
    from app.main import app

    return TestClient(app)


@pytest.fixture
def car_payload():
    return {"make": "Mazda", "model": "MX-5", "year": 2020, "color": "Red"}
