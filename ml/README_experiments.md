# Experiment Tracking (MLflow)

All training runs are tracked with MLflow. By default this uses the local
`mlruns/` backend; when `DAGSHUB_REPO_OWNER` / `DAGSHUB_REPO_NAME` (plus
`MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD`) are set, runs and models
go to DagsHub's MLflow server (see `15-MLFlow.pdf`).

## What is logged per run

- **Code version**: `git_sha`.
- **Dataset version**: `data_version` and `train_checksum` (MD5).
- **Hyperparameters**: `mode` (baseline/tuned) plus vectorizer/classifier settings.
- **Metrics**: per-aspect `macro_f1` and `accuracy`, plus per-class F1.
- **Models**: each of the four aspect classifiers is logged with the `sklearn`
  flavor and **registered** in the MLflow Model Registry.

## Experiments

| Run | Model | Data | Description |
|-----|-------|------|-------------|
| `baseline-v2` | TF-IDF (unigrams) + LogisticRegression | v2 | Simple baseline. |
| `tuned-v2` | TF-IDF (1-2 grams, sublinear) + LogisticRegression (balanced class weights, tuned `C`) | v2 | Improved model. |

### Results (macro-F1 per aspect, v2)

| Aspect | baseline | tuned |
|--------|----------|-------|
| food | 0.4738 | 0.5513 |
| service | 0.3887 | 0.5315 |
| price | 0.6369 | 0.7293 |
| ambience | 0.5713 | 0.6344 |

The tuned model improves macro-F1 on every aspect.

## Metric we optimize for

**Macro-F1** (averaged over `negative`/`neutral`/`positive`). The classes are
imbalanced, so raw accuracy is misleading; macro-F1 rewards the model for getting
the rare classes right.

## Registered models (MLflow Model Registry)

- `absa_restaurant_food`
- `absa_restaurant_service`
- `absa_restaurant_price`
- `absa_restaurant_ambience`

Each has two versions: v1 = baseline, v2 = tuned (production).

## Production-worthy run

The **tuned** run is production-worthy: it improves macro-F1 on all four aspects.
Its combined model is saved to `models/model.joblib` (referenced in
`ml/registry/current_model.md`) and served by the app.
