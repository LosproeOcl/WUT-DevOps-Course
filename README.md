# Aspect-Based Sentiment Analysis

> [中文版 README](README_zh.md)

A web app that takes a Chinese restaurant review and classifies its sentiment across four aspects — **taste / service / price / ambience** — each marked positive, negative, or neutral.

This is the final project for a DevOps & MLOps course. It ended up as a small end-to-end MLOps pipeline: DVC for data, MLflow for experiments, Docker + GitHub Actions for CI/CD, and a FastAPI app with a bilingual UI, three selectable models, CSV batch import/export, and CRUD for saved results.

## What the app does

- Two pages: `/` (analyze) and `/history` (saved records).
- One review in → four aspects with label + confidence + probability bars.
- Three models to choose from: TF-IDF + LR, BERT, RoBERTa.
- CSV upload → batch-analyze each row, save results, download a CSV with original columns plus sentiment/confidence/probability columns.
- Saved results live in SQLite, managed on `/history`: view, edit, single/batch delete, export CSV.
- UI switches between Chinese and English.

## Repo layout

```
app/                 FastAPI app
  main.py            routes + the two HTML pages
  model.py           model loading + inference (tfidf / bert / roberta)
  database.py        SQLite layer for saved reviews
  schemas.py         Pydantic models
ml/                  training + data code
  data_pipeline.py   ASAP CSV -> (text, aspect, polarity) rows, v1/v2
  train.py           TF-IDF + LR, logs to MLflow
  train_lstm.py      BiLSTM (PyTorch)
  train_bert.py      BERT/RoBERTa fine-tuning
  aspects.py         aspect mapping + tokenizer
data/                raw/ processed/ (DVC), demo.csv
models/              trained weights (tfidf committed; bert/roberta/lstm gitignored)
tests/               pytest unit + API tests
.github/workflows/ci.yml
Dockerfile
```

## Development notes

Topic selection was constrained by hardware. The machine has only a CPU, and renting compute was not planned at the outset; single-aspect sentiment classification was too basic, so multi-aspect sentiment analysis was chosen to deliver a complete result within the assignment window. Restaurant reviews fit the need for an interactive demo with a reserved test set.

The machine was fixed before development began. Five Python installations shared one user site-packages, and an interrupted pip upgrade left `~umpy`, `~ip`, and `~crypt` directories, so `import sklearn` raised `numpy.core.multiarray failed to import`. After consolidating on `C:\Python312`, removing the leftovers, and reinstalling numpy, all work moved into a project-local `.venv`.

The dataset changed twice. Starting from English SemEval-2014, the four-aspect output and bilingual UI were settled during development, moving labels from aspect-term to aspect-category and introducing Chinese data. MAMS is hosted on Google Drive and hard to fetch; ASAP from Meituan-Dianping was adopted instead — Chinese, on GitHub, roughly 46,850 reviews, 18 categories collapsed into four aspects, an order of magnitude larger than SemEval. Chinese is segmented at the character level, which removes the dictionary dependency.

The model saw the most iterations. The TF-IDF + LR baseline reported ~0.45 confidence, caused by a noisy neutral class; collapsing to binary classification and labelling low-confidence predictions neutral lifted both macro-F1 and confidence. A deep model requires a GPU, which the machine lacks; BiLSTM trained on CPU fell short for lack of samples, so an AutoDL RTX 3080 Ti was rented for 5 yuan to fine-tune BERT and RoBERTa. The latter beat the baseline on mixed multi-aspect sentences without leading across the board, and their CPU inference cost is high, so all three models remain, switchable at runtime with TF-IDF as default.

DVC's remote moved once. With no Azure account initially, a local directory served as a placeholder; after obtaining a student account, a Storage Account and container were created and the remote switched to Azure Blob. The first push hit socket timeouts on the large files — intermittent China-to-Azure latency — and finished on retry.

Experiment tracking follows the course MLflow guide, local first, then DagsHub; MLflow 3.x's `CreateLoggedModel` endpoint is not implemented by DagsHub's 2.x server, so the client is pinned to `mlflow<3`.

The app expanded from a single `/predict` endpoint to four-aspect output, a bilingual UI, model switching, CSV batch import/export, record CRUD, and finally two pages. One subtle failure: a `'\n'` in the Python triple-quoted string became a literal newline in the generated JavaScript and broke the script, avoided with `String.fromCharCode`.

CI/CD uses GitHub Actions: pull requests run ruff, pytest, and a Docker build; pushes to staging or main publish images. The image is `python:3.12-slim` with runtime dependencies only, with torch and transformers lazy-imported.

## Environment

