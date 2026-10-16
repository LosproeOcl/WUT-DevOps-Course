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
    model: str = "tfidf"


@lru_cache(maxsize=1)
def load_demo_set() -> pd.DataFrame:
    if not os.path.exists(DEMO_CSV):
        return pd.DataFrame()
    return pd.read_csv(DEMO_CSV)


_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aspect-Based Sentiment Analysis</title>
<style>
  :root {
    --bg: #f5f6f7;
    --card: #ffffff;
    --text: #2c3e50;
    --muted: #7f8c9b;
    --border: #e6e8eb;
    --accent: #467b96;
    --accent-hover: #3a6b85;
    --positive: #16a34a; --positive-bg: #ecf7ef;
    --negative: #dc2626; --negative-bg: #fdf0ef;
    --neutral: #6b7280; --neutral-bg: #f3f4f6;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; line-height: 1.6; }
  .page { max-width: 760px; margin: 0 auto; padding: 2.5rem 1rem 4rem; }
  .site-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
  .site-title { margin: 0 0 .25rem; font-size: 1.6rem; font-weight: 700; }
  .site-desc { margin: 0; color: var(--muted); font-size: .92rem; }
  .lang { flex: 0 0 auto; margin-left: 1rem; padding: .35rem .9rem; border: 1px solid var(--border); background: var(--card); border-radius: 20px; cursor: pointer; font-size: .85rem; color: var(--accent); font-weight: 600; }
  .lang:hover { border-color: var(--accent); }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,.05); }
  label { display: block; font-size: .85rem; font-weight: 600; color: var(--muted); margin: .8rem 0 .35rem; }
  textarea, select { width: 100%; padding: .7rem .8rem; font-size: .95rem; border: 1px solid var(--border); border-radius: 8px; background: #fafbfc; color: var(--text); font-family: inherit; }
  textarea { min-height: 110px; resize: vertical; }
  textarea:focus, select:focus { outline: none; border-color: var(--accent); background: #fff; box-shadow: 0 0 0 3px rgba(70,123,150,.12); }
  .actions { display: flex; gap: .6rem; margin-top: 1.1rem; }
  .btn { display: inline-flex; align-items: center; gap: .5rem; padding: .6rem 1.3rem; font-size: .95rem; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: background .15s, opacity .15s; }
  .btn.primary { background: var(--accent); color: #fff; }
  .btn.primary:hover { background: var(--accent-hover); }
  .btn.primary:disabled { opacity: .6; cursor: not-allowed; }
  .btn.ghost { background: transparent; color: var(--accent); border: 1px solid var(--border); }
  .btn.ghost:hover { border-color: var(--accent); }
  .spinner { display: none; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.4); border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
  .spinner.ghost { border-color: rgba(70,123,150,.3); border-top-color: var(--accent); }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status { display: none; margin-top: 1rem; color: var(--muted); font-size: .88rem; }
  .status.show { display: block; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-top: 1.3rem; }
  .aspect-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1.1rem; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
  .aspect-card h3 { margin: 0 0 .5rem; font-size: .95rem; font-weight: 600; color: var(--text); }
  .badge { display: inline-block; padding: .18rem .7rem; border-radius: 20px; font-size: .82rem; font-weight: 600; }
  .badge.positive { background: var(--positive-bg); color: var(--positive); }
  .badge.negative { background: var(--negative-bg); color: var(--negative); }
  .badge.neutral { background: var(--neutral-bg); color: var(--neutral); }
  .conf { font-size: .8rem; color: var(--muted); margin-top: .45rem; }
  .bar { height: 7px; border-radius: 4px; background: #eef0f2; margin: .35rem 0; overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--accent); border-radius: 4px; transition: width .3s; }
  .dist { font-size: .78rem; color: var(--muted); }
  .reveal { font-size: .8rem; color: var(--muted); margin-top: .4rem; }
  .footnote { color: #a8b0ba; font-size: .78rem; margin-top: 1.6rem; text-align: center; }
  .error { color: var(--negative); }
  @media (max-width: 560px) { .grid { grid-template-columns: 1fr; } }
</style></head><body>
<div class="page">
  <header class="site-header">
    <div>
      <h1 class="site-title" data-i18n="title">Aspect-Based Sentiment Analysis</h1>
      <p class="site-desc" data-i18n="subtitle">Enter a restaurant review to analyze its sentiment across four aspects.</p>
    </div>
    <button class="lang" id="lang-toggle">English</button>
  </header>

  <main class="card">
    <label data-i18n="reviewLabel">Review</label>
    <textarea id="text" rows="4" data-i18n-ph="reviewPlaceholder"></textarea>
    <label data-i18n="modelLabel">Model</label>
    <select id="model">
      <option value="tfidf">TF-IDF + LR</option>
      <option value="bert">BERT (bert-base-chinese)</option>
      <option value="roberta">RoBERTa (chinese-wwm-ext)</option>
    </select>
    <div class="actions">
      <button class="btn primary" id="predict"><span class="spinner" id="spinner"></span><span data-i18n="predict">Analyze</span></button>
      <button class="btn ghost" id="demo" data-i18n="demo">Random demo sample</button>
    </div>
    <div class="status" id="status"></div>
  </main>

  <div class="grid" id="results"></div>
  <p class="footnote" data-i18n="footnote"></p>
</div>
<script>
  const I18N = {
    en: {
      title: "Aspect-Based Sentiment Analysis",
      subtitle: "Enter a restaurant review to analyze its sentiment across four aspects.",
      reviewLabel: "Review",
      modelLabel: "Model",
      reviewPlaceholder: "The food was fantastic but the service was slow.",
      predict: "Analyze",
      analyzing: "Analyzing...",
      demo: "Random demo sample",
      aspects: { food: "Taste / Food", service: "Service", price: "Price", ambience: "Ambience" },
      labels: { negative: "Negative", neutral: "Neutral", positive: "Positive" },
      confidence: "confidence",
      trueLabel: "True label",
      hit: "hit", miss: "miss",
      empty: "Please enter a review.",
      noDemo: "No demo samples available.",
      loading: "Loading model (first run may take a few seconds)...",
      footnote: "Model: TF-IDF + LR (default), BERT, RoBERTa. 'Neutral' means confidence is below threshold (uncertain).",
    },
    zh: {
      title: "方面级情感分析",
      subtitle: "输入一条餐厅评论，分析其在口味、服务、价格、环境四个方面的情感。",
      reviewLabel: "评论",
      modelLabel: "模型",
      reviewPlaceholder: "食物很棒，但服务太慢了。",
      predict: "分析",
      analyzing: "分析中…",
      demo: "随机演示样本",
      aspects: { food: "口味", service: "服务", price: "价格", ambience: "环境" },
      labels: { negative: "负面", neutral: "中性", positive: "正面" },
      confidence: "置信度",
      trueLabel: "真实标签",
      hit: "命中", miss: "未命中",
      empty: "请输入评论。",
      noDemo: "暂无演示样本。",
      loading: "正在加载模型（首次运行可能需要几秒）…",
      footnote: "模型：TF-IDF + 逻辑回归（默认）、BERT、RoBERTa。「中性」表示置信度低于阈值（不确定）。",
    }
  };
  let lang = 'zh';
  let trueLabels = null;
  let lastResult = null;
  const results = document.getElementById('results');
  const status = document.getElementById('status');
  const spinner = document.getElementById('spinner');
  const predictBtn = document.getElementById('predict');
  const t = () => I18N[lang];

  function applyLang() {
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t()[el.dataset.i18n]; });
    document.getElementById('text').placeholder = t()['reviewPlaceholder'];
    document.getElementById('lang-toggle').textContent = lang === 'zh' ? 'English' : '中文';
    if (lastResult) renderResult(lastResult);
  }
  document.getElementById('lang-toggle').addEventListener('click', () => { lang = lang === 'zh' ? 'en' : 'zh'; applyLang(); });

  function setLoading(on) {
    spinner.style.display = on ? 'inline-block' : 'none';
    predictBtn.disabled = on;
    predictBtn.querySelector('[data-i18n]').textContent = on ? t()['analyzing'] : t()['predict'];
  }

  function renderResult(data) {
    lastResult = data;
    results.innerHTML = data.aspects.map(a => {
      const name = t().aspects[a.aspect] || a.aspect;
      const label = a.label ? t().labels[a.label] : '—';
      const cls = a.label || 'neutral';
      const bars = a.label && Object.keys(a.distribution).length ? Object.entries(a.distribution).map(([k, v]) =>
        '<div class="bar"><span style="width:' + (v * 100) + '%"></span></div>' +
        '<span class="dist">' + t().labels[k] + ' ' + (v * 100).toFixed(1) + '%</span>'
      ).join('') : '';
      const truth = trueLabels && trueLabels[a.aspect] ? '<div class="reveal">' + t().trueLabel + ': <b>' + t().labels[trueLabels[a.aspect]] + '</b> ' + (trueLabels[a.aspect] === a.label ? '(' + t().hit + ')' : '(' + t().miss + ')') + '</div>' : '';
      return '<div class="aspect-card"><h3>' + name + '</h3><span class="badge ' + cls + '">' + label + '</span>' +
        (a.confidence !== null ? '<div class="conf">' + t().confidence + ' ' + (a.confidence * 100).toFixed(1) + '%</div>' : '') +
        '<div style="margin-top:.4rem">' + bars + '</div>' + truth + '</div>';
    }).join('');
  }

  async function predict(text) {
    if (!text.trim()) { status.className = 'status show error'; status.textContent = t().empty; return; }
    const model = document.getElementById('model').value;
    setLoading(true);
    status.className = 'status show';
    status.textContent = (model === 'tfidf') ? t().analyzing : t().loading;
    try {
      const res = await fetch('/predict', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text, model }) });
      const data = await res.json();
      if (!res.ok) { status.className = 'status show error'; status.textContent = data.detail || t().empty; lastResult = null; results.innerHTML = ''; return; }
      trueLabels = null;
      status.className = 'status';
      renderResult(data);
    } finally {
      setLoading(false);
    }
  }

  document.getElementById('predict').addEventListener('click', () => predict(document.getElementById('text').value));
  document.getElementById('demo').addEventListener('click', async () => {
    const res = await fetch('/api/demo');
    if (!res.ok) { status.className = 'status show error'; status.textContent = t().noDemo; return; }
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
        aspects = ml_model.predict_aspects(req.text, req.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse({"text": req.text, "model": req.model, "aspects": aspects})


@app.get("/models")
def models_api() -> JSONResponse:
    return JSONResponse(ml_model.AVAILABLE_MODELS)


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
