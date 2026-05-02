"""
HERALD — Sector baseline comparison (CPU, no GPU needed).

Run from project root:
    python3 scripts/01_sector_baselines.py

Computes fold-safe sector WMAPE for 4 baselines, using HERALD's own
total predictions as the multiplier. By default it uses the final_gate tag
recorded in reports/FINAL_GATE_SELECTION.txt when those predictions exist,
then falls back to full_best, then core full.

Baselines:
  uniform_1_9         : 1/9 per sector (current no_sector_head reference)
  sector_national_mean: national mean proportion per sector (training years)
  sector_hist_zone    : per-zone mean proportion (training years)
  sector_lag1_zone    : per-zone proportion of previous year

Outputs printed to stdout and saved to reports/sector_baselines_v1.csv
"""

import json
import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT      = Path(__file__).resolve().parents[1]
A10_PATH  = ROOT / "data/processed/side_creations_a10_ze2020_v1.csv"
PRED_DIR  = ROOT / "data/processed"
SPLITS    = ROOT / "metadata/dynamic_stgnn_walk_forward_splits_v1.csv"
OUT_CSV   = ROOT / "reports/sector_baselines_v1.csv"

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
FOLDS       = [2021, 2022, 2023, 2024]


def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask   = np.isfinite(y_true) & np.isfinite(y_pred)
    d = np.abs(y_true[mask]).sum()
    return float(np.abs(y_true[mask] - y_pred[mask]).sum() / d) if d > 0 else np.nan


def resolve_prediction_files(run_tag=None):
    if run_tag:
        files = sorted(PRED_DIR.glob(f"herald_v6_predictions_total_full_{run_tag}_seed_*_v1.csv"))
        if not files:
            sys.exit(f"ERROR: no total prediction files found for run_tag={run_tag}")
        return files, run_tag

    final_gate_file = ROOT / "reports/FINAL_GATE_SELECTION.txt"
    if final_gate_file.exists():
        for line in final_gate_file.read_text().splitlines():
            if line.startswith("FINAL_GATE="):
                gate = line.split("=", 1)[1].strip()
                tag = f"final_gate{gate}"
                files = sorted(PRED_DIR.glob(f"herald_v6_predictions_total_full_{tag}_seed_*_v1.csv"))
                if files:
                    return files, tag

    candidates = [
        ("best", sorted(PRED_DIR.glob("herald_v6_predictions_total_full_best_seed_*_v1.csv"))),
        ("core_full", sorted(PRED_DIR.glob("herald_v6_predictions_total_full_seed_*_v1.csv"))),
    ]
    for label, files in candidates:
        if files:
            return files, label

    sys.exit("ERROR: no HERALD full total prediction files found in data/processed/")


def load_herald_totals(run_tag=None):
    """
    Load total predictions from the selected HERALD full prediction files.
    Returns DataFrame: target_year, ZE2020, y_true, y_pred_mean (mean across seeds).
    """
    files, selected_tag = resolve_prediction_files(run_tag)
    print(f"Loading total predictions from {len(files)} seed files (tag={selected_tag})...")
    dfs = [pd.read_csv(f)[["target_year","ZE2020","y_true","y_pred"]] for f in files]
    merged = dfs[0].rename(columns={"y_pred": "y_pred_0"})
    for i, df in enumerate(dfs[1:], 1):
        merged = merged.merge(df[["target_year","ZE2020","y_pred"]].rename(
            columns={"y_pred": f"y_pred_{i}"}), on=["target_year","ZE2020"])
    pred_cols = [c for c in merged.columns if c.startswith("y_pred_")]
    merged["y_pred_mean"] = merged[pred_cols].mean(axis=1)
    return merged[["target_year","ZE2020","y_true","y_pred_mean"]]


def compute_sector_wmape(a10, totals, test_year, prop_fn, label):
    """
    prop_fn(ze, train_years) → dict {sector: proportion} or None (→ national fallback)
    """
    train_years = [y for y in FOLDS if y < test_year] + list(range(2012, min(FOLDS)))
    train_years  = [y for y in range(2012, test_year)]

    # National fallback: aggregate France-level sector proportions across training years.
    a10_train = a10[a10["target_year"].isin(train_years)].copy()
    a10_train["total"] = a10_train[A10_SECTORS].sum(axis=1)
    a10_valid = a10_train[a10_train["total"] > 0]
    sector_totals = a10_valid[A10_SECTORS].sum(axis=0)
    tot_nat = float(sector_totals.sum())
    nat_props = {s: float(sector_totals[s]) / tot_nat for s in A10_SECTORS} \
        if tot_nat > 0 else {s: 1.0 / 9 for s in A10_SECTORS}

    test_totals = totals[totals["target_year"] == test_year]
    a10_test    = a10[a10["target_year"] == test_year].set_index("ZE2020")

    rows = []
    for _, tr in test_totals.iterrows():
        ze      = int(tr["ZE2020"])
        y_total = float(tr["y_pred_mean"])

        props = prop_fn(ze, train_years, a10, a10_train, nat_props)
        if props is None:
            props = nat_props

        for s in A10_SECTORS:
            y_pred_s = y_total * props.get(s, 1.0 / 9)
            y_true_s = float(a10_test.loc[ze, s]) if ze in a10_test.index else np.nan
            rows.append({"sector": s, "y_true": y_true_s, "y_pred": y_pred_s})

    df   = pd.DataFrame(rows).dropna(subset=["y_true"])
    mean = np.mean([wmape(df[df["sector"]==s]["y_true"],
                         df[df["sector"]==s]["y_pred"]) for s in A10_SECTORS])
    per_sector = {s: wmape(df[df["sector"]==s]["y_true"],
                           df[df["sector"]==s]["y_pred"]) for s in A10_SECTORS}
    return mean, per_sector


