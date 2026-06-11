"""G2 Temporal Preflight: characterise L2 co-growth graph dynamics.

Analyses the validated L2 edges (G-10 SUPPORTED) across time to quantify:
  - Inventory: country × sector × year coverage
  - Edge density (raw and top-k filtered)
  - Persistence: fraction of years each edge appears in top-k graph
  - Neighbor turnover: how often top-k neighborhoods change year-to-year
  - Annual weight variation: mean absolute change in positive-pair weights
  - Top-k sensitivity: Jaccard similarity of adjacency under k=3,5,10
  - LOYO stability: leave-one-year-out Pearson of adjacency matrices
  - COVID-period comparison: pre/during/post edge statistics

Outputs (all compact, no raw edges):
  data/processed/economic_graph/g2_preflight/g2_inventory.csv
  data/processed/economic_graph/g2_preflight/g2_density.csv
  data/processed/economic_graph/g2_preflight/g2_persistence.csv
  data/processed/economic_graph/g2_preflight/g2_turnover.csv
  data/processed/economic_graph/g2_preflight/g2_variation.csv
  data/processed/economic_graph/g2_preflight/g2_topk_sensitivity.csv
  data/processed/economic_graph/g2_preflight/g2_loyo.csv
  data/processed/economic_graph/g2_preflight/g2_covid_comparison.csv
  data/processed/economic_graph/g2_preflight/g2_preflight_summary.json

Results are per country × sector. Country results are never pooled.
No community labels are used (DEC-021: NOT_SUPPORTED).
No causal attribution. No economic recommendation.
"""
from __future__ import annotations

import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
EDGES_PATH = BASE / "data/processed/economic_graph/g1_l2_cogrowth/g1_l2_edges.csv"
OUT_DIR = BASE / "data/processed/economic_graph/g2_preflight"

# Parameters matching Phase 5 / L2 builder
TOP_K_DEFAULT = 5
TOP_K_VARIANTS = [3, 5, 10]
COVID_YEAR = 2020
PRE_COVID_YEARS = list(range(2015, 2020))   # 2015-2019
COVID_YEARS = [2020]
POST_COVID_YEARS = list(range(2021, 2024))  # 2021-2023

# Falsifiable criteria (pre-registered before analysis, DEC-024)
PERSISTENCE_THRESHOLD = 0.70  # edge in top-k in ≥70% of valid years
WEIGHT_CHANGE_THRESHOLD = 0.15  # |Δweight| ≥ 0.15 = strengthening/weakening
LOYO_STABILITY_MIN = 0.70       # Pearson(adj_loyo, adj_full) ≥ 0.70 = stable
TURNOVER_STABLE_MAX = 0.30      # turnover ≤ 30% = stable neighbourhood
SECTORAL_WAVE_THRESHOLD = 0.25  # ≥25% of pairs moving same direction = wave

# PT KZ: structural absence (DEC-018); excluded from PT analysis
PT_EXCLUDED_SECTORS = {"KZ"}


def _top_k_symmetric(corr: np.ndarray, k: int) -> np.ndarray:
    """Keep top-k positive correlations per row; symmetrise; positive only."""
    n = corr.shape[0]
    adj = np.zeros((n, n), dtype=float)
    for i in range(n):
        row = corr[i].copy()
        row[i] = -np.inf
        top_idx = np.argsort(row)[::-1][:k]
        for j in top_idx:
            if row[j] > 0:
                adj[i, j] = row[j]
    adj = np.maximum(adj, adj.T)
    return adj


def _adj_matrix(sub: pd.DataFrame, region_order: list[str], k: int) -> np.ndarray:
    """Build top-k adj matrix from long-format edge dataframe (one year×sector)."""
    n = len(region_order)
    idx = {r: i for i, r in enumerate(region_order)}
    corr = np.full((n, n), np.nan)
    np.fill_diagonal(corr, 1.0)
    for _, row in sub.iterrows():
        s, t = idx.get(row.source_region), idx.get(row.target_region)
        if s is not None and t is not None:
            corr[s, t] = row.weight_cogrowth
            corr[t, s] = row.weight_cogrowth
    corr = np.nan_to_num(corr, nan=-1.0)
    return _top_k_symmetric(corr, k)


