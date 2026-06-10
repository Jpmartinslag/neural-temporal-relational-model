"""Phase 5 residual corrector: H0, H0b, H1, H2 and permutation controls.

Architecture (DEC-022 / HERALD_PHASE5_HPC_SPEC.md):
    y_hat(t, r) = y_hat_baseline(t, r) + alpha * correction(t, r)

Where correction is a Ridge regression on graph-pooled sector features
(H2) or on node-only features without propagation (H1). alpha is reported
as the mean absolute correction relative to the baseline — it is NOT a
separately fitted scalar; it emerges from Ridge regularisation strength.

Leakage protocol (strictly enforced):
- Forecast year t uses only observation_year <= t-1 data.
- Graph edges are built from window [t-5..t-1] (causal window).
- Baseline y_hat_h0[r,t] = business_sector_total[r, t-1].
- H0b Ridge is fitted only on (r, tau) pairs where tau < t.
- Correction Ridge is fitted on residuals from years tau < t.
- No information from eval_year t enters any fitted object.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from src.modeles.phase5.l2_pool import territory_features

RIDGE_ALPHA_H0B = 10.0    # regularisation for H0b AR baseline
RIDGE_ALPHA_CORR = 100.0  # regularisation for residual corrector (conservative)
AR_LAGS = 2               # H0b uses lags t-1 and t-2


# ---------------------------------------------------------------------------
# Data utilities
# ---------------------------------------------------------------------------

def _region_order(panel: pd.DataFrame, country: str) -> list[str]:
    return sorted(panel[panel["country"].eq(country)]["region_id"].unique())


def _territory_totals(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    avail_year: int,
) -> np.ndarray:
    """business_sector_total for available_for_forecast_year = avail_year.

    avail_year = observation_year + 1.
    Returns (n_regions,); NaN where missing.
    """
    sub = (
        panel[panel["country"].eq(country) & panel["available_for_forecast_year"].eq(avail_year)]
        .drop_duplicates("region_id")
        .set_index("region_id")
    )
    out = np.full(len(region_order), np.nan)
    for i, r in enumerate(region_order):
        if r in sub.index:
            v = sub.at[r, "business_sector_total"]
            out[i] = float(v) if pd.notna(v) else np.nan
    return out


def wmape(y_hat: np.ndarray, y_true: np.ndarray) -> float:
    """Weighted Mean Absolute Percentage Error.

    WMAPE = sum|y_hat - y_true| / sum|y_true|
    NaN/Inf values and zero targets are excluded.
    """
    mask = np.isfinite(y_hat) & np.isfinite(y_true) & (np.abs(y_true) > 0)
    if not mask.any():
        return float("nan")
    return float(np.sum(np.abs(y_hat[mask] - y_true[mask])) / np.sum(np.abs(y_true[mask])))


def _alpha_ratio(correction: np.ndarray, baseline: np.ndarray) -> float:
    """Mean absolute correction / mean absolute baseline.

    Proxy for alpha: how large is the graph correction relative to baseline?
    """
    mask = np.isfinite(correction) & np.isfinite(baseline) & (np.abs(baseline) > 0)
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(correction[mask])) / np.mean(np.abs(baseline[mask])))


# ---------------------------------------------------------------------------
# Rolling-origin data builder
# ---------------------------------------------------------------------------

def _rolling_targets_and_baselines(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    train_years: list[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Build (y_true, y_baseline) matrices for training years.

    y_true[i, r] = births at observation_year = train_years[i].
    y_baseline[i, r] = persistence = births at observation_year = train_years[i] - 1.
    Both shape: (n_train_years, n_regions).
    """
    n_t = len(train_years)
    n_r = len(region_order)
    y_true = np.full((n_t, n_r), np.nan)
    y_base = np.full((n_t, n_r), np.nan)
    for i, t in enumerate(train_years):
        # target: avail_year = t + 1 (observation_year = t)
        y_true[i] = _territory_totals(panel, country, region_order, t + 1)
        # persistence: avail_year = t (observation_year = t-1)
        y_base[i] = _territory_totals(panel, country, region_order, t)
    return y_true, y_base


