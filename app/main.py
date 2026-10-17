"""FastAPI backend: REST API for aspect-based sentiment analysis (4 aspects).

The frontend is a separate Vue 3 + Vite project (see ``frontend/``) and is not
part of this module. In production this app serves the built SPA as static
files so the two can be deployed together; in development they run separately
(Vite dev server proxies API calls here).

API routes:
    POST /predict                 single review -> 4 aspects + rating + explanation
    GET  /models                  available models
    GET  /api/template            CSV template download
    POST /api/predict-csv         batch CSV -> NDJSON progress/result stream
    GET  /api/demo                random demo sample
    GET  /health                  readiness probe
    /api/reviews CRUD             saved records (create/list/export/get/update/delete)
"""
from __future__ import annotations

import io
import json
import os
import random
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import database
from . import model as ml_model
from .schemas import ReviewInput

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_CSV = os.path.join(_ROOT, "data", "demo.csv")
REVIEWS_DB_ENV = "REVIEWS_DB_PATH"
DEFAULT_DB = os.path.join(_ROOT, "reviews.db")
FRONTEND_DIST = os.path.join(_ROOT, "frontend", "dist")

app = FastAPI(title="Aspect-Based Sentiment Analysis")


def get_db_path() -> str:
    return os.environ.get(REVIEWS_DB_ENV, DEFAULT_DB)


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1)
    model: str = "tfidf"


class BatchDeleteRequest(BaseModel):
    ids: list[int] = []
    all: bool = False


@lru_cache(maxsize=1)
def load_demo_set() -> pd.DataFrame:
    if not os.path.exists(DEMO_CSV):
        return pd.DataFrame()
    return pd.read_csv(DEMO_CSV)


def _find_review_column(df: pd.DataFrame) -> str:
    for c in df.columns:
        if str(c).lower().strip() in ("review", "text", "comment", "content", "评论"):
            return c
    return df.columns[0]


def _spa_index() -> Response:
    """Serve the built Vue SPA (frontend/ is a separate project)."""
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="frontend not built: run `cd frontend && npm run build`")
    return FileResponse(index_path)


@app.get("/", include_in_schema=False)
@app.get("/history", include_in_schema=False)
def index() -> Response:
    return _spa_index()


