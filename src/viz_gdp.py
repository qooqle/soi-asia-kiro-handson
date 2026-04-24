"""
viz_gdp.py
Produces a scatter plot of GDP per capita (log scale) vs. internet penetration rate,
with a regression line, 95% CI band, Pearson r annotation, and country colour coding.

Usage:
    python src/viz_gdp.py
"""
from __future__ import annotations

import logging
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PANEL_PATH = "data/processed/panel_dataset.csv"
OUT_PATH = "outputs/gdp_vs_internet.png"
DPI = 150


def main() -> None:
    os.makedirs("outputs", exist_ok=True)

    df = pd.read_csv(PANEL_PATH)
    # Drop rows missing either axis variable
    plot_df = df.dropna(subset=["gdp_per_capita_usd", "internet_penetration_pct"]).copy()
    plot_df = plot_df[plot_df["gdp_per_capita_usd"] > 0]

    logger.info("Plotting %d country-year observations", len(plot_df))

    # Pearson correlation on log-GDP
    log_gdp = np.log10(plot_df["gdp_per_capita_usd"])
    r, p_value = stats.pearsonr(log_gdp, plot_df["internet_penetration_pct"])
    logger.info("Pearson r=%.3f, p=%.2e", r, p_value)

    # Colour palette — one colour per country
    countries = sorted(plot_df["iso3"].unique())
    palette = sns.color_palette("tab20", n_colors=len(countries))
    color_map = dict(zip(countries, palette))

    fig, ax = plt.subplots(figsize=(14, 9))

    # Scatter: colour by country, size by population
    pop_min = plot_df["population"].min()
    pop_max = plot_df["population"].max()
    sizes = 20 + 180 * (plot_df["population"] - pop_min) / (pop_max - pop_min + 1)

    for iso3 in countries:
        sub = plot_df[plot_df["iso3"] == iso3]
        ax.scatter(
            sub["gdp_per_capita_usd"],
            sub["internet_penetration_pct"],
            s=sizes[sub.index],
            color=color_map[iso3],
            alpha=0.6,
            label=iso3,
            linewidths=0,
        )

    # Regression line with 95% CI using seaborn on log-transformed x
    plot_df["log_gdp"] = log_gdp
    sns.regplot(
        data=plot_df,
        x="log_gdp",
        y="internet_penetration_pct",
        ax=ax,
        scatter=False,
        color="black",
        line_kws={"linewidth": 1.5, "linestyle": "--"},
        ci=95,
    )
    # Convert seaborn's log-x regression back to original scale for display
    # (seaborn regplot uses the log_gdp column directly, so x-axis needs relabelling)
    ax.set_xscale("log")
    # Re-draw on original scale
    ax.cla()

    # Redo scatter on log-scale axis
    for iso3 in countries:
        sub = plot_df[plot_df["iso3"] == iso3]
        ax.scatter(
            sub["gdp_per_capita_usd"],
            sub["internet_penetration_pct"],
            s=sizes[sub.index],
            color=color_map[iso3],
            alpha=0.6,
            label=iso3,
            linewidths=0,
        )

    ax.set_xscale("log")

    # Regression line on log scale
    x_fit = np.linspace(log_gdp.min(), log_gdp.max(), 200)
    slope, intercept, _, _, _ = stats.linregress(log_gdp, plot_df["internet_penetration_pct"])
    y_fit = slope * x_fit + intercept

    # 95% CI
    n = len(plot_df)
    se = np.sqrt(
        np.sum((plot_df["internet_penetration_pct"] - (slope * log_gdp + intercept)) ** 2) / (n - 2)
    )
    t_crit = stats.t.ppf(0.975, df=n - 2)
    x_mean = log_gdp.mean()
    ci = t_crit * se * np.sqrt(1 / n + (x_fit - x_mean) ** 2 / np.sum((log_gdp - x_mean) ** 2))

    ax.plot(10 ** x_fit, y_fit, color="black", linewidth=1.5, linestyle="--", label="_regression")
    ax.fill_between(10 ** x_fit, y_fit - ci, y_fit + ci, color="black", alpha=0.1, label="_ci")

    # Pearson annotation
    p_str = f"p < 0.001" if p_value < 0.001 else f"p = {p_value:.3f}"
    ax.annotate(
        f"Pearson r = {r:.3f}\n{p_str}",
        xy=(0.03, 0.92),
        xycoords="axes fraction",
        fontsize=11,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="grey", alpha=0.8),
    )

    # Axes
    ax.set_xlim(left=plot_df["gdp_per_capita_usd"].min() * 0.8)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_xlabel("GDP per Capita (constant 2015 USD, log scale)", fontsize=12)
    ax.set_ylabel("Internet Penetration Rate (% of population)", fontsize=12)
    ax.set_title(
        "GDP per Capita vs. Internet Penetration\nAsia, Oceania & Pacific Rim — 2010–2024",
        fontsize=14,
        fontweight="bold",
    )

    # Legend (countries only, outside plot)
    handles, labels = ax.get_legend_handles_labels()
    country_handles = [(h, l) for h, l in zip(handles, labels) if not l.startswith("_")]
    legend = ax.legend(
        [h for h, _ in country_handles],
        [l for _, l in country_handles],
        title="Country (ISO3)",
        bbox_to_anchor=(1.01, 1),
        loc="upper left",
        fontsize=7,
        title_fontsize=8,
        ncol=2,
        framealpha=0.9,
    )

    # Caption
    fig.text(
        0.5, -0.02,
        "Sources: World Bank (NY.GDP.PCAP.KD, IT.NET.USER.ZS) | "
        "Marker size proportional to population",
        ha="center", fontsize=9, color="grey",
    )

    plt.tight_layout()
    fig.savefig(OUT_PATH, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    size_kb = os.path.getsize(OUT_PATH) // 1024
    logger.info("Saved %s (%d KB)", OUT_PATH, size_kb)
    print(f"\nOutput: {OUT_PATH}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
