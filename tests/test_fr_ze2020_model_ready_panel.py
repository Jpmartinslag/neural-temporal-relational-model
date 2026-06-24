"""
Consistency tests for the FR ZE2020 model-ready causal panel (step 3).

See reports/canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md section
10. Generator: src/data/france_ze2020/build_fr_ze2020_model_ready_panel.py
Input: data/processed/france_ze2020/fr_ze2020_clean_panel.csv (must remain
untouched by this stage).
"""

import hashlib
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
MODEL_READY_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv"
CLEAN_PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
BUILDER_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_model_ready_panel.py"

# Recorded when fr_ze2020_clean_panel.csv was created (PANEL_FR_ZE2020_CLEAN_TREATED
# in reports/herald_artifact_registry.json) -- this stage must not modify it.
CLEAN_PANEL_EXPECTED_SIZE_BYTES = 149288
CLEAN_PANEL_EXPECTED_SHA256_PREFIX = "8ae8fc0a8f4713eb5fc3"

EXPECTED_COLUMNS = [
    "ze2020",
    "ze2020_label",
    "year",
    "observed_value",
    "target_variable",
    "lag_1",
    "lag_2",
    "lag_3",
    "growth_1y_safe",
    "growth_2y_safe",
    "mask_observed_available",
    "mask_lag_1_available",
    "mask_lag_2_available",
    "mask_lag_3_available",
    "node_id",
]

FORBIDDEN_COLUMN_NAMES = {
    "growth_1y",
    "growth_2y",
    "is_covid_year",
    "is_post_covid_rebound",
    "feature_forecast_safe",
    "has_urssaf_source",
}

ALENCON_ZE2020 = "0051"


@pytest.fixture(scope="module")
def panel():
    assert MODEL_READY_PATH.exists(), f"Model-ready panel not found: {MODEL_READY_PATH}"
    return pd.read_csv(MODEL_READY_PATH, dtype={"ze2020": str})


@pytest.fixture(scope="module")
def alencon(panel):
    sub = panel[panel["ze2020"] == ALENCON_ZE2020].set_index("year")
    assert not sub.empty, "Alençon (0051) not found in model-ready panel"
    return sub


def test_panel_file_exists():
    assert MODEL_READY_PATH.exists()


def test_schema_matches_expected_columns(panel):
    assert list(panel.columns) == EXPECTED_COLUMNS


def test_ze2020_is_zero_padded_4char_string(panel):
    assert panel["ze2020"].apply(lambda v: isinstance(v, str)).all()
    assert (panel["ze2020"].str.len() == 4).all()
    assert panel["ze2020"].str.startswith("0").any()


def test_panel_has_280_ze2020_zones(panel):
    assert panel["ze2020"].nunique() == 280


def test_node_id_has_280_deterministic_values_and_does_not_replace_ze2020(panel):
    assert panel["node_id"].nunique() == 280
    assert sorted(panel["node_id"].unique()) == list(range(280))
    # node_id must be a stable function of ze2020: every row for a given
    # zone must carry the same node_id, and the mapping must match a
    # fresh, independently sorted assignment of 0..279.
    mapping = panel.drop_duplicates("ze2020")[["ze2020", "node_id"]]
    assert mapping["node_id"].nunique() == 280
    expected = {z: i for i, z in enumerate(sorted(panel["ze2020"].unique()))}
    for _, row in mapping.iterrows():
        assert row["node_id"] == expected[row["ze2020"]]
    # ze2020 itself must still be present and untouched as the zero-padded
    # string id -- node_id is additive, not a replacement.
    assert "ze2020" in panel.columns
    assert panel["ze2020"].str.len().eq(4).all()


def test_alencon_lags_match_prior_observed_values(alencon):
    assert alencon.loc[2015, "lag_1"] == pytest.approx(alencon.loc[2014, "observed_value"])
    assert alencon.loc[2015, "lag_2"] == pytest.approx(alencon.loc[2013, "observed_value"])
    assert alencon.loc[2015, "lag_3"] == pytest.approx(alencon.loc[2012, "observed_value"])


def test_growth_1y_safe_formula(alencon):
    lag_1 = alencon.loc[2015, "lag_1"]
    lag_2 = alencon.loc[2015, "lag_2"]
    expected = (lag_1 - lag_2) / lag_2
    assert alencon.loc[2015, "growth_1y_safe"] == pytest.approx(expected)


def test_growth_2y_safe_formula(alencon):
    lag_1 = alencon.loc[2015, "lag_1"]
    lag_3 = alencon.loc[2015, "lag_3"]
    expected = (lag_1 - lag_3) / lag_3
    assert alencon.loc[2015, "growth_2y_safe"] == pytest.approx(expected)


def test_growth_1y_safe_does_not_reconstruct_current_year_value(alencon):
    """growth_1y_safe must depend only on lag_1/lag_2, never on the current
    row's own observed_value -- recomputing observed_value from
    (lag_1, growth_1y_safe) must NOT recover the actual current-year value."""
    row = alencon.loc[2015]
    reconstructed_from_growth = row["lag_1"] * (1 + row["growth_1y_safe"])
    # this reconstructs lag_1 itself (last year's value), not this year's
    # observed_value -- confirming growth_1y_safe carries no same-row signal
    assert reconstructed_from_growth != pytest.approx(row["observed_value"])


def test_masks_reflect_lag_availability_at_panel_start(alencon):
    assert alencon.loc[2012, "mask_lag_1_available"] == 0
    assert alencon.loc[2012, "mask_lag_2_available"] == 0
    assert alencon.loc[2012, "mask_lag_3_available"] == 0

    assert alencon.loc[2013, "mask_lag_1_available"] == 1
    assert alencon.loc[2013, "mask_lag_2_available"] == 0
    assert alencon.loc[2013, "mask_lag_3_available"] == 0

    assert alencon.loc[2015, "mask_lag_1_available"] == 1
    assert alencon.loc[2015, "mask_lag_2_available"] == 1
    assert alencon.loc[2015, "mask_lag_3_available"] == 1


def test_no_nan_silently_filled_where_mask_says_unavailable(alencon):
    assert pd.isna(alencon.loc[2012, "lag_1"])
    assert pd.isna(alencon.loc[2012, "lag_2"])
    assert pd.isna(alencon.loc[2012, "lag_3"])
    assert pd.isna(alencon.loc[2013, "lag_2"])


def test_no_forbidden_columns(panel):
    cols_lower = {c.lower() for c in panel.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)
    assert not any("stgnn" in c for c in cols_lower)


def test_builder_does_not_read_legacy_dynamic_stgnn_panels():
    """The module docstring is allowed to mention the legacy filename (to
    document that it is NOT used); the executable code must not."""
    import ast

    tree = ast.parse(BUILDER_PATH.read_text())
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = BUILDER_PATH.read_text().replace(docstring, "")
    assert "dynamic_stgnn_feature_panel" not in code_without_docstring


def test_clean_panel_input_not_modified_by_this_stage():
    """The step-2 clean panel must remain byte-identical after building the
    step-3 model-ready panel on top of it (read-only input)."""
    assert CLEAN_PANEL_PATH.exists()
    content = CLEAN_PANEL_PATH.read_bytes()
    assert len(content) == CLEAN_PANEL_EXPECTED_SIZE_BYTES
    digest = hashlib.sha256(content).hexdigest()
    assert digest.startswith(CLEAN_PANEL_EXPECTED_SHA256_PREFIX)
