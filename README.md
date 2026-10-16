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

## Project journey

Written in the order things actually happened, decisions included.

### 1. Picking a topic

The assignment (see `PracticeIntro/project-instructions.pdf`) asked for an ML app that trains or fine-tunes a model, with dataset versioning, experiment tracking, Git, Docker, and CI/CD, plus an interactive demo that reserves part of the test set. Aspect-based sentiment analysis on restaurant reviews fits well: the demo is "type a review, get per-aspect sentiment", and the reserved-set requirement is naturally a small `demo.csv` held out of evaluation.

### 2. Local environment

Before any code, the machine itself was broken. It had five Python installs (Microsoft Store 3.11, `C:\Python312`, Anaconda, 3.8, a VS-bundled 3.9) sharing one user site-packages, plus `~umpy`/`~ip`/`~crypt` folders left by an interrupted `pip` upgrade. `import sklearn` died with `numpy.core.multiarray failed to import`. I consolidated everything onto `C:\Python312`, deleted the `~`-prefixed leftovers, and reinstalled numpy. That one fix took longer than expected and shaped the rest of the project: from then on I used a project-local `.venv`.

### 3. Data: from English to Chinese

I started with SemEval-2014 restaurant reviews (English). Two requirements forced a rethink:

- The app must output **four fixed aspects** (taste/service/price/ambience), so I moved from aspect-term to aspect-category labeling.
- The UI must be bilingual and support Chinese input, so I needed a Chinese dataset.

MAMS (siat-nlp) is the canonical Chinese ABSA dataset, but the actual corpus is on Google Drive and hard to fetch. **ASAP** (Meituan-Dianping) turned out to be the better fit: Chinese, hosted on GitHub, ~46,850 reviews, with 18 aspect categories that map cleanly to the four aspects, and about 10x larger than SemEval. Chinese text is tokenized at the character level — fast, no dictionary dependency, small vocab.

### 4. Models: TF-IDF → LSTM → BERT/RoBERTa

TF-IDF + LR came first. Its confidence numbers were ~0.45, which turned out to be honest: the "neutral" class was a catch-all. Dropping neutral and going binary (positive/negative) raised both macro-F1 and confidence without any inflation. Calibrating or forcing higher confidence only made numbers look good while hurting F1, so I skipped that.

Then I wanted a deep model to beat it. My laptop has no NVIDIA GPU (Intel Iris Xe only), and fine-tuning a transformer on CPU would take hours, so I rented an **AutoDL** box (RTX 3080 Ti, pay-by-hour). I tried BiLSTM on CPU first — it underperformed because there wasn't enough data. On AutoDL I fine-tuned BERT (`bert-base-chinese`) and RoBERTa (`chinese-roberta-wwm-ext`).

The result: BERT/RoBERTa beat TF-IDF on ambiguous multi-aspect sentences but not everywhere, and they're slow on CPU. So I **kept all three** behind a model selector — TF-IDF as the fast default, BERT/RoBERTa as options when accuracy matters more than speed.

### 5. DVC: local directory → Azure Blob

At first I had no Azure account, so I pointed DVC at a local directory to simulate a remote. The course guide (`7. DVC-with-Azure-Blob-Storage.pdf`) assumes Azure. Later I got an Azure student account (EFREI email, $100 credit), created a Storage Account and a blob container, and switched the remote to Azure Blob. First `dvc push` hit `Timeout on reading data from socket` on the large files — an intermittent China-to-Azure issue — and retrying finished it.

### 6. MLflow + DagsHub

Following the course's MLflow guide (`15-MLFlow.pdf`), I used local tracking first, then pointed MLflow at DagsHub. That surfaced a version clash: MLflow 3.x uses a `CreateLoggedModel` endpoint that DagsHub's 2.x server doesn't support (`INVALID_PARAMETER_VALUE`), so I pinned `mlflow<3`. Runs and registered models now land on DagsHub.

### 7. The app grew

It started as a single `/predict` endpoint and accumulated: 4-aspect output, bilingual UI, a model selector, CSV batch import/export, saved-review CRUD, and finally a split into two pages (analyze + history). Along the way a `'\n'` inside the Python triple-quoted HTML string became a literal newline in the generated JS and silently broke every button — replaced with `String.fromCharCode(10)`.

### 8. CI/CD

GitHub Actions per the course guide (`3-1. GITHUB_ACTIONS_GUIDE.pdf`): a PR to the protected branches runs ruff + pytest + a Docker build; pushing to `staging`/`main` publishes images. The Docker image is `python:3.12-slim` with runtime deps only — torch/transformers are lazy-imported so the image doesn't carry the ~2 GB deep-learning stack.

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