# ---------------------------------------------------------------------------
# H0: persistence
# ---------------------------------------------------------------------------

def predict_h0(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    eval_year: int,
) -> tuple[np.ndarray, np.ndarray]:
    """H0: y_hat[r,t] = y[r,t-1].  Returns (y_hat, y_true)."""
    y_hat = _territory_totals(panel, country, region_order, eval_year)
    y_true = _territory_totals(panel, country, region_order, eval_year + 1)
    return y_hat, y_true


# ---------------------------------------------------------------------------
# H0b: Ridge AR baseline
# ---------------------------------------------------------------------------

def _build_ar_features(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    years: list[int],
    n_lags: int = AR_LAGS,
) -> np.ndarray:
    """Build AR feature matrix of shape (n_years * n_regions, n_lags).

    Feature j for (year t, region r) = y[r, t-1-j].
    Rows with any NaN are masked downstream.
    """
    rows = []
    for t in years:
        for r_idx in range(len(region_order)):
            lags = []
            for lag in range(n_lags):
                lag_year = t - lag  # avail_year = t - lag → obs_year = t - lag - 1
                col = _territory_totals(panel, country, [region_order[r_idx]], lag_year)
                lags.append(col[0])
            rows.append(lags)
    return np.array(rows, dtype=float)


def predict_h0b(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    train_years: list[int],
    eval_year: int,
    *,
    alpha: float = RIDGE_ALPHA_H0B,
    n_lags: int = AR_LAGS,
) -> tuple[np.ndarray, np.ndarray, Ridge]:
    """H0b: Ridge AR baseline.

    Fitted on (train_years × regions) pairs; predicts eval_year.
    Returns (y_hat, y_true, fitted_ridge).
    """
    n_r = len(region_order)
    n_tr = len(train_years)

    # Build training targets (flatten regions × years)
    y_true_mat, _ = _rolling_targets_and_baselines(panel, country, region_order, train_years)
    X_train = _build_ar_features(panel, country, region_order, train_years, n_lags)
    y_train = y_true_mat.ravel()

    valid = np.isfinite(X_train).all(axis=1) & np.isfinite(y_train)
    if not valid.any():
        raise ValueError(f"H0b: no valid training samples for {country} at {eval_year}")

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X_train[valid])
    ridge = Ridge(alpha=alpha)
    ridge.fit(X_sc, y_train[valid])

    # Predict eval_year
    X_test = _build_ar_features(panel, country, region_order, [eval_year], n_lags)
    X_test_sc = scaler.transform(X_test)
    y_hat = ridge.predict(X_test_sc)  # (n_regions,)
    y_hat = np.clip(y_hat, 0, None)

    y_true = _territory_totals(panel, country, region_order, eval_year + 1)
    return y_hat, y_true, ridge


# ---------------------------------------------------------------------------
# Graph-feature building (shared H1 / H2 / controls)
# ---------------------------------------------------------------------------