@app.post("/predict")
def predict_api(req: PredictRequest) -> JSONResponse:
    try:
        aspects = ml_model.predict_aspects(req.text, req.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        rating = ml_model.predict_rating(req.text)
    except FileNotFoundError:
        rating = None

    explanation = None
    if req.model == "tfidf":
        try:
            explanation = ml_model.explain_aspects(req.text)
        except Exception:  # noqa: BLE001 - explanation is best-effort
            explanation = None

    return JSONResponse(
        {"text": req.text, "model": req.model, "aspects": aspects, "rating": rating, "explanation": explanation}
    )


@app.get("/models")
def models_api() -> JSONResponse:
    return JSONResponse(ml_model.AVAILABLE_MODELS)


@app.get("/api/template")
def template_api() -> Response:
    csv_bytes = "review\n食物很好吃服务也很好\n价格有点贵环境一般般\n".encode("utf-8-sig")
    return Response(content=csv_bytes, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=template.csv"})


@app.post("/api/predict-csv")
async def predict_csv(file: UploadFile = File(...), model: str = Form("tfidf")) -> StreamingResponse:  # noqa: B008
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid CSV: {exc}") from exc
    if df.empty:
        raise HTTPException(status_code=422, detail="CSV is empty")

    review_col = _find_review_column(df)
    total = len(df)

    def generate():
        out = df.copy()
        for aspect in ["food", "service", "price", "ambience"]:
            out[f"{aspect}_sentiment"] = ""
            out[f"{aspect}_confidence"] = 0.0
            out[f"{aspect}_positive"] = 0.0
            out[f"{aspect}_negative"] = 0.0
        try:
            for idx, text in enumerate(df[review_col].astype(str)):
                aspects = ml_model.predict_aspects(text, model)
                for a in aspects:
                    asp = a["aspect"]
                    out.at[idx, f"{asp}_sentiment"] = a["label"]
                    if a["confidence"] is not None:
                        out.at[idx, f"{asp}_confidence"] = a["confidence"]
                        out.at[idx, f"{asp}_positive"] = a["distribution"].get("positive", 0.0)
                        out.at[idx, f"{asp}_negative"] = a["distribution"].get("negative", 0.0)
                database.create_review(get_db_path(), text, model, aspects)
                yield json.dumps({"type": "progress", "done": idx + 1, "total": total}, ensure_ascii=False) + "\n"
        except FileNotFoundError as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False) + "\n"
            return
        yield json.dumps({"type": "result", "filename": "results.csv", "csv": out.to_csv(index=False)}, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/api/demo")
def demo_api() -> JSONResponse:
    df = load_demo_set()
    if df.empty:
        raise HTTPException(status_code=404, detail="no demo samples available")
    row = df.sample(n=1, random_state=random.SystemRandom().randint(0, 2**31 - 1)).iloc[0]
    labels = {}
    for aspect in ["food", "service", "price", "ambience"]:
        val = row.get(aspect)
        if pd.notna(val) and str(val).strip():
            labels[aspect] = str(val).strip()
    return JSONResponse({"text": row["text"], "labels": labels})


@app.get("/health")
def health() -> JSONResponse:
    loaded = os.path.exists(ml_model.default_model_path())
    return JSONResponse({"status": "ok", "model_loaded": loaded})


# --------------------------------------------------------------------------
# Saved reviews CRUD (SQLite)
# --------------------------------------------------------------------------
@app.post("/api/reviews", status_code=201)
def create_review_api(payload: ReviewInput) -> JSONResponse:
    try:
        aspects = ml_model.predict_aspects(payload.text, payload.model)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    review = database.create_review(get_db_path(), payload.text, payload.model, aspects)
    return JSONResponse(status_code=201, content=review.model_dump())


@app.get("/api/reviews")
def list_reviews_api() -> JSONResponse:
    return JSONResponse([r.model_dump() for r in database.list_reviews(get_db_path())])


@app.get("/api/reviews/export")
def export_reviews_api() -> Response:
    reviews = database.list_reviews(get_db_path())
    rows = []
    for r in reviews:
        row = {"id": r.id, "text": r.text, "model": r.model}
        for a in ["food", "service", "price", "ambience"]:
            row[f"{a}_sentiment"] = getattr(r, f"{a}_label")
            row[f"{a}_confidence"] = getattr(r, f"{a}_confidence")
        row["created_at"] = r.created_at
        rows.append(row)
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return Response(content=csv_bytes, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=reviews.csv"})


@app.get("/api/reviews/{review_id}")
def get_review_api(review_id: int) -> JSONResponse:
    review = database.get_review(get_db_path(), review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return JSONResponse(review.model_dump())


@app.put("/api/reviews/{review_id}")
def update_review_api(review_id: int, payload: ReviewInput) -> JSONResponse:
    try:
        aspects = ml_model.predict_aspects(payload.text, payload.model)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    review = database.update_review(get_db_path(), review_id, payload.text, payload.model, aspects)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return JSONResponse(review.model_dump())


@app.post("/api/reviews/batch-delete")
def batch_delete_reviews_api(payload: BatchDeleteRequest) -> JSONResponse:
    ids = payload.ids
    if payload.all:
        ids = [r.id for r in database.list_reviews(get_db_path())]
    deleted = 0
    for rid in ids:
        if database.delete_review(get_db_path(), rid):
            deleted += 1
    return JSONResponse({"deleted": deleted})


@app.delete("/api/reviews/{review_id}")
def delete_review_api(review_id: int) -> JSONResponse:
    if not database.delete_review(get_db_path(), review_id):
        raise HTTPException(status_code=404, detail="review not found")
    return JSONResponse({"deleted": review_id})


_assets_dir = os.path.join(FRONTEND_DIST, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
