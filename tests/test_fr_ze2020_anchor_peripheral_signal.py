from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import NODES_OUT_PATH
from src.modeles.france_ze2020.audit_fr_ze2020_anchor_peripheral_signal import (
    CLAIM_STATUS,
    add_anchor_peripheral_scores,
    run_anchor_peripheral_audit,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (
    DEFAULT_EDGES_PATH,
    build_pairwise_relation_samples,
    load_edges,
    load_nodes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/audit_fr_ze2020_anchor_peripheral_signal.py"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = load_nodes(NODES_OUT_PATH)
    edges = load_edges(DEFAULT_EDGES_PATH)
    return nodes, edges


def test_anchor_peripheral_scores_are_deterministic_formulas():
    nodes, edges = _load_inputs()
    samples = build_pairwise_relation_samples(
        nodes,
        edges,
        negative_strategy="dual_endpoint_matched_hard",
        negative_ratio=1,
        node_feature_lag=1,
        positive_edge_states=["new_relation"],
        seed=42,
    )
    scored = add_anchor_peripheral_scores(samples)
    expected_asymmetry = (
        scored["source_dominant_sector_flag_t"] - scored["target_dominant_sector_flag_t"]
    ).abs()
    expected_product = scored["source_sector_share_t"] * scored["target_sector_share_t"]
    assert np.allclose(scored["dominance_asymmetry_score"], expected_asymmetry)
    assert np.allclose(scored["sector_share_product_score"], expected_product)
    assert np.allclose(scored["anchor_peripheral_score"], expected_asymmetry * expected_product)


def test_anchor_peripheral_audit_reports_shuffle_drop():
    nodes, edges = _load_inputs()
    _, metrics = run_anchor_peripheral_audit(
        nodes,
        edges,
        scenarios=["dual_endpoint_matched_negatives", "dual_endpoint_temporal_sector_shuffle"],
        positive_edge_states=["new_relation"],
        node_feature_lag=1,
        seed=42,
    )
    all_years = metrics[metrics["eval_scope"] == "all_years"]
    assert {
        "dominance_asymmetry_score",
        "sector_share_product_score",
        "anchor_peripheral_score",
    } == set(all_years["score_name"])
    full = all_years[all_years["falsification_scenario"] == "dual_endpoint_matched_negatives"]
    assert full["ap_drop_vs_temporal_sector_shuffle"].notna().all()
    assert (full["ap_drop_vs_temporal_sector_shuffle"] > 0).all()
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}


def test_anchor_peripheral_audit_has_no_training_or_forbidden_claims():
    code = SCRIPT_PATH.read_text()
    forbidden = [
        "LogisticRegression",
        "MLP",
        ".fit(",
        "recommended_action",
        "policy_action",
        "causal_effect",
        "causal_impact",
        "validated_gnn",
    ]
    for term in forbidden:
        assert term not in code
