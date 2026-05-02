"""
HERALD — Official Ridge AR baseline via the exact HERALD pipeline (CPU, no GPU).

Run from project root:
    python3 scripts/02_ridge_ar_official.py

Uses the same fit_ridge_ar(train_df, test_df) call used inside
make_sequences() in train_herald_v6.py. Resolves the 0.0668 vs 0.0581
discrepancy by producing a single authoritative number.

Also computes Spatial Ridge AR (fixed A_mob, A_geo, combo) for comparison,
using the same pipeline but with spatial lags added to Ridge features.

Outputs printed to stdout, saved to reports/ridge_ar_official_v1.json, and
mirrored into reports/herald_v6_metrics_v1.json under ridge_ar_official.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/data"))

# Import HERALD pipeline functions
from train_herald_v6 import (
    load_adjacency, build_quarterly_tensor, build_annual_tensor,
    build_sector_props_target, build_regime_vectors,
    fit_ridge_ar, fit_ridge_expanding, wmape,
    PANEL_PATH, SPLITS_PATH, GEO_ADJ_PATH, MOB_ADJ_PATH,
    NODE_IDX_PATH, SIDE_A10_PATH, TARGET_COL,
)

OUT_JSON = ROOT / "reports/ridge_ar_official_v1.json"
METRICS_JSON = ROOT / "reports/herald_v6_metrics_v1.json"
SPAT_COLS = ["side_lag_1", "growth_1y"]   # vars to spatially aggregate (forecast-safe)


def row_normalize(A):
    s = A.sum(axis=1, keepdims=True)
    return np.divide(A, s, out=np.zeros_like(A), where=s > 0)


def compute_spatial_lag(panel, zones_sorted, year, A_norm, cols):
    """
    Forecast-safe spatial lag: A @ X_{year-1}.
    Uses previous year's values aggregated through fixed adjacency.
    """
    prev = panel[panel["target_year"] == year - 1]
    zone_to_i = {z: i for i, z in enumerate(zones_sorted)}
    N  = len(zones_sorted)
    X  = np.full((N, len(cols)), np.nan, dtype=np.float32)
    for row in prev.itertuples(index=False):
        i = zone_to_i.get(int(row.ZE2020))
        if i is not None:
            X[i] = [float(getattr(row, c, np.nan)) for c in cols]
    # fill NaN with column median
    for j in range(X.shape[1]):
        col = X[:, j]
        med = float(np.nanmedian(col)) if np.any(np.isfinite(col)) else 0.0
        col[~np.isfinite(col)] = med
    return (A_norm @ X).astype(np.float32)


def run_ridge_spatial(panel, zones_sorted, years_sorted,
                      train_max, target_year, A_norm, cols_base):
    """
    Ridge AR with spatial lag appended.
    Uses exact same walk-forward split as HERALD.
    """
    zone_to_i = {z: i for i, z in enumerate(zones_sorted)}
    year_to_i = {y: i for i, y in enumerate(years_sorted)}

    train_df  = panel[panel["target_year"] <= train_max].copy()
    test_df   = panel[panel["target_year"] == target_year].copy()

    # Spatial lags for each year in train
    def get_X_with_sl(df, year):
        base_cols = [c for c in cols_base if c in df.columns]
        X_base = df[base_cols].values.astype(float)
        sl     = compute_spatial_lag(panel, zones_sorted, year, A_norm, SPAT_COLS)
        # align sl to df rows
        sl_aligned = np.full((len(df), len(SPAT_COLS)), np.nan, dtype=np.float32)
        for k, row in enumerate(df.itertuples(index=False)):
            i = zone_to_i.get(int(row.ZE2020))
            if i is not None:
                sl_aligned[k] = sl[i]
        return np.concatenate([X_base, sl_aligned], axis=1)

    # Build train set year by year to get correct spatial lags
    X_parts, y_parts = [], []
    for yr in sorted(train_df["target_year"].unique()):
        sub = train_df[train_df["target_year"] == yr]
        X_parts.append(get_X_with_sl(sub, yr))
        y_parts.append(sub[TARGET_COL].values.astype(float))

    X_tr_full = np.vstack(X_parts)
    y_tr_full = np.concatenate(y_parts)
    X_te      = get_X_with_sl(test_df, target_year)
    y_te      = test_df[TARGET_COL].values.astype(float)

    mask_tr = np.isfinite(y_tr_full) & np.all(np.isfinite(X_tr_full), axis=1)
    mask_te = np.isfinite(y_te)

    m = Pipeline([("imp", SimpleImputer(strategy="median")),
                  ("sc",  StandardScaler()),
                  ("r",   Ridge(alpha=1.0))])
    m.fit(X_tr_full[mask_tr], y_tr_full[mask_tr])
    pred = np.maximum(m.predict(X_te), 0.0)
    return wmape(y_te[mask_te], pred[mask_te])


def main():
    print("Loading data...")
    panel    = pd.read_csv(PANEL_PATH)
    splits   = pd.read_csv(SPLITS_PATH)
    node_idx = pd.read_csv(NODE_IDX_PATH)

    zones_sorted = sorted(node_idx["ze2020"].astype(int).tolist())
    years_sorted = sorted(panel["target_year"].unique().tolist())

    A_geo   = load_adjacency(GEO_ADJ_PATH)
    A_mob   = load_adjacency(MOB_ADJ_PATH)
    A_combo = row_normalize(0.5 * A_geo + 0.5 * A_mob)

    cols_base = ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]

    results = {}

    # ── 1. Official Ridge AR (HERALD pipeline) ────────────────────────────────
    print("\n── Official Ridge AR (HERALD make_sequences pipeline) ──")
    ridge_folds = []
    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max   = int(split["train_years_max"])

        train_df = panel[panel["target_year"] <= train_max].copy()
        test_df  = panel[panel["target_year"] == target_year].copy()

        _, ridge_preds = fit_ridge_expanding(train_df, target_year)
        # test_ridge: same as used in neural training
        ridge_test = fit_ridge_ar(train_df, test_df)

        y_te   = test_df[TARGET_COL].values.astype(float)
        mask_te = np.isfinite(y_te) & np.isfinite(ridge_test)
        w = wmape(y_te[mask_te], ridge_test[mask_te])
        ridge_folds.append(w)
        print(f"  fold {target_year}: WMAPE = {w:.6f}")

    ridge_mean = float(np.mean(ridge_folds))
    print(f"  MEAN: {ridge_mean:.6f}  (hardcoded in script was 0.0668)")
    results["ridge_ar_official"] = {"folds": ridge_folds, "mean": ridge_mean}

    # ── 2. Spatial Ridge AR (fixed adjacencies) ───────────────────────────────
    for adj_label, A_norm in [("A_mob", A_mob), ("A_geo", A_geo), ("A_combo", A_combo)]:
        print(f"\n── Spatial Ridge AR + {adj_label} ──")
        sp_folds = []
        for _, split in splits.iterrows():
            target_year = int(split["target_year"])
            train_max   = int(split["train_years_max"])
            w = run_ridge_spatial(panel, zones_sorted, years_sorted,
                                  train_max, target_year, A_norm, cols_base)
            sp_folds.append(w)
            print(f"  fold {target_year}: WMAPE = {w:.6f}")
        sp_mean = float(np.mean(sp_folds))
        print(f"  MEAN: {sp_mean:.6f}  delta_vs_ridge={sp_mean - ridge_mean:+.6f}")
        results[f"spatial_ridge_{adj_label}"] = {"folds": sp_folds, "mean": sp_mean}

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("SUMMARY")
    print(f"{'Model':<30} {'2021':>7} {'2022':>7} {'2023':>7} {'2024':>7} {'MEAN':>7}")
    print("-"*60)
    base_folds = results["ridge_ar_official"]["folds"]
    for k, v in results.items():
        folds = v["folds"]
        mean  = v["mean"]
        wins  = sum(f < b for f, b in zip(folds, base_folds)) if k != "ridge_ar_official" else "-"
        print(f"{k:<30} {folds[0]:7.4f} {folds[1]:7.4f} {folds[2]:7.4f} {folds[3]:7.4f} {mean:7.4f}  {wins}")

    print(f"\nUpdate train_herald_v6.py line ~780:")
    print(f"  ridge_ar = {ridge_mean:.4f}  # was 0.0668")

    OUT_JSON.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {OUT_JSON}")

    metrics = {}
    if METRICS_JSON.exists():
        metrics = json.loads(METRICS_JSON.read_text())
    metrics["ridge_ar_official"] = {
        "ablation": "ridge_ar_only",
        "seed": None,
        "run_tag": "official",
        "total_wmape_mean": round(ridge_mean, 6),
        "per_year_total": {
            int(year): round(float(w), 6)
            for year, w in zip([2021, 2022, 2023, 2024], ridge_folds)
        },
        "source": "scripts/02_ridge_ar_official.py",
    }
    METRICS_JSON.write_text(json.dumps(metrics, indent=2))
    print(f"Updated: {METRICS_JSON} [ridge_ar_official]")


if __name__ == "__main__":
    main()
