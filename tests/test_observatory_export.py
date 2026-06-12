"""Tests for HERALD Observatory aggregate v0.1.1 and sector v0.2 exports."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.build_observatory_export import (
    AGGREGATE_PANEL_PATH,
    SECTOR_PANEL_PATH,
    VALID_ECONOMIC_STATES,
    _economic_state,
    build_aggregate_export,
    build_sector_export,
)

KEY = ["country", "territory_id", "observation_year", "sector_id"]
EVIDENCE_COLUMNS = {
    "data_evidence_tier",
    "forecast_evidence_tier",
    "graph_evidence_tier",
}


def _load_product(builder, tmp_path):
    output = tmp_path / builder.__name__
    csv_path = builder(output_dir=output)
    stem = csv_path.stem.removesuffix("_panel")
    panel = pd.read_csv(
        csv_path,
        dtype={"territory_id": str, "meta_nuts3_code": str},
        low_memory=False,
    )
    manifest = json.loads((output / f"{stem}_manifest.json").read_text())
    summary = json.loads((output / f"{stem}_summary.json").read_text())
    return panel, manifest, summary, csv_path


@pytest.fixture(scope="module")
def aggregate_product(tmp_path_factory):
    return _load_product(
        build_aggregate_export, tmp_path_factory.mktemp("observatory_aggregate")
    )


@pytest.fixture(scope="module")
def sector_product(tmp_path_factory):
    return _load_product(
        build_sector_export, tmp_path_factory.mktemp("observatory_sector")
    )


def test_deceleration_is_positive_but_slower_growth():
    assert _economic_state(100, 120, 126) == "deceleration"


def test_negative_after_growth_is_decline():
    assert _economic_state(100, 120, 110) == "decline"


def test_acceleration_is_faster_positive_growth():
    assert _economic_state(100, 105, 120) == "acceleration"


def test_recovery_follows_decline():
    assert _economic_state(100, 90, 100) == "recovery"


def test_stagnation_threshold():
    assert _economic_state(100, 102, 103) == "stagnation"


@pytest.mark.parametrize("fixture_name", ["aggregate_product", "sector_product"])
def test_common_schema_and_unique_key(request, fixture_name):
    panel, _, _, _ = request.getfixturevalue(fixture_name)
    assert EVIDENCE_COLUMNS.issubset(panel.columns)
    assert not panel.duplicated(KEY).any()
    assert set(panel["economic_state"]).issubset(VALID_ECONOMIC_STATES)
    assert panel["sector_graph_available"].eq(0).all()
    assert panel["forecast_lower"].isna().all()
    assert panel["forecast_upper"].isna().all()


@pytest.mark.parametrize("fixture_name", ["aggregate_product", "sector_product"])
def test_structural_absence_never_becomes_zero(request, fixture_name):
    panel, _, _, _ = request.getfixturevalue(fixture_name)
    absent = panel["structural_mask"].eq(0)
    assert panel.loc[absent, "observed_value"].isna().all()
    assert panel.loc[absent, "persistence_forecast"].isna().all()
    assert panel.loc[absent, "ridge_forecast"].isna().all()


@pytest.mark.parametrize("fixture_name", ["aggregate_product", "sector_product"])
def test_persistence_uses_prior_observation(request, fixture_name):
    panel, _, _, _ = request.getfixturevalue(fixture_name)
    for _, group in panel.sort_values(KEY).groupby(
        ["country", "territory_id", "sector_id"]
    ):
        previous = group["observed_value"].shift(1)
        valid = group["persistence_forecast"].notna()
        assert np.allclose(
            group.loc[valid, "persistence_forecast"],
            previous.loc[valid],
            equal_nan=True,
        )


@pytest.mark.parametrize("fixture_name", ["aggregate_product", "sector_product"])
def test_manifest_checksum_and_causal_contract(request, fixture_name):
    _, manifest, _, csv_path = request.getfixturevalue(fixture_name)
    checksum = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert manifest["sha256"] == checksum
    assert manifest["causal_safety"]["same_year_feature_used"] is False
    assert manifest["causal_safety"]["rolling_origin"] is True
    assert manifest["causal_safety"]["leakage_free"] is True


def test_aggregate_product_contract(aggregate_product):
    panel, manifest, _, _ = aggregate_product
    source = pd.read_csv(AGGREGATE_PANEL_PATH)
    assert len(panel) == len(source) == 1963
    assert set(panel["country"]) == {"AT", "IT", "PT"}
    assert set(panel["sector_id"]) == {"AGGREGATE"}
    assert panel["territorial_graph_available"].eq(0).all()
    assert set(panel["data_evidence_tier"]) == {"harmonized_enterprise_birth"}
    assert manifest["version"] == "0.1.1"


def test_sector_product_contract(sector_product):
    panel, manifest, _, _ = sector_product
    source = pd.read_csv(SECTOR_PANEL_PATH, low_memory=False)
    assert len(panel) == len(source) == 45945
    assert set(panel["country"]) == {"FR", "NL", "PT"}
    assert panel["sector_id"].nunique() == 9
    assert manifest["version"] == "0.2"


def test_sector_country_dimensions(sector_product):
    panel, _, summary, _ = sector_product
    expected = {
        "FR": (280, 9, 2012, 2025),
        "NL": (40, 9, 2007, 2025),
        "PT": (25, 9, 2008, 2024),
    }
    for country, (territories, sectors, year_min, year_max) in expected.items():
        actual = summary["countries"][country]
        assert actual["territories"] == territories
        assert actual["sectors"] == sectors
        assert actual["year_min"] == year_min
        assert actual["year_max"] == year_max


def test_pt_kz_is_structural_absence(sector_product):
    panel, _, _, _ = sector_product
    pt_kz = panel[(panel["country"] == "PT") & (panel["sector_id"] == "KZ")]
    assert len(pt_kz) == 25 * 17
    assert pt_kz["structural_mask"].eq(0).all()
    assert pt_kz["data_evidence_tier"].eq("structural_absence").all()
    assert pt_kz["territorial_graph_available"].eq(0).all()


def test_nl_oq_missing_years_remain_missing(sector_product):
    panel, _, _, _ = sector_product
    nl_oq = panel[(panel["country"] == "NL") & (panel["sector_id"] == "OQ")]
    missing = nl_oq["observation_mask"].eq(0)
    assert missing.any()
    assert nl_oq.loc[missing, "observed_value"].isna().all()
    assert nl_oq["structural_mask"].eq(1).all()
    assert nl_oq.loc[missing, "data_evidence_tier"].eq(
        "missing_observation"
    ).all()


def test_graph_evidence_is_separate_from_forecast_evidence(sector_product):
    panel, _, _, _ = sector_product
    eligible = panel[
        panel["observation_mask"].eq(1) & panel["structural_mask"].eq(1)
    ]
    assert eligible["graph_evidence_tier"].eq(
        "supported_association_field"
    ).all()
    assert "validated_loco" not in set(eligible["forecast_evidence_tier"])


def test_outputs_are_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    p1 = build_sector_export(output_dir=first)
    p2 = build_sector_export(output_dir=second)
    assert hashlib.sha256(p1.read_bytes()).hexdigest() == hashlib.sha256(
        p2.read_bytes()
    ).hexdigest()


def test_no_p6_or_q7_dependency_in_builder():
    source = Path(
        "src/data/european_panel/build_observatory_export.py"
    ).read_text()
    lowered = source.lower()
    assert "dual_graph_s1" not in lowered
    assert "learned_sector_edges" not in lowered
    assert "0.0204" not in source
