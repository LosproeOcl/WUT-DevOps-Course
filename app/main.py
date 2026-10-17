"""FastAPI application: interactive aspect-based sentiment analysis (4 aspects).

Two pages:
    /          analyze page (single + batch CSV import)
    /history   saved-records page (view / edit / delete / batch-delete / export)
"""
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

from . import database
from . import model as ml_model
from .schemas import ReviewInput

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_CSV = os.path.join(_ROOT, "data", "demo.csv")
REVIEWS_DB_ENV = "REVIEWS_DB_PATH"
DEFAULT_DB = os.path.join(_ROOT, "reviews.db")

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


_CSS = """
  :root { --bg:#f7f7f7; --card:#fff; --text:#444; --muted:#999; --border:#e5e5e5; --accent:#0068c1;
    --positive:#2e9e5b; --positive-bg:#eefaf1; --negative:#d9534f; --negative-bg:#fdf1f0; --neutral:#8a8a8a; --neutral-bg:#f4f4f4; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font-family:"Helvetica Neue",Helvetica,Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; font-size:15px; line-height:1.6; }
  .page { max-width:760px; margin:0 auto; padding:2rem 1rem 3rem; }
  .site-header { margin-bottom:1.2rem; }
  .site-header .row { display:flex; align-items:center; justify-content:space-between; }
  .site-title { margin:0; font-size:1.5rem; font-weight:400; }
  .site-desc { margin:.2rem 0 .4rem; color:var(--muted); font-size:.9rem; }
  .nav { display:flex; gap:1rem; margin-top:.5rem; }
  .nav a { color:var(--muted); text-decoration:none; font-size:.9rem; padding:.2rem .1rem; border-bottom:2px solid transparent; }
  .nav a.active, .nav a:hover { color:var(--accent); border-bottom-color:var(--accent); }
  .lang { flex:0 0 auto; margin-left:1rem; padding:.3rem .8rem; border:1px solid var(--border); background:var(--card); border-radius:4px; cursor:pointer; font-size:.85rem; color:var(--accent); }
  .card { background:var(--card); border:1px solid var(--border); border-radius:4px; padding:1.4rem; margin-bottom:1.2rem; }
  label { display:block; font-size:.85rem; color:var(--muted); margin:.7rem 0 .3rem; }
  textarea, select, input[type=file] { width:100%; padding:.55rem .7rem; font-size:.95rem; border:1px solid var(--border); border-radius:4px; background:#fff; color:var(--text); font-family:inherit; line-height:1.5; }
  textarea { min-height:100px; resize:vertical; }
  textarea:focus, select:focus { outline:none; border-color:var(--accent); }
  .actions { display:flex; gap:.6rem; margin-top:1rem; flex-wrap:wrap; }
  .btn { display:inline-flex; align-items:center; gap:.5rem; padding:.5rem 1.2rem; font-size:.92rem; border:none; border-radius:4px; cursor:pointer; transition:background .15s,opacity .15s; }
  .btn.primary { background:var(--accent); color:#fff; }
  .btn.primary:hover { background:#005aa8; }
  .btn.primary:disabled { opacity:.6; cursor:not-allowed; }
  .btn.ghost { background:#fff; color:var(--accent); border:1px solid var(--border); }
  .btn.ghost:hover { border-color:var(--accent); }
  .btn.danger { background:#fff; color:var(--negative); border:1px solid var(--negative); }
  .spinner { display:none; width:13px; height:13px; border:2px solid rgba(255,255,255,.4); border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .status { display:none; margin-top:.8rem; color:var(--muted); font-size:.86rem; }
  .status.show { display:block; }
  .status.error { color:var(--negative); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:.9rem; margin-top:1.2rem; }
  .aspect-card { background:var(--card); border:1px solid var(--border); border-radius:4px; padding:1rem; }
  .aspect-card h3 { margin:0 0 .45rem; font-size:.93rem; font-weight:400; }
  .badge { display:inline-block; padding:.15rem .65rem; border-radius:3px; font-size:.8rem; }
  .badge.positive { background:var(--positive-bg); color:var(--positive); }
  .badge.negative { background:var(--negative-bg); color:var(--negative); }
  .badge.neutral { background:var(--neutral-bg); color:var(--neutral); }
  .conf { font-size:.78rem; color:var(--muted); margin-top:.4rem; }
  .bar { height:6px; border-radius:3px; background:#eee; margin:.3rem 0; overflow:hidden; }
  .bar span { display:block; height:100%; background:var(--accent); transition:width .3s; }
  .dist { font-size:.76rem; color:var(--muted); }
  .reveal { font-size:.78rem; color:var(--muted); margin-top:.35rem; }
  .rating { display:flex; align-items:center; gap:.5rem; margin-top:1.1rem; font-size:.95rem; }
  .rating-stars { color:#f5a623; letter-spacing:.1rem; }
  .rating-text { color:var(--muted); }
  .explain { margin-top:.4rem; font-size:.78rem; }
  .explain-pos { color:var(--positive); margin-right:.6rem; }
  .explain-neg { color:var(--negative); }
  .footnote { color:#b0b0b0; font-size:.76rem; margin-top:1.4rem; text-align:center; }
  .batch-hint { font-size:.82rem; color:var(--muted); margin-top:.5rem; }
  .progress { display:none; height:6px; border-radius:3px; background:#eee; margin-top:.8rem; overflow:hidden; }
  .progress.show { display:block; }
  .progress-fill { height:100%; width:0; background:var(--accent); transition:width .2s; }
  .progress-text { font-size:.8rem; color:var(--muted); margin-top:.3rem; }
  .toolbar { display:flex; gap:.6rem; margin-bottom:1rem; flex-wrap:wrap; align-items:center; }
  .history-item { border:1px solid var(--border); border-radius:4px; padding:.8rem; margin-bottom:.6rem; background:#fafafa; display:flex; gap:.7rem; align-items:flex-start; }
  .history-check { margin-top:.15rem; }
  .history-body { flex:1; min-width:0; }
  .history-text { font-size:.9rem; color:var(--text); margin-bottom:.4rem; word-break:break-all; }
  .history-tags { display:flex; flex-wrap:wrap; gap:.35rem; margin-bottom:.4rem; }
  .history-meta { font-size:.78rem; color:var(--muted); margin-bottom:.4rem; }
  .history-actions { display:flex; gap:.7rem; }
  .link { background:none; border:none; color:var(--accent); cursor:pointer; font-size:.82rem; padding:0; }
  .link:hover { text-decoration:underline; }
  .link.danger { color:var(--negative); }
  .empty-hint { color:var(--muted); font-size:.85rem; }
  @media (max-width:560px) { .grid { grid-template-columns:1fr; } }
"""

