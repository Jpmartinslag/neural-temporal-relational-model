"""
HERALD -- France ZE2020 dynamic relation learner smoke.

HERALD_27 local gate: test whether observed dynamic ZE2020 x sector edges can be
distinguished from controlled non-edges using node-pair features only.

No causal claim. No automatic recommendation. No policy prescription.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_dynamic_graph_falsifications import (  # noqa: E402
    SECTOR_COLUMNS,
    TEMPORAL_COLUMNS,
    _shuffle_columns,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_graph_ranker import (  # noqa: E402
    BASE_FEATURE_COLUMNS,
    load_nodes,
)

OUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_EDGES_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz"
DEFAULT_OUTPUT_DIR = OUT_DIR
DEFAULT_EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
TEST_PAIR_MODES = ["all", "unseen_pair"]
FEATURE_FAMILIES = [
    "all",
    "temporal_only",
    "sector_only",
    "sector_context_only",
    "sector_position_only",
    "sector_position_no_share",
    "sector_position_no_rank",
    "sector_position_no_dominant",
    "sector_share_only",
    "sector_rank_only",
    "dominant_sector_only",
    "ze_composition_only",
    "national_sector_only",
    "relation_memory_only",
    "non_temporal",
]
PAIR_FEATURE_MODES = [
    "both",
    "source_only",
    "target_only",
    "difference_only",
    "compatibility_only",
    "pair_structure_only",
]
SEED = 42
CLAIM_STATUS = "dynamic_relation_learner_smoke_exploratory_not_recommendation"

SCENARIOS = [
    "full_control",
    "easy_random_negatives",
    "typed_hard_negatives",
    "distance_hard_negatives",
    "scaled_distance_hard_negatives",
    "pair_distance_hard_negatives",
    "source_preserving_endpoint_matched_negatives",
    "target_preserving_hard_negatives",
    "target_preserving_endpoint_matched_negatives",
    "source_distance_target_preserving_negatives",
    "dual_profile_hard_negatives",
    "dual_profile_temporal_shuffle",
    "dual_profile_sector_shuffle",
    "dual_profile_temporal_sector_shuffle",
    "edge_sign_only",
    "random_edge_targets",
    "temporal_shuffle",
    "sector_shuffle",
    "temporal_sector_shuffle",
]

NEGATIVE_STRATEGY_BY_SCENARIO = {
    "full_control": "typed_hard",
    "easy_random_negatives": "easy_random",
    "typed_hard_negatives": "typed_hard",
    "distance_hard_negatives": "distance_hard",
    "scaled_distance_hard_negatives": "scaled_distance_hard",
    "pair_distance_hard_negatives": "pair_distance_hard",
    "source_preserving_endpoint_matched_negatives": "endpoint_target_matched_hard",
    "target_preserving_hard_negatives": "target_preserving_hard",
    "target_preserving_endpoint_matched_negatives": "endpoint_source_matched_target_preserving_hard",
    "source_distance_target_preserving_negatives": "source_distance_target_preserving_hard",
    "dual_profile_hard_negatives": "dual_profile_hard",
    "dual_profile_temporal_shuffle": "dual_profile_hard",
    "dual_profile_sector_shuffle": "dual_profile_hard",
    "dual_profile_temporal_sector_shuffle": "dual_profile_hard",
    "edge_sign_only": "typed_hard",
    "random_edge_targets": "typed_hard",
    "temporal_shuffle": "typed_hard",
    "sector_shuffle": "typed_hard",
    "temporal_sector_shuffle": "typed_hard",
}

FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)

ENDPOINT_MATCH_COLUMNS = ["sector_share_t", "dominant_sector_flag_t"]


def load_edges(path: Path = DEFAULT_EDGES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def _split_node_id(node_id: str) -> tuple[str, str]:
    ze2020, sector_code = str(node_id).split("_", 1)
    return ze2020.zfill(4), sector_code


def _node_frame(nodes: pd.DataFrame) -> pd.DataFrame:
    cols = ["node_id", "ze2020", "sector_code", "decision_year", "feature_complete", *BASE_FEATURE_COLUMNS]
    out = nodes[cols].copy()
    out[BASE_FEATURE_COLUMNS] = out[BASE_FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    out = out[(out["feature_complete"] == 1)].dropna(subset=BASE_FEATURE_COLUMNS).copy()
    out["ze2020"] = out["ze2020"].astype(str).str.zfill(4)
    return out


def _candidate_targets(
    nodes_year: pd.DataFrame,
    source_node_id: str,
    edge_type: str,
    strategy: str,
) -> list[str]:
    source_ze, source_sector = _split_node_id(source_node_id)
    if strategy == "easy_random":
        mask = nodes_year["node_id"] != source_node_id
    elif strategy in {
        "typed_hard",
        "distance_hard",
        "scaled_distance_hard",
        "pair_distance_hard",
        "endpoint_target_matched_hard",
    } and edge_type == "cross_ze_same_sector":
        mask = (nodes_year["sector_code"] == source_sector) & (nodes_year["node_id"] != source_node_id)
    elif strategy in {
        "typed_hard",
        "distance_hard",
        "scaled_distance_hard",
        "pair_distance_hard",
        "endpoint_target_matched_hard",
    } and edge_type == "intra_ze_sector":
        mask = (nodes_year["ze2020"] == source_ze) & (nodes_year["node_id"] != source_node_id)
    else:
        raise ValueError(f"Unknown negative strategy: {strategy}")
    return nodes_year.loc[mask, "node_id"].tolist()


def _candidate_sources_for_target(
    nodes_year: pd.DataFrame,
    target_node_id: str,
    edge_type: str,
) -> list[str]:
    target_ze, target_sector = _split_node_id(target_node_id)
    if edge_type == "cross_ze_same_sector":
        mask = (nodes_year["sector_code"] == target_sector) & (nodes_year["node_id"] != target_node_id)
    elif edge_type == "intra_ze_sector":
        mask = (nodes_year["ze2020"] == target_ze) & (nodes_year["node_id"] != target_node_id)
    else:
        raise ValueError(f"Unknown edge_type for target-preserving negatives: {edge_type}")
    return nodes_year.loc[mask, "node_id"].tolist()


def _choose_negative_targets(
    nodes_year: pd.DataFrame,
    source_node_id: str,
    positive_target: str,
    candidates: list[str],
    strategy: str,
    count: int,
    rng: np.random.Generator,
) -> list[str]:
    if not candidates:
        return []
    if strategy not in {
        "distance_hard",
        "scaled_distance_hard",
        "pair_distance_hard",
        "endpoint_target_matched_hard",
    }:
        return rng.choice(candidates, size=min(count, len(candidates)), replace=False).tolist()

    indexed = nodes_year.set_index("node_id")
    if positive_target not in indexed.index:
        return rng.choice(candidates, size=min(count, len(candidates)), replace=False).tolist()
    feature_columns = ENDPOINT_MATCH_COLUMNS if strategy == "endpoint_target_matched_hard" else BASE_FEATURE_COLUMNS
    candidate_frame = indexed.loc[candidates, feature_columns].astype(float).replace([np.inf, -np.inf], np.nan)
    positive_vector = indexed.loc[positive_target, feature_columns].astype(float).replace([np.inf, -np.inf], np.nan)
    if strategy == "pair_distance_hard":
        if source_node_id not in indexed.index:
            return rng.choice(candidates, size=min(count, len(candidates)), replace=False).tolist()
        source_vector = indexed.loc[source_node_id, BASE_FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], np.nan)
        positive_delta = (source_vector - positive_vector).abs()
        candidate_delta = (candidate_frame - source_vector).abs()
        distances = (candidate_delta - positive_delta).pow(2).sum(axis=1)
        distances = distances.sort_values(kind="mergesort")
        return distances.head(min(count, len(distances))).index.tolist()
    if strategy == "scaled_distance_hard":
        scale_frame = pd.concat([candidate_frame, positive_vector.to_frame().T], ignore_index=True)
        std = scale_frame.std(axis=0).replace(0, np.nan)
        mean = scale_frame.mean(axis=0)
        candidate_frame = (candidate_frame - mean) / std
        positive_vector = (positive_vector - mean) / std
    distances = (candidate_frame - positive_vector).pow(2).sum(axis=1)
    distances = distances.sort_values(kind="mergesort")
    return distances.head(min(count, len(distances))).index.tolist()


def _choose_negative_sources(
    nodes_year: pd.DataFrame,
    positive_source: str,
    candidates: list[str],
    strategy: str,
    count: int,
    rng: np.random.Generator,
) -> list[str]:
    if not candidates:
        return []
    if strategy not in {
        "source_distance_target_preserving_hard",
        "endpoint_source_matched_target_preserving_hard",
    }:
        return rng.choice(candidates, size=min(count, len(candidates)), replace=False).tolist()

    indexed = nodes_year.set_index("node_id")
    if positive_source not in indexed.index:
        return rng.choice(candidates, size=min(count, len(candidates)), replace=False).tolist()
    feature_columns = (
        ENDPOINT_MATCH_COLUMNS
        if strategy == "endpoint_source_matched_target_preserving_hard"
        else BASE_FEATURE_COLUMNS
    )
    candidate_frame = indexed.loc[candidates, feature_columns].astype(float).replace([np.inf, -np.inf], np.nan)
    positive_vector = indexed.loc[positive_source, feature_columns].astype(float).replace([np.inf, -np.inf], np.nan)
    distances = (candidate_frame - positive_vector).pow(2).sum(axis=1)
    distances = distances.sort_values(kind="mergesort")
    return distances.head(min(count, len(distances))).index.tolist()


def _feature_distance(indexed: pd.DataFrame, node_a: str, node_b: str) -> float:
    vector_a = indexed.loc[node_a, BASE_FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], np.nan)
    vector_b = indexed.loc[node_b, BASE_FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], np.nan)
    return float((vector_a - vector_b).pow(2).sum())


def _closest_nodes(
    indexed: pd.DataFrame,
    candidates: list[str],
    positive_node: str,
    limit: int,
) -> list[tuple[str, float]]:
    if not candidates or positive_node not in indexed.index:
        return []
    candidate_frame = indexed.loc[candidates, BASE_FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], np.nan)
    positive_vector = indexed.loc[positive_node, BASE_FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], np.nan)
    distances = (candidate_frame - positive_vector).pow(2).sum(axis=1).sort_values(kind="mergesort")
    return [(str(node_id), float(distance)) for node_id, distance in distances.head(limit).items()]


def _choose_dual_profile_negative_pairs(
    nodes_year: pd.DataFrame,
    positive_source: str,
    positive_target: str,
    edge_type: str,
    existing: set[tuple[object, object, int, object]],
    decision_year: int,
    count: int,
) -> list[tuple[str, str]]:
    indexed = nodes_year.set_index("node_id")
    if positive_source not in indexed.index or positive_target not in indexed.index:
        return []

    positive_source_ze, positive_source_sector = _split_node_id(positive_source)
    if edge_type == "cross_ze_same_sector":
        source_mask = nodes_year["sector_code"] == positive_source_sector
    elif edge_type == "intra_ze_sector":
        source_mask = nodes_year["ze2020"] == positive_source_ze
    else:
        raise ValueError(f"Unknown edge_type for dual-profile negatives: {edge_type}")
    source_candidates = [
        source
        for source in nodes_year.loc[source_mask, "node_id"].tolist()
        if source != positive_source
    ]
    if not source_candidates:
        return []
    source_rank = _closest_nodes(indexed, [str(source) for source in source_candidates], positive_source, limit=12)

    scored_pairs: list[tuple[float, str, str]] = []
    for source, source_distance in source_rank:
        target_candidates = [
            target
            for target in _candidate_targets(nodes_year, str(source), edge_type, "typed_hard")
            if target != positive_target
            and (source, target, decision_year, edge_type) not in existing
        ]
        if not target_candidates:
            continue
        target_rank = _closest_nodes(indexed, [str(target) for target in target_candidates], positive_target, limit=8)
        for target, target_distance in target_rank:
            score = source_distance + target_distance
            scored_pairs.append((score, str(source), str(target)))

    scored_pairs = sorted(scored_pairs, key=lambda item: (item[0], item[1], item[2]))
    return [(source, target) for _, source, target in scored_pairs[:count]]


def _precision_at_k(labels: np.ndarray, scores: np.ndarray, k: int) -> float:
    if len(labels) == 0:
        return float("nan")
    top = np.argsort(scores)[::-1][: min(k, len(scores))]
    return float(labels[top].mean())


def apply_relation_scenario(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenario: str,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown relation learner scenario: {scenario}")

    out_nodes = nodes.copy()
    out_edges = edges.copy()
    rng = np.random.default_rng(seed)

    if scenario == "edge_sign_only":
        out_edges["edge_weight"] = np.sign(out_edges["edge_weight"].to_numpy(dtype=float))
        out_edges.loc[out_edges["edge_weight"] == 0, "edge_weight"] = 1.0
    elif scenario == "random_edge_targets":
        source_parts = out_edges["source_node_id"].map(_split_node_id)
        out_edges["_source_ze"] = [part[0] for part in source_parts]
        out_edges["_source_sector"] = [part[1] for part in source_parts]
        cross_mask = out_edges["edge_type"] == "cross_ze_same_sector"
        intra_mask = out_edges["edge_type"] == "intra_ze_sector"
        random_groups = []
        random_groups.extend(
            out_edges.loc[cross_mask]
            .groupby(["decision_year", "edge_type", "_source_sector"], sort=False)
            .groups.values()
        )
        random_groups.extend(
            out_edges.loc[intra_mask]
            .groupby(["decision_year", "edge_type", "_source_ze"], sort=False)
            .groups.values()
        )
        for idx in random_groups:
            idx_list = list(idx)
            if len(idx_list) <= 1:
                continue
            out_edges.loc[idx_list, "target_node_id"] = rng.permutation(
                out_edges.loc[idx_list, "target_node_id"].to_numpy()
            )
        out_edges = out_edges.drop(columns=["_source_ze", "_source_sector"])
        out_edges = out_edges[out_edges["source_node_id"] != out_edges["target_node_id"]].copy()
    elif scenario in {"temporal_shuffle", "dual_profile_temporal_shuffle"}:
        out_nodes = _shuffle_columns(out_nodes, TEMPORAL_COLUMNS, seed=seed, group_cols=["decision_year"])
    elif scenario in {"sector_shuffle", "dual_profile_sector_shuffle"}:
        out_nodes = _shuffle_columns(out_nodes, SECTOR_COLUMNS, seed=seed, group_cols=["ze2020", "decision_year"])
    elif scenario in {"temporal_sector_shuffle", "dual_profile_temporal_sector_shuffle"}:
        out_nodes = _shuffle_columns(out_nodes, TEMPORAL_COLUMNS, seed=seed, group_cols=["decision_year"])
        out_nodes = _shuffle_columns(
            out_nodes, SECTOR_COLUMNS, seed=seed + 1, group_cols=["ze2020", "decision_year"]
        )

    return out_nodes, out_edges, NEGATIVE_STRATEGY_BY_SCENARIO[scenario]


def build_pairwise_relation_samples(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    negative_strategy: str = "easy_random",
    negative_ratio: int = 1,
    node_feature_lag: int = 0,
    positive_edge_states: list[str] | None = None,
    seed: int = SEED,
) -> pd.DataFrame:
    if negative_ratio < 1:
        raise ValueError("negative_ratio must be >= 1")
    if node_feature_lag < 0:
        raise ValueError("node_feature_lag must be >= 0")

    node = _node_frame(nodes)
    valid_node_year = set(zip(node["node_id"], node["decision_year"].astype(int)))
    edge_cols = ["source_node_id", "target_node_id", "decision_year", "edge_type"]
    if positive_edge_states:
        if "edge_state" not in edges.columns:
            raise ValueError("positive_edge_states requires an edge_state column")
        edges = edges[edges["edge_state"].isin(positive_edge_states)].copy()
        edge_cols.append("edge_state")
    positives = edges[edge_cols].copy()
    positives["node_feature_year"] = positives["decision_year"].astype(int) - int(node_feature_lag)
    positives = positives[
        positives.apply(
            lambda r: (r["source_node_id"], int(r["node_feature_year"])) in valid_node_year
            and (r["target_node_id"], int(r["node_feature_year"])) in valid_node_year,
            axis=1,
        )
    ].drop_duplicates()
    if positives.empty:
        raise ValueError("No positive relation samples remain after filtering")
    positives["relation_label"] = 1
    positives["sample_role"] = "observed_edge"

    existing = set(
        zip(
            positives["source_node_id"],
            positives["target_node_id"],
            positives["decision_year"].astype(int),
            positives["edge_type"],
        )
    )
    nodes_by_year = {int(year): group.copy() for year, group in node.groupby("decision_year")}
    rng = np.random.default_rng(seed)
    negative_rows: list[dict[str, object]] = []

    for row in positives.itertuples(index=False):
        year = int(row.decision_year)
        feature_year = int(row.node_feature_year)
        nodes_year = nodes_by_year.get(feature_year)
        if nodes_year is None:
            continue
        if negative_strategy == "dual_profile_hard":
            chosen_pairs = _choose_dual_profile_negative_pairs(
                nodes_year,
                positive_source=str(row.source_node_id),
                positive_target=str(row.target_node_id),
                edge_type=str(row.edge_type),
                existing=existing,
                decision_year=year,
                count=negative_ratio,
            )
            for source, target in chosen_pairs:
                negative_rows.append(
                    {
                        "source_node_id": source,
                        "target_node_id": target,
                        "decision_year": year,
                        "node_feature_year": feature_year,
                        "edge_type": row.edge_type,
                        "edge_state": "non_edge",
                        "relation_label": 0,
                        "sample_role": f"{negative_strategy}_non_edge",
                    }
                )
        elif negative_strategy in {
            "target_preserving_hard",
            "source_distance_target_preserving_hard",
            "endpoint_source_matched_target_preserving_hard",
        }:
            candidates = [
                source
                for source in _candidate_sources_for_target(
                    nodes_year,
                    str(row.target_node_id),
                    str(row.edge_type),
                )
                if source != row.source_node_id
                and (source, row.target_node_id, year, row.edge_type) not in existing
            ]
            chosen_sources = _choose_negative_sources(
                nodes_year,
                positive_source=str(row.source_node_id),
                candidates=candidates,
                strategy=negative_strategy,
                count=negative_ratio,
                rng=rng,
            )
            for source in chosen_sources:
                negative_rows.append(
                    {
                        "source_node_id": source,
                        "target_node_id": row.target_node_id,
                        "decision_year": year,
                        "node_feature_year": feature_year,
                        "edge_type": row.edge_type,
                        "edge_state": "non_edge",
                        "relation_label": 0,
                        "sample_role": f"{negative_strategy}_non_edge",
                    }
                )
        else:
            candidates = [
                target
                for target in _candidate_targets(
                    nodes_year,
                    str(row.source_node_id),
                    str(row.edge_type),
                    negative_strategy,
                )
                if (row.source_node_id, target, year, row.edge_type) not in existing
            ]
            if not candidates:
                continue
            chosen_targets = _choose_negative_targets(
                nodes_year,
                source_node_id=str(row.source_node_id),
                positive_target=str(row.target_node_id),
                candidates=candidates,
                strategy=negative_strategy,
                count=negative_ratio,
                rng=rng,
            )
            for target in chosen_targets:
                negative_rows.append(
                    {
                        "source_node_id": row.source_node_id,
                        "target_node_id": target,
                        "decision_year": year,
                        "node_feature_year": feature_year,
                        "edge_type": row.edge_type,
                        "edge_state": "non_edge",
                        "relation_label": 0,
                        "sample_role": f"{negative_strategy}_non_edge",
                    }
                )

    negatives = pd.DataFrame(negative_rows)
    if "edge_state" not in positives.columns:
        positives["edge_state"] = "observed_edge"
    samples = pd.concat([positives, negatives], ignore_index=True)
    if samples.empty:
        raise ValueError("No relation samples could be built")

    source = node.rename(columns={"node_id": "source_node_id", "decision_year": "node_feature_year"})
    source = source.rename(columns={c: f"source_{c}" for c in ["ze2020", "sector_code", *BASE_FEATURE_COLUMNS]})
    source = source.drop(columns=["feature_complete"])
    target = node.rename(columns={"node_id": "target_node_id", "decision_year": "node_feature_year"})
    target = target.rename(columns={c: f"target_{c}" for c in ["ze2020", "sector_code", *BASE_FEATURE_COLUMNS]})
    target = target.drop(columns=["feature_complete"])

    samples = samples.merge(source, on=["source_node_id", "node_feature_year"], how="inner")
    samples = samples.merge(target, on=["target_node_id", "node_feature_year"], how="inner")
    samples["same_ze"] = (samples["source_ze2020"] == samples["target_ze2020"]).astype(int)
    samples["same_sector"] = (samples["source_sector_code"] == samples["target_sector_code"]).astype(int)
    return samples.sort_values(["decision_year", "edge_type", "source_node_id", "target_node_id"]).reset_index(drop=True)


def node_features_for_family(feature_family: str) -> list[str]:
    if feature_family not in FEATURE_FAMILIES:
        raise ValueError(f"Unknown feature_family: {feature_family}")
    temporal = [col for col in BASE_FEATURE_COLUMNS if col in TEMPORAL_COLUMNS]
    sector = [col for col in BASE_FEATURE_COLUMNS if col in SECTOR_COLUMNS]
    relation_memory = [col for col in ["relation_stability_mean_to_t", "relation_count_to_t"] if col in BASE_FEATURE_COLUMNS]
    if feature_family == "temporal_only":
        return temporal
    if feature_family == "sector_only":
        return sector
    if feature_family == "sector_context_only":
        sector_context = ["sector_count_t", *sector]
        return [col for col in sector_context if col in BASE_FEATURE_COLUMNS]
    if feature_family == "sector_position_only":
        sector_position = ["sector_share_t", "sector_rank_in_ze_year_t", "dominant_sector_flag_t"]
        return [col for col in sector_position if col in BASE_FEATURE_COLUMNS]
    if feature_family == "sector_position_no_share":
        return [col for col in ["sector_rank_in_ze_year_t", "dominant_sector_flag_t"] if col in BASE_FEATURE_COLUMNS]
    if feature_family == "sector_position_no_rank":
        return [col for col in ["sector_share_t", "dominant_sector_flag_t"] if col in BASE_FEATURE_COLUMNS]
    if feature_family == "sector_position_no_dominant":
        return [col for col in ["sector_share_t", "sector_rank_in_ze_year_t"] if col in BASE_FEATURE_COLUMNS]
    if feature_family == "sector_share_only":
        return ["sector_share_t"] if "sector_share_t" in BASE_FEATURE_COLUMNS else []
    if feature_family == "sector_rank_only":
        return ["sector_rank_in_ze_year_t"] if "sector_rank_in_ze_year_t" in BASE_FEATURE_COLUMNS else []
    if feature_family == "dominant_sector_only":
        return ["dominant_sector_flag_t"] if "dominant_sector_flag_t" in BASE_FEATURE_COLUMNS else []
    if feature_family == "ze_composition_only":
        ze_composition = [
            "sector_count_t",
            "dominant_sector_share_lag_1",
            "sector_diversity_lag_1",
            "sector_concentration_hhi_lag_1",
            "commerce_share_lag_1",
            "construction_share_lag_1",
        ]
        return [col for col in ze_composition if col in BASE_FEATURE_COLUMNS]
    if feature_family == "national_sector_only":
        national_sector = ["national_sector_share_lag_1", "national_sector_growth_lag_1"]
        return [col for col in national_sector if col in BASE_FEATURE_COLUMNS]
    if feature_family == "relation_memory_only":
        return relation_memory
    if feature_family == "non_temporal":
        temporal_set = set(temporal)
        return [col for col in BASE_FEATURE_COLUMNS if col not in temporal_set]
    return list(BASE_FEATURE_COLUMNS)


def relation_feature_columns(
    samples: pd.DataFrame,
    node_feature_columns: list[str] | None = None,
    pair_feature_mode: str = "both",
) -> list[str]:
    if pair_feature_mode not in PAIR_FEATURE_MODES:
        raise ValueError(f"Unknown pair_feature_mode: {pair_feature_mode}")
    node_feature_columns = node_feature_columns or list(BASE_FEATURE_COLUMNS)
    cols = ["same_ze", "same_sector"]
    for feature in node_feature_columns:
        source_col = f"source_{feature}"
        target_col = f"target_{feature}"
        absdiff_col = f"absdiff_{feature}"
        product_col = f"product_{feature}"
        samples[absdiff_col] = (samples[source_col].astype(float) - samples[target_col].astype(float)).abs()
        samples[product_col] = samples[source_col].astype(float) * samples[target_col].astype(float)
        if pair_feature_mode == "both":
            cols.extend([source_col, target_col, absdiff_col, product_col])
        elif pair_feature_mode == "source_only":
            cols.append(source_col)
        elif pair_feature_mode == "target_only":
            cols.append(target_col)
        elif pair_feature_mode == "difference_only":
            cols.append(absdiff_col)
        elif pair_feature_mode == "compatibility_only":
            cols.extend([absdiff_col, product_col])
    for edge_type in sorted(samples["edge_type"].dropna().unique()):
        col = f"edge_type_{edge_type}"
        samples[col] = (samples["edge_type"] == edge_type).astype(int)
        cols.append(col)
    return cols


def _fit_relation_logit(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    max_iter: int,
) -> np.ndarray:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logit",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=max_iter,
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(train[feature_cols], train["relation_label"])
    return model.predict_proba(test[feature_cols])[:, 1]


def _history_count_score(
    train: pd.DataFrame,
    test: pd.DataFrame,
    group_cols: list[str],
) -> np.ndarray:
    positives = train[train["relation_label"] == 1]
    if positives.empty:
        return np.zeros(len(test), dtype=float)
    counts = positives.groupby(group_cols).size().rename("_history_score").reset_index()
    scored = test.merge(counts, on=group_cols, how="left")
    score = scored["_history_score"].fillna(0).to_numpy(dtype=float)
    max_score = float(score.max())
    if max_score > 0:
        score = score / max_score
    return score


def _filter_test_pairs(
    train: pd.DataFrame,
    test: pd.DataFrame,
    test_pair_mode: str,
) -> pd.DataFrame:
    if test_pair_mode == "all":
        return test
    if test_pair_mode != "unseen_pair":
        raise ValueError(f"Unknown test_pair_mode: {test_pair_mode}")

    train_positive_pairs = set(
        zip(
            train.loc[train["relation_label"] == 1, "source_node_id"],
            train.loc[train["relation_label"] == 1, "target_node_id"],
            train.loc[train["relation_label"] == 1, "edge_type"],
        )
    )
    keep = [
        (row.source_node_id, row.target_node_id, row.edge_type) not in train_positive_pairs
        for row in test.itertuples(index=False)
    ]
    return test.loc[keep].copy()


def run_dynamic_relation_learner(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenarios: list[str] = SCENARIOS,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    negative_ratio: int = 1,
    min_train_years: int = 2,
    seed: int = SEED,
    max_iter: int = 300,
    k: int = 50,
    test_pair_mode: str = "all",
    node_feature_lag: int = 0,
    positive_edge_states: list[str] | None = None,
    feature_family: str = "all",
    pair_feature_mode: str = "both",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if test_pair_mode not in TEST_PAIR_MODES:
        raise ValueError(f"Unknown test_pair_mode: {test_pair_mode}")
    if node_feature_lag < 0:
        raise ValueError("node_feature_lag must be >= 0")
    node_feature_columns = node_features_for_family(feature_family)

    prediction_frames = []
    metric_rows = []
    manifest_rows = []

    for scenario in scenarios:
        scenario_nodes, scenario_edges, negative_strategy = apply_relation_scenario(
            nodes, edges, scenario=scenario, seed=seed
        )
        samples = build_pairwise_relation_samples(
            scenario_nodes,
            scenario_edges,
            negative_strategy=negative_strategy,
            negative_ratio=negative_ratio,
            node_feature_lag=node_feature_lag,
            positive_edge_states=positive_edge_states,
            seed=seed,
        )
        feature_cols = relation_feature_columns(
            samples,
            node_feature_columns=node_feature_columns,
            pair_feature_mode=pair_feature_mode,
        )

        for eval_year in eval_years:
            train = samples[samples["decision_year"] < eval_year].copy()
            test = samples[samples["decision_year"] == eval_year].copy()
            test = _filter_test_pairs(train, test, test_pair_mode=test_pair_mode)
            if test.empty or train["decision_year"].nunique() < min_train_years:
                continue
            if train["relation_label"].nunique() < 2 or test["relation_label"].nunique() < 2:
                continue

            scores = {
                "relation_logit": _fit_relation_logit(
                    train, test, feature_cols=feature_cols, seed=seed, max_iter=max_iter
                ),
                "target_popularity": _history_count_score(
                    train, test, group_cols=["target_node_id", "edge_type"]
                ),
                "source_popularity": _history_count_score(
                    train, test, group_cols=["source_node_id", "edge_type"]
                ),
                "pair_history": _history_count_score(
                    train,
                    test,
                    group_cols=["source_node_id", "target_node_id", "edge_type"],
                ),
                "random": np.random.default_rng(seed + eval_year).random(len(test)),
            }
            labels = test["relation_label"].to_numpy(dtype=int)

            for model_name, score in scores.items():
                pred = test[
                    [
                        "source_node_id",
                        "target_node_id",
                        "decision_year",
                        "node_feature_year",
                        "edge_type",
                        "edge_state",
                        "relation_label",
                        "sample_role",
                    ]
                ].copy()
                pred["model"] = model_name
                pred["score"] = score
                pred["falsification_scenario"] = scenario
                pred["negative_strategy"] = negative_strategy
                pred["feature_family"] = feature_family
                pred["pair_feature_mode"] = pair_feature_mode
                pred["claim_status"] = CLAIM_STATUS
                prediction_frames.append(pred)
                metric_rows.append(
                    {
                        "eval_year": int(eval_year),
                        "model": model_name,
                        "falsification_scenario": scenario,
                        "negative_strategy": negative_strategy,
                        "roc_auc": float(roc_auc_score(labels, score)),
                        "average_precision": float(average_precision_score(labels, score)),
                        "precision_at_k": _precision_at_k(labels, score, k=k),
                        "k": int(k),
                        "n_train_rows": int(len(train)),
                        "n_test_rows": int(len(test)),
                        "n_train_years": int(train["decision_year"].nunique()),
                        "n_features": int(len(feature_cols)),
                        "feature_family": feature_family,
                        "pair_feature_mode": pair_feature_mode,
                        "test_pair_mode": test_pair_mode,
                        "node_feature_lag": int(node_feature_lag),
                        "positive_edge_states": (
                            "all" if not positive_edge_states else " ".join(sorted(positive_edge_states))
                        ),
                        "claim_status": CLAIM_STATUS,
                    }
                )
        manifest_rows.append(
            {
                "falsification_scenario": scenario,
                "negative_strategy": negative_strategy,
                "negative_ratio": int(negative_ratio),
                "seed": int(seed),
                "eval_years": " ".join(str(y) for y in eval_years),
                "feature_family": feature_family,
                "pair_feature_mode": pair_feature_mode,
                "test_pair_mode": test_pair_mode,
                "node_feature_lag": int(node_feature_lag),
                "positive_edge_states": "all"
                if not positive_edge_states
                else " ".join(sorted(positive_edge_states)),
                "claim_status": CLAIM_STATUS,
            }
        )

    if not prediction_frames:
        raise ValueError("No dynamic relation learner evaluation rows were produced")
    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(metric_rows), pd.DataFrame(manifest_rows)


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby(
            [
                "falsification_scenario",
                "negative_strategy",
                "test_pair_mode",
                "node_feature_lag",
                "positive_edge_states",
                "feature_family",
                "pair_feature_mode",
                "model",
            ],
            as_index=False,
        )
        .agg(
            mean_roc_auc=("roc_auc", "mean"),
            mean_average_precision=("average_precision", "mean"),
            mean_precision_at_k=("precision_at_k", "mean"),
            n_eval_years=("eval_year", "nunique"),
        )
        .sort_values(["falsification_scenario", "mean_average_precision"], ascending=[True, False])
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="France ZE2020 dynamic relation learner smoke. Exploratory only."
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--scenarios", nargs="+", default=SCENARIOS, choices=SCENARIOS)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--negative-ratio", type=int, default=1)
    parser.add_argument("--min-train-years", type=int, default=2)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--max-iter", type=int, default=300)
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--test-pair-mode", default="all", choices=TEST_PAIR_MODES)
    parser.add_argument("--node-feature-lag", type=int, default=0)
    parser.add_argument("--positive-edge-states", nargs="*", default=None)
    parser.add_argument("--feature-family", default="all", choices=FEATURE_FAMILIES)
    parser.add_argument("--pair-feature-mode", default="both", choices=PAIR_FEATURE_MODES)
    args = parser.parse_args()

    joined_paths = "\n".join(str(p) for p in [args.nodes, args.edges])
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined_paths:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    predictions, metrics, manifest = run_dynamic_relation_learner(
        nodes,
        edges,
        scenarios=args.scenarios,
        eval_years=args.eval_years,
        negative_ratio=args.negative_ratio,
        min_train_years=args.min_train_years,
        seed=args.seed,
        max_iter=args.max_iter,
        k=args.k,
        test_pair_mode=args.test_pair_mode,
        node_feature_lag=args.node_feature_lag,
        positive_edge_states=args.positive_edge_states,
        feature_family=args.feature_family,
        pair_feature_mode=args.pair_feature_mode,
    )
    summary = summarize_metrics(metrics)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_dynamic_relation_learner"
    predictions_path = args.output_dir / f"{stem}_predictions_v1.csv"
    metrics_path = args.output_dir / f"{stem}_metrics_v1.csv"
    summary_path = args.output_dir / f"{stem}_summary_v1.csv"
    manifest_path = args.output_dir / f"{stem}_manifest_v1.csv"
    run_path = args.output_dir / f"{stem}_run_v1.json"

    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    manifest.to_csv(manifest_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "nodes": str(args.nodes),
                "edges": str(args.edges),
                "predictions": str(predictions_path),
                "metrics": str(metrics_path),
                "summary": str(summary_path),
                "manifest": str(manifest_path),
                "scenarios": args.scenarios,
                "eval_years": args.eval_years,
                "feature_family": args.feature_family,
                "pair_feature_mode": args.pair_feature_mode,
                "test_pair_mode": args.test_pair_mode,
                "node_feature_lag": args.node_feature_lag,
                "positive_edge_states": "all"
                if not args.positive_edge_states
                else " ".join(sorted(args.positive_edge_states)),
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(summary.to_string(index=False))
    print(f"Wrote {predictions_path}")
    print(f"Wrote {metrics_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
