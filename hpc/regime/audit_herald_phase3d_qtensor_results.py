#!/usr/bin/env python3
"""Results audit for HERALD Phase 3D q_tensor ablation battery.

Reads aggregated results from the Phase 3D OUT_ROOT and evaluates:
  - Total contribution: Q0_real vs Q1_zero (Wilcoxon)
  - Spatial falsification: Q0_real vs Q3_spatial_perm
  - Channel split: Q0 vs Q4_effectifs_only vs Q5_masse_only
  - Temporal recency: Q0_real vs Q6_lag1
  - Guard rail: WMAPE_2025 not degraded by >0.003 vs Q0_real
  - Per-year WMAPE table

Note: Q2 (temporal_perm) was excluded from this battery because a global
year permutation applied at build_quarterly_tensor time is not fold-safe —
it can leak future years into earlier folds. A fold-safe temporal
falsification requires permuting only within years <= train_max per fold,
which is not implemented in the current build_quarterly_tensor contract.

Usage:
  python3 hpc/regime/audit_herald_phase3d_qtensor_results.py \\
      --root hpc_results/herald_regime_phase3d_qtensor_<STAMP>_r1
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

BASELINE_WMAPE_MEAN = 0.020233   # L5_trainopt Phase 2R reference
GUARD_2025_MARGIN = 0.003
WILCOXON_ALPHA = 0.05


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
            "q_zeroed": m.get("quarterly_tensor_zeroed", None),
            "q_channels": str(m.get("q_tensor_channels_active", [])),
        }
        for yr, w in per_year.items():
            row[f"wmape_{yr}"] = w
        rows.append(row)
    return pd.DataFrame(rows)


def wilcoxon_paired(a: np.ndarray, b: np.ndarray):
    if not HAS_SCIPY:
        return None, None
    d = a - b
    if np.all(d == 0):
        return 1.0, 0.0
    try:
        stat, pval = wilcoxon(d, alternative="less")
        return float(pval), float(stat)
    except Exception:
        return None, None


def fmt_verdict(pval, wins, n):
    if pval is None:
        return f"  {wins}/{n} wins, scipy unavailable"
    sig = "✓ p<0.05" if pval < WILCOXON_ALPHA else "✗ n.s."
    return f"  {wins}/{n} wins, p={pval:.4f} — {sig}"


def audit_results(root: Path) -> None:
    print(f"\n{'='*65}")
    print(f" HERALD Phase 3D — q_tensor Ablation Audit")
    print(f" Root: {root}")
    print(f"{'='*65}")

    if not root.exists():
        print(f"\n  ✗ Root not found: {root}")
        return

    metrics = load_metrics(root)
    if not metrics:
        print(f"\n  ✗ No metrics found in {root}/reports/per_run/")
        return

    df = extract_wmapes(metrics)
    print(f"\n  Loaded {len(df)} runs, {df['label'].nunique()} unique labels")

    year_cols = sorted([
        c for c in df.columns
        if c.startswith("wmape_20") and c != "wmape_2025"
    ])

    # Aggregate by label
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
            yr_agg = df.groupby("label")[yr_col].agg(["mean", "std"]).reset_index()
            yr_agg.columns = ["label", f"{yr_col}_mu", f"{yr_col}_sd"]
            summary = summary.merge(yr_agg, on="label", how="left")

    # Config ordering for display
    config_order = ["Q0_real", "Q1_zero", "Q2_temporal_perm", "Q3_spatial_perm",
                    "Q4_effectifs_only", "Q5_masse_only", "Q6_lag1"]

    def sort_key(lbl):
        for i, c in enumerate(config_order):
            if c in lbl:
                return i
        return 99

    summary["_order"] = summary["label"].apply(sort_key)
    summary = summary.sort_values("_order").reset_index(drop=True)

    print(f"\n{'='*65}")
    print(f" Summary table")
    print(f"{'='*65}")
    print(f"\n  {'Label':<50} {'N':<4} {'Mean WMAPE':<14} {'WMAPE 2021':<14} {'WMAPE 2025':<12} {'Sector'}")
    print(f"  {'-'*50} {'-'*4} {'-'*14} {'-'*14} {'-'*12} {'-'*8}")
    for _, row in summary.iterrows():
        w2021 = f"{row['wmape_2021_mu']:.6f}" if "wmape_2021_mu" in row.index and pd.notna(row.get("wmape_2021_mu")) else "—"
        sect = f"{row['sector_wmape_mu']:.5f}" if pd.notna(row.get("sector_wmape_mu")) else "—"
        sd = row["wmape_mean_sd"] if pd.notna(row["wmape_mean_sd"]) else 0
        print(f"  {row['label']:<50} {int(row['n_seeds']):<4} "
              f"{row['wmape_mean_mu']:.6f}±{sd:.6f}  "
              f"{w2021:<14} "
              f"{row['wmape_2025_mu']:.6f}     "
              f"{sect}")

    # Get Q0_real seeds as reference
    q0_mask = df["label"].str.contains("Q0_real")
    if q0_mask.sum() == 0:
        print("\n  ⚠ Q0_real not found — cannot compute comparisons")
        return

    q0_means = df.loc[q0_mask, "wmape_mean"].values
    q0_2025 = df.loc[q0_mask, "wmape_2025"].values
    q0_mean_mu = q0_means.mean()
    print(f"\n  Q0_real reference: mean={q0_mean_mu:.6f}±{q0_means.std():.6f}, "
          f"2025={q0_2025.mean():.6f}")

    print(f"\n{'='*65}")
    print(f" Primary comparisons (all vs Q0_real, one-sided Wilcoxon)")
    print(f"{'='*65}")

    comparisons = [
        ("Q1_zero",          "Total q_tensor contribution"),
        ("Q3_spatial_perm",  "Spatial content (ZE identity)"),
        ("Q4_effectifs_only","Channel: effectifs only"),
        ("Q5_masse_only",    "Channel: masse_salariale only"),
        ("Q6_lag1",          "Temporal recency (lag1 shift)"),
    ]

    guard_header_done = False
    for cfg_key, description in comparisons:
        mask = df["label"].str.contains(cfg_key)
        if mask.sum() == 0:
            print(f"\n  ⚠ {cfg_key} not found")
            continue

        vals = df.loc[mask, "wmape_mean"].values
        wins = int((q0_means < vals).sum())
        pval, _ = wilcoxon_paired(q0_means, vals)
        delta = q0_means.mean() - vals.mean()
        verdict_str = fmt_verdict(pval, wins, len(q0_means))

        direction = "✓ Q0 better" if delta < 0 else "Q0 worse or equal"
        print(f"\n  {description} ({cfg_key}):")
        print(f"    Q0={q0_means.mean():.6f} vs {cfg_key}={vals.mean():.6f}, Δ={delta:+.6f} ({direction})")
        print(f"   {verdict_str}")

        # Guard 2025
        vals_2025 = df.loc[mask, "wmape_2025"].values
        q0_2025_mean = q0_2025.mean()
        real_2025_mean = vals_2025.mean()
        deg = real_2025_mean - q0_2025_mean
        guard_ok = deg <= GUARD_2025_MARGIN
        print(f"    Guard 2025: {cfg_key}={real_2025_mean:.6f}, Q0={q0_2025_mean:.6f}, "
              f"Δ={deg:+.6f} — {'✓ OK' if guard_ok else '✗ VIOLATED'}")

    print(f"\n{'='*65}")
    print(f" Interpretation")
    print(f"{'='*65}")

    # Quick automated interpretation
    def get_pval(cfg_key):
        mask = df["label"].str.contains(cfg_key)
        if mask.sum() == 0:
            return None
        pval, _ = wilcoxon_paired(q0_means, df.loc[mask, "wmape_mean"].values)
        return pval

    p_zero = get_pval("Q1_zero")
    p_sperm = get_pval("Q3_spatial_perm")
    p_lag1 = get_pval("Q6_lag1")

    print()
    if p_zero is not None:
        if p_zero < WILCOXON_ALPHA:
            print("  ✓ Q0 beats Q1_zero (p<0.05) → q_tensor has measurable contribution")
        else:
            print("  ✗ Q0 does NOT beat Q1_zero → q_tensor contribution unclear")

    if p_sperm is not None:
        if p_sperm < WILCOXON_ALPHA:
            print("  ✓ Q0 beats Q3_spatial_perm (p<0.05) → q_tensor carries ZE-local information")
        else:
            print("  ✗ Q0 does NOT beat spatial perm → q_tensor may be national proxy, not ZE-local")

    if p_lag1 is not None:
        if p_lag1 < WILCOXON_ALPHA:
            print("  ✓ Q0 beats Q6_lag1 (p<0.05) → contemporaneous q_tensor adds over lagged version")
        else:
            print("  △ Q0 does not beat Q6_lag1 → lagged q_tensor sufficient; recency not critical")

    print()
    print("  Note: temporal_perm (Q2) excluded — global year perm is not fold-safe.")
    print("  For a causal temporal test, permutation must be restricted to years <= train_max.")

    print(f"\n{'='*65}")
    print(f" Per-year WMAPE (mean across seeds)")
    print(f"{'='*65}")
    year_mu_cols = [c for c in summary.columns if c.endswith("_mu") and c.startswith("wmape_20")]
    if year_mu_cols:
        year_years = sorted([c.replace("wmape_", "").replace("_mu", "") for c in year_mu_cols])
        print(f"\n  {'Label':<50} " + "  ".join(f"{y:>8}" for y in year_years))
        print(f"  {'-'*50} " + "  ".join(f"{'--------':>8}" for _ in year_years))
        for _, row in summary.iterrows():
            vals_yr = [f"{row.get(f'wmape_{y}_mu', np.nan):>8.5f}" for y in year_years]
            print(f"  {row['label']:<50} " + "  ".join(vals_yr))

    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="OUT_ROOT from the Phase 3D run")
    args = parser.parse_args()
    audit_results(args.root)


if __name__ == "__main__":
    main()
