"""G2 Corrected Controls: temporal dynamics of L2 co-growth graph.

DEC-024c. Replaces superseded control in commit cc48924.

The superseded control (cc48924) permuted pre-computed Pearson correlation weights
from g1_l2_edges.csv (territory-pair rows of matrix W). This is invalid: permuting
already-computed edge weights does not produce a valid null for the hypothesis
"does temporal ordering of source growth series matter?". The p=0.005 / 26/26
results from that run must not be used as evidence.

This module starts from sector_panel_fr_nl_pt.csv and rebuilds the full pipeline
(rolling windows -> pairwise Pearson -> top-k -> adjacency) for each permutation.

Metrics
-------
M1 - Consecutive temporal Jaccard: mean/median/min J(G_t, G_{t+1})
M2 - Mean pairwise temporal Jaccard: mean J over ALL (t,s) year pairs (t != s)
     (previously mislabeled "LOYO Jaccard" — NOT leave-one-year-out)
M3 - True LOYO reconstruction: remove obs_year y, rebuild affected windows, compare
     to original adjacency. Observed values only. NULL DISTRIBUTION: BLOCKED
     (computational cost: 199 perms x n_obs_years x n_affected_evals x full pipeline).

Null families
-------------
N1 - Temporal: permute observation_year within each territory x sector column.
     Tests: does temporal ordering of growth rates matter?
     Implementation: permute_growth_temporal (from build_g1_l2_cogrowth.py).
N2 - Territory row-wise: within each observation_year, permute which territory gets
     which growth value. Tests: does specific territory co-movement identity matter?
     Implementation: permute_growth_territory (from build_g1_l2_cogrowth.py, row-wise).

DEGENERACY FINDING (column permutation):
     Column permutation of the growth matrix (permute_growth_territory_cols) applies
     a uniform column shuffle across all observation_years. For M1/M2 Jaccard metrics,
     this is mathematically equivalent to relabeling territory nodes in the resulting
     adjacency: the Jaccard between any two yearly graphs is invariant to spatial
     relabeling. Result: null variance = 0.0, p = 1.0 always, no test possible.
     Column permutation is kept in this module for documentation purposes only.
     The gate uses N2 row-wise (within each year) as the territory null.

Gate (pre-registered, DEC-024c)
---------------------------------
G2_AGGREGATE_TEMPORAL_SIGNAL: N1+N2(row) FDR-sig (BH q=0.05) for M1 or M2.
  Positive effect required (obs > null median).
  Per country: >= 50% eligible sectors pass. Global: >= 2/3 countries.
G2_EDGE_STABILITY: M2 >= 0.70 (observed; no permutation required).
  Per country: >= 50% eligible sectors pass. Global: >= 2/3 countries.

COVID protocol
--------------
observation_year=2020 excluded from rolling windows (exclude_years frozenset{2020}).
eval_year=2020 is retained; its window covers [2015-2019] (no 2020 observations).
eval_year=2021 window: [2016-2020] minus {2020} = [2016-2019] (4 years, >= MIN_PERIODS).

PT KZ: structurally absent (DEC-018); excluded via mask_sector_supported=0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
OUT_DIR = BASE / "data/processed/economic_graph/g2_preflight"

_BUILDER_DIR = str(Path(__file__).parent)
if _BUILDER_DIR not in sys.path:
    sys.path.insert(0, _BUILDER_DIR)

from build_g1_l2_cogrowth import (  # noqa: E402
    build_growth_matrix,
    window_matrix,
    pairwise_corr,
    window_years_used,
    eval_years_for_country,
    eligible_sectors,
    empirical_p,
    bh_fdr,
    permute_growth_temporal,
    permute_growth_territory,  # row-wise: used as N2
)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

TOP_K_PRINCIPAL = 5
TOP_K_VARIANTS = [3, 5, 10]
WINDOW = 5
MIN_PERIODS = 4
COVID_YEAR = 2020
COVID_EXCLUDE: frozenset[int] = frozenset({COVID_YEAR})
N_PERMUTATIONS = 199
FDR_Q = 0.05
SEED_N1 = 42
SEED_N2 = 137
COUNTRIES_NEEDED = 2
SECTOR_FRAC_NEEDED = 0.50
M2_STABILITY_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Top-k adjacency from correlation matrix
# ---------------------------------------------------------------------------

def top_k_adjacency(corr: np.ndarray, k: int) -> np.ndarray:
    """Binary symmetric top-k adjacency (positive correlations only).

    Uses argpartition for efficiency. Sets diagonal to -inf before ranking so
    self-edges are never selected. Only positive correlations become edges.
    Returns bool array of shape (n, n).
    """
    n = corr.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=bool)
    corr_nd = corr.copy().astype(float)
    np.fill_diagonal(corr_nd, -np.inf)
    k_c = min(k, n - 1)
    top_idx = np.argpartition(corr_nd, -k_c, axis=1)[:, -k_c:]
    row_idx = np.repeat(np.arange(n), k_c)
    col_idx = top_idx.ravel()
    vals = corr[row_idx, col_idx]
    pos = vals > 0
    adj = np.zeros((n, n), dtype=bool)
    adj[row_idx[pos], col_idx[pos]] = True
    return adj | adj.T


# ---------------------------------------------------------------------------
# Permutation functions
# ---------------------------------------------------------------------------

def permute_growth_territory_cols(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    rng: np.random.Generator,
) -> dict[str, tuple[list[str], list[int], np.ndarray]]:
    """Column permutation: shuffle entire territory time series within country x sector.

    Permutes the columns (territory axis) of each sector's growth matrix.
    The same permutation applies to all years in the matrix, so each territory's
    own temporal trajectory is preserved but assigned to a different spatial label.
    This differs from graph relabeling because it is applied to the source series
    before correlation computation, preserving NaN mask heterogeneity effects.
    """
    result = {}
    for sector, (region_ids, growth_years, matrix) in sector_data.items():
        perm_cols = rng.permutation(matrix.shape[1])
        result[sector] = (region_ids, growth_years, matrix[:, perm_cols])
    return result


# ---------------------------------------------------------------------------
# Build adjacency time series for one sector
# ---------------------------------------------------------------------------

def build_adjs_for_sector(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sector: str,
    eval_years: list[int],
    k: int,
    exclude_years: frozenset[int] = COVID_EXCLUDE,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
) -> list[np.ndarray | None]:
    """Build list of top-k binary adjacency matrices for each eval_year.

    Returns None for eval_years where the window has fewer than min_periods rows.
    """
    region_ids, growth_years, matrix = sector_data[sector]
    adjs = []
    for t in eval_years:
        wmat = window_matrix(growth_years, matrix, t, window, exclude_years)
        if wmat.shape[0] < min_periods:
            adjs.append(None)
            continue
        corr = pairwise_corr(wmat, min_periods)
        if np.all(np.isnan(corr)):
            adjs.append(None)
            continue
        adjs.append(top_k_adjacency(corr, k))
    return adjs


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def jaccard_binary(a1: np.ndarray, a2: np.ndarray) -> float:
    """Jaccard similarity of upper triangles of two boolean adjacency matrices."""
    b1 = np.triu(a1.astype(bool), k=1).ravel()
    b2 = np.triu(a2.astype(bool), k=1).ravel()
    inter = int((b1 & b2).sum())
    union = int((b1 | b2).sum())
    return float(inter / union) if union > 0 else np.nan


def m1_consecutive_jaccard(adjs: list[np.ndarray | None]) -> dict:
    """M1: consecutive temporal Jaccard J(G_t, G_{t+1}).

    Reports mean, median, min over all valid consecutive year pairs.
    """
    values = []
    for i in range(len(adjs) - 1):
        if adjs[i] is not None and adjs[i + 1] is not None:
            v = jaccard_binary(adjs[i], adjs[i + 1])
            if np.isfinite(v):
                values.append(v)
    if not values:
        return {"m1_mean": np.nan, "m1_median": np.nan, "m1_min": np.nan, "m1_n_pairs": 0}
    return {
        "m1_mean": float(np.mean(values)),
        "m1_median": float(np.median(values)),
        "m1_min": float(np.min(values)),
        "m1_n_pairs": len(values),
    }


def m2_mean_pairwise_jaccard(adjs: list[np.ndarray | None]) -> dict:
    """M2: mean pairwise temporal Jaccard over ALL (t,s) year pairs (t != s).

    This was previously mislabeled 'LOYO Jaccard'. It is NOT leave-one-year-out.
    """
    valid = [a for a in adjs if a is not None]
    values = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            v = jaccard_binary(valid[i], valid[j])
            if np.isfinite(v):
                values.append(v)
    if not values:
        return {"m2_mean": np.nan, "m2_n_pairs": 0}
    return {
        "m2_mean": float(np.mean(values)),
        "m2_n_pairs": len(values),
    }


def m3_loyo_reconstruction(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sector: str,
    eval_years: list[int],
    k: int,
    observed_adjs: list[np.ndarray | None],
    exclude_years: frozenset[int] = COVID_EXCLUDE,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
) -> dict:
    """M3: true LOYO reconstruction stability.

    For each observation year y (not already excluded), removes y from the growth
    matrix (set column values for row y to NaN), rebuilds all affected eval_year
    windows, and computes Jaccard between the LOYO adjacency and the original.

    Reports mean loyo_reconstruction_jaccard over all (y, eval_year) combinations
    where both original and loyo adjacencies are valid.

    NULL DISTRIBUTION: BLOCKED — cost is 199 perms x n_obs_years x n_affected_evals
    x full pipeline per permutation, which would take hours for FR (280 regions,
    9 sectors). Only observed values are computed here.
    """
    region_ids, growth_years, matrix = sector_data[sector]
    eval_year_to_idx = {t: i for i, t in enumerate(eval_years)}
    jaccard_vals = []
    n_comparisons = 0

    all_obs_years = [y for y in growth_years if y not in exclude_years]

    for y in all_obs_years:
        affected = [
            t for t in eval_years
            if y in window_years_used(growth_years, t, window, exclude_years)
        ]
        if not affected:
            continue

        exclude_with_y = exclude_years | frozenset({y})
        loyo_adjs = build_adjs_for_sector(
            sector_data, sector, affected, k, exclude_with_y, window, min_periods,
        )

        for t_i, t in enumerate(affected):
            orig_idx = eval_year_to_idx.get(t)
            if orig_idx is None:
                continue
            if observed_adjs[orig_idx] is None or loyo_adjs[t_i] is None:
                continue
            j = jaccard_binary(observed_adjs[orig_idx], loyo_adjs[t_i])
            if np.isfinite(j):
                jaccard_vals.append(j)
                n_comparisons += 1

    if not jaccard_vals:
        return {
            "m3_loyo_reconstruction_jaccard_mean": np.nan,
            "m3_n_loyo_comparisons": 0,
            "m3_null": "BLOCKED",
        }
    return {
        "m3_loyo_reconstruction_jaccard_mean": float(np.mean(jaccard_vals)),
        "m3_n_loyo_comparisons": n_comparisons,
        "m3_null": "BLOCKED",
    }


# ---------------------------------------------------------------------------
# Null family runner
# ---------------------------------------------------------------------------

def run_null_family(
    sector_data: dict,
    sectors: list[str],
    eval_years: list[int],
    k: int,
    permute_fn,
    n_permutations: int,
    seed: int,
    exclude_years: frozenset[int] = COVID_EXCLUDE,
) -> dict[str, dict[str, list[float]]]:
    """Run n_permutations permutations; return M1/M2 null distributions per sector."""
    rng = np.random.default_rng(seed)
    null_dists: dict[str, dict[str, list[float]]] = {
        s: {"m1_mean": [], "m2_mean": []} for s in sectors
    }
    for _ in range(n_permutations):
        psd = permute_fn(sector_data, rng)
        for s in sectors:
            adjs = build_adjs_for_sector(psd, s, eval_years, k, exclude_years)
            null_dists[s]["m1_mean"].append(m1_consecutive_jaccard(adjs)["m1_mean"])
            null_dists[s]["m2_mean"].append(m2_mean_pairwise_jaccard(adjs)["m2_mean"])
    return null_dists


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

def _bh_reject(pvalues: list[float], q: float = FDR_Q) -> list[bool]:
    """BH/FDR correction. Returns boolean reject list."""
    adj = bh_fdr(pvalues)
    return [float(a) <= q for a in adj]


def compute_signal_gate_country(
    obs: dict[str, dict],
    n1_dists: dict[str, dict[str, list]],
    n2_dists: dict[str, dict[str, list]],
    sectors: list[str],
    fdr_q: float = FDR_Q,
    sector_frac: float = SECTOR_FRAC_NEEDED,
) -> dict:
    """G2_AGGREGATE_TEMPORAL_SIGNAL gate for one country.

    Families: M1xN1, M1xN2, M2xN1, M2xN2. BH/FDR per family over all sectors.
    Sector passes if (M1 sig+pos under N1 AND N2) OR (M2 sig+pos under N1 AND N2).
    Country passes if >= sector_frac of eligible sectors pass.
    """
    metrics_nulls = [
        ("m1_mean", "n1"), ("m1_mean", "n2"),
        ("m2_mean", "n1"), ("m2_mean", "n2"),
    ]

    raw_p: dict[str, dict] = {s: {} for s in sectors}
    for metric, null_lbl in metrics_nulls:
        dists = n1_dists if null_lbl == "n1" else n2_dists
        pvals = [empirical_p(obs[s][metric], dists[s][metric]) for s in sectors]
        qvals = bh_fdr(pvals)
        rejects = [float(qv) <= fdr_q for qv in qvals]
        for i, s in enumerate(sectors):
            raw_p[s][f"{metric}_{null_lbl}_p"] = pvals[i]
            raw_p[s][f"{metric}_{null_lbl}_q"] = float(qvals[i])
            raw_p[s][f"{metric}_{null_lbl}_reject"] = rejects[i]
            null_arr = np.array([v for v in dists[s][metric] if np.isfinite(v)])
            raw_p[s][f"{metric}_{null_lbl}_pos"] = bool(
                np.isfinite(obs[s][metric]) and len(null_arr) > 0
                and obs[s][metric] > float(np.median(null_arr))
            )

    sector_pass = {}
    for s in sectors:
        m1_ok = (
            raw_p[s]["m1_mean_n1_reject"] and raw_p[s]["m1_mean_n1_pos"]
            and raw_p[s]["m1_mean_n2_reject"] and raw_p[s]["m1_mean_n2_pos"]
        )
        m2_ok = (
            raw_p[s]["m2_mean_n1_reject"] and raw_p[s]["m2_mean_n1_pos"]
            and raw_p[s]["m2_mean_n2_reject"] and raw_p[s]["m2_mean_n2_pos"]
        )
        sector_pass[s] = bool(m1_ok or m2_ok)

    n_pass = sum(sector_pass.values())
    n_elig = len(sectors)
    country_pass = (n_pass / n_elig) >= sector_frac if n_elig > 0 else False

    return {
        "sector_pass": sector_pass,
        "n_pass": n_pass,
        "n_eligible": n_elig,
        "country_pass": country_pass,
        "sector_frac_pass": n_pass / n_elig if n_elig > 0 else 0.0,
        "per_sector_detail": {s: raw_p[s] for s in sectors},
    }


def compute_stability_gate_country(
    obs: dict[str, dict],
    sectors: list[str],
    threshold: float = M2_STABILITY_THRESHOLD,
    sector_frac: float = SECTOR_FRAC_NEEDED,
) -> dict:
    """G2_EDGE_STABILITY gate: M2 >= threshold for >= sector_frac of eligible sectors."""
    sector_pass = {
        s: bool(np.isfinite(obs[s]["m2_mean"]) and obs[s]["m2_mean"] >= threshold)
        for s in sectors
    }
    n_pass = sum(sector_pass.values())
    n_elig = len(sectors)
    return {
        "sector_pass": sector_pass,
        "n_pass": n_pass,
        "n_eligible": n_elig,
        "country_pass": (n_pass / n_elig) >= sector_frac if n_elig > 0 else False,
        "threshold": threshold,
    }


# ---------------------------------------------------------------------------
# Floor-p diagnostics
# ---------------------------------------------------------------------------

def floor_p_diagnostics(
    obs_sector: dict,
    n1_dists: dict[str, list],
    n2_dists: dict[str, list],
) -> dict:
    """Summary stats for null distributions to detect degenerate cases."""
    diag = {}
    for metric in ["m1_mean", "m2_mean"]:
        for lbl, dists in [("n1", n1_dists), ("n2", n2_dists)]:
            arr = np.array([v for v in dists[metric] if np.isfinite(v)])
            key = f"{metric}_{lbl}"
            if len(arr) == 0:
                diag[key] = {"n_finite": 0}
                continue
            diag[key] = {
                "obs": float(obs_sector[metric]),
                "null_mean": float(np.mean(arr)),
                "null_std": float(np.std(arr)),
                "null_min": float(np.min(arr)),
                "null_max": float(np.max(arr)),
                "n_finite": int(len(arr)),
                "n_unique": int(len(np.unique(arr.round(8)))),
                "obs_above_all_null": bool(
                    np.isfinite(obs_sector[metric]) and obs_sector[metric] > arr.max()
                ),
            }
    return diag


# ---------------------------------------------------------------------------
# Reconciliation table: G1-L2 0.78 vs G2 M2 0.07-0.26
# ---------------------------------------------------------------------------

RECONCILIATION_G1_VS_G2 = {
    "note": (
        "G1-L2 0.78 and G2 M2 0.07-0.26 measure different aspects of the same graph. "
        "Both are correct. They are NOT contradictory."
    ),
    "table": [
        {
            "result": "G1-L2",
            "object": "Dense Pearson matrix of ALL region-pair correlations",
            "metric": "Pearson of consecutive dense upper-triangle weight vectors",
            "sparsification": "None (all pairs including negative)",
            "granularity": "Per country (all sectors concatenated)",
            "values": {"FR": 0.782, "NL": 0.789, "PT": 0.778},
            "interpretation": "Full correlation STRUCTURE is stable year-to-year (0.78)",
        },
        {
            "result": "G2 M2",
            "object": "Binary top-k=5 adjacency matrix per country x sector",
            "metric": "Mean Jaccard over ALL year pairs (M2)",
            "sparsification": "Top-k=5 (only top 5 connections per region retained)",
            "granularity": "Per country x sector",
            "values_range": "FR ~0.07, NL ~0.17, PT ~0.26 (sector-dependent)",
            "interpretation": (
                "Specific top-5 CONNECTIONS are volatile. "
                "With FR=280 regions, many candidates compete for 5 slots; "
                "small rank changes in correlation rotate top-5 set."
            ),
        },
    ],
    "compatible_finding": (
        "Full Pearson correlation structure is smooth and stable (0.78), "
        "while the specific identity of top-5 connections is volatile (0.07-0.26). "
        "These measure different things: aggregate co-movement vs extreme-edge identity."
    ),
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_corrected_controls(
    panel_path: Path = DEFAULT_PANEL,
    out_dir: Path = OUT_DIR,
    n_permutations: int = N_PERMUTATIONS,
    top_k_list: list[int] | None = None,
    seed_n1: int = SEED_N1,
    seed_n2: int = SEED_N2,
    exclude_years: frozenset[int] = COVID_EXCLUDE,
    scenario: str = "exclude_observation_2020",
    verbose: bool = True,
) -> dict:
    """Run corrected G2 temporal controls. Returns summary dict."""
    if top_k_list is None:
        top_k_list = TOP_K_VARIANTS

    panel = pd.read_csv(panel_path, low_memory=False)
    countries = sorted(panel["country"].unique())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_main: list[dict] = []
    rows_sensitivity: list[dict] = []
    rows_m3: list[dict] = []

    signal_gate_per_country: dict[str, bool] = {}
    stability_gate_per_country: dict[str, bool] = {}
    floor_p_all: dict = {}

    for country in countries:
        if verbose:
            print(f"\n=== {country} ===")

        sectors = eligible_sectors(panel, country)
        sector_data: dict[str, tuple] = {
            s: build_growth_matrix(panel, country, s) for s in sectors
        }
        eval_years = eval_years_for_country(sector_data, sectors)

        if verbose:
            print(f"  Sectors: {sectors}")
            print(f"  Eval years: {eval_years[0]}-{eval_years[-1]} ({len(eval_years)})")

        exclude = exclude_years

        # Observed metrics for all k variants (k=principal needed for nulls)
        obs_by_k: dict[int, dict[str, dict]] = {}
        for k in top_k_list:
            obs_by_k[k] = {}
            for s in sectors:
                adjs = build_adjs_for_sector(sector_data, s, eval_years, k, exclude)
                obs_by_k[k][s] = {
                    **m1_consecutive_jaccard(adjs),
                    **m2_mean_pairwise_jaccard(adjs),
                }

        obs_principal = obs_by_k[TOP_K_PRINCIPAL]

        # M3 LOYO reconstruction (observed only, null BLOCKED)
        for s in sectors:
            adjs_obs = build_adjs_for_sector(
                sector_data, s, eval_years, TOP_K_PRINCIPAL, exclude
            )
            m3 = m3_loyo_reconstruction(
                sector_data, s, eval_years, TOP_K_PRINCIPAL, adjs_obs, exclude,
            )
            rows_m3.append({"country": country, "sector": s, **m3})

        # N1: temporal permutation (permute obs_year within territory x sector)
        if verbose:
            print(f"  N1: {n_permutations} temporal permutations...")
        n1_dists = run_null_family(
            sector_data, sectors, eval_years, TOP_K_PRINCIPAL,
            permute_growth_temporal, n_permutations, seed_n1, exclude,
        )

        # N2: territory row-wise permutation (within each year, shuffle growth values)
        # NOTE: column permutation (permute_growth_territory_cols) was tested and found
        # DEGENERATE for M1/M2 Jaccard: null variance=0, p=1.0 always (mathematically
        # equivalent to graph relabeling when NaN patterns are uniform). Row-wise
        # permutation (within each year) provides a non-trivial territory null.
        if verbose:
            print(f"  N2 (row-wise territory): {n_permutations} permutations...")
        n2_dists = run_null_family(
            sector_data, sectors, eval_years, TOP_K_PRINCIPAL,
            permute_growth_territory, n_permutations, seed_n2, exclude,
        )

        # Gate decisions
        sig_gate = compute_signal_gate_country(
            obs_principal, n1_dists, n2_dists, sectors
        )
        stab_gate = compute_stability_gate_country(obs_principal, sectors)

        signal_gate_per_country[country] = sig_gate["country_pass"]
        stability_gate_per_country[country] = stab_gate["country_pass"]

        if verbose:
            s_lbl = "PASS" if sig_gate["country_pass"] else "FAIL"
            t_lbl = "PASS" if stab_gate["country_pass"] else "FAIL"
            print(
                f"  Signal gate: {sig_gate['n_pass']}/{sig_gate['n_eligible']} sectors -> {s_lbl}"
            )
            print(
                f"  Stability gate: {stab_gate['n_pass']}/{stab_gate['n_eligible']} "
                f"sectors M2>={M2_STABILITY_THRESHOLD} -> {t_lbl}"
            )

        # Floor-p diagnostics per sector
        floor_p_all[country] = {
            s: floor_p_diagnostics(obs_principal[s], n1_dists[s], n2_dists[s])
            for s in sectors
        }

        # Build main result rows (principal k)
        for s in sectors:
            obs_s = obs_principal[s]
            n1_m1 = [v for v in n1_dists[s]["m1_mean"] if np.isfinite(v)]
            n1_m2 = [v for v in n1_dists[s]["m2_mean"] if np.isfinite(v)]
            n2_m1 = [v for v in n2_dists[s]["m1_mean"] if np.isfinite(v)]
            n2_m2 = [v for v in n2_dists[s]["m2_mean"] if np.isfinite(v)]
            rows_main.append({
                "country": country,
                "sector": s,
                "scenario": scenario,
                "top_k": TOP_K_PRINCIPAL,
                "m1_obs_mean": obs_s["m1_mean"],
                "m1_obs_median": obs_s["m1_median"],
                "m1_obs_min": obs_s["m1_min"],
                "m1_n_pairs": obs_s["m1_n_pairs"],
                "m2_obs_mean": obs_s["m2_mean"],
                "m2_n_pairs": obs_s["m2_n_pairs"],
                "m1_null_n1_mean": float(np.mean(n1_m1)) if n1_m1 else np.nan,
                "m1_null_n2_mean": float(np.mean(n2_m1)) if n2_m1 else np.nan,
                "m2_null_n1_mean": float(np.mean(n1_m2)) if n1_m2 else np.nan,
                "m2_null_n2_mean": float(np.mean(n2_m2)) if n2_m2 else np.nan,
                "p_m1_n1": empirical_p(obs_s["m1_mean"], n1_dists[s]["m1_mean"]),
                "p_m1_n2": empirical_p(obs_s["m1_mean"], n2_dists[s]["m1_mean"]),
                "p_m2_n1": empirical_p(obs_s["m2_mean"], n1_dists[s]["m2_mean"]),
                "p_m2_n2": empirical_p(obs_s["m2_mean"], n2_dists[s]["m2_mean"]),
                "q_m1_n1": sig_gate["per_sector_detail"][s]["m1_mean_n1_q"],
                "q_m1_n2": sig_gate["per_sector_detail"][s]["m1_mean_n2_q"],
                "q_m2_n1": sig_gate["per_sector_detail"][s]["m2_mean_n1_q"],
                "q_m2_n2": sig_gate["per_sector_detail"][s]["m2_mean_n2_q"],
                "sector_signal_pass": sig_gate["sector_pass"][s],
                "sector_stability_pass": stab_gate["sector_pass"][s],
            })

        # Sensitivity rows (all k variants)
        for k in top_k_list:
            for s in sectors:
                rows_sensitivity.append({
                    "country": country,
                    "sector": s,
                    "scenario": scenario,
                    "top_k": k,
                    "m1_obs_mean": obs_by_k[k][s]["m1_mean"],
                    "m2_obs_mean": obs_by_k[k][s]["m2_mean"],
                })

    # Global gate
    n_countries = len(countries)
    n_sig_pass = sum(signal_gate_per_country.values())
    n_stab_pass = sum(stability_gate_per_country.values())

    signal_supported = n_sig_pass >= COUNTRIES_NEEDED
    stability_supported = n_stab_pass >= COUNTRIES_NEEDED

    verdict_signal = (
        "G2_AGGREGATE_TEMPORAL_SIGNAL_SUPPORTED"
        if signal_supported else
        "G2_AGGREGATE_TEMPORAL_SIGNAL_NOT_SUPPORTED"
    )
    verdict_stability = (
        "G2_EDGE_STABILITY_SUPPORTED"
        if stability_supported else
        "G2_EDGE_STABILITY_NOT_SUPPORTED"
    )

    if verbose:
        print(f"\n=== GLOBAL GATE ===")
        print(f"  Signal:    {n_sig_pass}/{n_countries} countries -> {verdict_signal}")
        print(f"  Stability: {n_stab_pass}/{n_countries} countries -> {verdict_stability}")

    # Save artifacts
    df_main = pd.DataFrame(rows_main)
    df_sens = pd.DataFrame(rows_sensitivity)
    df_m3 = pd.DataFrame(rows_m3)

    df_main.to_csv(out_dir / "g2_corrected_controls.csv", index=False)
    df_sens.to_csv(out_dir / "g2_corrected_controls_sensitivity.csv", index=False)
    df_m3.to_csv(out_dir / "g2_corrected_m3_loyo.csv", index=False)

    summary = {
        "protocol": "DEC-024c — corrected controls from source growth series",
        "source": str(DEFAULT_PANEL.relative_to(BASE)),
        "supersedes": "commit cc48924 (permuted pre-computed edge weights — invalid null)",
        "n2_implementation_note": (
            "N2 column permutation (permute_growth_territory_cols) was verified degenerate "
            "for M1/M2 Jaccard: null std=0.0, p=1.0 always (mathematically equivalent to "
            "node relabeling; Jaccard is label-invariant). N2 uses row-wise territory "
            "permutation (permute_growth_territory from build_g1_l2_cogrowth.py): within "
            "each observation_year, shuffle which territory receives which growth value. "
            "This tests whether co-movement identity depends on specific territory assignments."
        ),
        "params": {
            "scenario": scenario,
            "top_k_principal": TOP_K_PRINCIPAL,
            "top_k_variants": top_k_list,
            "window": WINDOW,
            "min_periods": MIN_PERIODS,
            "n_permutations": n_permutations,
            "seed_n1": seed_n1,
            "seed_n2_row_wise": seed_n2,
            "fdr_q": FDR_Q,
            "observation_years_excluded_from_windows": sorted(list(exclude_years)),
            "eval_year_2020_retained": True,
            "m2_stability_threshold": M2_STABILITY_THRESHOLD,
            "countries_needed": COUNTRIES_NEEDED,
            "sector_frac_needed": SECTOR_FRAC_NEEDED,
        },
        "gate": {
            "signal_country_results": signal_gate_per_country,
            "stability_country_results": stability_gate_per_country,
            "n_signal_pass": n_sig_pass,
            "n_stability_pass": n_stab_pass,
            "n_countries": n_countries,
            "verdict_signal": verdict_signal,
            "verdict_stability": verdict_stability,
            "g13_status": (
                "G2_AGGREGATE_TEMPORAL_SIGNAL_SUPPORTED"
                if signal_supported else
                "EXPLORATORY_PENDING_REVALIDATION"
            ),
        },
        "floor_p_diagnostics": floor_p_all,
        "reconciliation_g1_l2_vs_g2": RECONCILIATION_G1_VS_G2,
        "m3_null_status": (
            "BLOCKED — 199 perms x n_obs_years x n_affected_evals x full pipeline is prohibitive"
        ),
        "artifacts": {
            "g2_corrected_controls.csv": "per country x sector, principal k=5, N1+N2 results",
            "g2_corrected_controls_sensitivity.csv": "k=3,5,10 observed metrics",
            "g2_corrected_m3_loyo.csv": "M3 LOYO reconstruction (observed only, null BLOCKED)",
            "g2_corrected_controls_summary.json": "this file",
        },
    }

    with open(out_dir / "g2_corrected_controls_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if verbose:
        print(f"\nArtifacts -> {out_dir}")

    return summary


def build_covid_comparison(
    included_csv: Path,
    excluded_csv: Path,
    out_csv: Path,
    out_json: Path,
) -> dict:
    """Compare identical corrected-control runs with and without obs-year 2020."""
    inc = pd.read_csv(included_csv)
    exc = pd.read_csv(excluded_csv)
    keys = ["country", "sector", "top_k"]
    merged = inc.merge(exc, on=keys, suffixes=("_included", "_excluded"), validate="one_to_one")

    for metric in ["m1_obs_mean", "m2_obs_mean"]:
        merged[f"{metric}_delta_excluded_minus_included"] = (
            merged[f"{metric}_excluded"] - merged[f"{metric}_included"]
        )
        denom = merged[f"{metric}_included"].abs().replace(0, np.nan)
        merged[f"{metric}_relative_delta"] = (
            merged[f"{metric}_delta_excluded_minus_included"] / denom
        )

    merged["decision_changed"] = (
        merged["sector_signal_pass_included"].astype(bool)
        != merged["sector_signal_pass_excluded"].astype(bool)
    )
    merged["covid_classification"] = np.select(
        [
            merged["decision_changed"],
            merged[
                [
                    "m1_obs_mean_included",
                    "m1_obs_mean_excluded",
                    "m2_obs_mean_included",
                    "m2_obs_mean_excluded",
                ]
            ].isna().any(axis=1),
        ],
        ["COVID_SENSITIVE", "INSUFFICIENT_DATA"],
        default="COVID_ROBUST",
    )
    merged.to_csv(out_csv, index=False)

    country_summary = {}
    for country, group in merged.groupby("country", sort=True):
        included_pass = int(group["sector_signal_pass_included"].astype(bool).sum())
        excluded_pass = int(group["sector_signal_pass_excluded"].astype(bool).sum())
        changed = int(group["decision_changed"].sum())
        n = len(group)
        country_summary[country] = {
            "n_sectors": n,
            "included_pass_sectors": included_pass,
            "excluded_pass_sectors": excluded_pass,
            "changed_sectors": changed,
            "country_pass_included": included_pass / n >= SECTOR_FRAC_NEEDED,
            "country_pass_excluded": excluded_pass / n >= SECTOR_FRAC_NEEDED,
            "classification": (
                "COVID_ROBUST"
                if changed == 0 and (included_pass / n >= SECTOR_FRAC_NEEDED)
                == (excluded_pass / n >= SECTOR_FRAC_NEEDED)
                else "COVID_SENSITIVE"
            ),
        }

    summary = {
        "protocol": "same corrected G2 controls; only observation_year=2020 exclusion differs",
        "covid_has_special_weight": False,
        "included_artifact": str(included_csv),
        "excluded_artifact": str(excluded_csv),
        "country_summary": country_summary,
        "n_sector_decisions_changed": int(merged["decision_changed"].sum()),
        "n_sector_comparisons": int(len(merged)),
    }
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="G2 corrected temporal controls (DEC-024c)"
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--n-permutations", type=int, default=N_PERMUTATIONS)
    parser.add_argument("--seed-n1", type=int, default=SEED_N1)
    parser.add_argument("--seed-n2", type=int, default=SEED_N2)
    parser.add_argument(
        "--include-observation-year-2020",
        action="store_true",
        help="Include observation_year=2020 in rolling windows (main scenario).",
    )
    args = parser.parse_args()
    run_corrected_controls(
        panel_path=args.panel,
        out_dir=args.out_dir,
        n_permutations=args.n_permutations,
        seed_n1=args.seed_n1,
        seed_n2=args.seed_n2,
        exclude_years=(
            frozenset()
            if args.include_observation_year_2020
            else COVID_EXCLUDE
        ),
        scenario=(
            "include_observation_2020"
            if args.include_observation_year_2020
            else "exclude_observation_2020"
        ),
    )


if __name__ == "__main__":
    main()
