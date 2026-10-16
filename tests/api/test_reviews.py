def test_create_and_list_reviews(client):
    resp = client.post("/api/reviews", json={"text": "食物很棒", "model": "tfidf"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] == 1
    assert created["text"] == "食物很棒"
    assert created["food_label"] in ["negative", "neutral", "positive"]

    resp = client.get("/api/reviews")
    assert resp.status_code == 200
    reviews = resp.json()
    assert len(reviews) == 1
    assert reviews[0]["text"] == "食物很棒"


def test_get_review(client):
    client.post("/api/reviews", json={"text": "食物很棒", "model": "tfidf"})
    resp = client.get("/api/reviews/1")
    assert resp.status_code == 200
    assert resp.json()["text"] == "食物很棒"


def test_get_review_not_found(client):
    resp = client.get("/api/reviews/999")
    assert resp.status_code == 404


def test_update_review(client):
    client.post("/api/reviews", json={"text": "食物很棒", "model": "tfidf"})
    resp = client.put("/api/reviews/1", json={"text": "服务很差", "model": "tfidf"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "服务很差"


def test_update_review_not_found(client):
    resp = client.put("/api/reviews/999", json={"text": "x", "model": "tfidf"})
    assert resp.status_code == 404


def test_delete_review(client):
    client.post("/api/reviews", json={"text": "食物很棒", "model": "tfidf"})
    resp = client.delete("/api/reviews/1")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1
    resp = client.get("/api/reviews")
    assert resp.json() == []


def test_delete_review_not_found(client):
    resp = client.delete("/api/reviews/999")
    assert resp.status_code == 404


def test_create_review_empty_text_rejected(client):
    resp = client.post("/api/reviews", json={"text": "", "model": "tfidf"})
    assert resp.status_code == 422


def test_create_review_unknown_model_rejected(client):
    resp = client.post("/api/reviews", json={"text": "食物很棒", "model": "nonexistent"})
    assert resp.status_code == 400
