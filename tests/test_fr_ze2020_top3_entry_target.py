from pathlib import Path

import pandas as pd

from src.modeles.france_ze2020.audit_fr_ze2020_top3_entry_target import (
    CLAIM_STATUS,
    add_top3_entry_labels,
    summarize_top3_entry_target,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py"
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"


def _toy_panel() -> pd.DataFrame:
    rows = []
    sectors = ["A", "B", "C", "D"]
    current_ranks = {"A": 1, "B": 2, "C": 4, "D": 5}
    future_1y = {"A": 0.1, "B": 0.2, "C": 0.9, "D": 0.8}
    future_3y = {"A": 0.1, "B": 0.2, "C": 0.9, "D": 0.8}
    for sector in sectors:
        rows.append(
            {
                "ze2020": "51",
                "sector_code": sector,
                "decision_year": 2020,
                "sector_rank_in_ze_year_t": current_ranks[sector],
                "future_growth_1y": future_1y[sector],
                "future_growth_3y": future_3y[sector],
                "mask_future_growth_1y_available": 1,
                "mask_future_growth_3y_available": 1,
                "ranking_feature_complete": 1,
            }
        )
    rows.append(
        {
            "ze2020": "51",
            "sector_code": "E",
            "decision_year": 2020,
            "sector_rank_in_ze_year_t": 6,
            "future_growth_1y": float("nan"),
            "future_growth_3y": float("nan"),
            "mask_future_growth_1y_available": 0,
            "mask_future_growth_3y_available": 0,
            "ranking_feature_complete": 1,
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


def test_add_top3_entry_labels_zero_pads_ze2020_and_marks_entry():
    labelled = add_top3_entry_labels(_toy_panel(), horizons=[1, 3])
    assert set(labelled["ze2020"]) == {"0051"}
    c_row = labelled[labelled["sector_code"] == "C"].iloc[0]
    a_row = labelled[labelled["sector_code"] == "A"].iloc[0]
    e_row = labelled[labelled["sector_code"] == "E"].iloc[0]
    assert c_row["future_top3_growth_1y_label"] == 1
    assert c_row["future_top3_entry_1y_label"] == 1
    assert a_row["future_top3_growth_1y_label"] == 0
    assert a_row["future_top3_entry_1y_label"] == 0
    assert e_row["future_top3_entry_1y_label"] == 0


def test_summarize_top3_entry_target_counts_only_available_targets():
    summary, by_year = summarize_top3_entry_target(_toy_panel(), horizons=[1, 3])
    assert set(summary["claim_status"]) == {CLAIM_STATUS}
    assert set(by_year["claim_status"]) == {CLAIM_STATUS}
    row = summary[summary["target_horizon_years"] == 1].iloc[0]
    assert row["eligible_rows"] == 4
    assert row["future_top3_positive_rows"] == 3
    assert row["future_top3_entry_positive_rows"] == 2
    assert row["eligible_decision_years"] == "2020"


def test_real_panel_preflight_if_available():
    if not PANEL_PATH.exists():
        return
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str, "sector_code": str})
    summary, by_year = summarize_top3_entry_target(panel)
    assert not summary.empty
    assert not by_year.empty
    assert set(summary["target_horizon_years"]) == {1, 3}
    assert (summary["future_top3_entry_positive_rows"] > 0).all()
    h3 = summary[summary["target_horizon_years"] == 3].iloc[0]
    assert h3["eligible_decision_year_end"] <= 2022
