import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_context_conditioned_sector_relation_gate import (
    COMMON_FEATURES,
    RELATION_FEATURES,
    VIEW_NAMES,
    assign_ze_folds,
    audit_gate,
    build_pair_samples,
    shuffle_context,
    shuffle_source,
    shuffle_training_target,
)


def _frame() -> pd.DataFrame:
    rows = []
    for year in [2020, 2021]:
        for ze_index, ze in enumerate(["0001", "0002", "0003"]):
            for source in ["BE", "FZ"]:
                rows.append(
                    {
                        "ze2020": ze,
                        "year": year,
                        "source_sector": source,
                        "target_sector": "GI",
                        "source_growth_lag_1": ze_index + year / 10000,
                        "source_growth_lag_2": ze_index + 0.1,
                        "source_share_lag_1": ze_index + 0.2,
                        "source_national_growth_lag_1": ze_index + 0.3,
                        "dominant_sector_lag_1": "GI",
                        "dominant_sector_share_lag_1": ze_index + 0.4,
                        "sector_diversity_lag_1": ze_index + 0.5,
                        "sector_concentration_hhi_lag_1": ze_index + 0.6,
                        "commerce_share_lag_1": ze_index + 0.7,
                        "construction_share_lag_1": ze_index + 0.8,
                        "target_growth": ze_index + year / 1000,
                    }
                )
    return pd.DataFrame(rows)


def test_fold_assignment_is_deterministic_and_complete() -> None:
    zones = pd.Series([f"{value:04d}" for value in range(20)])
    first = assign_ze_folds(zones)
    second = assign_ze_folds(zones)
    assert first == second
    assert set(first.values()) == set(range(5))


def test_source_shuffle_preserves_keys_and_changes_source_block() -> None:
    frame = _frame()
    shuffled = shuffle_source(frame, seed=42)
    keys = ["ze2020", "year", "source_sector", "target_sector"]
    assert shuffled[keys].equals(frame[keys])
    assert not shuffled["source_growth_lag_1"].equals(frame["source_growth_lag_1"])


def test_context_shuffle_preserves_relation_and_changes_context() -> None:
    frame = _frame()
    shuffled = shuffle_context(frame, seed=43)
    assert shuffled["source_growth_lag_1"].equals(frame["source_growth_lag_1"])
    assert not shuffled["sector_diversity_lag_1"].equals(
        frame["sector_diversity_lag_1"]
    )


def test_target_shuffle_is_coherent_across_source_pairs() -> None:
    shuffled = shuffle_training_target(_frame(), seed=44)
    counts = shuffled.groupby(["ze2020", "year", "target_sector"])[
        "target_growth"
    ].nunique()
    assert counts.eq(1).all()


def test_gate_requires_every_registered_control() -> None:
    control_mae = {
        "no_source_mlp": 1.1,
        "pooled_linear_relation": 1.1,
        "context_conditioned_mlp": 1.0,
        "source_shuffled_mlp": 1.2,
        "context_shuffled_mlp": 1.2,
        "target_shuffled_mlp": 1.2,
    }
    rows = []
    for fold in range(5):
        for view in VIEW_NAMES:
            rows.append(
                {
                    "view": view,
                    "seed": 42,
                    "eval_year": 2022,
                    "ze_fold": fold,
                    "mae": control_mae[view],
                    "r2": 0.1,
                    "n_test": 100,
                    "train_test_ze_overlap": 0,
                    "model_converged": 1,
                }
            )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is True


