"""
verify_outputs.py
Verifies that all required pipeline outputs exist and meet the success criteria
defined in requirements.md (Requirement 12).

Usage:
    python src/verify_outputs.py
Exit code 0 = all checks passed. Exit code 1 = one or more checks failed.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
from PIL import Image

REQUIRED_IMAGES = [
    "outputs/gdp_vs_internet.png",
    "outputs/country_trends.png",
    "outputs/cluster_pca.png",
    "outputs/annotated_timeline.png",
]
REQUIRED_FILES = REQUIRED_IMAGES + ["outputs/policy_summary.md"]

PANEL_PATH = "data/processed/panel_dataset.csv"
MIN_COUNTRIES = 30
MIN_YEARS = 10
MAX_NULL_RATE = 0.10
MIN_DPI = 150
MAX_WORDS = 1000


def check(label: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}]  {label}{suffix}")
    return passed


def main() -> None:
    print("\nVerifying pipeline outputs against success criteria (Requirement 12)...")
    print("-" * 65)

    results: list[bool] = []

    # 12.1 — All five output files exist
    for path in REQUIRED_FILES:
        exists = os.path.exists(path)
        size_kb = os.path.getsize(path) // 1024 if exists else 0
        results.append(check(f"File exists: {path}", exists, f"{size_kb} KB" if exists else "MISSING"))

    # DPI check for images
    for path in REQUIRED_IMAGES:
        if os.path.exists(path):
            img = Image.open(path)
            dpi = img.info.get("dpi", (0, 0))
            dpi_val = dpi[0] if dpi[0] else 0
            results.append(check(
                f"DPI >= {MIN_DPI}: {path}",
                dpi_val >= MIN_DPI,
                f"DPI={dpi_val:.0f}",
            ))

    # 12.2 — Panel covers >= 30 countries and >= 10 years
    if os.path.exists(PANEL_PATH):
        panel = pd.read_csv(PANEL_PATH)
        n_countries = panel["iso3"].nunique()
        n_years = panel["year"].nunique()
        results.append(check(
            f"Panel covers >= {MIN_COUNTRIES} countries",
            n_countries >= MIN_COUNTRIES,
            f"{n_countries} countries",
        ))
        results.append(check(
            f"Panel covers >= {MIN_YEARS} years",
            n_years >= MIN_YEARS,
            f"{n_years} years",
        ))

        # 12.3 — Null rate in internet_penetration_pct <= 10%
        null_rate = panel["internet_penetration_pct"].isna().mean()
        results.append(check(
            f"Null rate in internet_penetration_pct <= {MAX_NULL_RATE:.0%}",
            null_rate <= MAX_NULL_RATE,
            f"{null_rate:.1%}",
        ))
    else:
        results.append(check(f"Panel dataset exists: {PANEL_PATH}", False, "MISSING"))

    # 12.5 — Policy summary word count <= 1000
    summary_path = "outputs/policy_summary.md"
    if os.path.exists(summary_path):
        with open(summary_path, encoding="utf-8") as fh:
            text = fh.read()
        word_count = len(text.split())
        results.append(check(
            f"Policy summary word count <= {MAX_WORDS}",
            word_count <= MAX_WORDS,
            f"{word_count} words",
        ))
    else:
        results.append(check(f"Policy summary word count <= {MAX_WORDS}", False, "file missing"))

    # Summary
    print("-" * 65)
    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} checks passed.\n")

    if passed < total:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
