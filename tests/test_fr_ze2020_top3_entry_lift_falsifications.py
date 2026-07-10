from pathlib import Path

from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_lift_falsifications import (
    CLAIM_STATUS,
    run_top3_entry_lift_falsification_suite,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import load_ranking_panel

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_falsifications.py"
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"


def test_lift_falsification_script_has_no_forbidden_claim_terms():
    source = SCRIPT_PATH.read_text()
    forbidden_terms = [
        "recommended" + "_action",
        "policy" + "_action",
        "causal" + "_effect",
        "causal" + "_impact",
    ]
    for term in forbidden_terms:
        assert term not in source


def test_real_panel_lift_falsification_smoke_if_available():
    if not PANEL_PATH.exists():
        return
    panel = load_ranking_panel(PANEL_PATH)
    predictions, metrics, summary = run_top3_entry_lift_falsification_suite(
        panel,
        scenarios=["full_control", "sector_shuffle"],
        target_horizon=3,
        eval_years=[2020],
        seeds=[42],
        feature_configs=[
            "no_relation_features",
            "base_plus_target_aligned_lifts",
            "shuffled_target_aligned_lifts",
        ],
        max_epochs=10,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert not summary.empty
    assert set(predictions["claim_status"]) == {CLAIM_STATUS}
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert set(summary["falsification_scenario"]) == {"full_control", "sector_shuffle"}
    assert "recommendation" not in {col.lower() for col in predictions.columns}
