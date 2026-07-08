"""
HERALD -- France ZE2020 dynamic relation encoder prototype.

Uses the HERALD_27/28 relation objective to produce learned source-target
compatibility scores and node-level relation embeddings.

No causal claim. No automatic recommendation. No validated dynamic-GNN claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    EXPANDING_EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    DEFAULT_EDGES_PATH,
    load_edges,
    load_nodes,
    run_dynamic_relation_learner,
)

DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_EVAL_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
DEFAULT_SCENARIO = "dual_endpoint_matched_negatives"
CLAIM_STATUS = "dynamic_relation_encoder_prototype_exploratory_not_recommendation"
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def _topk_mean(values: pd.Series, k: int = 3) -> float:
    if values.empty:
        return 0.0
    return float(values.nlargest(min(k, len(values))).mean())


def _score_metrics(scored_edges: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in scored_edges.groupby("decision_year"):
        if frame["relation_label"].nunique() < 2:
            continue
        labels = frame["relation_label"].astype(int)
        scores = frame["relation_score"].astype(float)
        rows.append(
            {
                "eval_year": int(year),
                "model": "dynamic_relation_encoder",
                "average_precision": float(average_precision_score(labels, scores)),
                "roc_auc": float(roc_auc_score(labels, scores)),
                "n_rows": int(len(frame)),
                "n_positive": int(labels.sum()),
                "claim_status": CLAIM_STATUS,
            }
        )
    if not rows:
        raise ValueError("No relation encoder metric rows were produced")
    metrics = pd.DataFrame(rows)
    metrics.loc[len(metrics)] = {
        "eval_year": "mean",
        "model": "dynamic_relation_encoder",
        "average_precision": float(np.average(metrics["average_precision"], weights=metrics["n_rows"])),
        "roc_auc": float(np.average(metrics["roc_auc"], weights=metrics["n_rows"])),
        "n_rows": int(metrics["n_rows"].sum()),
        "n_positive": int(metrics["n_positive"].sum()),
        "claim_status": CLAIM_STATUS,
    }
    return metrics


def _relation_score_edges(predictions: pd.DataFrame) -> pd.DataFrame:
    scored = predictions[predictions["model"] == "relation_logit"].copy()
    if scored.empty:
        raise ValueError("No relation_logit predictions available for relation encoder")
    scored = scored.rename(columns={"score": "relation_score"})
    scored["relation_score"] = scored["relation_score"].astype(float).clip(0.0, 1.0)
    scored["relation_rank_in_year_type"] = scored.groupby(["decision_year", "edge_type"])[
        "relation_score"
    ].rank(ascending=False, method="first")
    scored["claim_status"] = CLAIM_STATUS
    return scored[
        [
            "source_node_id",
            "target_node_id",
            "decision_year",
            "node_feature_year",
            "edge_type",
            "edge_state",
            "relation_label",
            "sample_role",
            "relation_score",
            "relation_rank_in_year_type",
            "falsification_scenario",
            "negative_strategy",
            "feature_family",
            "pair_feature_mode",
            "claim_status",
        ]
    ].sort_values(["decision_year", "edge_type", "relation_rank_in_year_type"])


def build_relation_node_embeddings(nodes: pd.DataFrame, scored_edges: pd.DataFrame) -> pd.DataFrame:
    base = nodes[["node_id", "ze2020", "sector_code", "decision_year"]].copy()
    base["ze2020"] = base["ze2020"].astype(str).str.zfill(4)

    incoming = (
        scored_edges.groupby(["target_node_id", "decision_year"])
        .agg(
            relation_in_score_mean=("relation_score", "mean"),
            relation_in_score_max=("relation_score", "max"),
            relation_in_score_top3_mean=("relation_score", _topk_mean),
            relation_in_count=("relation_score", "size"),
        )
        .reset_index()
        .rename(columns={"target_node_id": "node_id"})
    )
    outgoing = (
        scored_edges.groupby(["source_node_id", "decision_year"])
        .agg(
            relation_out_score_mean=("relation_score", "mean"),
            relation_out_score_max=("relation_score", "max"),
            relation_out_score_top3_mean=("relation_score", _topk_mean),
            relation_out_count=("relation_score", "size"),
        )
        .reset_index()
        .rename(columns={"source_node_id": "node_id"})
    )
    by_type = (
        scored_edges.pivot_table(
            index=["target_node_id", "decision_year"],
            columns="edge_type",
            values="relation_score",
            aggfunc="mean",
            fill_value=0.0,
        )
        .reset_index()
        .rename(columns={"target_node_id": "node_id"})
    )
    by_type.columns = [
        f"relation_in_{col}_score_mean" if col not in {"node_id", "decision_year"} else col
        for col in by_type.columns
    ]

    embeddings = base.merge(incoming, on=["node_id", "decision_year"], how="left")
    embeddings = embeddings.merge(outgoing, on=["node_id", "decision_year"], how="left")
    embeddings = embeddings.merge(by_type, on=["node_id", "decision_year"], how="left")
    relation_cols = [col for col in embeddings.columns if col.startswith("relation_")]
    embeddings[relation_cols] = embeddings[relation_cols].fillna(0.0)
    embeddings["relation_embedding_available"] = (
        (embeddings["relation_in_count"] > 0) | (embeddings["relation_out_count"] > 0)
    ).astype(int)
    embeddings["claim_status"] = CLAIM_STATUS
    return embeddings.sort_values(["decision_year", "node_id"]).reset_index(drop=True)


def build_dense_graph_signal_embeddings(nodes: pd.DataFrame, graph_edges: pd.DataFrame) -> pd.DataFrame:
    """Aggregate audited dynamic-graph edge memory into dense node-year signals.

    The learned relation objective is intentionally sparse because it scores only
    controlled evaluation pairs. These graph-memory aggregates keep a dense,
    time-respecting representation available for downstream ranking without using labels.
    """
    base = nodes[["node_id", "decision_year"]].copy()
    if graph_edges.empty:
        base["relation_graph_embedding_available"] = 0
        return base

    edges = graph_edges.copy()
    edges["edge_weight"] = edges["edge_weight"].astype(float)
    edges["signal_strength"] = edges["signal_strength"].astype(float)
    edges["stability_score"] = edges["stability_score"].astype(float)

    incoming = (
        edges.groupby(["target_node_id", "decision_year"])
        .agg(
            relation_graph_in_weight_mean=("edge_weight", "mean"),
            relation_graph_in_weight_abs_sum=("edge_weight", lambda s: float(s.abs().sum())),
            relation_graph_in_signal_mean=("signal_strength", "mean"),
            relation_graph_in_stability_mean=("stability_score", "mean"),
            relation_graph_in_count=("edge_weight", "size"),
        )
        .reset_index()
        .rename(columns={"target_node_id": "node_id"})
    )
    outgoing = (
        edges.groupby(["source_node_id", "decision_year"])
        .agg(
            relation_graph_out_weight_mean=("edge_weight", "mean"),
            relation_graph_out_weight_abs_sum=("edge_weight", lambda s: float(s.abs().sum())),
            relation_graph_out_signal_mean=("signal_strength", "mean"),
            relation_graph_out_stability_mean=("stability_score", "mean"),
            relation_graph_out_count=("edge_weight", "size"),
        )
        .reset_index()
        .rename(columns={"source_node_id": "node_id"})
    )

    by_type = (
        edges.pivot_table(
            index=["target_node_id", "decision_year"],
            columns="edge_type",
            values="edge_weight",
            aggfunc="mean",
            fill_value=0.0,
        )
        .reset_index()
        .rename(columns={"target_node_id": "node_id"})
    )
    by_type.columns = [
        f"relation_graph_in_{col}_weight_mean" if col not in {"node_id", "decision_year"} else col
        for col in by_type.columns
    ]

    dense = base.merge(incoming, on=["node_id", "decision_year"], how="left")
    dense = dense.merge(outgoing, on=["node_id", "decision_year"], how="left")
    dense = dense.merge(by_type, on=["node_id", "decision_year"], how="left")
    relation_cols = [col for col in dense.columns if col.startswith("relation_graph_")]
    dense[relation_cols] = dense[relation_cols].fillna(0.0)
    dense["relation_graph_embedding_available"] = (
        (dense["relation_graph_in_count"] > 0) | (dense["relation_graph_out_count"] > 0)
    ).astype(int)
    return dense.sort_values(["decision_year", "node_id"]).reset_index(drop=True)


def run_dynamic_relation_encoder(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    dense_graph_edges: pd.DataFrame | None = None,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    seed: int = 42,
    max_iter: int = 500,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions, _, _ = run_dynamic_relation_learner(
        nodes=nodes,
        edges=edges,
        scenarios=[DEFAULT_SCENARIO],
        eval_years=eval_years,
        negative_ratio=1,
        min_train_years=2,
        seed=seed,
        max_iter=max_iter,
        test_pair_mode="unseen_pair",
        node_feature_lag=1,
        positive_edge_states=["new_relation"],
        feature_family="sector_position_no_rank",
        pair_feature_mode="compatibility_only",
    )
    scored_edges = _relation_score_edges(predictions)
    embeddings = build_relation_node_embeddings(nodes, scored_edges)
    if dense_graph_edges is not None:
        dense_embeddings = build_dense_graph_signal_embeddings(nodes, dense_graph_edges)
        embeddings = embeddings.merge(dense_embeddings, on=["node_id", "decision_year"], how="left")
        dense_cols = [col for col in embeddings.columns if col.startswith("relation_graph_")]
        embeddings[dense_cols] = embeddings[dense_cols].fillna(0.0)
    metrics = _score_metrics(scored_edges)
    return scored_edges, embeddings, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="France ZE2020 dynamic relation encoder prototype. Exploratory only."
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--dense-edges", type=Path, default=EXPANDING_EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iter", type=int, default=500)
    args = parser.parse_args()

    joined_paths = "\n".join(str(path) for path in [args.nodes, args.edges, args.dense_edges])
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined_paths:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    dense_edges = load_edges(args.dense_edges) if args.dense_edges else None
    scored_edges, embeddings, metrics = run_dynamic_relation_encoder(
        nodes=nodes,
        edges=edges,
        dense_graph_edges=dense_edges,
        eval_years=args.eval_years,
        seed=args.seed,
        max_iter=args.max_iter,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_dynamic_relation_encoder"
    edges_path = args.output_dir / f"{stem}_edges_v1.csv"
    embeddings_path = args.output_dir / f"{stem}_node_embeddings_v1.csv"
    metrics_path = args.output_dir / f"{stem}_metrics_v1.csv"
    run_path = args.output_dir / f"{stem}_run_v1.json"
    scored_edges.to_csv(edges_path, index=False)
    embeddings.to_csv(embeddings_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "nodes": str(args.nodes),
                "edges": str(args.edges),
                "dense_edges": str(args.dense_edges) if args.dense_edges else None,
                "scored_edges": str(edges_path),
                "node_embeddings": str(embeddings_path),
                "metrics": str(metrics_path),
                "scenario": DEFAULT_SCENARIO,
                "eval_years": args.eval_years,
                "seed": args.seed,
                "node_feature_lag": 1,
                "positive_edge_states": "new_relation",
                "feature_family": "sector_position_no_rank",
                "pair_feature_mode": "compatibility_only",
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print("DYNAMIC RELATION ENCODER -- prototype only, not causal, not recommendation.")
    print(metrics.to_string(index=False))
    print(f"Scored edges: {edges_path}")
    print(f"Node embeddings: {embeddings_path}")


if __name__ == "__main__":
    main()
