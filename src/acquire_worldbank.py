"""
acquire_worldbank.py
Downloads World Bank indicator series for all countries in scope and saves raw JSON
to data/raw/. Implements retry logic via http_client.get_with_retry.

Usage:
    python src/acquire_worldbank.py
"""
from __future__ import annotations

import json
import logging
import os
import sys

# Allow running as a script from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import load_countries
from src.utils.http_client import HTTPError, get_with_retry

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# World Bank REST API v2 base URL
WB_BASE = "https://api.worldbank.org/v2"

# Study period
YEAR_START = 2010
YEAR_END = 2024

# Indicators to download
INDICATORS = [
    "NY.GDP.PCAP.KD",   # GDP per capita (constant 2015 USD)
    "SP.POP.TOTL",       # Total population
    "SP.URB.TOTL.IN.ZS", # Urban population (% of total)
    "IT.NET.BBND.P2",    # Fixed broadband subscriptions per 100 people
    "IT.NET.USER.ZS",    # Individuals using the Internet (% of population) — WB fallback
]

RAW_DIR = "data/raw"


def iso3_to_iso2(iso3: str) -> str | None:
    """Convert ISO 3166-1 alpha-3 to alpha-2 using pycountry.
    Returns None if not found (e.g. TWN).
    """
    import pycountry
    # Special cases not in pycountry as sovereign states
    _MANUAL = {"TWN": "TW"}
    if iso3 in _MANUAL:
        return _MANUAL[iso3]
    country = pycountry.countries.get(alpha_3=iso3)
    return country.alpha_2 if country else None


def fetch_indicator(indicator: str, iso2_codes: list[str]) -> tuple[list[dict], int, int]:
    """Fetch one indicator for all countries in a single paginated request.

    Returns (records, success_count, failure_count).
    """
    # World Bank accepts semicolon-separated ISO2 codes
    country_str = ";".join(iso2_codes)
    url = f"{WB_BASE}/country/{country_str}/indicator/{indicator}"
    params = {
        "date": f"{YEAR_START}:{YEAR_END}",
        "format": "json",
        "per_page": "2000",  # large enough to get all country-years in one page
    }

    try:
        resp = get_with_retry(url, params=params)
        data = resp.json()
        # WB response: [metadata_dict, [records...]]
        records = data[1] if isinstance(data, list) and len(data) > 1 else []
        if records is None:
            records = []
        logger.info("  %s: fetched %d records", indicator, len(records))
        return records, 1, 0
    except (HTTPError, Exception) as exc:
        logger.error("  %s: FAILED — %s", indicator, exc)
        return [], 0, 1


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)

    countries = load_countries()
    iso2_codes = [iso3_to_iso2(c["iso3"]) for c in countries]
    iso2_codes = [c for c in iso2_codes if c]  # drop any unmapped codes

    total_success = 0
    total_failure = 0

    for indicator in INDICATORS:
        logger.info("Fetching indicator: %s", indicator)
        records, ok, fail = fetch_indicator(indicator, iso2_codes)
        total_success += ok
        total_failure += fail

        out_path = os.path.join(RAW_DIR, f"wb_{indicator}.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        logger.info("  Saved to %s (%d bytes)", out_path, os.path.getsize(out_path))

    print(f"\nWorld Bank acquisition complete.")
    print(f"  Indicators succeeded : {total_success}/{len(INDICATORS)}")
    print(f"  Indicators failed    : {total_failure}/{len(INDICATORS)}")

    # Show first record of GDP file as reviewable output
    gdp_path = os.path.join(RAW_DIR, "wb_NY.GDP.PCAP.KD.json")
    if os.path.exists(gdp_path):
        with open(gdp_path, encoding="utf-8") as fh:
            records = json.load(fh)
        if records:
            print(f"\nFirst record in wb_NY.GDP.PCAP.KD.json:")
            print(json.dumps(records[0], indent=2))


if __name__ == "__main__":
    main()
