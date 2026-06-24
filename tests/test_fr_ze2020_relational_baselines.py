"""
Tests for src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py --
the MVP2 relational smoke comparison. Fast/local: no HPC, no heavy training,
runs against the real (small) relational model-ready panel.
"""

import ast
from pathlib import Path

import numpy as np
import pytest

from src.modeles.france_ze2020.train_fr_ze2020_relational_baselines import (
    COMBINED_FEATURE_COLS,
    RELATIONAL_FEATURE_COLS,
    RELATIONAL_PANEL_PATH,
    TEMPORAL_FEATURE_COLS,
    load_relational_panel,
    run_relational_baselines,
)

SCRIPT_PATH = (
    Path(__file__).parent.parent
    / "src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py"
)
ORIGINAL_BASELINE_PATH = (
    Path(__file__).parent.parent / "src/modeles/france_ze2020/train_fr_ze2020_baselines.py"
)


@pytest.fixture(scope="module")
def panel():
    assert RELATIONAL_PANEL_PATH.exists(), f"Relational panel missing: {RELATIONAL_PANEL_PATH}"
    return load_relational_panel()


def test_script_does_not_read_legacy_or_unprovenanced_sources():
    """Docstring may name them (to document exclusion); executable code
    must not reference the legacy panel or the unprovenanced legacy ZE
    adjacency matrices."""
    source = SCRIPT_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_panel_path_points_to_relational_model_ready_panel():
    assert RELATIONAL_PANEL_PATH.name == "fr_ze2020_relational_model_ready_panel.csv"


def test_original_baseline_script_is_not_modified_by_this_one():
    """This script must add a third model next to the original two, never
    replace or edit train_fr_ze2020_baselines.py."""
    assert ORIGINAL_BASELINE_PATH.exists()
    source = SCRIPT_PATH.read_text()
    assert "def run_baselines(" not in source  # original function name, not redefined here
    assert "def predict_persistence(" not in source  # reused via import, not redefined


def test_feature_sets_are_disjoint_then_combined():
    assert set(RELATIONAL_FEATURE_COLS).isdisjoint(TEMPORAL_FEATURE_COLS)
    assert set(COMBINED_FEATURE_COLS) == set(TEMPORAL_FEATURE_COLS) | set(RELATIONAL_FEATURE_COLS)


def test_run_relational_baselines_smoke_produces_all_three_models(panel):
    eval_years = [2019, 2020, 2021, 2022, 2023, 2024]
    predictions, metrics = run_relational_baselines(panel, eval_years=eval_years)

    assert set(metrics["model"].unique()) == {"persistence", "ridge_temporal", "ridge_relational"}
    assert set(predictions["model"].unique()) == {
        "persistence",
        "ridge_temporal",
        "ridge_relational",
    }


def test_ridge_relational_skips_years_with_insufficient_relational_history(panel):
    """Relational features only exist from 2017 onward (panel-level fact);
    with RIDGE_MIN_TRAIN_YEARS=4, ridge_relational cannot run for eval_year
    2019/2020 (only 2017-2018 would be available) but can from 2021 onward
    (2017-2020 = 4 years)."""
    eval_years = [2019, 2020, 2021]
    _, metrics = run_relational_baselines(panel, eval_years=eval_years)
    relational_years = set(metrics[metrics["model"] == "ridge_relational"]["eval_year"])
    assert 2019 not in relational_years
    assert 2020 not in relational_years
    assert 2021 in relational_years


def test_all_three_models_share_the_same_test_rows_per_year(panel):
    """WMAPE across models is only comparable if n_test matches for every
    model at a given eval_year."""
    eval_years = [2021, 2022, 2023, 2024]
    _, metrics = run_relational_baselines(panel, eval_years=eval_years)
    for eval_year in eval_years:
        sub = metrics[metrics["eval_year"] == eval_year]
        assert sub["n_test"].nunique() == 1


def test_no_leakage_train_years_strictly_before_eval_year(panel):
    eval_years = [2021, 2022, 2023]
    _, metrics = run_relational_baselines(panel, eval_years=eval_years)
    relational_rows = metrics[metrics["model"] == "ridge_relational"]
    assert (relational_rows["n_train_years"] >= 4).all()


def test_wmape_values_are_finite_where_present(panel):
    _, metrics = run_relational_baselines(panel, eval_years=[2021, 2022, 2023, 2024])
    assert np.isfinite(metrics["wmape"].to_numpy(dtype=float)).all()


def test_predictions_and_metrics_marked_relational_smoke_not_headline(panel):
    predictions, metrics = run_relational_baselines(panel, eval_years=[2022, 2023, 2024])
    assert (predictions["claim_status"] == "relational_smoke_result").all()
    assert (metrics["claim_status"] == "relational_smoke_result").all()


def test_main_writes_outputs_to_tmp_dir_without_touching_repo(tmp_path, panel):
    predictions, metrics = run_relational_baselines(panel, eval_years=[2023, 2024])
    pred_path = tmp_path / "fr_ze2020_relational_baseline_predictions_v1.csv"
    metrics_path = tmp_path / "fr_ze2020_relational_baseline_metrics_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    assert pred_path.exists()
    assert metrics_path.exists()
