"""Load a registered MLflow model and run a prediction.

Demonstrates registry-based deployment: instead of a local joblib file, the model
is loaded from the MLflow Model Registry (e.g. `models:/absa_restaurant/Production`).

Usage:
    python -m ml.serve_model --model models:/absa_restaurant/Production --text "食物很好吃"
"""
from __future__ import annotations

import argparse
import os
import sys

import mlflow.pyfunc
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models:/absa_restaurant/Production")
    parser.add_argument("--text", default="食物很好吃，服务也不错")
    args = parser.parse_args()

    owner = os.environ.get("DAGSHUB_REPO_OWNER")
    name = os.environ.get("DAGSHUB_REPO_NAME")
    if owner and name:
        import dagshub

        dagshub.init(repo_owner=owner, repo_name=name, mlflow=True)

    model = mlflow.pyfunc.load_model(args.model)
    result = model.predict(pd.DataFrame({"text": [args.text]}))
    print(result.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
