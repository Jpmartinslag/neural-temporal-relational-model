from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import NODES_OUT_PATH
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (
    CLAIM_STATUS,
    DEFAULT_EDGES_PATH,
    SCENARIOS,
    TEST_PAIR_MODES,
    apply_relation_scenario,
    build_pairwise_relation_samples,
    load_edges,
    run_dynamic_relation_learner,
    summarize_metrics,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str, "sector_code": str})
    edges = load_edges(DEFAULT_EDGES_PATH)
    return nodes, edges


def test_relation_learner_scenarios_are_explicit():
    assert SCENARIOS == [
        "full_control",
        "easy_random_negatives",
        "typed_hard_negatives",
        "edge_sign_only",
        "random_edge_targets",
        "temporal_shuffle",
        "sector_shuffle",
    ]
    assert TEST_PAIR_MODES == ["all", "unseen_pair"]


def test_pairwise_samples_have_balanced_positive_and_negative_rows():
    nodes, edges = _load_inputs()
    samples = build_pairwise_relation_samples(
        nodes,
        edges,
        negative_strategy="easy_random",
        negative_ratio=1,
        seed=42,
    )
    counts = samples["relation_label"].value_counts().to_dict()
    assert counts[0] == counts[1]
    assert {"observed_edge", "easy_random_non_edge"} == set(samples["sample_role"])


def test_node_feature_lag_uses_previous_year_features():
    nodes, edges = _load_inputs()
    samples = build_pairwise_relation_samples(
        nodes,
        edges,
        negative_strategy="typed_hard",
        negative_ratio=1,
        node_feature_lag=1,
        seed=42,
    )
    assert not samples.empty
    assert (samples["node_feature_year"] == samples["decision_year"] - 1).all()


def test_typed_hard_negatives_respect_edge_type_semantics():
    nodes, edges = _load_inputs()
    samples = build_pairwise_relation_samples(
        nodes,
        edges,
        negative_strategy="typed_hard",
        negative_ratio=1,
        seed=42,
    )
    negatives = samples[samples["relation_label"] == 0]
    assert not negatives.empty
    cross = negatives[negatives["edge_type"] == "cross_ze_same_sector"]
    intra = negatives[negatives["edge_type"] == "intra_ze_sector"]
    assert not cross.empty
    assert not intra.empty
    assert (cross["source_sector_code"] == cross["target_sector_code"]).all()
    assert (cross["source_ze2020"] != cross["target_ze2020"]).all()
    assert (intra["source_ze2020"] == intra["target_ze2020"]).all()
    assert (intra["source_sector_code"] != intra["target_sector_code"]).all()


def test_edge_sign_only_removes_magnitude_only():
    nodes, edges = _load_inputs()
    _, out_edges, _ = apply_relation_scenario(nodes, edges.copy(), "edge_sign_only", seed=42)
    assert set(out_edges["edge_weight"].abs()) == {1.0}
    assert np.array_equal(
        np.sign(out_edges["edge_weight"].to_numpy(dtype=float)),
        np.sign(edges["edge_weight"].to_numpy(dtype=float)),
    )


def test_random_edge_targets_keeps_non_self_edges():
    nodes, edges = _load_inputs()
    _, out_edges, _ = apply_relation_scenario(nodes, edges.copy(), "random_edge_targets", seed=42)
    assert not out_edges.empty
    assert not (out_edges["source_node_id"] == out_edges["target_node_id"]).any()
    parts = out_edges.assign(
        source_ze=out_edges["source_node_id"].str.split("_").str[0].str.zfill(4),
        source_sector=out_edges["source_node_id"].str.split("_").str[1],
        target_ze=out_edges["target_node_id"].str.split("_").str[0].str.zfill(4),
        target_sector=out_edges["target_node_id"].str.split("_").str[1],
    )
    cross = parts[parts["edge_type"] == "cross_ze_same_sector"]
    intra = parts[parts["edge_type"] == "intra_ze_sector"]
    assert (cross["source_sector"] == cross["target_sector"]).all()
    assert (intra["source_ze"] == intra["target_ze"]).all()


