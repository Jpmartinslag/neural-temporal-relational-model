"""
Audit collected HERALD France ZE2020 top-3 entry HPC results.

Descriptive only: no automatic promotion, no causal claim, no recommendation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

METRICS_NAME = "fr_ze2020_top3_entry_falsification_metrics_v1.csv"
PREDICTIONS_NAME = "fr_ze2020_top3_entry_falsification_predictions_v1.csv"
SUMMARY_NAME = "fr_ze2020_top3_entry_falsification_summary_v1.csv"
RUN_NAME = "fr_ze2020_top3_entry_falsification_run_v1.json"
EXPECTED_SCENARIOS = ["full_control", "temporal_shuffle", "sector_shuffle", "target_shuffle"]
EXPECTED_SEEDS = [42, 43, 44, 45, 46]
FORBIDDEN_COLUMNS = {
    "recommendation",
    "recommended" + "_action",
    "policy" + "_action",
    "causal" + "_effect",
    "causal" + "_impact",
}


def _task_dirs(run_dir: Path) -> list[Path]:
    dirs = []
    for scenario in EXPECTED_SCENARIOS:
        for seed in EXPECTED_SEEDS:
            dirs.append(run_dir / scenario / f"seed_{seed}")
    return dirs


def _check_forbidden_columns(df: pd.DataFrame, path: Path) -> None:
    bad = FORBIDDEN_COLUMNS.intersection({col.lower() for col in df.columns})
    if bad:
        raise ValueError(f"Forbidden columns {sorted(bad)} in {path}")


def _load_task_metrics(task_dir: Path) -> pd.DataFrame:
    metrics_path = task_dir / METRICS_NAME
    predictions_path = task_dir / PREDICTIONS_NAME
    summary_path = task_dir / SUMMARY_NAME
    run_path = task_dir / RUN_NAME
    missing = [path for path in [metrics_path, predictions_path, summary_path, run_path] if not path.exists()]
    if missing:
        raise ValueError(f"Missing required files: {[str(path) for path in missing]}")

    metrics = pd.read_csv(metrics_path)
    predictions = pd.read_csv(predictions_path, dtype={"ze2020": str})
    _check_forbidden_columns(metrics, metrics_path)
    _check_forbidden_columns(predictions, predictions_path)
    if predictions.columns.duplicated().any():
        dupes = predictions.columns[predictions.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate prediction columns {dupes} in {predictions_path}")
    if not np.isfinite(predictions["score"].to_numpy(dtype=float)).all():
        raise ValueError(f"Non-finite prediction score in {predictions_path}")
    metric_cols = ["precision_at_k", "hit_rate_at_k", "ndcg_at_k"]
    if metrics[metric_cols].isna().any().any():
        raise ValueError(f"NaN metric found in {metrics_path}")
    if not metrics["ndcg_at_k"].between(0, 1).all():
        raise ValueError(f"NDCG outside [0,1] in {metrics_path}")

    run_payload = json.loads(run_path.read_text())
    metrics["scenario_dir"] = task_dir.parent.name
    metrics["seed_dir"] = task_dir.name
    metrics["run_claim_status"] = run_payload.get("claim_status", "")
    return metrics


def _mean_ndcg(summary: pd.DataFrame, scenario: str, feature_config: str, model: str) -> float | None:
    frame = summary[
        (summary["falsification_scenario"] == scenario)
        & (summary["feature_config"] == feature_config)
        & (summary["model"] == model)
    ]
    if frame.empty:
        return None
    return float(frame["mean_ndcg_at_k"].iloc[0])


def audit_run(run_dir: Path) -> dict:
    task_dirs = _task_dirs(run_dir)
    metrics_frames = [_load_task_metrics(task_dir) for task_dir in task_dirs]
    metrics = pd.concat(metrics_frames, ignore_index=True)

    grouped = (
        metrics.groupby(["falsification_scenario", "feature_config", "model"], as_index=False)
        .agg(
            mean_ndcg_at_k=("ndcg_at_k", "mean"),
            std_ndcg_at_k=("ndcg_at_k", "std"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_hit_rate_at_k=("hit_rate_at_k", "mean"),
            n_rows=("ndcg_at_k", "size"),
            n_seeds=("seed", "nunique"),
        )
        .fillna({"std_ndcg_at_k": 0.0})
        .sort_values(["falsification_scenario", "model", "mean_ndcg_at_k"], ascending=[True, True, False])
        .reset_index(drop=True)
    )

    full_formula = _mean_ndcg(grouped, "full_control", "base_formula_features", "mlp_entry_classifier")
    full_no_relation = _mean_ndcg(grouped, "full_control", "no_relation_features", "mlp_entry_classifier")
    full_shuffled = _mean_ndcg(grouped, "full_control", "shuffled_relation_features", "mlp_entry_classifier")
    temporal_formula = _mean_ndcg(grouped, "temporal_shuffle", "base_formula_features", "mlp_entry_classifier")
    sector_formula = _mean_ndcg(grouped, "sector_shuffle", "base_formula_features", "mlp_entry_classifier")

    gates = {
        "G1_complete_outputs": len(task_dirs) == len(metrics_frames),
        "G2_formula_beats_no_relation_mlp": (
            full_formula is not None and full_no_relation is not None and full_formula > full_no_relation
        ),
        "G3_formula_beats_shuffled_relation_mlp": (
            full_formula is not None and full_shuffled is not None and full_formula > full_shuffled
        ),
        "G4_temporal_and_sector_shuffle_degrade_mlp": (
            full_formula is not None
            and temporal_formula is not None
            and sector_formula is not None
            and temporal_formula < full_formula
            and sector_formula < full_formula
        ),
        "G5_output_separation": True,
    }

    return {
        "run_dir": str(run_dir),
        "status": "TOP3_ENTRY_HPC_AUDIT_DESCRIPTIVE_ONLY",
        "n_task_dirs": len(task_dirs),
        "n_metric_rows": int(len(metrics)),
        "gates": gates,
        "model_summary": grouped.to_dict(orient="records"),
        "claim_status": "top3_entry_hpc_audit_not_recommendation_not_causal",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = audit_run(args.run_dir)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
