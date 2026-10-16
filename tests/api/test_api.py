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


def test_predict_returns_four_aspects(client):
    resp = client.post("/predict", json={"text": "the food was great"})
    assert resp.status_code == 200
    data = resp.json()
    aspects = [a["aspect"] for a in data["aspects"]]
    assert aspects == ["food", "service", "price", "ambience"]
    assert all(a["label"] in ["negative", "neutral", "positive"] for a in data["aspects"])


def test_predict_empty_text_rejected(client):
    resp = client.post("/predict", json={"text": ""})
    assert resp.status_code == 422


def test_predict_missing_field_rejected(client):
    resp = client.post("/predict", json={})
    assert resp.status_code == 422


def test_predict_whitespace_text_rejected(client):
    resp = client.post("/predict", json={"text": "   "})
    assert resp.status_code == 422


def test_demo_returns_reserved_sample(client):
    resp = client.get("/api/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"]
    assert isinstance(data["labels"], dict)
