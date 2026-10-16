"""Data pipeline for the ASAP (Meituan) Chinese restaurant aspect dataset.

Parses the ASAP CSV files into (text, aspect, polarity, label) rows, maps the 18
fine-grained categories to the four coarse aspects, and writes v1/v2 CSVs.

Output CSV columns: text, aspect, polarity, label, split
    aspect    : one of food / service / price / ambience
    polarity  : 1 (positive) / 0 (neutral) / -1 (negative); -2 (not mentioned) is dropped
    label     : positive / neutral / negative
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

from .aspects import ASAP_ASPECT_MAP, ASPECTS, tokenize_zh

POLARITY_TO_LABEL = {1: "positive", 0: "neutral", -1: "negative"}

COLUMNS = ["text", "aspect", "polarity", "label", "split"]

SPLITS = {"train": "train.csv", "dev": "dev.csv", "test": "test.csv"}


def parse_asap_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    frames = []
    for col, aspect in ASAP_ASPECT_MAP.items():
        if col not in df.columns:
            continue
        sub = df[df[col] != -2][["review", col]].copy()
        sub.columns = ["text", "polarity"]
        sub["aspect"] = aspect
        sub["label"] = sub["polarity"].map(POLARITY_TO_LABEL)
        frames.append(sub[["text", "aspect", "polarity", "label"]])
    return pd.concat(frames, ignore_index=True)


def build_dataframe(raw_dir: str) -> pd.DataFrame:
    frames = []
    for split, filename in SPLITS.items():
        path = os.path.join(raw_dir, filename)
        df = parse_asap_csv(path)
        df["split"] = "val" if split == "dev" else split
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_v1(df: pd.DataFrame) -> pd.DataFrame:
    return df[COLUMNS].copy()


def build_v2(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    unique_texts = out["text"].unique()
    tokenized = {t: tokenize_zh(t) for t in unique_texts}
    out["text"] = out["text"].map(tokenized).str.strip()
    out = out.drop_duplicates(subset=["text", "aspect", "label"]).reset_index(drop=True)
    return out[COLUMNS]


def save(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v1/v2 aspect-category datasets (ASAP)")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--out-dir", default="data/processed")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.normpath(os.path.join(root, args.raw_dir))
    out_dir = os.path.normpath(os.path.join(root, args.out_dir))

    df = build_dataframe(raw_dir)
    v1 = build_v1(df)
    v2 = build_v2(df)

    for split in ("train", "val", "test"):
        save(v1[v1["split"] == split], os.path.join(out_dir, f"{split}_v1.csv"))
        save(v2[v2["split"] == split], os.path.join(out_dir, f"{split}_v2.csv"))

    print(f"[pipeline] raw rows: {len(df)}")
    print(f"[pipeline] v1 rows: {len(v1)}  v2 rows: {len(v2)}")
    print("[pipeline] aspects:", {a: int((v2["aspect"] == a).sum()) for a in ASPECTS})
    print("[pipeline] wrote train/val/test v1+v2 CSVs to", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
