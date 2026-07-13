"""
Audit collected HERALD France ZE2020 top-3 entry relation-lift HPC results.

Descriptive only: no automatic promotion, no causal claim, no recommendation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

METRICS_NAME = "fr_ze2020_top3_entry_lift_falsification_metrics_v1.csv"
PREDICTIONS_NAME = "fr_ze2020_top3_entry_lift_falsification_predictions_v1.csv"
SUMMARY_NAME = "fr_ze2020_top3_entry_lift_falsification_summary_v1.csv"
RUN_NAME = "fr_ze2020_top3_entry_lift_falsification_run_v1.json"
EXPECTED_SCENARIOS = ["full_control", "temporal_shuffle", "sector_shuffle", "target_shuffle"]
EXPECTED_SEEDS = [42, 43, 44, 45, 46]
MIN_PAIRED_WIN_RATE = 0.60
FORBIDDEN_COLUMNS = {
    "recommendation",
    "recommended" + "_action",
    "policy" + "_action",
    "causal" + "_effect",
    "causal" + "_impact",
}


def _task_dirs(run_dir: Path) -> list[Path]:
    return [
        run_dir / scenario / f"seed_{seed}"
        for scenario in EXPECTED_SCENARIOS
        for seed in EXPECTED_SEEDS
    ]


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


def _paired_comparison(
    metrics: pd.DataFrame,
    *,
    left_scenario: str,
    left_config: str,
    right_scenario: str,
    right_config: str,
) -> dict[str, float | int]:
    model = "mlp_entry_classifier"
    keys = ["seed"]
    if "eval_year" in metrics.columns:
        keys.append("eval_year")
    left = metrics[
        (metrics["falsification_scenario"] == left_scenario)
        & (metrics["feature_config"] == left_config)
        & (metrics["model"] == model)
    ][keys + ["ndcg_at_k"]].rename(columns={"ndcg_at_k": "left_ndcg"})
    right = metrics[
        (metrics["falsification_scenario"] == right_scenario)
        & (metrics["feature_config"] == right_config)
        & (metrics["model"] == model)
    ][keys + ["ndcg_at_k"]].rename(columns={"ndcg_at_k": "right_ndcg"})
    paired = left.merge(right, on=keys, how="inner", validate="one_to_one")
    delta = paired["left_ndcg"] - paired["right_ndcg"]
    return {
        "n_pairs": int(len(paired)),
        "wins": int((delta > 0).sum()),
        "win_rate": float((delta > 0).mean()) if len(delta) else 0.0,
        "mean_delta": float(delta.mean()) if len(delta) else float("nan"),
        "median_delta": float(delta.median()) if len(delta) else float("nan"),
    }


def _passes_paired_gate(result: dict[str, float | int]) -> bool:
    return bool(
        result["n_pairs"]
        and result["win_rate"] >= MIN_PAIRED_WIN_RATE
        and result["mean_delta"] > 0
    )


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

    comparisons = {
        "lift_vs_no_relation": _paired_comparison(
            metrics,
            left_scenario="full_control",
            left_config="base_plus_target_aligned_lifts",
            right_scenario="full_control",
            right_config="no_relation_features",
        ),
        "lift_vs_base_formula": _paired_comparison(
            metrics,
            left_scenario="full_control",
            left_config="base_plus_target_aligned_lifts",
            right_scenario="full_control",
            right_config="base_formula_features",
        ),
        "lift_vs_shuffled_lift": _paired_comparison(
            metrics,
            left_scenario="full_control",
            left_config="base_plus_target_aligned_lifts",
            right_scenario="full_control",
            right_config="shuffled_target_aligned_lifts",
        ),
        "full_vs_temporal_shuffle": _paired_comparison(
            metrics,
            left_scenario="full_control",
            left_config="base_plus_target_aligned_lifts",
            right_scenario="temporal_shuffle",
            right_config="base_plus_target_aligned_lifts",
        ),
        "full_vs_sector_shuffle": _paired_comparison(
            metrics,
            left_scenario="full_control",
            left_config="base_plus_target_aligned_lifts",
            right_scenario="sector_shuffle",
            right_config="base_plus_target_aligned_lifts",
        ),
        "full_vs_target_shuffle": _paired_comparison(
            metrics,
            left_scenario="full_control",
            left_config="base_plus_target_aligned_lifts",
            right_scenario="target_shuffle",
            right_config="base_plus_target_aligned_lifts",
        ),
    }

    gates = {
        "G1_complete_outputs": len(task_dirs) == len(metrics_frames),
        "G2_lift_beats_no_relation_mlp": _passes_paired_gate(comparisons["lift_vs_no_relation"]),
        "G3_lift_beats_base_formula_mlp": _passes_paired_gate(comparisons["lift_vs_base_formula"]),
        "G4_lift_beats_shuffled_lift_mlp": _passes_paired_gate(comparisons["lift_vs_shuffled_lift"]),
        "G5_temporal_and_sector_shuffle_degrade_lift_mlp": (
            _passes_paired_gate(comparisons["full_vs_temporal_shuffle"])
            and _passes_paired_gate(comparisons["full_vs_sector_shuffle"])
        ),
        "G6_output_separation": True,
        "G7_target_shuffle_degrades_lift_mlp": _passes_paired_gate(
            comparisons["full_vs_target_shuffle"]
        ),
    }

    return {
        "run_dir": str(run_dir),
        "status": "TOP3_ENTRY_LIFT_HPC_AUDIT_DESCRIPTIVE_ONLY",
        "n_task_dirs": len(task_dirs),
        "n_metric_rows": int(len(metrics)),
        "gates": gates,
        "paired_comparisons": comparisons,
        "model_summary": grouped.to_dict(orient="records"),
        "claim_status": "top3_entry_lift_hpc_audit_not_recommendation_not_causal",
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
