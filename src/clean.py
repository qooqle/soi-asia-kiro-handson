"""
clean.py
Merges raw World Bank and ITU data into a tidy country-year panel dataset,
applies linear interpolation for small gaps, and writes data/processed/panel_dataset.csv.

Usage:
    python src/clean.py
"""
from __future__ import annotations

import json
import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import load_countries
from src.utils.quality import print_quality_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
YEAR_START = 2010
YEAR_END = 2024


def load_wb_indicator(indicator: str) -> pd.DataFrame:
    """Load a World Bank JSON file into a DataFrame with columns [iso3, year, <indicator>]."""
    path = os.path.join(RAW_DIR, f"wb_{indicator}.json")
    with open(path, encoding="utf-8") as fh:
        records = json.load(fh)

    rows = []
    for rec in records:
        iso3 = rec.get("countryiso3code", "")
        year_str = rec.get("date", "")
        value = rec.get("value")
        if iso3 and year_str.isdigit():
            rows.append({"iso3": iso3, "year": int(year_str), indicator: value})

    return pd.DataFrame(rows)


def load_internet_penetration(iso3_set: set[str]) -> pd.DataFrame:
    """Load internet penetration from itu_internet_use.csv (already merged with WB fallback)."""
    path = os.path.join(RAW_DIR, "itu_internet_use.csv")
    df = pd.read_csv(path, dtype={"iso3": str, "year": int})
    df = df[df["iso3"].isin(iso3_set)].copy()
    df = df[["iso3", "year", "internet_penetration_pct"]]
    return df


def interpolate_internet(group: pd.DataFrame) -> pd.DataFrame:
    """Apply linear interpolation for gaps of <= 3 consecutive missing values.

    Sets internet_pct_interpolated=True for filled rows, False otherwise.
    """
    group = group.sort_values("year").copy()
    original_null = group["internet_penetration_pct"].isna()

    # Interpolate (limit=3 means fill at most 3 consecutive NaNs)
    group["internet_penetration_pct"] = group["internet_penetration_pct"].interpolate(
        method="linear", limit=3, limit_direction="forward"
    )

    # Mark newly filled values
    now_filled = ~group["internet_penetration_pct"].isna() & original_null
    group["internet_pct_interpolated"] = now_filled

    return group


def main() -> None:
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    countries = load_countries()
    iso3_set = {c["iso3"] for c in countries}
    iso3_to_name = {c["iso3"]: c["country_name"] for c in countries}

    years = list(range(YEAR_START, YEAR_END + 1))

    # Build a complete skeleton: every (iso3, year) combination
    skeleton = pd.DataFrame(
        [{"iso3": iso3, "year": year} for iso3 in sorted(iso3_set) for year in years]
    )
    skeleton["country_name"] = skeleton["iso3"].map(iso3_to_name)

    logger.info("Skeleton: %d rows (%d countries × %d years)", len(skeleton), len(iso3_set), len(years))

    # Load internet penetration
    logger.info("Loading internet penetration data...")
    internet_df = load_internet_penetration(iso3_set)

    # Load World Bank indicators
    logger.info("Loading World Bank indicators...")
    gdp_df = load_wb_indicator("NY.GDP.PCAP.KD").rename(columns={"NY.GDP.PCAP.KD": "gdp_per_capita_usd"})
    pop_df = load_wb_indicator("SP.POP.TOTL").rename(columns={"SP.POP.TOTL": "population"})
    urban_df = load_wb_indicator("SP.URB.TOTL.IN.ZS").rename(columns={"SP.URB.TOTL.IN.ZS": "urban_pop_share_pct"})
    bb_df = load_wb_indicator("IT.NET.BBND.P2").rename(columns={"IT.NET.BBND.P2": "broadband_per_100"})

    # Merge all onto skeleton
    panel = skeleton.copy()
    for df, label in [
        (internet_df, "internet"),
        (gdp_df, "gdp"),
        (pop_df, "population"),
        (urban_df, "urban"),
        (bb_df, "broadband"),
    ]:
        panel = panel.merge(df, on=["iso3", "year"], how="left")
        logger.info("  Merged %s: panel now %d rows", label, len(panel))

    # Filter to scope
    panel = panel[panel["iso3"].isin(iso3_set)].copy()

    # Deduplicate
    before = len(panel)
    panel = panel.drop_duplicates(subset=["iso3", "year"])
    if len(panel) < before:
        logger.warning("Dropped %d duplicate (iso3, year) rows", before - len(panel))

    # Apply interpolation per country
    logger.info("Applying linear interpolation (limit=3 consecutive gaps)...")
    groups = []
    for _, grp in panel.groupby("iso3", group_keys=False):
        groups.append(interpolate_internet(grp))
    panel = pd.concat(groups, ignore_index=True)

    # Ensure correct column order and types
    panel["internet_pct_interpolated"] = panel["internet_pct_interpolated"].fillna(False).astype(bool)
    panel["year"] = panel["year"].astype(int)

    col_order = [
        "iso3", "country_name", "year",
        "internet_penetration_pct", "gdp_per_capita_usd",
        "population", "urban_pop_share_pct", "broadband_per_100",
        "internet_pct_interpolated",
    ]
    panel = panel[col_order]
    panel = panel.sort_values(["iso3", "year"]).reset_index(drop=True)

    # Write output
    out_path = os.path.join(PROCESSED_DIR, "panel_dataset.csv")
    panel.to_csv(out_path, index=False, encoding="utf-8")
    logger.info("Wrote %s (%d rows)", out_path, len(panel))

    # Print quality report
    print_quality_report(panel)
    print(f"panel_dataset.csv: {len(panel)} rows, {panel['iso3'].nunique()} countries, "
          f"years {panel['year'].min()}–{panel['year'].max()}")


if __name__ == "__main__":
    main()
