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


def test_template_returns_csv(client):
    resp = client.get("/api/template")
    assert resp.status_code == 200
    assert "review" in resp.text
    assert "text/csv" in resp.headers["content-type"]


def test_predict_csv_streams_progress_and_result(client):
    import json

    csv_content = "review\n食物很好吃\n服务很差\n"
    resp = client.post(
        "/api/predict-csv",
        files={"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"model": "tfidf"},
    )
    assert resp.status_code == 200
    lines = [ln for ln in resp.text.strip().split("\n") if ln]
    msgs = [json.loads(ln) for ln in lines]
    progress = [m for m in msgs if m["type"] == "progress"]
    result = [m for m in msgs if m["type"] == "result"]
    assert len(progress) == 2
    assert progress[-1]["done"] == 2 and progress[-1]["total"] == 2
    assert len(result) == 1
    for col in ["food_sentiment", "service_sentiment", "price_sentiment", "ambience_sentiment"]:
        assert col in result[0]["csv"]
    assert "食物很好吃" in result[0]["csv"]
