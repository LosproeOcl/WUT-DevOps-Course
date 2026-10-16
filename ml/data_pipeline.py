"""Data pipeline for the SemEval-2014 Restaurant aspect sentiment dataset.

Turns the raw "segmented" triple format into clean CSV datasets, producing two
documented versions (v1 = minimal parse, v2 = cleaned/normalized/deduplicated).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import pandas as pd

POLARITY_TO_LABEL = {-1: "negative", 0: "neutral", 1: "positive"}
LABEL_TO_POLARITY = {v: k for k, v in POLARITY_TO_LABEL.items()}

COLUMNS = ["text", "term", "polarity", "label", "split"]

# Artifacts left by the `.seg` tokenization that we clean up in v2.
_LRB = re.compile(r"\s*-LRB-\s*")
_RRB = re.compile(r"\s*-RRB-\s*")
_WS = re.compile(r"\s+")


def parse_seg_file(path: str) -> list[dict]:
    """Parse a `.seg` file (3 lines per instance) into records."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = [ln.strip() for ln in fh.read().splitlines()]

    records: list[dict] = []
    for i in range(0, len(lines) - 2, 3):
        sentence, term, polarity = lines[i], lines[i + 1], lines[i + 2]
        if not sentence or not term or polarity not in ("-1", "0", "1"):
            continue
        records.append(
            {
                "text": sentence,  # still contains the `$T$` placeholder
                "term": term,
                "polarity": int(polarity),
                "label": POLARITY_TO_LABEL[int(polarity)],
            }
        )
    return records


def inject_term(text: str, term: str) -> str:
    """Replace the `$T$` placeholder with the target term."""
    return text.replace("$T$", term)


def clean_text(text: str) -> str:
    """Normalize a sentence: restore parentheses, drop stray tokens."""
    text = _LRB.sub(" ( ", text)
    text = _RRB.sub(" ) ", text)
    text = text.replace("`", "").replace(" '", "'")
    text = text.lower()
    return _WS.sub(" ", text).strip()


def build_dataframe(raw_dir: str) -> pd.DataFrame:
    """Load train + test `.seg` files into a single DataFrame."""
    frames = []
    for split, filename in [
        ("train", "Restaurants_Train.xml.seg"),
        ("test", "Restaurants_Test_Gold.xml.seg"),
    ]:
        path = os.path.join(raw_dir, filename)
        records = parse_seg_file(path)
        df = pd.DataFrame(records, columns=COLUMNS[:4])
        df["split"] = split
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_v1(df: pd.DataFrame) -> pd.DataFrame:
    """v1: minimal parse — inject term, keep everything else as-is."""
    out = df.copy()
    out["text"] = [inject_term(t, a) for t, a in zip(out["text"], out["term"])]
    return out[COLUMNS]


def build_v2(df: pd.DataFrame) -> pd.DataFrame:
    """v2: cleaned — normalize text, deduplicate (text, term, label) pairs."""
    out = df.copy()
    out["text"] = [clean_text(inject_term(t, a)) for t, a in zip(out["text"], out["term"])]
    out["term"] = out["term"].str.lower().str.strip()
    out = out.drop_duplicates(subset=["text", "term", "label"]).reset_index(drop=True)
    return out[COLUMNS]


def save(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v1/v2 processed datasets")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--out-dir", default="data/processed")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.normpath(os.path.join(root, args.raw_dir))
    out_dir = os.path.normpath(os.path.join(root, args.out_dir))

    df = build_dataframe(raw_dir)
    v1 = build_v1(df)
    v2 = build_v2(df)

    for split in ("train", "test"):
        save(v1[v1["split"] == split], os.path.join(out_dir, f"{split}_v1.csv"))
        save(v2[v2["split"] == split], os.path.join(out_dir, f"{split}_v2.csv"))

    print(f"[pipeline] raw rows: {len(df)}")
    print(f"[pipeline] v1 rows: {len(v1)}  v2 rows: {len(v2)}")
    print(f"[pipeline] v2 dedup removed: {len(v1) - len(v2)} rows")
    print("[pipeline] wrote train/test v1+v2 CSVs to", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
