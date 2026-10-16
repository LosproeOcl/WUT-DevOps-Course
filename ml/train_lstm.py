"""Train a BiLSTM model for 4-aspect binary sentiment and register it to MLflow.

Replaces the TF-IDF + LogisticRegression baseline with a small bidirectional
LSTM (PyTorch, CPU-friendly). One binary classifier per aspect, sharing a single
word vocabulary.

Usage:
    python -m ml.train_lstm --data-version v2
"""
from __future__ import annotations

import argparse
import os
import sys

import mlflow
import mlflow.pyfunc
import pandas as pd
import torch
from torch import nn

from .aspects import ASPECTS, BINARY_LABELS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "processed")
MODEL_PATH = os.path.join(ROOT, "models", "lstm.joblib")
EXPERIMENT_NAME = "absa_restaurant_aspects"
MODEL_NAME = "absa_restaurant_lstm"

EMBED_DIM = 128
HIDDEN_DIM = 128
MAX_LEN = 60
EPOCHS = 8
BATCH_SIZE = 32
LR = 1e-3
THRESHOLD = 0.55


class TextVocab:
    def __init__(self, texts, max_len=MAX_LEN):
        self.max_len = max_len
        freq: dict[str, int] = {}
        for t in texts:
            for w in str(t).split():
                freq[w] = freq.get(w, 0) + 1
        words = sorted(freq, key=freq.get, reverse=True)
        self.word2idx = {"<pad>": 0, "<unk>": 1}
        for w in words:
            if w not in self.word2idx:
                self.word2idx[w] = len(self.word2idx)

    def encode(self, text: str) -> list[int]:
        ids = [self.word2idx.get(w, 1) for w in str(text).split()][: self.max_len]
        return ids + [0] * (self.max_len - len(ids))

    def encode_batch(self, texts) -> torch.Tensor:
        return torch.tensor([self.encode(t) for t in texts], dtype=torch.long)


class BiLSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim=EMBED_DIM, hidden_dim=HIDDEN_DIM, num_classes=2, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        emb = self.embedding(x)
        out, _ = self.lstm(emb)
        pooled = out.max(dim=1).values
        return self.fc(self.dropout(pooled))


def train_one_aspect(vocab, sub: pd.DataFrame, epochs=EPOCHS, lr=LR, seed=42):
    torch.manual_seed(seed)
    X = vocab.encode_batch(sub["text"].tolist())
    y = torch.tensor([0 if l == "negative" else 1 for l in sub["label"]], dtype=torch.long)
    model = BiLSTMClassifier(len(vocab.word2idx))
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    n = len(y)
    for _ in range(epochs):
        model.train()
        perm = torch.randperm(n)
        for i in range(0, n, BATCH_SIZE):
            idx = perm[i : i + BATCH_SIZE]
            opt.zero_grad()
            out = model(X[idx])
            loss = loss_fn(out, y[idx])
            loss.backward()
            opt.step()
    return model


def evaluate(model, vocab, ev: pd.DataFrame):
    model.eval()
    X = vocab.encode_batch(ev["text"].tolist())
    y_true = ev["label"].tolist()
    with torch.no_grad():
        logits = model(X)
        preds = logits.argmax(dim=1).tolist()
    y_pred = ["negative" if p == 0 else "positive" for p in preds]
    return y_true, y_pred


def f1_macro(y_true, y_pred):
    per = {}
    for label in BINARY_LABELS:
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == b == label)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
        per[label] = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    return sum(per.values()) / len(per)


class LstmAbsaModel(mlflow.pyfunc.PythonModel):
    """pyfunc wrapper that rebuilds and serves the four BiLSTM classifiers."""

    def load_context(self, context):
        data = torch.load(context.artifacts["model"], map_location="cpu", weights_only=False)
        vocab = TextVocab([], max_len=data["max_len"])
        vocab.word2idx = data["vocab"]
        self.vocab = vocab
        self.models = {}
        for aspect in ASPECTS:
            m = BiLSTMClassifier(len(vocab.word2idx))
            m.load_state_dict(data["state_dicts"][aspect])
            m.eval()
            self.models[aspect] = m

    def predict(self, context, model_input, params=None):
        texts = model_input["text"].astype(str).tolist()
        X = self.vocab.encode_batch(texts)
        rows = []
        with torch.no_grad():
            for i, text in enumerate(texts):
                row = {"text": text}
                for aspect in ASPECTS:
                    logits = self.models[aspect](X[i : i + 1])
                    probs = torch.softmax(logits, dim=1)[0]
                    best = int(probs.argmax())
                    conf = float(probs[best])
                    label = ("negative" if best == 0 else "positive") if conf >= THRESHOLD else "neutral"
                    row[f"{aspect}_label"] = label
                    row[f"{aspect}_confidence"] = round(conf, 4)
                rows.append(row)
        return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-version", default="v2", choices=["v1", "v2"])
    args = parser.parse_args()

    owner = os.environ.get("DAGSHUB_REPO_OWNER")
    name = os.environ.get("DAGSHUB_REPO_NAME")
    if owner and name:
        import dagshub

        dagshub.init(repo_owner=owner, repo_name=name, mlflow=True)
    mlflow.set_experiment(EXPERIMENT_NAME)

    train = pd.read_csv(os.path.join(DATA_DIR, f"train_{args.data_version}.csv"))
    val = pd.read_csv(os.path.join(DATA_DIR, f"val_{args.data_version}.csv"))
    test = pd.read_csv(os.path.join(DATA_DIR, f"test_{args.data_version}.csv"))
    train = pd.concat([train, val], ignore_index=True)

    vocab = TextVocab(train["text"].tolist())

    with mlflow.start_run(run_name=f"lstm-{args.data_version}"):
        mlflow.log_param("model", "BiLSTM")
        mlflow.log_param("data_version", args.data_version)
        mlflow.log_param("embed_dim", EMBED_DIM)
        mlflow.log_param("hidden_dim", HIDDEN_DIM)
        mlflow.log_param("epochs", EPOCHS)
        mlflow.log_param("vocab_size", len(vocab.word2idx))

        state_dicts = {}
        for aspect in ASPECTS:
            sub = train[(train["aspect"] == aspect) & (train["label"] != "neutral")]
            ev = test[(test["aspect"] == aspect) & (test["label"] != "neutral")]
            if sub.empty or ev.empty:
                continue
            model = train_one_aspect(vocab, sub)
            y_true, y_pred = evaluate(model, vocab, ev)
            macro = f1_macro(y_true, y_pred)
            mlflow.log_metric(f"{aspect}_macro_f1", macro)
            state_dicts[aspect] = model.state_dict()
            print(f"  [{aspect}] lstm: macro_f1={macro:.4f} (n={len(ev)})")

        torch.save(
            {"vocab": vocab.word2idx, "max_len": vocab.max_len, "state_dicts": state_dicts},
            MODEL_PATH,
        )

        info = mlflow.pyfunc.log_model(
            artifact_path="lstm",
            python_model=LstmAbsaModel(),
            artifacts={"model": MODEL_PATH},
        )
        mlflow.register_model(info.model_uri, MODEL_NAME)
        print(f"[train] registered '{MODEL_NAME}' -> {info.model_uri}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
