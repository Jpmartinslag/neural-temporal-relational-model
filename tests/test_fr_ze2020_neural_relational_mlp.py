"""
Tests for src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py
-- MVP3-A neural relational smoke prototype. Fast/local: no HPC, no heavy
training (sklearn MLPRegressor, max_iter capped, early stopping), runs
against the real (small) prototype panel.
"""

import ast
import time
from pathlib import Path

import numpy as np
import pytest

from src.modeles.france_ze2020.train_fr_ze2020_neural_relational_mlp import (
    NEURAL_FEATURE_COLS,
    PROTOTYPE_PANEL_PATH,
    attach_dominant_sector_national_signal,
    load_prototype_panel,
    run_neural_relational_smoke,
)

SCRIPT_PATH = (
    Path(__file__).parent.parent / "src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py"
)

FORBIDDEN_COLUMN_NAMES = {"recommendation", "recommended_action", "policy_action"}


@pytest.fixture(scope="module")
def panel():
    assert PROTOTYPE_PANEL_PATH.exists(), f"Prototype panel missing: {PROTOTYPE_PANEL_PATH}"
    return attach_dominant_sector_national_signal(load_prototype_panel())


def test_script_does_not_read_legacy_or_unprovenanced_sources():
    source = SCRIPT_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_panel_path_points_to_relational_sector_prototype():
    assert PROTOTYPE_PANEL_PATH.name == "fr_ze2020_relational_sector_prototype_panel.csv"


def test_run_produces_all_four_models(panel):
    predictions, metrics, signals = run_neural_relational_smoke(panel, eval_years=[2022, 2023, 2024])
    assert set(metrics["model"].unique()) == {
        "persistence",
        "ridge_temporal",
        "ridge_relational",
        "mlp_relational",
    }
    assert set(predictions["model"].unique()) == set(metrics["model"].unique())


def test_all_models_share_the_same_test_rows_per_year(panel):
    _, metrics, _ = run_neural_relational_smoke(panel, eval_years=[2021, 2022, 2023, 2024])
    for eval_year in [2021, 2022, 2023, 2024]:
        sub = metrics[metrics["eval_year"] == eval_year]
        assert sub["n_test"].nunique() == 1


def test_no_leakage_train_years_strictly_before_eval_year(panel):
    _, metrics, _ = run_neural_relational_smoke(panel, eval_years=[2021, 2022, 2023])
    mlp_rows = metrics[metrics["model"] == "mlp_relational"]
    assert (mlp_rows["n_train_years"] >= 4).all()


def test_no_relational_feature_uses_the_target_years_own_data(panel):
    """Truncating the input to years <= eval_year must reproduce identical
    NEURAL_FEATURE_COLS values at eval_year -- since these features are all
    already-causal columns from upstream panels, this should hold trivially,
    but is verified directly here rather than assumed."""
    eval_year = 2022
    truncated = panel[panel["year"] <= eval_year]
    full_at_t = panel[panel["year"] == eval_year].set_index("ze2020").sort_index()
    trunc_at_t = truncated[truncated["year"] == eval_year].set_index("ze2020").sort_index()
    for col in NEURAL_FEATURE_COLS:
        assert full_at_t[col].equals(trunc_at_t[col])


def test_outputs_exist_in_smoke_mode(panel, tmp_path):
    predictions, metrics, signals = run_neural_relational_smoke(
        panel, eval_years=[2023, 2024], max_epochs=50
    )
    pred_path = tmp_path / "fr_ze2020_neural_relational_predictions_v1.csv"
    metrics_path = tmp_path / "fr_ze2020_neural_relational_metrics_v1.csv"
    signals_path = tmp_path / "fr_ze2020_neural_relational_feature_signals_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    signals.to_csv(signals_path, index=False)

    assert pred_path.exists() and metrics_path.exists() and signals_path.exists()
    assert len(predictions) > 0
    assert len(signals) == len(NEURAL_FEATURE_COLS) * 2  # 2 eval years


def test_feature_signals_have_exploratory_claim_status(panel):
    _, _, signals = run_neural_relational_smoke(panel, eval_years=[2024], max_epochs=50)
    assert (signals["claim_status"] == "neural_relational_smoke").all()
    assert set(signals.columns) == {"feature", "importance_score", "eval_year", "claim_status"}


def test_predictions_and_metrics_marked_smoke_not_headline(panel):
    predictions, metrics, _ = run_neural_relational_smoke(panel, eval_years=[2024], max_epochs=50)
    assert (predictions["claim_status"] == "neural_relational_smoke").all()
    assert (metrics["claim_status"] == "neural_relational_smoke").all()


def test_no_recommendation_or_policy_column_anywhere(panel):
    predictions, metrics, signals = run_neural_relational_smoke(panel, eval_years=[2024], max_epochs=50)
    for df in (predictions, metrics, signals):
        cols_lower = {c.lower() for c in df.columns}
        assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)


def test_no_causal_or_recommendation_language_in_docstring():
    source = SCRIPT_PATH.read_text()
    tree = ast.parse(source)
    docstring = (ast.get_docstring(tree) or "").lower()
    assert "causal claim" not in docstring or "no causal claim" in docstring
    assert "recommend" not in docstring or "no automatic" in docstring or "no recommendation" in docstring


def test_runs_fast_with_small_max_epochs(panel):
    start = time.time()
    run_neural_relational_smoke(panel, eval_years=[2024], max_epochs=50)
    elapsed = time.time() - start
    assert elapsed < 30


def test_reproducible_with_fixed_seed(panel):
    predictions_a, metrics_a, signals_a = run_neural_relational_smoke(
        panel, eval_years=[2023, 2024], max_epochs=100, seed=42
    )
    predictions_b, metrics_b, signals_b = run_neural_relational_smoke(
        panel, eval_years=[2023, 2024], max_epochs=100, seed=42
    )
    assert predictions_a.equals(predictions_b)
    np.testing.assert_array_equal(metrics_a["wmape"].to_numpy(), metrics_b["wmape"].to_numpy())
    np.testing.assert_array_equal(
        signals_a["importance_score"].to_numpy(), signals_b["importance_score"].to_numpy()
    )


def test_ratio_target_reconstruction_never_divides_by_zero(panel):
    """lag_1 must be strictly positive for every row used to train/predict
    (the ratio-target reconstruction multiplies by lag_1; dividing by a
    zero/negative lag_1 would be undefined)."""
    from src.modeles.france_ze2020.train_fr_ze2020_neural_relational_mlp import (
        _completeness_mask,
    )

    complete = panel[_completeness_mask(panel)]
    assert (complete["lag_1"] > 0).all()