_I18N = """
  const I18N = {
    en: {
      title: "Aspect-Based Sentiment Analysis",
      subtitle: "Enter a restaurant review to analyze its sentiment across four aspects.",
      navAnalyze: "Analyze", navHistory: "History",
      reviewLabel: "Review", modelLabel: "Model",
      reviewPlaceholder: "The food was fantastic but the service was slow.",
      predict: "Analyze", analyzing: "Analyzing...", save: "Save result", demo: "Random demo sample",
      batchLabel: "Batch import (CSV)", template: "Download template", batch: "Batch analyze",
      batchHint: "CSV needs a 'review' column. Results are saved to history.",
      historyTitle: "Saved records", historySub: "Manage saved analyses: view, edit, delete, export.",
      selectAll: "Select all", exportCsv: "Export CSV", deleteSelected: "Delete selected", deleteAll: "Delete all",
      aspects: { food: "Taste", service: "Service", price: "Price", ambience: "Ambience" },
      labels: { negative: "Negative", neutral: "Neutral", positive: "Positive" },
      confidence: "confidence", trueLabel: "True label", hit: "hit", miss: "miss", ratingLabel: "Overall rating",
      empty: "Please enter a review.", noDemo: "No demo samples available.",
      loading: "Loading model (first run may take a few seconds)...",
      noFile: "Please choose a CSV file first.", batchDone: "Done, saved and downloaded results.csv",
      edit: "Edit", delete: "Delete", saved: "Saved.",
      emptyHistory: "No saved records yet.",
      confirmDeleteAll: "Delete all records?", noneSelected: "Select at least one record.",
      footnote: "Models: TF-IDF + LR (default), BERT, RoBERTa. 'Neutral' means confidence below threshold."
    },
    zh: {
      title: "方面级情感分析",
      subtitle: "输入一条餐厅评论，分析其在口味、服务、价格、环境四个方面的情感。",
      navAnalyze: "分析", navHistory: "历史记录",
      reviewLabel: "评论", modelLabel: "模型",
      reviewPlaceholder: "食物很棒，但服务太慢了。",
      predict: "分析", analyzing: "分析中…", save: "保存结果", demo: "随机演示样本",
      batchLabel: "批量导入（CSV）", template: "下载模板", batch: "批量分析",
      batchHint: "CSV 需包含 review 列；结果会同时保存到历史记录。",
      historyTitle: "历史记录", historySub: "管理已保存的分析：查看、编辑、删除、导出。",
      selectAll: "全选", exportCsv: "导出 CSV", deleteSelected: "删除选中", deleteAll: "删除全部",
      aspects: { food: "口味", service: "服务", price: "价格", ambience: "环境" },
      labels: { negative: "负面", neutral: "中性", positive: "正面" },
      confidence: "置信度", trueLabel: "真实标签", hit: "命中", miss: "未命中", ratingLabel: "整体评分",
      empty: "请输入评论。", noDemo: "暂无演示样本。",
      loading: "正在加载模型（首次运行可能需要几秒）…",
      noFile: "请先选择 CSV 文件。", batchDone: "处理完成，已保存并下载 results.csv",
      edit: "编辑", delete: "删除", saved: "已保存。",
      emptyHistory: "暂无保存的记录。",
      confirmDeleteAll: "确定删除全部记录？", noneSelected: "请至少选择一条记录。",
      footnote: "模型：TF-IDF + 逻辑回归（默认）、BERT、RoBERTa。「中性」表示置信度低于阈值。"
    }
  };
  let lang = 'zh';
  const t = () => I18N[lang];
  function applyLang() {
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t()[el.dataset.i18n]; });
    const ta = document.getElementById('text');
    if (ta) ta.placeholder = t()['reviewPlaceholder'];
    const lt = document.getElementById('lang-toggle');
    if (lt) lt.textContent = lang === 'zh' ? 'English' : '中文';
  }
  document.getElementById('lang-toggle').addEventListener('click', () => { lang = lang === 'zh' ? 'en' : 'zh'; applyLang(); if (typeof afterLang === 'function') afterLang(); });
"""

