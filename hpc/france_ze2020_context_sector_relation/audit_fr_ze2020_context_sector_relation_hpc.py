"""Aggregate and audit the DEC-077 five-seed HPC gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_context_conditioned_sector_relation_gate import (
    CLAIM_STATUS,
    VIEW_NAMES,
    audit_gate,
)

EXPECTED_SEEDS = [42, 43, 44, 45, 46]
EXPECTED_YEARS = list(range(2019, 2026))
EXPECTED_FOLDS = list(range(5))
METRICS_NAME = "fr_ze2020_context_conditioned_sector_relation_gate_metrics_v1.csv"
FORBIDDEN_COLUMNS = {
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
}


def load_metrics(run_dir: Path) -> pd.DataFrame:
    frames = []
    for seed in EXPECTED_SEEDS:
        path = run_dir / f"seed_{seed}" / METRICS_NAME
        if not path.exists():
            raise ValueError(f"Missing seed output: {path}")
        frame = pd.read_csv(path)
        forbidden = FORBIDDEN_COLUMNS.intersection(map(str.lower, frame.columns))
        if forbidden:
            raise ValueError(f"Forbidden columns in {path}: {sorted(forbidden)}")
        if set(frame["seed"].unique()) != {seed}:
            raise ValueError(f"Unexpected seed content in {path}")
        frames.append(frame)
    metrics = pd.concat(frames, ignore_index=True)
    key = ["view", "seed", "eval_year", "ze_fold"]
    if metrics.duplicated(key).any():
        raise ValueError("Duplicate metric keys across seed outputs")
    return metrics


def audit_run(run_dir: Path) -> dict[str, object]:
    metrics = load_metrics(run_dir)
    expected_rows = (
        len(VIEW_NAMES)
        * len(EXPECTED_SEEDS)
        * len(EXPECTED_YEARS)
        * len(EXPECTED_FOLDS)
    )
    numeric = ["mae", "r2", "n_train", "n_test", "model_n_iter", "model_converged"]
    integrity = {
        "expected_row_count": len(metrics) == expected_rows,
        "expected_views": set(metrics["view"]) == set(VIEW_NAMES),
        "expected_years": set(metrics["eval_year"]) == set(EXPECTED_YEARS),
        "expected_folds": set(metrics["ze_fold"]) == set(EXPECTED_FOLDS),
        "finite_metrics": bool(
            np.isfinite(metrics[numeric].to_numpy(dtype=float)).all()
        ),
        "zero_ze_overlap": bool(metrics["train_test_ze_overlap"].eq(0).all()),
        "claim_status_consistent": set(metrics["claim_status"]) == {CLAIM_STATUS},
    }
    gate = audit_gate(metrics)
    summary = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_mae=("mae", "mean"),
            mean_r2=("r2", "mean"),
            convergence_rate=("model_converged", "mean"),
            mean_model_n_iter=("model_n_iter", "mean"),
            rows=("mae", "size"),
        )
        .sort_values("view")
    )
    return {
        "status": "CONTEXT_CONDITIONED_SECTOR_RELATION_HPC_AUDIT",
        "run_dir": str(run_dir),
        "n_metric_rows": int(len(metrics)),
        "integrity": integrity,
        "gate": gate,
        "view_summary": summary.to_dict(orient="records"),
        "claim_status": CLAIM_STATUS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
