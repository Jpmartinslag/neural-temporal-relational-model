#!/usr/bin/env python3
"""Phase 4O-B: rigorous residual spatial autocorrelation diagnostic.

Three residual definitions:
  abs      — y_true - y_pred
  rel      — (y_true - y_pred) / max(|y_true|, EPSILON)
  causal   — (y_true - y_pred) / causal_scale(territory, year)

Causal scale: std of historical target_births for the territory across all
panel years < current eval year. Fallback (< 3 historical observations):
median absolute target for the country-year, computed from the same causal
window.  Never uses the current year or future years.

p-value formula (one-sided, positive autocorrelation):
  p = (1 + #{I_perm >= I_obs}) / (1 + N_PERM)
This guarantees p >= 1/(N_PERM+1) > 0.

FDR/Benjamini-Hochberg applied within each family:
  - primary: country × config × residual_type, years 2012-2020 (9 tests)
  - sensitivity: global (all countries × years) per config × residual_type

Graph controls: 999 conjugation permutations W_ctrl = P W P^T (row-renormed).
These preserve the row/column sum pattern (degree sequence), breaking geographic
identity. p_graph is computed the same way as the residual p-value.

Leave-one-out: for each year that passes FDR (within-family), remove the region
with the largest |residual| and recompute I. Pass requires I_LOO > 0 and
I_LOO >= 0.5 × I_original.

Gate (pre-specified): a country passes for a config if
  (a) >= 2 years with I > 0 AND FDR-significant, for >= 1 robust residual type
      (rel or causal; absolute alone is insufficient);
  (b) >= 1 of those years is not 2020;
  (c) real graph beats controls (FDR, within-family);
  (d) LOO preserves direction and >= 50% of effect for each qualifying year.

Phase 4P is authorised if >= 2/3 countries pass for the same config.
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
EPSILON = 1.0      # births are always >= 0; epsilon prevents div-by-zero
MIN_HIST = 3       # minimum historical obs for causal std
LOO_FRACTION = 0.5 # I_LOO >= LOO_FRACTION * I_original
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
        raise ValueError(f"{country}: {len(missing)} panel IDs not in geojson: {sorted(missing)[:5]}")
    gdf = gdf.set_index("panel_id").loc[sorted(panel_ids)]
    gdf = gdf.to_crs("EPSG:3035")
    return gdf


def queen_adjacency_raw(gdf: gpd.GeoDataFrame) -> np.ndarray:
    """Unweighted symmetric queen-contiguity matrix (no self-loops)."""
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
    """Global Moran's I with row-normalised W."""
    if W.sum() < 1e-12:
        return float("nan")
    n = len(x); dev = x - x.mean()
    ss = float(dev @ dev)
    if ss < 1e-12:
        return float("nan")
    lag = W @ dev
    return float(n * (dev @ lag) / (ss * W.sum()))


def pvalue_one_sided(
    x: np.ndarray,
    W: np.ndarray,
    I_obs: float,
    rng: np.random.Generator,
    n_perm: int = N_PERM,
) -> float:
    """One-sided (positive autocorrelation) permutation p-value; never 0."""
    if math.isnan(I_obs):
        return float("nan")
    r = x.copy()
    count = 0
    for _ in range(n_perm):
        rng.shuffle(r)
        if moran_global(r, W) >= I_obs:
            count += 1
    return (1 + count) / (1 + n_perm)


def pvalue_graph_one_sided(
    I_obs: float,
    I_controls: list[float],
) -> float:
    """One-sided p_graph: fraction of control-graph Moran's >= I_obs."""
    valid = [v for v in I_controls if not math.isnan(v)]
    if not valid or math.isnan(I_obs):
        return float("nan")
    n = len(valid)
    count = sum(1 for v in valid if v >= I_obs)
    return (1 + count) / (1 + n)


