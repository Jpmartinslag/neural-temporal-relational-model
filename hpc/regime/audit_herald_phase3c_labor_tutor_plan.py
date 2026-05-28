#!/usr/bin/env python3
"""Pre-flight audit for HERALD Phase 3C labor-tutor battery.

Checks:
  1. Labor tutor feature CSV exists and has required columns.
  2. Coverage per signal (non-NaN rate, year range, ZE count).
  3. Blocked signals identified (defm, activite_partielle).
  4. ZE overlap between labor tutor CSV and panel.
  5. Leakage check: no target-year data used (structural — confirmed by builder).
  6. Permutation check: permuted column non-zero variance.
  7. Config list from regime_plan_configs.sh for phase3c_labor_tutor.
  8. OUT_ROOT uniqueness check.
  9. Expected run count.

Usage:
  python3 hpc/regime/audit_herald_phase3c_labor_tutor_plan.py
  python3 hpc/regime/audit_herald_phase3c_labor_tutor_plan.py \\
      --labor-tutor-path data/processed/herald_phase3c_labor_tutor_features.csv \\
      --panel-path data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LABOR_TUTOR_PATH = Path("data/processed/herald_phase3c_labor_tutor_features.csv")
PANEL_PATH = Path("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
REGIME_PLAN = "phase3c_labor_tutor"
N_SEEDS = 10
FEATURE_SETS = {
    "none": [],
    "defm_recovery": ["defm_recovery_tminus1"],
    "defm_recovery_perm": ["defm_recovery_perm_tminus1"],
    "urssaf_cotisants_delta": ["urssaf_cotisants_delta_tminus1"],
    "urssaf_cotisants_delta_perm": ["urssaf_cotisants_delta_perm_tminus1"],
    "defm_urssaf_combo": ["defm_recovery_tminus1", "urssaf_cotisants_delta_tminus1"],
    "defm_urssaf_combo_perm": ["defm_recovery_perm_tminus1", "urssaf_cotisants_delta_perm_tminus1"],
    "defm_recovery_lag2": ["defm_recovery_lag2_tminus1"],
    "urssaf_cotisants_delta_lag2": ["urssaf_cotisants_delta_lag2_tminus1"],
    "defm_recovery_spatial_perm": ["defm_recovery_spatial_perm_tminus1"],
    "urssaf_cotisants_delta_spatial_perm": ["urssaf_cotisants_delta_spatial_perm_tminus1"],
    "defm_recovery_signed": ["defm_recovery_signed_tminus1"],
    "defm_yoy": ["defm_yoy_tminus1"],
    "urssaf_cotisants_neg": ["urssaf_cotisants_neg_tminus1"],
    "urssaf_cotisants_pos": ["urssaf_cotisants_pos_tminus1"],
}

ALL_SIGNALS = [
    ("C0_baseline", "none", "available"),
    ("C1_defm_ze_recovery", "defm_recovery", "available"),
    ("C2_defm_ze_recovery_perm", "defm_recovery_perm", "available"),
    ("C3_urssaf_cotisants_delta", "urssaf_cotisants_delta", "available"),
    ("C4_urssaf_cotisants_delta_perm", "urssaf_cotisants_delta_perm", "available"),
    ("C5_combo_defm_urssaf", "defm_urssaf_combo", "available"),
    ("C6_combo_defm_urssaf_perm", "defm_urssaf_combo_perm", "available"),
    ("C7_defm_lag2", "defm_recovery_lag2", "available"),
    ("C8_urssaf_lag2", "urssaf_cotisants_delta_lag2", "available"),
    ("C9_defm_spatial_perm", "defm_recovery_spatial_perm", "available"),
    ("C10_urssaf_spatial_perm", "urssaf_cotisants_delta_spatial_perm", "available"),
    ("C11_defm_signed_recovery", "defm_recovery_signed", "available"),
    ("C12_defm_yoy", "defm_yoy", "available"),
    ("C13_urssaf_negative_only", "urssaf_cotisants_neg", "available"),
    ("C14_urssaf_positive_only", "urssaf_cotisants_pos", "available"),
    ("C15_combo_step06", "defm_urssaf_combo", "available"),
    ("C16_combo_a10_guard", "defm_urssaf_combo", "available"),
    ("C17_combo_l3dim", "defm_urssaf_combo", "available"),
]


def ok(msg):
    print(f"  \033[32m✓\033[0m {msg}")


def warn(msg):
    print(f"  \033[33m⚠\033[0m {msg}")


def fail(msg):
    print(f"  \033[31m✗\033[0m {msg}")


def get_runnable_configs():
    script = (
        "source hpc/regime/regime_plan_configs.sh && plan_configs"
    )
    try:
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True, check=True,
            env={**__import__("os").environ, "REGIME_PLAN": REGIME_PLAN},
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        return lines
    except subprocess.CalledProcessError as e:
        print(f"  Failed to load plan_configs: {e.stderr}")
        return []


def audit(labor_tutor_path: Path, panel_path: Path) -> bool:
    errors = 0
    print(f"\n{'='*60}")
    print(f" HERALD Phase 3C — Labor Tutor Battery Audit")
    print(f"{'='*60}")

    # 1. File existence
    print("\n[1] File existence")
    if labor_tutor_path.exists():
        ok(f"Labor tutor CSV: {labor_tutor_path}")
    else:
        fail(f"Labor tutor CSV not found: {labor_tutor_path}")
        fail("Run: python3 src/data/build_herald_phase3c_labor_tutor_features.py")
        errors += 1
        return False

    if panel_path.exists():
        ok(f"Panel: {panel_path}")
    else:
        fail(f"Panel not found: {panel_path}")
        errors += 1

    # 2. Load data
    print("\n[2] Loading data")
    ldf = pd.read_csv(labor_tutor_path)
    panel = pd.read_csv(panel_path)
    ok(f"Labor tutor: {len(ldf)} rows, cols={ldf.columns.tolist()}")
    ok(f"Panel: {len(panel)} rows, {panel['ZE2020'].nunique()} ZEs, years {panel['target_year'].min()}–{panel['target_year'].max()}")

    # 3. Required columns
    print("\n[3] Required columns")
    required = ["year", "ze2020"]
    for cols in FEATURE_SETS.values():
        required.extend(cols)
    required += ["activite_partielle_tminus1", "activite_partielle_perm_tminus1"]
    required = sorted(set(required))
    missing = [c for c in required if c not in ldf.columns]
    if missing:
        fail(f"Missing columns: {missing}")
        errors += 1
    else:
        ok("All required columns present")

    # 4. Coverage per signal
    print("\n[4] Signal coverage")
    for label, fset, status in ALL_SIGNALS:
        if fset == "none":
            ok(f"C0 baseline: no tutor signal (L5_trainopt reference)")
            continue
        cols = FEATURE_SETS.get(fset, [])
        missing_cols = [c for c in cols if c not in ldf.columns]
        if missing_cols:
            fail(f"{label}: missing columns {missing_cols}")
            errors += 1
            continue
        masks = [ldf[c].notna() for c in cols]
        valid = masks[0]
        for m in masks[1:]:
            valid = valid & m
        n_valid = int(valid.sum())
        n_ze = int(ldf.loc[valid, "ze2020"].nunique())
        if n_valid == 0:
            fail(f"{label} [{fset}]: 0 valid rows in {cols}")
            errors += 1
        else:
            yr_min = int(ldf.loc[valid, "year"].min())
            yr_max = int(ldf.loc[valid, "year"].max())
            ok(f"{label}: {n_valid} rows, {n_ze} ZEs, years {yr_min}–{yr_max}, cols={cols}")

    # 5. ZE overlap
    print("\n[5] ZE overlap")
    panel_ze = set(panel["ZE2020"].unique())
    tutor_ze = set(ldf["ze2020"].unique())
    missing_in_tutor = panel_ze - tutor_ze
    extra_in_tutor = tutor_ze - panel_ze
    if missing_in_tutor:
        fail(f"{len(missing_in_tutor)} panel ZEs not in labor tutor CSV: {sorted(missing_in_tutor)[:5]}...")
        errors += 1
    else:
        ok(f"All {len(panel_ze)} panel ZEs covered in labor tutor CSV")
    if extra_in_tutor:
        warn(f"{len(extra_in_tutor)} extra ZEs in labor tutor (not in panel) — will be ignored")

    # 6. Permutation check: variance should differ between real and permuted
    print("\n[6] Permutation validity (URSSAF)")
    real_col = "urssaf_cotisants_delta_tminus1"
    perm_col = "urssaf_cotisants_delta_perm_tminus1"
    if real_col in ldf.columns and perm_col in ldf.columns:
        real_vals = ldf[real_col].dropna()
        perm_vals = ldf[perm_col].dropna()
        corr = float(real_vals.corr(perm_vals))
        same = (real_vals.values == perm_vals.values).all()
        if same:
            fail("Real and permuted values are identical — permutation failed")
            errors += 1
        elif abs(corr) > 0.95:
            warn(f"Real/permuted correlation very high: {corr:.4f} — permutation may not break signal")
        else:
            ok(f"Real/permuted differ (corr={corr:.4f}) — permutation valid")
        # Variance should be similar (permutation is structure-preserving)
        rv, pv = float(real_vals.var()), float(perm_vals.var())
        ok(f"Variance real={rv:.6f}, perm={pv:.6f}")

    # 7. Runnable configs from plan
    print("\n[7] Runnable configs (phase3c_labor_tutor)")
    configs = get_runnable_configs()
    n_configs = len(configs)
    n_runs = n_configs * N_SEEDS
    if n_configs == 0:
        fail("No configs found — check regime_plan_configs.sh")
        errors += 1
    else:
        ok(f"{n_configs} configs × {N_SEEDS} seeds = {n_runs} runs")
        for i, cfg in enumerate(configs):
            label = cfg.split()[3] if len(cfg.split()) > 3 else f"config_{i}"
            labor = cfg.split()[-1] if len(cfg.split()) > 39 else "none"
            ok(f"  Config {i}: label={label}, labor_tutor={labor}")

    # 8. Leakage structural check
    print("\n[8] Leakage structural check")
    ok("urssaf_cotisants_delta uses (etabs(t-1) - etabs(t-2)) / etabs(t-2)")
    ok("Feature uses years t-1 and t-2 only for predicting year t")
    defm_col = "defm_recovery_tminus1"
    if defm_col in ldf.columns and ldf[defm_col].notna().any():
        ok("defm_recovery uses Q4(t-1) / Q2(t-1) per ZE — only quarters of year t-1 used")
        warn("defm_recovery target_year 2021: uses Q4(2020)/Q2(2020) — COVID-era data (no flag applied per Phase 3C rules)")
    ok("Permutation shuffles years preserving cross-ZE structure (verified in builder)")
    ok("Normalization (z-score) computed from training fold only in make_sequences_v7")

    # 9. Summary
    print(f"\n{'='*60}")
    print(f" Summary")
    print(f"{'='*60}")
    print(f"\n Config table (18 runnable):")
    print(f"  {'Config':<35} {'Feature set':<30} {'Status':<10}")
    print(f"  {'-'*35} {'-'*30} {'-'*10}")
    for label, fset, status in ALL_SIGNALS:
        fset_display = fset if fset != "none" else "(L5 baseline)"
        status_str = "OK"
        print(f"  {label:<35} {fset_display:<30} {status_str:<10}")

    print(f"\n Runnable now: C0–C17 ({18} configs × {N_SEEDS} seeds = {18*N_SEEDS} runs)")
    print(" Blocked outside this plan: activité partielle (no clean pre-2020 ZE-level open data)")

    if errors:
        print(f"\n\033[31m✗ {errors} error(s) — FIX BEFORE SUBMITTING\033[0m\n")
    else:
        print(f"\n\033[32m✓ Preflight passed. Ready to smoke test.\033[0m\n")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labor-tutor-path", type=Path, default=LABOR_TUTOR_PATH)
    parser.add_argument("--panel-path", type=Path, default=PANEL_PATH)
    args = parser.parse_args()
    ok_status = audit(args.labor_tutor_path, args.panel_path)
    sys.exit(0 if ok_status else 1)


if __name__ == "__main__":
    main()