def test_relation_learner_smoke_outputs_metrics():
    nodes, edges = _load_inputs()
    predictions, metrics, manifest = run_dynamic_relation_learner(
        nodes,
        edges,
        scenarios=["full_control", "typed_hard_negatives"],
        eval_years=[2021],
        negative_ratio=1,
        min_train_years=2,
        seed=42,
        max_iter=100,
        k=20,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert set(metrics["falsification_scenario"]) == {"full_control", "typed_hard_negatives"}
    assert {"relation_logit", "target_popularity", "pair_history", "random"}.issubset(set(metrics["model"]))
    assert metrics["roc_auc"].between(0, 1).all()
    assert metrics["average_precision"].between(0, 1).all()
    assert metrics["precision_at_k"].between(0, 1).all()
    control_predictions = predictions[predictions["model"].isin(["target_popularity", "pair_history"])]
    assert not control_predictions.empty
    assert control_predictions["score"].between(0, 1).all()
    assert set(predictions["claim_status"]) == {CLAIM_STATUS}
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert set(manifest["claim_status"]) == {CLAIM_STATUS}


def test_summary_has_one_row_per_scenario_model():
    nodes, edges = _load_inputs()
    _, metrics, _ = run_dynamic_relation_learner(
        nodes,
        edges,
        scenarios=["full_control"],
        eval_years=[2021],
        negative_ratio=1,
        min_train_years=2,
        seed=42,
        max_iter=100,
        k=20,
    )
    summary = summarize_metrics(metrics)
    assert {"falsification_scenario", "model", "mean_average_precision"}.issubset(summary.columns)
    assert set(summary["test_pair_mode"]) == {"all"}
    assert set(summary["node_feature_lag"]) == {0}
    assert summary["mean_roc_auc"].between(0, 1).all()


def test_unseen_pair_mode_excludes_train_positive_pairs_from_test():
    nodes, edges = _load_inputs()
    predictions, metrics, _ = run_dynamic_relation_learner(
        nodes,
        edges,
        scenarios=["full_control"],
        eval_years=[2021],
        negative_ratio=1,
        min_train_years=2,
        seed=42,
        max_iter=100,
        k=20,
        test_pair_mode="unseen_pair",
    )
    assert set(metrics["test_pair_mode"]) == {"unseen_pair"}
    positive_pairs = edges[edges["decision_year"] < 2021][
        ["source_node_id", "target_node_id", "edge_type"]
    ].drop_duplicates()
    seen = set(map(tuple, positive_pairs.to_numpy()))
    tested = predictions[["source_node_id", "target_node_id", "edge_type"]].drop_duplicates()
    assert not any(tuple(row) in seen for row in tested.to_numpy())


def test_node_feature_lag_is_reported_in_metrics_and_predictions():
    nodes, edges = _load_inputs()
    predictions, metrics, manifest = run_dynamic_relation_learner(
        nodes,
        edges,
        scenarios=["full_control"],
        eval_years=[2022],
        negative_ratio=1,
        min_train_years=2,
        seed=42,
        max_iter=100,
        k=20,
        test_pair_mode="unseen_pair",
        node_feature_lag=1,
    )
    assert not predictions.empty
    assert (predictions["node_feature_year"] == predictions["decision_year"] - 1).all()
    assert set(metrics["node_feature_lag"]) == {1}
    assert set(manifest["node_feature_lag"]) == {1}


def test_relation_learner_has_no_forbidden_outputs_or_legacy_inputs():
    source_lines = SCRIPT_PATH.read_text().splitlines()
    read_lines = [line for line in source_lines if "read_csv" in line or "Path(" in line or " / " in line]
    code_only = "\n".join(read_lines)
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
        assert term not in code_only
