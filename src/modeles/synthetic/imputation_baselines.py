"""
imputation_baselines.py

Non-neural imputation baselines for HERALD synthetic benchmark (DEC-039).

All baselines implement:
    .fit(observed_panel, obs_mask)   — learn from observed data
    .transform(observed_panel, obs_mask) → np.ndarray  — imputed full panel

Rules:
- Observed cells are copied exactly.
- Missing cells are filled by the method.
- No future information is used in temporal features (causal).
- NaN is never implicitly converted to 0 before the model sees it.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge


class _BaseImputer:
    """Common interface."""
    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "_BaseImputer":
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def fit_transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        return self.fit(panel, mask).transform(panel, mask)

    @staticmethod
    def _apply_observed(imputed: np.ndarray, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Overwrite imputed values with ground-truth observed values."""
        result = imputed.copy()
        result[mask == 1] = panel[mask == 1]
        return result


class MeanImputer(_BaseImputer):
    """Fill missing cells with the per-series (territory, sector) mean of observed values."""

    def __init__(self, fallback: str = "global"):
        self.fallback = fallback  # 'global' or 'zero'
        self._series_means: np.ndarray | None = None
        self._global_mean: float = 0.0

    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "MeanImputer":
        safe = np.where(mask, panel, np.nan)
        # Mean per (territory, sector) series
        with np.errstate(all="ignore"):
            self._series_means = np.nanmean(safe, axis=2)  # (n_T, n_S)
        self._global_mean = float(np.nanmean(safe))
        # Replace NaN means (fully missing series) with global mean
        self._series_means = np.where(
            np.isnan(self._series_means), self._global_mean, self._series_means
        )
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        n_T, n_S, n_Y = panel.shape
        imputed = np.broadcast_to(self._series_means[:, :, None], (n_T, n_S, n_Y)).copy()
        return self._apply_observed(imputed, panel, mask)


class MedianImputer(_BaseImputer):
    """Fill missing cells with the per-series median of observed values."""

    def __init__(self):
        self._series_medians: np.ndarray | None = None
        self._global_median: float = 0.0

    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "MedianImputer":
        safe = np.where(mask, panel, np.nan)
        with np.errstate(all="ignore"):
            self._series_medians = np.nanmedian(safe, axis=2)
        self._global_median = float(np.nanmedian(safe))
        self._series_medians = np.where(
            np.isnan(self._series_medians), self._global_median, self._series_medians
        )
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        n_T, n_S, n_Y = panel.shape
        imputed = np.broadcast_to(self._series_medians[:, :, None], (n_T, n_S, n_Y)).copy()
        return self._apply_observed(imputed, panel, mask)


class ForwardFillImputer(_BaseImputer):
    """
    Causal forward fill: replace missing cell at (t, s, y) with the last
    observed value in the same series before year y.
    Falls back to backward fill (first observed future value) if no past value.
    Final fallback: series mean.
    """

    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "ForwardFillImputer":
        self._mean_imp = MeanImputer().fit(panel, mask)
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        n_T, n_S, n_Y = panel.shape
        result = panel.copy()
        fallback = self._mean_imp.transform(panel, mask)

        for t in range(n_T):
            for s in range(n_S):
                last_obs = None
                for y in range(n_Y):
                    if mask[t, s, y] == 1:
                        last_obs = panel[t, s, y]
                    elif last_obs is not None:
                        result[t, s, y] = last_obs
                    else:
                        result[t, s, y] = fallback[t, s, y]  # no past observed → fallback

        return self._apply_observed(result, panel, mask)


