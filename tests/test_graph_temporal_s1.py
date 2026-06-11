"""Unit tests for the pre-registered S1-FR runner."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.modeles.run_s1_fr_local import (
    _load_checkpoint_rows,
    _missing_years,
    paired_sign_flip_pvalue,
    permute_growth_source,
)


def _panel() -> pd.DataFrame:
    rows = []
    for year in range(2015, 2021):
        for region in ["R1", "R2", "R3"]:
            rows.append({
                "country": "FR",
                "sector_a10": "BE",
                "region_id": region,
                "observation_year": year,
                "sector_growth_1y": float(year + int(region[-1])),
            })
    return pd.DataFrame(rows)


def test_temporal_permutation_preserves_each_series_values():
    panel = _panel()
    permuted = permute_growth_source(panel, "FR", "temporal", 42)
    for region in ["R1", "R2", "R3"]:
        mask = panel["region_id"].eq(region)
        assert sorted(panel.loc[mask, "sector_growth_1y"]) == sorted(
            permuted.loc[mask, "sector_growth_1y"]
        )


def test_territory_permutation_preserves_each_year_values():
    panel = _panel()
    permuted = permute_growth_source(panel, "FR", "territory", 42)
    for year in range(2015, 2021):
        mask = panel["observation_year"].eq(year)
        assert sorted(panel.loc[mask, "sector_growth_1y"]) == sorted(
            permuted.loc[mask, "sector_growth_1y"]
        )


def test_permutation_is_deterministic():
    panel = _panel()
    a = permute_growth_source(panel, "FR", "temporal", 43)
    b = permute_growth_source(panel, "FR", "temporal", 43)
    pd.testing.assert_frame_equal(a, b)


def test_permutation_does_not_change_other_columns():
    panel = _panel()
    permuted = permute_growth_source(panel, "FR", "territory", 44)
    cols = [c for c in panel.columns if c != "sector_growth_1y"]
    pd.testing.assert_frame_equal(panel[cols], permuted[cols])


def test_sign_flip_detects_consistent_improvement():
    observed = np.full(25, 0.08)
    control = np.full(25, 0.10)
    p = paired_sign_flip_pvalue(observed, control, seed=42, n_permutations=999)
    assert p <= 0.05


def test_sign_flip_fails_when_control_is_better():
    observed = np.full(25, 0.10)
    control = np.full(25, 0.08)
    assert paired_sign_flip_pvalue(observed, control, seed=42, n_permutations=999) == 1.0


def test_missing_years_supports_resume():
    rows = [
        {"model_name": "GConvGRU", "seed": 42, "eval_year": 2021},
        {"model_name": "GConvGRU", "seed": 42, "eval_year": 2023},
    ]
    assert _missing_years(rows, "GConvGRU", 42) == [2022, 2024, 2025]


def test_load_checkpoint_rows(tmp_path):
    path = tmp_path / "checkpoint.json"
    path.write_text(
        '{"status":"RUNNING","rows":{"observed":[{"eval_year":2021}],'
        '"temporal_null":[],"territory_null":[],"covid_excluded":[]}}'
    )
    observed, temporal, territory, covid = _load_checkpoint_rows(path)
    assert observed == [{"eval_year": 2021}]
    assert temporal == territory == covid == []
