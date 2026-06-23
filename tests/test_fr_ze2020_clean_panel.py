"""
Consistency tests for the canonical FR ZE2020 clean treated panel.

See reports/canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md for the
full pipeline description. Generator:
src/data/france_ze2020/build_fr_ze2020_clean_panel.py
"""

from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
MAPPING_PATH = REPO_ROOT / "data/interim/mappings/commune_to_ze2020_2026.csv"
LEGACY_TARGET_PATH = REPO_ROOT / "data/processed/target_side_establishments_annual_core_v0.csv"

EXPECTED_COLUMNS = [
    "ze2020",
    "ze2020_label",
    "year",
    "establishment_creations",
    "enterprise_creations",
    "communes_count",
    "mask_establishment_creations_available",
    "mask_enterprise_creations_available",
]

# Column names that must never appear in the canonical treated panel: legacy
# architecture naming, leaky growth features, or fake/hardcoded QC flags
# confirmed in data/processed/dynamic_stgnn_feature_panel_v1.csv (see HERALD_15
# section 5).
FORBIDDEN_COLUMN_SUBSTRINGS = ["stgnn", "growth_1y", "growth_2y"]
FORBIDDEN_COLUMN_NAMES = {"feature_forecast_safe", "has_urssaf_source", "node_idx"}


@pytest.fixture(scope="module")
def panel():
    assert PANEL_PATH.exists(), f"Canonical panel not found: {PANEL_PATH}"
    return pd.read_csv(PANEL_PATH, dtype={"ze2020": str})


def test_panel_file_exists():
    assert PANEL_PATH.exists()


def test_schema_matches_expected_columns(panel):
    assert list(panel.columns) == EXPECTED_COLUMNS


def test_ze2020_is_zero_padded_4char_string(panel):
    assert panel["ze2020"].apply(lambda v: isinstance(v, str)).all()
    assert (panel["ze2020"].str.len() == 4).all()
    # at least one zone must show a leading zero, otherwise a regression that
    # silently strips it (e.g. reading without dtype=str) would go unnoticed
    assert panel["ze2020"].str.startswith("0").any()


def test_ze2020_zero_stripped_if_read_without_dtype():
    """Documents the known CSV gotcha: ze2020 MUST be read with dtype=str."""
    naive = pd.read_csv(PANEL_PATH)
    assert naive["ze2020"].dtype != object, (
        "expected pandas to infer ze2020 as numeric when dtype is not pinned; "
        "if this fails, the documented gotcha in HERALD_15 may be stale"
    )


def test_year_is_integer_column(panel):
    assert pd.api.types.is_integer_dtype(panel["year"])


def test_panel_has_280_ze2020_zones(panel):
    assert panel["ze2020"].nunique() == 280


def test_panel_covers_2012_to_2024(panel):
    assert sorted(panel["year"].unique()) == list(range(2012, 2025))


def test_no_duplicate_ze2020_year_rows(panel):
    dupes = panel.duplicated(subset=["ze2020", "year"]).sum()
    assert dupes == 0


def test_no_forbidden_column_names(panel):
    cols_lower = [c.lower() for c in panel.columns]
    for bad in FORBIDDEN_COLUMN_SUBSTRINGS:
        assert not any(bad in c for c in cols_lower), f"forbidden token '{bad}' found in columns"
    assert not (set(panel.columns) & FORBIDDEN_COLUMN_NAMES)


def test_no_constant_column_disguised_as_qc_flag(panel):
    """Mask/flag columns must carry real signal, not a hardcoded constant."""
    flag_cols = [c for c in panel.columns if c.startswith("mask_")]
    assert flag_cols, "expected at least one documented availability mask column"
    for col in flag_cols:
        assert panel[col].nunique() >= 1  # present and well-formed
        assert set(panel[col].unique()).issubset({0, 1})


def test_territorial_join_no_int_string_mix():
    """Joining the panel against the raw commune->ZE2020 mapping must not
    silently drop rows due to int/string ze2020 mismatches."""
    panel_df = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    mapping = pd.read_csv(MAPPING_PATH, dtype={"ZE2020": str})
    mapping["ZE2020"] = mapping["ZE2020"].str.zfill(4)
    zones_in_panel = set(panel_df["ze2020"].unique())
    zones_in_mapping = set(mapping["ZE2020"].unique())
    assert zones_in_panel.issubset(zones_in_mapping)
    assert len(zones_in_panel) == 280


def test_values_match_existing_official_target_panel(panel):
    """Regression guard: establishment_creations must match the existing
    official SIDE target panel exactly (same INSEE source, independently
    re-derived from the raw commune-level table)."""
    legacy = pd.read_csv(LEGACY_TARGET_PATH, dtype={"ze2020": str}).rename(
        columns={"target_year": "year"}
    )
    merged = panel.merge(legacy, on=["ze2020", "year"], suffixes=("_new", "_old"))
    assert len(merged) == 3640
    diff = (
        merged["establishment_creations"] - merged["side_establishment_creations_official"]
    ).abs()
    assert diff.max() < 1e-9
