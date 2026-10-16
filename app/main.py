"""FastAPI application: interactive aspect-based sentiment analysis demo."""
from __future__ import annotations

import os
import random
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from . import model as ml_model

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_CSV = os.path.join(_ROOT, "data", "demo.csv")

app = FastAPI(title="Aspect-Based Sentiment Analysis")


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1)
    term: str = Field(..., min_length=1)


@lru_cache(maxsize=1)
def load_demo_set() -> pd.DataFrame:
    if not os.path.exists(DEMO_CSV):
        return pd.DataFrame(columns=["text", "term", "label"])
    return pd.read_csv(DEMO_CSV)


# --------------------------------------------------------------------------
# HTML page
# --------------------------------------------------------------------------
_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aspect-Based Sentiment Analysis</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #222; }
  h1 { font-size: 1.6rem; }
  textarea, input { width: 100%; box-sizing: border-box; padding: .6rem; margin: .3rem 0; font-size: 1rem; border: 1px solid #ccc; border-radius: 6px; }
  button { padding: .6rem 1.2rem; font-size: 1rem; border: 0; border-radius: 6px; cursor: pointer; background: #2563eb; color: #fff; }
  button.secondary { background: #6b7280; margin-left: .5rem; }
  .result { margin-top: 1.2rem; padding: 1rem; border-radius: 8px; background: #f3f4f6; }
  .positive { color: #16a34a; } .negative { color: #dc2626; } .neutral { color: #6b7280; }
  .bar { height: 18px; border-radius: 9px; background: #e5e7eb; margin: .3rem 0; overflow: hidden; }
  .bar span { display: block; height: 100%; border-radius: 9px; }
  .reveal { color: #6b7280; font-size: .9rem; margin-top: .5rem; }
</style></head><body>
<h1>Aspect-Based Sentiment Analysis</h1>
<p>Enter a restaurant review and the <strong>aspect term</strong> (e.g. <code>food</code>, <code>service</code>, <code>price</code>) to classify its sentiment.</p>
<label for="text">Review</label>
<textarea id="text" rows="4" placeholder="The food was fantastic but the service was slow."></textarea>
<label for="term">Aspect term</label>
<input id="term" placeholder="service">
<button id="predict">Predict</button>
<button id="demo" class="secondary">Random demo sample</button>
<div id="result" class="result" style="display:none"></div>
<script>
  const result = document.getElementById('result');
  let trueLabel = null;

  async function predict(text, term) {
    const res = await fetch('/predict', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, term}),
    });
    if (!res.ok) { const e = await res.json(); result.innerHTML = '<span class="negative">Error: ' + e.detail + '</span>'; result.style.display = 'block'; return; }
    const data = await res.json();
    const bars = Object.entries(data.distribution).map(([k, v]) =>
      '<div class="bar"><span style="width:' + (v * 100) + '%;background:#2563eb"></span></div>' +
      '<span>' + k + ': ' + (v * 100).toFixed(1) + '%</span>'
    ).join('');
    result.innerHTML =
      '<strong>Sentiment:</strong> <span class="' + data.label + '">' + data.label + '</span>' +
      ' (confidence ' + (data.confidence * 100).toFixed(1) + '%)' +
      '<div style="margin-top:.5rem">' + bars + '</div>' +
      (trueLabel !== null ? '<div class="reveal">True label: <b>' + trueLabel + '</b> ' + (trueLabel === data.label ? '(hit)' : '(miss)') + '</div>' : '');
    result.style.display = 'block';
    trueLabel = null;
  }

  document.getElementById('predict').addEventListener('click', () => {
    predict(document.getElementById('text').value, document.getElementById('term').value);
  });

  document.getElementById('demo').addEventListener('click', async () => {
    const res = await fetch('/api/demo');
    if (!res.ok) { result.innerHTML = '<span class="negative">No demo samples available.</span>'; result.style.display = 'block'; return; }
    const d = await res.json();
    document.getElementById('text').value = d.text;
    document.getElementById('term').value = d.term;
    trueLabel = d.label;
    predict(d.text, d.term);
  });
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(_PAGE)


# --------------------------------------------------------------------------
# JSON API
# --------------------------------------------------------------------------
@app.post("/predict")
def predict_api(req: PredictRequest) -> JSONResponse:
    try:
        return JSONResponse(ml_model.predict(req.text, req.term))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/demo")
def demo_api() -> JSONResponse:
    df = load_demo_set()
    if df.empty:
        raise HTTPException(status_code=404, detail="no demo samples available")
    row = df.sample(n=1, random_state=random.SystemRandom().randint(0, 2**31 - 1)).iloc[0]
    return JSONResponse({"text": row["text"], "term": row["term"], "label": row["label"]})


@app.get("/health")
def health() -> JSONResponse:
    loaded = os.path.exists(ml_model.default_model_path())
    return JSONResponse({"status": "ok", "model_loaded": loaded})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