_HEADER = """
  <header class="site-header">
    <div class="row"><h1 class="site-title" data-i18n="title">Aspect-Based Sentiment Analysis</h1><button class="lang" id="lang-toggle">English</button></div>
    <p class="site-desc" data-i18n="subtitle">Enter a restaurant review to analyze its sentiment across four aspects.</p>
    <nav class="nav"><a href="/" id="nav-analyze" data-i18n="navAnalyze">Analyze</a><a href="/history" id="nav-history" data-i18n="navHistory">History</a></nav>
  </header>
"""

_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aspect-Based Sentiment Analysis</title><style>""" + _CSS + """</style></head><body>
<div class="page">""" + _HEADER + """
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
      <button class="btn ghost" id="save" data-i18n="save">Save result</button>
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

  <div id="rating"></div>
  <div class="grid" id="results"></div>
  <p class="footnote" data-i18n="footnote"></p>
</div>
<script>""" + _I18N + """
  document.getElementById('nav-analyze').classList.add('active');
  let trueLabels = null, lastResult = null, editingId = null;
  const results = document.getElementById('results');
  const status = document.getElementById('status');
  const spinner = document.getElementById('spinner');
  const predictBtn = document.getElementById('predict');

  function setLoading(on) {
    spinner.style.display = on ? 'inline-block' : 'none';
    predictBtn.disabled = on;
    predictBtn.querySelector('[data-i18n]').textContent = on ? t()['analyzing'] : t()['predict'];
  }

  function renderResult(data) {
    lastResult = data;
    const rating = document.getElementById('rating');
    if (data.rating && data.rating.star) {
      const stars = '★'.repeat(data.rating.star) + '☆'.repeat(5 - data.rating.star);
      rating.innerHTML = '<div class="rating"><span class="rating-stars">' + stars + '</span>' +
        '<span class="rating-text">' + t().ratingLabel + ': ' + data.rating.star + ' / 5</span></div>';
    } else {
      rating.innerHTML = '';
    }
    const expMap = {};
    (data.explanation || []).forEach(e => { expMap[e.aspect] = e; });
    results.innerHTML = data.aspects.map(a => {
      const name = t().aspects[a.aspect] || a.aspect;
      const label = a.label ? t().labels[a.label] : '—';
      const cls = a.label || 'neutral';
      const bars = a.label && Object.keys(a.distribution).length ? Object.entries(a.distribution).map(([k, v]) =>
        '<div class="bar"><span style="width:' + (v * 100) + '%"></span></div>' +
        '<span class="dist">' + t().labels[k] + ' ' + (v * 100).toFixed(1) + '%</span>').join('') : '';
      const exp = expMap[a.aspect];
      let explain = '';
      if (exp && (exp.positive.length || exp.negative.length)) {
        const pos = exp.positive.map(x => x[0]).join(' ');
        const neg = exp.negative.map(x => x[0]).join(' ');
        explain = '<div class="explain">' +
          (exp.positive.length ? '<span class="explain-pos">+ ' + pos + '</span>' : '') +
          (exp.negative.length ? '<span class="explain-neg">- ' + neg + '</span>' : '') +
          '</div>';
      }
      const truth = trueLabels && trueLabels[a.aspect] ? '<div class="reveal">' + t().trueLabel + ': <b>' + t().labels[trueLabels[a.aspect]] + '</b> ' + (trueLabels[a.aspect] === a.label ? '(' + t().hit + ')' : '(' + t().miss + ')') + '</div>' : '';
      return '<div class="aspect-card"><h3>' + name + '</h3><span class="badge ' + cls + '">' + label + '</span>' +
        (a.confidence !== null ? '<div class="conf">' + t().confidence + ' ' + (a.confidence * 100).toFixed(1) + '%</div>' : '') +
        '<div style="margin-top:.4rem">' + bars + '</div>' + explain + truth + '</div>';
    }).join('');
  }

  async function predict(text) {
    if (!text.trim()) { status.className = 'status show error'; status.textContent = t().empty; return; }
    const model = document.getElementById('model').value;
    setLoading(true);
    status.className = 'status show'; status.textContent = (model === 'tfidf') ? t().analyzing : t().loading;
    try {
      const res = await fetch('/predict', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text: text, model: model }) });
      const data = await res.json();
      if (!res.ok) { status.className = 'status show error'; status.textContent = data.detail || t().empty; lastResult = null; results.innerHTML = ''; return; }
      trueLabels = null; status.className = 'status'; renderResult(data);
    } finally { setLoading(false); }
  }

  async function saveReview() {
    const text = document.getElementById('text').value;
    const model = document.getElementById('model').value;
    if (!text.trim()) { status.className = 'status show error'; status.textContent = t().empty; return; }
    const url = editingId ? ('/api/reviews/' + editingId) : '/api/reviews';
    const method = editingId ? 'PUT' : 'POST';
    const res = await fetch(url, { method: method, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text: text, model: model }) });
    if (!res.ok) { const e = await res.json().catch(() => ({})); status.className = 'status show error'; status.textContent = e.detail || 'error'; return; }
    editingId = null; status.className = 'status show'; status.textContent = t().saved;
  }

  function editReview(id) {
    fetch('/api/reviews/' + id).then(r => r.json()).then(rv => {
      document.getElementById('text').value = rv.text;
      document.getElementById('model').value = rv.model;
      editingId = id;
      predict(rv.text);
    });
  }

  document.getElementById('predict').addEventListener('click', () => predict(document.getElementById('text').value));
  document.getElementById('save').addEventListener('click', saveReview);
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
      const NL = String.fromCharCode(10);
      while (true) {
        const r2 = await reader.read();
        if (r2.done) break;
        buffer += decoder.decode(r2.value, { stream: true });
        let nl;
        while ((nl = buffer.indexOf(NL)) >= 0) {
          const line = buffer.slice(0, nl).trim(); buffer = buffer.slice(nl + 1);
          if (!line) continue;
          const msg = JSON.parse(line);
          if (msg.type === 'progress') { fill.style.width = Math.round(msg.done / msg.total * 100) + '%'; ptext.textContent = msg.done + ' / ' + msg.total; }
          else if (msg.type === 'error') { bs.className = 'status show error'; bs.textContent = msg.detail; }
          else if (msg.type === 'result') {
            const blob = new Blob([String.fromCharCode(65279) + msg.csv], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = msg.filename; a.click();
            URL.revokeObjectURL(url);
            bs.className = 'status show'; bs.textContent = t().batchDone;
          }
        }
      }
      prog.className = 'progress';
    } catch (e) { bs.className = 'status show error'; bs.textContent = String(e); prog.className = 'progress'; }
  });

  const params = new URLSearchParams(window.location.search);
  const editParam = params.get('edit');
  if (editParam) editReview(parseInt(editParam, 10));
  applyLang();
