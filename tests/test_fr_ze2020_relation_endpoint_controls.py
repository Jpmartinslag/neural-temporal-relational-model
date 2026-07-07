from pathlib import Path

import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import NODES_OUT_PATH
from src.modeles.france_ze2020.audit_fr_ze2020_relation_endpoint_controls import (
    CLAIM_STATUS,
    DEFAULT_PAIR_MODES,
    run_endpoint_control_audit,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (
    DEFAULT_EDGES_PATH,
    load_edges,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/audit_fr_ze2020_relation_endpoint_controls.py"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.read_csv(NODES_OUT_PATH, dtype={"ze2020": str, "sector_code": str})
    edges = load_edges(DEFAULT_EDGES_PATH)
    return nodes, edges


def test_endpoint_control_audit_reports_all_pair_modes_and_margins():
    nodes, edges = _load_inputs()
    pair_summary, endpoint_summary = run_endpoint_control_audit(
        nodes,
        edges,
        scenarios=["pair_distance_hard_negatives"],
        eval_years=[2022],
        positive_edge_states=["new_relation"],
        max_iter=100,
        k=20,
    )
    assert set(pair_summary["pair_feature_mode"]) == set(DEFAULT_PAIR_MODES)
    assert len(endpoint_summary) == 1
    row = endpoint_summary.iloc[0]
    best_endpoint = max(
        row["mean_average_precision_source_only"],
        row["mean_average_precision_target_only"],
    )
    assert row["best_endpoint_ap"] == best_endpoint
    assert row["compatibility_minus_best_endpoint_ap"] == (
        row["mean_average_precision_compatibility_only"] - best_endpoint
    )
    assert row["both_minus_best_endpoint_ap"] == (
        row["mean_average_precision_both"] - best_endpoint
    )
    assert "combined_gate_pass" in endpoint_summary.columns
    assert "compatibility_ap_drop_vs_shuffle" in endpoint_summary.columns


def test_dual_endpoint_gate_requires_margin_and_shuffle_drop():
    nodes, edges = _load_inputs()
    _, endpoint_summary = run_endpoint_control_audit(
        nodes,
        edges,
        scenarios=["dual_endpoint_matched_negatives", "dual_endpoint_temporal_sector_shuffle"],
        eval_years=[2022, 2023],
        positive_edge_states=["new_relation"],
        max_iter=100,
        k=20,
        margin_threshold=0.02,
        shuffle_drop_threshold=0.10,
    )
    rows = endpoint_summary.set_index("falsification_scenario")
    assert rows.loc["dual_endpoint_matched_negatives", "compatibility_gate_pass"] == 1
    assert rows.loc["dual_endpoint_matched_negatives", "compatibility_ap_drop_vs_shuffle"] > 0.10
    assert rows.loc["dual_endpoint_matched_negatives", "combined_gate_pass"] == 1


def test_endpoint_control_audit_keeps_exploratory_claim_status():
    nodes, edges = _load_inputs()
    _, endpoint_summary = run_endpoint_control_audit(
        nodes,
        edges,
        scenarios=["source_distance_target_preserving_negatives"],
        eval_years=[2022],
        positive_edge_states=["new_relation"],
        max_iter=100,
        k=20,
    )
    assert set(endpoint_summary["claim_status"]) == {CLAIM_STATUS}
    assert endpoint_summary["claim_status"].str.contains("not_recommendation").all()


def test_endpoint_control_audit_has_no_forbidden_claim_language():
    code = SCRIPT_PATH.read_text()
    forbidden = [
        "recommended_action",
        "policy_action",
        "causal_effect",
        "causal_impact",
        "validated_gnn",
    ]
    for term in forbidden:
        assert term not in code
