"""
Consistency tests for the FR ZE2020 sector composition panel (MVP2 Category
C, step 1). Generator: src/data/france_ze2020/build_fr_ze2020_sector_panel.py.

Audited source (data/processed/side_creations_a10_ze2020_through_2025_v1.csv) has no
generator script in the current tree -- CANDIDATE_NEEDS_PROVENANCE, used
only because its values reconcile exactly with the canonical clean panel.
See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md, "MVP2
Categoria C" section.
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_sector_panel import (
    A10_SOURCE_PATH,
    CLEAN_PANEL_PATH,
    OUT_PATH,
    SECTOR_CODES,
    build_sector_panel,
    load_a10_source,
    load_clean_panel,
)

REPO_ROOT = Path(__file__).parent.parent
BUILDER_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_sector_panel.py"

EXPECTED_COLUMNS = [
    "ze2020",
    "ze2020_label",
    "year",
    "sector_code",
    "sector_label",
    "sector_establishment_creations",
    "total_establishment_creations",
    "sector_share",
    "sector_rank_in_ze_year",
    "mask_sector_available",
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
    assert OUT_PATH.exists(), f"Sector panel not found: {OUT_PATH}"
    return pd.read_csv(OUT_PATH, dtype={"ze2020": str})


@pytest.fixture(scope="module")
def a10_raw():
    return load_a10_source()


def test_a10_source_audit_280_zones_14_years_9_sectors(a10_raw):
    assert a10_raw["ze2020"].nunique() == 280
    assert a10_raw["year"].nunique() == 14
    assert sorted(a10_raw["year"].unique()) == list(range(2012, 2026))
    assert len(a10_raw) == 280 * 14
    for sector in SECTOR_CODES:
        assert sector in a10_raw.columns


def test_a10_source_has_no_negative_or_missing_values(a10_raw):
    assert a10_raw[SECTOR_CODES + ["a10_total"]].isna().sum().sum() == 0
    assert (a10_raw[SECTOR_CODES + ["a10_total"]] >= 0).all().all()


def test_a10_source_has_no_duplicate_ze2020_year_rows(a10_raw):
    assert a10_raw.duplicated(subset=["ze2020", "year"]).sum() == 0


def test_a10_total_equals_sum_of_sector_columns(a10_raw):
    diff = (a10_raw["a10_total"] - a10_raw[SECTOR_CODES].sum(axis=1)).abs()
    assert diff.max() == 0


def test_a10_total_reconciles_with_canonical_clean_panel(a10_raw):
    clean = load_clean_panel()
    merged = a10_raw.merge(clean, on=["ze2020", "year"])
    assert len(merged) == len(a10_raw)
    diff = (merged["a10_total"] - merged["establishment_creations"]).abs()
    assert diff.max() == 0


def test_builder_raises_if_reconciliation_fails():
    a10 = load_a10_source()
    clean = load_clean_panel()
    corrupted = a10.copy()
    corrupted.loc[corrupted.index[0], "a10_total"] += 1000
    with pytest.raises(ValueError, match="does not reconcile"):
        build_sector_panel(corrupted, clean)


def test_panel_file_exists():
    assert OUT_PATH.exists()


def test_schema_matches_expected_columns(panel):
    assert list(panel.columns) == EXPECTED_COLUMNS


def test_ze2020_is_zero_padded_4char_string(panel):
    assert panel["ze2020"].apply(lambda v: isinstance(v, str)).all()
    assert (panel["ze2020"].str.len() == 4).all()


def test_panel_has_280_zones_14_years_9_sectors(panel):
    assert panel["ze2020"].nunique() == 280
    assert panel["year"].nunique() == 14
    assert panel["sector_code"].nunique() == 9
    assert len(panel) == 280 * 14 * 9


def test_sector_shares_sum_to_approximately_one_per_ze_year(panel):
    sums = panel.groupby(["ze2020", "year"])["sector_share"].sum()
    assert (sums - 1.0).abs().max() < 1e-9


def test_sector_rank_in_ze_year_is_1_to_9_with_rank_1_as_max_share(panel):
    assert panel["sector_rank_in_ze_year"].min() == 1
    assert panel["sector_rank_in_ze_year"].max() == 9
    top_ranked = panel[panel["sector_rank_in_ze_year"] == 1]
    max_share_per_group = panel.groupby(["ze2020", "year"])["sector_share"].max()
    merged = top_ranked.merge(
        max_share_per_group.rename("expected_max_share"), on=["ze2020", "year"]
    )
    assert (merged["sector_share"] == merged["expected_max_share"]).all()


def test_no_negative_shares_or_creations(panel):
    assert (panel["sector_establishment_creations"] >= 0).all()
    assert (panel["sector_share"] >= 0).all()


def test_no_forbidden_columns(panel):
    cols_lower = {c.lower() for c in panel.columns}
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


def test_alencon_2012_dominant_sector_is_trade_transport_hospitality(panel):
    sub = panel[(panel["ze2020"] == ALENCON_ZE2020) & (panel["year"] == 2012)]
    top = sub[sub["sector_rank_in_ze_year"] == 1].iloc[0]
    assert top["sector_code"] == "GI"
    assert top["sector_label"] == "Trade, transport and hospitality"
