"""
Audit collected HERALD France ZE2020 dynamic graph ranker/falsification results.

Descriptive only: no automatic promotion, no causal claim, no recommendation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

FORBIDDEN_COLUMNS = {"recommendation", "recommended_action", "policy_action", "causal_effect", "causal_impact"}

RANKER_PATTERNS = {
    "predictions": ["fr_ze2020_dynamic_graph_ranker_*y_predictions_v1.csv"],
    "metrics": ["fr_ze2020_dynamic_graph_ranker_*y_metrics_v1.csv"],
}

FALSIFICATION_PATTERNS = {
    "predictions": ["fr_ze2020_dynamic_graph_falsification_*y_predictions_v1.csv"],
    "metrics": ["fr_ze2020_dynamic_graph_falsification_*y_metrics_v1.csv"],
    "summary": ["fr_ze2020_dynamic_graph_falsification_*y_summary_v1.csv"],
    "manifest": ["fr_ze2020_dynamic_graph_falsification_*y_manifest_v1.csv"],
    "run": ["fr_ze2020_dynamic_graph_falsification_*y_run_v1.json"],
}


def _first_match(seed_dir: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(seed_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _seed_dirs(run_dir: Path, metrics_patterns: list[str], predictions_patterns: list[str]) -> list[Path]:
    seed_dirs = sorted(p for p in run_dir.glob("seed_*") if p.is_dir())
    if seed_dirs:
        return seed_dirs
    if _first_match(run_dir, metrics_patterns) and _first_match(run_dir, predictions_patterns):
        return [run_dir]
    raise ValueError(f"No seed_* directories or direct dynamic graph outputs found in {run_dir}")


def _load_metrics_and_check(seed_dir: Path, metrics_path: Path, predictions_path: Path) -> pd.DataFrame:
    metrics = pd.read_csv(metrics_path)
    predictions = pd.read_csv(predictions_path, dtype={"ze2020": str})
    for path, df in [(metrics_path, metrics), (predictions_path, predictions)]:
        bad_cols = FORBIDDEN_COLUMNS & {c.lower() for c in df.columns}
        if bad_cols:
            raise ValueError(f"Forbidden columns {bad_cols} in {path}")
        if df.columns.duplicated().any():
            dupes = df.columns[df.columns.duplicated()].tolist()
            raise ValueError(f"Duplicate columns {dupes} in {path}")
    if not np.isfinite(predictions["score"].to_numpy(dtype=float)).all():
        raise ValueError(f"Non-finite score found in {predictions_path}")
    metric_cols = ["precision_at_k", "hit_rate_at_k", "ndcg_at_k"]
    if metrics[metric_cols].isna().any().any():
        raise ValueError(f"NaN found in dynamic graph metrics: {metrics_path}")
    if not metrics["ndcg_at_k"].between(0, 1).all():
        raise ValueError(f"NDCG outside [0,1] in {metrics_path}")
    metrics["seed_dir"] = seed_dir.name
    return metrics


def audit_ranker(run_dir: Path) -> dict:
    seed_dirs = _seed_dirs(run_dir, RANKER_PATTERNS["metrics"], RANKER_PATTERNS["predictions"])
    missing = []
    frames = []
    for seed_dir in seed_dirs:
        metrics_path = _first_match(seed_dir, RANKER_PATTERNS["metrics"])
        predictions_path = _first_match(seed_dir, RANKER_PATTERNS["predictions"])
        if metrics_path is None:
            missing.append(str(seed_dir / "<dynamic graph ranker metrics csv>"))
        if predictions_path is None:
            missing.append(str(seed_dir / "<dynamic graph ranker predictions csv>"))
        if metrics_path and predictions_path:
            frames.append(_load_metrics_and_check(seed_dir, metrics_path, predictions_path))
    if missing:
        raise ValueError(f"Missing required files: {missing}")

    all_metrics = pd.concat(frames, ignore_index=True)
    grouped = (
        all_metrics.groupby("model")
        .agg(
            mean_ndcg_at_k=("ndcg_at_k", "mean"),
            std_ndcg_at_k=("ndcg_at_k", "std"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_hit_rate_at_k=("hit_rate_at_k", "mean"),
            n_rows=("ndcg_at_k", "size"),
        )
        .fillna({"std_ndcg_at_k": 0.0})
        .reset_index()
        .sort_values("mean_ndcg_at_k", ascending=False)
    )
    return {
        "run_dir": str(run_dir),
        "n_seed_dirs": len(seed_dirs),
        "status": "DYNAMIC_GRAPH_RANKER_AUDIT_DESCRIPTIVE_ONLY",
        "top_model_by_mean_ndcg": grouped.iloc[0]["model"] if not grouped.empty else None,
        "model_summary": grouped.to_dict(orient="records"),
        "claim_status": "dynamic_graph_exploratory_not_recommendation_not_causal",
    }


def audit_falsification(run_dir: Path) -> dict:
    seed_dirs = _seed_dirs(run_dir, FALSIFICATION_PATTERNS["metrics"], FALSIFICATION_PATTERNS["predictions"])
    missing = []
    frames = []
    for seed_dir in seed_dirs:
        metrics_path = _first_match(seed_dir, FALSIFICATION_PATTERNS["metrics"])
        predictions_path = _first_match(seed_dir, FALSIFICATION_PATTERNS["predictions"])
        if metrics_path is None:
            missing.append(str(seed_dir / "<dynamic graph falsification metrics csv>"))
        if predictions_path is None:
            missing.append(str(seed_dir / "<dynamic graph falsification predictions csv>"))
        for key in ["summary", "manifest", "run"]:
            if _first_match(seed_dir, FALSIFICATION_PATTERNS[key]) is None:
                missing.append(str(seed_dir / f"<dynamic graph falsification {key}>"))
        if metrics_path and predictions_path:
            frames.append(_load_metrics_and_check(seed_dir, metrics_path, predictions_path))
    if missing:
        raise ValueError(f"Missing required files: {missing}")

    all_metrics = pd.concat(frames, ignore_index=True)
    grouped = (
        all_metrics.groupby(["falsification_scenario", "model"])
        .agg(
            mean_ndcg_at_k=("ndcg_at_k", "mean"),
            std_ndcg_at_k=("ndcg_at_k", "std"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_hit_rate_at_k=("hit_rate_at_k", "mean"),
            n_rows=("ndcg_at_k", "size"),
        )
        .fillna({"std_ndcg_at_k": 0.0})
        .reset_index()
        .sort_values(["falsification_scenario", "mean_ndcg_at_k"], ascending=[True, False])
    )
    top_by_scenario = (
        grouped.groupby("falsification_scenario")
        .head(1)[["falsification_scenario", "model", "mean_ndcg_at_k"]]
        .to_dict(orient="records")
    )
    return {
        "run_dir": str(run_dir),
        "n_seed_dirs": len(seed_dirs),
        "status": "DYNAMIC_GRAPH_FALSIFICATION_AUDIT_DESCRIPTIVE_ONLY",
        "top_by_scenario": top_by_scenario,
        "model_summary": grouped.to_dict(orient="records"),
        "claim_status": "dynamic_graph_falsification_exploratory_not_recommendation_not_causal",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--mode", choices=["ranker", "falsification"], required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = audit_ranker(args.run_dir) if args.mode == "ranker" else audit_falsification(args.run_dir)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
