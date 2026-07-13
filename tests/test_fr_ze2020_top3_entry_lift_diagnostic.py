from pathlib import Path

import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_lift_diagnostic import (
    CLAIM_STATUS,
    FEATURE_CONFIGS,
    _shuffle_lift_columns,
    add_target_aligned_relation_lifts,
    relation_lift_columns,
    run_top3_entry_lift_diagnostic,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import load_ranking_panel

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_diagnostic.py"
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"


def _toy_lift_panel() -> pd.DataFrame:
    rows = []
    for year in [2017, 2018, 2019, 2020, 2021, 2022]:
        for sector, rank, rel_count, future_growth in [
            ("A", 1, 0, 0.1),
            ("B", 2, 0, 0.2),
            ("C", 4, 2, 0.9),
            ("D", 5, 2, 0.8),
        ]:
            rows.append(
                {
                    "ze2020": "51",
                    "ze2020_label": "Toy",
                    "sector_code": sector,
                    "sector_label": sector,
                    "decision_year": year,
                    "sector_rank_in_ze_year_t": rank,
                    "future_growth_3y": future_growth,
                    "mask_future_growth_3y_available": 1,
                    "ranking_feature_complete": 1,
                    "relation_count_to_t": rel_count,
                    "relation_signal_strength_max_to_t": 0.6 if rel_count else 0.0,
                    "relation_stability_mean_to_t": 0.7 if rel_count else 0.0,
                }
            )
    return pd.DataFrame(rows)


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


def test_feature_configs_and_lift_columns_are_explicit():
    assert set(FEATURE_CONFIGS) == {
        "no_relation_features",
        "base_formula_features",
        "target_aligned_lift_features",
        "base_plus_target_aligned_lifts",
        "shuffled_target_aligned_lifts",
    }
    cols = relation_lift_columns()
    assert len(cols) == 12
    assert all(col.startswith("relation_") for col in cols)
    assert all(col.endswith(("_entry_lift_prior", "_entry_rate_prior", "_entry_rows_prior")) for col in cols)


def test_relation_lifts_use_only_mature_prior_labels():
    panel = _toy_lift_panel()
    lifted = add_target_aligned_relation_lifts(panel, target_horizon=3)
    first_year = lifted[lifted["decision_year"] == 2017]
    assert set(first_year["relation_count_bin_entry_lift_prior"]) == {1.0}

    year_2020 = lifted[lifted["decision_year"] == 2020]
    high_bin = year_2020[year_2020["relation_count_bin"] == 2]
    low_bin = year_2020[year_2020["relation_count_bin"] == 0]
    assert set(high_bin["relation_count_bin_entry_rate_prior"]) == {1.0}
    assert set(low_bin["relation_count_bin_entry_rate_prior"]) == {0.0}

    mutated = panel.copy()
    mutated.loc[mutated["decision_year"] == 2019, "future_growth_3y"] = [-10.0, -9.0, -8.0, -7.0]
    lifted_mutated = add_target_aligned_relation_lifts(mutated, target_horizon=3)
    compare_cols = ["sector_code", "relation_count_bin_entry_lift_prior"]
    pd.testing.assert_frame_equal(
        lifted.loc[lifted["decision_year"] == 2021, compare_cols].reset_index(drop=True),
        lifted_mutated.loc[lifted_mutated["decision_year"] == 2021, compare_cols].reset_index(drop=True),
    )


def test_shuffle_lift_columns_preserves_year_distribution():
    panel = add_target_aligned_relation_lifts(_toy_lift_panel(), target_horizon=3)
    shuffled = _shuffle_lift_columns(panel, seed=42)
    for col in relation_lift_columns():
        for year, group in panel.groupby("decision_year"):
            original = sorted(group[col].tolist())
            changed = sorted(shuffled[shuffled["decision_year"] == year][col].tolist())
            assert changed == original


def test_real_panel_lift_diagnostic_smoke_if_available():
    if not PANEL_PATH.exists():
        return
    panel = load_ranking_panel(PANEL_PATH)
    predictions, metrics, summary = run_top3_entry_lift_diagnostic(
        panel,
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
    assert set(summary["feature_config"]) == {
        "no_relation_features",
        "base_plus_target_aligned_lifts",
        "shuffled_target_aligned_lifts",
    }
    assert "recommendation" not in {col.lower() for col in predictions.columns}
