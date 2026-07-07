from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import NODES_OUT_PATH
from src.modeles.france_ze2020.audit_fr_ze2020_relation_lift_over_formulas import (
    CLAIM_STATUS,
    FORMULA_SCORE_COLUMNS,
    run_relation_lift_over_formulas_audit,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (
    DEFAULT_EDGES_PATH,
    load_edges,
    load_nodes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT / "src/modeles/france_ze2020/audit_fr_ze2020_relation_lift_over_formulas.py"
)


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = load_nodes(NODES_OUT_PATH)
    edges = load_edges(DEFAULT_EDGES_PATH)
    return nodes, edges


@pytest.fixture(scope="module")
def relation_lift_metrics() -> pd.DataFrame:
    nodes, edges = _load_inputs()
    return run_relation_lift_over_formulas_audit(
        nodes,
        edges,
        scenarios=["dual_endpoint_matched_negatives", "dual_endpoint_temporal_sector_shuffle"],
        eval_years=[2022, 2023, 2024, 2025],
        positive_edge_states=["new_relation"],
        node_feature_lag=1,
        seed=42,
    )


def test_relation_lift_audit_compares_formulas_and_local_learner(
    relation_lift_metrics: pd.DataFrame,
):
    metrics = relation_lift_metrics
    mean_rows = metrics[metrics["eval_year"].astype(str) == "mean"]
    assert set(FORMULA_SCORE_COLUMNS).issubset(set(metrics["model_or_score"]))
    assert "relation_logit" in set(metrics["model_or_score"])
    assert "ap_lift_over_best_formula" in metrics.columns
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    full_mean = mean_rows[
        (mean_rows["falsification_scenario"] == "dual_endpoint_matched_negatives")
        & (mean_rows["model_or_score"] == "relation_logit")
    ]
    assert not full_mean.empty
    assert full_mean["ap_lift_over_best_formula"].iloc[0] > 0


def test_relation_lift_audit_retains_shuffle_control(relation_lift_metrics: pd.DataFrame):
    metrics = relation_lift_metrics
    mean_rows = metrics[metrics["eval_year"].astype(str) == "mean"]
    full = mean_rows[
        (mean_rows["falsification_scenario"] == "dual_endpoint_matched_negatives")
        & (mean_rows["model_or_score"] == "relation_logit")
    ]["average_precision"].iloc[0]
    shuffle = mean_rows[
        (mean_rows["falsification_scenario"] == "dual_endpoint_temporal_sector_shuffle")
        & (mean_rows["model_or_score"] == "relation_logit")
    ]["average_precision"].iloc[0]
    assert full > shuffle


def test_relation_lift_audit_has_no_forbidden_claims_or_inputs():
    code = SCRIPT_PATH.read_text()
    forbidden = [
        "recommended_action",
        "policy_action",
        "causal_effect",
        "causal_impact",
        "validated_gnn",
        "dynamic_stgnn_feature_panel",
        "graph_adjacency_core_v0",
        "graph_adjacency_mobility_v0",
    ]
    for term in forbidden:
        assert term not in code
