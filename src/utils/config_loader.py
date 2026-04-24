"""
config_loader.py
Loads and validates configuration files for the Internet Adoption Analysis pipeline.
"""
from __future__ import annotations

import pycountry
import yaml


class ConfigError(ValueError):
    """Raised when a configuration file fails validation."""


def load_countries(path: str = "config/countries.yaml") -> list[dict]:
    """Load and validate the country scope configuration.

    Returns a flat list of dicts with keys: iso3, country_name, sub_region.

    Raises ConfigError if:
    - The file is missing or unreadable
    - The country count is outside [30, 40]
    - Any iso3 code is not a valid ISO 3166-1 alpha-3 code
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        raise ConfigError(f"countries.yaml not found at {path}")
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse {path}: {exc}")

    sub_regions = data.get("sub_regions", {})
    countries: list[dict] = []

    for region_name, entries in sub_regions.items():
        if not entries:
            continue
        for entry in entries:
            iso3 = entry.get("iso3", "").strip().upper()
            country_name = entry.get("country_name", "").strip()
            countries.append(
                {"iso3": iso3, "country_name": country_name, "sub_region": region_name}
            )

    # Validate count
    count = len(countries)
    if count < 30 or count > 40:
        raise ConfigError(
            f"Expected between 30 and 40 countries, got {count}. "
            "Please update config/countries.yaml."
        )

    # Validate ISO3 codes
    for i, c in enumerate(countries):
        iso3 = c["iso3"]
        # pycountry does not include Taiwan (TWN) as a sovereign state;
        # allow it explicitly as a known valid code.
        if iso3 == "TWN":
            continue
        if pycountry.countries.get(alpha_3=iso3) is None:
            raise ConfigError(
                f"Invalid ISO 3166-1 alpha-3 code '{iso3}' at entry {i + 1} "
                f"(country_name='{c['country_name']}')."
            )

    return countries


def load_key_events(path: str = "config/key_events.yaml") -> list[dict]:
    """Load key event definitions from YAML.

    Returns a list of dicts with keys: name (str), year (int), month (int, optional).

    Raises ConfigError if the file is missing or unparseable.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        raise ConfigError(f"key_events.yaml not found at {path}")
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse {path}: {exc}")

    events = data.get("key_events", [])
    return [
        {k: v for k, v in event.items() if k in ("name", "year", "month")}
        for event in events
    ]


if __name__ == "__main__":
    countries = load_countries()
    print(f"Loaded {len(countries)} countries:")
    for c in countries:
        print(f"  [{c['sub_region']}] {c['iso3']} — {c['country_name']}")

    events = load_key_events()
    print(f"\nLoaded {len(events)} key events:")
    for e in events:
        month_str = f"-{e['month']:02d}" if "month" in e else ""
        print(f"  {e['year']}{month_str}: {e['name']}")
