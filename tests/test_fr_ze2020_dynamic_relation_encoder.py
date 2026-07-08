from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import NODES_OUT_PATH
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_encoder import (
    CLAIM_STATUS,
    build_dense_graph_signal_embeddings,
    build_relation_node_embeddings,
    run_dynamic_relation_encoder,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (
    DEFAULT_EDGES_PATH,
    load_edges,
    load_nodes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_encoder.py"


@pytest.fixture(scope="module")
def encoder_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nodes = load_nodes(NODES_OUT_PATH)
    edges = load_edges(DEFAULT_EDGES_PATH)
    return run_dynamic_relation_encoder(nodes, edges, eval_years=[2022, 2023], seed=42)


def test_dynamic_relation_encoder_outputs_scored_edges_and_embeddings(encoder_outputs):
    scored_edges, embeddings, metrics = encoder_outputs
    assert not scored_edges.empty
    assert not embeddings.empty
    assert not metrics.empty
    assert scored_edges["relation_score"].between(0, 1).all()
    assert set(scored_edges["claim_status"]) == {CLAIM_STATUS}
    assert set(embeddings["claim_status"]) == {CLAIM_STATUS}


def test_dynamic_relation_encoder_embeddings_are_node_level_not_label_level(encoder_outputs):
    _, embeddings, _ = encoder_outputs
    forbidden_cols = {"relation_label", "sample_role", "edge_state"}
    assert forbidden_cols.isdisjoint(set(embeddings.columns))
    relation_cols = [col for col in embeddings.columns if col.startswith("relation_")]
    assert relation_cols
    numeric = embeddings[relation_cols].drop(columns=["claim_status"], errors="ignore")
    assert np.isfinite(numeric.to_numpy(dtype=float)).all()


def test_dynamic_relation_encoder_metrics_are_above_random_control(encoder_outputs):
    _, _, metrics = encoder_outputs
    mean_row = metrics[metrics["eval_year"].astype(str) == "mean"].iloc[0]
    assert mean_row["average_precision"] > 0.5
    assert mean_row["roc_auc"] > 0.5


def test_build_relation_node_embeddings_fills_missing_nodes_with_zero():
    nodes = pd.DataFrame(
        {
            "node_id": ["0001_A", "0002_A"],
            "ze2020": ["0001", "0002"],
            "sector_code": ["A", "A"],
            "decision_year": [2025, 2025],
        }
    )
    scored = pd.DataFrame(
        {
            "source_node_id": ["0001_A"],
            "target_node_id": ["0002_A"],
            "decision_year": [2025],
            "edge_type": ["cross_ze_same_sector"],
            "relation_score": [0.75],
        }
    )
    embeddings = build_relation_node_embeddings(nodes, scored)
    source = embeddings[embeddings["node_id"] == "0001_A"].iloc[0]
    target = embeddings[embeddings["node_id"] == "0002_A"].iloc[0]
    assert source["relation_out_count"] == 1
    assert source["relation_in_count"] == 0
    assert target["relation_in_count"] == 1
    assert target["relation_in_score_mean"] == pytest.approx(0.75)


def test_build_dense_graph_signal_embeddings_covers_graph_connected_nodes():
    nodes = pd.DataFrame(
        {
            "node_id": ["0001_A", "0002_A", "0003_A"],
            "ze2020": ["0001", "0002", "0003"],
            "sector_code": ["A", "A", "A"],
            "decision_year": [2025, 2025, 2025],
        }
    )
    graph_edges = pd.DataFrame(
        {
            "source_node_id": ["0001_A", "0002_A"],
            "target_node_id": ["0002_A", "0001_A"],
            "decision_year": [2025, 2025],
            "edge_type": ["cross_ze_same_sector", "cross_ze_same_sector"],
            "edge_weight": [0.4, 0.8],
            "signal_strength": [0.5, 0.9],
            "stability_score": [0.2, 0.7],
        }
    )
    embeddings = build_dense_graph_signal_embeddings(nodes, graph_edges)
    connected = embeddings[embeddings["node_id"].isin(["0001_A", "0002_A"])]
    isolated = embeddings[embeddings["node_id"] == "0003_A"].iloc[0]
    assert connected["relation_graph_embedding_available"].eq(1).all()
    assert isolated["relation_graph_embedding_available"] == 0
    assert embeddings["relation_graph_in_count"].sum() == 2
    assert embeddings["relation_graph_out_count"].sum() == 2


def test_dynamic_relation_encoder_has_no_forbidden_claims_or_inputs():
    code = SCRIPT_PATH.read_text()
    forbidden_claims = [
        "recommended_action",
        "policy_action",
        "causal_effect",
        "causal_impact",
        "validated_gnn",
    ]
    for term in forbidden_claims:
        assert term not in code

    executable_path_lines = "\n".join(
        line for line in code.splitlines() if "read_csv" in line or "Path(" in line or "DEFAULT_" in line
    )
    forbidden_inputs = [
        "dynamic_stgnn_feature_panel",
        "graph_adjacency_core_v0",
        "graph_adjacency_mobility_v0",
    ]
    for term in forbidden_inputs:
        assert term not in executable_path_lines
