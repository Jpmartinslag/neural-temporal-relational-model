from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_commuting_strict_ex_ante_edges import (
    CLAIM_STATUS,
    STRICT_EDGES_OUT_PATH,
    STRICT_SUMMARY_OUT_PATH,
    build_strict_ex_ante_edges,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "src/data/france_ze2020/build_fr_ze2020_commuting_strict_ex_ante_edges.py"
)


def _source_fixture() -> pd.DataFrame:
    rows = []
    for snapshot, valid_from, valid_through, release in [
        (2012, 2016, 2020, "2015-06-25"),
        (2017, 2021, 2026, "2020-12-09"),
        (2023, 2027, 9999, "2026-06-25"),
    ]:
        for source, target, weight, self_loop in [
            ("0001", "0001", 0.0, 1),
            ("0001", "0002", 1.0, 0),
            ("0002", "0001", 1.0, 0),
            ("0002", "0002", 0.0, 1),
        ]:
            rows.append(
                {
                    "source_ze2020": source,
                    "target_ze2020": target,
                    "observation_year": snapshot,
                    "commuter_count": 100.0,
                    "origin_worker_share": 0.2,
                    "origin_in_scope_share": 0.3,
                    "origin_interze_share": weight,
                    "is_self_loop": self_loop,
                    "aggregated_flow_below_200_caution": 1,
                    "strict_ex_ante_valid_from_year": valid_from,
                    "strict_ex_ante_valid_through_year": valid_through,
                    "source_release_date": release,
                }
            )
    return pd.DataFrame(rows)


def test_strict_assignment_excludes_unpublished_snapshot():
    edges, summary = build_strict_ex_ante_edges(
        _source_fixture(), decision_years=tuple(range(2012, 2026))
    )
    assert summary["unavailable_decision_years"] == [2012, 2013, 2014, 2015]
    assert set(edges.loc[edges["decision_year"] <= 2020, "observation_year"]) == {2012}
    assert set(edges.loc[edges["decision_year"] >= 2021, "observation_year"]) == {2017}
    assert 2023 not in set(edges["observation_year"])


def test_strict_assignment_is_directed_cross_ze_and_normalized():
    edges, _ = build_strict_ex_ante_edges(
        _source_fixture(), decision_years=(2020, 2021)
    )
    assert not (edges["source_ze2020"] == edges["target_ze2020"]).any()
    sums = edges.groupby(["decision_year", "source_ze2020"])["edge_weight"].sum()
    assert np.allclose(sums.to_numpy(float), 1.0)
    assert set(edges["edge_type"]) == {"ze_commuting_strict_ex_ante"}
    assert set(edges["claim_status"]) == {CLAIM_STATUS}


def test_generated_strict_edges_when_available():
    if not STRICT_EDGES_OUT_PATH.exists():
        return
    edges = pd.read_csv(
        STRICT_EDGES_OUT_PATH,
        dtype={"source_ze2020": str, "target_ze2020": str},
    )
    assert edges["decision_year"].min() == 2016
    assert edges["decision_year"].max() == 2025
    assert set(edges["observation_year"]) == {2012, 2017}
    assert 2023 not in set(edges["observation_year"])
    assert edges["edge_id"].is_unique
    assert edges["source_ze2020"].nunique() == 280
    assert edges["target_ze2020"].nunique() == 280
    assert np.isfinite(edges.select_dtypes(include=[np.number]).to_numpy(float)).all()
    assert (
        pd.to_datetime(edges["source_release_date"]).dt.year
        < edges["decision_year"]
    ).all()


def test_generated_summary_when_available():
    if not STRICT_SUMMARY_OUT_PATH.exists():
        return
    import json

    summary = json.loads(STRICT_SUMMARY_OUT_PATH.read_text())
    assert summary["unavailable_decision_years"] == [2012, 2013, 2014, 2015]
    assert summary["available_decision_years"] == list(range(2016, 2026))
    assert summary["source_zone_count"] == 280
    assert summary["target_zone_count"] == 280


def test_strict_builder_has_no_legacy_or_model_logic():
    source = SCRIPT_PATH.read_text().lower()
    for forbidden in [
        "graph_adjacency_mobility_v0",
        "dynamic_stgnn_feature_panel",
        "mlpregressor",
        "logisticregression",
        "recommendation_score",
        "causal_effect",
    ]:
        assert forbidden not in source
