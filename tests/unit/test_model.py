import pytest

from app import model as ml_model
from ml.aspects import ASPECTS


def test_predict_empty_text_raises(trained_model_path):
    with pytest.raises(ValueError, match="text"):
        ml_model.predict_aspects("", path=trained_model_path)


def test_predict_whitespace_only_raises(trained_model_path):
    with pytest.raises(ValueError):
        ml_model.predict_aspects("   ", path=trained_model_path)


def test_predict_missing_model_file_raises():
    with pytest.raises(FileNotFoundError):
        ml_model.predict_aspects("text", path="does-not-exist.joblib")


def test_predict_returns_four_aspects(trained_model_path):
    out = ml_model.predict_aspects("the food was great", path=trained_model_path)
    assert [a["aspect"] for a in out] == ASPECTS
    for a in out:
        assert set(a) == {"aspect", "label", "confidence", "distribution"}
        assert a["label"] in ["negative", "neutral", "positive"]
        assert 0 <= a["confidence"] <= 1
        assert sum(a["distribution"].values()) == pytest.approx(1.0, abs=1e-3)


def test_predict_is_deterministic(trained_model_path):
    a = ml_model.predict_aspects("the service was slow", path=trained_model_path)
    b = ml_model.predict_aspects("the service was slow", path=trained_model_path)
    assert a == b
