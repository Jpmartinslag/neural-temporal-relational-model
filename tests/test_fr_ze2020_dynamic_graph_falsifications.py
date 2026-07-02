from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_dynamic_graph_falsifications import (
    CLAIM_STATUS,
    SCENARIOS,
    apply_dynamic_graph_falsification,
    run_dynamic_graph_falsification_suite,
    summarize_metrics,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_dynamic_graph_falsifications.py"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_OUT_PATH)
    return nodes, edges


def test_dynamic_graph_falsification_scenarios_are_explicit():
    assert SCENARIOS == [
        "full_control",
        "no_edges",
        "edge_sign_only",
        "random_edge_weights",
        "random_edge_targets",
        "no_cross_ze_same_sector",
        "no_intra_ze_sector",
        "no_ze_similarity",
        "temporal_shuffle",
        "sector_shuffle",
    ]


def test_no_edges_removes_only_edges():
    nodes, edges = _load_inputs()
    out_nodes, out_edges = apply_dynamic_graph_falsification(nodes, edges, "no_edges", seed=42)
    assert len(out_nodes) == len(nodes)
    assert out_edges.empty


def test_edge_type_ablation_removes_only_one_type():
    nodes, edges = _load_inputs()
    _, out_edges = apply_dynamic_graph_falsification(
        nodes, edges, "no_ze_similarity", seed=42
    )
    assert "ze_similarity" not in set(out_edges["edge_type"])
    assert {"cross_ze_same_sector", "intra_ze_sector"}.issubset(set(out_edges["edge_type"]))


def test_edge_sign_only_removes_weight_magnitude_but_keeps_sign():
    nodes, edges = _load_inputs()
    sample = edges.head(1000).copy()
    _, out_edges = apply_dynamic_graph_falsification(nodes, sample, "edge_sign_only", seed=42)
    assert set(out_edges["edge_weight"].abs()) == {1.0}
    assert np.array_equal(
        np.sign(out_edges["edge_weight"].to_numpy(dtype=float)),
        np.sign(sample["edge_weight"].to_numpy(dtype=float)),
    )


def test_random_edge_weights_preserves_distribution_not_order():
    nodes, edges = _load_inputs()
    _, out_edges = apply_dynamic_graph_falsification(
        nodes, edges.head(1000).copy(), "random_edge_weights", seed=42
    )
    assert sorted(out_edges["edge_weight"].round(12).tolist()) == sorted(
        edges.head(1000)["edge_weight"].round(12).tolist()
    )
    assert not out_edges["edge_weight"].equals(edges.head(1000)["edge_weight"])


def test_random_edge_targets_preserves_valid_non_self_edges():
    nodes, edges = _load_inputs()
    _, out_edges = apply_dynamic_graph_falsification(
        nodes, edges.head(1000).copy(), "random_edge_targets", seed=42
    )
    assert not out_edges.empty
    assert not (out_edges["source_node_id"] == out_edges["target_node_id"]).any()


def test_dynamic_graph_falsification_smoke_outputs_expected_schema():
    nodes, edges = _load_inputs()
    predictions, metrics, manifest = run_dynamic_graph_falsification_suite(
        nodes,
        edges,
        scenarios=["full_control", "no_edges"],
        eval_years=[2018],
        seed=42,
        max_epochs=15,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert set(metrics["falsification_scenario"]) == {"full_control", "no_edges"}
    assert set(predictions["claim_status"]) == {CLAIM_STATUS}
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert set(manifest["falsification_scenario"]) == {"full_control", "no_edges"}
    assert metrics["ndcg_at_k"].between(0, 1).all()
    assert np.isfinite(predictions["score"].to_numpy(dtype=float)).all()


def test_dynamic_graph_falsification_supports_one_year_target():
    nodes, edges = _load_inputs()
    predictions, metrics, manifest = run_dynamic_graph_falsification_suite(
        nodes,
        edges,
        scenarios=["full_control"],
        eval_years=[2024],
        seed=42,
        max_epochs=10,
        target_horizon=1,
    )
    assert set(predictions["target_horizon_years"]) == {1}
    assert set(metrics["target_horizon_years"]) == {1}
    assert set(manifest["target_horizon_years"]) == {1}
    assert set(metrics["eval_year"]) == {2024}


def test_summary_has_one_row_per_scenario_model():
    nodes, edges = _load_inputs()
    _, metrics, _ = run_dynamic_graph_falsification_suite(
        nodes,
        edges,
        scenarios=["full_control"],
        eval_years=[2018],
        seed=42,
        max_epochs=10,
    )
    summary = summarize_metrics(metrics)
    assert {"falsification_scenario", "model", "mean_ndcg_at_k"}.issubset(summary.columns)
    assert summary["mean_ndcg_at_k"].between(0, 1).all()


def test_falsification_script_has_no_forbidden_outputs_or_legacy_inputs():
    source = SCRIPT_PATH.read_text()
    forbidden = [
        "dynamic_stgnn_feature_panel",
        "graph_adjacency_core_v0",
        "graph_adjacency_mobility_v0",
        "recommended_action",
        "policy_action",
        "causal_effect",
        "causal_impact",
    ]
    for term in forbidden:
        assert term not in source
