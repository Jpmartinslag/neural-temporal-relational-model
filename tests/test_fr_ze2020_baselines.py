"""
Tests for src/modeles/france_ze2020/train_fr_ze2020_baselines.py -- the
minimal current France ZE2020 baseline path. Fast/local (smoke): no HPC,
no heavy training, runs against the real (small) model-ready panel.
"""

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeles.france_ze2020.train_fr_ze2020_baselines import (
    PANEL_PATH,
    causal_train_test_split,
    compute_wmape,
    fit_predict_ridge,
    load_panel,
    predict_persistence,
    run_baselines,
)

SCRIPT_PATH = Path(__file__).parent.parent / "src/modeles/france_ze2020/train_fr_ze2020_baselines.py"


@pytest.fixture(scope="module")
def panel():
    assert PANEL_PATH.exists(), f"Model-ready panel missing: {PANEL_PATH}"
    return load_panel()


def test_script_does_not_read_legacy_dynamic_stgnn_panel():
    """The module docstring is allowed to name the legacy file (to document
    that it must not be used); the executable code must not reference it."""
    tree = ast.parse(SCRIPT_PATH.read_text())
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = SCRIPT_PATH.read_text().replace(docstring, "")
    assert "dynamic_stgnn_feature_panel" not in code_without_docstring


def test_panel_path_points_to_model_ready_panel():
    assert PANEL_PATH.name == "fr_ze2020_model_ready_panel.csv"
    assert "france_ze2020" in str(PANEL_PATH)


def test_causal_split_uses_only_strictly_prior_years(panel):
    split = causal_train_test_split(panel, eval_year=2022, min_train_years=4)
    assert split is not None
    train, test = split
    assert train["year"].max() < 2022
    assert (test["year"] == 2022).all()


def test_causal_split_returns_none_when_insufficient_train_years(panel):
    # Complete features (lag_1/2/3) start at year=2015; eval_year=2016 only
    # has one complete prior year (2015), below RIDGE_MIN_TRAIN_YEARS=4.
    split = causal_train_test_split(panel, eval_year=2016, min_train_years=4)
    assert split is None


def test_persistence_is_exactly_lag_1_no_fitting(panel):
    split = causal_train_test_split(panel, eval_year=2022, min_train_years=4)
    train, test = split
    y_pred = predict_persistence(test)
    np.testing.assert_array_equal(y_pred, test["lag_1"].to_numpy(dtype=float))


def test_ridge_predictions_are_finite(panel):
    split = causal_train_test_split(panel, eval_year=2022, min_train_years=4)
    train, test = split
    y_pred = fit_predict_ridge(train, test)
    assert np.isfinite(y_pred).all()
    assert len(y_pred) == len(test)


def test_compute_wmape_matches_manual_calculation():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 33.0])
    expected = (2.0 + 2.0 + 3.0) / (10.0 + 20.0 + 30.0)
    assert compute_wmape(y_true, y_pred) == pytest.approx(expected)


def test_compute_wmape_zero_denominator_is_nan():
    assert np.isnan(compute_wmape(np.array([0.0, 0.0]), np.array([1.0, 2.0])))


def test_run_baselines_smoke_produces_both_models(panel):
    eval_years = [2019, 2020, 2021, 2022, 2023, 2024]
    predictions, metrics = run_baselines(panel, eval_years=eval_years)

    assert set(predictions["model"].unique()) == {"persistence", "ridge"}
    assert set(metrics["model"].unique()) == {"persistence", "ridge"}
    assert set(metrics["eval_year"].unique()) == set(eval_years)

    expected_pred_cols = {"ze2020", "year", "model", "y_true", "y_pred", "claim_status"}
    assert expected_pred_cols.issubset(predictions.columns)

    expected_metric_cols = {"eval_year", "model", "n_test", "n_train_years", "wmape", "claim_status"}
    assert expected_metric_cols.issubset(metrics.columns)


def test_run_baselines_no_leakage_train_year_strictly_before_eval(panel):
    eval_years = [2020, 2022, 2024]
    predictions, metrics = run_baselines(panel, eval_years=eval_years)
    for eval_year in eval_years:
        sub = metrics[metrics["eval_year"] == eval_year]
        assert (sub["n_train_years"] >= 4).all()
    # n_test must equal the 280 zones (all complete at these eval years)
    assert (metrics["n_test"] == 280).all()


def test_predictions_and_metrics_marked_exploratory_not_headline(panel):
    predictions, metrics = run_baselines(panel, eval_years=[2022, 2023, 2024])
    assert (predictions["claim_status"] == "exploratory_smoke").all()
    assert (metrics["claim_status"] == "exploratory_smoke").all()


def test_main_writes_outputs_to_tmp_dir_without_touching_repo(tmp_path, panel):
    from src.modeles.france_ze2020.train_fr_ze2020_baselines import run_baselines

    predictions, metrics = run_baselines(panel, eval_years=[2023, 2024])
    pred_path = tmp_path / "fr_ze2020_baseline_predictions_v1.csv"
    metrics_path = tmp_path / "fr_ze2020_baseline_metrics_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    assert pred_path.exists()
    assert metrics_path.exists()
    reloaded = pd.read_csv(pred_path)
    assert len(reloaded) == len(predictions)
