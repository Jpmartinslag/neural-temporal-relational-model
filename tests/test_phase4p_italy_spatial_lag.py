"""Tests for causal Italy-only Phase 4P diagnostic."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hpc.phase4.run_phase4p_italy_spatial_lag import (
    GRAPH_FEATURE,
    add_neighbour_lag1,
    decision_payload,
    select_alpha,
)
from hpc.phase4.run_phase4o_c_residual_spatial_diagnostic import (
    conjugation_permutation,
)


def test_neighbour_lag_uses_lag1_not_current_target() -> None:
    panel = pd.DataFrame(
        {
            "region_id": ["A", "B", "A", "B"],
            "year": [2011, 2011, 2012, 2012],
            "lag1_births": [1.0, 2.0, 10.0, 20.0],
            "target_births": [1000.0, 2000.0, 3000.0, 4000.0],
        }
    )
    W = np.array([[0.0, 1.0], [1.0, 0.0]])
    result = add_neighbour_lag1(panel, W, ["A", "B"])
    values = result[result["year"].eq(2012)].set_index("region_id")[GRAPH_FEATURE]
    assert values["A"] == 20.0
    assert values["B"] == 10.0


def test_neighbour_lag_rejects_incomplete_alignment() -> None:
    panel = pd.DataFrame(
        {"region_id": ["A"], "year": [2012], "lag1_births": [1.0]}
    )
    W = np.array([[0.0, 1.0], [1.0, 0.0]])
    try:
        add_neighbour_lag1(panel, W, ["A", "B"])
    except ValueError as exc:
        assert "alignment mismatch" in str(exc)
    else:
        raise AssertionError("Expected graph alignment failure")


def test_permuted_control_is_row_normalised_like_real_graph() -> None:
    W_raw = np.array(
        [
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
    )
    W_control = conjugation_permutation(W_raw, np.random.default_rng(42))
    assert np.allclose(W_control.sum(axis=1), 1.0)


def test_alpha_selection_does_not_use_outer_year_target() -> None:
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
                }
            )
    panel = pd.DataFrame(rows)
    alpha_before, candidates_before = select_alpha(panel, 2012, use_graph=False)
    panel.loc[panel["year"].eq(2012), "target_births"] = 1_000_000.0
    alpha_after, candidates_after = select_alpha(panel, 2012, use_graph=False)
    assert alpha_before == alpha_after
    assert candidates_before == candidates_after


def test_promotion_rejects_sub_one_percent_gain() -> None:
    summary = pd.DataFrame(
        [
            {
                "config": "p0_persistence",
                "graph_id": "none",
                "mean_yearly_wmape": 0.1000,
                "worst_year_wmape": 0.1500,
            },
            {
                "config": "p1_ridge_residual",
                "graph_id": "none",
                "mean_yearly_wmape": 0.1000,
                "worst_year_wmape": 0.1500,
            },
            {
                "config": "p2_real_graph",
                "graph_id": "real",
                "mean_yearly_wmape": 0.0995,
                "worst_year_wmape": 0.1500,
            },
        ]
        + [
            {
                "config": "p3_permuted_graph",
                "graph_id": f"perm_{idx:03d}",
                "mean_yearly_wmape": 0.1100,
                "worst_year_wmape": 0.1600,
            }
            for idx in range(99)
        ]
    )
    yearly = pd.DataFrame(
        [
            {
                "config": "p2_real_graph",
                "graph_id": "real",
                "year": year,
                "wmape": 0.0995,
            }
            for year in range(2012, 2021)
        ]
        + [
            {
                "config": "p3_permuted_graph",
                "graph_id": f"perm_{idx:03d}",
                "year": year,
                "wmape": 0.1100,
            }
            for idx in range(99)
            for year in range(2012, 2021)
        ]
    )
    decision = decision_payload(summary, yearly)
    assert decision["real_graph_gain_vs_persistence"] < 0.01
    assert decision["diagnostic_supports_spatial_feature"] is False
