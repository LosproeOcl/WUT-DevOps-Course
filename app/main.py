"""FastAPI application: interactive aspect-based sentiment analysis (4 aspects)."""
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


@lru_cache(maxsize=1)
def load_demo_set() -> pd.DataFrame:
    if not os.path.exists(DEMO_CSV):
        return pd.DataFrame()
    return pd.read_csv(DEMO_CSV)


_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aspect-Based Sentiment Analysis</title>
<style>
  body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", Roboto, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; color: #1f2937; }
  .header { display: flex; align-items: center; justify-content: space-between; }
  h1 { font-size: 1.5rem; }
  .lang { border: 1px solid #d1d5db; background: #fff; border-radius: 999px; padding: .35rem .9rem; cursor: pointer; font-size: .95rem; font-weight: 600; color: #2563eb; }
  textarea { width: 100%; box-sizing: border-box; padding: .7rem; font-size: 1rem; border: 1px solid #d1d5db; border-radius: 8px; resize: vertical; }
  button.action { padding: .6rem 1.2rem; font-size: 1rem; border: 0; border-radius: 8px; cursor: pointer; background: #2563eb; color: #fff; margin-top: .5rem; }
  button.secondary { background: #6b7280; margin-left: .5rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; margin-top: 1.2rem; }
  .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: .9rem; background: #f9fafb; }
  .card h3 { margin: 0 0 .5rem; font-size: 1rem; }
  .badge { display: inline-block; padding: .15rem .6rem; border-radius: 999px; font-weight: 600; font-size: .85rem; }
  .positive { background: #dcfce7; color: #15803d; }
  .negative { background: #fee2e2; color: #b91c1c; }
  .neutral { background: #e5e7eb; color: #4b5563; }
  .conf { font-size: .85rem; color: #6b7280; margin-top: .3rem; }
  .bar { height: 10px; border-radius: 5px; background: #e5e7eb; margin: .25rem 0; overflow: hidden; }
  .bar span { display: block; height: 100%; background: #2563eb; }
  .reveal { font-size: .85rem; color: #6b7280; margin-top: .4rem; }
</style></head><body>
<div class="header"><h1 data-i18n="title">Aspect-Based Sentiment Analysis</h1><button class="lang" id="lang-toggle">English</button></div>
<p data-i18n="subtitle">Enter a restaurant review to analyze its sentiment across four aspects.</p>
<label data-i18n="reviewLabel">Review</label>
<textarea id="text" rows="4" data-i18n-ph="reviewPlaceholder"></textarea>
<div>
  <button class="action" id="predict" data-i18n="predict">Analyze</button>
  <button class="action secondary" id="demo" data-i18n="demo">Random demo sample</button>
</div>
<div class="grid" id="results"></div>
<script>
  const I18N = {
    en: {
      title: "Aspect-Based Sentiment Analysis",
      subtitle: "Enter a restaurant review to analyze its sentiment across four aspects.",
      reviewLabel: "Review",
      reviewPlaceholder: "The food was fantastic but the service was slow.",
      predict: "Analyze",
      demo: "Random demo sample",
      aspects: { food: "Taste / Food", service: "Service", price: "Price", ambience: "Ambience" },
      labels: { negative: "Negative", neutral: "Neutral", positive: "Positive" },
      confidence: "confidence",
      trueLabel: "True label",
      hit: "hit", miss: "miss",
      empty: "Please enter a review.",
      noDemo: "No demo samples available.",
    },
    zh: {
      title: "方面级情感分析",
      subtitle: "输入一条餐厅评论，分析其在四个方面的情感。",
      reviewLabel: "评论",
      reviewPlaceholder: "食物很棒，但服务太慢了。",
      predict: "分析",
      demo: "随机演示样本",
      aspects: { food: "口味", service: "服务", price: "价格", ambience: "环境" },
      labels: { negative: "负面", neutral: "中性", positive: "正面" },
      confidence: "置信度",
      trueLabel: "真实标签",
      hit: "命中", miss: "未命中",
      empty: "请输入评论。",
      noDemo: "暂无演示样本。",
    }
  };
  let lang = 'zh';
  let trueLabels = null;
  const results = document.getElementById('results');
  const t = () => I18N[lang];

  function applyLang() {
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t()[el.dataset.i18n]; });
    const ph = t()['reviewPlaceholder'];
    const ta = document.getElementById('text');
    ta.placeholder = ph;
    document.getElementById('lang-toggle').textContent = lang === 'zh' ? 'English' : '中文';
    if (lastResult) renderResult(lastResult);
  }
  document.getElementById('lang-toggle').addEventListener('click', () => { lang = lang === 'en' ? 'zh' : 'en'; applyLang(); });

  let lastResult = null;

  function renderResult(data) {
    lastResult = data;
    results.innerHTML = data.aspects.map(a => {
      const name = t().aspects[a.aspect] || a.aspect;
      const label = a.label ? t().labels[a.label] : '—';
      const cls = a.label || 'neutral';
      const bars = a.label ? Object.entries(a.distribution).map(([k, v]) =>
        '<div class="bar"><span style="width:' + (v * 100) + '%"></span></div>' +
        '<span>' + t().labels[k] + ': ' + (v * 100).toFixed(1) + '%</span>'
      ).join('') : '';
      const truth = trueLabels && trueLabels[a.aspect] ? '<div class="reveal">' + t().trueLabel + ': <b>' + t().labels[trueLabels[a.aspect]] + '</b> ' + (trueLabels[a.aspect] === a.label ? '(' + t().hit + ')' : '(' + t().miss + ')') + '</div>' : '';
      return '<div class="card"><h3>' + name + '</h3><span class="badge ' + cls + '">' + label + '</span>' +
        (a.confidence !== null ? '<div class="conf">' + t().confidence + ' ' + (a.confidence * 100).toFixed(1) + '%</div>' : '') +
        '<div style="margin-top:.3rem">' + bars + '</div>' + truth + '</div>';
    }).join('');
  }

  async function predict(text) {
    const res = await fetch('/predict', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text }) });
    if (!res.ok) { const e = await res.json(); results.innerHTML = '<p>' + (e.detail || t().empty) + '</p>'; lastResult = null; return; }
    const data = await res.json();
    trueLabels = null;
    renderResult(data);
  }

  document.getElementById('predict').addEventListener('click', () => predict(document.getElementById('text').value));
  document.getElementById('demo').addEventListener('click', async () => {
    const res = await fetch('/api/demo');
    if (!res.ok) { results.innerHTML = '<p>' + t().noDemo + '</p>'; lastResult = null; return; }
    const d = await res.json();
    document.getElementById('text').value = d.text;
    trueLabels = d.labels;
    predict(d.text);
  });
  applyLang();
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(_PAGE)


@app.post("/predict")
def predict_api(req: PredictRequest) -> JSONResponse:
    try:
        aspects = ml_model.predict_aspects(req.text)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse({"text": req.text, "aspects": aspects})


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
