"""
viz_trends.py
Produces a small-multiples line chart with one panel per country showing
internet penetration rate over time (2010–2024).

Usage:
    python src/viz_trends.py
"""
from __future__ import annotations

import logging
import math
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PANEL_PATH = "data/processed/panel_dataset.csv"
OUT_PATH = "outputs/country_trends.png"
DPI = 150


def main() -> None:
    os.makedirs("outputs", exist_ok=True)

    df = pd.read_csv(PANEL_PATH)
    countries = sorted(df["iso3"].unique())
    n = len(countries)

    # Grid layout: aim for ~6 columns
    ncols = 6
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(ncols * 3, nrows * 2.5),
        sharey=True,
    )
    axes_flat = axes.flatten()

    for i, iso3 in enumerate(countries):
        ax = axes_flat[i]
        sub = df[df["iso3"] == iso3].sort_values("year")
        country_name = sub["country_name"].iloc[0] if len(sub) > 0 else iso3

        ax.plot(
            sub["year"],
            sub["internet_penetration_pct"],
            color="#1f77b4",
            linewidth=1.5,
            marker="o",
            markersize=2.5,
        )
        ax.set_ylim(0, 100)
        ax.set_xlim(2010, 2024)
        ax.set_title(f"{iso3}\n{country_name}", fontsize=7, pad=3)
        ax.tick_params(axis="both", labelsize=6)
        ax.set_xticks([2010, 2015, 2020, 2024])
        ax.set_xticklabels(["'10", "'15", "'20", "'24"], fontsize=5)
        ax.yaxis.set_tick_params(labelsize=6)
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)

    # Hide unused subplots
    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)

    # Shared y-axis label
    fig.text(0.01, 0.5, "Internet Penetration (% of population)", va="center",
             rotation="vertical", fontsize=10)

    fig.suptitle(
        "Internet Penetration Trends by Country — 2010–2024\n"
        "Asia, Oceania & Pacific Rim",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.text(
        0.5, -0.01,
        "Source: World Bank (IT.NET.USER.ZS). Y-axis: 0–100% (consistent across all panels).",
        ha="center", fontsize=8, color="grey",
    )

    plt.tight_layout()
    fig.savefig(OUT_PATH, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    size_kb = os.path.getsize(OUT_PATH) // 1024
    logger.info("Saved %s (%d KB)", OUT_PATH, size_kb)
    print(f"\nOutput: {OUT_PATH}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
