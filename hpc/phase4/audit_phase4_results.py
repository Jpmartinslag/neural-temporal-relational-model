#!/usr/bin/env python3
"""Aggregate and compare HERALD Phase 4 results across countries.

Usage:
    # Single-country run root:
    python3 hpc/phase4/audit_phase4_results.py --root hpc_results/herald_phase4_nl_<STAMP>_r1

    # Multi-country comparison:
    python3 hpc/phase4/audit_phase4_results.py \
        --root-nl hpc_results/herald_phase4_nl_<STAMP>_r1 \
        --root-be hpc_results/herald_phase4_be_<STAMP>_r1 \
        --root-pt hpc_results/herald_phase4_pt_<STAMP>_r1

    # With France reference:
    python3 hpc/phase4/audit_phase4_results.py \
        --root-nl ... --root-be ... --root-pt ... \
        --france-wmape 0.020398
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load_runs(per_run_dir: Path, pattern: str = "*.json") -> list[dict]:
    runs = []
    for p in sorted(per_run_dir.glob(pattern)):
        try:
            payload = json.loads(p.read_text())
            result = next(iter(payload.values()))
            runs.append(result)
        except Exception as e:
            print(f"  WARNING: failed to load {p}: {e}")
    return runs


def summarize_by_config(runs: list[dict]) -> dict[str, dict]:
    by_config: dict[str, list[float]] = {}
    by_config_years: dict[str, dict[int, list[float]]] = {}

    for r in runs:
        tag = r.get("run_tag", "")
        wmape = r.get("total_wmape_mean", r.get("wmape_mean", None))
        per_year = r.get("per_year_total", {})

        # Extract config label from tag: phase4_{country}_{label}_seed_{n}
        parts = tag.split("_seed_")[0]
        label = parts.replace("phase4_nl_", "").replace("phase4_be_", "").replace("phase4_pt_", "")

        if wmape is not None and not math.isnan(float(wmape)):
            by_config.setdefault(label, []).append(float(wmape))

        if per_year:
            for yr_str, yw in per_year.items():
                yr = int(yr_str)
                by_config_years.setdefault(label, {}).setdefault(yr, []).append(float(yw))

    summary: dict[str, dict] = {}
    for label, values in by_config.items():
        n = len(values)
        mean = sum(values) / n
        std = (sum((v - mean) ** 2 for v in values) / n) ** 0.5
        summary[label] = {
            "n": n,
            "wmape_mean": round(mean, 6),
            "wmape_std": round(std, 6),
            "wmape_min": round(min(values), 6),
            "wmape_max": round(max(values), 6),
            "per_year": {
                yr: round(sum(yw) / len(yw), 6)
                for yr, yw in sorted(by_config_years.get(label, {}).items())
            },
        }
    return summary


def print_summary_table(country: str, summary: dict[str, dict], france_wmape: float | None) -> None:
    print(f"\n{'='*70}")
    print(f" HERALD Phase 4 — {country.upper()}")
    print(f"{'='*70}")
    print(f"  {'Config':<28} {'N':>4}  {'WMAPE mean':>12}  {'±std':>8}  {'vs France':>10}")
    print(f"  {'-'*28} {'-'*4}  {'-'*12}  {'-'*8}  {'-'*10}")

    for label, s in sorted(summary.items()):
        vs_france = ""
        if france_wmape and "baseline" in label:
            gain = (france_wmape - s["wmape_mean"]) / france_wmape * 100
            vs_france = f"{gain:+.1f}%"
        print(f"  {label:<28} {s['n']:>4}  {s['wmape_mean']:>12.6f}  {s['wmape_std']:>8.6f}  {vs_france:>10}")

    if len(summary) >= 2:
        labels = list(summary.keys())
        if "baseline_side2" in labels and ("qtensor_jobs_lag1" in labels or "sector_births_lag1" in labels):
            baseline_wmape = summary["baseline_side2"]["wmape_mean"]
            tensor_label = "qtensor_jobs_lag1" if "qtensor_jobs_lag1" in labels else "sector_births_lag1"
            tensor_wmape = summary[tensor_label]["wmape_mean"]
            gain_tensor = (baseline_wmape - tensor_wmape) / baseline_wmape * 100
            print(f"\n  Tensor gain ({tensor_label} vs baseline_side2): {gain_tensor:+.2f}%")
            direction = "IMPROVES" if gain_tensor > 0 else "DOES NOT IMPROVE"
            print(f"  → Tensor {direction} baseline for {country.upper()}")

    print()
    print(f"  Per-year WMAPE (means across seeds):")
    if summary:
        first_label = list(summary.keys())[0]
        years = sorted(summary[first_label].get("per_year", {}).keys())
        header = f"  {'Year':<6}" + "".join(f"  {lb[:14]:>14}" for lb in sorted(summary.keys()))
        print(header)
        for yr in years:
            row = f"  {yr:<6}" + "".join(
                f"  {summary[lb]['per_year'].get(yr, float('nan')):>14.6f}"
                for lb in sorted(summary.keys())
            )
            print(row)


def audit_root(root: Path, country: str, france_wmape: float | None) -> dict:
    per_run = root / "reports" / "per_run"
    if not per_run.exists():
        print(f"WARNING: {per_run} does not exist — skipping {country}")
        return {}

    runs = load_runs(per_run)
    print(f"\n[{country.upper()}] Loaded {len(runs)} runs from {root}")

    summary = summarize_by_config(runs)
    print_summary_table(country, summary, france_wmape)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None,
                        help="Single-country run root (auto-detects country from path)")
    parser.add_argument("--root-nl", type=Path, default=None)
    parser.add_argument("--root-be", type=Path, default=None)
    parser.add_argument("--root-pt", type=Path, default=None)
    parser.add_argument("--france-wmape", type=float, default=None,
                        help="France HERALD Q7 baseline WMAPE for comparison (e.g. 0.020398)")
    parser.add_argument("--out-json", type=Path, default=None,
                        help="Write aggregated results to JSON")
    args = parser.parse_args()

    france_wmape = args.france_wmape

    results: dict[str, dict] = {}

    if args.root:
        root_str = str(args.root)
        if "_nl_" in root_str:
            country = "nl"
        elif "_be_" in root_str:
            country = "be"
        elif "_pt_" in root_str:
            country = "pt"
        else:
            country = "unknown"
        results[country] = audit_root(args.root, country, france_wmape)

    for country, root in [("nl", args.root_nl), ("be", args.root_be), ("pt", args.root_pt)]:
        if root is not None:
            results[country] = audit_root(root, country, france_wmape)

    if len(results) >= 2:
        print(f"\n{'='*70}")
        print(" Cross-country comparison — baseline_side2")
        print(f"{'='*70}")
        print(f"  {'Country':<10} {'WMAPE mean':>12}  {'±std':>8}  {'N':>4}")
        print(f"  {'-'*10} {'-'*12}  {'-'*8}  {'-'*4}")
        if france_wmape:
            print(f"  {'France (Q7)':10} {france_wmape:>12.6f}  {'(ref)':>8}  {'20':>4}")
        for country, summary in sorted(results.items()):
            s = summary.get("baseline_side2")
            if s:
                print(f"  {country.upper():<10} {s['wmape_mean']:>12.6f}  {s['wmape_std']:>8.6f}  {s['n']:>4}")

    if args.out_json and results:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults written to {args.out_json}")


if __name__ == "__main__":
    main()
