def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Aspect-Based Sentiment Analysis" in resp.text


def test_predict_ok(client):
    resp = client.post("/predict", json={"text": "the food was great", "term": "food"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] in ["negative", "neutral", "positive"]
    assert "distribution" in data


def test_predict_empty_text_rejected(client):
    resp = client.post("/predict", json={"text": "", "term": "food"})
    assert resp.status_code == 422


def test_predict_empty_term_rejected(client):
    resp = client.post("/predict", json={"text": "the food was great", "term": ""})
    assert resp.status_code == 422


def test_predict_missing_field_rejected(client):
    resp = client.post("/predict", json={"text": "the food was great"})
    assert resp.status_code == 422


def test_predict_whitespace_text_rejected(client):
    resp = client.post("/predict", json={"text": "   ", "term": "food"})
    assert resp.status_code == 422


def test_demo_returns_reserved_sample(client):
    resp = client.get("/api/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] in ["negative", "neutral", "positive"]
    assert data["text"] and data["term"]
