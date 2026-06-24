"""
Tests for src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py
-- the exploratory relation analysis layer (NOT a predictive model; see
reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md).
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_exploratory_relation_signals import (
    CLAIM_STATUS,
    OUT_PATH,
    RELATION_COLUMNS,
    build_exploratory_relation_signals,
)

REPO_ROOT = Path(__file__).parent.parent
BUILDER_PATH = (
    REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py"
)

FORBIDDEN_COLUMN_NAMES = {"recommendation", "recommended_action", "policy_action"}
PREDICTIVE_METRIC_NAMES = {"wmape", "mae", "rmse", "y_pred", "y_true"}
CAUSAL_WORDS = ("causal", "causa diretamente", "prova economica", "prova econômica")
EXPECTED_FAMILIES = {
    "ze_to_ze_similarity",
    "ze_to_ze_same_sector_signal",
    "intra_ze_sector_interaction",
    "ze_sector_specialization",
}


@pytest.fixture(scope="module")
def signals():
    assert OUT_PATH.exists(), f"Exploratory relation signals not found: {OUT_PATH}"
    return pd.read_csv(OUT_PATH, dtype={"source_id": str, "target_id": str, "sector_code": str})


def test_file_exists():
    assert OUT_PATH.exists()


def test_schema_matches_expected_columns(signals):
    assert list(signals.columns) == RELATION_COLUMNS


def test_no_forbidden_recommendation_columns(signals):
    cols_lower = {c.lower() for c in signals.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)


def test_no_predictive_metric_columns_mixed_in(signals):
    """Relational ranking must never be mixed with predictive metrics in the
    same table (Parte 3 / Parte 6 requirement)."""
    cols_lower = {c.lower() for c in signals.columns}
    assert not (cols_lower & PREDICTIVE_METRIC_NAMES)


def test_claim_status_always_denies_causality(signals):
    assert (signals["claim_status"] == CLAIM_STATUS).all()
    assert "not_causal" in CLAIM_STATUS or "nao_causal" in CLAIM_STATUS


def test_every_row_has_a_nonempty_caveat(signals):
    assert signals["caveat"].notna().all()
    assert (signals["caveat"].str.len() > 0).all()
    assert signals["caveat"].str.contains("causalidade", case=False).all()


def test_no_causal_language_outside_the_negation(signals):
    """The only permitted appearance of 'causal' is inside the explicit
    negation phrase ('não estabelece causalidade'); no row's
    interpretation_label may otherwise claim a causal/proof relationship."""
    for label in signals["interpretation_label"].dropna():
        lowered = label.lower()
        assert "causal" not in lowered
        assert "prova" not in lowered
        assert "descobriu" not in lowered


def test_relation_id_is_unique(signals):
    assert signals["relation_id"].is_unique


def test_all_four_expected_families_present(signals):
    assert set(signals["relation_family"].unique()) == EXPECTED_FAMILIES


def test_builder_does_not_read_legacy_or_unprovenanced_sources():
    source = BUILDER_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_ze2020_ids_are_zero_padded_4char_strings(signals):
    ze_rows = signals[signals["source_type"] == "ZE2020"]
    assert (ze_rows["source_id"].str.len() == 4).all()
    target_ze_rows = signals[signals["target_type"] == "ZE2020"]
    assert (target_ze_rows["target_id"].str.len() == 4).all()


def test_years_include_2025_where_applicable(signals):
    assert (signals["year_end"] <= 2025).all()
    assert (signals["year_end"] >= 2025).any()


def test_rank_within_family_starts_at_1_and_has_no_gaps(signals):
    for family, group in signals.groupby("relation_family"):
        ranks = sorted(group["rank_within_family"].unique())
        assert ranks == list(range(1, len(ranks) + 1))


def test_output_is_regenerable_deterministic():
    """Same inputs must produce an identical table on a second build (no
    randomness anywhere in this layer -- it is pure aggregation/extraction,
    not a trained model)."""
    first = build_exploratory_relation_signals()
    second = build_exploratory_relation_signals()
    pd.testing.assert_frame_equal(
        first.sort_values("relation_id").reset_index(drop=True),
        second.sort_values("relation_id").reset_index(drop=True),
    )


def test_stability_score_is_a_fraction(signals):
    assert (signals["stability_score"] > 0).all()
    assert (signals["stability_score"] <= 1.0).all()
