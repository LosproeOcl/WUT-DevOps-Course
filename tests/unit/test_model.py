import pytest

from app import model as ml_model


def test_make_feature_prepends_term():
    assert ml_model.make_feature("the food was great", "food") == "food the food was great"


def test_predict_empty_text_raises(trained_model_path):
    with pytest.raises(ValueError, match="text"):
        ml_model.predict("", "food", path=trained_model_path)


def test_predict_empty_term_raises(trained_model_path):
    with pytest.raises(ValueError, match="term"):
        ml_model.predict("the food was great", "", path=trained_model_path)


def test_predict_whitespace_only_raises(trained_model_path):
    with pytest.raises(ValueError):
        ml_model.predict("   ", "food", path=trained_model_path)


def test_predict_missing_model_file_raises():
    with pytest.raises(FileNotFoundError):
        ml_model.predict("text", "term", path="does-not-exist.joblib")


def test_predict_returns_expected_shape(trained_model_path):
    out = ml_model.predict("the food was great", "food", path=trained_model_path)
    assert set(out) == {"text", "term", "label", "confidence", "distribution"}
    assert out["label"] in ["negative", "neutral", "positive"]
    assert 0 <= out["confidence"] <= 1
    assert sum(out["distribution"].values()) == pytest.approx(1.0, abs=1e-3)


def test_predict_is_deterministic(trained_model_path):
    a = ml_model.predict("the service was slow", "service", path=trained_model_path)
    b = ml_model.predict("the service was slow", "service", path=trained_model_path)
    assert a == b
