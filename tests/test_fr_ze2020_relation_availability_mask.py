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
    COMMUTING_FAMILY,
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
    build_mask,
    sha256,
    validate_mask,
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


def test_summary_declares_no_model_input_claim() -> None:
    if not SUMMARY_PATH.exists():
        pytest.skip("summary not generated; run the builder first")
    import json

    summary = json.loads(SUMMARY_PATH.read_text())
    assert summary["claim_status"] == "availability_provenance_only_not_model_input"
    assert summary["inputs_unchanged"] is True
    assert summary["row_count"] == len(ALL_FAMILIES) * len(PANEL_YEARS)
    assert summary["observed_status_used"] is False
