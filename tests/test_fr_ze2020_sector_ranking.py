from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_sector_ranking_panel import (
    FEATURE_COLUMNS,
    OUT_PATH,
    build_sector_ranking_panel,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (
    run_sector_ranking,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_sector_ranking_panel.py"
TRAIN_SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/train_fr_ze2020_sector_ranking.py"

FORBIDDEN_TERMS = [
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
]


def test_sector_ranking_panel_exists_and_schema():
    df = pd.read_csv(OUT_PATH, dtype={"ze2020": str})
    expected = {
        "ze2020",
        "sector_code",
        "decision_year",
        "future_growth_1y",
        "future_growth_3y",
        "future_top3_growth_3y_label",
        "ranking_feature_complete",
        "claim_status",
        *FEATURE_COLUMNS,
    }
    assert expected.issubset(df.columns)
    assert len(df) == 280 * 9 * 14
    assert df["ze2020"].str.len().eq(4).all()
    assert df["sector_code"].nunique() == 9


def test_sector_ranking_panel_is_deterministic():
    disk = pd.read_csv(OUT_PATH, dtype={"ze2020": str}).sort_index(axis=1)
    rebuilt = build_sector_ranking_panel().sort_index(axis=1)
    pd.testing.assert_frame_equal(disk, rebuilt, check_dtype=False)


def test_decision_year_features_use_current_or_past_not_future():
    df = pd.read_csv(OUT_PATH, dtype={"ze2020": str})
    row = df[(df["ze2020"] == "0051") & (df["sector_code"] == "GI") & (df["decision_year"] == 2015)].iloc[0]
    sector = pd.read_csv(
        REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv",
        dtype={"ze2020": str},
    )
    current = sector[
        (sector["ze2020"] == "0051") & (sector["sector_code"] == "GI") & (sector["year"] == 2015)
    ].iloc[0]
    future = sector[
        (sector["ze2020"] == "0051") & (sector["sector_code"] == "GI") & (sector["year"] == 2018)
    ].iloc[0]
    expected_growth = (
        future["sector_establishment_creations"] - current["sector_establishment_creations"]
    ) / current["sector_establishment_creations"]
    assert row["sector_count_t"] == current["sector_establishment_creations"]
    assert row["sector_share_t"] == current["sector_share"]
    assert np.isclose(row["future_growth_3y"], expected_growth)


def test_ranking_panel_claim_status_and_forbidden_columns():
    df = pd.read_csv(OUT_PATH, dtype={"ze2020": str})
    assert set(df["claim_status"]) == {"ranking_panel_exploratory_not_recommendation"}
    lowered_cols = {c.lower() for c in df.columns}
    for term in FORBIDDEN_TERMS[3:]:
        assert term not in lowered_cols


def test_scripts_do_not_read_forbidden_legacy_inputs_in_executable_code():
    for path in [SCRIPT_PATH, TRAIN_SCRIPT_PATH]:
        source_lines = path.read_text().splitlines()
        read_lines = [line for line in source_lines if "read_csv" in line or "Path(" in line or " / " in line]
        code_only = "\n".join(read_lines)
        for term in FORBIDDEN_TERMS[:3]:
            assert term not in code_only


def test_sector_ranking_training_smoke_outputs_metrics():
    panel = pd.read_csv(OUT_PATH, dtype={"ze2020": str})
    predictions, metrics = run_sector_ranking(
        panel,
        eval_years=[2019],
        k=3,
        min_train_years=3,
        seed=42,
        max_epochs=40,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert {"random", "past_volume", "ridge_ranking", "mlp_temporal_relational"}.issubset(
        set(metrics["model"])
    )
    assert metrics["ndcg_at_k"].between(0, 1).all()
    assert set(metrics["claim_status"]) == {"sector_ranking_exploratory_not_recommendation"}
    assert "recommendation" not in {c.lower() for c in predictions.columns}


def test_sector_ranking_supports_one_year_target_for_longer_window():
    panel = pd.read_csv(OUT_PATH, dtype={"ze2020": str})
    predictions, metrics = run_sector_ranking(
        panel,
        eval_years=[2023, 2024],
        k=3,
        min_train_years=3,
        seed=42,
        max_epochs=30,
        target_horizon=1,
    )
    assert not predictions.empty
    assert not metrics.empty
    assert set(predictions["target_horizon_years"]) == {1}
    assert set(metrics["target_horizon_years"]) == {1}
    assert set(metrics["eval_year"]) == {2023, 2024}
    assert {"target_growth", "target_top3_label"}.issubset(predictions.columns)
    assert predictions["target_top3_label"].isin([0, 1]).all()
    assert metrics["ndcg_at_k"].between(0, 1).all()
