from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EDGES_OUT_PATH,
    LABEL_COLUMNS,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_graph_ranker import (
    BASE_FEATURE_COLUMNS,
    CLAIM_STATUS,
    EDGE_TYPES,
    build_dynamic_graph_feature_frame,
    build_typed_messages,
    run_dynamic_graph_ranker,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py"

FORBIDDEN_INPUTS = [
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
]

FORBIDDEN_COLUMNS = [
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
]


def test_typed_message_frame_has_expected_columns_and_no_labels_as_features():
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    frame, model_features = build_dynamic_graph_feature_frame(nodes, edges)

    assert len(frame) == len(nodes)
    assert set(BASE_FEATURE_COLUMNS).issubset(model_features)
    for edge_type in EDGE_TYPES:
        assert f"msg_{edge_type}_edge_count" in model_features
        assert any(c.startswith(f"msg_{edge_type}_") for c in model_features)
    assert set(LABEL_COLUMNS).isdisjoint(model_features)
    message_columns = [c for c in model_features if c.startswith("msg_")]
    assert np.isfinite(frame[message_columns].to_numpy(dtype=float)).all()
    complete = frame[frame["feature_complete"] == 1]
    assert np.isfinite(complete[model_features].to_numpy(dtype=float)).all()


def test_message_passing_uses_edges_not_only_node_features():
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    messages = build_typed_messages(nodes, edges)
    message_cols = [c for c in messages.columns if c.startswith("msg_") and not c.endswith("_edge_count")]
    count_cols = [c for c in messages.columns if c.endswith("_edge_count")]
    assert message_cols
    assert count_cols
    assert messages[count_cols].sum().sum() > 0
    assert (messages[message_cols].abs().sum(axis=1) > 0).any()


def test_dynamic_graph_ranker_smoke_outputs_metrics():
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    predictions, metrics = run_dynamic_graph_ranker(
        nodes,
        edges,
        eval_years=[2018],
        target_horizon=3,
        min_train_years=3,
        max_epochs=20,
        seed=42,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert {"ridge_dynamic_graph", "mlp_dynamic_graph"}.issubset(set(metrics["model"]))
    assert metrics["ndcg_at_k"].between(0, 1).all()
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert set(predictions["claim_status"]) == {CLAIM_STATUS}


def test_dynamic_graph_ranker_supports_one_year_target():
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    predictions, metrics = run_dynamic_graph_ranker(
        nodes,
        edges,
        eval_years=[2023],
        target_horizon=1,
        min_train_years=3,
        max_epochs=15,
        seed=42,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert set(predictions["target_horizon_years"]) == {1}
    assert set(metrics["target_horizon_years"]) == {1}
    assert predictions["target_top3_label"].isin([0, 1]).all()


def test_ranker_script_does_not_read_forbidden_legacy_inputs_in_executable_paths():
    source_lines = SCRIPT_PATH.read_text().splitlines()
    read_lines = [line for line in source_lines if "read_csv" in line or "Path(" in line or " / " in line]
    code_only = "\n".join(read_lines)
    for term in FORBIDDEN_INPUTS:
        assert term not in code_only


def test_ranker_outputs_have_no_forbidden_action_columns():
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    predictions, metrics = run_dynamic_graph_ranker(
        nodes,
        edges,
        eval_years=[2018],
        target_horizon=3,
        min_train_years=3,
        max_epochs=10,
        seed=42,
    )
    for df in [predictions, metrics]:
        lowered = {c.lower() for c in df.columns}
        for term in FORBIDDEN_COLUMNS[1:]:
            assert term not in lowered
