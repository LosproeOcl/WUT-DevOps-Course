"""Fine-tune a Chinese BERT for 4-aspect binary sentiment (GPU).

Single BERT encoder (bert-base-chinese) + 4 binary classification heads
(food/service/price/ambience). Reads the raw ASAP CSV files directly.

Usage:
    python train_bert.py --data-dir /root/data --epochs 3 --batch-size 32
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

ASPECTS = ["food", "service", "price", "ambience"]

# ASAP (Meituan) fine-grained columns -> coarse aspect
ASPECT_COLS = {
    "food": ["Food#Portion", "Food#Taste", "Food#Appearance", "Food#Recommend"],
    "service": ["Service#Queue", "Service#Hospitality", "Service#Parking", "Service#Timely"],
    "price": ["Price#Level", "Price#Cost_effective", "Price#Discount"],
    "ambience": ["Ambience#Decoration", "Ambience#Noise", "Ambience#Space", "Ambience#Sanitary"],
}

MODEL_NAME = "bert-base-chinese"
MAX_LEN = 128


def load_reviews(data_dir: str, split: str) -> list[dict]:
    path = os.path.join(data_dir, f"{split}.csv")
    df = pd.read_csv(path)
    records = []
    for _, row in df.iterrows():
        text = str(row["review"]).strip()
        if not text:
            continue
        labels = {}
        for aspect in ASPECTS:
            vals = [int(row[c]) for c in ASPECT_COLS[aspect] if c in row and pd.notna(row[c])]
            vals = [v for v in vals if v != -2]
            if not vals:
                labels[aspect] = -100  # not mentioned -> ignore
            elif any(v == 1 for v in vals):
                labels[aspect] = 1  # positive
            elif any(v == -1 for v in vals):
                labels[aspect] = 0  # negative
            else:
                labels[aspect] = -100  # neutral only -> ignore
        records.append({"text": text, "labels": [labels[a] for a in ASPECTS]})
    return records


class AbsaDataset(Dataset):
    def __init__(self, records, tokenizer):
        self.texts = [r["text"] for r in records]
        self.labels = torch.tensor([r["labels"] for r in records], dtype=torch.long)
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i):
        enc = self.tokenizer(
            self.texts[i], max_length=MAX_LEN, truncation=True, padding="max_length", return_tensors="pt"
        )
        return {
            "input_ids": enc["input_ids"][0],
            "attention_mask": enc["attention_mask"][0],
            "labels": self.labels[i],
        }


class BertAbsa(nn.Module):
    def __init__(self, model_name=MODEL_NAME):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden = self.bert.config.hidden_size
        self.heads = nn.ModuleList([nn.Linear(hidden, 1) for _ in ASPECTS])

    def forward(self, input_ids, attention_mask):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        logits = torch.stack([head(cls).squeeze(-1) for head in self.heads], dim=1)
        return logits  # (B, 4)


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path)

    train_records = load_reviews(args.data_dir, "train") + load_reviews(args.data_dir, "dev")
    test_records = load_reviews(args.data_dir, "test")
    print(f"train reviews: {len(train_records)}, test reviews: {len(test_records)}")

    train_ds = AbsaDataset(train_records, tokenizer)
    test_ds = AbsaDataset(test_records, tokenizer)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size)

    model = BertAbsa(args.model_path).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5)

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)  # (B, 4)

            logits = model(input_ids, mask)  # (B, 4)
            label_float = (labels == 1).float()
            bce = nn.functional.binary_cross_entropy_with_logits(logits, label_float, reduction="none")
            valid = (labels != -100).float()
            loss = (bce * valid).sum() / valid.sum()

            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()
        print(f"epoch {epoch + 1}/{args.epochs} loss={total_loss / len(train_loader):.4f}")

    # evaluate
    model.eval()
    preds = {a: [] for a in ASPECTS}
    trues = {a: [] for a in ASPECTS}
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            labels = batch["labels"]  # (B, 4)
            logits = model(input_ids, mask)
            prob = torch.sigmoid(logits)  # (B, 4)
            pred = (prob >= 0.5).long()
            for j, aspect in enumerate(ASPECTS):
                valid = labels[:, j] != -100
                if valid.any():
                    trues[aspect].extend(labels[:, j][valid].tolist())
                    preds[aspect].extend(pred[:, j][valid].tolist())

    for aspect in ASPECTS:
        f1 = macro_f1(trues[aspect], preds[aspect])
        print(f"[{aspect}] macro_f1={f1:.4f} (n={len(trues[aspect])})")

    torch.save({"state_dict": model.state_dict(), "config": model.bert.config.to_dict()}, args.out_path)
    print(f"saved to {args.out_path}")


def macro_f1(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    per = {}
    for c in (0, 1):
        tp = ((y_true == c) & (y_pred == c)).sum()
        fp = ((y_true != c) & (y_pred == c)).sum()
        fn = ((y_true == c) & (y_pred != c)).sum()
        per[c] = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
    return float(sum(per.values()) / 2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default="/root/data")
    p.add_argument("--model-path", default="bert-base-chinese")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--out-path", default="/root/bert_absa.pt")
    args = p.parse_args()
    train(args)


if __name__ == "__main__":
    sys.exit(main())
