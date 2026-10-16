# Aspect-Based Sentiment Analysis (MLOps + DevOps)

A machine-learning web app that performs **aspect-category sentiment analysis** on
restaurant reviews: given a review, it classifies the sentiment of four aspects —
**Taste/Food (口味), Service (服务), Price (价格), Ambience (环境)** — as
**negative / neutral / positive**, with a bilingual (中/EN) UI.

Built end-to-end with the DevOps + MLOps practices required by the course:

- **DevOps** — Git branching (`main` / `staging` / `dev`), Docker, GitHub Actions CI/CD.
- **MLOps** — DVC for data versioning, MLflow for experiment tracking + model registry
  (logged to DagsHub).

## Tech stack

- Python 3.12, FastAPI (app), scikit-learn (model)
- DVC (data versioning), MLflow + DagsHub (experiment tracking + model registry)
- Docker, GitHub Actions

## Repository layout

```
app/                    # FastAPI application (API + bilingual HTML page)
  main.py               # routes, 4-aspect result page, /predict, /api/demo
  model.py              # model loading + inference (unit-testable)
ml/                     # machine-learning code
  aspects.py            # the four aspects + category mapping + bilingual names
  data_pipeline.py      # parse MAMS-ACSA XML -> v1/v2 processed CSVs
  train.py              # training script (4 aspect classifiers, MLflow logging)
  configs/              # hyperparameter configs
  registry/             # which models are production
  README_data.md        # data versioning documentation
  README_experiments.md # MLflow experiment summary
  PROVENANCE.md         # code<->data<->model traceability
data/                   # raw/ + processed/ (tracked by DVC), demo.csv (committed)
models/                 # trained model artifact (dict of 4 pipelines)
scripts/download_data.py
tests/                  # unit + api tests
Dockerfile
.github/workflows/ci.yml
```

## Quick start (local)

```bash
# 1. install deps (training + serving)
python -m pip install -r requirements-ml.txt

# 2. download the MAMS-ACSA restaurant dataset
python scripts/download_data.py

# 3. build v1/v2 datasets
python -m ml.data_pipeline

# 4. train (baseline and tuned), logs + registers models to MLflow
python -m ml.train --data-version v2 --mode baseline
python -m ml.train --data-version v2 --mode tuned

# 5. run the app
python -m uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

## Tracking experiments to DagsHub

The training script points MLflow at DagsHub (see `15-MLFlow.pdf`) when these
environment variables are set:

```bash
export DAGSHUB_REPO_OWNER=<owner>
export DAGSHUB_REPO_NAME=<repo>
export MLFLOW_TRACKING_USERNAME=<username>
export MLFLOW_TRACKING_PASSWORD=<dagshub token>
```

Without them, MLflow uses the local `mlruns/` backend. When tracking to DagsHub,
each aspect model is logged and registered in the MLflow Model Registry
(`absa_restaurant_food` / `service` / `price` / `ambience`).

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
