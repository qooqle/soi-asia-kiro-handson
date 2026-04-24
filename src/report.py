"""
report.py
Generates a plain-language policy summary report (outputs/policy_summary.md)
from the panel dataset, cluster assignments, and key events config.

Usage:
    python src/report.py
"""
from __future__ import annotations

import logging
import os
import re
import sys

import pandas as pd
import textstat

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import load_key_events

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PANEL_PATH = "data/processed/panel_dataset.csv"
CLUSTER_PATH = "data/processed/cluster_assignments.csv"
OUT_PATH = "outputs/policy_summary.md"

CLUSTER_DESCRIPTIONS = {
    0: {
        "name": "Rapid-Growth Mid-Income",
        "narrative": (
            "These countries started with some internet access and grew fast. "
            "Better mobile networks and rising incomes helped more people get online. "
            "Many crossed the 50 percent mark in the mid-2010s."
        ),
    },
    1: {
        "name": "Large Developing Nations",
        "narrative": (
            "These are large countries where many people use the internet in total, "
            "but the share of the population online is still below the regional average. "
            "Growth has been steady, driven by mobile phones. "
            "Cost and coverage gaps remain in rural areas."
        ),
    },
    2: {
        "name": "High-Income Early Adopters",
        "narrative": (
            "These countries already had high internet use at the start of the study. "
            "By the end, nearly everyone was online. "
            "The focus has shifted from getting people connected to improving speed and skills."
        ),
    },
    3: {
        "name": "Low-Connectivity Frontier",
        "narrative": (
            "These are small island nations and low-income countries with the fewest people online. "
            "Distance, cost, and limited infrastructure make it hard to connect. "
            "Some saw faster growth after new undersea cables were laid nearby."
        ),
    },
}

EVENT_IMPACTS = {
    "Jio commercial launch": (
        "Reliance Jio launched in India in September 2016. "
        "It cut mobile data prices sharply across South Asia. "
        "More people in India got online in the years after. "
        "The regional average rose faster from 2017 onward."
    ),
    "Palapa Ring completion": (
        "Indonesia finished the Palapa Ring project in 2019. "
        "It linked remote eastern islands to the main internet network. "
        "More people in those areas could get online as a result. "
        "The full effect on usage took a few more years to show up."
    ),
    "Coral Sea Cable activation": (
        "The Coral Sea Cable went live in 2019. "
        "It gave Solomon Islands and Papua New Guinea fast, direct internet links for the first time. "
        "Before this, both countries relied on costly satellite links. "
        "The cable set the stage for more people to get online in the Pacific."
    ),
    "COVID-19 pandemic onset": (
        "COVID-19 hit in 2020 and pushed more people online fast. "
        "Work, school, and daily life moved to the internet. "
        "The share of people online rose more steeply from 2020 to 2022 "
        "than it had in the five years before."
    ),
    "Starlink Asia-Pacific expansion": (
        "Starlink began serving the Asia-Pacific region from 2022. "
        "It uses low-orbit satellites to bring internet to remote and island areas. "
        "Some Pacific island countries started to see early gains. "
        "Full data for 2023 and later is not yet available."
    ),
}


