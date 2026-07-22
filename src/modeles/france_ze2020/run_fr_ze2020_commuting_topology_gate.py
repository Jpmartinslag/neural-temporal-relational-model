#!/usr/bin/env python3
"""Gate uniform commuting topology against matched endpoint placebos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_commuting_strict_ex_ante_edges import (  # noqa: E402
    STRICT_EDGES_OUT_PATH,
)
from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_commuting_relation_gate import (  # noqa: E402
    AVAILABILITY_FEATURE,
    TOPOLOGY_FEATURES,
    build_commuting_feature_frame,
    load_commuting_edges,
    make_edge_variant,
)
from src.modeles.france_ze2020.run_fr_ze2020_relation_embedding_linear_probes import (  # noqa: E402
    BASE_FEATURE_COLUMNS,
)
from src.modeles.france_ze2020.run_fr_ze2020_relational_transition_transfer_probe import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    DEFAULT_SEEDS,
    assign_ze_folds,
    evaluate_transfer_view,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    load_nodes,
)

CLAIM_STATUS = "commuting_topology_gate_exploratory_not_recommendation"
VIEW_NAMES = [
    "node_only",
    "commuting_availability_only",
    "commuting_topology_degree_only",
    "commuting_topology_real_uniform",
    "commuting_topology_endpoint_randomized_uniform",
    "commuting_topology_reversed_uniform",
    "commuting_topology_target_shuffled",
]
DETERMINISTIC_CONTROLS = {
    "node_only",
    "commuting_availability_only",
    "commuting_topology_degree_only",
    "commuting_topology_reversed_uniform",
}


def uniform_variant(edges: pd.DataFrame, *, endpoint_seed: int | None = None) -> pd.DataFrame:
    candidate = edges
    if endpoint_seed is not None:
        candidate = make_edge_variant(
            candidate, "endpoint_randomized", seed=endpoint_seed
        )
    return make_edge_variant(candidate, "uniform_weights")


def reversed_uniform_variant(edges: pd.DataFrame) -> pd.DataFrame:
    return make_edge_variant(
        make_edge_variant(edges, "reversed_direction"), "uniform_weights"
    )


def _summary(metrics: pd.DataFrame) -> pd.DataFrame:
    out = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_ndcg_at_3=("ndcg_at_3", "mean"),
            mean_precision_at_3=("precision_at_3", "mean"),
            mean_hit_rate_at_3=("hit_rate_at_3", "mean"),
            mean_average_precision=("average_precision", "mean"),
            n_evaluations=("ndcg_at_3", "size"),
            n_seeds=("seed", "nunique"),
        )
        .sort_values("view")
        .reset_index(drop=True)
    )
    out["claim_status"] = CLAIM_STATUS
    return out


def validate_populations(metrics: pd.DataFrame) -> None:
    keys = ["seed", "eval_year", "ze_fold"]
    columns = [*keys, "n_train", "n_test", "n_test_positive"]
    reference = (
        metrics[metrics["view"] == "commuting_topology_real_uniform"][columns]
        .sort_values(keys)
        .reset_index(drop=True)
    )
    if reference.duplicated(keys).any():
        raise ValueError("Duplicate topology-real evaluation key")
    for view in VIEW_NAMES:
        candidate = (
            metrics[metrics["view"] == view][columns]
            .sort_values(keys)
            .reset_index(drop=True)
        )
        if not reference.equals(candidate):
            raise ValueError(f"Evaluation population differs for view: {view}")


def evaluate_topology_gate(metrics: pd.DataFrame) -> dict[str, object]:
    def compare(control: str) -> dict[str, float]:
        keys = ["seed", "eval_year", "ze_fold"]
        real = metrics[metrics["view"] == "commuting_topology_real_uniform"][
            [*keys, "ndcg_at_3"]
        ].rename(columns={"ndcg_at_3": "real"})
        other = metrics[metrics["view"] == control][[*keys, "ndcg_at_3"]].rename(
            columns={"ndcg_at_3": "control"}
        )
        paired = real.merge(other, on=keys, validate="one_to_one")
        if control in DETERMINISTIC_CONTROLS:
            unique_keys = ["eval_year", "ze_fold"]
            variation = paired.groupby(unique_keys)[["real", "control"]].nunique()
            if (variation > 1).any().any():
                raise ValueError(f"Deterministic view varies across seeds: {control}")
            paired = paired.drop_duplicates(unique_keys)
        delta = paired["real"] - paired["control"]
        return {
            "mean_ndcg_lift": float(delta.mean()),
            "paired_win_rate": float((delta > 0).mean()),
            "n_pairs": int(len(delta)),
        }

    controls = [view for view in VIEW_NAMES if view != "commuting_topology_real_uniform"]
    comparisons = {view: compare(view) for view in controls}
    endpoint = comparisons["commuting_topology_endpoint_randomized_uniform"]
    gate_pass = (
        comparisons["node_only"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_availability_only"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_topology_degree_only"]["mean_ndcg_lift"] > 0
        and endpoint["mean_ndcg_lift"] > 0
        and endpoint["paired_win_rate"] >= 0.60
        and comparisons["commuting_topology_reversed_uniform"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_topology_target_shuffled"]["mean_ndcg_lift"] > 0
    )
    return {
        "gate_pass": bool(gate_pass),
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def run_topology_gate(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    nodes = nodes.copy()
    nodes["ze2020"] = nodes["ze2020"].astype(str).str.zfill(4)
    nodes["ze_fold"] = assign_ze_folds(nodes)

    real, relation_features = build_commuting_feature_frame(
        nodes, uniform_variant(edges)
    )
    reversed_frame, reversed_features = build_commuting_feature_frame(
        nodes, reversed_uniform_variant(edges)
    )
    if relation_features != reversed_features:
        raise AssertionError("Topology feature schemas differ")
    full_features = [*BASE_FEATURE_COLUMNS, *relation_features]
    degree_features = [
        *BASE_FEATURE_COLUMNS,
        AVAILABILITY_FEATURE,
        *TOPOLOGY_FEATURES,
    ]
    availability_features = [*BASE_FEATURE_COLUMNS, AVAILABILITY_FEATURE]
    rows: list[dict[str, object]] = []

    for seed in seeds:
        endpoint_frame, endpoint_features = build_commuting_feature_frame(
            nodes, uniform_variant(edges, endpoint_seed=seed + 7000)
        )
        if endpoint_features != relation_features:
            raise AssertionError("Endpoint topology feature schema differs")
        configurations = [
            ("node_only", real, list(BASE_FEATURE_COLUMNS), False),
            ("commuting_availability_only", real, availability_features, False),
            ("commuting_topology_degree_only", real, degree_features, False),
            ("commuting_topology_real_uniform", real, full_features, False),
            (
                "commuting_topology_endpoint_randomized_uniform",
                endpoint_frame,
                full_features,
                False,
            ),
            (
                "commuting_topology_reversed_uniform",
                reversed_frame,
                full_features,
                False,
            ),
            (
                "commuting_topology_target_shuffled",
                real,
                full_features,
                True,
            ),
        ]
        for view, frame, features, shuffle_target in configurations:
            rows.extend(
                evaluate_transfer_view(
                    frame,
                    view_name=view,
                    feature_columns=features,
                    seed=seed,
                    eval_years=eval_years,
                    shuffle_target=shuffle_target,
                    claim_status=CLAIM_STATUS,
                )
            )

    metrics = pd.DataFrame(rows).sort_values(
        ["view", "seed", "eval_year", "ze_fold"]
    ).reset_index(drop=True)
    numeric = ["ndcg_at_3", "precision_at_3", "hit_rate_at_3", "average_precision"]
    if metrics.empty or not np.isfinite(metrics[numeric].to_numpy(float)).all():
        raise ValueError("Missing or non-finite topology-gate metric")
    validate_populations(metrics)
    return metrics, _summary(metrics), evaluate_topology_gate(metrics)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--commuting-edges", type=Path, default=STRICT_EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()

    metrics, summary, gate = run_topology_gate(
        load_nodes(args.nodes),
        load_commuting_edges(args.commuting_edges),
        eval_years=args.eval_years,
        seeds=args.seeds,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_commuting_topology_gate"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