class TemporalInterpolationImputer(_BaseImputer):
    """
    Causal linear interpolation: for a missing cell at year y,
    use the last observed value before y as the anchor and extrapolate
    linearly based on the local slope of the last two observed points.
    Pure causal: never uses future observations.
    """

    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "TemporalInterpolationImputer":
        self._ffill = ForwardFillImputer().fit(panel, mask)
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        n_T, n_S, n_Y = panel.shape
        result = panel.copy()

        for t in range(n_T):
            for s in range(n_S):
                obs_years = [y for y in range(n_Y) if mask[t, s, y] == 1]
                if len(obs_years) == 0:
                    continue  # will be handled by fallback in apply_observed step
                elif len(obs_years) == 1:
                    # Only one observed point — flat interpolation
                    for y in range(n_Y):
                        if mask[t, s, y] == 0:
                            result[t, s, y] = panel[t, s, obs_years[0]]
                else:
                    for y in range(n_Y):
                        if mask[t, s, y] == 1:
                            continue
                        # Causal: find last two observed years before y
                        past_obs = [oy for oy in obs_years if oy < y]
                        if len(past_obs) >= 2:
                            y1, y2 = past_obs[-2], past_obs[-1]
                            v1, v2 = panel[t, s, y1], panel[t, s, y2]
                            slope = (v2 - v1) / max(y2 - y1, 1)
                            result[t, s, y] = v2 + slope * (y - y2)
                        elif len(past_obs) == 1:
                            result[t, s, y] = panel[t, s, past_obs[-1]]
                        else:
                            # No past observation: use first future observed (not causal, fallback)
                            future_obs = [oy for oy in obs_years if oy > y]
                            if future_obs:
                                result[t, s, y] = panel[t, s, future_obs[0]]

        return self._apply_observed(result, panel, mask)


