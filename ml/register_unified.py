"""Register the current (TF-IDF + LR) model as a single unified MLflow model.

The trained artifact `models/model.joblib` is a dict {aspect: sklearn pipeline}.
This wraps that dict in a single `pyfunc` model and registers it under one name,
so DagsHub shows one consolidated model instead of four separate ones.
"""
from __future__ import annotations

import os
import sys

import joblib
import mlflow
import mlflow.pyfunc
import pandas as pd

from .aspects import ASPECTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "models", "model.joblib")
UNIFIED_NAME = "absa_restaurant"
THRESHOLD = 0.55


class UnifiedAbsaModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        self.models = joblib.load(context.artifacts["model"])

    def predict(self, context, model_input, params=None):
        texts = model_input["text"].astype(str).tolist()
        rows = []
        for text in texts:
            row = {"text": text}
            for aspect in ASPECTS:
                pipe = self.models.get(aspect)
                if pipe is None:
                    row[f"{aspect}_label"] = "neutral"
                    row[f"{aspect}_confidence"] = 0.0
                    continue
                probs = pipe.predict_proba([text])[0]
                classes = [str(c) for c in pipe.classes_]
                best = int(probs.argmax())
                conf = float(probs[best])
                label = classes[best] if conf >= THRESHOLD else "neutral"
                row[f"{aspect}_label"] = label
                row[f"{aspect}_confidence"] = round(conf, 4)
            rows.append(row)
        return pd.DataFrame(rows)


def main() -> int:
    owner = os.environ.get("DAGSHUB_REPO_OWNER")
    name = os.environ.get("DAGSHUB_REPO_NAME")
    if owner and name:
        import dagshub

        dagshub.init(repo_owner=owner, repo_name=name, mlflow=True)
    mlflow.set_experiment("absa_restaurant_aspects")

    with mlflow.start_run(run_name="register-unified"):
        info = mlflow.pyfunc.log_model(
            artifact_path="unified",
            python_model=UnifiedAbsaModel(),
            artifacts={"model": MODEL_PATH},
        )
        mlflow.register_model(info.model_uri, UNIFIED_NAME)
        print(f"[register] unified model '{UNIFIED_NAME}' -> {info.model_uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
