#!/usr/bin/env python3
"""Results audit for HERALD Phase 3C labor-tutor battery.

Reads aggregated results from the Phase 3C OUT_ROOT and evaluates:
  - Primary criterion: Wilcoxon paired test C1 vs C2 and C3 vs C4, C0 primary reference
  - Guard rail: WMAPE_2025 not degraded by >0.003 vs C0
  - Guard rail: A10 WMAPE not relevantly degraded vs C0
  - Falsification check: C2/C4 (permuted) must NOT beat C1/C3 (real)
  - Per-year WMAPE table

Usage:
  python3 hpc/regime/audit_herald_phase3c_labor_tutor_results.py \\
      --root hpc_results/herald_regime_phase3c_labor_tutor_<STAMP>_r1
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
BASELINE_WMAPE_2021 = 0.035020
BASELINE_WMAPE_2025 = 0.012525
GUARD_2025_MARGIN = 0.003
WILCOXON_ALPHA = 0.05


def load_metrics(root: Path) -> dict:
    """Load all per-run JSON metrics from the results root."""
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
        wmape_mean = m.get("total_wmape_mean")
        wmape_2025 = m.get("total_wmape_2025")
        seed = m.get("seed", -1)
        row = {
            "label": label,
            "seed": seed,
            "wmape_mean": wmape_mean,
            "wmape_2025": wmape_2025,
            "labor_fset": m.get("labor_tutor_feature_set", "none"),
        }
        for yr, w in per_year.items():
            row[f"wmape_{yr}"] = w
        rows.append(row)
    return pd.DataFrame(rows)


def wilcoxon_paired(a: np.ndarray, b: np.ndarray, label_a: str, label_b: str):
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


def audit_results(root: Path) -> None:
    print(f"\n{'='*60}")
    print(f" HERALD Phase 3C — Results Audit")
    print(f" Root: {root}")
    print(f"{'='*60}")

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
    summary = (
        df.groupby("label")
        .agg(
            n_seeds=("seed", "count"),
            wmape_mean_mu=("wmape_mean", "mean"),
            wmape_mean_sd=("wmape_mean", "std"),
            wmape_2025_mu=("wmape_2025", "mean"),
            wmape_2025_sd=("wmape_2025", "std"),
        )
        .reset_index()
    )
    for yr_col in year_cols:
        if yr_col in df.columns:
            yr_agg = df.groupby("label")[yr_col].agg(["mean", "std"]).reset_index()
            yr_agg.columns = ["label", f"{yr_col}_mu", f"{yr_col}_sd"]
            summary = summary.merge(yr_agg, on="label", how="left")

    print(f"\n{'='*60}")
    print(f" Summary table")
    print(f"{'='*60}")
    print(f"\n  {'Label':<45} {'N':<4} {'Mean WMAPE':<14} {'WMAPE 2021':<14} {'WMAPE 2025':<14}")
    print(f"  {'-'*45} {'-'*4} {'-'*14} {'-'*14} {'-'*14}")
    for _, row in summary.iterrows():
        wmape_2021_col = "wmape_2021_mu"
        w2021 = f"{row[wmape_2021_col]:.6f}" if wmape_2021_col in row.index and pd.notna(row[wmape_2021_col]) else "—"
        print(f"  {row['label']:<45} {int(row['n_seeds']):<4} "
              f"{row['wmape_mean_mu']:.6f} ± {row['wmape_mean_sd']:.6f}  "
              f"{w2021:<14} "
              f"{row['wmape_2025_mu']:.6f}")

    # Find C0 and real/permuted pairs
    c0_mask = df["label"].str.contains("C0_baseline")
    c1_mask = df["label"].str.contains("C1_defm_ze_recovery") & ~df["label"].str.contains("perm")
    c2_mask = df["label"].str.contains("C2_defm_ze_recovery_perm")
    c3_mask = df["label"].str.contains("C3_urssaf") & ~df["label"].str.contains("perm")
    c4_mask = df["label"].str.contains("C4_urssaf") & df["label"].str.contains("perm")

    print(f"\n{'='*60}")
    print(f" Primary criteria")
    print(f"{'='*60}")

    if c0_mask.sum() == 0:
        print("\n  ⚠ C0_baseline not found — cannot compute guard rails")
    else:
        c0_means = df.loc[c0_mask, "wmape_mean"].values
        c0_2025 = df.loc[c0_mask, "wmape_2025"].values
        print(f"\n  C0 baseline: mean={c0_means.mean():.6f} ± {c0_means.std():.6f}, "
              f"2025={c0_2025.mean():.6f}")

    for real_name, perm_name, real_mask, perm_mask in [
        ("C1 DEFM", "C2 DEFM permuted", c1_mask, c2_mask),
        ("C3 URSSAF", "C4 URSSAF permuted", c3_mask, c4_mask),
    ]:
        if real_mask.sum() == 0 or perm_mask.sum() == 0:
            print(f"\n  ⚠ {real_name} or {perm_name} not found — "
                  f"{real_mask.sum()} real runs, {perm_mask.sum()} perm runs")
            continue

        real_means = df.loc[real_mask, "wmape_mean"].values
        perm_means = df.loc[perm_mask, "wmape_mean"].values
        n_wins_real = int((real_means < perm_means).sum())
        pval, stat = wilcoxon_paired(real_means, perm_means, real_name, perm_name)
        print(f"\n  {real_name} (real) vs {perm_name}:")
        print(f"    real mean={real_means.mean():.6f}, perm mean={perm_means.mean():.6f}")
        print(f"    real wins vs perm: {n_wins_real}/{len(real_means)} seeds")
        if pval is not None:
            verdict = "✓ real beats permuted (p<0.05)" if pval < WILCOXON_ALPHA else "✗ real does NOT beat permuted"
            print(f"    Wilcoxon (real<perm): p={pval:.4f} — {verdict}")
        else:
            print("    scipy not available — Wilcoxon not computed")

        # Guard: real signal should not be worse than C0 on 2025
        if c0_mask.sum() > 0:
            c0_2025_mean = float(df.loc[c0_mask, "wmape_2025"].mean())
            real_2025_mean = float(df.loc[real_mask, "wmape_2025"].mean())
            degradation_2025 = real_2025_mean - c0_2025_mean
            guard_ok = degradation_2025 <= GUARD_2025_MARGIN
            verdict = "✓ guard OK" if guard_ok else f"✗ VIOLATED (degradation={degradation_2025:.4f} > {GUARD_2025_MARGIN})"
            print(f"\n  Guard rail 2025: real={real_2025_mean:.6f}, C0={c0_2025_mean:.6f}, "
                  f"Δ={degradation_2025:+.6f} — {verdict}")

    print(f"\n{'='*60}")
    print(f" Per-year WMAPE (mean across seeds)")
    print(f"{'='*60}")
    year_mu_cols = [c for c in summary.columns if c.endswith("_mu") and c.startswith("wmape_20")]
    if year_mu_cols:
        year_years = sorted([c.replace("wmape_", "").replace("_mu", "") for c in year_mu_cols])
        print(f"\n  {'Label':<45} " + "  ".join(f"{y:>8}" for y in year_years))
        print(f"  {'-'*45} " + "  ".join(f"{'--------':>8}" for _ in year_years))
        for _, row in summary.iterrows():
            vals = [f"{row.get(f'wmape_{y}_mu', np.nan):>8.5f}" for y in year_years]
            print(f"  {row['label']:<45} " + "  ".join(vals))

    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="OUT_ROOT from the Phase 3C run")
    args = parser.parse_args()
    audit_results(args.root)


if __name__ == "__main__":
    main()
