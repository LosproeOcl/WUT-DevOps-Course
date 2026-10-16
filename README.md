# Aspect-Based Sentiment Analysis

> [中文版 README](README_zh.md)

A web app that takes a Chinese restaurant review and classifies its sentiment across four aspects — **taste / service / price / ambience** — each marked positive, negative, or neutral.

It started as the final project for a DevOps & MLOps course. Along the way it turned into a small but complete MLOps pipeline: DVC for data, MLflow for experiments, Docker + GitHub Actions for CI/CD, and a FastAPI app with a bilingual UI, three selectable models, CSV batch import/export, and CRUD for saved results.

## What the app does

- Two pages: `/` (analyze) and `/history` (saved records).
- Enter one review → four aspects with label + confidence + probability bars.
- Pick a model: TF-IDF + LR, BERT, or RoBERTa.
- Upload a CSV → batch-analyze every row, save results, download a CSV with the original columns plus sentiment/confidence/probability columns.
- Saved results go to a SQLite database, managed on `/history`: view, edit, single/batch delete, export CSV.
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

## Environment

Python 3.12 in a project venv:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-ml.txt -r requirements-dev.txt
```

Three requirement files, split by purpose:

| File | What it's for |
|------|---------------|
| `requirements.txt` | runtime only (fastapi, uvicorn, joblib, scikit-learn, numpy, pandas, python-multipart) |
| `requirements-ml.txt` | training + deep-model serving (mlflow<3, matplotlib, dagshub, torch, transformers) |
| `requirements-dev.txt` | pytest, httpx, ruff |

Environment variables for DagsHub tracking (tokens stay out of git):

| Variable | Meaning |
|----------|---------|
| `DAGSHUB_REPO_OWNER` / `DAGSHUB_REPO_NAME` | DagsHub repo, e.g. `losproeocl` / `WUT-DevOps-Course` |
| `MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD` | DagsHub username / access token |

## Data

Dataset is **ASAP** (Meituan-Dianping/asap): ~46,850 Chinese restaurant reviews, each annotated with 18 fine-grained aspect categories. `ml/aspects.py` maps them to the four coarse aspects:

| Aspect | ASAP categories |
|--------|-----------------|
| taste | Food#Portion, Food#Taste, Food#Appearance, Food#Recommend |
| service | Service#Queue, Service#Hospitality, Service#Parking, Service#Timely |
| price | Price#Level, Price#Cost_effective, Price#Discount |
| ambience | Ambience#Decoration, Ambience#Noise, Ambience#Space, Ambience#Sanitary |

Polarity is `1`/`0`/`-1` (`-2` means "not mentioned" and is dropped). Chinese is tokenized at the character level — fast, no dictionary dependency, small vocab.

DVC tracks `data/raw` and `data/processed`. The remote is Azure Blob Storage:

```bash
dvc remote add -d myazure azure://efreiwut-projdvc
dvc remote modify myazure account_name efreiwut2026dvc
dvc remote modify --local myazure connection_string "<secret>"   # goes to .dvc/config.local, gitignored
dvc push
```

Two processed versions exist: `v1` (raw text) and `v2` (char-tokenized + deduplicated).

## Models and training

Three models were tried. The task is binary per aspect (positive vs negative); the murky "neutral" class is dropped at training time, and predictions below a confidence threshold are reported as neutral.

| Model | Where | macro-F1 (food/service/price/ambience) |
|-------|-------|------------------------------------------|
| TF-IDF + LR (tuned) | CPU, `ml/train.py` | 0.738 / 0.784 / 0.786 / 0.760 |
| BiLSTM | CPU, `ml/train_lstm.py` | weaker on this data |
| BERT (bert-base-chinese, 3 epochs) | AutoDL GPU, `ml/train_bert.py` | 0.758 / 0.806 / 0.758 / 0.824 |
| RoBERTa (chinese-wwm-ext, 3 epochs) | AutoDL GPU | 0.765 / 0.803 / 0.763 / 0.789 |

BERT/RoBERTa were fine-tuned on an AutoDL RTX 3080 Ti. The TF-IDF + LR model stays the default because it runs instantly on CPU and is competitive; BERT is the best for ambiguous multi-aspect sentences.

Training commands:

```bash
python -m ml.data_pipeline              # build v1/v2 CSVs
python -m ml.train --data-version v2 --mode tuned   # TF-IDF + LR, logs to MLflow
python -m ml.train_lstm --data-version v2           # BiLSTM
python -m ml.train_bert --data-dir data --epochs 3  # BERT/RoBERTa (GPU recommended)
```

## Experiments and model registry

MLflow tracks every run (git SHA, data checksum, hyperparams, per-aspect metrics) and registers models. Tracking goes to DagsHub when the env vars above are set, otherwise to a local `mlruns/`. Registered models on DagsHub:

`absa_restaurant` (unified TF-IDF+LR), `absa_restaurant_lstm`, `absa_restaurant_bert`, `absa_restaurant_roberta`.

Note: DagsHub's MLflow server is 2.x, so the client must be `mlflow<3`.

## CI/CD and Docker

`.github/workflows/ci.yml`:

- PR to `dev`/`staging`/`main`/`finalProject_sentimentAnalysis`: ruff + pytest + docker build.
- push to `staging`: publish `:staging` image; push to `main`: publish `:latest`.

`Dockerfile` is `python:3.12-slim` with runtime deps only. torch/transformers are lazy-imported, so the image serves the TF-IDF model without the ~2 GB deep-learning stack.

## Problems I hit, and how I fixed them

1. **Broken numpy/scipy across multiple Python installs.** The machine had five Pythons sharing one user site-packages, and an interrupted `pip` upgrade left `~umpy`/`~ip`/`~crypt` folders. `import sklearn` failed with `numpy.core.multiarray failed to import`. Fixed by picking C:\Python312, deleting the `~`-prefixed leftovers, and reinstalling numpy.

2. **Confidence numbers were meaningless.** The first 3-class model reported ~0.45 confidence because the "neutral" class was a catch-all. Dropping neutral and going binary raised both macro-F1 and confidence honestly — calibrating or forcing higher confidence only inflated numbers while hurting F1, so I didn't.

3. **Small dataset capped the models.** The English SemEval data (~3k reviews) was too small for any deep model to matter. Switched to ASAP (~46,850 Chinese reviews); price alone went from ~400 to ~39k rows.

4. **MLflow 3.x can't talk to DagsHub.** `CreateLoggedModel` returned `INVALID_PARAMETER_VALUE` because DagsHub's server is 2.x. Pinned `mlflow<3`.

5. **huggingface_hub + httpx2 download bug.** On AutoDL, `AutoTokenizer.from_pretrained` died with `process() takes no keyword arguments`. Worked around by downloading the model files with `wget` from hf-mirror and loading from a local path.

6. **TF-IDF produced empty features for Chinese.** The default `token_pattern=\b\w\w+\b` drops single CJK characters. Set `token_pattern=r"\S+"`.

7. **The whole page's JS stopped working once.** A `'\n'` inside the Python triple-quoted HTML string became a literal newline in the generated JS, which broke `buffer.indexOf('...')` and killed the script. Replaced escapes with `String.fromCharCode(10)`.

8. **400 MB model weights shouldn't live in git.** BERT/RoBERTa state dicts are ~440 MB each; they're gitignored (and DVC-tracked for the LSTM), with the TF-IDF model (~30 MB) committed for Docker.

9. **More epochs made the model worse.** RoBERTa at 5 epochs overfit (train loss 0.12, test F1 dropped). Three epochs is the sweet spot on this dataset.

10. **Azure push timing out from China.** First `dvc push` hit `Timeout on reading data from socket` on the large files. It was intermittent; retrying finished the job.

## Running it

```bash
python -m uvicorn app.main:app --reload      # or: python -m app.main
# http://127.0.0.1:8000  (analyze)  /history (saved records)

docker build -t absa-app .
docker run -p 8000:8000 absa-app
```

Run tests with `python -m pytest` and lint with `ruff check app ml tests scripts`.