def _build_graph_features(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    years: list[int],
    *,
    identity_graph: bool = False,
    permute_mode: str | None = None,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Build (n_years * n_regions, 1) graph-pooled feature matrix.

    Each row = territory_state[r, t] for year t and region r (in region_order order).
    Shape: (n_years * n_regions, 1) — extra dims allow concatenation with AR features.
    """
    rows = []
    for t in years:
        r_ids, state = territory_features(
            panel, country, t,
            identity_graph=identity_graph,
            permute_mode=permute_mode,
            rng=rng,
        )
        # Align to region_order
        r_map = {r: i for i, r in enumerate(r_ids)}
        feat = np.array([
            state[r_map[r]] if r in r_map and np.isfinite(state[r_map[r]]) else np.nan
            for r in region_order
        ])
        rows.append(feat)
    return np.array(rows).ravel()[:, np.newaxis]  # (n_years * n_regions, 1)


# ---------------------------------------------------------------------------
# H1 / H2 / controls: residual corrector
# ---------------------------------------------------------------------------

@dataclass
class CorrectorResult:
    hypothesis: str
    country: str
    eval_year: int
    y_hat: np.ndarray
    y_true: np.ndarray
    y_baseline: np.ndarray
    correction: np.ndarray
    wmape: float
    wmape_baseline: float
    alpha_ratio: float
    n_train_samples: int
    any_nan_in_hat: bool
    any_inf_in_hat: bool
    metadata: dict = field(default_factory=dict)


def predict_graph_corrector(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    train_years: list[int],
    eval_year: int,
    hypothesis: str,
    *,
    identity_graph: bool = False,
    permute_mode: str | None = None,
    rng: np.random.Generator | None = None,
    ridge_alpha: float = RIDGE_ALPHA_CORR,
) -> CorrectorResult:
    """H1 / H2 / PC-temporal / PC-territory residual corrector.

    1. Compute persistence baseline y_hat_h0 for training and test years.
    2. Compute graph-pooled features for training and test years.
    3. Fit Ridge on (features_train, residuals_train).
    4. Predict correction at eval_year; add to baseline.

    Leakage constraint: graph for year t uses window [t-5..t-1]. Training
    residuals use only years < eval_year. No target information from eval_year
    enters the fitted Ridge.
    """
    n_r = len(region_order)

    # Training targets and baselines
    y_true_tr, y_base_tr = _rolling_targets_and_baselines(
        panel, country, region_order, train_years
    )
    resid_tr = (y_true_tr - y_base_tr).ravel()

    # Graph features for training years
    feat_tr = _build_graph_features(
        panel, country, region_order, train_years,
        identity_graph=identity_graph,
        permute_mode=permute_mode,
        rng=rng,
    )

    # Valid training mask
    valid_tr = (
        np.isfinite(feat_tr).all(axis=1)
        & np.isfinite(resid_tr)
    )
    n_valid = int(valid_tr.sum())

    if n_valid < 2:
        warnings.warn(f"{hypothesis}/{country}/{eval_year}: insufficient training samples ({n_valid})")
        y_base_test = _territory_totals(panel, country, region_order, eval_year)
        y_true_test = _territory_totals(panel, country, region_order, eval_year + 1)
        return CorrectorResult(
            hypothesis=hypothesis, country=country, eval_year=eval_year,
            y_hat=y_base_test, y_true=y_true_test, y_baseline=y_base_test,
            correction=np.zeros(n_r), wmape=wmape(y_base_test, y_true_test),
            wmape_baseline=wmape(y_base_test, y_true_test),
            alpha_ratio=0.0, n_train_samples=n_valid,
            any_nan_in_hat=bool(np.isnan(y_base_test).any()),
            any_inf_in_hat=bool(np.isinf(y_base_test).any()),
            metadata={"ridge_alpha": ridge_alpha, "permute_mode": permute_mode},
        )

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(feat_tr[valid_tr])
    ridge = Ridge(alpha=ridge_alpha)
    ridge.fit(X_sc, resid_tr[valid_tr])

    # Test
    y_base_test = _territory_totals(panel, country, region_order, eval_year)
    y_true_test = _territory_totals(panel, country, region_order, eval_year + 1)

    feat_test = _build_graph_features(
        panel, country, region_order, [eval_year],
        identity_graph=identity_graph,
        permute_mode=permute_mode,
        rng=rng,
    )
    feat_test_sc = scaler.transform(feat_test)
    corr = ridge.predict(feat_test_sc)  # (n_regions,)

    y_hat = y_base_test + corr
    y_hat = np.clip(y_hat, 0, None)

    alpha = _alpha_ratio(corr, y_base_test)

    return CorrectorResult(
        hypothesis=hypothesis,
        country=country,
        eval_year=eval_year,
        y_hat=y_hat,
        y_true=y_true_test,
        y_baseline=y_base_test,
        correction=corr,
        wmape=wmape(y_hat, y_true_test),
        wmape_baseline=wmape(y_base_test, y_true_test),
        alpha_ratio=alpha,
        n_train_samples=n_valid,
        any_nan_in_hat=bool(np.isnan(y_hat).any()),
        any_inf_in_hat=bool(np.isinf(y_hat).any()),
        metadata={"ridge_alpha": ridge_alpha, "permute_mode": permute_mode},
    )
