import pytest

from app import model as ml_model
from ml.aspects import ASPECTS


@pytest.fixture
def use_tfidf(trained_model_path, monkeypatch):
    monkeypatch.setattr(ml_model, "default_model_path", lambda: trained_model_path)
    ml_model._load_tfidf.cache_clear()
    return trained_model_path


def test_predict_empty_text_raises(use_tfidf):
    with pytest.raises(ValueError, match="text"):
        ml_model.predict_aspects("")


def test_predict_whitespace_only_raises(use_tfidf):
    with pytest.raises(ValueError):
        ml_model.predict_aspects("   ")


def test_predict_unknown_model_raises(use_tfidf):
    with pytest.raises(ValueError):
        ml_model.predict_aspects("text", "nonexistent")


def test_predict_returns_four_aspects(use_tfidf):
    out = ml_model.predict_aspects("the food was great")
    assert [a["aspect"] for a in out] == ASPECTS
    for a in out:
        assert set(a) == {"aspect", "label", "confidence", "distribution"}
        assert a["label"] in ["negative", "neutral", "positive"]
        assert 0 <= a["confidence"] <= 1
        assert sum(a["distribution"].values()) == pytest.approx(1.0, abs=1e-3)


def test_predict_is_deterministic(use_tfidf):
    a = ml_model.predict_aspects("the service was slow")
    b = ml_model.predict_aspects("the service was slow")
    assert a == b