def jaccard_adjacency(a1: np.ndarray, a2: np.ndarray) -> float:
    """Jaccard similarity of binary adjacency (upper triangle)."""
    b1 = (np.triu(a1, k=1) > 0).ravel()
    b2 = (np.triu(a2, k=1) > 0).ravel()
    inter = (b1 & b2).sum()
    union = (b1 | b2).sum()
    return float(inter / union) if union > 0 else np.nan


def pearson_adj(a1: np.ndarray, a2: np.ndarray) -> float:
    """Pearson correlation of upper-triangle weights."""
    mask = np.triu(np.ones_like(a1, dtype=bool), k=1)
    v1, v2 = a1[mask], a2[mask]
    if v1.std() < 1e-9 or v2.std() < 1e-9:
        return np.nan
    return float(np.corrcoef(v1, v2)[0, 1])


# ---------------------------------------------------------------------------
# Negative control helpers
# ---------------------------------------------------------------------------

# Gate constants (pre-registered, DEC-024)
NEG_CTRL_N_PERMUTATIONS = 199
NEG_CTRL_FDR_Q = 0.05
NEG_CTRL_COUNTRIES_NEEDED = 2
NEG_CTRL_SECTOR_FRAC_NEEDED = 0.50


def _bh_fdr_reject(pvalues: np.ndarray, q: float = NEG_CTRL_FDR_Q) -> np.ndarray:
    """Benjamini-Hochberg FDR correction. Returns boolean reject array."""
    n = len(pvalues)
    if n == 0:
        return np.array([], dtype=bool)
    sorted_idx = np.argsort(pvalues)
    sorted_p = pvalues[sorted_idx]
    thresholds = (np.arange(1, n + 1) / n) * q
    sig = sorted_p <= thresholds
    reject = np.zeros(n, dtype=bool)
    if sig.any():
        cutoff = int(np.where(sig)[0].max())
        reject[sorted_idx[: cutoff + 1]] = True
    return reject


def _top_k_symmetric_vec(corr: np.ndarray, k: int) -> np.ndarray:
    """Vectorized top-k symmetric adjacency. Equivalent to _top_k_symmetric."""
    n = corr.shape[0]
    corr_nd = corr.copy()
    np.fill_diagonal(corr_nd, -np.inf)
    k_clamped = min(k, n - 1)
    # argpartition: indices of top-k per row (unsorted, correct set)
    top_idx = np.argpartition(corr_nd, -k_clamped, axis=1)[:, -k_clamped:]
    row_idx = np.repeat(np.arange(n), k_clamped)
    col_idx = top_idx.ravel()
    vals = corr[row_idx, col_idx]
    pos = vals > 0
    adj = np.zeros((n, n), dtype=float)
    adj[row_idx[pos], col_idx[pos]] = vals[pos]
    return np.maximum(adj, adj.T)


