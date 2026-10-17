"""Transition registered models between MLflow stages.

Stages: Staging -> Production -> Archived.

Usage:
    python -m ml.stage_models
"""
from __future__ import annotations

import os
import sys

from mlflow.tracking import MlflowClient

TRANSITIONS = {
    "absa_restaurant": "Production",
    "absa_restaurant_rating": "Production",
    "absa_restaurant_bert": "Staging",
    "absa_restaurant_roberta": "Archived",
    "absa_restaurant_lstm": "Archived",
}


def main() -> int:
    owner = os.environ.get("DAGSHUB_REPO_OWNER")
    name = os.environ.get("DAGSHUB_REPO_NAME")
    if owner and name:
        import dagshub

        dagshub.init(repo_owner=owner, repo_name=name, mlflow=True)

    client = MlflowClient()
    for model_name, stage in TRANSITIONS.items():
        try:
            versions = client.get_latest_versions(model_name)
            if not versions:
                print(f"[skip] {model_name}: no versions")
                continue
            version = versions[-1]
            client.transition_model_version_stage(name=model_name, version=version.version, stage=stage)
            print(f"[stage] {model_name} v{version.version} -> {stage}")
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {model_name}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