def test_target_shuffle_nonconvergence_is_recorded_but_does_not_block_gate() -> None:
    control_mae = {
        "no_source_mlp": 1.1,
        "pooled_linear_relation": 1.1,
        "context_conditioned_mlp": 1.0,
        "source_shuffled_mlp": 1.2,
        "context_shuffled_mlp": 1.2,
        "target_shuffled_mlp": 1.2,
    }
    rows = []
    for fold in range(5):
        for view in VIEW_NAMES:
            rows.append(
                {
                    "view": view,
                    "seed": 42,
                    "eval_year": 2022,
                    "ze_fold": fold,
                    "mae": control_mae[view],
                    "r2": 0.1,
                    "n_test": 100,
                    "train_test_ze_overlap": 0,
                    "model_converged": int(view != "target_shuffled_mlp"),
                }
            )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is True
    assert gate["integrity"]["all_primary_models_converged"] is True
    assert gate["integrity"]["target_shuffle_convergence_recorded"] is True


def test_primary_model_nonconvergence_blocks_gate() -> None:
    control_mae = {
        "no_source_mlp": 1.1,
        "pooled_linear_relation": 1.1,
        "context_conditioned_mlp": 1.0,
        "source_shuffled_mlp": 1.2,
        "context_shuffled_mlp": 1.2,
        "target_shuffled_mlp": 1.2,
    }
    rows = []
    for fold in range(5):
        for view in VIEW_NAMES:
            rows.append(
                {
                    "view": view,
                    "seed": 42,
                    "eval_year": 2022,
                    "ze_fold": fold,
                    "mae": control_mae[view],
                    "r2": 0.1,
                    "n_test": 100,
                    "train_test_ze_overlap": 0,
                    "model_converged": int(view != "context_conditioned_mlp"),
                }
            )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is False
    assert gate["integrity"]["all_primary_models_converged"] is False


def test_target_year_observation_changes_label_not_features() -> None:
    sectors = ["BE", "FZ", "GI"]
    panel_rows = []
    feature_rows = []
    for ze_index, ze in enumerate(["0001", "0002"]):
        for year in range(2012, 2017):
            for sector_index, sector in enumerate(sectors):
                count = 100 + ze_index * 10 + sector_index * 5 + (year - 2012) * 2
                panel_rows.append(
                    {
                        "ze2020": ze,
                        "year": year,
                        "sector_code": sector,
                        "sector_establishment_creations": float(count),
                    }
                )
                feature_rows.append(
                    {
                        "ze2020": ze,
                        "year": year,
                        "sector_code": sector,
                        "sector_share_lag_1": 0.2 + sector_index * 0.01,
                        "sector_growth_lag_1": 0.02 + sector_index * 0.01,
                        "sector_growth_lag_2": 0.01 + sector_index * 0.01,
                        "dominant_sector_lag_1": "GI",
                        "dominant_sector_share_lag_1": 0.4,
                        "sector_diversity_lag_1": 0.8,
                        "sector_concentration_hhi_lag_1": 0.2,
                        "commerce_share_lag_1": 0.3,
                        "construction_share_lag_1": 0.2,
                        "national_sector_growth_lag_1": 0.03,
                    }
                )
    panel = pd.DataFrame(panel_rows)
    features = pd.DataFrame(feature_rows)
    original = build_pair_samples(panel, features)
    mutated_panel = panel.copy()
    mask = (
        (mutated_panel["ze2020"] == "0001")
        & (mutated_panel["year"] == 2016)
        & (mutated_panel["sector_code"] == "GI")
    )
    mutated_panel.loc[mask, "sector_establishment_creations"] += 1000
    mutated = build_pair_samples(mutated_panel, features)
    key = ["ze2020", "year", "source_sector", "target_sector"]
    left = original[(original["year"] == 2016) & (original["target_sector"] == "GI")]
    right = mutated[(mutated["year"] == 2016) & (mutated["target_sector"] == "GI")]
    left = left.sort_values(key).reset_index(drop=True)
    right = right.sort_values(key).reset_index(drop=True)
    assert left[[*COMMON_FEATURES, *RELATION_FEATURES]].equals(
        right[[*COMMON_FEATURES, *RELATION_FEATURES]]
    )
    assert not left["target_growth"].equals(right["target_growth"])
