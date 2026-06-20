"""Tests for the fixed causal Phase 4Q Spatial-Durbin diagnostic."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hpc.phase4.run_phase4q_italy_spatial_durbin import (
    SPATIAL_FEATURES,
    add_spatial_durbin_features,
    select_alpha,
)


def test_spatial_block_uses_declared_causal_columns() -> None:
    panel = pd.DataFrame(
        {
            "region_id": ["A", "B"],
            "year": [2012, 2012],
            "lag1_births": [10.0, 20.0],
            "growth_1y": [1.0, 2.0],
            "growth_2y": [3.0, 4.0],
            "stock_lag1": [100.0, 200.0],
            "target_births": [9999.0, 8888.0],
        }
    )
    W = np.array([[0.0, 1.0], [1.0, 0.0]])
    result = add_spatial_durbin_features(panel, W, ["A", "B"]).set_index(
        "region_id"
    )
    assert result.loc["A", list(SPATIAL_FEATURES)].tolist() == [
        20.0,
        2.0,
        4.0,
        200.0,
    ]
    assert result.loc["B", list(SPATIAL_FEATURES)].tolist() == [
        10.0,
        1.0,
        3.0,
        100.0,
    ]


def test_spatial_block_does_not_use_current_target() -> None:
    panel = pd.DataFrame(
        {
            "region_id": ["A", "B"],
            "year": [2012, 2012],
            "lag1_births": [10.0, 20.0],
            "growth_1y": [1.0, 2.0],
            "growth_2y": [3.0, 4.0],
            "stock_lag1": [100.0, 200.0],
            "target_births": [30.0, 40.0],
        }
    )
    W = np.array([[0.0, 1.0], [1.0, 0.0]])
    before = add_spatial_durbin_features(panel, W, ["A", "B"])
    panel["target_births"] = [3_000_000.0, 4_000_000.0]
    after = add_spatial_durbin_features(panel, W, ["A", "B"])
    assert np.allclose(before[list(SPATIAL_FEATURES)], after[list(SPATIAL_FEATURES)])


def test_alpha_selection_ignores_outer_year_target() -> None:
    rows = []
    for region_idx, region_id in enumerate(("A", "B", "C")):
        for year in range(2008, 2013):
            lag1 = 100.0 + region_idx * 10 + year - 2008
            rows.append(
                {
                    "region_id": region_id,
                    "year": year,
                    "lag1_births": lag1,
                    "lag2_births": lag1 - 1,
                    "lag3_births": lag1 - 2,
                    "growth_1y": 0.01,
                    "growth_2y": 0.02,
                    "stock_lag1": lag1 * 5,
                    "target_births": lag1 + 2,
                    **{feature: lag1 for feature in SPATIAL_FEATURES},
                }
            )
    panel = pd.DataFrame(rows)
    before = select_alpha(panel, 2012, use_spatial_block=True)
    panel.loc[panel["year"].eq(2012), "target_births"] = 1_000_000.0
    after = select_alpha(panel, 2012, use_spatial_block=True)
    assert before == after
