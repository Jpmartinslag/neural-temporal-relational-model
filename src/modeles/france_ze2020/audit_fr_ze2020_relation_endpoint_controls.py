"""
HERALD -- France ZE2020 relation endpoint-control audit.

Runs the local dynamic relation learner across pair feature modes and reports
whether source-target compatibility beats source-only and target-only shortcuts.

No causal claim. No recommendation. No validated graph-model claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    CLAIM_STATUS as RELATION_LEARNER_CLAIM_STATUS,
    DEFAULT_EDGES_PATH,
    DEFAULT_EVAL_YEARS,
    PAIR_FEATURE_MODES,
    load_edges,
    load_nodes,
    run_dynamic_relation_learner,
    summarize_metrics,
)

DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_PAIR_MODES = ["both", "source_only", "target_only", "compatibility_only"]
DEFAULT_SCENARIOS = [
    "pair_distance_hard_negatives",
    "source_preserving_endpoint_matched_negatives",
    "target_preserving_endpoint_matched_negatives",
    "source_distance_target_preserving_negatives",
    "dual_profile_hard_negatives",
    "dual_endpoint_matched_negatives",
    "dual_endpoint_temporal_sector_shuffle",
    "dual_profile_temporal_sector_shuffle",
]
CLAIM_STATUS = "relation_endpoint_control_audit_exploratory_not_recommendation"


def run_endpoint_control_audit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenarios: list[str] = DEFAULT_SCENARIOS,
    pair_modes: list[str] = DEFAULT_PAIR_MODES,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    feature_family: str = "sector_position_no_rank",
    node_feature_lag: int = 1,
    positive_edge_states: list[str] | None = None,
    test_pair_mode: str = "unseen_pair",
    seed: int = 42,
    max_iter: int = 300,
    k: int = 80,
    margin_threshold: float = 0.02,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if margin_threshold < 0:
        raise ValueError("margin_threshold must be >= 0")
    unknown_modes = sorted(set(pair_modes) - set(PAIR_FEATURE_MODES))
    if unknown_modes:
        raise ValueError(f"Unknown pair feature mode(s): {unknown_modes}")

    summary_frames = []
    for pair_mode in pair_modes:
        _, metrics, _ = run_dynamic_relation_learner(
            nodes,
            edges,
            scenarios=scenarios,
            eval_years=eval_years,
            negative_ratio=1,
            min_train_years=2,
            seed=seed,
            max_iter=max_iter,
            k=k,
            test_pair_mode=test_pair_mode,
            node_feature_lag=node_feature_lag,
            positive_edge_states=positive_edge_states,
            feature_family=feature_family,
            pair_feature_mode=pair_mode,
        )
        summary = summarize_metrics(metrics)
        relation_rows = summary[summary["model"] == "relation_logit"].copy()
        summary_frames.append(relation_rows)

    pair_summary = pd.concat(summary_frames, ignore_index=True)
    metric_cols = ["mean_roc_auc", "mean_average_precision", "mean_precision_at_k"]
    index_cols = [
        "falsification_scenario",
        "negative_strategy",
        "test_pair_mode",
        "node_feature_lag",
        "positive_edge_states",
        "feature_family",
    ]
    wide = pair_summary.pivot_table(
        index=index_cols,
        columns="pair_feature_mode",
        values=metric_cols,
        aggfunc="first",
    )
    wide.columns = [f"{metric}_{mode}" for metric, mode in wide.columns]
    wide = wide.reset_index()

    source_ap = wide.get("mean_average_precision_source_only")
    target_ap = wide.get("mean_average_precision_target_only")
    compatibility_ap = wide.get("mean_average_precision_compatibility_only")
    both_ap = wide.get("mean_average_precision_both")
    if source_ap is None or target_ap is None or compatibility_ap is None or both_ap is None:
        raise ValueError("Endpoint audit requires both/source_only/target_only/compatibility_only modes")

    wide["best_endpoint_ap"] = pd.concat([source_ap, target_ap], axis=1).max(axis=1)
    wide["compatibility_minus_best_endpoint_ap"] = compatibility_ap - wide["best_endpoint_ap"]
    wide["both_minus_best_endpoint_ap"] = both_ap - wide["best_endpoint_ap"]
    wide["compatibility_gate_pass"] = (
        wide["compatibility_minus_best_endpoint_ap"] >= float(margin_threshold)
    ).astype(int)
    wide["both_gate_pass"] = (wide["both_minus_best_endpoint_ap"] >= float(margin_threshold)).astype(int)
    wide["margin_threshold"] = float(margin_threshold)
    wide["claim_status"] = CLAIM_STATUS
    return pair_summary, wide


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit whether relation compatibility beats endpoint-only shortcuts."
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--scenarios", nargs="+", default=DEFAULT_SCENARIOS)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--feature-family", default="sector_position_no_rank")
    parser.add_argument("--node-feature-lag", type=int, default=1)
    parser.add_argument("--positive-edge-states", nargs="*", default=["new_relation"])
    parser.add_argument("--test-pair-mode", default="unseen_pair")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iter", type=int, default=300)
    parser.add_argument("--k", type=int, default=80)
    parser.add_argument("--margin-threshold", type=float, default=0.02)
    args = parser.parse_args()

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    pair_summary, endpoint_summary = run_endpoint_control_audit(
        nodes=nodes,
        edges=edges,
        scenarios=args.scenarios,
        eval_years=args.eval_years,
        feature_family=args.feature_family,
        node_feature_lag=args.node_feature_lag,
        positive_edge_states=args.positive_edge_states,
        test_pair_mode=args.test_pair_mode,
        seed=args.seed,
        max_iter=args.max_iter,
        k=args.k,
        margin_threshold=args.margin_threshold,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_relation_endpoint_control"
    pair_summary_path = args.output_dir / f"{stem}_pair_summary_v1.csv"
    endpoint_summary_path = args.output_dir / f"{stem}_summary_v1.csv"
    run_path = args.output_dir / f"{stem}_run_v1.json"
    pair_summary.to_csv(pair_summary_path, index=False)
    endpoint_summary.to_csv(endpoint_summary_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "nodes": str(args.nodes),
                "edges": str(args.edges),
                "pair_summary": str(pair_summary_path),
                "endpoint_summary": str(endpoint_summary_path),
                "scenarios": args.scenarios,
                "eval_years": args.eval_years,
                "feature_family": args.feature_family,
                "node_feature_lag": args.node_feature_lag,
                "positive_edge_states": " ".join(args.positive_edge_states or []),
                "test_pair_mode": args.test_pair_mode,
                "margin_threshold": args.margin_threshold,
                "relation_learner_claim_status": RELATION_LEARNER_CLAIM_STATUS,
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(endpoint_summary.to_string(index=False))
    print(f"Wrote {pair_summary_path}")
    print(f"Wrote {endpoint_summary_path}")


if __name__ == "__main__":
    main()
