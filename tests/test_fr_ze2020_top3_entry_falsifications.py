from pathlib import Path

import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_falsifications import (
    CLAIM_STATUS,
    SCENARIOS,
    SECTOR_COLUMNS,
    TEMPORAL_COLUMNS,
    apply_top3_entry_falsification,
    run_top3_entry_falsification_suite,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import load_ranking_panel

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py"
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"


def test_scenarios_are_explicit():
    assert SCENARIOS == [
        "full_control",
        "temporal_shuffle",
        "sector_shuffle",
        "target_shuffle",
    ]


def test_script_has_no_forbidden_claim_terms():
    source = SCRIPT_PATH.read_text()
    forbidden_terms = [
        "recommended" + "_action",
        "policy" + "_action",
        "causal" + "_effect",
        "causal" + "_impact",
    ]
    for term in forbidden_terms:
        assert term not in source


def test_temporal_shuffle_preserves_year_distribution():
    panel = load_ranking_panel()
    sample = panel[panel["decision_year"] == 2019].head(500).copy()
    out = apply_top3_entry_falsification(sample, "temporal_shuffle", seed=42)
    for col in TEMPORAL_COLUMNS:
        assert sorted(out[col].fillna(-999).round(12).tolist()) == sorted(
            sample[col].fillna(-999).round(12).tolist()
        )
    assert set(out["decision_year"]) == {2019}


def test_sector_shuffle_preserves_ze_year_distribution():
    panel = load_ranking_panel()
    sample = panel[(panel["ze2020"] == "0051") & (panel["decision_year"] == 2019)].copy()
    out = apply_top3_entry_falsification(sample, "sector_shuffle", seed=42)
    for col in SECTOR_COLUMNS:
        assert sorted(out[col].fillna(-999).round(12).tolist()) == sorted(
            sample[col].fillna(-999).round(12).tolist()
        )


def test_target_shuffle_preserves_ze_year_future_growth_distribution():
    panel = load_ranking_panel()
    sample = panel[(panel["ze2020"] == "0051") & (panel["decision_year"] == 2019)].copy()
    out = apply_top3_entry_falsification(sample, "target_shuffle", seed=42)
    assert sorted(out["future_growth_3y"].fillna(-999).round(12).tolist()) == sorted(
        sample["future_growth_3y"].fillna(-999).round(12).tolist()
    )
    pd.testing.assert_series_equal(out["sector_growth_lag_1"], sample["sector_growth_lag_1"])


def test_real_panel_falsification_smoke_if_available():
    if not PANEL_PATH.exists():
        return
    panel = load_ranking_panel(PANEL_PATH)
    predictions, metrics, summary = run_top3_entry_falsification_suite(
        panel,
        scenarios=["full_control", "target_shuffle"],
        eval_years=[2020],
        seeds=[42],
        feature_configs=["no_relation_features", "base_formula_features"],
        max_epochs=10,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert not summary.empty
    assert set(predictions["claim_status"]) == {CLAIM_STATUS}
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert set(summary["claim_status"]) == {CLAIM_STATUS}
    assert set(summary["falsification_scenario"]) == {"full_control", "target_shuffle"}
    assert "recommendation" not in {col.lower() for col in predictions.columns}
