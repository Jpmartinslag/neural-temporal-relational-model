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
