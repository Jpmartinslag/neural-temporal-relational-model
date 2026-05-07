#!/usr/bin/env python3
"""Compare original strict predictions against target-shuffled leak-stress runs."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PRED_PATTERNS = [
    "herald_v6_predictions_total_*_v1.csv",
    "herald_v7_predictions_total_*_v1.csv",
    "herald_semi_v2_predictions_total_*_v1.csv",
]


def load_predictions(root: Path):
    data_dir = root / "data_processed"
    out = {}
    for pat in PRED_PATTERNS:
        for path in data_dir.glob(pat):
            df = pd.read_csv(path)
            if "target_year" not in df.columns or "ZE2020" not in df.columns or "y_pred" not in df.columns:
                continue
            key = path.name
            out[key] = df.sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--stress-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    args = parser.parse_args()

    original = load_predictions(args.original_root)
    stress = load_predictions(args.stress_root)
    if not original:
        raise SystemExit(f"No original prediction CSVs under {args.original_root}")
    if not stress:
        raise SystemExit(f"No stress prediction CSVs under {args.stress_root}")

    common = sorted(set(original) & set(stress))
    missing_in_stress = sorted(set(original) - set(stress))
    extra_in_stress = sorted(set(stress) - set(original))
    rows = []
    failures = []

    for key in common:
        a = original[key]
        b = stress[key]
        if len(a) != len(b) or not a[["target_year", "ZE2020"]].equals(b[["target_year", "ZE2020"]]):
            failures.append({"file": key, "reason": "index_mismatch"})
            continue
        diff = np.abs(a["y_pred"].to_numpy() - b["y_pred"].to_numpy())
        max_diff = float(diff.max()) if len(diff) else 0.0
        mean_diff = float(diff.mean()) if len(diff) else 0.0
        same = bool(max_diff <= args.tolerance)
        if not same:
            failures.append({"file": key, "reason": "prediction_changed", "max_diff": max_diff})
        rows.append({
            "file": key,
            "rows": int(len(a)),
            "max_abs_pred_diff": max_diff,
            "mean_abs_pred_diff": mean_diff,
            "same_within_tolerance": same,
        })

    payload = {
        "original_files": len(original),
        "stress_files": len(stress),
        "common_files": len(common),
        "missing_in_stress": missing_in_stress,
        "extra_in_stress": extra_in_stress,
        "tolerance": args.tolerance,
        "failures": failures,
        "n_failures": len(failures),
        "comparisons": rows,
    }
    out = args.out_json or args.stress_root / "reports/leak_stress_prediction_invariance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"original_files={len(original)}")
    print(f"stress_files={len(stress)}")
    print(f"common_files={len(common)}")
    print(f"missing_in_stress={len(missing_in_stress)}")
    print(f"extra_in_stress={len(extra_in_stress)}")
    print(f"n_failures={len(failures)}")
    print(f"saved={out}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
