from pathlib import Path

import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_ranking_smoke import (
    CLAIM_STATUS,
    FEATURE_CONFIGS,
    _feature_columns,
    _shuffle_relation_columns,
    run_top3_entry_ranking_smoke,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (
    MODEL_FEATURE_COLUMNS,
    load_ranking_panel,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py"
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"


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


def test_feature_configs_are_explicit_and_relation_removal_is_real():
    assert set(FEATURE_CONFIGS) == {
        "no_relation_features",
        "base_formula_features",
        "shuffled_relation_features",
    }
    no_relation = _feature_columns("no_relation_features")
    base = _feature_columns("base_formula_features")
    assert len(no_relation) < len(base)
    assert not any(col.startswith("relation_") for col in no_relation)
    assert any(col.startswith("relation_") for col in base)


def test_shuffle_relation_columns_keeps_non_relation_columns():
    panel = pd.DataFrame(
        {
            "decision_year": [2020, 2020, 2020],
            "relation_signal_strength_mean_to_t": [0.1, 0.2, 0.3],
            "sector_share_t": [0.4, 0.5, 0.6],
        }
    )
    original_features = list(MODEL_FEATURE_COLUMNS)
    try:
        import src.modeles.france_ze2020.run_fr_ze2020_top3_entry_ranking_smoke as smoke

        smoke.MODEL_FEATURE_COLUMNS = ["relation_signal_strength_mean_to_t", "sector_share_t"]
        shuffled = _shuffle_relation_columns(panel, seed=42)
    finally:
        smoke.MODEL_FEATURE_COLUMNS = original_features
    assert sorted(shuffled["relation_signal_strength_mean_to_t"].tolist()) == [0.1, 0.2, 0.3]
    assert shuffled["sector_share_t"].tolist() == [0.4, 0.5, 0.6]


def test_real_panel_top3_entry_smoke_if_available():
    if not PANEL_PATH.exists():
        return
    panel = load_ranking_panel(PANEL_PATH)
    predictions, metrics, summary = run_top3_entry_ranking_smoke(
        panel,
        target_horizon=3,
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
    assert set(summary["feature_config"]) == {"no_relation_features", "base_formula_features"}
    assert {"logit_entry_classifier", "mlp_entry_classifier"}.issubset(set(summary["model"]))
    assert "recommendation" not in {col.lower() for col in predictions.columns}
