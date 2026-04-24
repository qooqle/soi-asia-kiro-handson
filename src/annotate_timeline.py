"""
annotate_timeline.py
Plots the population-weighted mean internet penetration rate across all countries
in scope, annotated with key events from config/key_events.yaml.

Usage:
    python src/annotate_timeline.py
"""
from __future__ import annotations

import logging
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import load_key_events

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PANEL_PATH = "data/processed/panel_dataset.csv"
OUT_PATH = "outputs/annotated_timeline.png"
DPI = 150


def compute_weighted_mean(df: pd.DataFrame) -> pd.DataFrame:
    """Compute population-weighted mean internet penetration per year."""
    valid = df.dropna(subset=["internet_penetration_pct", "population"]).copy()
    valid["weighted"] = valid["internet_penetration_pct"] * valid["population"]
    agg = valid.groupby("year").agg(
        weighted_sum=("weighted", "sum"),
        pop_sum=("population", "sum"),
    )
    agg["weighted_mean"] = agg["weighted_sum"] / agg["pop_sum"]
    return agg.reset_index()[["year", "weighted_mean"]]


def main() -> None:
    os.makedirs("outputs", exist_ok=True)

    df = pd.read_csv(PANEL_PATH)
    trend = compute_weighted_mean(df)
    logger.info("Computed weighted mean for %d years", len(trend))

    # Load key events
    events = load_key_events()
    year_min = int(trend["year"].min())
    year_max = int(trend["year"].max())

    # Filter events to study period
    valid_events = []
    for ev in events:
        if year_min <= ev["year"] <= year_max:
            valid_events.append(ev)
        else:
            logger.warning(
                "Key event '%s' (year=%d) is outside study period %d–%d; skipping.",
                ev["name"], ev["year"], year_min, year_max,
            )

    fig, ax = plt.subplots(figsize=(13, 6))

    # Main trend line
    ax.plot(
        trend["year"], trend["weighted_mean"],
        color="#1f77b4", linewidth=2.5, marker="o", markersize=5,
        label="Population-weighted mean",
        zorder=3,
    )
    ax.fill_between(trend["year"], 0, trend["weighted_mean"], alpha=0.08, color="#1f77b4")

    # Event annotations — alternate label heights to avoid overlap
    label_heights = [0.82, 0.70, 0.58, 0.46, 0.34]
    for i, ev in enumerate(valid_events):
        year = ev["year"]
        label_y = label_heights[i % len(label_heights)]
        ax.axvline(x=year, color="grey", linestyle="--", linewidth=1.0, alpha=0.7, zorder=2)
        ax.text(
            year + 0.1,
            label_y,
            ev["name"],
            transform=ax.get_xaxis_transform(),
            fontsize=8,
            color="dimgrey",
            rotation=0,
            ha="left",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="lightgrey", alpha=0.85),
        )

    ax.set_xlim(year_min - 0.3, year_max + 0.3)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(year_min, year_max + 1))
    ax.set_xticklabels([str(y) for y in range(year_min, year_max + 1)], rotation=45, ha="right")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Population-Weighted Mean Internet Penetration (%)", fontsize=11)
    ax.set_title(
        "Regional Internet Adoption Trend — Asia, Oceania & Pacific Rim\n"
        "Population-Weighted Mean with Key Events Annotated",
        fontsize=13, fontweight="bold",
    )
    ax.grid(True, linestyle=":", alpha=0.5)

    # Legend for events
    from matplotlib.lines import Line2D
    event_handles = [
        Line2D([0], [0], color="grey", linestyle="--", linewidth=1.0, label=ev["name"])
        for ev in valid_events
    ]
    trend_handle = Line2D([0], [0], color="#1f77b4", linewidth=2.5, marker="o",
                          markersize=5, label="Population-weighted mean")
    ax.legend(
        handles=[trend_handle] + event_handles,
        loc="upper left", fontsize=8, framealpha=0.9,
    )

    fig.text(
        0.5, -0.04,
        "Source: World Bank (IT.NET.USER.ZS, SP.POP.TOTL). "
        "Weighted mean = Σ(penetration × population) / Σ(population) per year.",
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