Python 3.12 in a project venv:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-ml.txt -r requirements-dev.txt
```

| File | Purpose |
|------|---------|
| `requirements.txt` | runtime (fastapi, uvicorn, joblib, scikit-learn, numpy, pandas, python-multipart) |
| `requirements-ml.txt` | training + deep-model serving (mlflow<3, matplotlib, dagshub, torch, transformers) |
| `requirements-dev.txt` | pytest, httpx, ruff |

Environment variables (tokens stay out of git):

| Variable | Meaning |
|----------|---------|
| `DAGSHUB_REPO_OWNER` / `DAGSHUB_REPO_NAME` | DagsHub repo, e.g. `losproeocl` / `WUT-DevOps-Course` |
| `MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD` | DagsHub username / access token |
| `REVIEWS_DB_PATH` | optional; path to the saved-reviews SQLite DB |
| `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` | GitHub Actions secrets for image publishing |

## Data

ASAP (Meituan-Dianping/asap), ~46,850 Chinese reviews, 18 aspect categories mapped to four:

| Aspect | ASAP categories |
|--------|-----------------|
| taste | Food#Portion, Food#Taste, Food#Appearance, Food#Recommend |
| service | Service#Queue, Service#Hospitality, Service#Parking, Service#Timely |
| price | Price#Level, Price#Cost_effective, Price#Discount |
| ambience | Ambience#Decoration, Ambience#Noise, Ambience#Space, Ambience#Sanitary |

Polarity is `1`/`0`/`-1` (`-2` = not mentioned, dropped). DVC tracks `data/raw` and `data/processed`, remote on Azure Blob:

```bash
dvc remote add -d myazure azure://efreiwut-projdvc
dvc remote modify myazure account_name efreiwut2026dvc
dvc remote modify --local myazure connection_string "<secret>"   # .dvc/config.local, gitignored
dvc push
```

Two versions: `v1` (raw) and `v2` (char-tokenized + deduplicated).

## Models and training

Binary per aspect (positive vs negative); the "neutral" class is dropped at training time, and low-confidence predictions are reported as neutral.

| Model | Where | macro-F1 (taste/service/price/ambience) |
|-------|-------|------------------------------------------|
| TF-IDF + LR (tuned) | CPU, `ml/train.py` | 0.738 / 0.784 / 0.786 / 0.760 |
| BiLSTM | CPU, `ml/train_lstm.py` | weaker on this data |
| BERT (bert-base-chinese, 3 ep) | AutoDL GPU, `ml/train_bert.py` | 0.758 / 0.806 / 0.758 / 0.824 |
| RoBERTa (chinese-wwm-ext, 3 ep) | AutoDL GPU | 0.765 / 0.803 / 0.763 / 0.789 |

```bash
python -m ml.data_pipeline              # build v1/v2 CSVs
python -m ml.train --data-version v2 --mode tuned   # TF-IDF + LR, logs to MLflow
python -m ml.train_lstm --data-version v2           # BiLSTM
python -m ml.train_bert --data-dir data --epochs 3  # BERT/RoBERTa (GPU recommended)
```

Registered on DagsHub: `absa_restaurant` (unified TF-IDF+LR), `absa_restaurant_lstm`, `absa_restaurant_bert`, `absa_restaurant_roberta`.

## Course requirements, mapped

| Requirement (from `project-instructions.pdf`) | Where it's met |
|-----------------------------------------------|----------------|
| Train or fine-tune a model | BERT/RoBERTa fine-tuned on GPU |
| Dataset with multiple versions | ASAP, DVC `v1`/`v2` |
| 3+ tests with edge cases | 33 pytest tests (unit + API) |
| Git branching (main/staging/dev) | plus `finalProject_sentimentAnalysis` |
| Docker (slim Dockerfile + .dockerignore) | `python:3.12-slim`, `.dockerignore` |
| CI/CD (PR: test+lint+docker build, deploy) | `.github/workflows/ci.yml` |
| DVC (Azure remote, 2+ versions) | Azure Blob, `v1`/`v2` |
| MLflow (2+ experiments, registry) | baseline vs tuned; model registry on DagsHub |
| Interactive app + reserved test set | `data/demo.csv`, held out of evaluation |

## Bugs, quick reference

- `numpy.core.multiarray failed to import` → multiple Pythons sharing user site + `~` leftovers; consolidated on C:\Python312 and deleted them.
- Confidence ~0.45 → "neutral" was a catch-all; went binary.
- Small data capped models → switched to ASAP (~10x bigger).
- `CreateLoggedModel` → `INVALID_PARAMETER_VALUE` → pin `mlflow<3` (DagsHub server is 2.x).
- `process() takes no keyword arguments` on AutoDL → `wget` the model from hf-mirror, load from a local path.
- Empty TF-IDF features for Chinese → `token_pattern=r"\S+"` (default drops single CJK chars).
- JS buttons dead → `'\n'` in the triple-quoted HTML became a real newline; use `String.fromCharCode(10)`.
- 400 MB weights → gitignored (LSTM DVC-tracked; TF-IDF ~30 MB committed).
- 5 epochs overfit → 3 is the sweet spot.
- Azure push timeout → intermittent, retry.

## Running

```bash
python -m uvicorn app.main:app --reload      # or: python -m app.main
# http://127.0.0.1:8000 (analyze)  /history (saved records)

docker build -t absa-app .
docker run -p 8000:8000 absa-app
```

Tests: `python -m pytest`; lint: `ruff check app ml tests scripts`.
