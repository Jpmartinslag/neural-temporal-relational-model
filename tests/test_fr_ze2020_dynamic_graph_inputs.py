from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EDGES_OUT_PATH,
    EXPANDING_EDGES_OUT_PATH,
    LABEL_COLUMNS,
    NODES_OUT_PATH,
    NODE_FEATURE_COLUMNS,
    RANKING_PANEL_PATH,
    SPLITS_OUT_PATH,
    build_dynamic_graph_edges,
    build_dynamic_graph_inputs,
    build_dynamic_graph_nodes,
    build_dynamic_graph_splits,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_dynamic_graph_inputs.py"

FORBIDDEN_INPUTS = [
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
]

FORBIDDEN_CLAIMS = [
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
]


def test_dynamic_graph_outputs_exist_and_schema():
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    expanding_edges = pd.read_csv(EXPANDING_EDGES_OUT_PATH)
    splits = pd.read_csv(SPLITS_OUT_PATH)

    assert len(nodes) == 280 * 9 * 14
    assert nodes["node_id"].str.match(r"^\d{4}_[A-Z]{2}$").all()
    assert nodes["ze2020"].str.len().eq(4).all()
    assert nodes["sector_code"].nunique() == 9
    assert nodes["decision_year"].min() == 2012
    assert nodes["decision_year"].max() == 2025
    assert set(LABEL_COLUMNS).issubset(nodes.columns)
    assert set(NODE_FEATURE_COLUMNS).issubset(nodes.columns)

    expected_edge_cols = {
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "claim_status",
    }
    expected_expanding_edge_cols = {
        *expected_edge_cols,
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
    }
    assert expected_edge_cols.issubset(edges.columns)
    assert expected_expanding_edge_cols.issubset(expanding_edges.columns)
    assert set(edges["edge_type"]) == {
        "cross_ze_same_sector",
        "intra_ze_sector",
        "ze_similarity",
    }
    assert set(expanding_edges["edge_type"]) == set(edges["edge_type"])
    assert len(splits) == 14


def test_dynamic_graph_build_is_deterministic():
    disk_nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str}).sort_index(axis=1)
    disk_edges = pd.read_csv(EDGES_OUT_PATH).sort_index(axis=1)
    disk_expanding_edges = pd.read_csv(EXPANDING_EDGES_OUT_PATH).sort_index(axis=1)
    disk_splits = pd.read_csv(SPLITS_OUT_PATH).sort_index(axis=1)

    nodes, edges, expanding_edges, splits = build_dynamic_graph_inputs()
    pd.testing.assert_frame_equal(disk_nodes, nodes.sort_index(axis=1), check_dtype=False)
    pd.testing.assert_frame_equal(disk_edges, edges.sort_index(axis=1), check_dtype=False)
    pd.testing.assert_frame_equal(
        disk_expanding_edges, expanding_edges.sort_index(axis=1), check_dtype=False
    )
    pd.testing.assert_frame_equal(disk_splits, splits.sort_index(axis=1), check_dtype=False)


def test_edges_only_reference_existing_nodes_in_same_year():
    nodes = pd.read_csv(NODES_OUT_PATH)
    edges = pd.read_csv(EDGES_OUT_PATH)
    node_keys = set(zip(nodes["node_id"], nodes["decision_year"]))
    source_keys = set(zip(edges["source_node_id"], edges["decision_year"]))
    target_keys = set(zip(edges["target_node_id"], edges["decision_year"]))
    assert source_keys.issubset(node_keys)
    assert target_keys.issubset(node_keys)
    assert not (edges["source_node_id"] == edges["target_node_id"]).any()


def test_edges_are_finite_and_exploratory_not_causal():
    for path in [EDGES_OUT_PATH, EXPANDING_EDGES_OUT_PATH]:
        edges = pd.read_csv(path)
        for col in ["edge_weight", "signal_strength", "stability_score"]:
            assert np.isfinite(edges[col].to_numpy(dtype=float)).all()
        assert edges["signal_strength"].between(-1, 1).all()
        assert edges["stability_score"].between(0, 1).all()
        assert set(edges["claim_status"]) == {"dynamic_graph_edge_exploratory_not_causal"}


def test_expanding_edges_are_leakage_safe_memory_snapshots():
    instant_edges = pd.read_csv(EDGES_OUT_PATH)
    expanding_edges = pd.read_csv(EXPANDING_EDGES_OUT_PATH)
    assert len(expanding_edges) > len(instant_edges)
    assert set(expanding_edges["edge_memory_mode"]) == {"expanding_stability_decay"}
    assert (expanding_edges["edge_age"] >= 0).all()
    assert (expanding_edges["source_relation_year_end"] <= expanding_edges["decision_year"]).all()
    assert (
        expanding_edges["edge_age"]
        == expanding_edges["decision_year"] - expanding_edges["source_relation_year_end"]
    ).all()
    assert "instant" not in set(expanding_edges["edge_memory_mode"])


def test_specialization_signal_is_not_fabricated_as_edge():
    for path in [EDGES_OUT_PATH, EXPANDING_EDGES_OUT_PATH]:
        edges = pd.read_csv(path)
        assert "ze_sector_specialization" not in set(edges["edge_type"])
        assert not edges["source_relation_id"].str.contains("ze_sector_specialization", na=False).any()


def test_label_columns_are_separate_from_feature_columns():
    nodes = pd.read_csv(NODES_OUT_PATH)
    assert set(LABEL_COLUMNS).isdisjoint(NODE_FEATURE_COLUMNS)
    assert {"future_growth_1y", "future_growth_3y"}.issubset(nodes.columns)
    assert "future_growth_1y" not in NODE_FEATURE_COLUMNS
    assert "future_growth_3y" not in NODE_FEATURE_COLUMNS


def test_script_does_not_read_forbidden_legacy_inputs_in_executable_paths():
    source_lines = SCRIPT_PATH.read_text().splitlines()
    read_lines = [line for line in source_lines if "read_csv" in line or "Path(" in line or " / " in line]
    code_only = "\n".join(read_lines)
    for term in FORBIDDEN_INPUTS:
        assert term not in code_only


def test_no_forbidden_claim_columns():
    for path in [NODES_OUT_PATH, EDGES_OUT_PATH, EXPANDING_EDGES_OUT_PATH, SPLITS_OUT_PATH]:
        df = pd.read_csv(path)
        lowered = {c.lower() for c in df.columns}
        for term in FORBIDDEN_CLAIMS[1:]:
            assert term not in lowered


def test_builders_accept_explicit_inputs():
    ranking_panel = pd.read_csv(RANKING_PANEL_PATH, dtype={"ze2020": str})
    nodes = build_dynamic_graph_nodes(ranking_panel)
    edges = build_dynamic_graph_edges(nodes=nodes)
    splits = build_dynamic_graph_splits(nodes=nodes)
    assert not nodes.empty
    assert not edges.empty
    assert not splits.empty
