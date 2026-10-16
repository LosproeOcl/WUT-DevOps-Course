"""Download the MAMS-ACSA restaurant aspect-category sentiment dataset.

Source: https://github.com/siat-nlp/MAMS-for-ABSA (MAMS: Multi-Aspect
Multi-Sentiment). The `MAMS-ACSA/raw` files are XML with, per sentence, a set
of `<aspectCategory category="..." polarity="..."/>` annotations.

Note: this raw snapshot contains the *English* restaurant reviews (reformatted
from SemEval-2014); the full Chinese MAMS data is a separate, much larger
download from the MAMS authors.
"""
from __future__ import annotations

import os
import sys
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/siat-nlp/MAMS-for-ABSA/master/data/MAMS-ACSA/raw"

FILES = {"train.xml": "train", "val.xml": "val", "test.xml": "test"}


def download(raw_dir: str) -> dict[str, str]:
    os.makedirs(raw_dir, exist_ok=True)
    downloaded: dict[str, str] = {}
    for filename, split in FILES.items():
        dest = os.path.join(raw_dir, filename)
        url = f"{BASE_URL}/{filename}"
        print(f"[download] {split}: {url}")
        urllib.request.urlretrieve(url, dest)
        downloaded[split] = dest
    return downloaded


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(root, "data", "raw")
    paths = download(raw_dir)
    for split, path in paths.items():
        print(f"[done] {split} -> {path} ({os.path.getsize(path)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
