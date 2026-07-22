"""Isolate ZE2020 graph edge families under the DEC-070 transfer gate."""

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

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    EXPANDING_EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_relation_embedding_linear_probes import (  # noqa: E402
    BASE_FEATURE_COLUMNS,
    _graph_columns,
    random_endpoint_placebo,
)
from src.modeles.france_ze2020.run_fr_ze2020_relational_transition_transfer_probe import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    DEFAULT_SEEDS,
    add_graph_changes,
    assign_ze_folds,
    evaluate_transfer_view,
    shuffle_sector_alignment,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_encoder import (  # noqa: E402
    build_dense_graph_signal_embeddings,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    load_edges,
    load_nodes,
)

CLAIM_STATUS = "edge_family_isolation_probe_exploratory_not_recommendation"
EDGE_FAMILIES = ["ze_similarity", "cross_ze_same_sector", "intra_ze_sector"]
VARIANTS = {
    "ze_similarity_only": ["ze_similarity"],
    "cross_ze_same_sector_only": ["cross_ze_same_sector"],
    "intra_ze_sector_only": ["intra_ze_sector"],
    "economic_sector_balanced": ["cross_ze_same_sector", "intra_ze_sector"],
    "all_families_balanced": EDGE_FAMILIES,
}
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def prefix_family_embedding(embedding: pd.DataFrame, family: str) -> pd.DataFrame:
    """Give one family an independent, collision-free feature block."""
    rename = {
        column: column.replace("relation_graph_", f"relation_graph_{family}__", 1)
        for column in _graph_columns(embedding)
    }
    return embedding[["node_id", "decision_year", *rename]].rename(columns=rename)


def build_balanced_family_frame(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    families: list[str],
    *,
    seed: int,
    randomize_endpoints: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    """Build equal-schema per-family blocks and return their change features."""
    frame = nodes.copy()
    for offset, family in enumerate(families):
        family_edges = edges[edges["edge_type"] == family].copy()
        if family_edges.empty:
            raise ValueError(f"No edges for family: {family}")
        if randomize_endpoints:
            family_edges = random_endpoint_placebo(family_edges, seed=seed + offset * 101)
        embedding = build_dense_graph_signal_embeddings(nodes, family_edges)
        block = prefix_family_embedding(embedding, family)
        frame = frame.merge(
            block,
            on=["node_id", "decision_year"],
            how="left",
            validate="one_to_one",
        )
    graph_columns = _graph_columns(frame)
    frame[graph_columns] = frame[graph_columns].fillna(0.0)
    changed, degree_features, relation_features = add_graph_changes(frame)
    return changed, [*BASE_FEATURE_COLUMNS, *degree_features, *relation_features]


def _summary(metrics: pd.DataFrame) -> pd.DataFrame:
    summary = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_ndcg_at_3=("ndcg_at_3", "mean"),
            mean_precision_at_3=("precision_at_3", "mean"),
            mean_hit_rate_at_3=("hit_rate_at_3", "mean"),
            mean_average_precision=("average_precision", "mean"),
            n_paired_evaluations=("ndcg_at_3", "size"),
            n_seeds=("seed", "nunique"),
        )
        .sort_values("view")
        .reset_index(drop=True)
    )
    summary["claim_status"] = CLAIM_STATUS
    return summary


