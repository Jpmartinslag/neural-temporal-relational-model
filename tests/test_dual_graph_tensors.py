from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.build_dual_graph_tensors import (
    FEATURE_NAMES,
    _fit_scale,
    build_fold,
)


def _panel() -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(7)
    for region in ("R1", "R2", "R3"):
        for sector in ("BE", "FZ"):
            prior = 100.0
            for year in range(2012, 2023):
                births = prior * (1 + rng.normal(0.03, 0.04))
                rows.append({
                    "region_id": region,
                    "sector_a10": sector,
                    "country": "FR",
                    "observation_year": year,
                    "available_for_forecast_year": year + 1,
                    "sector_births": births,
                    "sector_growth_1y": np.nan if year == 2012 else births / prior - 1,
                    "sector_share": 0.3 if sector == "BE" else 0.7,
                    "mask_sector_supported": 1,
                })
                prior = births
    return pd.DataFrame(rows)


def _ardeco() -> pd.DataFrame:
    rows = []
    for region in ("R1", "R2", "R3"):
        for sector in ("BE", "FZ"):
            for year in range(2012, 2023):
                rows.append({
                    "region_id": region,
                    "observation_year": year,
                    "sector_a10": sector,
                    "log_employment": np.log1p(100 + year),
                    "employment_growth": 0.01,
                    "employment_share": 0.5,
                })
    return pd.DataFrame(rows)


def test_fit_scale_preserves_missing_mask():
    raw = np.array([[[[1.0, np.nan], [3.0, 2.0]]]])
    mask = np.isfinite(raw).astype(np.uint8)
    scaled, means, stds = _fit_scale(raw, mask)
    assert scaled[0, 0, 0, 1] == 0
    assert means.tolist() == [2.0, 2.0]
    assert np.isfinite(stds).all()


def test_build_fold_shapes_and_causality():
    arrays = build_fold(_panel(), _ardeco(), 2021)
    assert arrays["features_seq"].shape == (5, 5, 3, 2, len(FEATURE_NAMES))
    assert arrays["territory_adj_seq"].shape == (5, 5, 2, 3, 3)
    assert arrays["territory_adj_mask"].shape == (5, 5, 2)
    assert arrays["target_log_growth"].shape == (5, 3, 2)
    assert arrays["sample_years"].tolist() == [2017, 2018, 2019, 2020, 2021]
    assert arrays["observation_years"][-1].max() == 2020
    assert arrays["target_mask"][-1].sum() == 6


def test_build_fold_finite_observed_features():
    arrays = build_fold(_panel(), _ardeco(), 2021)
    observed = arrays["feature_mask_seq"].astype(bool)
    assert np.isfinite(arrays["features_seq"][observed]).all()


def test_adjacency_mask_matches_nonzero_edges():
    arrays = build_fold(_panel(), _ardeco(), 2021)
    expected = (arrays["territory_adj_seq"].sum(axis=(-1, -2)) > 0).astype(np.uint8)
    assert np.array_equal(arrays["territory_adj_mask"], expected)


def test_build_fold_targets_and_labels_are_finite():
    arrays = build_fold(_panel(), _ardeco(), 2021)
    mask = arrays["target_mask"][-1].astype(bool)
    assert np.isfinite(arrays["target_log_growth"][-1][mask]).all()
    assert set(np.unique(arrays["target_regime"][-1][mask])).issubset({0, 1, 2})
    assert set(np.unique(arrays["target_recovery"][-1][mask])).issubset({0, 1})
    assert set(np.unique(arrays["target_emergence"][-1][mask])).issubset({0, 1})


def test_build_fold_deterministic():
    first = build_fold(_panel(), _ardeco(), 2021)
    second = build_fold(_panel(), _ardeco(), 2021)
    for key in first:
        if first[key].dtype.kind in "f":
            assert np.allclose(first[key], second[key], equal_nan=True)
        else:
            assert np.array_equal(first[key], second[key])


def test_no_target_year_changes_features():
    panel = _panel()
    first = build_fold(panel, _ardeco(), 2021)
    panel.loc[panel["observation_year"] == 2021, "sector_births"] *= 10
    second = build_fold(panel, _ardeco(), 2021)
    assert np.array_equal(first["features_seq"], second["features_seq"])


def test_missing_ardeco_is_masked_not_zero_observed():
    ardeco = _ardeco()
    ardeco = ardeco[~(
        (ardeco["region_id"] == "R1")
        & (ardeco["sector_a10"] == "BE")
        & (ardeco["observation_year"] == 2020)
    )]
    arrays = build_fold(_panel(), ardeco, 2021)
    assert arrays["feature_mask_seq"][-1, -1, 0, 0, 3:].sum() == 0
    assert np.all(arrays["features_seq"][-1, -1, 0, 0, 3:] == 0)


def test_scaling_fits_training_samples_only():
    panel = _panel()
    first = build_fold(panel, _ardeco(), 2021)
    panel.loc[panel["observation_year"] == 2021, "sector_births"] *= 100
    second = build_fold(panel, _ardeco(), 2021)
    assert np.array_equal(first["feature_means"], second["feature_means"])
    assert np.array_equal(first["feature_stds"], second["feature_stds"])
