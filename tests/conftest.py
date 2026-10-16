"""Shared fixtures: a tiny 4-aspect model + demo set, so tests run without real data."""
import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def _make_tiny_models():
    data = {
        "food": [("the food was great", "positive"), ("the food was awful", "negative")],
        "service": [("the service was slow", "negative"), ("the service was quick", "positive")],
        "price": [("the price was high", "negative"), ("the price was fair", "neutral")],
        "ambience": [("the ambience was nice", "positive"), ("the ambience was dull", "negative")],
    }
    models = {}
    for aspect, pairs in data.items():
        X = [p[0] for p in pairs]
        y = [p[1] for p in pairs]
        pipe = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(max_iter=1000))])
        pipe.fit(X, y)
        models[aspect] = pipe
    return models


@pytest.fixture
def trained_model_path(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(_make_tiny_models(), path)
    return str(path)


@pytest.fixture
def demo_csv_path(tmp_path):
    path = tmp_path / "demo.csv"
    path.write_text(
        "text,food,service,price,ambience\n"
        '"The food was amazing.",positive,,,\n'
        '"The service was slow.",,negative,,\n',
        encoding="utf-8",
    )
    return str(path)


@pytest.fixture
def client(trained_model_path, demo_csv_path, monkeypatch):
    import app.main as main_mod
    import app.model as model_mod

    monkeypatch.setattr(model_mod, "default_model_path", lambda: trained_model_path)
    model_mod.load_models.cache_clear()
    monkeypatch.setattr(main_mod, "DEMO_CSV", demo_csv_path)
    main_mod.load_demo_set.cache_clear()

    from app.main import app

    return TestClient(app)
