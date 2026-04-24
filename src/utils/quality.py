"""
quality.py
Data-quality report helpers for the Internet Adoption Analysis pipeline.
"""
from __future__ import annotations

import pandas as pd


def print_quality_report(df: pd.DataFrame) -> None:
    """Print a data-quality report for the panel dataset.

    Reports:
    - Total row count
    - Count of interpolated internet_penetration_pct values per country
    - Count of null values per indicator column
    """
    indicator_cols = [
        "internet_penetration_pct",
        "gdp_per_capita_usd",
        "population",
        "urban_pop_share_pct",
        "broadband_per_100",
    ]

    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)
    print(f"Total rows       : {len(df):,}")
    print(f"Countries        : {df['iso3'].nunique()}")
    print(f"Year range       : {df['year'].min()} – {df['year'].max()}")

    # Null counts per indicator column
    print("\nNull values per indicator column:")
    for col in indicator_cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            null_pct = 100 * null_count / len(df) if len(df) > 0 else 0
            flag = "  *** WARNING: > 10%" if null_pct > 10 else ""
            print(f"  {col:<30} {null_count:>5} nulls  ({null_pct:.1f}%){flag}")

    # Interpolated values per country
    if "internet_pct_interpolated" in df.columns:
        interp_by_country = (
            df[df["internet_pct_interpolated"] == True]
            .groupby("iso3")
            .size()
            .sort_values(ascending=False)
        )
        total_interp = interp_by_country.sum()
        print(f"\nInterpolated internet_penetration_pct values: {total_interp} total")
        if len(interp_by_country) > 0:
            print("  Countries with interpolated values:")
            for iso3, count in interp_by_country.items():
                print(f"    {iso3}: {count} year(s)")
        else:
            print("  None.")

    print("=" * 60 + "\n")