def build_report(panel: pd.DataFrame, clusters: pd.DataFrame, events: list[dict]) -> str:
    """Build the policy summary Markdown string."""
    n_countries = panel["iso3"].nunique()
    year_min = int(panel["year"].min())
    year_max = int(panel["year"].max())
    n_years = year_max - year_min + 1

    def weighted_mean_year(y: int) -> float:
        sub = panel[panel["year"] == y].dropna(subset=["internet_penetration_pct", "population"])
        if sub.empty:
            return float("nan")
        return (sub["internet_penetration_pct"] * sub["population"]).sum() / sub["population"].sum()

    mean_start = weighted_mean_year(year_min)
    mean_end = weighted_mean_year(year_max)

    lines: list[str] = []

    lines += [
        "# Internet Adoption in Asia, Oceania, and the Pacific Rim",
        f"## Policy Summary — {year_min}–{year_max}",
        "",
        f"*Prepared from World Bank public data. "
        f"Covers {n_countries} countries over {n_years} years ({year_min}–{year_max}).*",
        "",
        "## Overview",
        "",
        f"Internet access across Asia, Oceania, and the Pacific Rim has grown a lot "
        f"over the past 15 years. "
        f"The share of people using the internet rose from about "
        f"{mean_start:.0f} percent in {year_min} to about {mean_end:.0f} percent in {year_max}. "
        f"This report groups countries by how they grew, "
        f"and looks at key events that seem to have sped things up.",
        "",
        "## Key Findings",
        "",
    ]

    for cluster_id in sorted(clusters["cluster_label"].unique()):
        members = clusters[clusters["cluster_label"] == cluster_id]["country_name"].tolist()
        desc = CLUSTER_DESCRIPTIONS.get(cluster_id, {})
        cluster_name = desc.get("name", f"Cluster {cluster_id}")
        narrative = desc.get("narrative", "")
        lines += [
            f"### Group {cluster_id + 1}: {cluster_name}",
            "",
            f"**Countries:** {', '.join(members)}",
            "",
            narrative,
            "",
        ]

    lines += ["## Event Impacts", ""]
    for ev in events:
        ev_name = ev["name"]
        impact = EVENT_IMPACTS.get(ev_name, f"No impact description available for {ev_name}.")
        lines += [f"### {ev_name} ({ev['year']})", "", impact, ""]

    lines += [
        "## Data Limitations",
        "",
        "This report uses World Bank data, which can be one to two years behind for some countries. "
        "The ITU website does not offer a direct data download, "
        "so World Bank numbers are used for internet use rates. "
        "Some small Pacific island nations have gaps in their data. "
        "We filled short gaps of up to three years using a straight-line estimate. "
        "This report describes what the data shows. It does not prove cause and effect.",
        "",
        "## Scope",
        "",
        f"This report covers {n_countries} countries in Asia, Oceania, and the Pacific Rim "
        f"from {year_min} to {year_max}. "
        "It does not cover other regions or years before 2010. "
        "It does not make forecasts or policy recommendations. "
        "All findings describe what the data shows.",
        "",
    ]

    return "\n".join(lines)


def flesch_score(text: str) -> float:
    """Compute Flesch reading ease, falling back to a simple approximation if needed."""
    try:
        textstat.set_lang("en_legacy")
        return textstat.flesch_reading_ease(text)
    except Exception:
        pass
    try:
        return textstat.flesch_reading_ease(text)
    except Exception:
        words = text.split()
        sentences = max(1, len(re.findall(r"[.!?]+", text)))
        syllables = sum(max(1, len(re.findall(r"[aeiouAEIOU]+", w))) for w in words)
        n_words = max(1, len(words))
        return 206.835 - 1.015 * (n_words / sentences) - 84.6 * (syllables / n_words)


def main() -> None:
    os.makedirs("outputs", exist_ok=True)

    panel = pd.read_csv(PANEL_PATH)
    clusters = pd.read_csv(CLUSTER_PATH)
    events = load_key_events()

    report_text = build_report(panel, clusters, events)

    word_count = len(report_text.split())
    logger.info("Report word count: %d", word_count)
    if word_count > 1000:
        logger.warning("Policy summary exceeds 1,000 words (%d). Consider trimming.", word_count)

    fk_score = flesch_score(report_text)
    logger.info("Flesch-Kincaid reading ease: %.1f", fk_score)
    if fk_score < 50:
        logger.warning("Policy summary readability score %.1f is below target of 50.", fk_score)

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    size_kb = os.path.getsize(OUT_PATH) // 1024
    logger.info("Saved %s (%d KB)", OUT_PATH, size_kb)

    print(f"\nPolicy summary generated.")
    print(f"  Word count          : {word_count}  (target <= 1000)")
    print(f"  Flesch-Kincaid score: {fk_score:.1f}  (target >= 50)")
    print(f"  Sections            : Overview, Key Findings, Event Impacts, Data Limitations, Scope")
    print(f"  Output              : {OUT_PATH}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
