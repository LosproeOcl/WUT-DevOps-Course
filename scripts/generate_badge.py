"""Generate badges/coverage.json from a pytest-cov JSON report.

Reads coverage.json (produced by `pytest --cov --cov-report=json`) and writes a
shields.io endpoint badge to badges/coverage.json.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    cov_path = os.path.join(ROOT, "coverage.json")
    badge_path = os.path.join(ROOT, "badges", "coverage.json")

    with open(cov_path, encoding="utf-8") as fh:
        cov = json.load(fh)
    total = float(cov["totals"]["percent_covered_display"])
    color = "green" if total >= 80 else ("yellow" if total >= 60 else "red")

    os.makedirs(os.path.dirname(badge_path), exist_ok=True)
    with open(badge_path, "w", encoding="utf-8") as fh:
        json.dump(
            {"schemaVersion": 1, "label": "coverage", "message": f"{int(total)}%", "color": color},
            fh,
        )
    print(f"coverage badge written: {int(total)}% ({color})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