def evaluate_family_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]

    def compare(real_name: str, control_name: str) -> dict[str, float]:
        real = metrics[metrics["view"] == real_name][keys + ["ndcg_at_3"]].rename(
            columns={"ndcg_at_3": "real"}
        )
        control = metrics[metrics["view"] == control_name][keys + ["ndcg_at_3"]].rename(
            columns={"ndcg_at_3": "control"}
        )
        paired = real.merge(control, on=keys, how="inner", validate="one_to_one")
        delta = paired["real"] - paired["control"]
        return {
            "mean_ndcg_lift": float(delta.mean()),
            "paired_win_rate": float((delta > 0).mean()),
            "n_pairs": int(len(paired)),
        }

    comparisons: dict[str, dict[str, dict[str, float]]] = {}
    passing_variants = []
    for variant in VARIANTS:
        node = compare(variant, "node_only")
        endpoint = compare(variant, f"{variant}__endpoint_randomized")
        result = {"vs_node_only": node, "vs_endpoint_randomized": endpoint}
        passes = node["mean_ndcg_lift"] > 0 and (
            endpoint["mean_ndcg_lift"] > 0 and endpoint["paired_win_rate"] >= 0.60
        )
        if variant == "economic_sector_balanced":
            sector = compare(variant, "economic_sector_balanced__sector_shuffled")
            result["vs_sector_shuffled"] = sector
            passes = passes and sector["mean_ndcg_lift"] > 0
        comparisons[variant] = result
        if passes:
            passing_variants.append(variant)
    return {
        "gate_pass": bool(passing_variants),
        "passing_variants": passing_variants,
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def run_edge_family_probe(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object], pd.DataFrame]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    nodes = nodes.copy()
    nodes["ze2020"] = nodes["ze2020"].astype(str).str.zfill(4)
    nodes["ze_fold"] = assign_ze_folds(nodes)
    counts = (
        edges.groupby("edge_type", as_index=False)
        .size()
        .rename(columns={"size": "edge_rows"})
        .sort_values("edge_type")
    )
    rows: list[dict[str, object]] = []

    for seed in seeds:
        rows.extend(
            evaluate_transfer_view(
                nodes,
                view_name="node_only",
                feature_columns=list(BASE_FEATURE_COLUMNS),
                seed=seed,
                eval_years=eval_years,
                claim_status=CLAIM_STATUS,
            )
        )
        for variant, families in VARIANTS.items():
            real, features = build_balanced_family_frame(
                nodes, edges, families, seed=seed
            )
            randomized, randomized_features = build_balanced_family_frame(
                nodes, edges, families, seed=seed + 5000, randomize_endpoints=True
            )
            if features != randomized_features:
                raise AssertionError(f"Feature mismatch for {variant}")
            rows.extend(
                evaluate_transfer_view(
                    real,
                    view_name=variant,
                    feature_columns=features,
                    seed=seed,
                    eval_years=eval_years,
                    claim_status=CLAIM_STATUS,
                )
            )
            rows.extend(
                evaluate_transfer_view(
                    randomized,
                    view_name=f"{variant}__endpoint_randomized",
                    feature_columns=randomized_features,
                    seed=seed,
                    eval_years=eval_years,
                    claim_status=CLAIM_STATUS,
                )
            )
            if variant == "economic_sector_balanced":
                relation_changes = [
                    column
                    for column in features
                    if column.startswith("delta__relation_graph_")
                    and not column.endswith("_count")
                ]
                shuffled = shuffle_sector_alignment(
                    real, relation_changes, seed=seed + 9000
                )
                rows.extend(
                    evaluate_transfer_view(
                        shuffled,
                        view_name="economic_sector_balanced__sector_shuffled",
                        feature_columns=features,
                        seed=seed,
                        eval_years=eval_years,
                        claim_status=CLAIM_STATUS,
                    )
                )

    metrics = pd.DataFrame(rows).sort_values(
        ["view", "seed", "eval_year", "ze_fold"]
    ).reset_index(drop=True)
    numeric = ["ndcg_at_3", "precision_at_3", "hit_rate_at_3", "average_precision"]
    if metrics.empty or not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Missing or non-finite edge-family metrics")
    return metrics, _summary(metrics), evaluate_family_gate(metrics), counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=EXPANDING_EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()

    joined = f"{args.nodes}\n{args.edges}"
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")

    metrics, summary, gate, counts = run_edge_family_probe(
        load_nodes(args.nodes),
        load_edges(args.edges),
        eval_years=args.eval_years,
        seeds=args.seeds,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_edge_family_isolation_probe"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    counts.to_csv(args.output_dir / f"{stem}_edge_counts_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
