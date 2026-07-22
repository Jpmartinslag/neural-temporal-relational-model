from pathlib import Path

import numpy as np
import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_commuting_relation_gate import (
    AVAILABILITY_FEATURE,
    CLAIM_STATUS,
    build_commuting_feature_frame,
    make_edge_variant,
    validate_paired_populations,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "src/modeles/france_ze2020/run_fr_ze2020_commuting_relation_gate.py"
)


def _edges() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "decision_year": [2020, 2020],
            "source_ze2020": ["0001", "0002"],
            "target_ze2020": ["0002", "0001"],
            "edge_weight": [1.0, 1.0],
        }
    )


def _nodes() -> pd.DataFrame:
    rows = []
    for zone, share, count in [("0001", 0.2, 20.0), ("0002", 0.8, 80.0)]:
        rows.append(
            {
                "node_id": f"{zone}_AA",
                "ze2020": zone,
                "sector_code": "AA",
                "decision_year": 2020,
                "sector_count_t": count,
                "sector_share_t": share,
                "sector_rank_in_ze_year_t": 1.0,
                "sector_growth_lag_1": 0.1,
                "mask_sector_growth_lag_1_available": 1.0,
                "dominant_sector_flag_t": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_real_commuting_aggregates_directed_neighbor_features():
    frame, columns = build_commuting_feature_frame(
        _nodes(), _edges(), expected_zone_count=2
    )
    first = frame.set_index("ze2020").loc["0001"]
    second = frame.set_index("ze2020").loc["0002"]
    assert first["commuting_out_neighbor__sector_share_t"] == 0.8
    assert second["commuting_out_neighbor__sector_share_t"] == 0.2
    assert first[AVAILABILITY_FEATURE] == 1
    assert len(columns) == 18


def test_masked_neighbor_growth_is_not_treated_as_zero():
    nodes = _nodes()
    nodes.loc[nodes["ze2020"] == "0002", "sector_growth_lag_1"] = np.inf
    nodes.loc[
        nodes["ze2020"] == "0002", "mask_sector_growth_lag_1_available"
    ] = 1.0
    frame, _ = build_commuting_feature_frame(
        nodes, _edges(), expected_zone_count=2
    )
    first = frame.set_index("ze2020").loc["0001"]
    assert first["commuting_out_neighbor__sector_growth_lag_1"] == 0.0
    assert (
        first["commuting_out_neighbor__sector_growth_lag_1__available_share"] == 0.0
    )


def test_variants_are_cross_ze_and_row_normalized():
    expanded = pd.concat(
        [
            _edges(),
            pd.DataFrame(
                {
                    "decision_year": [2020, 2020],
                    "source_ze2020": ["0001", "0002"],
                    "target_ze2020": ["0003", "0003"],
                    "edge_weight": [0.5, 0.5],
                }
            ),
        ],
        ignore_index=True,
    )
    for variant in ["real", "endpoint_randomized", "uniform_weights", "reversed_direction"]:
        result = make_edge_variant(expanded, variant, seed=7)
        assert not (result["source_ze2020"] == result["target_ze2020"]).any()
        sums = result.groupby(["decision_year", "source_ze2020"])["edge_weight"].sum()
        assert np.allclose(sums.to_numpy(float), 1.0)


def test_endpoint_randomization_preserves_source_weight_mass_and_target_multiset():
    expanded = pd.DataFrame(
        {
            "decision_year": [2020] * 6,
            "source_ze2020": ["0001", "0001", "0002", "0002", "0003", "0003"],
            "target_ze2020": ["0002", "0003", "0001", "0003", "0001", "0002"],
            "edge_weight": [0.8, 0.2, 0.6, 0.4, 0.7, 0.3],
        }
    )
    result = make_edge_variant(expanded, "endpoint_randomized", seed=17)
    assert sorted(result["target_ze2020"].tolist()) == sorted(
        expanded["target_ze2020"].tolist()
    )
    assert np.allclose(
        result.groupby("source_ze2020")["edge_weight"].sum().sort_index(),
        expanded.groupby("source_ze2020")["edge_weight"].sum().sort_index(),
    )


def test_population_validator_rejects_mismatched_view():
    rows = []
    for view in [
        "node_only",
        "commuting_availability_only",
        "commuting_real",
        "commuting_endpoint_randomized",
        "commuting_uniform_weights",
        "commuting_reversed_direction",
        "trajectory_similarity_reference",
        "commuting_target_shuffled",
    ]:
        rows.append(
            {
                "view": view,
                "seed": 42,
                "eval_year": 2022,
                "ze_fold": 0,
                "n_train": 100,
                "n_test": 20,
                "n_test_positive": 3,
            }
        )
    metrics = pd.DataFrame(rows)
    validate_paired_populations(metrics)
    metrics.loc[metrics["view"] == "commuting_uniform_weights", "n_test"] = 19
    try:
        validate_paired_populations(metrics)
    except ValueError as error:
        assert "commuting_uniform_weights" in str(error)
    else:
        raise AssertionError("Mismatched evaluation population was accepted")


def test_gate_script_has_no_legacy_or_neural_model():
    source = SCRIPT_PATH.read_text().lower()
    executable_inputs = "\n".join(
        line
        for line in source.splitlines()
        if "read_csv" in line or "parser.add_argument" in line or "default=" in line
    )
    for forbidden_input in [
        "graph_adjacency_mobility_v0",
        "dynamic_stgnn_feature_panel",
    ]:
        assert forbidden_input not in executable_inputs
    for forbidden_claim_or_model in [
        "mlpregressor",
        "gconvgru",
        "evolvegcn",
        "recommendation_score",
        "causal_effect",
    ]:
        assert forbidden_claim_or_model not in source
    assert CLAIM_STATUS in SCRIPT_PATH.read_text()
