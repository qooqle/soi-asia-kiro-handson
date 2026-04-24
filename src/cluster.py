"""
cluster.py
Computes per-country adoption-pattern features, runs k-means clustering for k in {4,5},
selects k by silhouette score, and produces a PCA scatter plot and summary CSVs.

Usage:
    python src/cluster.py
"""
from __future__ import annotations

import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PANEL_PATH = "data/processed/panel_dataset.csv"
CLUSTER_ASSIGN_PATH = "data/processed/cluster_assignments.csv"
CLUSTER_SUMMARY_PATH = "outputs/cluster_summary.csv"
PCA_PLOT_PATH = "outputs/cluster_pca.png"
DPI = 150

# Sentinel for year_crossed_50pct when never reached
SENTINEL_YEAR = 2030


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-country clustering features from the panel dataset."""
    rows = []
    for iso3, grp in df.groupby("iso3"):
        grp = grp.sort_values("year")
        country_name = grp["country_name"].iloc[0]
        series = grp.set_index("year")["internet_penetration_pct"].dropna()

        if len(series) < 2:
            continue

        penetration_2010 = series.get(series.index.min(), np.nan)
        penetration_latest = series.iloc[-1]

        # Mean annual growth (year-on-year differences)
        yoy = series.diff().dropna()
        mean_annual_growth = yoy.mean() if len(yoy) > 0 else np.nan

        # First year penetration exceeded 50%
        above_50 = series[series > 50]
        year_crossed_50 = float(above_50.index.min()) if len(above_50) > 0 else SENTINEL_YEAR

        rows.append({
            "iso3": iso3,
            "country_name": country_name,
            "penetration_2010": penetration_2010,
            "penetration_latest": penetration_latest,
            "mean_annual_growth": mean_annual_growth,
            "year_crossed_50pct": year_crossed_50,
        })

    return pd.DataFrame(rows)


def main() -> None:
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    df = pd.read_csv(PANEL_PATH)
    features_df = compute_features(df)
    logger.info("Computed features for %d countries", len(features_df))

    feature_cols = ["penetration_2010", "penetration_latest", "mean_annual_growth", "year_crossed_50pct"]
    X_raw = features_df[feature_cols].fillna(features_df[feature_cols].median())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # K-means for k in {4, 5}
    results = {}
    for k in [4, 5]:
        km = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        results[k] = {"labels": labels, "score": score, "model": km}
        logger.info("k=%d  silhouette=%.4f", k, score)

    # Select best k
    best_k = max(results, key=lambda k: results[k]["score"])
    best_score = results[best_k]["score"]
    best_labels = results[best_k]["labels"]
    logger.info("Selected k=%d (silhouette=%.4f)", best_k, best_score)

    if best_score < 0.25:
        print(f"WARNING: Cluster separation is weak (silhouette = {best_score:.3f}); "
              "interpret results with caution.")

    features_df["cluster_label"] = best_labels

    # Write cluster assignments
    features_df.to_csv(CLUSTER_ASSIGN_PATH, index=False)
    logger.info("Saved %s", CLUSTER_ASSIGN_PATH)

    # Cluster summary (mean features per cluster)
    summary = features_df.groupby("cluster_label")[feature_cols].mean().round(2)
    summary["n_countries"] = features_df.groupby("cluster_label").size()
    summary.to_csv(CLUSTER_SUMMARY_PATH)
    logger.info("Saved %s", CLUSTER_SUMMARY_PATH)

    # PCA for 2-D visualisation
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    var_explained = pca.explained_variance_ratio_ * 100

    palette = plt.colormaps.get_cmap("tab10").resampled(best_k)
    fig, ax = plt.subplots(figsize=(10, 7))

    for cluster_id in range(best_k):
        mask = best_labels == cluster_id
        ax.scatter(
            X_pca[mask, 0], X_pca[mask, 1],
            color=palette(cluster_id),
            s=80, alpha=0.85,
            label=f"Cluster {cluster_id}",
            edgecolors="white", linewidths=0.5,
        )
        for idx in np.where(mask)[0]:
            ax.annotate(
                features_df.iloc[idx]["iso3"],
                (X_pca[idx, 0], X_pca[idx, 1]),
                fontsize=7, ha="center", va="bottom",
                xytext=(0, 4), textcoords="offset points",
            )

    ax.set_xlabel(f"PC1 ({var_explained[0]:.1f}% variance)", fontsize=11)
    ax.set_ylabel(f"PC2 ({var_explained[1]:.1f}% variance)", fontsize=11)
    ax.set_title(
        f"Country Clusters by Internet Adoption Pattern (k={best_k})\n"
        f"PCA of 4 features — silhouette score = {best_score:.3f}",
        fontsize=13, fontweight="bold",
    )
    ax.legend(title="Cluster", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)

    fig.text(
        0.5, -0.02,
        "Features: penetration_2010, penetration_latest, mean_annual_growth, year_crossed_50pct",
        ha="center", fontsize=8, color="grey",
    )

    plt.tight_layout()
    fig.savefig(PCA_PLOT_PATH, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    size_kb = os.path.getsize(PCA_PLOT_PATH) // 1024
    logger.info("Saved %s (%d KB)", PCA_PLOT_PATH, size_kb)

    # Print summary
    print(f"\nClustering complete.")
    print(f"  Selected k          : {best_k}")
    print(f"  Silhouette score    : {best_score:.4f}")
    print(f"\nCluster sizes:")
    for cid, count in features_df["cluster_label"].value_counts().sort_index().items():
        members = features_df[features_df["cluster_label"] == cid]["iso3"].tolist()
        print(f"  Cluster {cid}: {count} countries — {', '.join(members)}")
    print(f"\nOutputs:")
    print(f"  {CLUSTER_ASSIGN_PATH}")
    print(f"  {CLUSTER_SUMMARY_PATH}")
    print(f"  {PCA_PLOT_PATH}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
