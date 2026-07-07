"""
Audit HERALD France ZE2020 relation-objective HPC outputs.

Descriptive only: no automatic promotion, no causal claim, no recommendation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_SEEDS = [42, 43, 44, 45, 46]
FORBIDDEN_COLUMNS = {
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
}
FORBIDDEN_TEXT = {
    "validated_gnn",
    "causal effect",
    "policy recommendation",
    "automatic recommendation",
}
METRICS_NAME = "fr_ze2020_relation_lift_over_formulas_metrics_v1.csv"
REAL_SCENARIO = "dual_endpoint_matched_negatives"
SHUFFLE_SCENARIO = "dual_endpoint_temporal_sector_shuffle"
LEARNER_NAME = "relation_logit"
CLAIM_STATUS = "relation_objective_hpc_audit_descriptive_only"


def find_seed_dirs(run_dir: Path) -> dict[int, Path]:
    seed_dirs = {}
    for path in sorted(run_dir.glob("seed_*")):
        if not path.is_dir():
            continue
        try:
            seed = int(path.name.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        seed_dirs[seed] = path
    return seed_dirs


def _load_seed_metrics(seed_dir: Path) -> pd.DataFrame:
    path = seed_dir / METRICS_NAME
    if not path.exists():
        raise FileNotFoundError(path)
    metrics = pd.read_csv(path)
    bad_cols = FORBIDDEN_COLUMNS & {col.lower() for col in metrics.columns}
    if bad_cols:
        raise ValueError(f"Forbidden columns {bad_cols} in {path}")
    if metrics.columns.duplicated().any():
        dupes = metrics.columns[metrics.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate columns {dupes} in {path}")
    text = " ".join(str(v).lower() for v in metrics.select_dtypes(include="object").to_numpy().ravel())
    found_text = sorted(term for term in FORBIDDEN_TEXT if term in text)
    if found_text:
        raise ValueError(f"Forbidden claim text {found_text} in {path}")
    numeric_cols = [
        "average_precision",
        "roc_auc",
        "best_formula_ap",
        "best_formula_auc",
        "ap_lift_over_best_formula",
        "auc_lift_over_best_formula",
    ]
    for col in numeric_cols:
        if col not in metrics.columns:
            raise ValueError(f"Missing metric column {col} in {path}")
        values = pd.to_numeric(metrics[col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"Non-finite values in {path}:{col}")
    metrics["seed_dir"] = seed_dir.name
    metrics["seed"] = int(seed_dir.name.split("_", 1)[1])
    return metrics


def _mean_row(metrics: pd.DataFrame, scenario: str, score: str) -> pd.Series:
    rows = metrics[
        (metrics["eval_year"].astype(str) == "mean")
        & (metrics["falsification_scenario"] == scenario)
        & (metrics["model_or_score"] == score)
    ]
    if rows.empty:
        raise ValueError(f"Missing mean row for scenario={scenario}, score={score}")
    return rows.iloc[0]


def gate_g1_no_errors(run_dir: Path, expected_seeds: list[int]) -> tuple[dict, pd.DataFrame]:
    seed_dirs = find_seed_dirs(run_dir)
    missing = [seed for seed in expected_seeds if seed not in seed_dirs]
    frames = []
    errors = []
    for seed in expected_seeds:
        seed_dir = seed_dirs.get(seed)
        if seed_dir is None:
            continue
        try:
            frames.append(_load_seed_metrics(seed_dir))
        except Exception as exc:  # noqa: BLE001 - report all audit failures.
            errors.append(f"seed_{seed}: {exc}")
    report = {
        "passed": not missing and not errors,
        "missing_seeds": missing,
        "errors": errors,
        "n_seed_dirs_found": len(seed_dirs),
    }
    return report, pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def gate_g2_real_lift(metrics: pd.DataFrame, min_lift: float = 0.05) -> dict:
    rows = []
    for seed in sorted(metrics["seed"].unique()):
        row = _mean_row(metrics[metrics["seed"] == seed], REAL_SCENARIO, LEARNER_NAME)
        rows.append(
            {
                "seed": int(seed),
                "average_precision": float(row["average_precision"]),
                "best_formula_ap": float(row["best_formula_ap"]),
                "ap_lift_over_best_formula": float(row["ap_lift_over_best_formula"]),
            }
        )
    lifts = [row["ap_lift_over_best_formula"] for row in rows]
    return {
        "passed": bool(rows) and min(lifts) >= min_lift,
        "threshold_min_lift": min_lift,
        "min_lift": float(min(lifts)) if lifts else None,
        "mean_lift": float(np.mean(lifts)) if lifts else None,
        "per_seed": rows,
    }


def gate_g3_shuffle_degradation(metrics: pd.DataFrame, min_drop: float = 0.20) -> dict:
    rows = []
    for seed in sorted(metrics["seed"].unique()):
        seed_metrics = metrics[metrics["seed"] == seed]
        real = _mean_row(seed_metrics, REAL_SCENARIO, LEARNER_NAME)
        shuffle = _mean_row(seed_metrics, SHUFFLE_SCENARIO, LEARNER_NAME)
        drop = float(real["average_precision"] - shuffle["average_precision"])
        lift_drop = float(real["ap_lift_over_best_formula"] - shuffle["ap_lift_over_best_formula"])
        rows.append(
            {
                "seed": int(seed),
                "real_average_precision": float(real["average_precision"]),
                "shuffle_average_precision": float(shuffle["average_precision"]),
                "ap_drop": drop,
                "lift_drop": lift_drop,
            }
        )
    drops = [row["ap_drop"] for row in rows]
    return {
        "passed": bool(rows) and min(drops) >= min_drop,
        "threshold_min_ap_drop": min_drop,
        "min_ap_drop": float(min(drops)) if drops else None,
        "mean_ap_drop": float(np.mean(drops)) if drops else None,
        "per_seed": rows,
    }


def gate_g4_stability(metrics: pd.DataFrame, max_cv: float = 0.20) -> dict:
    rows = []
    for seed in sorted(metrics["seed"].unique()):
        row = _mean_row(metrics[metrics["seed"] == seed], REAL_SCENARIO, LEARNER_NAME)
        rows.append(float(row["ap_lift_over_best_formula"]))
    mean_lift = float(np.mean(rows)) if rows else float("nan")
    std_lift = float(np.std(rows, ddof=0)) if rows else float("nan")
    cv = float(std_lift / mean_lift) if mean_lift else float("inf")
    return {
        "passed": bool(rows) and cv <= max_cv,
        "threshold_max_cv": max_cv,
        "mean_lift": mean_lift,
        "std_lift": std_lift,
        "cv_lift": cv,
        "n_seeds": len(rows),
    }


def gate_g5_output_separation(metrics: pd.DataFrame) -> dict:
    claim_values = set(metrics.get("claim_status", pd.Series(dtype=str)).dropna().astype(str))
    forbidden_claims = []
    for value in claim_values:
        lower = value.lower()
        recommendation_is_negated = "not_recommend" in lower or "no_recommend" in lower
        causal_is_negated = "not_causal" in lower or "no_causal" in lower
        if "recommend" in lower and not recommendation_is_negated:
            forbidden_claims.append(value)
        elif "causal" in lower and not causal_is_negated:
            forbidden_claims.append(value)
    forbidden_claims = sorted(forbidden_claims)
    return {
        "passed": not forbidden_claims,
        "claim_status_values": sorted(claim_values),
        "forbidden_claim_status_values": forbidden_claims,
    }


def build_report(run_dir: Path, expected_seeds: list[int] = EXPECTED_SEEDS) -> dict:
    g1, metrics = gate_g1_no_errors(run_dir, expected_seeds)
    gates = {"G1_no_errors": g1}
    if not metrics.empty:
        gates["G2_real_lift_over_formula"] = gate_g2_real_lift(metrics)
        gates["G3_shuffle_degradation"] = gate_g3_shuffle_degradation(metrics)
        gates["G4_lift_stability"] = gate_g4_stability(metrics)
        gates["G5_output_separation"] = gate_g5_output_separation(metrics)
    else:
        gates["G2_real_lift_over_formula"] = {"passed": False, "reason": "no metrics"}
        gates["G3_shuffle_degradation"] = {"passed": False, "reason": "no metrics"}
        gates["G4_lift_stability"] = {"passed": False, "reason": "no metrics"}
        gates["G5_output_separation"] = {"passed": False, "reason": "no metrics"}

    all_pass = all(gate.get("passed") is True for gate in gates.values())
    summary_rows = []
    if not metrics.empty:
        mean_rows = metrics[metrics["eval_year"].astype(str) == "mean"]
        summary_rows = (
            mean_rows.groupby(["falsification_scenario", "model_or_score"], as_index=False)
            .agg(
                mean_average_precision=("average_precision", "mean"),
                mean_best_formula_ap=("best_formula_ap", "mean"),
                mean_ap_lift=("ap_lift_over_best_formula", "mean"),
                n_seed_rows=("average_precision", "size"),
            )
            .sort_values(["falsification_scenario", "mean_average_precision"], ascending=[True, False])
            .to_dict(orient="records")
        )
    return {
        "run_dir": str(run_dir),
        "status": "RELATION_OBJECTIVE_HPC_AUDIT_PASS" if all_pass else "RELATION_OBJECTIVE_HPC_AUDIT_PARTIAL_OR_FAIL",
        "claim_status": CLAIM_STATUS,
        "gates": gates,
        "summary": summary_rows,
        "caveat": "Descriptive HPC falsification only: no causal claim, no automatic recommendation, no validated dynamic graph model.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--expected-seeds", nargs="+", type=int, default=EXPECTED_SEEDS)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = build_report(args.run_dir, expected_seeds=args.expected_seeds)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
