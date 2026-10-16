"""FastAPI application: interactive aspect-based sentiment analysis (4 aspects)."""
from __future__ import annotations

import io
import json
import os
import random
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
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


def _find_review_column(df: pd.DataFrame) -> str:
    for c in df.columns:
        if str(c).lower().strip() in ("review", "text", "comment", "content", "评论"):
            return c
    return df.columns[0]


_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aspect-Based Sentiment Analysis</title>
<style>
  :root {
    --bg: #f7f7f7; --card: #fff; --text: #444; --muted: #999;
    --border: #e5e5e5; --accent: #0068c1;
    --positive: #2e9e5b; --positive-bg: #eefaf1;
    --negative: #d9534f; --negative-bg: #fdf1f0;
    --neutral: #8a8a8a; --neutral-bg: #f4f4f4;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font-family: "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; font-size: 15px; line-height: 1.6; }
  .page { max-width: 760px; margin: 0 auto; padding: 2rem 1rem 3rem; }
  .site-header { margin-bottom: 1.4rem; }
  .site-header .row { display: flex; align-items: center; justify-content: space-between; }
  .site-title { margin: 0; font-size: 1.55rem; font-weight: 400; }
  .site-desc { margin: .2rem 0 0; color: var(--muted); font-size: .9rem; }
  .lang { flex: 0 0 auto; margin-left: 1rem; padding: .3rem .8rem; border: 1px solid var(--border); background: var(--card); border-radius: 4px; cursor: pointer; font-size: .85rem; color: var(--accent); }
  .lang:hover { border-color: var(--accent); }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 1.4rem; margin-bottom: 1.2rem; }
  label { display: block; font-size: .85rem; color: var(--muted); margin: .7rem 0 .3rem; }
  textarea, select, input[type=file] { width: 100%; padding: .55rem .7rem; font-size: .95rem; border: 1px solid var(--border); border-radius: 4px; background: #fff; color: var(--text); font-family: inherit; line-height: 1.5; }
  textarea { min-height: 100px; resize: vertical; line-height: 1.6; }
  textarea:focus, select:focus, input[type=file]:focus { outline: none; border-color: var(--accent); }
  .actions { display: flex; gap: .6rem; margin-top: 1rem; }
  .btn { display: inline-flex; align-items: center; gap: .5rem; padding: .5rem 1.2rem; font-size: .92rem; border: none; border-radius: 4px; cursor: pointer; transition: background .15s, opacity .15s; }
  .btn.primary { background: var(--accent); color: #fff; }
  .btn.primary:hover { background: #005aa8; }
  .btn.primary:disabled { opacity: .6; cursor: not-allowed; }
  .btn.ghost { background: #fff; color: var(--accent); border: 1px solid var(--border); }
  .btn.ghost:hover { border-color: var(--accent); }
  .spinner { display: none; width: 13px; height: 13px; border: 2px solid rgba(255,255,255,.4); border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status { display: none; margin-top: .8rem; color: var(--muted); font-size: .86rem; }
  .status.show { display: block; }
  .status.error { color: var(--negative); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-top: 1.2rem; }
  .aspect-card { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 1rem; }
  .aspect-card h3 { margin: 0 0 .45rem; font-size: .93rem; font-weight: 400; }
  .badge { display: inline-block; padding: .15rem .65rem; border-radius: 3px; font-size: .8rem; }
  .badge.positive { background: var(--positive-bg); color: var(--positive); }
  .badge.negative { background: var(--negative-bg); color: var(--negative); }
  .badge.neutral { background: var(--neutral-bg); color: var(--neutral); }
  .conf { font-size: .78rem; color: var(--muted); margin-top: .4rem; }
  .bar { height: 6px; border-radius: 3px; background: #eee; margin: .3rem 0; overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--accent); transition: width .3s; }
  .dist { font-size: .76rem; color: var(--muted); }
  .reveal { font-size: .78rem; color: var(--muted); margin-top: .35rem; }
  .footnote { color: #b0b0b0; font-size: .76rem; margin-top: 1.4rem; text-align: center; }
  .batch-hint { font-size: .82rem; color: var(--muted); margin-top: .5rem; }
  .progress { display: none; height: 6px; border-radius: 3px; background: #eee; margin-top: .8rem; overflow: hidden; }
  .progress.show { display: block; }
  .progress-fill { height: 100%; width: 0; background: var(--accent); transition: width .2s; }
  .progress-text { font-size: .8rem; color: var(--muted); margin-top: .3rem; }
  @media (max-width: 560px) { .grid { grid-template-columns: 1fr; } }
</style></head><body>
<div class="page">
  <header class="site-header">
    <div class="row">
      <h1 class="site-title" data-i18n="title">Aspect-Based Sentiment Analysis</h1>
      <button class="lang" id="lang-toggle">English</button>
    </div>
    <p class="site-desc" data-i18n="subtitle">Enter a restaurant review to analyze its sentiment across four aspects.</p>
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

  <section class="card">
    <label data-i18n="batchLabel">Batch import (CSV)</label>
    <input type="file" id="csv-file" accept=".csv">
    <div class="actions">
      <button class="btn ghost" id="template" data-i18n="template">Download template</button>
      <button class="btn ghost" id="batch" data-i18n="batch">Batch analyze</button>
    </div>
    <p class="batch-hint" data-i18n="batchHint"></p>
    <div class="progress" id="batch-progress"><div class="progress-fill" id="batch-progress-fill"></div></div>
    <div class="progress-text" id="batch-progress-text"></div>
    <div class="status" id="batch-status"></div>
  </section>

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
      batchLabel: "Batch import (CSV)",
      template: "Download template",
      batch: "Batch analyze",
      batchHint: "CSV needs a 'review' column. The result adds food/service/price/ambience sentiment columns.",
      aspects: { food: "Taste / Food", service: "Service", price: "Price", ambience: "Ambience" },
      labels: { negative: "Negative", neutral: "Neutral", positive: "Positive" },
      confidence: "confidence",
      trueLabel: "True label",
      hit: "hit", miss: "miss",
      empty: "Please enter a review.",
      noDemo: "No demo samples available.",
      loading: "Loading model (first run may take a few seconds)...",
      noFile: "Please choose a CSV file first.",
      batchDone: "Done, downloaded results.csv",
      footnote: "Models: TF-IDF + LR (default), BERT, RoBERTa. 'Neutral' means confidence below threshold.",
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
      batchLabel: "批量导入（CSV）",
      template: "下载模板",
      batch: "批量分析",
      batchHint: "CSV 需包含 review 列；结果会在原文件基础上新增 food/service/price/ambience 四列情感结果。",
      aspects: { food: "口味", service: "服务", price: "价格", ambience: "环境" },
      labels: { negative: "负面", neutral: "中性", positive: "正面" },
      confidence: "置信度",
      trueLabel: "真实标签",
      hit: "命中", miss: "未命中",
      empty: "请输入评论。",
      noDemo: "暂无演示样本。",
      loading: "正在加载模型（首次运行可能需要几秒）…",
      noFile: "请先选择 CSV 文件。",
      batchDone: "处理完成，已下载 results.csv",
      footnote: "模型：TF-IDF + 逻辑回归（默认）、BERT、RoBERTa。「中性」表示置信度低于阈值。",
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
  document.getElementById('template').addEventListener('click', () => { window.location.href = '/api/template'; });
  document.getElementById('batch').addEventListener('click', async () => {
    const file = document.getElementById('csv-file').files[0];
    const bs = document.getElementById('batch-status');
    const prog = document.getElementById('batch-progress');
    const fill = document.getElementById('batch-progress-fill');
    const ptext = document.getElementById('batch-progress-text');
    if (!file) { bs.className = 'status show error'; bs.textContent = t().noFile; return; }
    const fd = new FormData();
    fd.append('file', file);
    fd.append('model', document.getElementById('model').value);
    bs.className = 'status'; bs.textContent = '';
    prog.className = 'progress show'; fill.style.width = '0%'; ptext.textContent = '';
    try {
      const res = await fetch('/api/predict-csv', { method: 'POST', body: fd });
      if (!res.ok) { const e = await res.json().catch(() => ({})); bs.className = 'status show error'; bs.textContent = e.detail || 'error'; prog.className = 'progress'; return; }
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let nl;
        while ((nl = buffer.indexOf('\n')) >= 0) {
          const line = buffer.slice(0, nl).trim();
          buffer = buffer.slice(nl + 1);
          if (!line) continue;
          const msg = JSON.parse(line);
          if (msg.type === 'progress') {
            fill.style.width = Math.round(msg.done / msg.total * 100) + '%';
            ptext.textContent = msg.done + ' / ' + msg.total;
          } else if (msg.type === 'error') {
            bs.className = 'status show error'; bs.textContent = msg.detail;
          } else if (msg.type === 'result') {
            const blob = new Blob(['\uFEFF' + msg.csv], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = msg.filename; a.click();
            URL.revokeObjectURL(url);
            bs.className = 'status show'; bs.textContent = t().batchDone;
          }
        }
      }
      prog.className = 'progress';
    } catch (e) {
      bs.className = 'status show error'; bs.textContent = String(e);
      prog.className = 'progress';
    }
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


@app.get("/api/template")
def template_api() -> Response:
    csv_bytes = "review\n食物很好吃服务也很好\n价格有点贵环境一般般\n".encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template.csv"},
    )


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
        try:
            for idx, text in enumerate(df[review_col].astype(str)):
                aspects = ml_model.predict_aspects(text, model)
                for a in aspects:
                    out.at[idx, f"{a['aspect']}_sentiment"] = a["label"]
                yield json.dumps({"type": "progress", "done": idx + 1, "total": total}, ensure_ascii=False) + "\n"
        except FileNotFoundError as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False) + "\n"
            return
        yield json.dumps(
            {"type": "result", "filename": "results.csv", "csv": out.to_csv(index=False)},
            ensure_ascii=False,
        ) + "\n"

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
