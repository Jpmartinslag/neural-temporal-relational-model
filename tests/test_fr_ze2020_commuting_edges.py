from pathlib import Path
import tempfile
import zipfile

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_commuting_edges import (
    ARM_TO_PARENT,
    EDGES_OUT_PATH,
    SNAPSHOTS,
    SUMMARY_OUT_PATH,
    HistoricalZeResolver,
    aggregate_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_commuting_edges.py"


def test_snapshot_contract_has_separate_observation_and_release_clocks():
    assert [spec.observation_year for spec in SNAPSHOTS] == [2012, 2017, 2023]
    assert [spec.strict_ex_ante_valid_from_year for spec in SNAPSHOTS] == [2016, 2021, 2027]
    assert SNAPSHOTS[-1].observation_valid_from_year == 2024
    assert SNAPSHOTS[-1].strict_ex_ante_valid_from_year == 2027


def test_historical_resolver_advances_mergers_and_rejects_cross_scope_results():
    resolver = HistoricalZeResolver(
        code_to_ze={"A": "0001", "C": "0002", "D": "0003"},
        scope={"0001", "0002"},
        movements_by_date={
            "2020-01-01": {"OLD": {"MID"}},
            "2022-01-01": {"MID": {"A"}, "SPLIT": {"C", "D"}},
        },
        geography_reference_date="2019-01-01",
    )
    assert resolver.resolve("OLD") == "0001"
    assert resolver.resolve("SPLIT") is None
    assert resolver.resolve("UNKNOWN") is None


def test_arm_codes_are_collapsed_to_parent_communes():
    assert ARM_TO_PARENT["75101"] == "75056"
    assert ARM_TO_PARENT["69381"] == "69123"
    assert ARM_TO_PARENT["13216"] == "13055"


def test_synthetic_snapshot_preserves_direction_and_denominators():
    spec = SNAPSHOTS[0]
    content = (
        f"CODGEO;DCLT;{spec.value_column}\n"
        "A;A;100\n"
        "A;B;50\n"
        "A;FOREIGN;10\n"
        "B;A;20\n"
        "OUT;A;30\n"
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "snapshot.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(spec.archive_member, content.encode(spec.encoding))
        edges, summary = aggregate_snapshot(
            path,
            spec,
            scope={"0001", "0002"},
            code_to_ze={"A": "0001", "B": "0002", "OUT": "9999"},
            movements_by_date={},
        )

    a_to_b = edges[
        (edges["source_ze2020"] == "0001")
        & (edges["target_ze2020"] == "0002")
    ].iloc[0]
    b_to_a = edges[
        (edges["source_ze2020"] == "0002")
        & (edges["target_ze2020"] == "0001")
    ].iloc[0]
    assert a_to_b["commuter_count"] == 50
    assert np.isclose(a_to_b["origin_worker_share"], 50 / 160)
    assert np.isclose(a_to_b["origin_in_scope_share"], 50 / 150)
    assert a_to_b["origin_interze_share"] == 1
    assert b_to_a["commuter_count"] == 20
    assert summary["input_rows"] == 5
    assert np.isclose(summary["source_in_scope_share"], 180 / 210)
    assert np.isclose(summary["in_scope_pair_coverage"], 170 / 210)


def test_generated_edges_schema_and_invariants_when_available():
    if not EDGES_OUT_PATH.exists():
        return
    edges = pd.read_csv(
        EDGES_OUT_PATH,
        dtype={"source_ze2020": str, "target_ze2020": str},
    )
    required = {
        "relation_id",
        "source_ze2020",
        "target_ze2020",
        "observation_year",
        "relation_type",
        "relation_direction",
        "commuter_count",
        "origin_worker_share",
        "origin_in_scope_share",
        "origin_interze_share",
        "is_self_loop",
        "aggregated_flow_below_200_caution",
        "strict_ex_ante_valid_from_year",
        "source_release_date",
        "claim_status",
    }
    assert required.issubset(edges.columns)
    assert set(edges["observation_year"]) == {2012, 2017, 2023}
    assert edges["relation_id"].is_unique
    assert edges["source_ze2020"].str.match(r"^\d{4}$").all()
    assert edges["target_ze2020"].str.match(r"^\d{4}$").all()
    assert np.isfinite(edges.select_dtypes(include=[np.number]).to_numpy(float)).all()
    assert (edges["commuter_count"] > 0).all()
    assert edges["origin_worker_share"].between(0, 1).all()
    assert edges["origin_in_scope_share"].between(0, 1).all()
    assert edges["origin_interze_share"].between(0, 1).all()
    self_edges = edges[edges["is_self_loop"] == 1]
    assert (self_edges["source_ze2020"] == self_edges["target_ze2020"]).all()
    assert (self_edges["origin_interze_share"] == 0).all()
    assert set(edges["aggregated_flow_below_200_caution"]).issubset({0, 1})
    assert (
        edges["aggregated_flow_below_200_caution"]
        == (edges["commuter_count"] < 200.0).astype(int)
    ).all()
    assert set(edges["claim_status"]) == {"official_commuting_relation_not_causal"}


def test_interze_weights_sum_to_one_per_source_snapshot_when_available():
    if not EDGES_OUT_PATH.exists():
        return
    edges = pd.read_csv(EDGES_OUT_PATH)
    cross = edges[edges["is_self_loop"] == 0]
    sums = cross.groupby(["observation_year", "source_ze2020"])[
        "origin_interze_share"
    ].sum()
    assert np.allclose(sums.to_numpy(float), 1.0, atol=1e-9)


def test_summary_records_source_coverage_when_available():
    if not SUMMARY_OUT_PATH.exists():
        return
    import json

    summary = json.loads(SUMMARY_OUT_PATH.read_text())
    assert summary["snapshot_count"] == 3
    assert summary["canonical_scope_zone_count"] == 280
    assert len(summary["snapshots"]) == 3
    assert all(
        item["source_code_resolution_coverage"] > 0.98
        for item in summary["snapshots"]
    )


def test_builder_does_not_reference_legacy_inputs():
    source = SCRIPT_PATH.read_text()
    assert "graph_adjacency_mobility_v0" not in source
    assert "dynamic_stgnn_feature_panel" not in source


def test_builder_has_no_model_or_recommendation_logic():
    source = SCRIPT_PATH.read_text().lower()
    for forbidden in ["mlpregressor", "gnn", "recommendation_score", "causal_effect"]:
        assert forbidden not in source
