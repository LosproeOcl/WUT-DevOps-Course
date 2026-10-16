# Experiment Tracking (MLflow)

All training runs are tracked with MLflow (local file backend under `mlruns/`).

## What is logged per run

- **Code version**: `git_sha` (the commit that produced the run).
- **Dataset version**: `data_version` (`v1`/`v2`) and `train_checksum` (MD5).
- **Hyperparameters**: `mode` (baseline/tuned) plus the vectorizer/classifier settings.
- **Metrics**: `accuracy`, `macro_f1`, `weighted_f1`, and per-class precision/recall/f1.
- **Artifacts**: the fitted model (`mlflow.sklearn.log_model`), a confusion-matrix
  plot, and a classification report.

## Experiments

| Run | Model | Data | Description |
|-----|-------|------|-------------|
| `baseline-v2` | TF-IDF (unigrams) + LogisticRegression | v2 | Simple baseline. |
| `tuned-v2` | TF-IDF (1-2 grams, sublinear) + LogisticRegression (balanced class weights, tuned `C`) | v2 | Improved model. |

## Metric we optimize for

**Macro-F1** (averaged over `negative`/`neutral`/`positive`). The classes are
imbalanced (~60% positive), so raw accuracy is misleading — a model that always
predicts "positive" scores high accuracy but fails on negative/neutral aspects.
Macro-F1 rewards the model for getting the rare classes right, which is exactly
what a sentiment demo needs.

## Production-worthy run

The **tuned** run is considered production-worthy: it adds bigram features and
balanced class weights, which improves macro-F1 on the held-out evaluation set.
Its model is saved to `models/model.joblib` and referenced in
`ml/registry/current_model.md`.

View the history with `mlflow ui` (http://127.0.0.1:5000).
