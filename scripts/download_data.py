"""Download the SemEval-2014 Restaurant aspect-based sentiment dataset.

Source: the widely-used mirror in the `songyouwei/ABSA-PyTorch` repository
(original data from the SemEval-2014 Task 4 shared task).

The raw files use a compact "segmented" triple format:
    <sentence with the target term replaced by `$T$`>
    <target term>
    <polarity: -1 negative / 0 neutral / 1 positive>
"""
from __future__ import annotations

import os
import sys
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/songyouwei/ABSA-PyTorch/master/datasets/semeval14"

FILES = {
    "Restaurants_Train.xml.seg": "train",
    "Restaurants_Test_Gold.xml.seg": "test",
}


def download(raw_dir: str) -> dict[str, str]:
    """Download the raw dataset files into `raw_dir` and return their paths."""
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
