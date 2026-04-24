"""
acquire_itu.py
Downloads ITU internet-use data, falls back to World Bank IT.NET.USER.ZS for missing
country-years, and writes a provenance log.

Usage:
    python src/acquire_itu.py
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import load_countries
from src.utils.http_client import get_with_retry

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = "data/raw"
YEAR_START = 2010
YEAR_END = 2024

# ITU Data Hub — bulk CSV export for IT_NET_USER_PP
ITU_URL = "https://datahub.itu.int/data/?e=IT_NET_USER_PP&bu=0&d=WITS_CS"


def load_wb_fallback(iso3_set: set[str]) -> dict[tuple[str, int], float]:
    """Load World Bank IT.NET.USER.ZS as a fallback lookup {(iso3, year): value}."""
    wb_path = os.path.join(RAW_DIR, "wb_IT.NET.USER.ZS.json")
    if not os.path.exists(wb_path):
        logger.warning("WB fallback file not found: %s", wb_path)
        return {}

    with open(wb_path, encoding="utf-8") as fh:
        records = json.load(fh)

    lookup: dict[tuple[str, int], float] = {}
    for rec in records:
        iso3 = rec.get("countryiso3code", "")
        year_str = rec.get("date", "")
        value = rec.get("value")
        if iso3 in iso3_set and year_str.isdigit() and value is not None:
            lookup[(iso3, int(year_str))] = float(value)
    return lookup


def fetch_itu_data() -> dict[tuple[str, int], float]:
    """Attempt to download ITU bulk CSV and parse into {(iso3, year): value}.
    Returns empty dict on failure (fallback will cover all values).
    """
    logger.info("Fetching ITU internet-use data from %s", ITU_URL)
    try:
        resp = get_with_retry(ITU_URL, timeout=60)
        content = resp.text

        # ITU CSV has varying headers; try to detect iso3, year, value columns
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
        logger.info("ITU CSV columns: %s", fieldnames)

        # Normalise column names to lowercase for flexible matching
        col_map = {f.lower().strip(): f for f in fieldnames}

        iso3_col = next((col_map[k] for k in col_map if "iso" in k or "code" in k), None)
        year_col = next((col_map[k] for k in col_map if "year" in k), None)
        val_col = next(
            (col_map[k] for k in col_map if "value" in k or "percent" in k or "%" in k),
            None,
        )

        if not all([iso3_col, year_col, val_col]):
            logger.warning(
                "Could not identify required columns in ITU CSV "
                "(iso3=%s, year=%s, value=%s). Will use WB fallback for all.",
                iso3_col, year_col, val_col,
            )
            return {}

        itu: dict[tuple[str, int], float] = {}
        for row in reader:
            iso3 = row.get(iso3_col, "").strip().upper()
            year_str = row.get(year_col, "").strip()
            val_str = row.get(val_col, "").strip()
            if iso3 and year_str.isdigit() and val_str:
                try:
                    itu[(iso3, int(year_str))] = float(val_str)
                except ValueError:
                    pass

        logger.info("ITU data parsed: %d country-year records", len(itu))
        return itu

    except Exception as exc:
        logger.warning("ITU download failed (%s). Will use WB fallback for all values.", exc)
        return {}


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)

    countries = load_countries()
    iso3_set = {c["iso3"] for c in countries}
    iso3_to_name = {c["iso3"]: c["country_name"] for c in countries}

    # Build year range
    years = list(range(YEAR_START, YEAR_END + 1))

    # Fetch ITU data
    itu_data = fetch_itu_data()

    # Load WB fallback
    wb_fallback = load_wb_fallback(iso3_set)

    # Build merged dataset and provenance log
    merged_rows: list[dict] = []
    provenance_rows: list[dict] = []

    for iso3 in sorted(iso3_set):
        for year in years:
            key = (iso3, year)
            if key in itu_data:
                value = itu_data[key]
                source = "ITU"
            elif key in wb_fallback:
                value = wb_fallback[key]
                source = "WorldBank_IT.NET.USER.ZS"
            else:
                value = None
                source = "missing"

            merged_rows.append({
                "iso3": iso3,
                "country_name": iso3_to_name.get(iso3, ""),
                "year": year,
                "internet_penetration_pct": value,
            })
            provenance_rows.append({
                "iso3": iso3,
                "year": year,
                "source": source,
            })

    # Write ITU merged CSV
    itu_out = os.path.join(RAW_DIR, "itu_internet_use.csv")
    with open(itu_out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["iso3", "country_name", "year", "internet_penetration_pct"])
        writer.writeheader()
        writer.writerows(merged_rows)
    logger.info("Saved %s (%d rows)", itu_out, len(merged_rows))

    # Write provenance log
    prov_out = os.path.join(RAW_DIR, "provenance.csv")
    with open(prov_out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["iso3", "year", "source"])
        writer.writeheader()
        writer.writerows(provenance_rows)
    logger.info("Saved %s (%d rows)", prov_out, len(provenance_rows))

    # Summary
    itu_count = sum(1 for r in provenance_rows if r["source"] == "ITU")
    wb_count = sum(1 for r in provenance_rows if r["source"] == "WorldBank_IT.NET.USER.ZS")
    missing_count = sum(1 for r in provenance_rows if r["source"] == "missing")

    print(f"\nITU acquisition complete.")
    print(f"  ITU primary values      : {itu_count}")
    print(f"  World Bank fallback     : {wb_count}")
    print(f"  Missing (no source)     : {missing_count}")

    # Show first 10 rows of provenance
    print(f"\nFirst 10 rows of provenance.csv:")
    print(f"  {'iso3':<6} {'year':<6} {'source'}")
    print(f"  {'-'*5} {'-'*5} {'-'*30}")
    for row in provenance_rows[:10]:
        print(f"  {row['iso3']:<6} {row['year']:<6} {row['source']}")


if __name__ == "__main__":
    main()
