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

These are the decisions and detours that shaped the project, in the order they happened.

The assignment asked for a trained or fine-tuned model with dataset versioning, experiment tracking, Git, Docker, and CI/CD, plus an interactive demo that reserves part of the test set. Aspect-based sentiment analysis on restaurant reviews fits that brief: the demo is "type a review, get per-aspect sentiment", and the reserved-set requirement reduces to a small `demo.csv` held out of evaluation. That fit, not novelty, is why the topic was chosen.

The machine had to be fixed before any code ran. Five Python installations shared a single user site-packages, and an interrupted `pip` upgrade left `~umpy`, `~ip`, and `~crypt` folders behind, so `import sklearn` failed with `numpy.core.multiarray failed to import`. Consolidating on `C:\Python312` and deleting the leftovers took longer than expected, and it is the reason everything since has lived in a project-local `.venv` rather than the global environment.

The dataset was replaced twice. Work began with English SemEval-2014 restaurant reviews, but two requirements made that untenable: the app had to emit four fixed aspects, which meant moving from aspect-term to aspect-category labels, and the UI had to be bilingual with Chinese support. MAMS is the standard Chinese ABSA corpus, but it sits on Google Drive and is awkward to fetch. ASAP from Meituan-Dianping was the better choice — Chinese, on GitHub, roughly 46,850 reviews, 18 aspect categories that collapse neatly into the four, and an order of magnitude larger than SemEval. Chinese text is tokenized at the character level, which removes any dictionary dependency.

The model went through the most revisions. TF-IDF + LR was the first baseline, and its ~0.45 confidence was not a calibration problem but a symptom of the "neutral" class acting as a catch-all; dropping it in favor of binary positive/negative lifted both macro-F1 and confidence without any hand-tuning. A deep model still needed a GPU, which the laptop lacks, so an AutoDL box was rented for that. BiLSTM on CPU went nowhere — there was not enough data — but on AutoDL, fine-tuning BERT and RoBERTa paid off. They beat TF-IDF on ambiguous multi-aspect sentences, though not uniformly, and they are slow on CPU, so all three models remain, selectable at runtime, with TF-IDF as the default.

DVC's remote moved once. With no Azure account at the outset, a local directory served as a placeholder remote. After the Azure student account arrived, a Storage Account and container were created and the remote switched to Azure Blob. The first push timed out on the large files — an intermittent China-to-Azure latency issue — and succeeded on retry.

Experiment tracking followed the course's MLflow guide, local first, then DagsHub. That surfaced a version clash: MLflow 3.x calls a `CreateLoggedModel` endpoint that DagsHub's 2.x server does not implement, so the client is pinned to `mlflow<3`.

The application itself grew from a single `/predict` endpoint through four-aspect output, a bilingual UI, a model selector, CSV batch import/export, saved-review CRUD, and finally a split into two pages. The most irritating bug was a `'\n'` inside the Python triple-quoted HTML string that turned into a literal newline in the generated JavaScript and silently disabled every button; it was fixed with `String.fromCharCode`.

CI/CD is GitHub Actions, following the course guide: a pull request runs ruff, pytest, and a Docker build, and pushes to staging or main publish images. The image is `python:3.12-slim` with runtime dependencies only — torch and transformers are imported lazily so the image does not carry the two-gigabyte deep-learning stack.

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