</script>
</body></html>"""

_HISTORY_PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>History</title><style>""" + _CSS + """</style></head><body>
<div class="page">""" + _HEADER + """
  <h2 style="margin:.5rem 0 .2rem;font-weight:400" data-i18n="historyTitle">Saved records</h2>
  <p style="color:#999;font-size:.85rem;margin:0 0 1rem" data-i18n="historySub">Manage saved analyses.</p>
  <div class="toolbar">
    <button class="btn ghost" id="select-all" data-i18n="selectAll">Select all</button>
    <button class="btn ghost" id="export" data-i18n="exportCsv">Export CSV</button>
    <button class="btn danger" id="delete-selected" data-i18n="deleteSelected">Delete selected</button>
    <button class="btn danger" id="delete-all" data-i18n="deleteAll">Delete all</button>
  </div>
  <div id="history"></div>
  <p class="footnote" data-i18n="footnote"></p>
</div>
<script>""" + _I18N + """
  document.getElementById('nav-history').classList.add('active');
  const historyEl = document.getElementById('history');
  let allSelected = false;

  function escapeHtml(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  function renderHistory(reviews) {
    if (!reviews.length) { historyEl.innerHTML = '<p class="empty-hint">' + t().emptyHistory + '</p>'; return; }
    historyEl.innerHTML = reviews.map(r => {
      const tags = ['food', 'service', 'price', 'ambience'].map(a => {
        const lbl = r[a + '_label'] || 'neutral';
        return '<span class="badge ' + lbl + '">' + t().aspects[a] + ' ' + t().labels[lbl] + '</span>';
      }).join('');
      const conf = ['food', 'service', 'price', 'ambience'].map(a => {
        const c = r[a + '_confidence'] || 0;
        return t().aspects[a] + ' ' + (c * 100).toFixed(0) + '%';
      }).join(' / ');
      return '<div class="history-item">' +
        '<input type="checkbox" class="history-check" data-id="' + r.id + '">' +
        '<div class="history-body">' +
        '<div class="history-text">' + escapeHtml(r.text) + '</div>' +
        '<div class="history-tags">' + tags + '</div>' +
        '<div class="history-meta">' + escapeHtml(r.model) + ' · ' + conf + '</div>' +
        '<div class="history-actions">' +
        '<a class="link" href="/?edit=' + r.id + '">' + t().edit + '</a>' +
        '<button class="link danger" data-del="' + r.id + '">' + t().delete + '</button>' +
        '</div></div></div>';
    }).join('');
  }

  async function loadHistory() {
    const res = await fetch('/api/reviews');
    const reviews = await res.json();
    renderHistory(reviews);
  }

  function selectedIds() {
    return Array.from(document.querySelectorAll('.history-check:checked')).map(c => parseInt(c.dataset.id, 10));
  }

  async function deleteReview(id) {
    await fetch('/api/reviews/' + id, { method: 'DELETE' });
    loadHistory();
  }

  document.getElementById('export').addEventListener('click', () => { window.location.href = '/api/reviews/export'; });
  document.getElementById('select-all').addEventListener('click', () => {
    allSelected = !allSelected;
    document.querySelectorAll('.history-check').forEach(c => { c.checked = allSelected; });
  });
  document.getElementById('delete-selected').addEventListener('click', async () => {
    const ids = selectedIds();
    if (!ids.length) { alert(t().noneSelected); return; }
    await fetch('/api/reviews/batch-delete', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ ids: ids }) });
    loadHistory();
  });
  document.getElementById('delete-all').addEventListener('click', async () => {
    if (!confirm(t().confirmDeleteAll)) return;
    await fetch('/api/reviews/batch-delete', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ all: true }) });
    loadHistory();
  });
  historyEl.addEventListener('click', function (ev) {
    const delBtn = ev.target.closest('[data-del]');
    if (delBtn) deleteReview(parseInt(delBtn.dataset.del, 10));
  });

  loadHistory();
  applyLang();
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(_PAGE)


@app.get("/history", response_class=HTMLResponse, include_in_schema=False)
def history_page() -> HTMLResponse:
    return HTMLResponse(_HISTORY_PAGE)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
