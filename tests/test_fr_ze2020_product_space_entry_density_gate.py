import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_product_space_entry_density_gate import (
    VIEWS,
    assign_ze_folds,
    audit_gate,
    build_rca_states,
)


def test_fold_assignment_is_deterministic_and_balanced() -> None:
    zones = [f"{index:04d}" for index in range(20)]
    first = assign_ze_folds(zones)
    assert first == assign_ze_folds(zones)
    counts = pd.Series(first).value_counts().to_dict()
    assert counts == {0: 4, 1: 4, 2: 4, 3: 4, 4: 4}


def test_rca_state_uses_only_the_requested_year() -> None:
    rows = []
    for year in [2020, 2021]:
        for ze_index, ze in enumerate(["0001", "0002"]):
            for sector_index, sector in enumerate(
                ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
            ):
                rows.append(
                    {
                        "ze2020": ze,
                        "year": year,
                        "sector_code": sector,
                        "sector_establishment_creations": 10
                        + ze_index * sector_index
                        + sector_index,
                    }
                )
    panel = pd.DataFrame(rows)
    original = build_rca_states(panel)
    mutated = panel.copy()
    mutated.loc[
        (mutated["year"] == 2021)
        & (mutated["ze2020"] == "0001")
        & (mutated["sector_code"] == "GI"),
        "sector_establishment_creations",
    ] += 1000
    changed = build_rca_states(mutated)
    assert original[2020]["rca"].equals(changed[2020]["rca"])
    assert not original[2021]["rca"].equals(changed[2021]["rca"])


def test_gate_requires_semantic_controls_and_year_recurrence() -> None:
    scores = {
        "product_space_density": 0.70,
        "target_prevalence": 0.60,
        "target_rca": 0.61,
        "randomized_product_space": 0.55,
        "sector_shuffled_density": 0.56,
        "target_shuffled_density": 0.40,
        "random_score": 0.35,
    }
    rows = []
    for seed in [42, 43, 44, 45, 46]:
        for year in range(2012, 2025):
            for fold in range(5):
                for view in VIEWS:
                    rows.append(
                        {
                            "view": view,
                            "seed": seed,
                            "eval_year": year,
                            "ze_fold": fold,
                            "ndcg_at_3": scores[view],
                            "precision_at_3": 0.5,
                            "hit_rate_at_3": 0.8,
                            "average_precision": 0.6,
                            "candidate_key_sha256": f"{seed}-{year}-{fold}",
                            "train_test_ze_overlap": 0,
                        }
                    )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is True
    assert gate["years_beating_both_marginals"] == 13


def test_missing_view_blocks_gate() -> None:
    rows = []
    for seed in [42, 43, 44, 45, 46]:
        for year in range(2012, 2025):
            for fold in range(5):
                for view in VIEWS[:-1]:
                    rows.append(
                        {
                            "view": view,
                            "seed": seed,
                            "eval_year": year,
                            "ze_fold": fold,
                            "ndcg_at_3": 0.7 if view == "product_space_density" else 0.5,
                            "precision_at_3": 0.5,
                            "hit_rate_at_3": 0.8,
                            "average_precision": 0.6,
                            "candidate_key_sha256": f"{seed}-{year}-{fold}",
                            "train_test_ze_overlap": 0,
                        }
                    )
    gate = audit_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is False
    assert gate["integrity"]["all_views_present"] is False
