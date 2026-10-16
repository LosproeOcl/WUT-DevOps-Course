"""Data pipeline for the MAMS-ACSA restaurant aspect-category dataset.

Parses the raw XML (per-sentence `<aspectCategory category polarity>` pairs),
maps fine-grained categories to the four coarse aspects, and writes v1/v2 CSVs.

Output CSV columns: text, aspect, polarity, label, split
    aspect    : one of food / service / price / ambience
    polarity  : 1 (positive) / 0 (neutral) / -1 (negative)
    label     : positive / neutral / negative
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

import pandas as pd

from .aspects import ASPECTS, map_category

POLARITY_TO_LABEL = {"positive": 1, "neutral": 0, "negative": -1}
LABEL_TO_POLARITY = {v: k for k, v in POLARITY_TO_LABEL.items()}

COLUMNS = ["text", "aspect", "polarity", "label", "split"]

_WS = re.compile(r"\s+")


def parse_xml_file(path: str) -> list[dict]:
    """Parse a MAMS ACSA XML file into (text, aspect, polarity) records."""
    tree = ET.parse(path)
    records: list[dict] = []
    for sentence in tree.getroot().findall("sentence"):
        text_el = sentence.find("text")
        text = text_el.text if text_el is not None and text_el.text else ""
        text = _WS.sub(" ", text).strip()
        for ac in sentence.findall(".//aspectCategory"):
            category = ac.get("category", "").lower()
            polarity = ac.get("polarity", "").lower()
            aspect = map_category(category)
            if aspect is None or polarity not in POLARITY_TO_LABEL:
                continue
            records.append(
                {
                    "text": text,
                    "aspect": aspect,
                    "polarity": POLARITY_TO_LABEL[polarity],
                    "label": polarity,
                }
            )
    return records


def build_dataframe(raw_dir: str) -> pd.DataFrame:
    frames = []
    for split, filename in [("train", "train.xml"), ("val", "val.xml"), ("test", "test.xml")]:
        path = os.path.join(raw_dir, filename)
        records = parse_xml_file(path)
        df = pd.DataFrame(records, columns=COLUMNS[:4])
        df["split"] = split
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_v1(df: pd.DataFrame) -> pd.DataFrame:
    return df[COLUMNS].copy()


def build_v2(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["text"] = out["text"].str.lower().str.strip()
    out = out.drop_duplicates(subset=["text", "aspect", "label"]).reset_index(drop=True)
    return out[COLUMNS]


def save(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v1/v2 aspect-category datasets")
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