# ─── proportion functions ─────────────────────────────────────────────────────

def prop_uniform(ze, train_years, a10, a10_train, nat_props):
    return {s: 1.0 / 9 for s in A10_SECTORS}


def prop_national_mean(ze, train_years, a10, a10_train, nat_props):
    return nat_props


def prop_hist_zone(ze, train_years, a10, a10_train, nat_props):
    sub = a10_train[a10_train["ZE2020"] == ze].copy()
    sub["total"] = sub[A10_SECTORS].sum(axis=1)
    sub = sub[sub["total"] > 0]
    if len(sub) == 0:
        return None
    props = {s: float((sub[s] / sub["total"]).mean()) for s in A10_SECTORS}
    tot   = sum(props.values())
    return {s: v / tot for s, v in props.items()} if tot > 0 else None


def prop_lag1_zone(ze, train_years, a10, a10_train, nat_props):
    prev_year = max(train_years)
    sub = a10[(a10["ZE2020"] == ze) & (a10["target_year"] == prev_year)]
    if len(sub) == 0:
        return None
    total = float(sub[A10_SECTORS].sum(axis=1).values[0])
    if total <= 0:
        return None
    props = {s: float(sub[s].values[0]) / total for s in A10_SECTORS}
    return props


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", default=None,
                        help="Prediction run tag to use, e.g. final_gate2.0. Default: auto.")
    args = parser.parse_args()

    a10    = pd.read_csv(A10_PATH)
    totals = load_herald_totals(args.run_tag)

    baselines = [
        ("uniform_1_9",          prop_uniform),
        ("national_mean",         prop_national_mean),
        ("hist_mean_by_zone",     prop_hist_zone),
        ("lag1_by_zone",          prop_lag1_zone),
    ]

    results = []
    print(f"\n{'Baseline':<25} {'2021':>7} {'2022':>7} {'2023':>7} {'2024':>7} {'MEAN':>7}")
    print("-" * 68)

    for label, fn in baselines:
        fold_means = []
        fold_sectors = []
        for year in FOLDS:
            mean_w, per_s = compute_sector_wmape(a10, totals, year, fn, label)
            fold_means.append(mean_w)
            fold_sectors.append(per_s)

        overall = float(np.mean(fold_means))
        print(f"{label:<25} {fold_means[0]:7.4f} {fold_means[1]:7.4f} "
              f"{fold_means[2]:7.4f} {fold_means[3]:7.4f} {overall:7.4f}")

        for fi, year in enumerate(FOLDS):
            for s in A10_SECTORS:
                results.append({
                    "baseline":    label,
                    "target_year": year,
                    "sector":      s,
                    "wmape":       fold_sectors[fi][s],
                })

    # Per-sector breakdown (mean across folds)
    df_res = pd.DataFrame(results)
    print("\nPer-sector WMAPE (mean across 4 folds):")
    pivot = df_res.groupby(["baseline","sector"])["wmape"].mean().unstack("sector")
    print(pivot.round(4).to_string())

    # Also load HERALD sector WMAPE from JSON for comparison
    json_path = ROOT / "reports/herald_v6_metrics_v1.json"
    if json_path.exists():
        metrics = json.loads(json_path.read_text())
        herald_sector = [v["sector_wmape_mean"] for k, v in metrics.items()
                         if v.get("ablation") == "full" and v.get("run_tag","") == "best"
                         and v.get("sector_wmape_mean") is not None]
        if herald_sector:
            print(f"\nHERALD sector head (best, {len(herald_sector)} seeds): "
                  f"mean={np.mean(herald_sector):.4f}  std={np.std(herald_sector):.4f}")
        herald_core = [v["sector_wmape_mean"] for k, v in metrics.items()
                       if v.get("ablation") == "full" and v.get("run_tag","") == ""
                       and v.get("sector_wmape_mean") is not None]
        if herald_core:
            print(f"HERALD sector head (core, {len(herald_core)} seeds): "
                  f"mean={np.mean(herald_core):.4f}  std={np.std(herald_core):.4f}")

    df_res.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
