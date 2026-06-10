"""Audit Phase 5 HPC results: WMAPE by country/year, gate check, tail risk.

Usage:
    python3 hpc/phase5/audit_phase5_results.py --results-dir hpc_results/phase5/raw
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]


def load_results(results_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(results_dir.glob("*.json")):
        with open(f) as fh:
            d = json.load(fh)
        meta = d.get("metadata", {})
        for yr_result in d.get("results_by_year", []):
            rows.append({
                "country": yr_result["country"],
                "hypothesis": yr_result["hypothesis"],
                "eval_year": yr_result["eval_year"],
                "seed": meta.get("seed"),
                "commit": meta.get("commit", "?"),
                "wmape": yr_result["wmape"],
                "wmape_baseline": yr_result["wmape_baseline"],
                "alpha_ratio": yr_result["alpha_ratio"],
                "n_train_samples": yr_result["n_train_samples"],
                "any_nan": yr_result["any_nan"],
                "any_inf": yr_result["any_inf"],
                "leakage_ok": yr_result["leakage_ok"],
            })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="hpc_results/phase5/raw")
    args = parser.parse_args()

    rdir = BASE / args.results_dir
    if not rdir.exists():
        print(f"Results dir not found: {rdir}")
        return

    df = load_results(rdir)
    if df.empty:
        print("No results found.")
        return

    print(f"Loaded {len(df)} result rows from {rdir}")
    print()

    # WMAPE by country × hypothesis
    print("=== Mean WMAPE by country × hypothesis ===")
    pivot = df.groupby(["country", "hypothesis"])["wmape"].agg(["mean", "std", "count"])
    print(pivot.to_string())
    print()

    # Tail risk (p90 WMAPE per country × hypothesis)
    print("=== P90 WMAPE (tail risk) ===")
    for (c, h), grp in df.groupby(["country", "hypothesis"]):
        p90 = np.nanpercentile(grp["wmape"].values, 90)
        print(f"  {c}/{h}: p90={p90:.4f}")
    print()

    # Leakage check
    print("=== Leakage audit ===")
    bad = df[~df["leakage_ok"]]
    if bad.empty:
        print("  All leakage checks OK.")
    else:
        print(f"  LEAKAGE VIOLATIONS: {len(bad)} rows")
        print(bad[["country", "hypothesis", "eval_year", "seed"]].to_string())
    print()

    # NaN/Inf
    print("=== NaN / Inf ===")
    nan_rows = df[df["any_nan"]]
    inf_rows = df[df["any_inf"]]
    print(f"  any_nan: {len(nan_rows)} rows | any_inf: {len(inf_rows)} rows")
    print()

    # Gate check: H2-neural vs controls per country
    from src.modeles.phase5.rolling_origin import gate_h2_neural, summarise, YearResult
    for country in df["country"].unique():
        sub = df[df["country"] == country]
        # Build summary in gate_h2_neural format
        agg = {}
        for hyp, grp in sub.groupby("hypothesis"):
            agg[hyp] = {
                "mean_wmape": float(grp["wmape"].mean()),
                "wmape_by_year": {int(y): float(g["wmape"].mean())
                                   for y, g in grp.groupby("eval_year")},
            }
        gate = gate_h2_neural(agg, country)
        print(f"Gate {country}: {gate['note']}")
        for ctrl, info in gate.get("controls", {}).items():
            sym = "✓" if info.get("beats") else "✗"
            print(f"  {sym} {ctrl}")
    print()

    # Correction amplitude
    print("=== Correction amplitude (mean alpha_ratio per hypothesis) ===")
    for h, grp in df.groupby("hypothesis"):
        print(f"  {h:<26}: {grp['alpha_ratio'].mean():.4f} ± {grp['alpha_ratio'].std():.4f}")
    print()

    print("=== Determinism check (WMAPE std across seeds per year) ===")
    det = df.groupby(["country", "hypothesis", "eval_year"])["wmape"].std()
    noisy = det[det > 0.001]
    if noisy.empty:
        print("  All results deterministic across seeds (std < 0.001).")
    else:
        print(f"  Non-deterministic combinations: {len(noisy)}")
        print(noisy.to_string())


if __name__ == "__main__":
    main()