def conjugation_permutation(W_raw: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Generate control W = P W_raw P^T (conjugation, same degree sequence)."""
    n = W_raw.shape[0]
    perm = rng.permutation(n)
    W_ctrl_raw = W_raw[np.ix_(perm, perm)]
    return row_normalise(W_ctrl_raw)


# ── FDR ───────────────────────────────────────────────────────────────────────

def benjamini_hochberg(pvalues: list[float], q: float = BH_Q) -> list[bool]:
    """BH procedure. Returns rejection decision for each p-value (same order)."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    reject = [False] * m
    # Find largest k satisfying BH criterion
    last = -1
    for rank, idx in enumerate(order, 1):
        if pvalues[idx] <= (rank / m) * q:
            last = rank
    if last >= 0:
        for rank, idx in enumerate(order, 1):
            if rank <= last:
                reject[idx] = True
    return reject


# ── Residuals ─────────────────────────────────────────────────────────────────

def causal_scale(panel: pd.DataFrame, country: str, region_id: str, year: int) -> float:
    """Std of target_births for this territory over all panel years < year."""
    hist = panel[
        (panel["country"] == country)
        & (panel["region_id"] == region_id)
        & (panel["year"] < year)
    ]["target_births"].dropna()
    if len(hist) >= MIN_HIST:
        std = float(hist.std(ddof=1))
        if std > EPSILON:
            return std
    # Fallback: median |target| for this country, years < year
    fallback = panel[
        (panel["country"] == country) & (panel["year"] < year)
    ]["target_births"].dropna()
    med = float(fallback.abs().median()) if len(fallback) > 0 else EPSILON
    return max(med, EPSILON)


def compute_residuals(
    pred_sub: pd.DataFrame,
    panel: pd.DataFrame,
    country: str,
    year: int,
    residual_type: str,
    region_order: list[str],
) -> np.ndarray:
    """Compute aligned residuals for the given type."""
    df = pred_sub.set_index("region_id")
    missing = set(region_order) - set(df.index)
    if missing:
        raise ValueError(f"Missing regions: {sorted(missing)[:3]}")
    df = df.loc[region_order]
    raw = (df["y_true"] - df["y_pred"]).to_numpy(dtype=float)
    if residual_type == "abs":
        return raw
    elif residual_type == "rel":
        denom = np.maximum(df["y_true"].abs().to_numpy(dtype=float), EPSILON)
        return raw / denom
    elif residual_type == "causal":
        scales = np.array([
            causal_scale(panel, country, rid, year) for rid in region_order
        ])
        return raw / scales
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
        return {"skipped": True}
    r_loo = residuals[keep]
    W_loo_raw = W_raw[np.ix_(keep, keep)]
    W_loo = row_normalise(W_loo_raw)
    I_loo = moran_global(r_loo, W_loo)
    p_loo = pvalue_one_sided(r_loo, W_loo, I_loo, rng, n_perm)
    preserves_direction = bool(I_loo > 0)
    preserves_magnitude = bool(
        not math.isnan(I_loo) and not math.isnan(I_original)
        and I_original > 0
        and I_loo >= LOO_FRACTION * I_original
    )
    return {
        "excluded_region": region_order[idx_max],
        "I_loo": float(I_loo),
        "p_loo": float(p_loo),
        "I_original": float(I_original),
        "preserves_direction": preserves_direction,
        "preserves_magnitude": preserves_magnitude,
        "loo_pass": bool(preserves_direction and preserves_magnitude),
    }


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
                        default=Path("hpc_results/herald_phase4o_b_spatial_r1"))
    parser.add_argument("--n-perm", type=int, default=N_PERM)
    parser.add_argument("--n-graph-ctrl", type=int, default=N_GRAPH_CTRL)
    args = parser.parse_args()

    n4n_root  = args.phase4n_root  if args.phase4n_root.is_absolute()  else BASE / args.phase4n_root
    panel_path = args.panel        if args.panel.is_absolute()         else BASE / args.panel
    geo_path   = args.geojson      if args.geojson.is_absolute()       else BASE / args.geojson
    out_dir    = args.output_dir   if args.output_dir.is_absolute()    else BASE / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "adjacency").mkdir(exist_ok=True)

    rng = np.random.default_rng(RNG_SEED)
    panel = pd.read_csv(panel_path)
    pred_all = pd.read_csv(n4n_root / "phase4n_predictions.csv")

    # ── Per-country: build adjacency, controls, run tests ───────────────────
    moran_rows   : list[dict] = []
    graph_rows   : list[dict] = []
    loo_rows     : list[dict] = []
    adj_manifest : dict       = {}

    for country in COUNTRIES:
        print(f"\n=== {country} ===")
        panel_ids = sorted(panel[panel["country"] == country]["region_id"].unique())
        gdf = load_geometry(geo_path, country, panel_ids)
        region_order = list(gdf.index)

        W_raw  = queen_adjacency_raw(gdf)
        W_real = row_normalise(W_raw)
        n = W_raw.shape[0]

        # 999 graph controls (conjugation permutations, same degree sequence)
        print(f"  Building {args.n_graph_ctrl} graph controls…", flush=True)
        W_controls = [
            conjugation_permutation(W_raw, rng) for _ in range(args.n_graph_ctrl)
        ]

        np.save(out_dir / "adjacency" / f"adj_raw_{country}.npy", W_raw)
        np.save(out_dir / "adjacency" / f"adj_norm_{country}.npy", W_real)
        adj_manifest[country] = {
            "n_regions": n,
            "n_edges": int((W_raw > 0).sum() // 2),
            "isolated_nodes": int((W_raw.sum(axis=1) == 0).sum()),
            "n_components": _connected_components(W_raw),
            "degree_mean": float(W_raw.sum(axis=1).mean()),
            "degree_std": float(W_raw.sum(axis=1).std(ddof=1)),
        }

        for config in CONFIGS:
            print(f"    config={config}", flush=True)
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
                        r = compute_residuals(sub, panel, country, year, res_type, region_order)
                    except ValueError as e:
                        print(f"      residual error: {e}")
                        continue

                    I_real = moran_global(r, W_real)
                    p_perm = pvalue_one_sided(r, W_real, I_real, rng, args.n_perm)
                    I_controls = [moran_global(r, Wc) for Wc in W_controls]
                    p_graph    = pvalue_graph_one_sided(I_real, I_controls)

                    p_perm_list.append(p_perm)
                    year_data.append({
                        "country": country, "config": config,
                        "residual_type": res_type, "year": year,
                        "I_real": float(I_real),
                        "I_median_ctrl": float(np.nanmedian(I_controls)),
                        "real_gt_perm_median": bool(I_real > float(np.nanmedian(I_controls))),
                        "p_perm": float(p_perm),
                        "p_graph": float(p_graph),
                        "neighbor_corr": float(_neighbor_correlation(r, W_real)),
                    })
                    graph_rows.append({
                        "country": country, "config": config,
                        "residual_type": res_type, "year": year,
                        "I_real": float(I_real),
                        "I_ctrl_mean": float(np.nanmean(I_controls)),
                        "I_ctrl_median": float(np.nanmedian(I_controls)),
                        "I_ctrl_p95": float(np.nanpercentile(I_controls, 95)),
                        "p_graph": float(p_graph),
                        "n_ctrl_valid": sum(1 for v in I_controls if not math.isnan(v)),
                    })

                # Within-family FDR (BH) on p_perm
                p_perm_clean = [p for p in p_perm_list if not math.isnan(p)]
                years_clean  = [d["year"] for d in year_data]
                reject_perm  = benjamini_hochberg(p_perm_clean, BH_Q)
                # BH on p_graph (within same family)
                p_graph_list = [d["p_graph"] for d in year_data]
                p_graph_clean = [p for p in p_graph_list if not math.isnan(p)]
                reject_graph = benjamini_hochberg(p_graph_clean, BH_Q)

                for i, d in enumerate(year_data):
                    d["sig_perm_raw"] = bool(d["p_perm"] < BH_Q)
                    d["sig_perm_fdr"] = bool(reject_perm[i]) if i < len(reject_perm) else False
                    d["sig_graph_fdr"] = bool(reject_graph[i]) if i < len(reject_graph) else False
                    moran_rows.append(d)

                # Leave-one-out for FDR-significant positive years
                for i, d in enumerate(year_data):
                    if not (d.get("sig_perm_fdr") and d["I_real"] > 0):
                        continue
                    year = d["year"]
                    sub = pred_all[
                        pred_all["country"].eq(country)
                        & pred_all["config"].eq(config)
                        & pred_all["year"].eq(year)
                    ].copy()
                    r = compute_residuals(sub, panel, country, year, res_type, region_order)
                    loo = leave_one_out(r, W_raw, region_order, d["I_real"], rng, args.n_perm)
                    loo.update({"country": country, "config": config,
                                "residual_type": res_type, "year": year})
                    loo_rows.append(loo)

    # ── Global sensitivity BH ───────────────────────────────────────────────
    moran_df = pd.DataFrame(moran_rows)
    for config in CONFIGS:
        for res_type in RESIDUAL_TYPES:
            mask = (moran_df["config"] == config) & (moran_df["residual_type"] == res_type)
            ps = moran_df.loc[mask, "p_perm"].tolist()
            rej = benjamini_hochberg(ps, BH_Q)
            moran_df.loc[mask, "sig_perm_fdr_global"] = rej

    moran_df["sig_perm_fdr_global"] = moran_df.get("sig_perm_fdr_global", False).fillna(False)

    # ── Gate evaluation ─────────────────────────────────────────────────────
    loo_df = pd.DataFrame(loo_rows) if loo_rows else pd.DataFrame()
    graph_df = pd.DataFrame(graph_rows)

    gate_results: dict = {}
    for config in CONFIGS:
        gate_results[config] = {}
        countries_passing = 0
        for country in COUNTRIES:
            sub_m = moran_df[
                (moran_df["country"] == country) & (moran_df["config"] == config)
            ]
            # Criteria evaluated per robust residual type (rel or causal)
            robust_pass_for_any_type = False
            for res_type in ("rel", "causal"):
                sub_t = sub_m[sub_m["residual_type"] == res_type]
                # (a) >= 2 years FDR-significant with I > 0
                fdr_pos = sub_t[sub_t["sig_perm_fdr"] & (sub_t["I_real"] > 0)]
                c_a = len(fdr_pos) >= 2
                # (b) >= 1 of those years != 2020
                c_b = c_a and any(yr != 2020 for yr in fdr_pos["year"])
                # (c) real graph beats controls FDR
                c_c = sub_t["sig_graph_fdr"].any()
                # (d) LOO
                c_d = True
                if not loo_df.empty and c_b:
                    loo_sub = loo_df[
                        (loo_df["country"] == country)
                        & (loo_df["config"] == config)
                        & (loo_df["residual_type"] == res_type)
                    ]
                    if len(loo_sub) > 0:
                        c_d = bool(loo_sub["loo_pass"].all())
                if c_a and c_b and c_c and c_d:
                    robust_pass_for_any_type = True
                    break

            gate_results[config][country] = {
                "pass": robust_pass_for_any_type,
                "criteria_detail": _gate_detail(sub_m, loo_df, country, config),
            }
            if robust_pass_for_any_type:
                countries_passing += 1

        phase4p_auth = countries_passing >= 2
        gate_results[config]["summary"] = {
            "countries_passing": countries_passing,
            "phase4p_authorised": phase4p_auth,
        }

    any_auth = any(
        gate_results[cfg]["summary"]["phase4p_authorised"] for cfg in CONFIGS
    )

    decision = {
        "phase": "4O-B",
        "n_perm": args.n_perm,
        "n_graph_ctrl": args.n_graph_ctrl,
        "rng_seed": RNG_SEED,
        "bh_q": BH_Q,
        "loo_fraction": LOO_FRACTION,
        "gate_criteria": {
            "a": ">=2 years FDR-significant Moran I>0 for rel or causal residuals",
            "b": ">=1 of those years != 2020",
            "c": "real graph beats controls after FDR",
            "d": "LOO preserves direction and >=50% magnitude",
            "threshold": ">=2/3 countries must pass same config",
        },
        "gate_by_config": gate_results,
        "any_phase4p_authorised": any_auth,
        "next_step": (
            "Prepare Phase 4P linear spatial-lag comparison plan" if any_auth
            else "Do not add graph/GNN capacity; residuals lack robust spatial structure"
        ),
    }

    # ── Save outputs ─────────────────────────────────────────────────────────
    moran_df.to_csv(out_dir / "moran_yearly.csv", index=False)
    graph_df.to_csv(out_dir / "graph_control_results.csv", index=False)
    if not loo_df.empty:
        loo_df.to_csv(out_dir / "leave_one_out_results.csv", index=False)
    (out_dir / "adjacency_manifest.json").write_text(
        json.dumps(adj_manifest, indent=2), encoding="utf-8"
    )
    (out_dir / "phase4o_b_decision.json").write_text(
        json.dumps(decision, indent=2), encoding="utf-8"
    )

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n=== MORAN YEARLY (FDR) ===")
    cols = ["country", "config", "residual_type", "year",
            "I_real", "p_perm", "sig_perm_fdr", "sig_graph_fdr"]
    print(moran_df[cols].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("\n=== GATE ===")
    for cfg in CONFIGS:
        print(f"\n{cfg}:")
        for country in COUNTRIES:
            print(f"  {country}: {gate_results[cfg][country]['pass']}")
        print(f"  → Phase 4P authorised: {gate_results[cfg]['summary']['phase4p_authorised']}")
    print(f"\nFinal: any Phase 4P authorised: {any_auth}")


def _neighbor_correlation(x: np.ndarray, W: np.ndarray) -> float:
    lag = W @ x
    if np.std(x) < 1e-12 or np.std(lag) < 1e-12:
        return float("nan")
    return float(np.corrcoef(x, lag)[0, 1])


def _connected_components(W_raw: np.ndarray) -> int:
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


def _gate_detail(sub_m: pd.DataFrame, loo_df: pd.DataFrame,
                 country: str, config: str) -> dict:
    detail = {}
    for res_type in ("rel", "causal", "abs"):
        sub_t = sub_m[sub_m["residual_type"] == res_type]
        fdr_pos = sub_t[sub_t["sig_perm_fdr"] & (sub_t["I_real"] > 0)]
        loo_sub = loo_df[
            (loo_df["country"] == country) & (loo_df["config"] == config)
            & (loo_df["residual_type"] == res_type)
        ] if not loo_df.empty else pd.DataFrame()
        detail[res_type] = {
            "fdr_positive_years": sorted(int(y) for y in fdr_pos["year"]),
            "non_2020_count": int(sum(1 for y in fdr_pos["year"] if y != 2020)),
            "graph_sig_fdr_years": int(sub_t["sig_graph_fdr"].sum()),
            "loo_all_pass": bool(loo_sub["loo_pass"].all()) if len(loo_sub) > 0 else None,
        }
    return detail


if __name__ == "__main__":
    main()
