"""
Consistency tests for the FR ZE2020 sector relational features (MVP2
Category C, step 2). Generator:
src/data/france_ze2020/build_fr_ze2020_sector_relational_features.py.
Input: data/processed/france_ze2020/fr_ze2020_sector_panel.csv (must remain
untouched by this stage).
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_sector_panel import (
    OUT_PATH as SECTOR_PANEL_PATH,
)
from src.data.france_ze2020.build_fr_ze2020_sector_relational_features import (
    OUT_PATH,
    build_sector_relational_features,
    load_sector_panel,
)

REPO_ROOT = Path(__file__).parent.parent
BUILDER_PATH = (
    REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_sector_relational_features.py"
)

EXPECTED_COLUMNS = [
    "ze2020",
    "year",
    "sector_code",
    "sector_share_lag_1",
    "mask_sector_share_lag_1_available",
    "sector_growth_lag_1",
    "mask_sector_growth_lag_1_available",
    "sector_growth_lag_2",
    "mask_sector_growth_lag_2_available",
    "dominant_sector_lag_1",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "mask_ze_sector_distribution_lag_1_available",
    "national_sector_share_lag_1",
    "mask_national_sector_share_lag_1_available",
    "national_sector_growth_lag_1",
    "mask_national_sector_growth_lag_1_available",
]

FORBIDDEN_COLUMN_NAMES = {
    "growth_1y",
    "growth_2y",
    "is_covid_year",
    "is_post_covid_rebound",
    "feature_forecast_safe",
    "has_urssaf_source",
    "services_share_lag_1",
}

ALENCON_ZE2020 = "0051"


@pytest.fixture(scope="module")
def features():
    assert OUT_PATH.exists(), f"Sector relational features not found: {OUT_PATH}"
    return pd.read_csv(OUT_PATH, dtype={"ze2020": str})


def test_file_exists():
    assert OUT_PATH.exists()


def test_schema_matches_expected_columns(features):
    assert list(features.columns) == EXPECTED_COLUMNS


def test_no_forbidden_columns(features):
    cols_lower = {c.lower() for c in features.columns}
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
    assert "side_creations_a10_ze2020" not in code_without_docstring  # reads the audited panel, not the raw source


def test_row_count_matches_280_zones_13_years_9_sectors(features):
    assert len(features) == 280 * 14 * 9


def test_sector_growth_lag_1_unavailable_before_2014(features):
    early = features[features["year"].isin([2012, 2013])]
    assert (early["mask_sector_growth_lag_1_available"] == 0).all()
    assert early["sector_growth_lag_1"].isna().all()

    later = features[features["year"] >= 2014]
    assert (later["mask_sector_growth_lag_1_available"] == 1).all()
    assert later["sector_growth_lag_1"].notna().all()


def test_sector_growth_lag_2_unavailable_before_2015(features):
    early = features[features["year"].isin([2012, 2013, 2014])]
    assert (early["mask_sector_growth_lag_2_available"] == 0).all()

    later = features[features["year"] >= 2015]
    assert (later["mask_sector_growth_lag_2_available"] == 1).all()


def test_ze_sector_distribution_unavailable_only_in_2012(features):
    year_2012 = features[features["year"] == 2012]
    assert (year_2012["mask_ze_sector_distribution_lag_1_available"] == 0).all()
    assert year_2012["dominant_sector_lag_1"].isna().all()

    later = features[features["year"] >= 2013]
    assert (later["mask_ze_sector_distribution_lag_1_available"] == 1).all()
    assert later["dominant_sector_lag_1"].notna().all()


def test_national_sector_growth_unavailable_before_2014(features):
    early = features[features["year"].isin([2012, 2013])]
    assert (early["mask_national_sector_growth_lag_1_available"] == 0).all()

    later = features[features["year"] >= 2014]
    assert (later["mask_national_sector_growth_lag_1_available"] == 1).all()


def test_alencon_2014_lag_features_match_manual_calculation(features):
    """sector_growth_lag_1 at year=2014 must equal the growth between the
    sector's own observed values at 2012 and 2013 -- a manual cross-check
    against the underlying sector panel."""
    sector_panel = load_sector_panel()
    alencon = sector_panel[
        (sector_panel["ze2020"] == ALENCON_ZE2020) & (sector_panel["sector_code"] == "GI")
    ].set_index("year")

    row = features[
        (features["ze2020"] == ALENCON_ZE2020)
        & (features["sector_code"] == "GI")
        & (features["year"] == 2014)
    ].iloc[0]

    expected_growth = (
        alencon.loc[2013, "sector_establishment_creations"]
        - alencon.loc[2012, "sector_establishment_creations"]
    ) / alencon.loc[2012, "sector_establishment_creations"]
    assert row["sector_growth_lag_1"] == pytest.approx(expected_growth)
    assert row["sector_share_lag_1"] == pytest.approx(alencon.loc[2013, "sector_share"])


def test_dominant_sector_lag_1_matches_max_share_of_prior_year(features):
    sector_panel = load_sector_panel()
    prior_year_top = (
        sector_panel[sector_panel["year"] == 2013]
        .sort_values("sector_share", ascending=False)
        .groupby("ze2020")
        .first()["sector_code"]
    )

    rows_2014 = features[features["year"] == 2014].drop_duplicates("ze2020").set_index("ze2020")
    for ze2020, expected_sector in prior_year_top.items():
        assert rows_2014.loc[ze2020, "dominant_sector_lag_1"] == expected_sector


def test_national_sector_share_sums_to_one_per_year(features):
    """national_sector_share_lag_1, summed across the 9 sectors for a given
    target year, must equal 1 (it's a share of one prior year's national
    total, the same prior year for every sector)."""
    year_2015 = features[features["year"] == 2015].drop_duplicates("sector_code")
    assert year_2015["national_sector_share_lag_1"].sum() == pytest.approx(1.0)


def test_no_relational_feature_uses_the_target_years_own_data():
    """Truncating the input to years <= eval_year must produce IDENTICAL
    features at eval_year as building from the full sector panel."""
    panel = load_sector_panel()
    eval_year = 2020

    full_built = build_sector_relational_features(panel)
    truncated_built = build_sector_relational_features(panel[panel["year"] <= eval_year])

    full_at_t = (
        full_built[full_built["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    )
    trunc_at_t = (
        truncated_built[truncated_built["year"] == eval_year]
        .set_index(["ze2020", "sector_code"])
        .sort_index()
    )

    for col in EXPECTED_COLUMNS:
        if col in ("ze2020", "year", "sector_code"):
            continue
        if full_at_t[col].dtype == object:
            assert (full_at_t[col].fillna("NA") == trunc_at_t[col].fillna("NA")).all()
        else:
            pd.testing.assert_series_equal(full_at_t[col], trunc_at_t[col], check_names=False)


def test_mutating_current_year_values_does_not_change_its_own_lag_features():
    panel = load_sector_panel()
    eval_year = 2020

    baseline = build_sector_relational_features(panel)
    mutated_input = panel.copy()
    mutated_input.loc[
        mutated_input["year"] == eval_year, "sector_establishment_creations"
    ] = 999999.0
    mutated_input.loc[mutated_input["year"] == eval_year, "sector_share"] = 0.99

    mutated = build_sector_relational_features(mutated_input)

    baseline_at_t = (
        baseline[baseline["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    )
    mutated_at_t = (
        mutated[mutated["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    )

    for col in EXPECTED_COLUMNS:
        if col in ("ze2020", "year", "sector_code"):
            continue
        if baseline_at_t[col].dtype == object:
            assert (baseline_at_t[col].fillna("NA") == mutated_at_t[col].fillna("NA")).all()
        else:
            pd.testing.assert_series_equal(baseline_at_t[col], mutated_at_t[col], check_names=False)


def test_sector_panel_input_not_modified_by_this_stage():
    assert SECTOR_PANEL_PATH.exists()
    before = load_sector_panel()
    build_sector_relational_features()
    after = load_sector_panel()
    pd.testing.assert_frame_equal(before, after)
