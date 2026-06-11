"""G2 Aggregate Dynamics: characterize temporal variation of L2 co-growth graph.

Scientific question: how does the aggregate structure of the L2 graph vary over
time by country and sector?  Metrics: density, weight distribution, intensity,
dispersion, positive/negative fractions, turnover, Jaccard, period comparisons.

This module is a DESCRIPTIVE analysis.  It does not test causal hypotheses, does
not name individual edges as stable relationships, and does not pool counts
across countries.

Constraints (from DEC-024, DEC-021, DEC-023):
- Edges are statistical co-movement associations, not causality.
- Individual edges are NOT stable (M2 0.06-0.26; threshold 0.70).
- Communities are NOT validated (DEC-021).
- Residual corrector DOES NOT improve forecasting (DEC-023).
- FR aggregate temporal signal is COVID-robust; NL and PT are COVID-sensitive.
- No cross-country pooling of counts.  No economic recommendation.

Periods (defined by observation_year):
- pre-2020: observation_year < 2020
- 2020: observation_year == 2020
- post-2020: observation_year > 2020

Do NOT confuse observation_year (year that participates in the window) with
available_for_forecast_year (year in which the graph becomes available).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
OUT_DIR = BASE / "data/processed/economic_graph/g2_dynamics"

_BUILDER_DIR = str(Path(__file__).parent)
if _BUILDER_DIR not in sys.path:
    sys.path.insert(0, _BUILDER_DIR)

from build_g1_l2_cogrowth import (  # noqa: E402
    build_growth_matrix,
    window_matrix,
    pairwise_corr,
    eval_years_for_country,
    eligible_sectors,
)

from build_g2_corrected_controls import (  # noqa: E402
    top_k_adjacency,
    jaccard_binary,
)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

WINDOW = 5
MIN_PERIODS = 4
TOP_K_PRINCIPAL = 5
TOP_K_VARIANTS = [3, 5, 10]
COVID_OBS_YEAR = 2020
BOOTSTRAP_SEED = 42
N_BOOTSTRAP = 200
BOOTSTRAP_FRAC = 0.8  # fraction of pairs to resample

NEAR_ZERO_THRESHOLD = 0.05  # |weight| < threshold counts as near-zero


# ---------------------------------------------------------------------------
# Period definition (by observation_year)
# ---------------------------------------------------------------------------

def classify_period(obs_year: int) -> str:
    """Classify observation_year into pre-2020/2020/post-2020."""
    if obs_year < 2020:
        return "pre-2020"
    elif obs_year == 2020:
        return "2020"
    else:
        return "post-2020"


# ---------------------------------------------------------------------------
# Per-year graph metrics
# ---------------------------------------------------------------------------

def graph_annual_metrics(
    corr: np.ndarray,
    adj: np.ndarray,
    n_regions: int,
) -> dict:
    """Compute aggregate metrics for one year's graph.

    corr: full pairwise correlation matrix (n x n), may contain NaN.
    adj: binary top-k adjacency (n x n), bool.
    n_regions: number of territories.
    """
    n_possible = n_regions * (n_regions - 1) // 2
    mask_ut = np.triu(np.ones((n_regions, n_regions), dtype=bool), k=1)

    # Edge validity: both corr[i,j] and adj[i,j] defined
    adj_ut = adj[mask_ut].astype(bool)
    corr_ut = corr[mask_ut]

    n_edges_valid = int(adj_ut.sum())
    density = n_edges_valid / n_possible if n_possible > 0 else np.nan

    # Weights of connected edges
    weights = corr_ut[adj_ut]
    weights = weights[np.isfinite(weights)]

    if len(weights) == 0:
        return {
            "n_regions": n_regions,
            "n_possible_pairs": n_possible,
            "n_edges_valid": 0,
            "density": 0.0,
            "mean_weight": np.nan,
            "median_weight": np.nan,
            "std_weight": np.nan,
            "p10_weight": np.nan,
            "p25_weight": np.nan,
            "p75_weight": np.nan,
            "p90_weight": np.nan,
            "frac_positive": np.nan,
            "frac_negative": np.nan,
            "frac_near_zero": np.nan,
            "mean_abs_weight": np.nan,
        }

    return {
        "n_regions": n_regions,
        "n_possible_pairs": n_possible,
        "n_edges_valid": n_edges_valid,
        "density": density,
        "mean_weight": float(np.mean(weights)),
        "median_weight": float(np.median(weights)),
        "std_weight": float(np.std(weights)),
        "p10_weight": float(np.percentile(weights, 10)),
        "p25_weight": float(np.percentile(weights, 25)),
        "p75_weight": float(np.percentile(weights, 75)),
        "p90_weight": float(np.percentile(weights, 90)),
        "frac_positive": float(np.mean(weights > 0)),
        "frac_negative": float(np.mean(weights < 0)),
        "frac_near_zero": float(np.mean(np.abs(weights) < NEAR_ZERO_THRESHOLD)),
        "mean_abs_weight": float(np.mean(np.abs(weights))),
    }


# ---------------------------------------------------------------------------
# Turnover and Jaccard
# ---------------------------------------------------------------------------

def consecutive_turnover_topk(adj_prev: np.ndarray, adj_curr: np.ndarray) -> float:
    """Fraction of edges that changed between two consecutive top-k graphs.

    Turnover = 1 - Jaccard(prev, curr).
    """
    j = jaccard_binary(adj_prev, adj_curr)
    return 1.0 - j if np.isfinite(j) else np.nan


# ---------------------------------------------------------------------------
# Year-over-year change
# ---------------------------------------------------------------------------

def yoy_change(metrics_prev: dict, metrics_curr: dict) -> dict:
    """Compute absolute and relative change for key metrics."""
    result = {}
    for key in ["mean_weight", "median_weight", "density", "mean_abs_weight"]:
        prev_val = metrics_prev.get(key, np.nan)
        curr_val = metrics_curr.get(key, np.nan)
        if np.isfinite(prev_val) and np.isfinite(curr_val):
            abs_change = curr_val - prev_val
            if abs(prev_val) > 1e-9:
                rel_change = abs_change / abs(prev_val)
            else:
                rel_change = np.nan
        else:
            abs_change = np.nan
            rel_change = np.nan
        result[f"{key}_abs_change"] = abs_change
        result[f"{key}_rel_change"] = rel_change
    return result


# ---------------------------------------------------------------------------
# Pair-resampling sensitivity intervals
# ---------------------------------------------------------------------------

def bootstrap_metric(
    corr: np.ndarray,
    adj: np.ndarray,
    n_bootstrap: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
    frac: float = BOOTSTRAP_FRAC,
) -> dict:
    """Compute descriptive pair-resampling intervals for two graph metrics.

    Territory pairs are not independent because pairs share nodes. These
    intervals therefore quantify sensitivity to the observed pair set; they
    are not population confidence intervals and must not be used for
    inferential claims.
    """
    n = corr.shape[0]
    mask_ut = np.triu(np.ones((n, n), dtype=bool), k=1)
    adj_ut = adj[mask_ut].astype(bool)
    corr_ut = corr[mask_ut]
    n_pairs = int(mask_ut.sum())
    sample_size = max(1, int(n_pairs * frac))

    rng = np.random.default_rng(seed)
    boot_means = []
    boot_densities = []

    for _ in range(n_bootstrap):
        idx = rng.choice(n_pairs, size=sample_size, replace=True)
        b_adj = adj_ut[idx]
        b_corr = corr_ut[idx]
        b_weights = b_corr[b_adj & np.isfinite(b_corr)]
        if len(b_weights) > 0:
            boot_means.append(float(np.mean(b_weights)))
        else:
            boot_means.append(np.nan)
        boot_densities.append(float(b_adj.sum()) / sample_size if sample_size > 0 else np.nan)

    finite_means = [v for v in boot_means if np.isfinite(v)]
    finite_densities = [v for v in boot_densities if np.isfinite(v)]

    return {
        "pair_resample_mean_weight_p025": float(np.percentile(finite_means, 2.5)) if finite_means else np.nan,
        "pair_resample_mean_weight_p975": float(np.percentile(finite_means, 97.5)) if finite_means else np.nan,
        "pair_resample_density_p025": float(np.percentile(finite_densities, 2.5)) if finite_densities else np.nan,
        "pair_resample_density_p975": float(np.percentile(finite_densities, 97.5)) if finite_densities else np.nan,
        "pair_resample_n": n_bootstrap,
        "pair_resample_frac": frac,
        "pair_resample_seed": seed,
    }


# ---------------------------------------------------------------------------
# Period summary
# ---------------------------------------------------------------------------

def period_summary(annual_rows: list[dict], period: str) -> dict:
    """Summarize metrics for a period (pre-2020 / 2020 / post-2020)."""
    rows = [r for r in annual_rows if r.get("period") == period]
    n_years = len(rows)
    if n_years == 0:
        return {"period": period, "n_years": 0}

    summary = {"period": period, "n_years": n_years}
    for key in [
        "density", "mean_weight", "median_weight", "std_weight",
        "mean_abs_weight", "frac_positive", "frac_negative",
        "frac_near_zero", "n_edges_valid",
    ]:
        vals = [r[key] for r in rows if np.isfinite(r.get(key, np.nan))]
        if vals:
            summary[f"{key}_mean"] = float(np.mean(vals))
            summary[f"{key}_min"] = float(np.min(vals))
            summary[f"{key}_max"] = float(np.max(vals))
        else:
            summary[f"{key}_mean"] = np.nan
            summary[f"{key}_min"] = np.nan
            summary[f"{key}_max"] = np.nan
    return summary


def period_comparison(
    pre_summary: dict, post_summary: dict, label: str,
) -> dict:
    """Compute difference between two period summaries."""
    result = {"comparison": label}
    for key in [
        "density", "mean_weight", "median_weight", "std_weight",
        "mean_abs_weight", "frac_positive", "frac_negative",
    ]:
        pre_val = pre_summary.get(f"{key}_mean", np.nan)
        post_val = post_summary.get(f"{key}_mean", np.nan)
        if np.isfinite(pre_val) and np.isfinite(post_val):
            diff = post_val - pre_val
            if abs(pre_val) > 1e-9:
                rel_eff = diff / abs(pre_val)
            else:
                rel_eff = np.nan
        else:
            diff = np.nan
            rel_eff = np.nan
        result[f"{key}_diff"] = diff
        result[f"{key}_rel_effect"] = rel_eff
    result["pre_n_years"] = pre_summary.get("n_years", 0)
    result["post_n_years"] = post_summary.get("n_years", 0)
    return result


# ---------------------------------------------------------------------------
# Build full analysis for one country×sector
# ---------------------------------------------------------------------------

def build_sector_analysis(
    panel: pd.DataFrame,
    country: str,
    sector: str,
    k: int,
    exclude_years: frozenset[int] = frozenset(),
) -> tuple[list[dict], list[dict], list[dict]]:
    """Build annual metrics, period summaries, and period comparisons.

    Returns (annual_rows, period_rows, comparison_rows).
    """
    region_ids, growth_years, matrix = build_growth_matrix(panel, country, sector)
    n_regions = len(region_ids)

    # Determine eval years
    first_eval = growth_years[0] + WINDOW
    last_eval = growth_years[-1] + 1
    eval_years = list(range(first_eval, last_eval + 1))

    annual_rows = []
    prev_adj = None
    prev_metrics = None
    prev_corr = None

    for eval_year in eval_years:
        wmat = window_matrix(growth_years, matrix, eval_year, WINDOW, exclude_years)
        if wmat.shape[0] < MIN_PERIODS:
            continue

        corr = pairwise_corr(wmat, MIN_PERIODS)
        if np.all(np.isnan(corr)):
            continue

        adj = top_k_adjacency(corr, k)
        metrics = graph_annual_metrics(corr, adj, n_regions)

        # YoY change
        yoy = {}
        turnover = np.nan
        jaccard = np.nan
        if prev_adj is not None and prev_metrics is not None:
            turnover = consecutive_turnover_topk(prev_adj, adj)
            jaccard = jaccard_binary(prev_adj, adj)
            yoy = yoy_change(prev_metrics, metrics)

        # Descriptive sensitivity to the observed territory-pair sample.
        boot = bootstrap_metric(corr, adj)

        # Period classification uses the last observation in the rolling
        # window. Thus the "2020" period is available at eval_year=2021.
        obs_year_for_period = eval_year - 1
        period = classify_period(obs_year_for_period)

        row = {
            "country": country,
            "sector": sector,
            "eval_year": eval_year,
            "observation_year_last": obs_year_for_period,
            "period": period,
            "top_k": k,
            **metrics,
            "turnover": turnover,
            "jaccard_consecutive": jaccard,
            **yoy,
            **boot,
        }
        annual_rows.append(row)
        prev_adj = adj
        prev_metrics = metrics
        prev_corr = corr

    # Period summaries
    period_rows = []
    for p in ["pre-2020", "2020", "post-2020"]:
        ps = period_summary(annual_rows, p)
        ps["country"] = country
        ps["sector"] = sector
        ps["top_k"] = k
        period_rows.append(ps)

    # Period comparisons
    pre_s = [r for r in period_rows if r["period"] == "pre-2020"]
    p2020_s = [r for r in period_rows if r["period"] == "2020"]
    post_s = [r for r in period_rows if r["period"] == "post-2020"]

    comparison_rows = []
    if pre_s and post_s:
        comp = period_comparison(pre_s[0], post_s[0], "post_minus_pre")
        comp["country"] = country
        comp["sector"] = sector
        comp["top_k"] = k
        comparison_rows.append(comp)

    if pre_s and p2020_s:
        comp = period_comparison(pre_s[0], p2020_s[0], "2020_minus_pre")
        comp["country"] = country
        comp["sector"] = sector
        comp["top_k"] = k
        comparison_rows.append(comp)

    return annual_rows, period_rows, comparison_rows


# ---------------------------------------------------------------------------
# Top-k sensitivity
# ---------------------------------------------------------------------------

def topk_sensitivity_row(
    panel: pd.DataFrame,
    country: str,
    sector: str,
    eval_year: int,
    k_list: list[int],
    exclude_years: frozenset[int] = frozenset(),
) -> dict:
    """Compute metrics at different k values for one year."""
    region_ids, growth_years, matrix = build_growth_matrix(panel, country, sector)
    n_regions = len(region_ids)
    wmat = window_matrix(growth_years, matrix, eval_year, WINDOW, exclude_years)
    if wmat.shape[0] < MIN_PERIODS:
        return {"country": country, "sector": sector, "eval_year": eval_year}

    corr = pairwise_corr(wmat, MIN_PERIODS)
    if np.all(np.isnan(corr)):
        return {"country": country, "sector": sector, "eval_year": eval_year}

    row = {"country": country, "sector": sector, "eval_year": eval_year}
    for k in k_list:
        adj = top_k_adjacency(corr, k)
        m = graph_annual_metrics(corr, adj, n_regions)
        row[f"density_k{k}"] = m["density"]
        row[f"mean_weight_k{k}"] = m["mean_weight"]
        row[f"n_edges_k{k}"] = m["n_edges_valid"]
    return row


# ---------------------------------------------------------------------------
# COVID sensitivity: with vs without observation_year=2020
# ---------------------------------------------------------------------------

def build_covid_sensitivity(
    panel: pd.DataFrame,
    country: str,
    sector: str,
    k: int,
) -> list[dict]:
    """Run analysis with and without observation_year=2020.

    Returns rows for both scenarios.
    """
    rows_with, _, _ = build_sector_analysis(
        panel, country, sector, k, exclude_years=frozenset(),
    )
    rows_without, _, _ = build_sector_analysis(
        panel, country, sector, k, exclude_years=frozenset({COVID_OBS_YEAR}),
    )

    results = []
    # Merge by eval_year
    with_by_year = {r["eval_year"]: r for r in rows_with}
    without_by_year = {r["eval_year"]: r for r in rows_without}
    all_years = sorted(set(with_by_year.keys()) | set(without_by_year.keys()))

    for ey in all_years:
        rw = with_by_year.get(ey, {})
        rwo = without_by_year.get(ey, {})
        row = {
            "country": country,
            "sector": sector,
            "eval_year": ey,
            "density_with_2020": rw.get("density", np.nan),
            "density_without_2020": rwo.get("density", np.nan),
            "mean_weight_with_2020": rw.get("mean_weight", np.nan),
            "mean_weight_without_2020": rwo.get("mean_weight", np.nan),
            "mean_abs_weight_with_2020": rw.get("mean_abs_weight", np.nan),
            "mean_abs_weight_without_2020": rwo.get("mean_abs_weight", np.nan),
        }
        for key in ["density", "mean_weight", "mean_abs_weight"]:
            w = rw.get(key, np.nan)
            wo = rwo.get(key, np.nan)
            if np.isfinite(w) and np.isfinite(wo):
                row[f"{key}_delta"] = wo - w
            else:
                row[f"{key}_delta"] = np.nan
        results.append(row)
    return results


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def generate_figures(
    annual_df: pd.DataFrame,
    period_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    out_dir: Path,
) -> list[str]:
    """Generate static publication-quality figures. Returns list of filenames."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    created = []

    countries = sorted(annual_df["country"].unique())
    # Colour-blind-conscious palette derived from Okabe-Ito plus neutral grey.
    sector_colors = {
        "BE": "#0072B2", "FZ": "#E69F00", "GI": "#009E73",
        "JZ": "#D55E00", "KZ": "#CC79A7", "LZ": "#56B4E9",
        "MN": "#F0E442", "OQ": "#666666", "RU": "#000000",
    }
    period_boundary_eval_year = COVID_OBS_YEAR + 1

    for c in countries:
        csub = annual_df[annual_df["country"] == c].copy()
        sectors = sorted(csub["sector"].unique())

        # ── Figure 1: Density temporal line ──
        fig, ax = plt.subplots(figsize=(10, 5))
        for s in sectors:
            ss = csub[csub["sector"] == s].sort_values("eval_year")
            ax.plot(ss["eval_year"], ss["density"], label=s,
                    color=sector_colors.get(s, "gray"), marker="o", markersize=3)
        ax.axvline(
            x=period_boundary_eval_year,
            color="#D55E00",
            linestyle="--",
            alpha=0.7,
            label="rolling window ending in 2020",
        )
        ax.set_xlabel("Evaluation year (graph available for)")
        ax.set_ylabel("Edge density (top-k / possible pairs)")
        ax.set_title(f"{c} — L2 graph density over time (top-k={TOP_K_PRINCIPAL})")
        ax.legend(fontsize=7, ncol=3)
        ax.grid(alpha=0.3)
        fname = f"g2_density_temporal_{c}.png"
        fig.tight_layout()
        fig.savefig(fig_dir / fname, dpi=300)
        plt.close(fig)
        created.append(fname)

        # ── Figure 2: Mean/median weight temporal ──
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for s in sectors:
            ss = csub[csub["sector"] == s].sort_values("eval_year")
            axes[0].plot(ss["eval_year"], ss["mean_weight"], label=s,
                         color=sector_colors.get(s, "gray"), marker="o", markersize=3)
            axes[1].plot(ss["eval_year"], ss["median_weight"], label=s,
                         color=sector_colors.get(s, "gray"), marker="o", markersize=3)
        for ax in axes:
            ax.axvline(
                x=period_boundary_eval_year,
                color="#D55E00",
                linestyle="--",
                alpha=0.7,
            )
            ax.grid(alpha=0.3)
        axes[0].set_title(f"{c} — Mean weight")
        axes[1].set_title(f"{c} — Median weight")
        axes[0].set_ylabel("Weight (Pearson correlation)")
        axes[0].set_xlabel("Evaluation year")
        axes[1].set_xlabel("Evaluation year")
        axes[0].legend(fontsize=6, ncol=3)
        fname = f"g2_weight_temporal_{c}.png"
        fig.tight_layout()
        fig.savefig(fig_dir / fname, dpi=300)
        plt.close(fig)
        created.append(fname)

        # ── Figure 3: Heatmap sector × year ──
        pivot = csub.pivot_table(
            index="sector", columns="eval_year", values="mean_weight", aggfunc="first",
        )
        fig, ax = plt.subplots(figsize=(12, 4))
        im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlBu_r", interpolation="nearest")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, fontsize=7)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=8)
        ax.set_title(f"{c} — Mean weight by sector × year (top-k={TOP_K_PRINCIPAL})")
        fig.colorbar(im, ax=ax, label="Mean weight (Pearson)")
        fname = f"g2_heatmap_{c}.png"
        fig.tight_layout()
        fig.savefig(fig_dir / fname, dpi=300)
        plt.close(fig)
        created.append(fname)

        # ── Figure 4: Post - Pre difference by sector ──
        comp_c = comparison_df[
            (comparison_df["country"] == c)
            & (comparison_df["comparison"] == "post_minus_pre")
        ]
        if not comp_c.empty:
            fig, ax = plt.subplots(figsize=(8, 4))
            x_sectors = comp_c["sector"].tolist()
            diff_vals = comp_c["mean_weight_diff"].tolist()
            colors = ["#0072B2" if v > 0 else "#E69F00" for v in diff_vals]
            bars = ax.bar(
                x_sectors,
                diff_vals,
                color=colors,
                edgecolor="black",
                linewidth=0.5,
            )
            for bar, value in zip(bars, diff_vals):
                if value <= 0:
                    bar.set_hatch("//")
            ax.axhline(y=0, color="black", linewidth=0.5)
            ax.set_ylabel("Δ mean weight (post − pre)")
            ax.set_title(f"{c} — Post-2020 vs Pre-2020 mean weight change")
            ax.grid(alpha=0.3, axis="y")
            fname = f"g2_post_minus_pre_{c}.png"
            fig.tight_layout()
            fig.savefig(fig_dir / fname, dpi=300)
            plt.close(fig)
            created.append(fname)

        # ── Figure 5: Turnover/Jaccard temporal ──
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for s in sectors:
            ss = csub[csub["sector"] == s].sort_values("eval_year")
            valid = ss[ss["turnover"].notna()]
            axes[0].plot(valid["eval_year"], valid["turnover"], label=s,
                         color=sector_colors.get(s, "gray"), marker="o", markersize=3)
            valid2 = ss[ss["jaccard_consecutive"].notna()]
            axes[1].plot(valid2["eval_year"], valid2["jaccard_consecutive"], label=s,
                         color=sector_colors.get(s, "gray"), marker="o", markersize=3)
        for ax in axes:
            ax.axvline(
                x=period_boundary_eval_year,
                color="#D55E00",
                linestyle="--",
                alpha=0.7,
            )
            ax.grid(alpha=0.3)
        axes[0].set_title(f"{c} — Annual turnover (1 - Jaccard)")
        axes[0].set_ylabel("Turnover")
        axes[1].set_title(f"{c} — Consecutive Jaccard")
        axes[1].set_ylabel("Jaccard")
        axes[0].set_xlabel("Evaluation year")
        axes[1].set_xlabel("Evaluation year")
        axes[0].legend(fontsize=6, ncol=3)
        fname = f"g2_turnover_jaccard_{c}.png"
        fig.tight_layout()
        fig.savefig(fig_dir / fname, dpi=300)
        plt.close(fig)
        created.append(fname)

    # ── Figure 6: Comparative panel with the window ending in 2020 marked ──
    fig, axes = plt.subplots(len(countries), 2, figsize=(14, 4 * len(countries)),
                             squeeze=False)
    for ci, c in enumerate(countries):
        csub = annual_df[annual_df["country"] == c].copy()
        sectors = sorted(csub["sector"].unique())
        for s in sectors:
            ss = csub[csub["sector"] == s].sort_values("eval_year")
            axes[ci, 0].plot(ss["eval_year"], ss["density"], label=s,
                             color=sector_colors.get(s, "gray"), marker=".", markersize=2)
            axes[ci, 1].plot(ss["eval_year"], ss["mean_weight"], label=s,
                             color=sector_colors.get(s, "gray"), marker=".", markersize=2)
        for j in range(2):
            axes[ci, j].axvline(
                x=period_boundary_eval_year,
                color="#D55E00",
                linestyle="--",
                alpha=0.7,
            )
            axes[ci, j].grid(alpha=0.3)
        axes[ci, 0].set_ylabel(f"{c}\nDensity")
        axes[ci, 1].set_ylabel(f"{c}\nMean weight")
        if ci == 0:
            axes[ci, 0].set_title("Edge density")
            axes[ci, 1].set_title("Mean weight")
            axes[ci, 1].legend(fontsize=5, ncol=3, loc="upper right")
    axes[-1, 0].set_xlabel("Evaluation year")
    axes[-1, 1].set_xlabel("Evaluation year")
    fig.suptitle("L2 graph aggregate dynamics — rolling window ending in 2020 marked",
                 fontsize=12, y=1.01)
    fname = "g2_comparative_panel.png"
    fig.tight_layout()
    fig.savefig(fig_dir / fname, dpi=300, bbox_inches="tight")
    plt.close(fig)
    created.append(fname)

    return created


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BASE), stderr=subprocess.DEVNULL,
        ).decode().strip()[:12]
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_aggregate_dynamics(
    panel_path: Path = DEFAULT_PANEL,
    out_dir: Path = OUT_DIR,
    top_k: int = TOP_K_PRINCIPAL,
    top_k_variants: list[int] | None = None,
    generate_figs: bool = True,
    verbose: bool = True,
) -> dict:
    """Run the complete G2 aggregate dynamics analysis.

    Produces:
      - g2_annual_metrics.csv  (country × sector × eval_year)
      - g2_period_metrics.csv  (country × sector × period)
      - g2_period_comparisons.csv  (country × sector × comparison)
      - g2_topk_sensitivity.csv  (country × sector × eval_year × k)
      - g2_covid_sensitivity.csv  (country × sector × eval_year)
      - g2_dynamics_summary.json
      - g2_dynamics_manifest.json
      - figures/ (if generate_figs)
    """
    if top_k_variants is None:
        top_k_variants = TOP_K_VARIANTS

    panel = pd.read_csv(panel_path, low_memory=False)
    countries = sorted(panel["country"].unique())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_checksum = file_checksum(panel_path)

    all_annual: list[dict] = []
    all_period: list[dict] = []
    all_comparison: list[dict] = []
    all_topk: list[dict] = []
    all_covid: list[dict] = []

    country_summaries = {}

    for country in countries:
        sectors = eligible_sectors(panel, country)
        if verbose:
            print(f"\n=== {country} ({len(sectors)} sectors) ===")

        country_annual = []
        country_period = []
        country_comp = []

        for sector in sectors:
            if verbose:
                print(f"  {sector}...", end="", flush=True)

            # Main analysis (exclude_years=empty for main scenario)
            annual, periods, comps = build_sector_analysis(
                panel, country, sector, top_k,
                exclude_years=frozenset(),
            )
            country_annual.extend(annual)
            country_period.extend(periods)
            country_comp.extend(comps)

            # Top-k sensitivity for sampled eval years
            region_ids, growth_years, matrix = build_growth_matrix(panel, country, sector)
            first_eval = growth_years[0] + WINDOW
            last_eval = growth_years[-1] + 1
            eval_years = list(range(first_eval, last_eval + 1))
            for ey in eval_years:
                tk_row = topk_sensitivity_row(
                    panel, country, sector, ey, top_k_variants,
                )
                all_topk.append(tk_row)

            # COVID sensitivity
            covid_rows = build_covid_sensitivity(panel, country, sector, top_k)
            all_covid.extend(covid_rows)

            if verbose:
                print(" done")

        all_annual.extend(country_annual)
        all_period.extend(country_period)
        all_comparison.extend(country_comp)

        # Country summary
        cs = pd.DataFrame(country_annual)
        pre = cs[cs["period"] == "pre-2020"]
        post = cs[cs["period"] == "post-2020"]
        country_summaries[country] = {
            "n_sectors": len(sectors),
            "sectors": sectors,
            "n_eval_years": len(cs["eval_year"].unique()),
            "eval_year_range": [int(cs["eval_year"].min()), int(cs["eval_year"].max())] if len(cs) > 0 else [],
            "mean_density_overall": float(cs["density"].mean()) if len(cs) > 0 else np.nan,
            "mean_weight_overall": float(cs["mean_weight"].mean()) if len(cs) > 0 else np.nan,
            "mean_turnover_overall": float(cs["turnover"].dropna().mean()) if cs["turnover"].notna().any() else np.nan,
            "mean_density_pre": float(pre["density"].mean()) if len(pre) > 0 else np.nan,
            "mean_density_post": float(post["density"].mean()) if len(post) > 0 else np.nan,
            "mean_weight_pre": float(pre["mean_weight"].mean()) if len(pre) > 0 else np.nan,
            "mean_weight_post": float(post["mean_weight"].mean()) if len(post) > 0 else np.nan,
        }

    # Save artifacts
    df_annual = pd.DataFrame(all_annual)
    df_period = pd.DataFrame(all_period)
    df_comparison = pd.DataFrame(all_comparison)
    df_topk = pd.DataFrame(all_topk)
    df_covid = pd.DataFrame(all_covid)

    df_annual.to_csv(out_dir / "g2_annual_metrics.csv", index=False)
    df_period.to_csv(out_dir / "g2_period_metrics.csv", index=False)
    df_comparison.to_csv(out_dir / "g2_period_comparisons.csv", index=False)
    df_topk.to_csv(out_dir / "g2_topk_sensitivity.csv", index=False)
    df_covid.to_csv(out_dir / "g2_covid_sensitivity.csv", index=False)

    # Figures
    fig_files = []
    if generate_figs:
        fig_files = generate_figures(df_annual, df_period, df_comparison, out_dir)
        expected_figures = len(countries) * 5 + 1
        if len(fig_files) != expected_figures:
            raise RuntimeError(
                f"Expected {expected_figures} figures, generated {len(fig_files)}"
            )
        if verbose:
            print(f"\nFigures generated: {len(fig_files)}")

    # Summary
    summary = {
        "protocol": "G2 Aggregate Dynamics — descriptive characterization of L2 temporal graph",
        "source_panel": str(panel_path.relative_to(BASE) if str(panel_path).startswith(str(BASE)) else panel_path),
        "source_checksum_sha256_16": source_checksum,
        "generated_from_commit": get_git_commit(),
        "parameters": {
            "window": WINDOW,
            "min_periods": MIN_PERIODS,
            "top_k_principal": top_k,
            "top_k_variants": top_k_variants,
            "near_zero_threshold": NEAR_ZERO_THRESHOLD,
            "pair_resample_n": N_BOOTSTRAP,
            "pair_resample_frac": BOOTSTRAP_FRAC,
            "pair_resample_seed": BOOTSTRAP_SEED,
            "pair_resample_interpretation": (
                "descriptive sensitivity interval; territory pairs share nodes "
                "and are not independent"
            ),
            "period_definition": (
                "period is classified by the last observation year in the "
                "rolling window; observation_year_last=2020 maps to eval_year=2021"
            ),
            "top_k_edge_sign": "positive correlations only",
        },
        "countries": country_summaries,
        "scope_constraints": {
            "edges_are": "statistical co-movement associations, not causality",
            "individual_edges_stable": False,
            "communities_validated": False,
            "forecast_utility": "NOT_SUPPORTED (DEC-023)",
            "cross_country_pooling": "PROHIBITED",
            "fr_aggregate_signal": "COVID_ROBUST",
            "nl_aggregate_signal": "COVID_SENSITIVE",
            "pt_aggregate_signal": "COVID_SENSITIVE",
            "cross_country_replication": "NOT_SUPPORTED (gate passes with different countries)",
        },
        "n_annual_rows": len(df_annual),
        "n_period_rows": len(df_period),
        "n_comparison_rows": len(df_comparison),
        "n_topk_rows": len(df_topk),
        "n_covid_rows": len(df_covid),
        "figures": fig_files,
    }

    with open(out_dir / "g2_dynamics_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Manifest
    manifest = {
        "builder": "src/data/european_panel/build_g2_aggregate_dynamics.py",
        "source": str(panel_path.relative_to(BASE) if str(panel_path).startswith(str(BASE)) else panel_path),
        "source_checksum": source_checksum,
        "generated_from_commit": get_git_commit(),
        "artifacts": {},
    }
    for p in sorted(out_dir.glob("g2_*")):
        if p.is_file():
            manifest["artifacts"][p.name] = {
                "size_bytes": p.stat().st_size,
                "checksum_sha256_16": file_checksum(p),
            }
    for p in sorted((out_dir / "figures").glob("*.png")) if (out_dir / "figures").exists() else []:
        manifest["artifacts"][f"figures/{p.name}"] = {
            "size_bytes": p.stat().st_size,
            "checksum_sha256_16": file_checksum(p),
        }
    with open(out_dir / "g2_dynamics_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    if verbose:
        print(f"\nAll artifacts saved to {out_dir}")
        print(f"Annual rows: {len(df_annual)}")
        print(f"Period rows: {len(df_period)}")
        print(f"Comparison rows: {len(df_comparison)}")

    return summary


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="G2 Aggregate Dynamics — L2 co-growth graph temporal characterization"
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--top-k", type=int, default=TOP_K_PRINCIPAL)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    run_aggregate_dynamics(
        panel_path=args.panel,
        out_dir=args.out_dir,
        top_k=args.top_k,
        generate_figs=not args.no_figures,
    )


if __name__ == "__main__":
    main()