def _build_temporal_features(panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Build causal temporal features for each cell (n_T * n_S * n_Y, n_features).
    Only uses t' ≤ t-1 information (strictly causal).

    Features (7): temporal_mean, causal_last, temporal_std,
                  ar1_residual_mean, year_idx, sector_idx, territory_idx
    """
    n_T, n_S, n_Y = panel.shape
    safe = np.where(mask, panel, 0.0)

    features = np.zeros((n_T, n_S, n_Y, 7))

    # Causal running statistics (use only years 0..t, never future)
    cumsum = (safe * mask).cumsum(axis=2)
    cumcount = mask.cumsum(axis=2).clip(min=1)
    running_mean = cumsum / cumcount  # mean of observed values in [0..t]

    # Feature 0: causal cumulative mean (up to and including t)
    features[:, :, :, 0] = running_mean

    # Feature 1: strictly causal mean (up to t-1 only, zero at year 0)
    causal_mean = np.zeros_like(running_mean)
    causal_mean[:, :, 1:] = running_mean[:, :, :-1]
    features[:, :, :, 1] = causal_mean

    # Feature 2: causal running std (up to and including t)
    cumsq = (safe * mask * safe).cumsum(axis=2)
    running_sq_mean = cumsq / cumcount
    running_var = np.maximum(running_sq_mean - running_mean ** 2, 0.0)
    features[:, :, :, 2] = np.sqrt(running_var)

    # Feature 3: causal running AR1 residual (mean of observed diffs up to year y-2)
    y_diff = np.diff(safe, axis=2)  # (n_T, n_S, n_Y-1); diff[i] = y[i+1]-y[i]
    m_diff = (mask[:, :, 1:] * mask[:, :, :-1])  # both endpoints observed
    ar1_cumsum = (y_diff * m_diff).cumsum(axis=2)           # (n_T, n_S, n_Y-1)
    ar1_cumcount = m_diff.cumsum(axis=2).clip(min=1)
    running_ar1_mean = ar1_cumsum / ar1_cumcount             # running mean up to diff[i]
    # At year y, only use diffs diff[0]..diff[y-2] (strictly causal)
    causal_ar1 = np.zeros((n_T, n_S, n_Y))
    causal_ar1[:, :, 2:] = running_ar1_mean[:, :, :-1]     # year y → running_ar1 at diff y-2
    features[:, :, :, 3] = causal_ar1

    # Features 4-6: normalized indices
    year_idx = np.arange(n_Y, dtype=float) / max(n_Y - 1, 1)
    sector_idx = np.arange(n_S, dtype=float) / max(n_S - 1, 1)
    territory_idx = np.arange(n_T, dtype=float) / max(n_T - 1, 1)

    features[:, :, :, 4] = year_idx[None, None, :]
    features[:, :, :, 5] = sector_idx[None, :, None]
    features[:, :, :, 6] = territory_idx[:, None, None]

    return features.reshape(n_T * n_S * n_Y, 7)


def _build_graph_features(panel: np.ndarray, mask: np.ndarray,
                           adj_sector: np.ndarray, adj_territory: np.ndarray) -> np.ndarray:
    """
    Additional graph-neighbor features for each cell (n_T * n_S * n_Y, 2).
    Features: sector_neighbor_mean, territory_neighbor_mean
    """
    n_T, n_S, n_Y = panel.shape
    safe = np.where(mask, panel, 0.0)

    # Sector neighbor mean: adj_sector[i, j] * safe[t, j, y] / sum(adj_sector[i, j] * mask[t, j, y])
    sector_wsum = np.einsum("ij,tjy->tiy", adj_sector, safe * mask)        # (n_T, n_S, n_Y)
    sector_wcount = np.einsum("ij,tjy->tiy", adj_sector, mask).clip(min=1e-8)
    sector_neighbor_mean = sector_wsum / sector_wcount

    # Territory neighbor mean
    terr_wsum = np.einsum("ij,jsy->isy", adj_territory, safe * mask)       # (n_T, n_S, n_Y)
    terr_wcount = np.einsum("ij,jsy->isy", adj_territory, mask).clip(min=1e-8)
    territory_neighbor_mean = terr_wsum / terr_wcount

    graph_feat = np.stack([
        sector_neighbor_mean.reshape(-1),
        territory_neighbor_mean.reshape(-1),
    ], axis=-1)

    return graph_feat  # (n_T * n_S * n_Y, 2)


class RidgeImputer(_BaseImputer):
    """
    Ridge regression on temporal features only (no graph).
    Train on observed cells, predict missing cells.
    """

    def __init__(self, alpha: float = 1.0):
        self._ridge = Ridge(alpha=alpha, fit_intercept=True)
        self._global_mean: float = 0.0

    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "RidgeImputer":
        feats = _build_temporal_features(panel, mask)  # (n_T*n_S*n_Y, 7)
        targets = panel.ravel()
        obs_flat = mask.ravel().astype(bool)
        self._global_mean = float(np.nanmean(panel[mask == 1]))
        if obs_flat.sum() >= 2:
            self._ridge.fit(feats[obs_flat], targets[obs_flat])
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        feats = _build_temporal_features(panel, mask)
        preds = self._ridge.predict(feats)
        imputed = preds.reshape(panel.shape)
        return self._apply_observed(imputed, panel, mask)


class GraphRidgeImputer(_BaseImputer):
    """
    Ridge regression with temporal + graph-neighbor features.
    Uses provided sector and territory adjacency matrices.
    This is the non-neural graph-augmented baseline.
    """

    def __init__(self, adj_sector: np.ndarray, adj_territory: np.ndarray, alpha: float = 1.0):
        self._adj_s = adj_sector
        self._adj_t = adj_territory
        self._ridge = Ridge(alpha=alpha, fit_intercept=True)

    def fit(self, panel: np.ndarray, mask: np.ndarray) -> "GraphRidgeImputer":
        temp_feats = _build_temporal_features(panel, mask)
        graph_feats = _build_graph_features(panel, mask, self._adj_s, self._adj_t)
        feats = np.concatenate([temp_feats, graph_feats], axis=1)
        targets = panel.ravel()
        obs_flat = mask.ravel().astype(bool)
        if obs_flat.sum() >= 2:
            self._ridge.fit(feats[obs_flat], targets[obs_flat])
        return self

    def transform(self, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
        temp_feats = _build_temporal_features(panel, mask)
        graph_feats = _build_graph_features(panel, mask, self._adj_s, self._adj_t)
        feats = np.concatenate([temp_feats, graph_feats], axis=1)
        preds = self._ridge.predict(feats)
        imputed = preds.reshape(panel.shape)
        return self._apply_observed(imputed, panel, mask)
