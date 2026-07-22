import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_relational_transition_transfer_probe import (
    add_graph_changes,
    assign_ze_folds,
    eligible_transition_candidates,
)


def test_assign_ze_folds_is_stable_and_ze_disjoint() -> None:
    frame = pd.DataFrame({"ze2020": ["0051", "0051", "0056", "0060", "0061"]})
    first = assign_ze_folds(frame, n_folds=2)
    second = assign_ze_folds(frame.sample(frac=1, random_state=7), n_folds=2)
    mapping_first = dict(zip(frame["ze2020"], first))
    mapping_second = dict(zip(frame.sample(frac=1, random_state=7)["ze2020"], second))
    assert mapping_first == mapping_second
    assert first.iloc[0] == first.iloc[1]


def test_graph_changes_use_only_same_node_previous_snapshot() -> None:
    frame = pd.DataFrame(
        {
            "node_id": ["0051_BE", "0051_BE", "0056_BE", "0056_BE"],
            "decision_year": [2020, 2021, 2020, 2021],
            "relation_graph_in_count": [2.0, 5.0, 10.0, 7.0],
            "relation_graph_in_signal_mean": [0.2, 0.8, 0.4, 0.1],
        }
    )
    changed, degree, relation = add_graph_changes(frame)
    row = changed[(changed["node_id"] == "0051_BE") & (changed["decision_year"] == 2021)].iloc[0]
    assert row["delta__relation_graph_in_count"] == 3.0
    assert abs(row["delta__relation_graph_in_signal_mean"] - 0.6) < 1e-12
    assert "relation_graph_in_count" in degree
    assert "delta__relation_graph_in_signal_mean" in relation


def test_transition_candidates_exclude_existing_top3_sectors() -> None:
    frame = pd.DataFrame(
        {
            "node_id": [f"0051_{code}" for code in ["A", "B", "C", "D"]],
            "ze2020": ["0051"] * 4,
            "decision_year": [2020] * 4,
            "sector_rank_in_ze_year_t": [1.0, 2.0, 3.0, 4.0],
            "future_top3_growth_3y_label": [0, 0, 0, 1],
            "future_growth_3y": [0.1, 0.2, 0.3, 0.4],
            "mask_future_growth_3y_available": [1] * 4,
            "feature_complete": [1] * 4,
        }
    )
    candidates = eligible_transition_candidates(frame)
    assert candidates["node_id"].tolist() == ["0051_D"]
    assert candidates["future_top3_entry_3y_label"].tolist() == [1]
