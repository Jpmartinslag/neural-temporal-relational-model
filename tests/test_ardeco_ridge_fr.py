from __future__ import annotations

import numpy as np
import pandas as pd

from src.modeles.run_ardeco_ridge_fr import (
    SECTOR_MAP,
    build_model_table,
    family_columns,
    fit_predict_fold,
    prepare_ardeco,
    summarize_candidate,
    temporally_permute_ardeco,
    wmape,
)


def _panel() -> pd.DataFrame:
    rows = []
    for region_idx, region in enumerate(("FR101", "FR102")):
        values = {year: 100 + 10 * region_idx + 3 * (year - 2012)
                  for year in range(2012, 2026)}
        for year in range(2012, 2026):
            rows.append(
                {
                    "region_id": region,
                    "year": year,
                    "target_births": values[year],
                    "lag1_births": values.get(year - 1, np.nan),
                    "lag2_births": values.get(year - 2, np.nan),
                }
            )
    return pd.DataFrame(rows)


def _ardeco() -> pd.DataFrame:
    rows = []
    for region_idx, region in enumerate(("FR101", "FR102")):
        for year in range(2012, 2025):
            for sector_idx, sector in enumerate(SECTOR_MAP):
                rows.append(
                    {
                        "COUNTRY_REQUEST": "FR",
                        "TERRITORY_ID": region,
                        "YEAR": year,
                        "SECTOR": sector,
                        "VALUE": 10 + region_idx + sector_idx + 0.2 * (year - 2012),
                    }
                )
    return pd.DataFrame(rows)


def test_wmape() -> None:
    assert wmape(np.array([10.0, 20.0]), np.array([9.0, 22.0])) == 0.1


def test_prepare_ardeco_feature_shapes() -> None:
    prepared = prepare_ardeco(_ardeco())
    assert len(prepared) == 2 * 13
    assert len(family_columns("level")) == 9
    assert len(family_columns("growth")) == 9
    assert len(family_columns("share")) == 9
    assert len(family_columns("joint")) == 27
    assert prepared[family_columns("level")].notna().all().all()
    first_year = prepared["source_year"].eq(2012)
    assert prepared.loc[first_year, family_columns("growth")].isna().all().all()


def test_model_table_uses_t_minus_1_only() -> None:
    table = build_model_table(_panel(), prepare_ardeco(_ardeco()))
    assert (table["source_year"] == table["year"] - 1).all()
    assert table["ardeco_observation_before_target"].all()


def test_temporal_permutation_is_causal_and_changes_alignment() -> None:
    table = build_model_table(_panel(), prepare_ardeco(_ardeco()))
    original = table[family_columns("level")].copy()
    permuted = temporally_permute_ardeco(
        table, eval_year=2021, family="level",
        rng=np.random.default_rng(42),
    )
    eligible = permuted["source_year"] < 2021
    assert not np.allclose(
        original.loc[eligible].to_numpy(),
        permuted.loc[eligible, family_columns("level")].to_numpy(),
    )
    assert (permuted.loc[eligible, "source_year"] < 2021).all()
    # The target-year row remains complete: it cannot be mapped to 2011,
    # before the local ARDECO history starts.
    assert permuted.loc[
        permuted["year"].eq(2021), family_columns("level")
    ].notna().all().all()


def test_fit_predict_fold_is_strictly_causal() -> None:
    table = build_model_table(_panel(), prepare_ardeco(_ardeco()))
    result = fit_predict_fold(table, eval_year=2021, family="joint")
    assert result["leakage_ok"]
    assert result["train_max_year"] == 2020
    assert result["ardeco_max_source_year"] == 2019
    assert result["n_test"] == 2


def test_summarize_candidate_fail_closed() -> None:
    baseline = [
        {"wmape": 0.10, "leakage_ok": True},
        {"wmape": 0.10, "leakage_ok": True},
        {"wmape": 0.10, "leakage_ok": True},
        {"wmape": 0.10, "leakage_ok": True},
        {"wmape": 0.10, "leakage_ok": True},
    ]
    observed = [
        {"wmape": 0.095, "leakage_ok": True},
        {"wmape": 0.095, "leakage_ok": True},
        {"wmape": 0.095, "leakage_ok": True},
        {"wmape": 0.11, "leakage_ok": True},
        {"wmape": 0.11, "leakage_ok": True},
    ]
    result = summarize_candidate("level", observed, baseline, [0.09] * 99)
    assert result["decision"] == "FAIL"
    assert not result["checks"]["beats_temporal_permutations_p_le_005"]
