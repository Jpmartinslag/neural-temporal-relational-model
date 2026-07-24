import numpy as np
import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_temporal_bipartite_reconstruction_gate import (
    FOLDS,
    SECTORS,
    VIEWS,
    assign_ze_folds,
    audit_gate,
    build_samples,
    project_hidden_predictions,
    shuffle_current_sector_identity,
    shuffle_lag_profiles,
)


def _shares() -> pd.DataFrame:
    rows = []
    for zone_index in range(10):
        zone = f"{zone_index:04d}"
        for year in [2019, 2020, 2021]:
            values = np.arange(1, 10, dtype=float) + zone_index + year % 3
            values /= values.sum()
            for sector, value in zip(SECTORS, values):
                rows.append((zone, year, sector, value))
    frame = pd.DataFrame(rows, columns=["ze2020", "year", "sector_code", "share"])
    return frame.pivot(index=["ze2020", "year"], columns="sector_code", values="share").reindex(columns=SECTORS)


def test_samples_hide_exactly_three_current_values() -> None:
    samples = build_samples(_shares(), ["0000", "0001"], [2020, 2021], seed=42)
    assert samples.groupby("group_id").size().eq(3).all()
    for _, row in samples.iterrows():
        sector = row["sector_code"]
        assert row[f"current_{sector}"] == 0
        assert row[f"visible_{sector}"] == 0
        assert row["remaining_mass"] > 0
    assert np.allclose(samples.groupby("group_id")["target_allocation"].sum(), 1.0)


def test_projection_preserves_hidden_mass() -> None:
    samples = build_samples(_shares(), ["0000", "0001"], [2020], seed=42)
    raw = np.linspace(-1, 1, len(samples))
    scored = project_hidden_predictions(samples, raw)
    predicted = scored.groupby("group_id")["predicted_share"].sum()
    expected = scored.groupby("group_id")["remaining_mass"].first()
    assert np.allclose(predicted, expected)
    assert scored["composition_error"].max() <= 1e-10


def test_shuffles_preserve_rows_but_change_feature_blocks() -> None:
    samples = build_samples(_shares(), [f"{index:04d}" for index in range(10)], [2020], seed=42)
    sector = shuffle_current_sector_identity(samples, 42)
    temporal = shuffle_lag_profiles(samples, 42)
    assert samples[["ze2020", "year", "sector_code"]].equals(
        sector[["ze2020", "year", "sector_code"]]
    )
    assert samples[["ze2020", "year", "sector_code"]].equals(
        temporal[["ze2020", "year", "sector_code"]]
    )
    assert not samples.filter(like="current_").equals(sector.filter(like="current_"))
    assert not samples.filter(like="lag_").equals(temporal.filter(like="lag_"))


def test_fold_assignment_is_deterministic_and_balanced() -> None:
    zones = [f"{index:04d}" for index in range(20)]
    mapping = assign_ze_folds(zones)
    assert mapping == assign_ze_folds(zones)
    assert pd.Series(mapping).value_counts().to_dict() == {fold: 4 for fold in FOLDS}


def test_registered_gate_can_pass_complete_synthetic_metrics() -> None:
    errors = {
        "mlp_bipartite": 0.05,
        "ridge_bipartite": 0.07,
        "temporal_persistence": 0.09,
        "sector_mean_closure": 0.10,
        "mlp_history_only": 0.08,
        "mlp_current_only": 0.08,
        "mlp_sector_shuffle": 0.09,
        "mlp_temporal_shuffle": 0.09,
        "random_closure": 0.15,
    }
    rows = []
    for seed in [42, 43, 44, 45, 46]:
        for year in range(2017, 2026):
            for fold in FOLDS:
                for view in VIEWS:
                    rows.append(
                        {
                            "view": view,
                            "seed": seed,
                            "eval_year": year,
                            "ze_fold": fold,
                            "masked_mae": errors[view],
                            "masked_rmse": errors[view],
                            "allocation_mae": errors[view],
                            "n_hidden_cells": 168,
                            "n_ze_year_groups": 56,
                            "max_composition_error": 0.0,
                            "target_key_sha256": f"{seed}-{year}-{fold}",
                            "train_test_ze_overlap": 0,
                        }
                    )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is True
    assert gate["years_beating_ridge_and_both_ablations"] == 9


def test_incomplete_configuration_cannot_pass() -> None:
    rows = []
    for view in VIEWS:
        rows.append(
            {
                "view": view,
                "seed": 42,
                "eval_year": 2025,
                "ze_fold": 0,
                "masked_mae": 0.05 if view == "mlp_bipartite" else 0.1,
                "masked_rmse": 0.1,
                "allocation_mae": 0.1,
                "n_hidden_cells": 168,
                "n_ze_year_groups": 56,
                "max_composition_error": 0.0,
                "target_key_sha256": "same",
                "train_test_ze_overlap": 0,
            }
        )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is False
    assert gate["integrity"]["full_configuration"] is False
