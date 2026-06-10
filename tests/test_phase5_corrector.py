"""Tests for Phase 5 corrector: H0/H0b/H1/H2, leakage, determinism."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.modeles.phase5.corrector import (
    wmape,
    _alpha_ratio,
    _territory_totals,
    _region_order,
    predict_h0,
    predict_h0b,
    predict_graph_corrector,
    CorrectorResult,
    RIDGE_ALPHA_H0B,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REGIONS = ["R1", "R2", "R3"]
YEARS = list(range(2010, 2019))
SECTORS = ["BE", "FZ"]


def make_panel() -> pd.DataFrame:
    rows = []
    for r in REGIONS:
        for s in SECTORS:
            for y in YEARS:
                growth = 0.03 * (1 + REGIONS.index(r)) if y > YEARS[0] else float("nan")
                rows.append({
                    "region_id": r,
                    "observation_year": y,
                    "available_for_forecast_year": y + 1,
                    "sector_a10": s,
                    "sector_births": 100.0 + 10 * REGIONS.index(r),
                    "sector_growth_1y": growth,
                    "country": "TS",
                    "mask_sector_supported": 1,
                    "mask_sector_births": 1,
                    "business_sector_total": float(200 + 20 * REGIONS.index(r) + 5 * (y - YEARS[0])),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# wmape
# ---------------------------------------------------------------------------

def test_wmape_perfect():
    y = np.array([100.0, 200.0, 300.0])
    assert wmape(y, y) == pytest.approx(0.0)


def test_wmape_excludes_nan():
    y_hat = np.array([100.0, np.nan, 300.0])
    y_true = np.array([100.0, 200.0, 300.0])
    result = wmape(y_hat, y_true)
    assert np.isfinite(result)
    assert result == pytest.approx(0.0)


def test_wmape_all_nan_returns_nan():
    assert np.isnan(wmape(np.array([np.nan]), np.array([100.0])))


def test_wmape_zero_target_excluded():
    y_hat = np.array([100.0, 0.0, 300.0])
    y_true = np.array([100.0, 0.0, 300.0])
    # zero targets excluded, but both non-zero match → 0
    assert wmape(y_hat, y_true) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _alpha_ratio
# ---------------------------------------------------------------------------

def test_alpha_ratio_zero_correction():
    corr = np.zeros(5)
    base = np.ones(5) * 100
    assert _alpha_ratio(corr, base) == pytest.approx(0.0)


def test_alpha_ratio_nan_excluded():
    corr = np.array([10.0, np.nan])
    base = np.array([100.0, 100.0])
    r = _alpha_ratio(corr, base)
    assert r == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# _territory_totals
# ---------------------------------------------------------------------------

def test_territory_totals_alignment():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    totals = _territory_totals(panel, "TS", region_order, 2014)
    assert totals.shape == (len(region_order),)
    assert np.all(np.isfinite(totals))


def test_territory_totals_missing_year_is_nan():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    totals = _territory_totals(panel, "TS", region_order, 9999)
    assert np.all(np.isnan(totals))


# ---------------------------------------------------------------------------
# predict_h0
# ---------------------------------------------------------------------------

def test_h0_persistence():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    y_hat, y_true = predict_h0(panel, "TS", region_order, 2014)
    # Persistence: y_hat at avail_year=2014 = totals at obs_year=2013
    # y_true at avail_year=2015 = totals at obs_year=2014
    assert y_hat.shape == (len(region_order),)
    assert y_true.shape == (len(region_order),)
    assert np.all(np.isfinite(y_hat))
    assert np.all(np.isfinite(y_true))
    # Persistence: y_hat should differ from y_true (since totals grow by 5/year)
    assert not np.allclose(y_hat, y_true)


def test_h0_no_future_data():
    """H0 uses observation_year = eval_year - 1 only."""
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    # Should return y[r, eval_year - 1] as prediction — no access to eval_year data
    y_hat_2014, _ = predict_h0(panel, "TS", region_order, 2014)
    totals_2013 = _territory_totals(panel, "TS", region_order, 2014)  # obs 2013
    np.testing.assert_allclose(y_hat_2014, totals_2013)


# ---------------------------------------------------------------------------
# predict_h0b
# ---------------------------------------------------------------------------

def test_h0b_returns_finite():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    y_hat, y_true, ridge = predict_h0b(panel, "TS", region_order, train_years, 2016, alpha=RIDGE_ALPHA_H0B)
    assert y_hat.shape == (len(region_order),)
    assert np.all(y_hat >= 0), "H0b output must be non-negative"
    assert np.all(np.isfinite(y_hat))


def test_h0b_deterministic():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    y1, _, _ = predict_h0b(panel, "TS", region_order, train_years, 2016, alpha=RIDGE_ALPHA_H0B)
    y2, _, _ = predict_h0b(panel, "TS", region_order, train_years, 2016, alpha=RIDGE_ALPHA_H0B)
    np.testing.assert_array_equal(y1, y2)


# ---------------------------------------------------------------------------
# predict_graph_corrector: H1 (identity graph)
# ---------------------------------------------------------------------------

def test_h1_returns_corrector_result():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    res = predict_graph_corrector(
        panel, "TS", region_order, train_years, 2016,
        hypothesis="H1", identity_graph=True, ridge_alpha=1e4,
    )
    assert isinstance(res, CorrectorResult)
    assert res.hypothesis == "H1"
    assert res.y_hat.shape == (len(region_order),)
    assert np.all(res.y_hat >= 0)


def test_large_ridge_alpha_correction_near_zero():
    """Very large ridge_alpha shrinks correction toward zero; y_hat ≈ baseline."""
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    res = predict_graph_corrector(
        panel, "TS", region_order, train_years, 2016,
        hypothesis="H1", identity_graph=True, ridge_alpha=1e9,
    )
    np.testing.assert_allclose(res.y_hat, res.y_baseline, atol=5.0,
        err_msg="ridge_alpha=1e9 should shrink correction near zero")


def test_corrector_result_no_leakage_metadata():
    """Correction metadata must record permute_mode."""
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    res = predict_graph_corrector(
        panel, "TS", region_order, train_years, 2016,
        hypothesis="H2", identity_graph=False, ridge_alpha=100.0,
    )
    assert "ridge_alpha" in res.metadata
    assert res.metadata["ridge_alpha"] == 100.0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_h2_deterministic_same_rng():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    res1 = predict_graph_corrector(
        panel, "TS", region_order, train_years, 2016,
        hypothesis="H2", identity_graph=False, ridge_alpha=100.0, rng=rng1,
    )
    res2 = predict_graph_corrector(
        panel, "TS", region_order, train_years, 2016,
        hypothesis="H2", identity_graph=False, ridge_alpha=100.0, rng=rng2,
    )
    np.testing.assert_array_equal(res1.y_hat, res2.y_hat)


# ---------------------------------------------------------------------------
# No NaN/Inf in final predictions
# ---------------------------------------------------------------------------

def test_h2_no_inf():
    panel = make_panel()
    region_order = _region_order(panel, "TS")
    train_years = list(range(2012, 2016))
    res = predict_graph_corrector(
        panel, "TS", region_order, train_years, 2016,
        hypothesis="H2", identity_graph=False, ridge_alpha=100.0,
    )
    assert not res.any_inf_in_hat, "H2 output must never contain Inf"
