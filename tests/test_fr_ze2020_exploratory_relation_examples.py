"""
Tests for src/data/france_ze2020/build_fr_ze2020_exploratory_relation_examples.py
-- the small, presentation-ready relation examples table.
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_exploratory_relation_examples import (
    EXAMPLE_COLUMNS,
    OUT_PATH,
    build_relation_examples,
)

REPO_ROOT = Path(__file__).parent.parent
BUILDER_PATH = (
    REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_exploratory_relation_examples.py"
)

FORBIDDEN_COLUMN_NAMES = {
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
}
PREDICTIVE_METRIC_NAMES = {"wmape", "mae", "rmse", "y_pred", "y_true"}


@pytest.fixture(scope="module")
def examples():
    assert OUT_PATH.exists(), f"Examples file not found: {OUT_PATH}"
    return pd.read_csv(
        OUT_PATH, dtype={"ze2020": str, "related_ze2020": str, "sector_code": str, "related_sector_code": str}
    )


def test_file_exists():
    assert OUT_PATH.exists()


def test_schema_matches_expected_columns(examples):
    assert list(examples.columns) == EXAMPLE_COLUMNS


def test_example_id_is_unique(examples):
    assert examples["example_id"].is_unique


def test_no_forbidden_recommendation_columns(examples):
    cols_lower = {c.lower() for c in examples.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)


def test_no_predictive_metric_columns_mixed_in(examples):
    cols_lower = {c.lower() for c in examples.columns}
    assert not (cols_lower & PREDICTIVE_METRIC_NAMES)


def test_every_row_has_a_nonempty_caveat(examples):
    assert examples["caveat"].notna().all()
    assert examples["caveat"].str.contains("causalidade", case=False).all()


def test_no_causal_language_in_interpretation(examples):
    for text in examples["plain_language_interpretation"].dropna():
        lowered = text.lower()
        assert "causal" not in lowered
        assert "descobriu" not in lowered


def test_all_four_families_represented(examples):
    assert set(examples["main_signal"].unique()) == {
        "ze_to_ze_similarity",
        "ze_to_ze_same_sector_signal",
        "intra_ze_sector_interaction",
        "ze_sector_specialization",
    }


def test_examples_are_curated_small_set(examples):
    """This file exists to be presentable, not exhaustive."""
    assert 0 < len(examples) <= 40


def test_ze2020_is_zero_padded_4char_string(examples):
    assert (examples["ze2020"].str.len() == 4).all()


def test_builder_does_not_read_legacy_or_unprovenanced_sources():
    source = BUILDER_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_examples_prefer_stability_over_raw_signal_strength(examples):
    """For ze_to_ze_similarity specifically, the parent file's highest
    signal_strength rows are mostly one-year spikes (low stability) --
    examples must not just take the global top-signal_strength rows."""
    ze_examples = examples[examples["main_signal"] == "ze_to_ze_similarity"]
    assert (ze_examples["stability_score"] >= 0.5).all()


def test_output_is_regenerable_deterministic():
    first = build_relation_examples()
    second = build_relation_examples()
    pd.testing.assert_frame_equal(first, second)
