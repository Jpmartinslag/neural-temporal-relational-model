#!/usr/bin/env python3
"""Gate strict ex-ante commuting relations against matched linear placebos."""

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
    EXPANDING_EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_edge_family_isolation_probe import (  # noqa: E402
    build_balanced_family_frame,
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
    load_edges,
    load_nodes,
)

CLAIM_STATUS = "commuting_relation_gate_exploratory_not_recommendation"
AGGREGATED_NODE_FEATURES = [
    "sector_count_t",
    "sector_share_t",
    "sector_rank_in_ze_year_t",
    "sector_growth_lag_1",
    "dominant_sector_flag_t",
]
TOPOLOGY_FEATURES = [
    "commuting_out_degree",
    "commuting_out_weight_max",
    "commuting_out_weight_entropy",
    "commuting_in_degree",
    "commuting_in_weight_sum",
]
AVAILABILITY_FEATURE = "commuting_relation_available"
VIEW_NAMES = [
    "node_only",
    "commuting_availability_only",
    "commuting_real",
    "commuting_endpoint_randomized",
    "commuting_uniform_weights",
    "commuting_reversed_direction",
    "trajectory_similarity_reference",
    "commuting_target_shuffled",
]
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def load_commuting_edges(path: Path = STRICT_EDGES_OUT_PATH) -> pd.DataFrame:
    edges = pd.read_csv(
        path,
        dtype={"source_ze2020": str, "target_ze2020": str},
    )
    edges["source_ze2020"] = edges["source_ze2020"].str.zfill(4)
    edges["target_ze2020"] = edges["target_ze2020"].str.zfill(4)
    return edges


def _normalize_edges(edges: pd.DataFrame) -> pd.DataFrame:
    out = (
        edges[["decision_year", "source_ze2020", "target_ze2020", "edge_weight"]]
        .copy()
    )
    out = out[out["source_ze2020"] != out["target_ze2020"]]
    totals = out.groupby(["decision_year", "source_ze2020"])["edge_weight"].transform(
        "sum"
    )
    if (totals <= 0).any():
        raise ValueError("Commuting variant contains an isolated source")
    out["edge_weight"] = out["edge_weight"] / totals
    return out.sort_values(
        ["decision_year", "source_ze2020", "target_ze2020"]
    ).reset_index(drop=True)


