"""
Tests for src/modeles/france_ze2020/run_fr_ze2020_training_block.py -- the
training block orchestrator (no new model, consolidates the 4 existing
scripts' metrics). Building the sector graph node table (~1 minute) is the
dominant cost regardless of how many eval_years are requested, so the full
run is done ONCE in a module-scoped fixture and reused by every test.
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from src.modeles.france_ze2020.run_fr_ze2020_training_block import (
    SUMMARY_CLAIM_STATUS,
    SUMMARY_COLUMNS,
    run_training_block,
)

SCRIPT_PATH = (
    Path(__file__).parent.parent / "src/modeles/france_ze2020/run_fr_ze2020_training_block.py"
)

FORBIDDEN_COLUMN_NAMES = {"recommendation", "recommended_action", "policy_action"}


@pytest.fixture(scope="module")
def summary():
    return run_training_block(eval_years=[2023, 2024, 2025], max_epochs=50)


def test_script_does_not_read_legacy_or_unprovenanced_sources():
    source = SCRIPT_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_script_does_not_define_a_new_model():
    """This is an orchestrator: it must import run_* functions, never
    define its own model-fitting logic."""
    source = SCRIPT_PATH.read_text()
    assert "MLPRegressor(" not in source
    assert "Ridge(" not in source
    assert "def run_baselines(" not in source
    assert "def run_relational_baselines(" not in source
    assert "def run_neural_relational_smoke(" not in source
    assert "def run_sector_graph_smoke(" not in source


def test_summary_schema(summary):
    assert list(summary.columns) == SUMMARY_COLUMNS


def test_summary_includes_all_four_source_scripts(summary):
    assert set(summary["source_script"].unique()) == {
        "train_fr_ze2020_baselines.py",
        "train_fr_ze2020_relational_baselines.py",
        "train_fr_ze2020_neural_relational_mlp.py",
        "train_fr_ze2020_sector_graph_prototype.py",
    }


def test_summary_includes_both_grains(summary):
    assert set(summary["grain"].unique()) == {"ze_x_year", "ze_x_sector_x_year"}


def test_all_rows_marked_smoke_local_only(summary):
    assert (summary["claim_status"] == SUMMARY_CLAIM_STATUS).all()
    assert "smoke" in SUMMARY_CLAIM_STATUS
    assert "local" in SUMMARY_CLAIM_STATUS


def test_no_recommendation_or_policy_column(summary):
    cols_lower = {c.lower() for c in summary.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)


def test_mean_wmape_values_are_finite_and_nonnegative(summary):
    assert summary["mean_wmape"].notna().all()
    assert (summary["mean_wmape"] >= 0).all()


def test_eval_year_window_within_requested_range(summary):
    assert (summary["eval_year_start"] >= 2019).all()
    assert (summary["eval_year_end"] <= 2025).all()
    assert (summary["eval_year_start"] <= summary["eval_year_end"]).all()


def test_output_writable_to_tmp_dir(tmp_path, summary):
    out_path = tmp_path / "fr_ze2020_training_block_summary_v1.csv"
    summary.to_csv(out_path, index=False)
    assert out_path.exists()
    reloaded = pd.read_csv(out_path)
    assert len(reloaded) == len(summary)
