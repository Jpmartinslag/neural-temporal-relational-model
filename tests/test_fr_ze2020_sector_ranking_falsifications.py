from pathlib import Path

import numpy as np
import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_sector_ranking_falsifications import (
    CLAIM_STATUS,
    RELATIONAL_COLUMNS,
    SCENARIOS,
    SECTOR_COMPOSITION_COLUMNS,
    TEMPORAL_COLUMNS,
    apply_falsification,
    run_falsification_suite,
    summarize_metrics,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import load_ranking_panel

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_sector_ranking_falsifications.py"


def test_falsification_scenarios_are_explicit():
    assert SCENARIOS == [
        "full_control",
        "no_relational",
        "random_relational",
        "no_sector_composition",
        "sector_shuffle",
        "temporal_shuffle",
    ]


def test_no_relational_zeroes_only_relation_columns():
    panel = load_ranking_panel().head(100)
    out = apply_falsification(panel, "no_relational", seed=42)
    assert (out[RELATIONAL_COLUMNS] == 0).all().all()
    pd.testing.assert_series_equal(out["sector_share_t"], panel["sector_share_t"])


def test_random_relational_preserves_distribution_not_order():
    panel = load_ranking_panel()
    sample = panel[panel["decision_year"] == 2019].head(500)
    out = apply_falsification(sample, "random_relational", seed=42)
    for col in RELATIONAL_COLUMNS:
        assert sorted(out[col].round(12).tolist()) == sorted(sample[col].round(12).tolist())
    assert not out[RELATIONAL_COLUMNS].equals(sample[RELATIONAL_COLUMNS])


def test_sector_shuffle_preserves_group_distribution():
    panel = load_ranking_panel()
    sample = panel[(panel["ze2020"] == "0051") & (panel["decision_year"] == 2019)].copy()
    out = apply_falsification(sample, "sector_shuffle", seed=42)
    for col in SECTOR_COMPOSITION_COLUMNS:
        assert sorted(out[col].round(12).tolist()) == sorted(sample[col].round(12).tolist())


def test_temporal_shuffle_preserves_year_distribution_without_future_mixing():
    panel = load_ranking_panel()
    sample = panel[panel["decision_year"] == 2019].head(500).copy()
    out = apply_falsification(sample, "temporal_shuffle", seed=42)
    for col in TEMPORAL_COLUMNS:
        assert sorted(out[col].fillna(-999).round(12).tolist()) == sorted(sample[col].fillna(-999).round(12).tolist())
    assert set(out["decision_year"]) == {2019}


def test_falsification_smoke_outputs_expected_schema():
    panel = load_ranking_panel()
    predictions, metrics, manifest = run_falsification_suite(
        panel,
        scenarios=["full_control", "no_relational"],
        eval_years=[2018],
        seed=42,
        max_epochs=30,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert set(metrics["falsification_scenario"]) == {"full_control", "no_relational"}
    assert set(predictions["claim_status"]) == {CLAIM_STATUS}
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert set(manifest["falsification_scenario"]) == {"full_control", "no_relational"}
    assert metrics["ndcg_at_k"].between(0, 1).all()
    assert np.isfinite(predictions["score"].to_numpy(dtype=float)).all()


def test_summary_has_one_row_per_scenario_model():
    panel = load_ranking_panel()
    _, metrics, _ = run_falsification_suite(
        panel,
        scenarios=["full_control"],
        eval_years=[2018],
        seed=42,
        max_epochs=20,
    )
    summary = summarize_metrics(metrics)
    assert {"falsification_scenario", "model", "mean_ndcg_at_k"}.issubset(summary.columns)
    assert summary["mean_ndcg_at_k"].between(0, 1).all()


def test_falsification_supports_one_year_target():
    panel = load_ranking_panel()
    predictions, metrics, manifest = run_falsification_suite(
        panel,
        scenarios=["full_control"],
        eval_years=[2024],
        seed=42,
        max_epochs=20,
        target_horizon=1,
    )
    assert set(predictions["target_horizon_years"]) == {1}
    assert set(metrics["target_horizon_years"]) == {1}
    assert set(manifest["target_horizon_years"]) == {1}
    assert set(metrics["eval_year"]) == {2024}


def test_falsification_script_has_no_forbidden_terms_as_outputs_or_claims():
    source = SCRIPT_PATH.read_text()
    forbidden_claims = ["recommended_action", "policy_action", "causal_effect", "causal_impact"]
    for term in forbidden_claims:
        assert term not in source
