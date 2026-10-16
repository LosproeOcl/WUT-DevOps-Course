"""Download the ASAP Chinese restaurant aspect-category sentiment dataset.

Source: https://github.com/Meituan-Dianping/asap (ASAP: A Chinese Review Dataset
Towards Aspect Category Sentiment Analysis and Rating Prediction). ~46k reviews
with 18 aspect categories (Food/Service/Price/Ambience/Location), each annotated
with polarity -1/0/1 (-2 = aspect not mentioned).

License: Apache-2.0.
"""
from __future__ import annotations

import os
import sys
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/Meituan-Dianping/asap/master/data"

FILES = {"train.csv": "train", "dev.csv": "val", "test.csv": "test"}


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
