# Aspect-Based Sentiment Analysis (MLOps + DevOps)

A machine-learning web app that performs **aspect-term sentiment analysis** on
restaurant reviews: given a review and an aspect term (e.g. `food`, `service`,
`price`), it classifies the sentiment of that aspect as **negative / neutral /
positive**.

Built end-to-end with the DevOps + MLOps practices required by the course:

- **DevOps** — Git branching (`main` / `staging` / `dev`), Docker, GitHub Actions CI/CD.
- **MLOps** — DVC for data versioning, MLflow for experiment tracking.

## Tech stack

- Python 3.12, FastAPI (app), scikit-learn (model)
- DVC (data versioning) + MLflow (experiment tracking)
- Docker, GitHub Actions

## Repository layout

```
app/                    # FastAPI application (API + interactive HTML page)
  main.py               # routes, HTML page, /predict, /api/demo
  model.py              # model loading + inference (unit-testable)
ml/                     # machine-learning code
  data_pipeline.py      # parse raw data -> v1/v2 processed CSVs
  train.py              # training script with MLflow logging
  configs/              # hyperparameter configs
  registry/             # which model is production
  README_data.md        # data versioning documentation
  README_experiments.md # MLflow experiment summary
  PROVENANCE.md         # code<->data<->model traceability
data/                   # raw/ + processed/ (tracked by DVC), demo.csv (committed)
models/                 # trained model artifact
scripts/download_data.py
tests/                  # unit + api tests
Dockerfile
.github/workflows/ci.yml
```

## Quick start (local)

```bash
# 1. install deps (training + serving)
python -m pip install -r requirements-ml.txt

# 2. download the SemEval-2014 Restaurant dataset
python scripts/download_data.py

# 3. build v1/v2 datasets
python ml/data_pipeline.py

# 4. train (baseline and tuned), logs to MLflow
python ml/train.py --data-version v2 --mode baseline
python ml/train.py --data-version v2 --mode tuned

# 5. run the app
python -m uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

View experiment history: `mlflow ui` (then open http://127.0.0.1:5000).

## Code flow: commit -> build -> test -> staging -> prod

```
feature/* --PR--> dev --PR--> staging --PR--> main
                    |            |            |
                    v            v            v
              CI: test+lint+docker build (PR blocked if CI fails)
                 push staging --> build staging image (Docker Hub)
                 push main     --> build prod image (Docker Hub :latest)
```

| Branch | Triggers | What runs |
|--------|----------|-----------|
| any PR to `dev`/`staging`/`main` | `pull_request` | test + lint + Docker build |
| push to `dev` | `push` | test + lint + Docker build |
| push to `staging` | `push` | test + lint + build, then publish `:staging` |
| push to `main` | `push` | test + lint + build, then publish `:latest` |

See `DEPLOYMENT.md` for the full deployment story.

## Docker

```bash
docker build -t absa-app .
docker run -p 8000:8000 absa-app
```

See `.dockerignore` for what is excluded from the image.
