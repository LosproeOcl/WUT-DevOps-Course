# Experiment Tracking (MLflow)

All training runs are tracked with MLflow. By default this uses the local
`mlruns/` backend; when `DAGSHUB_REPO_OWNER` / `DAGSHUB_REPO_NAME` (plus
`MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD`) are set, runs and models
go to DagsHub's MLflow server (see `15-MLFlow.pdf`).

## What is logged per run

- **Code version**: `git_sha`.
- **Dataset version**: `data_version` and `train_checksum` (MD5).
- **Hyperparameters**: `mode` (baseline/tuned) plus vectorizer/classifier settings.
- **Metrics**: per-aspect `macro_f1` and `accuracy`, plus per-class (positive/negative) F1.
- **Models**: each of the four aspect classifiers is logged with the `sklearn`
  flavor and **registered** in the MLflow Model Registry.

The sentiment task is **binary (positive vs negative)** per aspect: the murky
"neutral" class is dropped at training time, which both improves macro-F1 and
yields more trustworthy confidence. At inference, predictions below a confidence
threshold are reported as "neutral" (uncertain) rather than a forced polarity.

## Experiments

| Run | Model | Data | Description |
|-----|-------|------|-------------|
| `baseline-v2` | TF-IDF (unigrams) + LogisticRegression | v2 | Simple baseline. |
| `tuned-v2` | TF-IDF (1-2 grams, sublinear) + LogisticRegression (balanced class weights, tuned `C`) | v2 | Improved model. |

### Results (macro-F1 per aspect, v2, binary positive/negative)

| Aspect | baseline | tuned |
|--------|----------|-------|
| food | 0.4219 | 0.6609 |
| service | 0.5577 | 0.7039 |
| price | 0.5333 | 0.8518 |
| ambience | 0.6065 | 0.7164 |

The tuned model improves macro-F1 on every aspect.

## Metric we optimize for

**Macro-F1** (over `positive`/`negative`). The classes are imbalanced, so raw
accuracy is misleading; macro-F1 rewards the model for getting the minority class
right. Dropping the murky `neutral` class (binary task) measurably improved both
macro-F1 and the reliability of the reported confidence.

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
