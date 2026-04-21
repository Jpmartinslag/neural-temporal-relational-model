import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PRED_PATH = ROOT / "data" / "processed" / "rei_created_baseline_predictions_v0.csv"
REFERENCE_BUNDLE_PATH = ROOT / "reports" / "next_phase_reference_bundle_v0.json"


def wmape(y_true, y_pred):
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def compare(candidate_path: Path, prediction_col: str):
    ref = pd.read_csv(REFERENCE_PRED_PATH)
    cand = pd.read_csv(candidate_path)

    required = {"target_year", "node_idx", "y_true", prediction_col}
    missing = required - set(cand.columns)
    if missing:
        raise ValueError(f"Missing columns in candidate file: {sorted(missing)}")

    candidate_col = "__candidate_prediction__"
    merged = ref.merge(
        cand[["target_year", "node_idx", "y_true", prediction_col]].rename(columns={prediction_col: candidate_col}),
        on=["target_year", "node_idx", "y_true"],
        how="inner",
    )
    if len(merged) != len(ref):
        raise ValueError(f"Candidate rows do not align with reference bundle: merged={len(merged)} ref={len(ref)}")

    rows = []
    for year, sub in merged.groupby("target_year"):
        y_true = sub["y_true"].to_numpy(float)
        rows.append(
            {
                "target_year": int(year),
                "candidate_wmape": wmape(y_true, sub[candidate_col].to_numpy(float)),
                "rei_created_baseline_wmape": wmape(y_true, sub["pred_rei_created_baseline"].to_numpy(float)),
                "ridge_lag_nbcom_wmape": wmape(y_true, sub["pred_ridge_lag_nbcom"].to_numpy(float)),
            }
        )

    candidate_mean = float(np.mean([r["candidate_wmape"] for r in rows]))
    rei_mean = float(np.mean([r["rei_created_baseline_wmape"] for r in rows]))
    ridge_mean = float(np.mean([r["ridge_lag_nbcom_wmape"] for r in rows]))

    cmp_rei = {
        "mean_delta": float(candidate_mean - rei_mean),
        "per_year_delta": {
            str(r["target_year"]): float(r["candidate_wmape"] - r["rei_created_baseline_wmape"]) for r in rows
        },
        "worsened_years": [int(r["target_year"]) for r in rows if r["candidate_wmape"] - r["rei_created_baseline_wmape"] > 1e-6],
        "strictly_better_with_tolerance": bool(candidate_mean < rei_mean and all(r["candidate_wmape"] - r["rei_created_baseline_wmape"] <= 1e-6 for r in rows)),
    }
    cmp_ridge = {
        "mean_delta": float(candidate_mean - ridge_mean),
        "per_year_delta": {
            str(r["target_year"]): float(r["candidate_wmape"] - r["ridge_lag_nbcom_wmape"]) for r in rows
        },
        "worsened_years": [int(r["target_year"]) for r in rows if r["candidate_wmape"] - r["ridge_lag_nbcom_wmape"] > 1e-6],
        "strictly_better_with_tolerance": bool(candidate_mean < ridge_mean and all(r["candidate_wmape"] - r["ridge_lag_nbcom_wmape"] <= 1e-6 for r in rows)),
    }

    return {
        "candidate_path": str(candidate_path.relative_to(ROOT) if candidate_path.is_relative_to(ROOT) else candidate_path),
        "prediction_col": prediction_col,
        "candidate_mean_wmape": candidate_mean,
        "reference_bundle": json.load(open(REFERENCE_BUNDLE_PATH)),
        "year_rows": rows,
        "comparison_vs_rei_created_baseline": cmp_rei,
        "comparison_vs_ridge_lag_nbcom": cmp_ridge,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, help="CSV with target_year,node_idx,y_true and a prediction column")
    parser.add_argument("--prediction-col", default="prediction")
    parser.add_argument("--out-json")
    args = parser.parse_args()

    payload = compare(Path(args.candidate), args.prediction_col)
    if args.out_json:
        out = Path(args.out_json)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved metrics to {out}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