def _randomize_targets_without_self_loops(
    sources: np.ndarray,
    targets: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    randomized = rng.permutation(targets)
    max_repairs = len(randomized) * 2
    repairs = 0
    while True:
        bad = np.flatnonzero(randomized == sources)
        if not len(bad):
            return randomized
        position = int(bad[0])
        candidates = np.flatnonzero(
            (randomized != sources[position])
            & (randomized[position] != sources)
            & (np.arange(len(randomized)) != position)
        )
        if not len(candidates):
            raise ValueError("Could not randomize endpoints without self-loops")
        swap = int(rng.choice(candidates))
        randomized[position], randomized[swap] = randomized[swap], randomized[position]
        repairs += 1
        if repairs > max_repairs:
            raise ValueError("Endpoint randomization repair did not converge")


def make_edge_variant(edges: pd.DataFrame, variant: str, seed: int = 42) -> pd.DataFrame:
    out = edges[["decision_year", "source_ze2020", "target_ze2020", "edge_weight"]].copy()
    rng = np.random.default_rng(seed)
    if variant == "real":
        pass
    elif variant == "endpoint_randomized":
        for _, index in out.groupby("decision_year", sort=False).groups.items():
            idx = list(index)
            out.loc[idx, "target_ze2020"] = _randomize_targets_without_self_loops(
                out.loc[idx, "source_ze2020"].to_numpy(),
                out.loc[idx, "target_ze2020"].to_numpy(),
                rng,
            )
    elif variant == "uniform_weights":
        out["edge_weight"] = 1.0
    elif variant == "reversed_direction":
        source = out["source_ze2020"].copy()
        out["source_ze2020"] = out["target_ze2020"]
        out["target_ze2020"] = source
    else:
        raise ValueError(f"Unknown commuting variant: {variant}")
    return _normalize_edges(out)


def relation_feature_columns() -> list[str]:
    columns = [AVAILABILITY_FEATURE, *TOPOLOGY_FEATURES]
    for feature in AGGREGATED_NODE_FEATURES:
        columns.extend(
            [
                f"commuting_out_neighbor__{feature}",
                f"commuting_in_neighbor__{feature}",
            ]
        )
    return columns


def build_commuting_feature_frame(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    frame = nodes.copy()
    frame["ze2020"] = frame["ze2020"].astype(str).str.zfill(4)
    relation_columns = relation_feature_columns()
    frame[relation_columns] = 0.0

    for year, year_edges in edges.groupby("decision_year", sort=True):
        year_nodes = frame[frame["decision_year"] == int(year)]
        zones = sorted(year_nodes["ze2020"].unique())
        if len(zones) != 280:
            raise ValueError(f"Expected 280 zones in node year {year}, found {len(zones)}")
        zone_index = {zone: position for position, zone in enumerate(zones)}
        weight = np.zeros((len(zones), len(zones)), dtype=float)
        for row in year_edges.itertuples(index=False):
            source = zone_index.get(str(row.source_ze2020).zfill(4))
            target = zone_index.get(str(row.target_ze2020).zfill(4))
            if source is not None and target is not None:
                weight[source, target] += float(row.edge_weight)
        row_sum = weight.sum(axis=1)
        if not np.allclose(row_sum, 1.0, atol=1e-9):
            raise ValueError(f"Outgoing commuting matrix is not normalized in {year}")
        column_sum = weight.sum(axis=0)
        incoming_weight = np.divide(
            weight,
            column_sum[np.newaxis, :],
            out=np.zeros_like(weight),
            where=column_sum[np.newaxis, :] > 0,
        )
        nonzero = weight > 0
        out_degree = nonzero.sum(axis=1).astype(float)
        in_degree = nonzero.sum(axis=0).astype(float)
        out_max = weight.max(axis=1)
        entropy = -(np.where(nonzero, weight * np.log(np.maximum(weight, 1e-15)), 0.0)).sum(
            axis=1
        )

        for sector, sector_nodes in year_nodes.groupby("sector_code", sort=True):
            ordered = (
                sector_nodes.assign(_frame_index=sector_nodes.index)
                .set_index("ze2020")
                .loc[zones]
            )
            values = ordered[AGGREGATED_NODE_FEATURES].to_numpy(float)
            if not np.isfinite(values).all():
                raise ValueError(f"Non-finite node input for {sector} in {year}")
            frame_indices = ordered["_frame_index"].to_numpy()
            frame.loc[frame_indices, AVAILABILITY_FEATURE] = 1.0
            frame.loc[frame_indices, TOPOLOGY_FEATURES] = np.column_stack(
                [out_degree, out_max, entropy, in_degree, column_sum]
            )
            outgoing = weight @ values
            incoming = incoming_weight.T @ values
            for position, feature in enumerate(AGGREGATED_NODE_FEATURES):
                frame.loc[
                    frame_indices, f"commuting_out_neighbor__{feature}"
                ] = outgoing[:, position]
                frame.loc[
                    frame_indices, f"commuting_in_neighbor__{feature}"
                ] = incoming[:, position]

    numeric = frame[relation_columns].to_numpy(float)
    if not np.isfinite(numeric).all():
        raise ValueError("Non-finite commuting relation feature")
    return frame, relation_columns


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


def evaluate_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]

    def compare(control: str) -> dict[str, float]:
        real = metrics[metrics["view"] == "commuting_real"][
            keys + ["ndcg_at_3"]
        ].rename(columns={"ndcg_at_3": "real"})
        other = metrics[metrics["view"] == control][keys + ["ndcg_at_3"]].rename(
            columns={"ndcg_at_3": "control"}
        )
        paired = real.merge(other, on=keys, validate="one_to_one")
        delta = paired["real"] - paired["control"]
        return {
            "mean_ndcg_lift": float(delta.mean()),
            "paired_win_rate": float((delta > 0).mean()),
            "n_pairs": int(len(paired)),
        }

    comparisons = {
        name: compare(name)
        for name in [
            "node_only",
            "commuting_availability_only",
            "commuting_endpoint_randomized",
            "commuting_uniform_weights",
            "commuting_reversed_direction",
            "trajectory_similarity_reference",
            "commuting_target_shuffled",
        ]
    }
    gate_pass = (
        comparisons["commuting_availability_only"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_endpoint_randomized"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_endpoint_randomized"]["paired_win_rate"] >= 0.60
        and comparisons["commuting_uniform_weights"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_reversed_direction"]["mean_ndcg_lift"] > 0
        and comparisons["trajectory_similarity_reference"]["mean_ndcg_lift"] > 0
        and comparisons["commuting_target_shuffled"]["mean_ndcg_lift"] > 0
    )
    return {
        "gate_pass": bool(gate_pass),
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def validate_paired_populations(metrics: pd.DataFrame) -> None:
    keys = ["seed", "eval_year", "ze_fold"]
    population = [*keys, "n_train", "n_test", "n_test_positive"]
    reference = (
        metrics[metrics["view"] == "commuting_real"][population]
        .sort_values(keys)
        .reset_index(drop=True)
    )
    if reference.duplicated(keys).any():
        raise ValueError("Duplicate commuting_real evaluation key")
    for view in VIEW_NAMES:
        candidate = (
            metrics[metrics["view"] == view][population]
            .sort_values(keys)
            .reset_index(drop=True)
        )
        if not reference.equals(candidate):
            raise ValueError(f"Evaluation population differs for view: {view}")


def run_commuting_relation_gate(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    similarity_edges: pd.DataFrame,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    nodes = nodes.copy()
    nodes["ze2020"] = nodes["ze2020"].astype(str).str.zfill(4)
    nodes["ze_fold"] = assign_ze_folds(nodes)

    real_frame, relation_columns = build_commuting_feature_frame(
        nodes, make_edge_variant(edges, "real")
    )
    uniform_frame, uniform_columns = build_commuting_feature_frame(
        nodes, make_edge_variant(edges, "uniform_weights")
    )
    reversed_frame, reversed_columns = build_commuting_feature_frame(
        nodes, make_edge_variant(edges, "reversed_direction")
    )
    similarity_frame, similarity_features = build_balanced_family_frame(
        nodes, similarity_edges, ["ze_similarity"], seed=42
    )
    if relation_columns != uniform_columns or relation_columns != reversed_columns:
        raise AssertionError("Commuting variant feature mismatch")
    full_features = [*BASE_FEATURE_COLUMNS, *relation_columns]
    availability_features = [*BASE_FEATURE_COLUMNS, AVAILABILITY_FEATURE]
    rows: list[dict[str, object]] = []

    for seed in seeds:
        endpoint_frame, endpoint_columns = build_commuting_feature_frame(
            nodes, make_edge_variant(edges, "endpoint_randomized", seed=seed + 5000)
        )
        if endpoint_columns != relation_columns:
            raise AssertionError("Endpoint feature mismatch")
        configurations = [
            ("node_only", real_frame, list(BASE_FEATURE_COLUMNS), False),
            (
                "commuting_availability_only",
                real_frame,
                availability_features,
                False,
            ),
            ("commuting_real", real_frame, full_features, False),
            (
                "commuting_endpoint_randomized",
                endpoint_frame,
                full_features,
                False,
            ),
            (
                "commuting_uniform_weights",
                uniform_frame,
                full_features,
                False,
            ),
            (
                "commuting_reversed_direction",
                reversed_frame,
                full_features,
                False,
            ),
            (
                "trajectory_similarity_reference",
                similarity_frame,
                similarity_features,
                False,
            ),
            (
                "commuting_target_shuffled",
                real_frame,
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
        raise ValueError("Missing or non-finite commuting gate metric")
    validate_paired_populations(metrics)
    return metrics, _summary(metrics), evaluate_gate(metrics)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--commuting-edges", type=Path, default=STRICT_EDGES_OUT_PATH)
    parser.add_argument(
        "--similarity-edges", type=Path, default=EXPANDING_EDGES_OUT_PATH
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()

    joined = f"{args.nodes}\n{args.commuting_edges}\n{args.similarity_edges}"
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")
    metrics, summary, gate = run_commuting_relation_gate(
        load_nodes(args.nodes),
        load_commuting_edges(args.commuting_edges),
        load_edges(args.similarity_edges),
        eval_years=args.eval_years,
        seeds=args.seeds,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_commuting_relation_gate"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
