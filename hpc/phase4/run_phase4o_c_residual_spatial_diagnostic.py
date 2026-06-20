#!/usr/bin/env python3
"""Phase 4O-C: corrected rigorous residual spatial autocorrelation diagnostic.

Corrections over Phase 4O-B:
  1. Causal scale uses historical *residuals* (y_true - y_pred), not target scale.
  2. Gate LOO check is fail-closed: missing or duplicate LOO → gate FAIL.
  3. Graph-control gate requires qualifying years (Moran FDR-sig + I>0) to also
     pass graph FDR — not just any year.

Three residual types:
  abs    — y_true - y_pred
  rel    — (y_true - y_pred) / max(|y_true|, EPSILON)
  causal — (y_true - y_pred) / causal_residual_scale(config, region, years < t)
           using 1.4826 × MAD of past residuals; fallback to country-level.

p-value: one-sided, (1 + count) / (1 + N_PERM)  — never 0.
FDR: Benjamini-Hochberg at q=0.05, within each country × config × residual_type.
Graph controls: 999 conjugation permutations P W Pᵀ (relabels territories while
preserving multiset of degrees and spectrum of W).
LOO: required for every qualifying year; fail-closed.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
COUNTRIES = ("PT", "IT", "AT")
CONFIGS = ("n0_persistence", "n3_ridge_residual")
RESIDUAL_TYPES = ("abs", "rel", "causal")
EVAL_YEARS = tuple(range(2012, 2021))
N_PERM = 999
N_GRAPH_CTRL = 999
EPSILON = 1.0
MIN_HIST = 3       # minimum past residual observations for regional MAD
LOO_FRACTION = 0.5
BH_Q = 0.05
RNG_SEED = 42


# ── Geometry ──────────────────────────────────────────────────────────────────

def panel_id_to_nuts(region_id: str) -> str:
    return region_id.replace("_", "", 1) if region_id.startswith("PT_") else region_id


def load_geometry(geo_path: Path, country: str, panel_ids: list[str]) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(geo_path)
    nuts_to_panel = {panel_id_to_nuts(r): r for r in panel_ids}
    gdf = gdf[gdf["NUTS_ID"].isin(nuts_to_panel)].copy()
    gdf["panel_id"] = gdf["NUTS_ID"].map(nuts_to_panel)
    missing = set(panel_ids) - set(gdf["panel_id"])
    if missing:
        raise ValueError(f"{country}: {len(missing)} panel IDs missing from geojson: {sorted(missing)[:5]}")
    return gdf.set_index("panel_id").loc[sorted(panel_ids)].to_crs("EPSG:3035")


def queen_adjacency_raw(gdf: gpd.GeoDataFrame) -> np.ndarray:
    n = len(gdf); geoms = gdf.geometry.values
    W = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            if geoms[i].touches(geoms[j]) or geoms[i].intersects(geoms[j]):
                W[i, j] = W[j, i] = 1.0
    np.fill_diagonal(W, 0.0)
    return W


def row_normalise(W: np.ndarray) -> np.ndarray:
    rs = W.sum(axis=1, keepdims=True)
    rs[rs == 0] = 1.0
    return W / rs


# ── Spatial statistics ────────────────────────────────────────────────────────

def moran_global(x: np.ndarray, W: np.ndarray) -> float:
    if W.sum() < 1e-12:
        return float("nan")
    n = len(x); dev = x - x.mean(); ss = float(dev @ dev)
    if ss < 1e-12:
        return float("nan")
    return float(n * (dev @ (W @ dev)) / (ss * W.sum()))


def pvalue_one_sided(x: np.ndarray, W: np.ndarray, I_obs: float,
                     rng: np.random.Generator, n_perm: int = N_PERM) -> float:
    """(1 + #{I_perm >= I_obs}) / (1 + n_perm); never 0."""
    if math.isnan(I_obs):
        return float("nan")
    r = x.copy(); count = 0
    for _ in range(n_perm):
        rng.shuffle(r)
        if moran_global(r, W) >= I_obs:
            count += 1
    return (1 + count) / (1 + n_perm)


def pvalue_graph_one_sided(I_obs: float, I_controls: list[float]) -> float:
    valid = [v for v in I_controls if not math.isnan(v)]
    if not valid or math.isnan(I_obs):
        return float("nan")
    count = sum(1 for v in valid if v >= I_obs)
    return (1 + count) / (1 + len(valid))


def conjugation_permutation(W_raw: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """P W_raw Pᵀ; preserves multiset of degrees and spectrum; relabels territories."""
    n = W_raw.shape[0]; perm = rng.permutation(n)
    return row_normalise(W_raw[np.ix_(perm, perm)])


# ── FDR ───────────────────────────────────────────────────────────────────────

def benjamini_hochberg(pvalues: list[float], q: float = BH_Q) -> list[bool]:
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    last = -1
    for rank, idx in enumerate(order, 1):
        if pvalues[idx] <= (rank / m) * q:
            last = rank
    reject = [False] * m
    if last >= 0:
        for rank, idx in enumerate(order, 1):
            if rank <= last:
                reject[idx] = True
    return reject


# ── Causal residual scale ─────────────────────────────────────────────────────

def causal_residual_scale(
    pred_hist: pd.DataFrame,
    region_id: str,
    year: int,
    min_hist: int = MIN_HIST,
    epsilon: float = EPSILON,
) -> tuple[float, dict]:
    """Scale = 1.4826 × MAD of historical residuals (years < year, same config/region).

    pred_hist must contain rows from the SAME config and country (already filtered),
    with columns: region_id, year, y_true, y_pred.
    Never accesses year t or later. Returns (scale, metadata).
    """
    past = pred_hist[(pred_hist["region_id"] == region_id) & (pred_hist["year"] < year)]
    if len(past) >= min_hist:
        res = (past["y_true"] - past["y_pred"]).to_numpy(dtype=float)
        mad = float(np.median(np.abs(res - np.median(res))))
        scale = 1.4826 * mad
        if scale > epsilon:
            return scale, {"source": "region_mad", "n": int(len(res))}
        std = float(res.std(ddof=1)) if len(res) > 1 else 0.0
        if std > epsilon:
            return std, {"source": "region_std", "n": int(len(res))}

    # Country-level fallback: all regions, years < year
    past_country = pred_hist[pred_hist["year"] < year]
    if len(past_country) >= min_hist:
        res_c = (past_country["y_true"] - past_country["y_pred"]).to_numpy(dtype=float)
        mad_c = float(np.median(np.abs(res_c - np.median(res_c))))
        scale_c = 1.4826 * mad_c
        if scale_c > epsilon:
            return scale_c, {"source": "country_mad_fallback", "n": int(len(res_c))}
        std_c = float(res_c.std(ddof=1)) if len(res_c) > 1 else 0.0
        if std_c > epsilon:
            return std_c, {"source": "country_std_fallback", "n": int(len(res_c))}

    return epsilon, {"source": "epsilon_fallback", "n": int(len(past_country))}


# ── Residuals ─────────────────────────────────────────────────────────────────

def compute_residuals(
    pred_sub: pd.DataFrame,
    pred_hist: pd.DataFrame,
    year: int,
    residual_type: str,
    region_order: list[str],
    return_metadata: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict]:
    """pred_sub: predictions for this country/config/year.
    pred_hist: all predictions for this country/config (all eval years, causal use only).
    """
    df = pred_sub.set_index("region_id")
    missing = set(region_order) - set(df.index)
    if missing:
        raise ValueError(f"Residual alignment: missing regions {sorted(missing)[:3]}")
    df = df.loc[region_order]
    raw = (df["y_true"] - df["y_pred"]).to_numpy(dtype=float)

    metadata = {
        "scale_sources": {},
        "regional_scale_count": 0,
        "fallback_scale_count": 0,
        "all_scales_regional": residual_type != "causal",
    }
    if residual_type == "abs":
        return (raw, metadata) if return_metadata else raw
    if residual_type == "rel":
        denom = np.maximum(df["y_true"].abs().to_numpy(dtype=float), EPSILON)
        values = raw / denom
        return (values, metadata) if return_metadata else values
    if residual_type == "causal":
        scales = []
        sources: dict[str, int] = {}
        for rid in region_order:
            scale, scale_meta = causal_residual_scale(pred_hist, rid, year)
            scales.append(scale)
            source = str(scale_meta["source"])
            sources[source] = sources.get(source, 0) + 1
        regional_count = sum(
            count
            for source, count in sources.items()
            if source in {"region_mad", "region_std"}
        )
        metadata = {
            "scale_sources": sources,
            "regional_scale_count": regional_count,
            "fallback_scale_count": len(region_order) - regional_count,
            "all_scales_regional": regional_count == len(region_order),
        }
        values = raw / np.asarray(scales)
        return (values, metadata) if return_metadata else values
    raise ValueError(f"Unknown residual type: {residual_type}")


# ── Leave-one-out ─────────────────────────────────────────────────────────────

def leave_one_out(
    residuals: np.ndarray,
    W_raw: np.ndarray,
    region_order: list[str],
    I_original: float,
    rng: np.random.Generator,
    n_perm: int = N_PERM,
) -> dict:
    idx_max = int(np.argmax(np.abs(residuals)))
    keep = [i for i in range(len(residuals)) if i != idx_max]
    if len(keep) < 3:
        return {"skipped": True, "reason": "too few regions after LOO"}
    r_loo = residuals[keep]
    W_loo = row_normalise(W_raw[np.ix_(keep, keep)])
    I_loo = moran_global(r_loo, W_loo)
    p_loo = pvalue_one_sided(r_loo, W_loo, I_loo, rng, n_perm)
    preserves_direction = bool(I_loo > 0)
    preserves_magnitude = bool(
        not math.isnan(I_loo) and not math.isnan(I_original)
        and I_original > 0 and I_loo >= LOO_FRACTION * I_original
    )
    return {
        "excluded_region": region_order[idx_max],
        "I_original": float(I_original),
        "I_loo": float(I_loo),
        "p_loo": float(p_loo),
        "preserves_direction": preserves_direction,
        "preserves_magnitude": preserves_magnitude,
        "loo_pass": bool(preserves_direction and preserves_magnitude),
    }


# ── Gate (fail-closed) ────────────────────────────────────────────────────────

def evaluate_gate(
    sub_m: pd.DataFrame,
    loo_df: pd.DataFrame,
    country: str,
    config: str,
) -> tuple[bool, dict]:
    """Evaluate gate for one country/config. Fail-closed on LOO and graph alignment."""
    detail: dict = {}
    robust_pass = False

    for res_type in ("rel", "causal"):
        sub_t = sub_m[sub_m["residual_type"] == res_type]
        raw_fdr_pos = sub_t[sub_t["sig_perm_fdr"] & (sub_t["I_real"] > 0)]
        if res_type == "causal":
            if "causal_scale_all_regional" not in raw_fdr_pos.columns:
                fdr_pos = raw_fdr_pos.iloc[0:0]
                fallback_excluded = set(int(y) for y in raw_fdr_pos["year"])
            else:
                regional_mask = raw_fdr_pos["causal_scale_all_regional"].fillna(False)
                fdr_pos = raw_fdr_pos[regional_mask]
                fallback_excluded = set(
                    int(y) for y in raw_fdr_pos.loc[~regional_mask, "year"]
                )
        else:
            fdr_pos = raw_fdr_pos
            fallback_excluded = set()
        qualifying_years = set(int(y) for y in fdr_pos["year"])

        # (a) at least 2 FDR-significant positive years
        c_a = len(qualifying_years) >= 2
        # (b) at least 1 of those years != 2020
        c_b = c_a and any(y != 2020 for y in qualifying_years)

        # (c) graph control: qualifying years must ALL pass sig_graph_fdr
        if c_b and qualifying_years:
            graph_at_qualifying = sub_t[sub_t["year"].isin(qualifying_years)]
            graph_pass_years = set(
                int(r["year"]) for _, r in graph_at_qualifying.iterrows()
                if r["sig_graph_fdr"]
            )
            graph_missing = qualifying_years - graph_pass_years
            c_c = len(graph_missing) == 0
        else:
            graph_pass_years = set()
            graph_missing = qualifying_years
            c_c = False

        # (d) LOO: fail-closed — every qualifying year must have exactly one LOO result
        loo_sub = loo_df[
            (loo_df["country"] == country)
            & (loo_df["config"] == config)
            & (loo_df["residual_type"] == res_type)
        ] if not loo_df.empty else pd.DataFrame()

        observed_loo_years = set(int(y) for y in loo_sub["year"]) if len(loo_sub) > 0 else set()
        missing_loo = qualifying_years - observed_loo_years
        # Detect duplicates
        dup_loo = set(
            int(y) for y in loo_sub["year"]
            if len(loo_sub[loo_sub["year"] == y]) > 1
        ) if len(loo_sub) > 0 else set()

        if not c_b:
            c_d = False
            loo_all_pass = False
        elif missing_loo or dup_loo:
            # fail-closed: missing or duplicate → FAIL
            c_d = False
            loo_all_pass = False
        elif len(loo_sub) > 0:
            # Only check LOO for qualifying years
            loo_qualifying = loo_sub[loo_sub["year"].isin(qualifying_years)]
            loo_all_pass = bool(loo_qualifying["loo_pass"].all()) and len(loo_qualifying) == len(qualifying_years)
            c_d = loo_all_pass
        else:
            c_d = False
            loo_all_pass = False

        passes = c_a and c_b and c_c and c_d
        if passes:
            robust_pass = True

        detail[res_type] = {
            "fdr_positive_years": sorted(qualifying_years),
            "fdr_positive_years_before_scale_gate": sorted(
                int(y) for y in raw_fdr_pos["year"]
            ),
            "causal_fallback_excluded_years": sorted(fallback_excluded),
            "non_2020_count": int(sum(1 for y in qualifying_years if y != 2020)),
            "c_a_2plus_years": c_a,
            "c_b_non2020": c_b,
            "c_c_graph_all_qualifying": c_c,
            "graph_pass_years": sorted(graph_pass_years),
            "graph_missing_years": sorted(graph_missing),
            "c_d_loo_closed": c_d,
            "expected_loo_years": sorted(qualifying_years),
            "observed_loo_years": sorted(observed_loo_years),
            "missing_loo_years": sorted(missing_loo),
            "duplicate_loo_years": sorted(dup_loo),
            "loo_all_pass": loo_all_pass,
            "passes": passes,
        }

    # abs alone is never sufficient (may reflect heteroscedasticity)
    detail["abs"] = _abs_summary(sub_m[sub_m["residual_type"] == "abs"])
    return robust_pass, detail


def _abs_summary(sub_t: pd.DataFrame) -> dict:
    fdr_pos = sub_t[sub_t["sig_perm_fdr"] & (sub_t["I_real"] > 0)]
    return {
        "fdr_positive_years": sorted(int(y) for y in fdr_pos["year"]),
        "note": "abs alone insufficient (may reflect heteroscedasticity, not spatial structure)",
    }


# ── Connectivity helpers ──────────────────────────────────────────────────────

def connected_components(W_raw: np.ndarray) -> int:
    n = W_raw.shape[0]; visited = [False] * n; comps = 0
    for start in range(n):
        if visited[start]:
            continue
        comps += 1; queue = [start]
        while queue:
            node = queue.pop()
            if visited[node]:
                continue
            visited[node] = True
            queue.extend(j for j in range(n) if W_raw[node, j] > 0 and not visited[j])
    return comps


def neighbor_correlation(x: np.ndarray, W: np.ndarray) -> float:
    lag = W @ x
    if np.std(x) < 1e-12 or np.std(lag) < 1e-12:
        return float("nan")
    return float(np.corrcoef(x, lag)[0, 1])


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase4n-root", type=Path,
                        default=Path("hpc_results/herald_phase4n_a_local_r1"))
    parser.add_argument("--panel", type=Path,
                        default=Path("data/processed/european_panel/"
                                     "enterprise_birth_pt_it_at_mainland_panel.csv"))
    parser.add_argument("--geojson", type=Path,
                        default=Path("data/external/nuts3_2021_eurostat.geojson"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("hpc_results/herald_phase4o_c_spatial_r1"))
    parser.add_argument("--n-perm", type=int, default=N_PERM)
    parser.add_argument("--n-graph-ctrl", type=int, default=N_GRAPH_CTRL)
    args = parser.parse_args()

    n4n_root   = args.phase4n_root  if args.phase4n_root.is_absolute()  else BASE / args.phase4n_root
    panel_path = args.panel         if args.panel.is_absolute()         else BASE / args.panel
    geo_path   = args.geojson       if args.geojson.is_absolute()       else BASE / args.geojson
    out_dir    = args.output_dir    if args.output_dir.is_absolute()    else BASE / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "adjacency").mkdir(exist_ok=True)

    rng = np.random.default_rng(RNG_SEED)
    panel = pd.read_csv(panel_path)
    pred_all = pd.read_csv(n4n_root / "phase4n_predictions.csv")

    moran_rows: list[dict] = []
    graph_rows: list[dict] = []
    loo_rows:   list[dict] = []
    adj_manifest: dict = {}

    for country in COUNTRIES:
        print(f"\n=== {country} ===", flush=True)
        panel_ids = sorted(panel[panel["country"] == country]["region_id"].unique())
        gdf = load_geometry(geo_path, country, panel_ids)
        region_order = list(gdf.index)

        W_raw  = queen_adjacency_raw(gdf)
        W_real = row_normalise(W_raw)
        n = W_raw.shape[0]

        print(f"  Building {args.n_graph_ctrl} graph controls…", flush=True)
        W_controls = [conjugation_permutation(W_raw, rng) for _ in range(args.n_graph_ctrl)]

        np.save(out_dir / "adjacency" / f"adj_raw_{country}.npy",  W_raw)
        np.save(out_dir / "adjacency" / f"adj_norm_{country}.npy", W_real)

        adj_manifest[country] = {
            "n_regions": n,
            "n_edges": int((W_raw > 0).sum() // 2),
            "isolated_nodes": int((W_raw.sum(axis=1) == 0).sum()),
            "n_components": connected_components(W_raw),
            "degree_mean": float(W_raw.sum(axis=1).mean()),
            "degree_std":  float(W_raw.sum(axis=1).std(ddof=1)),
        }

        for config in CONFIGS:
            print(f"    config={config}", flush=True)
            # Filtered history for causal scale (same country, same config, all years)
            pred_hist = pred_all[
                pred_all["country"].eq(country) & pred_all["config"].eq(config)
            ].copy()

            for res_type in RESIDUAL_TYPES:
                p_perm_list: list[float] = []
                year_data: list[dict] = []

                for year in EVAL_YEARS:
                    sub = pred_all[
                        pred_all["country"].eq(country)
                        & pred_all["config"].eq(config)
                        & pred_all["year"].eq(year)
                    ].copy()
                    if sub.empty:
                        continue
                    try:
                        r, residual_meta = compute_residuals(
                            sub,
                            pred_hist,
                            year,
                            res_type,
                            region_order,
                            return_metadata=True,
                        )
                    except ValueError as exc:
                        print(f"      residual error year={year}: {exc}")
                        continue

                    I_real  = moran_global(r, W_real)
                    p_perm  = pvalue_one_sided(r, W_real, I_real, rng, args.n_perm)
                    I_ctrls = [moran_global(r, Wc) for Wc in W_controls]
                    p_graph = pvalue_graph_one_sided(I_real, I_ctrls)

                    p_perm_list.append(p_perm)
                    year_data.append({
                        "country": country, "config": config,
                        "residual_type": res_type, "year": year,
                        "I_real": float(I_real),
                        "I_ctrl_median": float(np.nanmedian(I_ctrls)),
                        "p_perm": float(p_perm),
                        "p_graph": float(p_graph),
                        "neighbor_corr": float(neighbor_correlation(r, W_real)),
                        "causal_scale_all_regional": bool(
                            residual_meta["all_scales_regional"]
                        ),
                        "causal_scale_regional_count": int(
                            residual_meta["regional_scale_count"]
                        ),
                        "causal_scale_fallback_count": int(
                            residual_meta["fallback_scale_count"]
                        ),
                        "causal_scale_sources_json": json.dumps(
                            residual_meta["scale_sources"], sort_keys=True
                        ),
                    })
                    graph_rows.append({
                        "country": country, "config": config,
                        "residual_type": res_type, "year": year,
                        "I_real": float(I_real),
                        "I_ctrl_mean":   float(np.nanmean(I_ctrls)),
                        "I_ctrl_median": float(np.nanmedian(I_ctrls)),
                        "I_ctrl_p95":    float(np.nanpercentile(I_ctrls, 95)),
                        "p_graph": float(p_graph),
                    })

                # FDR within family (country × config × residual_type)
                reject_perm  = benjamini_hochberg(p_perm_list, BH_Q)
                p_graph_list = [d["p_graph"] for d in year_data]
                reject_graph = benjamini_hochberg(p_graph_list, BH_Q)

                for i, d in enumerate(year_data):
                    d["sig_perm_raw"] = bool(d["p_perm"] < BH_Q)
                    d["sig_perm_fdr"] = bool(reject_perm[i]) if i < len(reject_perm) else False
                    d["sig_graph_fdr"] = bool(reject_graph[i]) if i < len(reject_graph) else False
                    moran_rows.append(d)

                # LOO for FDR-significant positive years
                for i, d in enumerate(year_data):
                    if not (d.get("sig_perm_fdr") and d["I_real"] > 0):
                        continue
                    year = d["year"]
                    sub = pred_all[
                        pred_all["country"].eq(country)
                        & pred_all["config"].eq(config)
                        & pred_all["year"].eq(year)
                    ].copy()
                    r = compute_residuals(sub, pred_hist, year, res_type, region_order)
                    loo = leave_one_out(r, W_raw, region_order, d["I_real"], rng, args.n_perm)
                    loo.update({"country": country, "config": config,
                                "residual_type": res_type, "year": year})
                    loo_rows.append(loo)

    moran_df = pd.DataFrame(moran_rows)
    graph_df = pd.DataFrame(graph_rows)
    loo_df   = pd.DataFrame(loo_rows) if loo_rows else pd.DataFrame()

    # Global BH sensitivity
    moran_df["sig_perm_fdr_global"] = False
    for config in CONFIGS:
        for res_type in RESIDUAL_TYPES:
            mask = (moran_df["config"] == config) & (moran_df["residual_type"] == res_type)
            ps = moran_df.loc[mask, "p_perm"].tolist()
            rej = benjamini_hochberg(ps, BH_Q)
            moran_df.loc[mask, "sig_perm_fdr_global"] = rej

    moran_df["sig_perm_fdr_global"] = moran_df["sig_perm_fdr_global"].astype(bool)

    # ── Gate ─────────────────────────────────────────────────────────────────
    gate_results: dict = {}
    for config in CONFIGS:
        gate_results[config] = {}
        n_passing = 0
        for country in COUNTRIES:
            sub_m = moran_df[
                (moran_df["country"] == country) & (moran_df["config"] == config)
            ]
            passes, detail = evaluate_gate(sub_m, loo_df, country, config)
            gate_results[config][country] = {"pass": passes, "detail": detail}
            if passes:
                n_passing += 1
        phase4p_auth = n_passing >= 2
        gate_results[config]["summary"] = {
            "countries_passing": n_passing,
            "phase4p_multi_country_authorised": phase4p_auth,
            "italy_single_country_spatial_lag_recommended": gate_results[config].get("IT", {}).get("pass", False),
        }

    any_multi = any(
        gate_results[cfg]["summary"]["phase4p_multi_country_authorised"]
        for cfg in CONFIGS
    )
    any_it_pass = any(
        gate_results[cfg].get("IT", {}).get("pass", False)
        for cfg in CONFIGS
    )

    decision = {
        "phase": "4O-C",
        "n_perm": args.n_perm,
        "n_graph_ctrl": args.n_graph_ctrl,
        "rng_seed": RNG_SEED,
        "bh_q": BH_Q,
        "loo_fraction": LOO_FRACTION,
        "loo_fail_closed": True,
        "causal_residual_scale_uses": "historical_residuals_not_target",
        "causal_gate_requires": (
            "all regions use region_mad or region_std; country/epsilon "
            "fallback years are exploratory only"
        ),
        "graph_control_note": "P W P^T conjugation: relabels territories, preserves degree multiset and spectrum",
        "p_value_note": "p=0.001 with N=999 means minimum estimable value (1/1000), not an exact probability",
        "gate_by_config": gate_results,
        "any_phase4p_multi_country_authorised": any_multi,
        "next_step": (
            "Phase 4P spatial-lag linear experiment for Italy only (no multi-country LOCO claim)"
            if any_it_pass and not any_multi
            else "No spatial-lag experiment authorised; gather third enterprise_birth country"
            if not any_it_pass
            else "Phase 4P multi-country spatial-lag authorised"
        ),
    }

    moran_df.to_csv(out_dir / "moran_yearly.csv", index=False)
    graph_df.to_csv(out_dir / "graph_control_results.csv", index=False)
    if not loo_df.empty:
        loo_df.to_csv(out_dir / "leave_one_out_results.csv", index=False)
    (out_dir / "adjacency_manifest.json").write_text(
        json.dumps(adj_manifest, indent=2), encoding="utf-8"
    )
    (out_dir / "phase4o_c_decision.json").write_text(
        json.dumps(decision, indent=2), encoding="utf-8"
    )

    print("\n=== GATE ===")
    for cfg in CONFIGS:
        s = gate_results[cfg]["summary"]
        print(f"\n{cfg}: {s['countries_passing']}/3 pass → multi-country: {s['phase4p_multi_country_authorised']}")
        for country in COUNTRIES:
            print(f"  {country}: {gate_results[cfg][country]['pass']}")
    print(f"\nFinal: multi-country 4P authorised: {any_multi}")
    print(f"Italy single-country spatial lag: {any_it_pass}")
    print(f"Next: {decision['next_step']}")
    print(f"\nOutput: {out_dir}")


if __name__ == "__main__":
    main()
