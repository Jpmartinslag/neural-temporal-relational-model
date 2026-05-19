"""Forecast-safe regime encodings for HERALD regime experiments.

These helpers deliberately separate manually labelled historical regimes from
latent or inferred regimes.  Non-manual modes must not use the COVID/rebound
indicator columns, either in regime vectors or in annual features.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

import train_herald_v6 as base


REGIME_MODES = (
    "manual_flags",
    "no_regime",
    "growth_only",
    "shock_zscore",
    "latent_quantile",
    "latent_change",
    "change_point",
    # Phase 2D: causal PELT change-point regimes
    "pelt_regime_pen3",
    "pelt_regime_pen5",
    # Phase 2E: regimes based on causal training residuals / lagged recovery.
    "resid_pelt",
    "resid_pelt_recovery_velocity",
    "recovery_velocity",
    "recovery_velocity_permute",
)

# Populated per-process during fold runs; keyed by train_max year.
# Read by train_herald_regime_experiment.py for metadata saving.
_pelt_breakpoints: Dict[int, List[int]] = {}
_regime_metadata: Dict[int, Dict[str, object]] = {}


def get_pelt_breakpoints() -> Dict[int, List[int]]:
    """Return a copy of the PELT breakpoint cache (train_max → year list)."""
    return dict(_pelt_breakpoints)


def get_regime_metadata() -> Dict[int, Dict[str, object]]:
    """Return per-fold regime diagnostics for metadata/audits."""
    return {int(k): dict(v) for k, v in _regime_metadata.items()}


def _require_ruptures() -> None:
    """Raise ImportError with a clear message if ruptures is not installed."""
    try:
        import ruptures  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "ruptures is required for pelt_regime modes. "
            "Install with: pip install ruptures"
        ) from exc


def feature_columns_for_regime(panel: pd.DataFrame, regime_mode: str) -> List[str]:
    """Return annual features for a regime experiment.

    Manual control keeps the current HERALD contract.  Every non-manual regime
    removes researcher-defined COVID/rebound flags from annual inputs, so the
    model must infer crisis structure from lagged economic signals.
    """
    if regime_mode == "manual_flags":
        return base.feature_columns(panel, ablation="full")
    return base.feature_columns(panel, ablation="regime_exclusive")


def build_regime_vectors(panel: pd.DataFrame, years_sorted, train_max: int,
                         regime_mode: str, y_train=None, ridge_train=None) -> np.ndarray:
    if regime_mode not in REGIME_MODES:
        raise ValueError(f"Unknown regime_mode={regime_mode!r}")
    if regime_mode == "manual_flags":
        return base.build_regime_vectors(panel, years_sorted, train_max)
    if regime_mode == "no_regime":
        return np.zeros((len(years_sorted), base.REGIME_DIM), dtype=np.float32)

    # Fail early if ruptures is missing for PELT modes (C3: no silent fallback)
    if regime_mode.startswith("pelt_") or regime_mode.startswith("resid_pelt"):
        _require_ruptures()

    agg = _global_lag_signals(panel)
    train_mask = agg["target_year"] <= train_max
    train_growth = agg.loc[train_mask, "global_growth"].to_numpy(dtype=float)
    train_abs = np.abs(train_growth)
    g_mean, g_std = _mean_std(train_growth)
    abs_mean, abs_std = _mean_std(train_abs)

    # Pre-compute PELT breakpoints once per fold (causal: only train data)
    pelt_last_bkp_year: Optional[int] = None
    if regime_mode.startswith("pelt_"):
        pen = 3.0 if regime_mode == "pelt_regime_pen3" else 5.0
        train_years_arr = agg.loc[train_mask, "target_year"].to_numpy(dtype=int)
        bkp_years = _run_pelt(train_growth, train_years_arr, pen, int(train_max))
        pelt_last_bkp_year = max(bkp_years) if bkp_years else None
        _regime_metadata[int(train_max)] = {
            "regime_series_used": "lagged_global_growth",
            "pelt_penalty": pen,
            "breakpoints": [int(x) for x in bkp_years],
        }
    elif regime_mode.startswith("resid_pelt"):
        if y_train is None or ridge_train is None:
            raise ValueError("resid_pelt requires y_train and ridge_train from the fold training set")
        train_years_arr = agg.loc[train_mask, "target_year"].to_numpy(dtype=int)
        residual_series, residual_valid = _mean_residual_series(y_train, ridge_train)
        if len(residual_series) != len(train_years_arr):
            raise ValueError(
                f"resid_pelt length mismatch: residual={len(residual_series)} years={len(train_years_arr)}"
            )
        residual_series_valid = residual_series[residual_valid]
        train_years_valid = train_years_arr[residual_valid]
        bkp_years = _run_pelt(residual_series_valid, train_years_valid, 3.0, int(train_max))
        pelt_last_bkp_year = max(bkp_years) if bkp_years else None
        _regime_metadata[int(train_max)] = {
            "regime_series_used": "ridge_residual_mean_by_training_year",
            "pelt_penalty": 3.0,
            "breakpoints": [int(x) for x in bkp_years],
            "residual_series_mean": [float(x) for x in residual_series_valid],
            "residual_series_years": [int(x) for x in train_years_valid],
            "residual_years_dropped": [
                int(y) for y, valid in zip(train_years_arr, residual_valid) if not bool(valid)
            ],
        }

    velocity_stats = None
    if regime_mode.startswith("recovery_velocity") or regime_mode == "resid_pelt_recovery_velocity":
        velocity_stats = _velocity_stats(agg, train_mask)
        meta = dict(_regime_metadata.get(int(train_max), {}))
        meta.update({
            "velocity_series_used": "lagged_global_growth_velocity",
            "velocity_by_year": {
                str(int(r.target_year)): float(r.global_velocity)
                for r in agg.itertuples(index=False)
            },
            "velocity_is_causal": True,
            "permuted_velocity": regime_mode.endswith("_permute"),
        })
        _regime_metadata[int(train_max)] = meta

    regime_by_year: Dict[int, np.ndarray] = {}
    for row in agg.itertuples(index=False):
        yr = int(row.target_year)
        growth_z = (float(row.global_growth) - g_mean) / g_std
        abs_z = (abs(float(row.global_growth)) - abs_mean) / abs_std
        vol_z = (float(row.local_dispersion) - float(agg.loc[train_mask, "local_dispersion"].mean())) / _safe_std(
            agg.loc[train_mask, "local_dispersion"].to_numpy(dtype=float)
        )
        if regime_mode == "growth_only":
            vec = np.array([0.0, 0.0, growth_z], dtype=np.float32)
        elif regime_mode == "shock_zscore":
            vec = np.array([growth_z, abs_z, vol_z], dtype=np.float32)
        elif regime_mode == "latent_quantile":
            vec = _quantile_state(float(row.global_growth), train_growth)
        elif regime_mode in {"latent_change", "change_point"}:
            vec = _change_state(growth_z, abs_z, vol_z)
        elif regime_mode.startswith("pelt_"):
            vec = _pelt_features_for_year(yr, pelt_last_bkp_year)
        elif regime_mode == "resid_pelt":
            vec = _pelt_features_for_year(yr, pelt_last_bkp_year)
        elif regime_mode == "resid_pelt_recovery_velocity":
            pelt_vec = _pelt_features_for_year(yr, pelt_last_bkp_year)
            vel_vec = _recovery_velocity_state(row, velocity_stats)
            vec = np.array([pelt_vec[0], pelt_vec[2], vel_vec[1]], dtype=np.float32)
        elif regime_mode.startswith("recovery_velocity"):
            vec = _recovery_velocity_state(row, velocity_stats)
        else:
            raise ValueError(f"Unhandled regime_mode={regime_mode!r}")
        regime_by_year[yr] = np.nan_to_num(vec, nan=0.0, posinf=5.0, neginf=-5.0)

    regime = np.zeros((len(years_sorted), base.REGIME_DIM), dtype=np.float32)
    for ti, yr in enumerate(years_sorted):
        regime[ti] = regime_by_year.get(int(yr), np.zeros(base.REGIME_DIM, dtype=np.float32))
    if regime_mode == "recovery_velocity_permute":
        rng = np.random.default_rng(20260513 + int(train_max))
        train_positions = [i for i, yr in enumerate(years_sorted) if int(yr) <= int(train_max)]
        if len(train_positions) > 1:
            shuffled = train_positions.copy()
            rng.shuffle(shuffled)
            regime[train_positions] = regime[shuffled]
        test_positions = [i for i, yr in enumerate(years_sorted) if int(yr) > int(train_max)]
        if test_positions and train_positions:
            # Keep this falsification causal: test years receive a shuffled
            # training-year regime vector, never a future/test-derived vector.
            for pos in test_positions:
                regime[pos] = regime[int(rng.choice(train_positions))]
    return regime


def _global_lag_signals(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    required = {"target_year", "side_lag_1"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns for regime signals: {missing}")

    growth_cols = [c for c in ("growth_1y", "growth_2y") if c in df.columns]
    agg_map = {
        "mean_lag1": ("side_lag_1", "mean"),
        "sum_lag1": ("side_lag_1", "sum"),
        "local_dispersion": ("side_lag_1", _safe_dispersion),
    }
    for c in growth_cols:
        agg_map[f"mean_{c}"] = (c, "mean")
    agg = df.groupby("target_year").agg(**agg_map).reset_index().sort_values("target_year")
    agg["global_growth"] = agg["sum_lag1"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if "mean_growth_1y" in agg:
        agg["global_growth"] = 0.5 * agg["global_growth"] + 0.5 * agg["mean_growth_1y"].fillna(0.0)
    agg["global_velocity"] = agg["global_growth"].diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return agg.reset_index(drop=True)


def _mean_residual_series(y_train, ridge_train) -> Tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_train, dtype=float)
    r = np.asarray(ridge_train, dtype=float)
    if y.shape != r.shape:
        raise ValueError(f"y_train/ridge_train shape mismatch: {y.shape} vs {r.shape}")
    resid = y - r
    with np.errstate(invalid="ignore"):
        finite = np.isfinite(resid)
        counts = finite.sum(axis=1)
        sums = np.where(finite, resid, 0.0).sum(axis=1)
        series = np.divide(sums, counts, out=np.full_like(sums, np.nan, dtype=float), where=counts > 0)
    valid = np.isfinite(series)
    clean = np.nan_to_num(series, nan=0.0, posinf=0.0, neginf=0.0).astype(float)
    return clean, valid


def _velocity_stats(agg: pd.DataFrame, train_mask: pd.Series) -> Dict[str, float]:
    vals = agg.loc[train_mask, "global_velocity"].to_numpy(dtype=float)
    growth_vals = agg.loc[train_mask, "global_growth"].to_numpy(dtype=float)
    v_mean, v_std = _mean_std(vals)
    g_mean, g_std = _mean_std(growth_vals)
    return {"v_mean": v_mean, "v_std": v_std, "g_mean": g_mean, "g_std": g_std}


def _recovery_velocity_state(row, stats: Dict[str, float]) -> np.ndarray:
    growth_z = (float(row.global_growth) - stats["g_mean"]) / stats["g_std"]
    vel_z = (float(row.global_velocity) - stats["v_mean"]) / stats["v_std"]
    decel = max(0.0, -vel_z)
    return np.array([growth_z, vel_z, decel], dtype=np.float32)


def _mean_std(values: np.ndarray) -> Tuple[float, float]:
    mean = float(np.nanmean(values)) if values.size else 0.0
    return mean, _safe_std(values)


def _safe_dispersion(values) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    return std / max(mean, 1.0)


def _safe_std(values: np.ndarray) -> float:
    std = float(np.nanstd(values)) if values.size else 1.0
    if not np.isfinite(std) or std < 1e-8:
        return 1.0
    return std


def _quantile_state(value: float, train_values: np.ndarray) -> np.ndarray:
    if train_values.size < 3:
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)
    q33, q67 = np.nanquantile(train_values, [0.33, 0.67])
    if value <= q33:
        return np.array([1.0, 0.0, 0.0], dtype=np.float32)
    if value >= q67:
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)
    return np.array([0.0, 1.0, 0.0], dtype=np.float32)


def _change_state(growth_z: float, abs_z: float, vol_z: float) -> np.ndarray:
    positive_break = max(growth_z, 0.0) if abs_z > 1.0 else 0.0
    negative_break = max(-growth_z, 0.0) if abs_z > 1.0 else 0.0
    volatility = max(vol_z, 0.0)
    return np.array([negative_break, positive_break, volatility], dtype=np.float32)


# ---------------------------------------------------------------------------
# PELT (Phase 2D — H2)
# ---------------------------------------------------------------------------

def _run_pelt(train_series: np.ndarray, train_years: np.ndarray,
              pen: float, train_max: int) -> List[int]:
    """Run PELT on the training series and return breakpoint years.

    Causal: uses only train_series (data <= train_max).
    Populates the module-level _pelt_breakpoints cache for metadata saving.
    No try/except — caller must have invoked _require_ruptures() first (C3).
    """
    import ruptures as rpt  # already verified by _require_ruptures()

    bkp_years: List[int] = []
    if len(train_series) >= 4:
        algo = rpt.Pelt(model="rbf", min_size=2, jump=1).fit(
            train_series.reshape(-1, 1)
        )
        bkps = algo.predict(pen=pen)  # [b1, b2, ..., T] — last element is len(series)
        # Convert 1-based end-exclusive indices to year labels.
        # bkp index b means the new segment starts at train_series[b].
        # The year of the last point before the break is train_years[b-1].
        bkp_years = [
            int(train_years[min(b - 1, len(train_years) - 1)])
            for b in bkps[:-1]  # exclude the sentinel end index
        ]

    _pelt_breakpoints[train_max] = bkp_years
    return bkp_years


def _pelt_features_for_year(target_year: int,
                             last_bkp_year: Optional[int]) -> np.ndarray:
    """Regime vector [dist_feat, is_0yr_post_bkp, is_1yr_post_bkp].

    dist_feat = 1 / (1 + years since new regime started).
    is_0yr = first year of new regime; is_1yr = second year.
    All-zero when no breakpoint detected.
    """
    if last_bkp_year is None:
        return np.zeros(3, dtype=np.float32)
    # New regime starts at last_bkp_year + 1
    years_since = max(0, int(target_year) - int(last_bkp_year) - 1)
    dist_feat = 1.0 / (1.0 + years_since)
    is_0yr = float(years_since == 0)
    is_1yr = float(years_since == 1)
    return np.array([dist_feat, is_0yr, is_1yr], dtype=np.float32)