def _loyo_jaccard_binary(B: np.ndarray) -> float | None:
    """
    Fast LOYO Jaccard from binary upper-triangle matrix [n_years, n_edges].
    Matches run_preflight LOYO logic: mean over leave-year means.
    Returns None if fewer than 4 years.
    """
    n_years = B.shape[0]
    if n_years < 4:
        return None
    B_i = B.astype(np.int32)
    inter = B_i @ B_i.T          # [n_years, n_years] — count of shared edges
    rowsum = B_i.sum(axis=1)      # [n_years]
    union = rowsum[:, None] + rowsum[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        jac = np.where(union > 0, inter.astype(float) / union, np.nan)
    np.fill_diagonal(jac, np.nan)
    per_yr = np.nanmean(jac, axis=1)   # mean Jaccard of each year vs others
    valid = per_yr[np.isfinite(per_yr)]
    return float(np.mean(valid)) if len(valid) > 0 else None


def _pivot_weights_mat(
    se: pd.DataFrame, regions: list[str], years: list[int]
) -> np.ndarray:
    """
    Build float matrix W[pair_idx, year_idx] from long-format edge DataFrame.
    Pairs are unique undirected: (regions[i], regions[j]) with i < j.
    Missing entries are NaN. Duplicate directed pairs are deduplicated (last wins).
    """
    n_r = len(regions)
    ridx = {r: i for i, r in enumerate(regions)}
    yidx = {y: j for j, y in enumerate(years)}
    n_pairs = n_r * (n_r - 1) // 2

    W = np.full((n_pairs, len(years)), np.nan)
    s_arr = se["source_region"].map(ridx).values
    t_arr = se["target_region"].map(ridx).values
    y_arr = se["available_for_forecast_year"].map(yidx).values
    w_arr = se["weight_cogrowth"].values.astype(float)

    valid = (
        ~(pd.isnull(s_arr) | pd.isnull(t_arr) | pd.isnull(y_arr))
    )
    s_arr = np.where(valid, s_arr.astype(float), np.nan)
    t_arr = np.where(valid, t_arr.astype(float), np.nan)
    valid2 = valid & np.isfinite(s_arr) & np.isfinite(t_arr)

    s_v = s_arr[valid2].astype(int)
    t_v = t_arr[valid2].astype(int)
    y_v = y_arr[valid2].astype(int)
    w_v = w_arr[valid2]

    same = s_v == t_v
    s_v, t_v, y_v, w_v = s_v[~same], t_v[~same], y_v[~same], w_v[~same]
    lo = np.minimum(s_v, t_v)
    hi = np.maximum(s_v, t_v)
    # Triangle index: lo*(2*n - lo - 1)//2 + (hi - lo - 1)
    p_idx = lo * (2 * n_r - lo - 1) // 2 + (hi - lo - 1)
    W[p_idx, y_v] = w_v
    return W


def _reconstruct_adjs_from_W(
    W: np.ndarray, n_r: int, years: list[int], k: int,
    triu_i: np.ndarray, triu_j: np.ndarray,
) -> np.ndarray:
    """
    Build binary upper-triangle matrix [n_years, n_pairs] from W.
    Returns B[yr_idx, pair_idx] = True if edge present in top-k graph.
    """
    n_years = len(years)
    n_pairs = W.shape[0]
    B = np.zeros((n_years, n_pairs), dtype=bool)
    for yi in range(n_years):
        w_col = W[:, yi]
        corr = np.full((n_r, n_r), -1.0)
        np.fill_diagonal(corr, 1.0)
        fin = np.isfinite(w_col)
        corr[triu_i[fin], triu_j[fin]] = w_col[fin]
        corr[triu_j[fin], triu_i[fin]] = w_col[fin]
        adj = _top_k_symmetric_vec(corr, k)
        B[yi] = adj[triu_i, triu_j] > 0
    return B


def _permute_W(W: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Permute years within each pair row, preserving NaN mask.
    No-NaN fast path uses rng.permuted(axis=1).
    """
    if not np.isnan(W).any():
        return rng.permuted(W, axis=1)
    W_p = W.copy()
    for pi in range(W.shape[0]):
        valid = np.where(np.isfinite(W[pi]))[0]
        if len(valid) > 1:
            W_p[pi, valid] = rng.permutation(W[pi, valid])
    return W_p


def _evaluate_neg_ctrl_gate(df: pd.DataFrame) -> tuple[dict, str]:
    """
    Fail-closed gate:
    - ≥NEG_CTRL_COUNTRIES_NEEDED countries where ≥NEG_CTRL_SECTOR_FRAC_NEEDED
      sectors are FDR-significant with positive observed effect.
    """
    countries = sorted(df["country"].unique())
    country_results: dict[str, dict] = {}
    for country in countries:
        cd = df[df["country"] == country]
        n_eligible = len(cd)
        sig = cd[cd["fdr_reject"] & cd["positive_effect"]]
        n_sig = len(sig)
        frac = n_sig / n_eligible if n_eligible > 0 else 0.0
        country_results[country] = {
            "n_eligible": n_eligible,
            "n_significant": n_sig,
            "frac_significant": round(frac, 4),
            "pass": (frac >= NEG_CTRL_SECTOR_FRAC_NEEDED and n_sig > 0),
        }
    n_pass = sum(1 for v in country_results.values() if v["pass"])
    gate_pass = n_pass >= NEG_CTRL_COUNTRIES_NEEDED
    gate = {
        "pass": gate_pass,
        "n_countries_passing": n_pass,
        "countries": country_results,
        "reason": (
            f"{n_pass}/{len(countries)} countries pass "
            f"(need ≥{NEG_CTRL_COUNTRIES_NEEDED}; each needs "
            f"≥{NEG_CTRL_SECTOR_FRAC_NEEDED:.0%} sectors FDR-q={NEG_CTRL_FDR_Q} "
            f"with positive observed effect)"
        ),
    }
    verdict = (
        "G2_EDGE_DYNAMICS_SUPPORTED"
        if gate_pass
        else "G2_EDGE_DYNAMICS_NOT_SUPPORTED"
    )
    return gate, verdict


def run_negative_control(
    edges: pd.DataFrame,
    n_permutations: int = NEG_CTRL_N_PERMUTATIONS,
    top_k_list: list | None = None,
    exclude_covid: bool = True,
    seed: int = 42,
) -> dict:
    """
    Temporal permutation negative control for LOYO Jaccard.

    For each country × sector: permute year labels within each territory-pair
    (preserving marginal distribution and NaN mask), rebuild graph from scratch,
    compute LOYO Jaccard. p = (1 + count(null≥obs)) / (N+1). BH/FDR q=0.05.

    Gate (fail-closed): ≥2 countries with ≥50% sectors FDR-significant
    and observed > null median.

    Returns dict with keys: 'results' (DataFrame), 'gate' (dict),
    'verdict' (str), 'sensitivity' (DataFrame).
    """
    if top_k_list is None:
        top_k_list = TOP_K_VARIANTS  # [3, 5, 10]
    rng = np.random.default_rng(seed)

    countries = sorted(edges["country"].unique())
    primary_k = TOP_K_DEFAULT

    rows_primary: list[dict] = []
    rows_sensitivity: list[dict] = []

    for country in countries:
        ce = edges[edges["country"] == country].copy()
        sectors = sorted(ce["sector"].unique())
        if country == "PT":
            sectors = [s for s in sectors if s not in PT_EXCLUDED_SECTORS]

        for sector in sectors:
            se = ce[ce["sector"] == sector]
            years_all = sorted(se["available_for_forecast_year"].unique())
            if exclude_covid:
                years_use = [y for y in years_all if y != COVID_YEAR]
            else:
                years_use = years_all
            if len(years_use) < 4:
                continue

            regions = sorted(set(se["source_region"]) | set(se["target_region"]))
            n_r = len(regions)
            se_filt = se[se["available_for_forecast_year"].isin(years_use)]
            W = _pivot_weights_mat(se_filt, regions, years_use)

            triu_i, triu_j = np.triu_indices(n_r, k=1)
            assert W.shape[0] == len(triu_i), "W row count must equal n_pairs"

            # Precompute observed LOYO Jaccard for all k variants in one pass
            obs_B: dict[int, np.ndarray] = {}
            for k in set(top_k_list) | {primary_k}:
                obs_B[k] = _reconstruct_adjs_from_W(W, n_r, years_use, k, triu_i, triu_j)
            obs_loyo: dict[int, float | None] = {
                k: _loyo_jaccard_binary(obs_B[k]) for k in obs_B
            }

            if obs_loyo.get(primary_k) is None:
                continue

            # Permutation loop: one W permutation → compute LOYO for all k
            null_dist: dict[int, list[float]] = {k: [] for k in obs_B}
            for _ in range(n_permutations):
                W_p = _permute_W(W, rng)
                for k in obs_B:
                    B_p = _reconstruct_adjs_from_W(W_p, n_r, years_use, k, triu_i, triu_j)
                    v = _loyo_jaccard_binary(B_p)
                    if v is not None:
                        null_dist[k].append(v)

            # Build result rows
            for k in obs_B:
                obs_val = obs_loyo[k]
                if obs_val is None:
                    continue
                null_arr = np.array(null_dist[k])
                if len(null_arr) < n_permutations * 0.9:
                    continue
                null_mean = float(np.mean(null_arr))
                null_median = float(np.median(null_arr))
                null_q5 = float(np.percentile(null_arr, 5))
                null_q95 = float(np.percentile(null_arr, 95))
                # p-value: never zero
                p_val = (1.0 + float(np.sum(null_arr >= obs_val))) / (len(null_arr) + 1.0)
                eff_abs = obs_val - null_mean
                eff_rel = eff_abs / null_mean if null_mean > 1e-12 else np.nan
                positive_effect = bool(obs_val > null_median)
                row = {
                    "country": country,
                    "sector": sector,
                    "top_k": k,
                    "exclude_covid": exclude_covid,
                    "n_years": len(years_use),
                    "n_regions": n_r,
                    "obs_loyo_jaccard": round(obs_val, 6),
                    "null_mean": round(null_mean, 6),
                    "null_median": round(null_median, 6),
                    "null_q5": round(null_q5, 6),
                    "null_q95": round(null_q95, 6),
                    "effect_abs": round(eff_abs, 6),
                    "effect_rel": round(eff_rel, 4) if np.isfinite(eff_rel) else np.nan,
                    "p_value": round(p_val, 6),
                    "positive_effect": positive_effect,
                    "n_permutations_valid": len(null_arr),
                }
                if k == primary_k:
                    rows_primary.append(row)
                else:
                    rows_sensitivity.append(row)

    if not rows_primary:
        return {
            "results": pd.DataFrame(),
            "sensitivity": pd.DataFrame(),
            "gate": {"pass": False, "reason": "no data"},
            "verdict": "G2_EDGE_DYNAMICS_NOT_SUPPORTED",
        }

    df_primary = pd.DataFrame(rows_primary)
    # BH/FDR on primary results
    reject = _bh_fdr_reject(df_primary["p_value"].values, q=NEG_CTRL_FDR_Q)
    df_primary = df_primary.copy()
    df_primary["fdr_reject"] = reject

    df_sensitivity = pd.DataFrame(rows_sensitivity) if rows_sensitivity else pd.DataFrame()
    if not df_sensitivity.empty:
        rej_s = _bh_fdr_reject(df_sensitivity["p_value"].values, q=NEG_CTRL_FDR_Q)
        df_sensitivity = df_sensitivity.copy()
        df_sensitivity["fdr_reject"] = rej_s

    gate, verdict = _evaluate_neg_ctrl_gate(df_primary)
    return {
        "results": df_primary,
        "sensitivity": df_sensitivity,
        "gate": gate,
        "verdict": verdict,
    }


def run_preflight(edges: pd.DataFrame) -> dict:
    """Run all G2 preflight metrics. Returns dict of DataFrames."""
    results: dict[str, list] = {
        k: [] for k in ["inventory", "density", "persistence", "turnover",
                         "variation", "topk_sensitivity", "loyo", "covid_comparison"]
    }

    countries = sorted(edges["country"].unique())

    for country in countries:
        ce = edges[edges["country"] == country].copy()
        sectors = sorted(ce["sector"].unique())
        if country == "PT":
            sectors = [s for s in sectors if s not in PT_EXCLUDED_SECTORS]

        all_years = sorted(ce["available_for_forecast_year"].unique())
        regions_all = sorted(set(ce["source_region"]) | set(ce["target_region"]))

        for sector in sectors:
            se = ce[ce["sector"] == sector]
            years = sorted(se["available_for_forecast_year"].unique())
            if len(years) < 2:
                continue

            regions = sorted(set(se["source_region"]) | set(se["target_region"]))
            n_r = len(regions)
            n_pairs = n_r * (n_r - 1) // 2

            # --- 1. Inventory ---
            results["inventory"].append({
                "country": country, "sector": sector,
                "n_years": len(years), "n_regions": n_r,
                "year_min": min(years), "year_max": max(years),
            })

            # --- 2. Density (top-k=5) ---
            adjs: dict[int, np.ndarray] = {}
            for yr in years:
                sub = se[se["available_for_forecast_year"] == yr]
                adj = _adj_matrix(sub, regions, TOP_K_DEFAULT)
                adjs[yr] = adj
                n_edges = int((np.triu(adj, k=1) > 0).sum())
                w_vals = adj[np.triu(np.ones_like(adj, dtype=bool), k=1) & (adj > 0)]
                results["density"].append({
                    "country": country, "sector": sector,
                    "eval_year": yr,
                    "n_edges_topk5": n_edges,
                    "density": n_edges / max(n_pairs, 1),
                    "w_mean": float(w_vals.mean()) if len(w_vals) > 0 else np.nan,
                    "w_std": float(w_vals.std()) if len(w_vals) > 1 else np.nan,
                    "w_median": float(np.median(w_vals)) if len(w_vals) > 0 else np.nan,
                })

            # --- 3. Persistence ---
            edge_counts: dict[tuple, int] = {}
            for yr, adj in adjs.items():
                triu_idx = np.argwhere(np.triu(adj, k=1) > 0)
                for i, j in triu_idx:
                    key = (regions[i], regions[j])
                    edge_counts[key] = edge_counts.get(key, 0) + 1

            n_yr = len(years)
            for (r1, r2), cnt in edge_counts.items():
                persist = cnt / n_yr
                results["persistence"].append({
                    "country": country, "sector": sector,
                    "source": r1, "target": r2,
                    "n_years_present": cnt, "n_years_total": n_yr,
                    "persistence": persist,
                    "persistent": persist >= PERSISTENCE_THRESHOLD,
                })

            # --- 4. Neighbor turnover ---
            sorted_years = sorted(adjs.keys())
            for yi in range(len(sorted_years) - 1):
                ya, yb = sorted_years[yi], sorted_years[yi + 1]
                adj_a, adj_b = adjs[ya], adjs[yb]
                turnovers = []
                for r in range(n_r):
                    nbrs_a = set(np.where(adj_a[r] > 0)[0])
                    nbrs_b = set(np.where(adj_b[r] > 0)[0])
                    if not nbrs_a and not nbrs_b:
                        continue
                    union = nbrs_a | nbrs_b
                    sym_diff = nbrs_a ^ nbrs_b
                    turnovers.append(len(sym_diff) / len(union))
                if turnovers:
                    results["turnover"].append({
                        "country": country, "sector": sector,
                        "year_from": ya, "year_to": yb,
                        "mean_turnover": float(np.mean(turnovers)),
                        "stable": float(np.mean(turnovers)) <= TURNOVER_STABLE_MAX,
                    })

            # --- 5. Annual weight variation ---
            raw_weights: dict[int, dict[tuple, float]] = {}
            for yr in years:
                sub = se[se["available_for_forecast_year"] == yr]
                wd: dict[tuple, float] = {}
                for _, row in sub.iterrows():
                    r1, r2 = row.source_region, row.target_region
                    if r1 > r2:
                        r1, r2 = r2, r1
                    wd[(r1, r2)] = float(row.weight_cogrowth)
                raw_weights[yr] = wd

            for yi in range(len(sorted_years) - 1):
                ya, yb = sorted_years[yi], sorted_years[yi + 1]
                wa, wb = raw_weights.get(ya, {}), raw_weights.get(yb, {})
                common = set(wa) & set(wb)
                if not common:
                    continue
                diffs = [wb[k] - wa[k] for k in common]
                abs_diffs = [abs(d) for d in diffs]
                results["variation"].append({
                    "country": country, "sector": sector,
                    "year_from": ya, "year_to": yb,
                    "n_common_pairs": len(common),
                    "mean_abs_change": float(np.mean(abs_diffs)),
                    "frac_strengthening": float(np.mean([d > WEIGHT_CHANGE_THRESHOLD for d in diffs])),
                    "frac_weakening": float(np.mean([d < -WEIGHT_CHANGE_THRESHOLD for d in diffs])),
                    "wave_signal": float(np.mean([d > WEIGHT_CHANGE_THRESHOLD for d in diffs])) >= SECTORAL_WAVE_THRESHOLD
                              or float(np.mean([d < -WEIGHT_CHANGE_THRESHOLD for d in diffs])) >= SECTORAL_WAVE_THRESHOLD,
                })

            # --- 6. Top-k sensitivity ---
            adjs_k: dict[int, dict[int, np.ndarray]] = {}
            for yr in years:
                sub = se[se["available_for_forecast_year"] == yr]
                adjs_k[yr] = {}
                for k in TOP_K_VARIANTS:
                    adjs_k[yr][k] = _adj_matrix(sub, regions, k)

            for yr in years:
                jac_3_5 = jaccard_adjacency(adjs_k[yr][3], adjs_k[yr][5])
                jac_5_10 = jaccard_adjacency(adjs_k[yr][5], adjs_k[yr][10])
                results["topk_sensitivity"].append({
                    "country": country, "sector": sector, "eval_year": yr,
                    "jaccard_k3_k5": jac_3_5,
                    "jaccard_k5_k10": jac_5_10,
                })

            # --- 7. LOYO stability ---
            # Pearson: full upper-triangle weights (sparse → low for structural changes)
            # Jaccard: binary adjacency (complementary structural metric)
            if len(adjs) >= 4:
                loyo_corrs = []
                loyo_jacs = []
                for leave_yr in sorted_years:
                    other_adjs = [adjs[y] for y in sorted_years if y != leave_yr]
                    full_adj = adjs[leave_yr]
                    pearson_vals = [pearson_adj(full_adj, a) for a in other_adjs]
                    jaccard_vals = [jaccard_adjacency(full_adj, a) for a in other_adjs]
                    valid_p = [p for p in pearson_vals if np.isfinite(p)]
                    valid_j = [j for j in jaccard_vals if np.isfinite(j)]
                    if valid_p:
                        loyo_corrs.append(np.mean(valid_p))
                    if valid_j:
                        loyo_jacs.append(np.mean(valid_j))
                if loyo_corrs:
                    mean_loyo = float(np.mean(loyo_corrs))
                    mean_jac = float(np.mean(loyo_jacs)) if loyo_jacs else np.nan
                    results["loyo"].append({
                        "country": country, "sector": sector,
                        "mean_loyo_pearson": mean_loyo,
                        "min_loyo_pearson": float(np.min(loyo_corrs)),
                        "mean_loyo_jaccard": mean_jac,
                        "stable": mean_loyo >= LOYO_STABILITY_MIN,
                    })

            # --- 8. COVID comparison ---
            def period_stats(period_years):
                valid = [y for y in period_years if y in adjs]
                if not valid:
                    return {}
                dens = []
                wmeans = []
                for y in valid:
                    adj = adjs[y]
                    n_e = int((np.triu(adj, k=1) > 0).sum())
                    wv = adj[np.triu(np.ones_like(adj, dtype=bool), k=1) & (adj > 0)]
                    dens.append(n_e / max(n_pairs, 1))
                    wmeans.append(float(wv.mean()) if len(wv) > 0 else np.nan)
                return {
                    "density": np.mean(dens),
                    "w_mean": np.nanmean(wmeans),
                    "n_years": len(valid),
                }

            pre = period_stats(PRE_COVID_YEARS)
            cov = period_stats(COVID_YEARS)
            post = period_stats(POST_COVID_YEARS)
            if pre and post:
                delta_density = post["density"] - pre["density"]
                delta_w = post["w_mean"] - pre["w_mean"]
                results["covid_comparison"].append({
                    "country": country, "sector": sector,
                    "pre_density": pre["density"], "pre_w_mean": pre["w_mean"],
                    "covid_density": cov.get("density", np.nan),
                    "covid_w_mean": cov.get("w_mean", np.nan),
                    "post_density": post["density"], "post_w_mean": post["w_mean"],
                    "delta_density_post_pre": delta_density,
                    "delta_w_post_pre": delta_w,
                    "density_disrupted": abs(delta_density) >= 0.05,
                    "weight_disrupted": abs(delta_w) >= WEIGHT_CHANGE_THRESHOLD,
                })

    return {k: pd.DataFrame(v) for k, v in results.items()}


def main() -> None:
    print("Loading L2 edges...")
    edges = pd.read_csv(EDGES_PATH, low_memory=False)
    print(f"  {len(edges):,} rows, {edges['country'].nunique()} countries, "
          f"{edges['sector'].nunique()} sectors, "
          f"{edges['available_for_forecast_year'].nunique()} years")

    print("Running preflight metrics...")
    dfs = run_preflight(edges)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in dfs.items():
        path = OUT_DIR / f"g2_{name}.csv"
        df.to_csv(path, index=False)
        print(f"  Saved {path.name} ({len(df):,} rows)")

    print(f"\nRunning negative control ({NEG_CTRL_N_PERMUTATIONS} permutations)...")
    nc = run_negative_control(edges)
    nc["results"].to_csv(OUT_DIR / "g2_negative_control.csv", index=False)
    print(f"  Saved g2_negative_control.csv ({len(nc['results'])} rows)")
    if not nc["sensitivity"].empty:
        nc["sensitivity"].to_csv(OUT_DIR / "g2_negative_control_sensitivity.csv", index=False)
        print(f"  Saved g2_negative_control_sensitivity.csv ({len(nc['sensitivity'])} rows)")
    print(f"  Verdict: {nc['verdict']}")
    print(f"  Gate: {nc['gate']['reason']}")

    # Re-save summary with negative control results
    summary["negative_control"] = {
        "verdict": nc["verdict"],
        "gate": nc["gate"],
        "n_permutations": NEG_CTRL_N_PERMUTATIONS,
        "fdr_q": NEG_CTRL_FDR_Q,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Summary
    inv = dfs["inventory"]
    loyo = dfs["loyo"]
    pers = dfs["persistence"]
    turn = dfs["turnover"]
    covid = dfs["covid_comparison"]
    topo = dfs["topk_sensitivity"]

    summary = {
        "protocol": {
            "top_k_default": TOP_K_DEFAULT,
            "top_k_variants": TOP_K_VARIANTS,
            "pre_covid_years": PRE_COVID_YEARS,
            "covid_years": COVID_YEARS,
            "post_covid_years": POST_COVID_YEARS,
            "falsifiable_criteria": {
                "persistence_threshold": PERSISTENCE_THRESHOLD,
                "weight_change_threshold": WEIGHT_CHANGE_THRESHOLD,
                "loyo_stability_min": LOYO_STABILITY_MIN,
                "turnover_stable_max": TURNOVER_STABLE_MAX,
                "sectoral_wave_threshold": SECTORAL_WAVE_THRESHOLD,
            },
        },
        "inventory": {
            "n_country_sector_combos": len(inv),
            "by_country": {c: int(inv[inv.country == c]["n_regions"].iloc[0])
                          for c in sorted(inv["country"].unique())},
        },
        "loyo_stability": {
            f"{row.country}/{row.sector}": {
                "mean_pearson": round(row.mean_loyo_pearson, 4),
                "stable": bool(row.stable),
            }
            for _, row in loyo.iterrows()
        } if not loyo.empty else {},
        "persistence": {
            "total_edges_seen": len(pers),
            "persistent_frac": round(float((pers["persistent"]).mean()), 4) if not pers.empty else None,
            "by_country": {c: round(float(pers[pers.country == c]["persistent"].mean()), 4)
                          for c in sorted(pers["country"].unique())} if not pers.empty else {},
        },
        "turnover": {
            "mean_turnover_by_country": {c: round(float(turn[turn.country == c]["mean_turnover"].mean()), 4)
                                          for c in sorted(turn["country"].unique())} if not turn.empty else {},
            "stable_frac": round(float(turn["stable"].mean()), 4) if not turn.empty else None,
        },
        "covid_comparison": {
            "disrupted_density_frac": round(float(covid["density_disrupted"].mean()), 4) if not covid.empty else None,
            "disrupted_weight_frac": round(float(covid["weight_disrupted"].mean()), 4) if not covid.empty else None,
            "mean_delta_density": round(float(covid["delta_density_post_pre"].mean()), 4) if not covid.empty else None,
            "mean_delta_w": round(float(covid["delta_w_post_pre"].mean()), 4) if not covid.empty else None,
        },
        "topk_sensitivity": {
            "mean_jaccard_k3_k5": round(float(topo["jaccard_k3_k5"].mean()), 4) if not topo.empty else None,
            "mean_jaccard_k5_k10": round(float(topo["jaccard_k5_k10"].mean()), 4) if not topo.empty else None,
        },
    }

    # Negative control summary (populated after nc run below if available)
    summary["negative_control"] = {"verdict": "PENDING", "gate": {}}

    summary_path = OUT_DIR / "g2_preflight_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Saved {summary_path.name}")
    print()
    print("=== Key results ===")
    print(f"  LOYO stability (mean Pearson): "
          f"{np.mean([v['mean_pearson'] for v in summary['loyo_stability'].values()]):.3f}"
          if summary['loyo_stability'] else "  LOYO: no data")
    print(f"  Persistent edges (≥{PERSISTENCE_THRESHOLD:.0%}): "
          f"{summary['persistence']['persistent_frac']:.1%}" if summary['persistence']['persistent_frac'] else "  Persistence: no data")
    stable_frac = summary['turnover']['stable_frac']
    print(f"  Mean turnover: "
          f"{stable_frac:.1%} stable combos" if stable_frac is not None else "  Turnover: no data")
    print(f"  Top-k Jaccard k=3 vs k=5: {summary['topk_sensitivity']['mean_jaccard_k3_k5']:.3f}")
    print(f"  Top-k Jaccard k=5 vs k=10: {summary['topk_sensitivity']['mean_jaccard_k5_k10']:.3f}")
    print(f"  COVID density disruption (|Δ|≥0.05): "
          f"{summary['covid_comparison']['disrupted_density_frac']:.1%}")
    print(f"  COVID weight disruption (|Δ|≥{WEIGHT_CHANGE_THRESHOLD}): "
          f"{summary['covid_comparison']['disrupted_weight_frac']:.1%}")


if __name__ == "__main__":
    main()
