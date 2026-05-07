"""
A10 sector baselines for HERALD V7 acceptance criteria.

Computes sector WMAPE for two priors that V7 must beat to claim a sector
contribution:

  - sector_lag1_by_zone : sector proportions in t-1 (per zone), forward-filled
  - sector_hist_mean_by_zone : mean sector proportions over training years (per zone)

For each split (target_year), we evaluate both decompositions against the
true sectoral panel using the OBSERVED total per zone as the multiplier
(so we isolate the decomposition error from any total-prediction error).

Outputs a JSON file structured like the other HERALD metrics files.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import train_herald_v6 as base


def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum(np.abs(y_true))
    if denom <= 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom)


def build_sector_props_panel(a10_panel, zones_sorted, years_sorted):
    """Return (T, N, S) tensor of sector proportions (NaN where missing)."""
    n_zones = len(zones_sorted)
    n_years = len(years_sorted)
    n_sec = len(base.A10_SECTORS)
    out = np.full((n_years, n_zones, n_sec), np.nan, dtype=np.float32)
    year_idx = {y: i for i, y in enumerate(years_sorted)}
    zone_idx = {z: i for i, z in enumerate(zones_sorted)}
    for row in a10_panel.itertuples(index=False):
        y = int(row.target_year)
        z = int(row.ZE2020)
        if y not in year_idx or z not in zone_idx:
            continue
        ti, zi = year_idx[y], zone_idx[z]
        total = sum(getattr(row, s) for s in base.A10_SECTORS)
        if not np.isfinite(total) or total <= 0:
            continue
        for si, s in enumerate(base.A10_SECTORS):
            out[ti, zi, si] = float(getattr(row, s)) / total
    return out


def lag1_props(props, year_idx_target, year_idx_train_max):
    """Return per-zone lag-1 proportions to use at target_year.

    For each zone, take the latest finite proportion in years <= target_year - 1.
    Fall back to uniform 1/S if zone has no historical record.
    """
    n_sec = props.shape[-1]
    last_valid = np.full(props.shape[1:], np.nan, dtype=np.float32)
    for ti in range(year_idx_target):  # strictly before target
        valid = np.isfinite(props[ti]).all(axis=-1)
        last_valid[valid] = props[ti, valid]
    fallback = np.full_like(last_valid, 1.0 / n_sec)
    out = np.where(np.isfinite(last_valid), last_valid, fallback)
    return out.astype(np.float32)


def hist_mean_props(props, year_idx_train_max):
    """Per-zone mean of sector proportions over training years (<= train_max)."""
    n_sec = props.shape[-1]
    train = props[: year_idx_train_max + 1]  # inclusive
    mask = np.isfinite(train).all(axis=-1, keepdims=True).astype(np.float32)
    train_filled = np.where(np.isfinite(train), train, 0.0)
    num = (train_filled * mask).sum(axis=0)
    den = mask.sum(axis=0)
    den = np.where(den < 1.0, 1.0, den)
    avg = num / den
    valid = np.isfinite(avg).all(axis=-1, keepdims=True)
    fallback = np.full_like(avg, 1.0 / n_sec)
    out = np.where(valid, avg, fallback)
    out = out / np.clip(out.sum(axis=-1, keepdims=True), 1e-8, None)
    return out.astype(np.float32)


def compute_baseline(method, panel, a10_panel, splits, zones_sorted, years_sorted, props):
    rows = []
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}
    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    n_sec = len(base.A10_SECTORS)
    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max = int(split["train_years_max"])
        if target_year not in year_to_idx:
            continue
        ti = year_to_idx[target_year]
        ti_train_max = year_to_idx[train_max]
        if method == "sector_lag1_by_zone":
            decomp = lag1_props(props, ti, ti_train_max)
        elif method == "sector_hist_mean_by_zone":
            decomp = hist_mean_props(props, ti_train_max)
        else:
            raise ValueError(method)

        a10_test = a10_panel[a10_panel["target_year"] == target_year].set_index("ZE2020")
        if a10_test.empty:
            continue
        for ze in zones_sorted:
            if ze not in a10_test.index:
                continue
            zi = zone_to_idx[ze]
            row = a10_test.loc[ze]
            total_obs = sum(float(row[s]) for s in base.A10_SECTORS if np.isfinite(row[s]))
            for si, s in enumerate(base.A10_SECTORS):
                y_true_s = float(row[s]) if np.isfinite(row[s]) else np.nan
                y_pred_s = float(total_obs * decomp[zi, si])
                rows.append({
                    "method": method,
                    "target_year": target_year,
                    "ZE2020": int(ze),
                    "sector": s,
                    "y_true_sector": y_true_s,
                    "y_pred_sector": y_pred_s,
                    "y_pred_total_used": float(total_obs),
                    "prop_pred": float(decomp[zi, si]),
                })
    return rows


def aggregate(rows, method):
    df = pd.DataFrame(rows).dropna(subset=["y_true_sector"])
    if df.empty:
        return {}
    sector_wmape = {
        s: round(wmape(df.loc[df["sector"] == s, "y_true_sector"],
                       df.loc[df["sector"] == s, "y_pred_sector"]), 6)
        for s in base.A10_SECTORS if (df["sector"] == s).any()
    }
    per_year = {
        int(y): round(wmape(g["y_true_sector"], g["y_pred_sector"]), 6)
        for y, g in df.groupby("target_year")
    }
    return {
        "method": method,
        "sector_wmape": sector_wmape,
        "sector_wmape_mean": round(float(np.mean(list(sector_wmape.values()))), 6),
        "per_year_sector_wmape": per_year,
        "n_rows": int(len(df)),
    }


def main():
    parser = argparse.ArgumentParser(description="A10 sector baselines (lag1, hist_mean)")
    parser.add_argument("--panel-path", type=Path, default=base.PANEL_PATH)
    parser.add_argument("--splits-path", type=Path, default=base.SPLITS_PATH)
    parser.add_argument("--side-a10-path", type=Path, default=base.SIDE_A10_PATH)
    parser.add_argument("--metrics-path", type=Path, required=True)
    parser.add_argument("--predictions-out", type=Path, default=None)
    parser.add_argument("--run-tag", default="")
    args = parser.parse_args()

    base.SIDE_A10_PATH = args.side_a10_path
    args.metrics_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading panel and splits...")
    panel = pd.read_csv(args.panel_path).sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    splits = pd.read_csv(args.splits_path)
    zones_sorted = sorted(panel["ZE2020"].unique())
    years_sorted = sorted(panel["target_year"].unique())

    print("Loading A10 sectoral panel...")
    a10_panel = base.load_or_build_side_a10_panel(zones_sorted)

    print("Building sector props tensor...")
    props = build_sector_props_panel(a10_panel, zones_sorted, years_sorted)

    out = {}
    all_rows = []
    for method in ("sector_lag1_by_zone", "sector_hist_mean_by_zone"):
        print(f"  Method: {method}")
        rows = compute_baseline(method, panel, a10_panel, splits, zones_sorted, years_sorted, props)
        all_rows.extend(rows)
        agg = aggregate(rows, method)
        run_key = f"{method}{('_' + args.run_tag) if args.run_tag else ''}"
        out[run_key] = agg
        print(f"    sector WMAPE mean: {agg.get('sector_wmape_mean')}")

    args.metrics_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    if args.predictions_out is not None:
        args.predictions_out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(all_rows).to_csv(args.predictions_out, index=False)
    print(f"\nWrote: {args.metrics_path}")
    if args.predictions_out is not None:
        print(f"Wrote: {args.predictions_out}")


if __name__ == "__main__":
    main()
