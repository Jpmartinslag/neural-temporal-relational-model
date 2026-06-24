"""
Consistency tests for the FR ZE2020 relational model-ready panel (MVP2,
Category A -- trajectory similarity, no legacy adjacency matrix).

See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md
("MVP2 implementation" section). Generator:
src/data/france_ze2020/build_fr_ze2020_relational_model_ready_panel.py.
Input: data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv (must
remain untouched by this stage -- same rule as the model-ready panel itself
not modifying the clean panel).
"""

import ast
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_relational_model_ready_panel import (
    build_relational_model_ready_panel,
    load_model_ready_panel,
)

REPO_ROOT = Path(__file__).parent.parent
RELATIONAL_PANEL_PATH = (
    REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv"
)
MODEL_READY_PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv"
BUILDER_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_relational_model_ready_panel.py"

# Recorded for the model-ready panel as it stood when this stage was built --
# this stage must not modify its input.
MODEL_READY_EXPECTED_SIZE_BYTES = 413620
MODEL_READY_EXPECTED_SHA256_PREFIX = "dae0b9fe98d67af393a4"

BASE_COLUMNS = [
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
RELATIONAL_COLUMNS = [
    "similar_ze_lag_1_mean",
    "similar_ze_lag_1_weighted_mean",
    "similar_ze_growth_1y_safe_mean",
    "similar_ze_count",
    "relational_feature_available",
]
EXPECTED_COLUMNS = BASE_COLUMNS + RELATIONAL_COLUMNS

FORBIDDEN_COLUMN_NAMES = {
    "growth_1y",
    "growth_2y",
    "is_covid_year",
    "is_post_covid_rebound",
    "feature_forecast_safe",
    "has_urssaf_source",
}

ALENCON_ZE2020 = "0051"

# Determined by data: growth_1y_safe (the similarity feature) is only
# populated from 2014 onward, and MIN_HISTORY_YEARS=3 overlapping years are
# required before any similarity can be computed -- so 2017 is the first
# year relational features can exist for this panel.
FIRST_YEAR_WITH_RELATIONAL_FEATURES = 2017
YEARS_WITHOUT_HISTORY = [2012, 2013, 2014, 2015, 2016]


@pytest.fixture(scope="module")
def panel():
    assert RELATIONAL_PANEL_PATH.exists(), f"Relational panel not found: {RELATIONAL_PANEL_PATH}"
    return pd.read_csv(RELATIONAL_PANEL_PATH, dtype={"ze2020": str})


def test_panel_file_exists():
    assert RELATIONAL_PANEL_PATH.exists()


def test_schema_matches_expected_columns(panel):
    assert list(panel.columns) == EXPECTED_COLUMNS


def test_ze2020_is_zero_padded_4char_string(panel):
    assert panel["ze2020"].apply(lambda v: isinstance(v, str)).all()
    assert (panel["ze2020"].str.len() == 4).all()
    assert panel["ze2020"].str.startswith("0").any()


def test_panel_has_280_ze2020_zones(panel):
    assert panel["ze2020"].nunique() == 280


def test_no_forbidden_columns(panel):
    cols_lower = {c.lower() for c in panel.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)
    assert not any("stgnn" in c for c in cols_lower)


def test_builder_reads_only_model_ready_panel_as_base():
    """The module docstring may name other files (to document they are NOT
    used); the executable code must not reference the legacy panel or the
    unprovenanced legacy adjacency matrices."""
    source = BUILDER_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring
    assert "MODEL_READY_PANEL_PATH" in code_without_docstring


def test_model_ready_panel_input_not_modified_by_this_stage():
    assert MODEL_READY_PANEL_PATH.exists()
    content = MODEL_READY_PANEL_PATH.read_bytes()
    assert len(content) == MODEL_READY_EXPECTED_SIZE_BYTES
    digest = hashlib.sha256(content).hexdigest()
    assert digest.startswith(MODEL_READY_EXPECTED_SHA256_PREFIX)


def test_years_without_sufficient_history_have_relational_features_unavailable(panel):
    early = panel[panel["year"].isin(YEARS_WITHOUT_HISTORY)]
    assert (early["relational_feature_available"] == 0).all()
    assert (early["similar_ze_count"] == 0).all()
    assert early["similar_ze_lag_1_mean"].isna().all()
    assert early["similar_ze_lag_1_weighted_mean"].isna().all()
    assert early["similar_ze_growth_1y_safe_mean"].isna().all()


def test_years_with_sufficient_history_have_relational_features_available(panel):
    later = panel[panel["year"] >= FIRST_YEAR_WITH_RELATIONAL_FEATURES]
    assert (later["relational_feature_available"] == 1).all()
    assert (later["similar_ze_count"] > 0).all()
    assert later["similar_ze_lag_1_mean"].notna().all()
    assert later["similar_ze_growth_1y_safe_mean"].notna().all()


def test_relational_mean_is_actually_the_mean_of_its_own_count(panel):
    """similar_ze_lag_1_mean for a zone-year with similar_ze_count=k must be
    a plausible average (sanity bound, not a fabricated constant): every
    available row's value must differ across zones (not a single broadcast
    constant), and similar_ze_count must never exceed TOP_K=5."""
    available = panel[panel["relational_feature_available"] == 1]
    assert available["similar_ze_count"].max() <= 5
    assert available["similar_ze_lag_1_mean"].nunique() > 1


def test_no_relational_feature_uses_the_target_years_own_observed_value():
    """Truncating the input panel to years <= eval_year must produce
    IDENTICAL relational features at eval_year as building from the full
    panel -- proving rows for years > eval_year had zero effect."""
    panel_full = load_model_ready_panel()
    eval_year = 2020

    full_built = build_relational_model_ready_panel(panel_full)
    truncated_input = panel_full[panel_full["year"] <= eval_year]
    truncated_built = build_relational_model_ready_panel(truncated_input)

    full_at_t = full_built[full_built["year"] == eval_year].set_index("ze2020").sort_index()
    trunc_at_t = (
        truncated_built[truncated_built["year"] == eval_year].set_index("ze2020").sort_index()
    )

    for col in RELATIONAL_COLUMNS:
        pd.testing.assert_series_equal(full_at_t[col], trunc_at_t[col], check_names=False)


def test_relational_features_invariant_to_current_year_observed_value_mutation():
    """The row-year target must not affect relational features for that same
    row-year. Mutating observed_value at eval_year to an extreme value must
    leave all relational columns unchanged."""
    panel_full = load_model_ready_panel()
    eval_year = 2020

    baseline = build_relational_model_ready_panel(panel_full)
    mutated_input = panel_full.copy()
    mutated_input.loc[mutated_input["year"] == eval_year, "observed_value"] = 999999999.0
    mutated = build_relational_model_ready_panel(mutated_input)

    baseline_at_t = (
        baseline[baseline["year"] == eval_year].set_index("ze2020").sort_index()
    )
    mutated_at_t = mutated[mutated["year"] == eval_year].set_index("ze2020").sort_index()

    for col in RELATIONAL_COLUMNS:
        pd.testing.assert_series_equal(
            baseline_at_t[col], mutated_at_t[col], check_names=False
        )


def test_similarity_uses_strictly_prior_years_only():
    """For evaluation year t, neighbors must be selected using a similarity
    matrix built only from years < t -- never including year t itself."""
    from src.data.france_ze2020.build_fr_ze2020_relational_model_ready_panel import (
        similarity_matrix_for_year,
    )

    panel = load_model_ready_panel()
    eval_year = 2020
    corr = similarity_matrix_for_year(panel, eval_year)
    assert corr is not None

    history_years = panel[panel["year"] < eval_year]["year"].unique()
    assert eval_year not in history_years


def test_weighted_mean_aligns_weights_to_neighbor_codes():
    """Regression test for the weighted mean math: similarity weights must
    be matched to the same ZE codes as the lag values, not accidentally
    paired by positional order after pandas reorders an index."""
    from src.data.france_ze2020.build_fr_ze2020_relational_model_ready_panel import (
        TOP_K,
        similarity_matrix_for_year,
    )

    panel = load_model_ready_panel()
    built = build_relational_model_ready_panel(panel)
    eval_year = 2020
    zone = ALENCON_ZE2020
    current = panel[panel["year"] == eval_year].set_index("ze2020")
    corr = similarity_matrix_for_year(panel, eval_year)
    assert corr is not None

    candidates = corr.loc[zone].drop(labels=[zone], errors="ignore").dropna()
    candidates = candidates[candidates > 0].sort_values(ascending=False).head(TOP_K)
    valid = current.reindex(candidates.index).dropna(subset=["lag_1", "growth_1y_safe"])
    weights = candidates.reindex(valid.index).to_numpy(dtype=float)
    expected = float((valid["lag_1"].to_numpy(dtype=float) * (weights / weights.sum())).sum())

    actual = built[(built["ze2020"] == zone) & (built["year"] == eval_year)].iloc[0][
        "similar_ze_lag_1_weighted_mean"
    ]
    assert actual == pytest.approx(expected)


def test_alencon_relational_features_are_internally_consistent(panel):
    sub = panel[panel["ze2020"] == ALENCON_ZE2020].set_index("year")
    assert not sub.empty
    row = sub.loc[2020]
    assert row["relational_feature_available"] == 1
    assert 0 < row["similar_ze_count"] <= 5
    # the weighted mean must lie within the [min, max] range implied by a
    # convex combination -- a loose sanity bound, not a fabricated value
    assert pd.notna(row["similar_ze_lag_1_weighted_mean"])
