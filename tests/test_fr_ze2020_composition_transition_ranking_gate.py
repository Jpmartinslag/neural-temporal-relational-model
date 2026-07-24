import numpy as np
import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_composition_transition_ranking_gate import (
    EVAL_YEARS,
    SEEDS,
    VIEWS,
    audit_gate,
    build_transition_samples,
    shuffle_sector_identity,
    shuffle_temporal_profiles,
    shuffle_training_target,
    transition_metrics,
)
from src.modeles.france_ze2020.run_fr_ze2020_temporal_bipartite_reconstruction_gate import (
    FOLDS,
    SECTORS,
)


def _shares() -> pd.DataFrame:
    rows = []
    for zone_index in range(10):
        zone = f"{zone_index:04d}"
        for year in range(2012, 2022):
            values = np.arange(1, 10, dtype=float) + zone_index
            values[(year + zone_index) % 9] += year - 2011
            values /= values.sum()
            for sector, value in zip(SECTORS, values):
                rows.append((zone, year, sector, value))
    frame = pd.DataFrame(rows, columns=["ze2020", "year", "sector_code", "share"])
    return frame.pivot(index=["ze2020", "year"], columns="sector_code", values="share").reindex(columns=SECTORS)


def test_transition_target_uses_next_year_and_complete_groups() -> None:
    shares = _shares()
    samples = build_transition_samples(shares, ["0000", "0001"], [2018, 2019])
    assert samples.groupby("group_id").size().eq(9).all()
    assert samples.groupby("group_id")["target_top3_change"].sum().eq(3).all()
    row = samples[(samples.ze2020 == "0000") & (samples.decision_year == 2018) & (samples.sector_code == "GI")].iloc[0]
    expected = shares.loc[("0000", 2019), "GI"] - shares.loc[("0000", 2018), "GI"]
    assert row.target_change == expected


def test_future_mutation_does_not_change_earlier_features() -> None:
    shares = _shares()
    original = build_transition_samples(shares, ["0000"], [2018])
    mutated = shares.copy()
    mutated.loc[("0000", 2019), "GI"] += 1
    changed = build_transition_samples(mutated, ["0000"], [2018])
    feature_columns = [column for column in original if column.startswith(("current_", "lag_", "delta_"))]
    pd.testing.assert_frame_equal(original[feature_columns], changed[feature_columns])
    assert not original["target_change"].equals(changed["target_change"])


def test_shuffles_preserve_keys_and_change_intended_blocks() -> None:
    samples = build_transition_samples(_shares(), [f"{i:04d}" for i in range(10)], [2018, 2019])
    sector = shuffle_sector_identity(samples, 42)
    temporal = shuffle_temporal_profiles(samples, 42)
    target = shuffle_training_target(samples, 42)
    keys = ["ze2020", "decision_year", "sector_code"]
    assert samples[keys].equals(sector[keys])
    assert samples[keys].equals(temporal[keys])
    assert samples[keys].equals(target[keys])
    assert not samples.filter(like="current_").equals(sector.filter(like="current_"))
    assert not samples.filter(like="lag_").equals(temporal.filter(like="lag_"))
    assert not samples.target_change.equals(target.target_change)


def test_transition_metrics_reward_correct_ranking_and_sign() -> None:
    samples = build_transition_samples(_shares(), ["0000", "0001"], [2018])
    perfect = transition_metrics(samples, samples.target_change.to_numpy())
    assert perfect["ndcg_at_3"] == 1.0
    assert perfect["precision_at_3"] == 1.0
    assert perfect["top3_sign_accuracy"] == 1.0
    assert perfect["signed_mae"] == 0.0


def _synthetic_metrics(full_score: float = 0.8) -> pd.DataFrame:
    scores = {
        "mlp_joint": full_score,
        "past_delta": 0.65,
        "ridge_joint": 0.68,
        "mlp_target_history_only": 0.66,
        "mlp_current_only": 0.67,
        "mlp_sector_shuffle": 0.60,
        "mlp_temporal_shuffle": 0.58,
        "mlp_target_shuffle": 0.40,
        "zero_change": 0.35,
        "random_ranking": 0.30,
    }
    rows = []
    for seed in SEEDS:
        for year in EVAL_YEARS:
            for fold in FOLDS:
                for view in VIEWS:
                    rows.append(
                        {
                            "view": view,
                            "seed": seed,
                            "eval_year": year,
                            "ze_fold": fold,
                            "ndcg_at_3": scores[view],
                            "precision_at_3": 0.8,
                            "hit_rate_at_3": 1.0,
                            "signed_mae": 0.01,
                            "top3_signed_mae": 0.01,
                            "top3_sign_accuracy": 0.8 if view == "mlp_joint" else 0.6,
                            "n_test": 504,
                            "n_test_groups": 56,
                            "n_test_top3": 168,
                            "target_key_sha256": f"{seed}-{year}-{fold}",
                            "train_test_ze_overlap": 0,
                            "max_training_decision_year": year - 1,
                        }
                    )
    return pd.DataFrame(rows)


def test_registered_gate_can_pass_complete_synthetic_metrics() -> None:
    gate = audit_gate(_synthetic_metrics())
    assert gate["gate_pass"] is True
    assert gate["years_beating_all_controls"] == 8


def test_incomplete_configuration_cannot_pass() -> None:
    metrics = _synthetic_metrics()
    gate = audit_gate(metrics[metrics.seed == 42])
    assert gate["gate_pass"] is False
    assert gate["integrity"]["registered_seeds"] is False
