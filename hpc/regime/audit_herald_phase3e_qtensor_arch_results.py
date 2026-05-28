#!/usr/bin/env python3
"""Results audit for HERALD Phase 3E q_tensor architecture selection battery.

240 runs (12 configs × 20 seeds). Evaluates:
  - Summary table: mean/std WMAPE, 2021, 2025, sector/A10
  - Paired Wilcoxon comparisons (20 seeds):
      Q0 vs Q1   — does q_tensor contribute at all?
      Q0 vs Q3   — does ZE identity matter (spatial falsification)?
      Q4 vs Q5   — which channel is stronger?
      Q6 vs Q0   — does lag1 beat contemporaneous?
      Q7 vs Q4   — does lag1 improve effectifs?
      Q7 vs Q8   — effectifs_lag1 vs masse_lag1
      Q7 vs Q10  — ZE-local test for effectifs_lag1
      Q6 vs Q11  — ZE-local test for lag1
      Q7 vs Q12  — A10 guard cost for effectifs_lag1
  - Per-year WMAPE table
  - Guard rail: WMAPE_2025 not degraded >0.003 vs Q0_real

Usage:
  python3 hpc/regime/audit_herald_phase3e_qtensor_arch_results.py \\
      --root hpc_results/herald_regime_phase3e_qtensor_arch_<STAMP>_r1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

GUARD_2025_MARGIN = 0.003
WILCOXON_ALPHA = 0.05
EXPECTED_SEEDS = 20
EXPECTED_CONFIGS = 12


def load_metrics(root: Path) -> dict:
    metrics = {}
    for p in sorted((root / "reports" / "per_run").glob("*.json")):
        try:
            payload = json.loads(p.read_text())
            for run_key, result in payload.items():
                metrics[run_key] = result
        except Exception as e:
            print(f"  Warning: failed to load {p}: {e}")
    return metrics


def extract_wmapes(metrics: dict) -> pd.DataFrame:
    rows = []
    for run_key, m in metrics.items():
        label = m.get("run_tag", run_key).replace("regime_", "")
        per_year = m.get("per_year_total", {})
        row = {
            "label": label,
            "seed": m.get("seed", -1),
            "wmape_mean": m.get("total_wmape_mean"),
            "wmape_2025": m.get("total_wmape_2025"),
            "sector_wmape": m.get("sector_wmape_mean"),
            "q_tensor_policy": m.get("quarterly_tensor_policy", "unknown"),
        }
        for yr, w in per_year.items():
            row[f"wmape_{yr}"] = w
        rows.append(row)
    return pd.DataFrame(rows)


def wilcoxon_paired(a: np.ndarray, b: np.ndarray):
    if not HAS_SCIPY or len(a) < 2:
        return None, None
    d = a - b
    if np.all(d == 0):
        return 1.0, 0.0
    try:
        stat, pval = wilcoxon(d, alternative="less")
        return float(pval), float(stat)
    except Exception:
        return None, None


def sig(pval):
    if pval is None:
        return "?"
    return "✓ p<0.05" if pval < WILCOXON_ALPHA else "✗ n.s."


def get_vals(df, key):
    mask = df["label"].str.contains(key, regex=False)
    if mask.sum() == 0:
        return None
    return df.loc[mask, "wmape_mean"].values


def audit_results(root: Path) -> None:
    print(f"\n{'='*70}")
    print(f" HERALD Phase 3E — q_tensor Architecture Selection Audit")
    print(f" Root: {root}")
    print(f"{'='*70}")

    if not root.exists():
        print(f"\n  ✗ Root not found: {root}")
        return

    metrics = load_metrics(root)
    if not metrics:
        print(f"\n  ✗ No metrics found in {root}/reports/per_run/")
        return

    df = extract_wmapes(metrics)
    n_runs = len(df)
    n_labels = df["label"].nunique()
    print(f"\n  Loaded {n_runs} runs, {n_labels} unique labels")

    # Integrity check
    if n_runs != EXPECTED_SEEDS * EXPECTED_CONFIGS:
        print(f"  ⚠ Expected {EXPECTED_SEEDS * EXPECTED_CONFIGS} runs, "
              f"got {n_runs} ({n_labels} configs × {n_runs // max(n_labels,1)} seeds avg)")
    else:
        print(f"  ✓ Integrity OK: {n_runs}/{EXPECTED_SEEDS * EXPECTED_CONFIGS}")

    year_cols = sorted([c for c in df.columns if c.startswith("wmape_20") and c != "wmape_2025"])

    # Aggregate
    agg_cols = {
        "n_seeds": ("seed", "count"),
        "wmape_mean_mu": ("wmape_mean", "mean"),
        "wmape_mean_sd": ("wmape_mean", "std"),
        "wmape_2025_mu": ("wmape_2025", "mean"),
        "wmape_2025_sd": ("wmape_2025", "std"),
        "sector_wmape_mu": ("sector_wmape", "mean"),
    }
    summary = df.groupby("label").agg(**agg_cols).reset_index()
    for yr_col in year_cols:
        if yr_col in df.columns:
            agg = df.groupby("label")[yr_col].agg(["mean", "std"]).reset_index()
            agg.columns = ["label", f"{yr_col}_mu", f"{yr_col}_sd"]
            summary = summary.merge(agg, on="label", how="left")

    config_order = [
        "Q0_real", "Q1_zero", "Q3_spatial_perm", "Q4_effectifs_only",
        "Q5_masse_only", "Q6_lag1", "Q7_effectifs_lag1", "Q8_masse_lag1",
        "Q9_lag2", "Q10_effectifs_spatial_perm", "Q11_lag1_spatial_perm",
        "Q12_effectifs_lag1_a10guard",
    ]

    def sort_key(lbl):
        for i, c in enumerate(config_order):
            if c in lbl:
                return i
        return 99

    summary["_order"] = summary["label"].apply(sort_key)
    summary = summary.sort_values("_order").reset_index(drop=True)

    print(f"\n{'='*70}")
    print(f" Summary table (n={EXPECTED_SEEDS} seeds per config)")
    print(f"{'='*70}")
    hdr = f"  {'Config':<40} {'N':>3} {'Mean WMAPE':>12} {'±std':>8} {'2021':>8} {'2025':>8} {'Sector':>8}"
    print(f"\n{hdr}")
    print(f"  {'-'*40} {'-'*3} {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for _, row in summary.iterrows():
        label = row["label"]
        # Extract short label (Q0_real etc.)
        short = label
        for c in config_order:
            if c in label:
                short = c
                break
        w2021 = row.get("wmape_2021_mu", np.nan)
        sect = row.get("sector_wmape_mu", np.nan)
        sd = row["wmape_mean_sd"] if pd.notna(row["wmape_mean_sd"]) else 0
        print(f"  {short:<40} {int(row['n_seeds']):>3} "
              f"{row['wmape_mean_mu']:>12.6f} "
              f"{sd:>8.6f} "
              f"{w2021:>8.5f} "
              f"{row['wmape_2025_mu']:>8.5f} "
              f"{sect:>8.5f}")

    # Reference: Q0_real
    q0_vals = get_vals(df, "Q0_real")
    if q0_vals is None:
        print("\n  ⚠ Q0_real not found")
        return
    q0_2025 = df.loc[df["label"].str.contains("Q0_real"), "wmape_2025"].values
    print(f"\n  Q0_real: mean={q0_vals.mean():.6f}±{q0_vals.std():.6f}, "
          f"2025={q0_2025.mean():.6f}, n={len(q0_vals)}")

    print(f"\n{'='*70}")
    print(f" Paired comparisons (Wilcoxon one-sided, A<B means A better)")
    print(f"{'='*70}")

    comparisons = [
        ("Q0_real",  "Q1_zero",                 "q_tensor contribution:  Q0_real vs Q1_zero"),
        ("Q0_real",  "Q3_spatial_perm",          "ZE identity (full):     Q0_real vs Q3_spatial_perm"),
        ("Q4_effectifs_only", "Q5_masse_only",   "Channel:               Q4_effectifs vs Q5_masse"),
        ("Q6_lag1",  "Q0_real",                  "Lag1 benefit:          Q6_lag1 vs Q0_real"),
        ("Q7_effectifs_lag1", "Q4_effectifs_only","Lag1 on effectifs:     Q7_eff_lag1 vs Q4_eff_only"),
        ("Q7_effectifs_lag1", "Q8_masse_lag1",   "Channel at lag1:       Q7_eff_lag1 vs Q8_masse_lag1"),
        ("Q7_effectifs_lag1", "Q10_effectifs_spatial_perm", "ZE identity (eff_lag1): Q7 vs Q10"),
        ("Q6_lag1",  "Q11_lag1_spatial_perm",    "ZE identity (lag1):    Q6_lag1 vs Q11_lag1_sperm"),
        ("Q7_effectifs_lag1", "Q12_effectifs_lag1_a10guard", "A10 guard cost:  Q7 vs Q12"),
    ]

    for a_key, b_key, description in comparisons:
        a_vals = get_vals(df, a_key)
        b_vals = get_vals(df, b_key)
        if a_vals is None or b_vals is None:
            print(f"\n  ⚠ {description}: missing data ({a_key}={a_vals is not None}, {b_key}={b_vals is not None})")
            continue

        # Align by seed
        df_a = df[df["label"].str.contains(a_key, regex=False)][["seed", "wmape_mean", "wmape_2025"]].sort_values("seed")
        df_b = df[df["label"].str.contains(b_key, regex=False)][["seed", "wmape_mean", "wmape_2025"]].sort_values("seed")
        merged = df_a.merge(df_b, on="seed", suffixes=("_a", "_b"))
        if len(merged) < 2:
            print(f"\n  ⚠ {description}: insufficient paired data ({len(merged)} seeds)")
            continue

        a_m = merged["wmape_mean_a"].values
        b_m = merged["wmape_mean_b"].values
        wins_a = int((a_m < b_m).sum())
        pval, _ = wilcoxon_paired(a_m, b_m)
        delta = a_m.mean() - b_m.mean()
        direction = "A<B ✓" if delta < 0 else "A≥B"

        # 2025 guard vs Q0
        a_2025 = merged["wmape_2025_a"].values.mean()
        q0_2025_mean = q0_2025.mean()
        guard = a_2025 - q0_2025_mean
        guard_str = f"Δ2025_vs_Q0={guard:+.4f} {'✓' if guard <= GUARD_2025_MARGIN else '✗'}"

        print(f"\n  {description}:")
        print(f"    A={a_m.mean():.6f}  B={b_m.mean():.6f}  Δ={delta:+.6f}  {direction}")
        pval_str = f"{pval:.4f}" if pval is not None else "?"
        print(f"    wins_A={wins_a}/{len(merged)}  p={pval_str}  {sig(pval)}  |  {guard_str}")

    print(f"\n{'='*70}")
    print(f" Per-year WMAPE (mean across seeds)")
    print(f"{'='*70}")
    year_mu_cols = [c for c in summary.columns if c.endswith("_mu") and c.startswith("wmape_20")]
    if year_mu_cols:
        year_years = sorted([c.replace("wmape_", "").replace("_mu", "") for c in year_mu_cols])
        hdr_yr = f"  {'Config':<40} " + "  ".join(f"{y:>6}" for y in year_years)
        print(f"\n{hdr_yr}")
        print(f"  {'-'*40} " + "  ".join(f"{'------':>6}" for _ in year_years))
        for _, row in summary.iterrows():
            short = row["label"]
            for c in config_order:
                if c in short:
                    short = c
                    break
            vals = [f"{row.get(f'wmape_{y}_mu', np.nan):>6.4f}" for y in year_years]
            print(f"  {short:<40} " + "  ".join(vals))

    print(f"\n{'='*70}")
    print(f" Ranking by mean WMAPE")
    print(f"{'='*70}")
    ranked = summary.sort_values("wmape_mean_mu").head(6)
    print()
    for rank, (_, row) in enumerate(ranked.iterrows(), 1):
        short = row["label"]
        for c in config_order:
            if c in short:
                short = c
                break
        print(f"  #{rank}  {short:<40} mean={row['wmape_mean_mu']:.6f}  2025={row['wmape_2025_mu']:.6f}")

    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="OUT_ROOT from the Phase 3E run")
    args = parser.parse_args()
    audit_results(args.root)


if __name__ == "__main__":
    main()
