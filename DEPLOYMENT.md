# Deployment

## Environments

The app is deployed as a Docker image. Two environments are published from the
CI pipeline:

| Environment | Git branch | Image tag | Trigger |
|-------------|------------|-----------|---------|
| Staging | `staging` | `absa-app:staging` | push to `staging` |
| Production | `main` | `absa-app:latest` | push to `main` |

## CI pipeline (`.github/workflows/ci.yml`)

Every pull request to `dev`/`staging`/`main` runs:

1. **Lint** — `ruff check app ml tests scripts`
2. **Tests** — `python -m pytest`
3. **Docker build** — `docker build -t absa-app:ci .`

A PR **cannot be merged if CI fails** (enable branch protection on the repo).

On push to `staging`/`main`, the pipeline additionally builds and publishes the
Docker image to Docker Hub using repository secrets
(`DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`).

## Required repository secrets

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Set these under **Settings -> Secrets and variables -> Actions**.

## Environment variables

The app reads no mandatory env vars (it serves the committed `models/model.joblib`
and `data/demo.csv`). Optional overrides:

- `MLFLOW_TRACKING_URI` — only used by the training script, not the app.

## Local deployment

```bash
docker build -t absa-app .
docker run -p 8000:8000 absa-app
# open http://127.0.0.1:8000
```

## Notes

- The Docker image is a `python:3.12-slim` runtime image containing only the
  serving dependencies (see `requirements.txt`); training-only deps (MLflow,
  matplotlib) live in `requirements-ml.txt` and are not installed in the image.
- `.dockerignore` excludes `tests/`, `ml/`, raw/processed data, and `mlruns/`.
