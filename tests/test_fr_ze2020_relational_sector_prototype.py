"""
Consistency tests for the FR ZE2020 relational + sector prototype panel
(MVP2 integration step). Generator:
src/data/france_ze2020/build_fr_ze2020_relational_sector_prototype_panel.py.
Joins the existing Category A relational panel with Category C sector
features WITHOUT modifying either input.
"""

import ast
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_relational_sector_prototype_panel import (
    OUT_PATH,
    RELATIONAL_PANEL_PATH,
    SECTOR_FEATURES_PATH,
    build_prototype_panel,
    load_relational_panel,
    load_sector_features,
)

REPO_ROOT = Path(__file__).parent.parent
BUILDER_PATH = (
    REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_relational_sector_prototype_panel.py"
)

EXPECTED_NEW_COLUMNS = [
    "dominant_sector_lag_1",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "mask_ze_sector_distribution_lag_1_available",
    "top_sector_signal_lag_1",
]

FORBIDDEN_COLUMN_NAMES = {
    "growth_1y",
    "growth_2y",
    "is_covid_year",
    "is_post_covid_rebound",
    "feature_forecast_safe",
    "has_urssaf_source",
}


@pytest.fixture(scope="module")
def prototype():
    assert OUT_PATH.exists(), f"Prototype panel not found: {OUT_PATH}"
    return pd.read_csv(OUT_PATH, dtype={"ze2020": str})


def test_file_exists():
    assert OUT_PATH.exists()


def test_schema_extends_relational_panel_with_sector_columns(prototype):
    relational = load_relational_panel()
    assert list(prototype.columns) == list(relational.columns) + EXPECTED_NEW_COLUMNS


def test_row_count_unchanged_from_relational_panel(prototype):
    relational = load_relational_panel()
    assert len(prototype) == len(relational) == 3920


def test_no_forbidden_columns(prototype):
    cols_lower = {c.lower() for c in prototype.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)
    assert not any("stgnn" in c for c in cols_lower)


def test_builder_does_not_read_legacy_or_unprovenanced_matrices():
    source = BUILDER_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_inputs_not_modified_by_this_stage():
    assert RELATIONAL_PANEL_PATH.exists()
    assert SECTOR_FEATURES_PATH.exists()

    before_relational = load_relational_panel()
    before_sector = load_sector_features()
    build_prototype_panel()
    after_relational = load_relational_panel()
    after_sector = load_sector_features()

    pd.testing.assert_frame_equal(before_relational, after_relational)
    pd.testing.assert_frame_equal(before_sector, after_sector)


def test_top_sector_signal_matches_dominant_sectors_own_growth(prototype):
    """top_sector_signal_lag_1 for a row must equal that same row's
    dominant_sector_lag_1's own sector_growth_lag_1 -- a self-consistency
    cross-check against the sector features file directly."""
    sector_features = load_sector_features()
    sample = prototype.dropna(subset=["dominant_sector_lag_1", "top_sector_signal_lag_1"]).iloc[:20]

    for _, row in sample.iterrows():
        match = sector_features[
            (sector_features["ze2020"] == row["ze2020"])
            & (sector_features["year"] == row["year"])
            & (sector_features["sector_code"] == row["dominant_sector_lag_1"])
        ]
        assert len(match) == 1
        assert match.iloc[0]["sector_growth_lag_1"] == pytest.approx(row["top_sector_signal_lag_1"])


def test_sector_distribution_unavailable_only_in_2012(prototype):
    year_2012 = prototype[prototype["year"] == 2012]
    assert (year_2012["mask_ze_sector_distribution_lag_1_available"] == 0).all()

    later = prototype[prototype["year"] >= 2013]
    assert (later["mask_ze_sector_distribution_lag_1_available"] == 1).all()


def test_relational_panel_checksum_matches_recorded_value():
    """Pinning the relational panel's checksum here too -- this integration
    step depends on it staying byte-identical to what was reconciled when
    this test was written."""
    content = RELATIONAL_PANEL_PATH.read_bytes()
    assert len(content) == 576032
    assert hashlib.sha256(content).hexdigest().startswith("b8faad7bd88238be2e4f")
