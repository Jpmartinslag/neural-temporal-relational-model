"""Tests for the France ZE2020 relational availability mask (HERALD_57, DEC-082).

The mask exists to make relational absence explicit, because absence in this
project is expressed as a missing row rather than a flag. These tests therefore
concentrate on the failure modes that motivated it: an unclassified cell, an
"available" cell that is silently empty, a computed relation mislabelled as
observed, and a canonical input mutated by the build.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_relation_availability_mask import (  # noqa: E402
    COMMUTING_EXPECTED_MODE,
    COMMUTING_FAMILY,
    COMMUTING_FIRST_AVAILABLE_YEAR,
    COMMUTING_UNRELEASED_THROUGH_YEAR,
    DERIVED_FAMILIES,
    DERIVED_FIRST_YEAR,
    NOT_CONSTRUCTED_FAMILIES,
    OUTPUT_COLUMNS,
    PANEL_YEARS,
    REASON_INSUFFICIENT_HISTORY,
    REASON_NOT_CONSTRUCTED,
    REASON_NOT_RELEASED,
    STATUS_CARRIED_FORWARD,
    STATUS_DERIVED,
    STATUS_OBSERVED,
    STATUS_UNAVAILABLE,
    VALID_REASONS,
    VALID_STATUSES,
    DERIVED_LAST_YEAR,
    REQUIRED_COMMUTING_COLUMNS,
    REQUIRED_SIGNAL_COLUMNS,
    build_mask,
    require_columns,
    sha256,
    validate_commuting_input,
    validate_mask,
    validate_signal_input,
)

MASK_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_relation_availability_mask.csv"
SUMMARY_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_relation_availability_mask_summary.json"
)
SIGNALS_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_temporal_relation_signals.csv.gz"
COMMUTING_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_commuting_strict_ex_ante_edges.csv.gz"
)
SECTOR_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"

ALL_FAMILIES = tuple(DERIVED_FAMILIES) + (COMMUTING_FAMILY,) + tuple(NOT_CONSTRUCTED_FAMILIES)


@pytest.fixture(scope="module")
def mask() -> pd.DataFrame:
    return build_mask()


@pytest.fixture(scope="module")
def written_mask() -> pd.DataFrame:
    if not MASK_PATH.exists():
        pytest.skip("mask artifact not generated; run the builder first")
    # keep_default_na=False: the mask deliberately writes empty strings for
    # inapplicable fields, and pandas would otherwise read them back as NaN,
    # making a blank indistinguishable from missing data.
    return pd.read_csv(MASK_PATH, keep_default_na=False, dtype=str)


# --- completeness: no cell may be missing or unclassified ------------------


def test_every_family_year_cell_exists(mask: pd.DataFrame) -> None:
    assert len(mask) == len(ALL_FAMILIES) * len(PANEL_YEARS)
    for family in ALL_FAMILIES:
        years = sorted(mask.loc[mask["relation_family"] == family, "decision_year"])
        assert years == list(PANEL_YEARS), family


def test_no_duplicate_cells(mask: pd.DataFrame) -> None:
    assert not mask.duplicated(["relation_family", "decision_year"]).any()


def test_no_unclassified_cell(mask: pd.DataFrame) -> None:
    assert mask["availability_status"].notna().all()
    assert (mask["availability_status"].astype(str).str.len() > 0).all()
    assert mask["availability_status"].isin(VALID_STATUSES).all()


def test_schema_is_the_agreed_schema(mask: pd.DataFrame) -> None:
    assert list(mask.columns) == OUTPUT_COLUMNS


# --- vocabulary discipline -------------------------------------------------


def test_computed_relations_are_never_called_observed(mask: pd.DataFrame) -> None:
    derived = mask[mask["relation_family"].isin(DERIVED_FAMILIES)]
    assert (derived["availability_status"] != STATUS_OBSERVED).all()
    available = derived[derived["availability_status"] != STATUS_UNAVAILABLE]
    assert (available["availability_status"] == STATUS_DERIVED).all()


def test_commuting_is_carried_forward_not_observed(mask: pd.DataFrame) -> None:
    rows = mask[mask["relation_family"] == COMMUTING_FAMILY]
    available = rows[rows["availability_status"] != STATUS_UNAVAILABLE]
    assert (available["availability_status"] == STATUS_CARRIED_FORWARD).all()
    assert (available["snapshot_age_years"].astype(int) > 0).all()


def test_unavailable_rows_carry_a_valid_reason(mask: pd.DataFrame) -> None:
    unavailable = mask[mask["availability_status"] == STATUS_UNAVAILABLE]
    assert not unavailable.empty
    assert unavailable["unavailable_reason"].isin(VALID_REASONS).all()


def test_available_rows_carry_no_reason(mask: pd.DataFrame) -> None:
    available = mask[mask["availability_status"] != STATUS_UNAVAILABLE]
    assert (available["unavailable_reason"].fillna("").astype(str) == "").all()


# --- the two gaps this artifact exists to expose ---------------------------


def test_commuting_2012_2015_is_explicitly_unavailable(mask: pd.DataFrame) -> None:
    rows = mask[(mask["relation_family"] == COMMUTING_FAMILY) & (mask["decision_year"] <= 2015)]
    assert len(rows) == 4
    assert (rows["availability_status"] == STATUS_UNAVAILABLE).all()
    assert (rows["unavailable_reason"] == REASON_NOT_RELEASED).all()


def test_signal_families_2012_2016_are_explicitly_unavailable(mask: pd.DataFrame) -> None:
    for family in DERIVED_FAMILIES:
        rows = mask[
            (mask["relation_family"] == family) & (mask["decision_year"] < DERIVED_FIRST_YEAR)
        ]
        assert len(rows) == 5, family
        assert (rows["availability_status"] == STATUS_UNAVAILABLE).all(), family
        assert (rows["unavailable_reason"] == REASON_INSUFFICIENT_HISTORY).all(), family


def test_insufficient_history_reason_states_the_mechanism(mask: pd.DataFrame) -> None:
    """The reason must be traceable to the builder rule, not asserted."""
    rows = mask[mask["unavailable_reason"] == REASON_INSUFFICIENT_HISTORY]
    provenance = rows["provenance"].astype(str)
    assert provenance.str.contains("2014").all()
    assert provenance.str.contains("min_periods=3").all()
    assert provenance.str.contains("2017").all()


def test_planned_but_unbuilt_families_are_recorded(mask: pd.DataFrame) -> None:
    for family in NOT_CONSTRUCTED_FAMILIES:
        rows = mask[mask["relation_family"] == family]
        assert len(rows) == len(PANEL_YEARS), family
        assert (rows["availability_status"] == STATUS_UNAVAILABLE).all(), family
        assert (rows["unavailable_reason"] == REASON_NOT_CONSTRUCTED).all(), family


# --- availability must not be confused with emptiness ---------------------


def test_available_years_actually_contain_edges(mask: pd.DataFrame) -> None:
    available = mask[mask["availability_status"] != STATUS_UNAVAILABLE]
    assert (available["actual_edge_count"] > 0).all()


def test_silent_emptiness_fails_validation(mask: pd.DataFrame) -> None:
    """An available cell with zero edges is the exact confusion the mask
    removes, so validation must reject it rather than emit it."""
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_DERIVED][0]
    broken.loc[target, "actual_edge_count"] = 0
    with pytest.raises(AssertionError, match="zero edges"):
        validate_mask(broken)


def test_missing_classification_fails_validation(mask: pd.DataFrame) -> None:
    broken = mask.drop(index=mask.index[0])
    with pytest.raises(AssertionError):
        validate_mask(broken)


def test_unavailable_without_reason_fails_validation(mask: pd.DataFrame) -> None:
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_UNAVAILABLE][0]
    broken.loc[target, "unavailable_reason"] = ""
    with pytest.raises(AssertionError, match="valid reason"):
        validate_mask(broken)


def test_structural_expectation_holds_where_documented(mask: pd.DataFrame) -> None:
    checked = mask[
        mask["expected_edge_count"].notna()
        & (mask["availability_status"] != STATUS_UNAVAILABLE)
    ]
    assert not checked.empty
    assert (
        checked["expected_edge_count"].astype(int) == checked["actual_edge_count"].astype(int)
    ).all()


# --- canonical inputs are read-only --------------------------------------


def test_build_does_not_modify_canonical_inputs() -> None:
    paths = [SIGNALS_PATH, COMMUTING_PATH, SECTOR_PANEL_PATH]
    before = {path: sha256(path) for path in paths}
    build_mask()
    after = {path: sha256(path) for path in paths}
    assert before == after


def test_builder_is_deterministic(tmp_path: Path) -> None:
    script = ROOT / "src/data/france_ze2020/build_fr_ze2020_relation_availability_mask.py"
    first = tmp_path / "run1"
    second = tmp_path / "run2"
    for out in (first, second):
        result = subprocess.run(
            [sys.executable, str(script), "--output-dir", str(out)],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
    name = "fr_ze2020_relation_availability_mask.csv"
    assert sha256(first / name) == sha256(second / name)


# --- the committed artifact matches the builder ---------------------------


def test_written_artifact_matches_builder(written_mask: pd.DataFrame, mask: pd.DataFrame) -> None:
    def as_text(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.reset_index(drop=True).copy()
        for column in OUTPUT_COLUMNS:
            values = out[column]
            if pd.api.types.is_numeric_dtype(values):
                # Integer-valued counts must not compare as "12600.0" vs "12600".
                values = values.map(
                    lambda value: "" if pd.isna(value) else str(int(value))
                )
            out[column] = values.fillna("").astype(str)
        return out[OUTPUT_COLUMNS]

    pd.testing.assert_frame_equal(as_text(written_mask), as_text(mask))


# --- mutation tests: the builder must not invent a reason ------------------


@pytest.fixture(scope="module")
def commuting_input() -> pd.DataFrame:
    return pd.read_csv(COMMUTING_PATH, dtype={"source_release_date": str})


@pytest.fixture(scope="module")
def signals_input() -> pd.DataFrame:
    return pd.read_csv(SIGNALS_PATH)


def test_truncated_commuting_year_is_not_relabelled_as_unreleased(
    commuting_input: pd.DataFrame, tmp_path: Path
) -> None:
    """A year lost to truncation must fail, not acquire a release excuse.

    Without this guard the builder would state that the source had not been
    published, which is a falsehood about INSEE rather than a missing row.
    """
    truncated = commuting_input[commuting_input["decision_year"] != 2025]
    with pytest.raises(AssertionError, match="truncation or corruption"):
        validate_commuting_input(truncated)

    path = tmp_path / "truncated.csv.gz"
    truncated.to_csv(path, index=False)
    with pytest.raises(AssertionError, match="truncation or corruption"):
        build_mask(commuting_path=path)


def test_commuting_row_before_release_is_rejected(
    commuting_input: pd.DataFrame,
) -> None:
    """A row dated before any snapshot existed contradicts the release rule."""
    impossible = commuting_input.copy()
    impossible.loc[impossible.index[0], "decision_year"] = COMMUTING_UNRELEASED_THROUGH_YEAR
    with pytest.raises(AssertionError, match="no snapshot had been released"):
        validate_commuting_input(impossible)


def test_unknown_signal_family_fails_instead_of_being_dropped(
    signals_input: pd.DataFrame, tmp_path: Path
) -> None:
    """A family the builder does not iterate would vanish from the mask."""
    drifted = signals_input.copy()
    drifted.loc[drifted.index[0], "relation_family"] = "brand_new_family"
    with pytest.raises(AssertionError, match="absent from DERIVED_FAMILIES"):
        validate_signal_input(drifted)

    path = tmp_path / "drifted.csv.gz"
    drifted.to_csv(path, index=False)
    with pytest.raises(AssertionError, match="absent from DERIVED_FAMILIES"):
        build_mask(signals_path=path)


def test_missing_signal_family_fails(signals_input: pd.DataFrame) -> None:
    reduced = signals_input[signals_input["relation_family"] != "intra_ze_sector"]
    with pytest.raises(AssertionError, match="missing expected families"):
        validate_signal_input(reduced)


def test_mixed_commuting_metadata_in_one_year_fails(
    commuting_input: pd.DataFrame, tmp_path: Path
) -> None:
    """`first` would silently pick one snapshot out of mixed metadata."""
    mixed = commuting_input.copy()
    target = mixed.index[mixed["decision_year"] == 2020][0]
    mixed.loc[target, "observation_year"] = 2017
    with pytest.raises(AssertionError, match="not unique per decision year"):
        validate_commuting_input(mixed)

    path = tmp_path / "mixed.csv.gz"
    mixed.to_csv(path, index=False)
    with pytest.raises(AssertionError, match="not unique per decision year"):
        build_mask(commuting_path=path)


def test_mixed_release_date_in_one_year_fails(commuting_input: pd.DataFrame) -> None:
    mixed = commuting_input.copy()
    target = mixed.index[mixed["decision_year"] == 2018][0]
    mixed.loc[target, "source_release_date"] = "2099-01-01"
    with pytest.raises(AssertionError, match="not unique per decision year"):
        validate_commuting_input(mixed)


def test_unavailable_commuting_row_is_rejected(commuting_input: pd.DataFrame) -> None:
    flagged = commuting_input.copy()
    flagged.loc[flagged.index[0], "data_available"] = 0
    with pytest.raises(AssertionError, match="data_available"):
        validate_commuting_input(flagged)


def test_unexpected_availability_mode_is_rejected(commuting_input: pd.DataFrame) -> None:
    altered = commuting_input.copy()
    altered.loc[altered.index[0], "availability_mode"] = "something_else"
    with pytest.raises(AssertionError, match="availability_mode"):
        validate_commuting_input(altered)


def test_extra_commuting_year_fails(commuting_input: pd.DataFrame) -> None:
    extra = commuting_input.copy()
    extra.loc[extra.index[0], "decision_year"] = DERIVED_LAST_YEAR + 1
    with pytest.raises(AssertionError, match="outside"):
        validate_commuting_input(extra)


def test_partially_null_commuting_metadata_fails(commuting_input: pd.DataFrame) -> None:
    """A single NaN inside an otherwise uniform year must not pass as uniform."""
    holed = commuting_input.copy()
    target = holed.index[holed["decision_year"] == 2019][0]
    holed.loc[target, "observation_year"] = None
    with pytest.raises(AssertionError, match="null values"):
        validate_commuting_input(holed)


def test_blank_commuting_metadata_fails(commuting_input: pd.DataFrame) -> None:
    blanked = commuting_input.copy()
    target = blanked.index[blanked["decision_year"] == 2019][0]
    blanked.loc[target, "source_release_date"] = "   "
    with pytest.raises(AssertionError, match="empty or whitespace-only"):
        validate_commuting_input(blanked)


def test_wrong_snapshot_age_fails(commuting_input: pd.DataFrame) -> None:
    """The recorded age must not contradict the recorded snapshot."""
    wrong = commuting_input.copy()
    wrong["snapshot_age_years"] = wrong["snapshot_age_years"] + 1
    with pytest.raises(AssertionError, match="does not equal decision_year"):
        validate_commuting_input(wrong)


def test_release_after_decision_year_fails(commuting_input: pd.DataFrame) -> None:
    """A snapshot released after the decision could not have been used ex ante."""
    late = commuting_input.copy()
    late["source_release_date"] = "2099-01-01"
    with pytest.raises(AssertionError, match="at or after their own"):
        validate_commuting_input(late)


def test_duplicate_commuting_key_fails(commuting_input: pd.DataFrame) -> None:
    duplicated = pd.concat([commuting_input, commuting_input.iloc[[0]]], ignore_index=True)
    with pytest.raises(AssertionError, match="duplicate edge_id"):
        validate_commuting_input(duplicated)


def test_missing_commuting_column_fails(commuting_input: pd.DataFrame) -> None:
    """A missing column must name itself, not surface as a KeyError."""
    stripped = commuting_input.drop(columns=["snapshot_age_years"])
    with pytest.raises(AssertionError, match="missing required columns"):
        validate_commuting_input(stripped)


def test_missing_signal_column_fails(signals_input: pd.DataFrame) -> None:
    stripped = signals_input.drop(columns=["relation_family"])
    with pytest.raises(AssertionError, match="missing required columns"):
        validate_signal_input(stripped)


def test_null_signal_key_field_fails(signals_input: pd.DataFrame) -> None:
    holed = signals_input.copy()
    holed.loc[holed.index[0], "source_node_id"] = None
    with pytest.raises(AssertionError, match="null values"):
        validate_signal_input(holed)


def test_duplicate_signal_key_fails(signals_input: pd.DataFrame) -> None:
    duplicated = pd.concat([signals_input, signals_input.iloc[[0]]], ignore_index=True)
    with pytest.raises(AssertionError, match="duplicate relation_snapshot_id"):
        validate_signal_input(duplicated)


def test_early_derived_year_fails(signals_input: pd.DataFrame) -> None:
    """2016 is impossible under the three-year correlation minimum."""
    early = signals_input.copy()
    early.loc[early.index[0], "decision_year"] = DERIVED_FIRST_YEAR - 1
    with pytest.raises(AssertionError, match="before 2017"):
        validate_signal_input(early)


def test_late_derived_year_fails(signals_input: pd.DataFrame) -> None:
    late = signals_input.copy()
    late.loc[late.index[0], "decision_year"] = DERIVED_LAST_YEAR + 1
    with pytest.raises(AssertionError, match="beyond the panel"):
        validate_signal_input(late)


def test_required_columns_helper_names_the_missing_column() -> None:
    frame = pd.DataFrame({"a": [1]})
    with pytest.raises(AssertionError, match=r"missing required columns: \['b'\]"):
        require_columns(frame, ("a", "b"), "fixture")


def test_unavailable_row_with_edges_fails_validation(mask: pd.DataFrame) -> None:
    """A classification that contradicts its own count must not be emitted."""
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_UNAVAILABLE][0]
    broken.loc[target, "actual_edge_count"] = 7
    with pytest.raises(AssertionError, match="status contradicts the count"):
        validate_mask(broken)


def test_unavailable_row_with_snapshot_fields_fails(mask: pd.DataFrame) -> None:
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_UNAVAILABLE][0]
    broken.loc[target, "source_snapshot_year"] = 2012
    with pytest.raises(AssertionError, match="unavailable row carries"):
        validate_mask(broken)


def test_derived_row_with_snapshot_fields_fails(mask: pd.DataFrame) -> None:
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_DERIVED][0]
    broken.loc[target, "source_snapshot_year"] = 2012
    with pytest.raises(AssertionError, match="derived_available row carries"):
        validate_mask(broken)


def test_carried_forward_without_snapshot_fails(mask: pd.DataFrame) -> None:
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_CARRIED_FORWARD][0]
    broken.loc[target, "source_release_date"] = ""
    with pytest.raises(AssertionError, match="missing source_release_date"):
        validate_mask(broken)


def test_carried_forward_with_zero_age_fails(mask: pd.DataFrame) -> None:
    """Age zero would mean observation at the decision year, a different status."""
    broken = mask.copy()
    target = broken.index[broken["availability_status"] == STATUS_CARRIED_FORWARD][0]
    broken.loc[target, "snapshot_age_years"] = 0
    with pytest.raises(AssertionError, match="age 0"):
        validate_mask(broken)


def test_negative_count_fails_validation(mask: pd.DataFrame) -> None:
    broken = mask.copy()
    broken.loc[broken.index[0], "actual_edge_count"] = -1
    with pytest.raises(AssertionError, match="negative"):
        validate_mask(broken)


def test_real_signal_input_satisfies_its_guards(signals_input: pd.DataFrame) -> None:
    validate_signal_input(signals_input)
    for column in REQUIRED_SIGNAL_COLUMNS:
        assert column in signals_input.columns
    for family in DERIVED_FAMILIES:
        years = sorted(
            int(year)
            for year in signals_input.loc[
                signals_input["relation_family"] == family, "decision_year"
            ].unique()
        )
        assert years == list(range(DERIVED_FIRST_YEAR, DERIVED_LAST_YEAR + 1)), family


def test_real_commuting_input_satisfies_its_guards(commuting_input: pd.DataFrame) -> None:
    for column in REQUIRED_COMMUTING_COLUMNS:
        assert column in commuting_input.columns
    validate_commuting_input(commuting_input)
    years = sorted(int(year) for year in commuting_input["decision_year"].unique())
    assert years == list(range(COMMUTING_FIRST_AVAILABLE_YEAR, max(PANEL_YEARS) + 1))
    assert set(commuting_input["availability_mode"].unique()) == {COMMUTING_EXPECTED_MODE}


# --- part A: the A10 observational mask (HERALD_57 section 1) --------------
#
# Part A needs no builder, but its properties are load-bearing for every later
# stage: the sectoral persistence audit, the forecast-derived states, and the
# dashboard all assume a complete A10 panel. A regression test fixes them so a
# future rebuild cannot quietly introduce a gap.


@pytest.fixture(scope="module")
def sector_panel() -> pd.DataFrame:
    return pd.read_csv(SECTOR_PANEL_PATH, dtype={"ze2020": str})


def test_a10_panel_shape(sector_panel: pd.DataFrame) -> None:
    assert len(sector_panel) == 35_280
    assert sector_panel["ze2020"].nunique() == 280
    assert sector_panel["sector_code"].nunique() == 9
    years = sorted(int(year) for year in sector_panel["year"].unique())
    assert years == list(PANEL_YEARS)
    assert len(sector_panel) == 280 * len(PANEL_YEARS) * 9


def test_a10_panel_has_no_missing_cell(sector_panel: pd.DataFrame) -> None:
    """One row per zone-year-sector, with nothing absent and nothing duplicated."""
    assert not sector_panel.duplicated(["ze2020", "year", "sector_code"]).any()
    assert sector_panel["sector_establishment_creations"].notna().all()


def test_a10_mask_is_integrally_available(sector_panel: pd.DataFrame) -> None:
    assert (sector_panel["mask_sector_available"].astype(int) == 1).all()


def test_a10_has_exactly_one_observed_zero(sector_panel: pd.DataFrame) -> None:
    """The single zero is `5218 / 2016 / JZ`, reconciled against the independent
    official total (DEC-076). A second zero would mean the panel changed and the
    HERALD_57 part A statement would no longer hold."""
    zeros = sector_panel[sector_panel["sector_establishment_creations"].astype(float) == 0]
    assert len(zeros) == 1, zeros
    row = zeros.iloc[0]
    assert row["ze2020"] == "5218"
    assert int(row["year"]) == 2016
    assert row["sector_code"] == "JZ"


def test_a10_positive_cell_count(sector_panel: pd.DataFrame) -> None:
    positives = (sector_panel["sector_establishment_creations"].astype(float) > 0).sum()
    assert positives == 35_279


def test_a10_is_the_complete_cartesian_set(sector_panel: pd.DataFrame) -> None:
    """Every zone x year x sector combination must be present exactly once.

    A row count alone would not catch a missing cell compensated by a duplicate
    elsewhere.
    """
    from itertools import product

    zones = sorted(sector_panel["ze2020"].unique())
    sectors = sorted(sector_panel["sector_code"].unique())
    expected = {
        (zone, year, sector)
        for zone, year, sector in product(zones, PANEL_YEARS, sectors)
    }
    actual = {
        (row.ze2020, int(row.year), row.sector_code)
        for row in sector_panel.itertuples(index=False)
    }
    assert actual == expected
    assert len(actual) == len(sector_panel)


def test_a10_has_no_negative_value(sector_panel: pd.DataFrame) -> None:
    assert (sector_panel["sector_establishment_creations"].astype(float) >= 0).all()


def test_a10_mask_vocabulary_is_binary(sector_panel: pd.DataFrame) -> None:
    """The mask column must never carry a third state such as -1 or NaN."""
    values = set(sector_panel["mask_sector_available"].astype(int).unique())
    assert values <= {0, 1}
    # In this artifact specifically, every cell is available.
    assert values == {1}


def test_summary_declares_no_model_input_claim() -> None:
    if not SUMMARY_PATH.exists():
        pytest.skip("summary not generated; run the builder first")
    import json

    summary = json.loads(SUMMARY_PATH.read_text())
    assert summary["claim_status"] == "availability_provenance_only_not_model_input"
    assert summary["inputs_unchanged"] is True
    assert summary["row_count"] == len(ALL_FAMILIES) * len(PANEL_YEARS)
    assert summary["observed_status_used"] is False
