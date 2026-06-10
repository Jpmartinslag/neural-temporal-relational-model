"""Phase 5 neural residual corrector: H1-neural and H2-neural.

Architecture (distinct from the Ridge linear corrector in corrector.py):
    correction(t, r) = alpha_scale * MLP(h_sector[r,t], ar_lags[r,t])
    y_hat(t, r)      = y_hat_baseline(t, r) + correction(t, r)

H1-neural: MLP on per-sector features WITHOUT graph propagation.
H2-neural: MLP on per-sector features WITH L2 message passing.

Both use:
    - Identical architecture (hidden_layer_sizes, alpha, max_iter, seed)
    - Multi-sector input: (n_sectors + AR_LAGS) features per region
    - alpha_scale ∈ [0, 1] fitted by Ridge on training MLP outputs vs residuals
    - Baseline (persistence H0) frozen; no information from eval_year

Capacity parity: H1-neural and H2-neural have the same n_params because
input dimension is identical (same sectors, same AR lags; only propagation differs).

Naming: "neural" here means sklearn MLPRegressor (relu, adam, L2 reg). Not PyTorch.
No GNN, STGNN, or attention.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from src.modeles.phase5.corrector import (
    _territory_totals,
    _alpha_ratio,
    wmape,
    CorrectorResult,
    AR_LAGS,
)
from src.modeles.phase5.l2_pool import (
    eligible_sectors,
    territory_features_multi,
)

# ---------------------------------------------------------------------------
# Hyper-parameters (small, regularised)
# ---------------------------------------------------------------------------
HIDDEN_LAYER_SIZES: tuple[int, ...] = (16, 8)
MLP_L2_ALPHA: float = 0.05         # L2 weight regularisation
MLP_MAX_ITER: int = 300
MLP_N_ITER_NO_CHANGE: int = 20
ALPHA_MAX: float = 1.0              # clip alpha_scale to [0, 1]
ALPHA_RIDGE: float = 1.0            # ridge alpha for alpha_scale fitting


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ar_features(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    avail_year: int,
    n_lags: int = AR_LAGS,
) -> np.ndarray:
    """AR lag features for one avail_year: (n_regions, n_lags).

    lag j → _territory_totals(avail_year - j).
    """
    n_r = len(region_order)
    out = np.full((n_r, n_lags), np.nan)
    for lag in range(n_lags):
        col = _territory_totals(panel, country, region_order, avail_year - lag)
        out[:, lag] = col
    return out


def _build_neural_features(
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    avail_year: int,
    *,
    identity_graph: bool,
    permute_mode: str | None,
    rng: np.random.Generator | None,
    n_lags: int = AR_LAGS,
) -> np.ndarray:
    """(n_regions, n_sectors + n_lags) feature matrix for one eval/avail year.

    Uses territory_features_multi for sector features (with or without graph).
    Concatenates AR lag features.
    """
    _, feat_ms, _ = territory_features_multi(
        panel, country, avail_year,
        identity_graph=identity_graph,
        permute_mode=permute_mode,
        rng=rng,
    )
    ar = _ar_features(panel, country, region_order, avail_year, n_lags)
    return np.concatenate([feat_ms, ar], axis=1)


def n_params(hidden_layer_sizes: tuple[int, ...], n_input: int) -> int:
    """Count MLP parameters for capacity-parity verification."""
    layers = [n_input] + list(hidden_layer_sizes) + [1]
    return sum(layers[i] * layers[i + 1] + layers[i + 1] for i in range(len(layers) - 1))


# ---------------------------------------------------------------------------
# Neural corrector: main function
# ---------------------------------------------------------------------------

def predict_neural_corrector(
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
    hidden_layer_sizes: tuple[int, ...] = HIDDEN_LAYER_SIZES,
    mlp_alpha: float = MLP_L2_ALPHA,
    max_iter: int = MLP_MAX_ITER,
    alpha_max: float = ALPHA_MAX,
    random_state: int = 42,
) -> CorrectorResult:
    """H1-neural / H2-neural / PC-temporal-neural / PC-territory-neural.

    Leakage guarantee: graph for year t uses window [t-5..t-1]; training
    targets and features use only years < eval_year.
    """
    n_r = len(region_order)
    sectors = eligible_sectors(panel, country)
    n_input = len(sectors) + AR_LAGS

    # ------------------------------------------------------------------ #
    # 1. Collect training samples                                          #
    # ------------------------------------------------------------------ #
    X_rows: list[np.ndarray] = []
    y_rows: list[float] = []

    for t in train_years:
        y_true_t = _territory_totals(panel, country, region_order, t + 1)
        y_base_t = _territory_totals(panel, country, region_order, t)
        resid_t = y_true_t - y_base_t

        feat_t = _build_neural_features(
            panel, country, region_order, t,
            identity_graph=identity_graph,
            permute_mode=permute_mode,
            rng=rng,
        )
        for r in range(n_r):
            row = feat_t[r]
            if np.isfinite(resid_t[r]) and np.isfinite(row).all():
                X_rows.append(row)
                y_rows.append(float(resid_t[r]))

    # ------------------------------------------------------------------ #
    # 2. Fallback when insufficient training data                          #
    # ------------------------------------------------------------------ #
    y_base_test = _territory_totals(panel, country, region_order, eval_year)
    y_true_test = _territory_totals(panel, country, region_order, eval_year + 1)

    if len(X_rows) < max(4, n_input):
        warnings.warn(
            f"{hypothesis}/{country}/{eval_year}: insufficient training samples "
            f"({len(X_rows)}); falling back to baseline"
        )
        return CorrectorResult(
            hypothesis=hypothesis, country=country, eval_year=eval_year,
            y_hat=y_base_test.copy(), y_true=y_true_test, y_baseline=y_base_test,
            correction=np.zeros(n_r),
            wmape=wmape(y_base_test, y_true_test),
            wmape_baseline=wmape(y_base_test, y_true_test),
            alpha_ratio=0.0, n_train_samples=len(X_rows),
            any_nan_in_hat=bool(np.isnan(y_base_test).any()),
            any_inf_in_hat=bool(np.isinf(y_base_test).any()),
            metadata={
                "fallback": True, "hidden_layer_sizes": list(hidden_layer_sizes),
                "permute_mode": permute_mode, "alpha_scale": 0.0,
                "n_params": n_params(hidden_layer_sizes, n_input),
            },
        )

    X_train = np.array(X_rows)
    y_train = np.array(y_rows)

    # ------------------------------------------------------------------ #
    # 3. Scale                                                             #
    # ------------------------------------------------------------------ #
    scaler_X = StandardScaler()
    X_sc = scaler_X.fit_transform(X_train)

    scaler_y = StandardScaler()
    y_sc = scaler_y.fit_transform(y_train[:, None]).ravel()

    # ------------------------------------------------------------------ #
    # 4. Fit MLP                                                           #
    # ------------------------------------------------------------------ #
    # early_stopping requires a validation set; disable for small datasets
    # (sklearn needs at least 1 sample in validation after fraction split)
    n_val_min = 3
    use_early_stopping = len(X_train) >= int(n_val_min / 0.1)  # i.e., >= 30

    mlp = MLPRegressor(
        hidden_layer_sizes=hidden_layer_sizes,
        activation="relu",
        solver="adam",
        alpha=mlp_alpha,
        learning_rate_init=1e-3,
        max_iter=max_iter,
        early_stopping=use_early_stopping,
        n_iter_no_change=MLP_N_ITER_NO_CHANGE if use_early_stopping else max_iter,
        random_state=random_state,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mlp.fit(X_sc, y_sc)

    # ------------------------------------------------------------------ #
    # 5. Fit alpha_scale via Ridge (clipped to [0, alpha_max])             #
    # ------------------------------------------------------------------ #
    pred_train_sc = mlp.predict(X_sc)
    pred_train = scaler_y.inverse_transform(pred_train_sc[:, None]).ravel()

    alpha_ridge = Ridge(alpha=ALPHA_RIDGE, fit_intercept=False)
    alpha_ridge.fit(pred_train[:, None], y_train)
    alpha_scale = float(np.clip(alpha_ridge.coef_[0], 0.0, alpha_max))

    # ------------------------------------------------------------------ #
    # 6. Predict at eval_year                                              #
    # ------------------------------------------------------------------ #
    feat_test = _build_neural_features(
        panel, country, region_order, eval_year,
        identity_graph=identity_graph,
        permute_mode=permute_mode,
        rng=rng,
    )

    corr = np.zeros(n_r)
    for r in range(n_r):
        row = feat_test[r]
        if np.isfinite(row).all():
            row_sc = scaler_X.transform(row[None, :])
            pred_sc = mlp.predict(row_sc)[0]
            pred = float(scaler_y.inverse_transform([[pred_sc]])[0, 0])
            corr[r] = alpha_scale * pred
        # else: no correction (NaN features → 0)

    y_hat = np.clip(y_base_test + corr, 0.0, None)
    alpha_r = _alpha_ratio(corr, y_base_test)

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
        alpha_ratio=alpha_r,
        n_train_samples=len(X_rows),
        any_nan_in_hat=bool(np.isnan(y_hat).any()),
        any_inf_in_hat=bool(np.isinf(y_hat).any()),
        metadata={
            "hidden_layer_sizes": list(hidden_layer_sizes),
            "n_params": n_params(hidden_layer_sizes, n_input),
            "n_iter": int(mlp.n_iter_),
            "alpha_scale": alpha_scale,
            "mlp_alpha": mlp_alpha,
            "permute_mode": permute_mode,
            "identity_graph": identity_graph,
        },
    )
