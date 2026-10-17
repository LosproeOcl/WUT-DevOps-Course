"""Register the RoBERTa star-rating model (metrics + model card) to MLflow/DagsHub.

The RoBERTa weights (~390 MB) stay in ``models/rating_bert/`` and are loaded by
the app directly; this script registers the held-out metrics and a lightweight
"model card" so DagsHub MLflow recognizes the model, matching how the BERT /
RoBERTa aspect models are tracked.

Usage (requires DagsHub tracking env vars):
    python -m ml.register_rating_roberta
"""
from __future__ import annotations

import json
import os
import sys

import mlflow
import mlflow.pyfunc
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENT = "absa_restaurant_aspects"
MODEL_NAME = "absa_restaurant_rating_roberta"

# Held-out metrics from the AutoDL training run (test split).
METRICS = {
    "rating_accuracy": 0.5923,
    "rating_mae": 0.4460,
    "rating_acc_within_1": 0.9642,
}
PARAMS = {
    "task": "star_rating",
    "model": "chinese-roberta-wwm-ext",
    "max_len": 384,
    "epochs": 5,
    "batch_size": 16,
    "label_smoothing": 0.1,
}


class RatingModelCard(mlflow.pyfunc.PythonModel):
    """Lightweight model card; the actual weights live in models/rating_bert/."""

    def __init__(self, info: dict):
        self.info = info

    def predict(self, context, model_input, params=None):
        return pd.DataFrame([self.info])


def main() -> int:
    owner = os.environ.get("DAGSHUB_REPO_OWNER")
    name = os.environ.get("DAGSHUB_REPO_NAME")
    if owner and name:
        import dagshub

        dagshub.init(repo_owner=owner, repo_name=name, mlflow=True)
    mlflow.set_experiment(EXPERIMENT)

    info = {"model": MODEL_NAME, "note": "RoBERTa 5-class rating (weights in models/rating_bert/)", **PARAMS, **METRICS}

    with mlflow.start_run(run_name="rating-roberta"):
        for k, v in PARAMS.items():
            mlflow.log_param(k, v)
        for k, v in METRICS.items():
            mlflow.log_metric(k, v)
        card_path = os.path.join(ROOT, "models", "rating_roberta_card.json")
        with open(card_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        mlflow.log_artifact(card_path)

        card = mlflow.pyfunc.log_model("rating_roberta", python_model=RatingModelCard(info))
        mlflow.register_model(card.model_uri, MODEL_NAME)
        print(f"[register] {MODEL_NAME} -> {card.model_uri}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
