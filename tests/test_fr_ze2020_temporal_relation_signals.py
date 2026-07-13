from pathlib import Path

import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_temporal_relation_signals import (
    OUT_PATH,
    OUTPUT_COLUMNS,
    _add_asof_recurrence,
    _ze_similarity_rows,
    load_model_ready_panel,
)


def test_temporal_relation_output_contract():
    assert Path(OUT_PATH).exists()
    signals = pd.read_csv(OUT_PATH)
    assert list(signals.columns) == OUTPUT_COLUMNS
    assert not signals.duplicated(["relation_id", "decision_year"]).any()
    assert set(signals["relation_family"]) == {
        "ze_similarity",
        "cross_ze_same_sector",
        "intra_ze_sector",
    }
    assert signals["stability_score"].between(0, 1).all()
    assert set(signals["claim_status"]) == {
        "temporal_relation_snapshot_exploratory_not_causal"
    }


def test_recurrence_denominator_uses_only_available_years():
    frame = pd.DataFrame(
        [
            {"relation_family": "x", "relation_id": "a", "decision_year": 2017},
            {"relation_family": "x", "relation_id": "a", "decision_year": 2019},
            {"relation_family": "x", "relation_id": "b", "decision_year": 2018},
        ]
    )
    result = _add_asof_recurrence(frame)
    edge_a = result[result["relation_id"] == "a"].set_index("decision_year")
    assert edge_a.loc[2017, "stability_score"] == 1.0
    assert edge_a.loc[2019, "recurrence_count_to_t"] == 2
    assert edge_a.loc[2019, "available_relation_years_to_t"] == 3
    assert edge_a.loc[2019, "stability_score"] == 2 / 3


def test_ze_similarity_snapshots_are_invariant_to_future_truncation():
    panel = load_model_ready_panel()
    sector_codes = ["GI"]
    full_rows = pd.DataFrame(_ze_similarity_rows(panel, sector_codes))
    truncated_rows = pd.DataFrame(
        _ze_similarity_rows(panel[panel["year"] <= 2020], sector_codes)
    )
    columns = [
        "source_node_id",
        "target_node_id",
        "decision_year",
        "relation_family",
        "signal_strength",
    ]
    full_asof = full_rows[full_rows["decision_year"] <= 2020][columns].sort_values(columns[:-1])
    truncated = truncated_rows[columns].sort_values(columns[:-1])
    pd.testing.assert_frame_equal(
        full_asof.reset_index(drop=True),
        truncated.reset_index(drop=True),
    )
