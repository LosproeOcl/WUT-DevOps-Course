"""Train an aspect-term sentiment model and log everything to MLflow.

Usage:
    python ml/train.py --data-version v2 --mode baseline
    python ml/train.py --data-version v2 --mode tuned

Produces:
    models/model.joblib            (the fitted sklearn pipeline, loaded by the app)
    data/processed/demo.csv        (a small reserved demo set, excluded from evaluation)
    mlruns/...                     (MLflow run history)
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys

import joblib
import matplotlib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")
MODEL_PATH = os.path.join(ROOT, "models", "model.joblib")
DEMO_PATH = os.path.join(ROOT, "data", "demo.csv")

EXPERIMENT_NAME = "absa_restaurant"

LABELS = ["negative", "neutral", "positive"]


def git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def data_checksum(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def make_features(df: pd.DataFrame) -> list[str]:
    """Prepend the target term so the model conditions on the aspect."""
    return [f"{term} {text}" for term, text in zip(df["term"], df["text"])]


def build_pipeline(mode: str) -> Pipeline:
    if mode == "baseline":
        vectorizer = TfidfVectorizer(min_df=2)
        classifier = LogisticRegression(max_iter=1000, random_state=42)
    elif mode == "tuned":
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        classifier = LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced", random_state=42)
    else:
        raise ValueError(f"unknown mode: {mode}")
    return Pipeline([("tfidf", vectorizer), ("clf", classifier)])


def reserve_demo(test: pd.DataFrame, per_class: int = 10, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reserve a balanced demo set; return (demo, eval_set)."""
    samples = []
    for label in LABELS:
        subset = test[test["label"] == label]
        n = min(per_class, len(subset))
        samples.append(subset.sample(n=n, random_state=seed))
    demo = pd.concat(samples).reset_index(drop=True)
    eval_set = test.drop(demo.index).reset_index(drop=True)
    return demo, eval_set


def save_confusion_matrix(y_true, y_pred, path: str) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(LABELS)))
    ax.set_yticks(range(len(LABELS)))
    ax.set_xticklabels(LABELS)
    ax.set_yticklabels(LABELS)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center", color="black")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-version", default="v2", choices=["v1", "v2"])
    parser.add_argument("--mode", default="baseline", choices=["baseline", "tuned"])
    parser.add_argument("--tracking-uri", default=None)
    args = parser.parse_args()

    if args.tracking_uri:
        mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)

    train = pd.read_csv(os.path.join(DATA_DIR, f"train_{args.data_version}.csv"))
    test = pd.read_csv(os.path.join(DATA_DIR, f"test_{args.data_version}.csv"))

    demo, eval_set = reserve_demo(test)
    demo.to_csv(DEMO_PATH, index=False)

    X_train = make_features(train)
    y_train = train["label"]
    X_eval = make_features(eval_set)
    y_eval = eval_set["label"]

    pipeline = build_pipeline(args.mode)

    with mlflow.start_run(run_name=f"{args.mode}-{args.data_version}"):
        mlflow.log_param("mode", args.mode)
        mlflow.log_param("data_version", args.data_version)
        mlflow.log_param("git_sha", git_sha())
        mlflow.log_param(
            "train_checksum",
            data_checksum(os.path.join(DATA_DIR, f"train_{args.data_version}.csv")),
        )
        mlflow.log_param("train_size", len(train))
        mlflow.log_param("eval_size", len(eval_set))
        mlflow.log_param("demo_size", len(demo))

        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_eval)
        acc = accuracy_score(y_eval, y_pred)
        macro_f1 = f1_score(y_eval, y_pred, average="macro", labels=LABELS)

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("macro_f1", macro_f1)
        mlflow.log_metric("weighted_f1", f1_score(y_eval, y_pred, average="weighted", labels=LABELS))

        report = classification_report(y_eval, y_pred, labels=LABELS, output_dict=True)
        for label in LABELS:
            for metric in ("precision", "recall", "f1-score"):
                mlflow.log_metric(f"{label}_{metric}", report[label][metric])

        report_path = os.path.join(ROOT, "models", "classification_report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(classification_report(y_eval, y_pred, labels=LABELS))
        mlflow.log_artifact(report_path)

        cm_path = os.path.join(ROOT, "models", "confusion_matrix.png")
        save_confusion_matrix(y_eval, y_pred, cm_path)
        mlflow.log_artifact(cm_path)

        mlflow.sklearn.log_model(pipeline, "model")

        joblib.dump(pipeline, MODEL_PATH)
        print(f"[train] {args.mode}-{args.data_version}: accuracy={acc:.4f} macro_f1={macro_f1:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
