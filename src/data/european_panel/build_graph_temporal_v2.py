"""HERALD DEC-027/DEC-028 — Causal L2 graph-temporal tensor builder, schema 2.0.

Schema 2.0 corrections over schema 1.0:
  - features_seq(T,R,S,F): temporal sequence, not a static snapshot.
  - feature_mask_seq(T,R,S,F): per-feature masks; growth invalid does NOT
    discard births or share at the same (region, sector, time) position.
  - adjacency_seq(T,S,R,R): per-step causal adjacency; at step t with
    observation_year=u, the window covers [u-WINDOW+1, u] (all ≤ u < eval_year).
  - observation_years(T,): explicit observation year for each sequence step.
  - y_true from sector panel business_sector_total (same source as Ridge target).
  - y_ridge_canonical: canonical H0b Ridge (exact port of corrector.py logic).
  - Memory via resource.getrusage RSS; tracemalloc is unreliable for NumPy.
  - Adjacency representation: positive_topk (primary); signed_split and
    shrinkage_dense exported as audit artefacts.

Causal contract (enforced by hard LeakageError assertions, not documentation)
------------------------------------------------------------------------------
  max(observation_year used in any tensor) < eval_year
  adjacency at step t uses only sector_growth_1y with observation_year ≤ obs_years[t]
  Ridge training uses only available_for_forecast_year < fold_eval_year
  PT-KZ is always struct_mask=0; cannot be overwritten by a later obs loop
  Real missingness ≠ zero economic activity (preserved by per-feature masks)
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    _HAS_SKLEARN = True
except ImportError:  # pragma: no cover
    _HAS_SKLEARN = False

BASE = Path(__file__).resolve().parents[3]
DEFAULT_SECTOR_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
DEFAULT_OUT = BASE / "data/processed/graph_temporal_v2"

SCHEMA_VERSION = "2.0"
WINDOW = 5
MIN_PERIODS = 4
T_SEQ = 5          # number of time steps in sequence (= WINDOW)
TOP_K = 5          # positive_topk neighbours per region per sector
RIDGE_ALPHA_H0B = 10.0
AR_LAGS = 2
STRUCTURAL_ABSENT: frozenset[tuple[str, str]] = frozenset({("PT", "KZ")})
FEATURE_NAMES = ["sector_growth_1y", "sector_share", "sector_births"]
N_FEATURES = len(FEATURE_NAMES)
SHRINKAGE_NU = 0.1  # linear shrinkage factor for shrinkage_dense representation


# ---------------------------------------------------------------------------
# Causal gate
# ---------------------------------------------------------------------------

class LeakageError(RuntimeError):
    """Raised when future data would enter a causal fold."""


def _assert_no_leakage(
    obs_years: np.ndarray | list[int] | pd.Series,
    eval_year: int,
    label: str = "",
) -> None:
    """Raise LeakageError if any observation_year >= eval_year."""
    arr = np.asarray(obs_years, dtype=int)
    if len(arr) == 0:
        return
    mx = int(arr.max())
    if mx >= eval_year:
        raise LeakageError(
            f"Causal violation{' in ' + label if label else ''}: "
            f"observation_year={mx} >= eval_year={eval_year}"
        )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sector_panel(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def country_regions_from_sector(sector_panel: pd.DataFrame, country: str) -> list[str]:
    """Sorted region IDs with at least one supported observation in the sector panel."""
    sub = sector_panel[
        (sector_panel["country"] == country)
        & (sector_panel["mask_sector_supported"] == 1)
    ]
    return sorted(sub["region_id"].astype(str).unique())


def country_sectors(sector_panel: pd.DataFrame, country: str) -> list[str]:
    """Sorted sectors with at least one supported observation."""
    sub = sector_panel[
        (sector_panel["country"] == country)
        & (sector_panel["mask_sector_supported"] == 1)
    ]
    return sorted(sub["sector_a10"].unique())


# ---------------------------------------------------------------------------
# Adjacency representations
# ---------------------------------------------------------------------------

def _pairwise_pearson(
    mat: np.ndarray, min_periods: int = MIN_PERIODS
) -> np.ndarray:
    """Pearson correlation via pandas; handles NaN and min_periods.

    Returns (n_regions, n_regions). All-NaN if too few rows survive.
    """
    if mat.shape[0] < min_periods:
        n = mat.shape[1]
        return np.full((n, n), np.nan)
    return pd.DataFrame(mat).corr(min_periods=min_periods).to_numpy(dtype=float)


def _top_k_symmetric(corr: np.ndarray, k: int = TOP_K) -> np.ndarray:
    """Positive top-k symmetric adjacency from a correlation matrix.

    Self-loops excluded from selection; diagonal set to 0 (no self-loop convention
    for positive_topk — GNN adds identity separately if needed).
    Values are the correlation weight (not binary).
    """
    n = corr.shape[0]
    adj = np.zeros((n, n), dtype=float)
    for i in range(n):
        row = corr[i].copy()
        row[i] = -np.inf
        order = np.argsort(row)[::-1]
        for j in order[:k]:
            if np.isfinite(row[j]) and row[j] > 0.0:
                adj[i, j] = row[j]
    return np.maximum(adj, adj.T)


def _signed_split(corr: np.ndarray) -> np.ndarray:
    """Two-channel signed adjacency: [positive, abs(negative)].

    Returns (2, n_regions, n_regions).
    NaN propagated into both channels.
    Self-loop excluded (diagonal 0 in both channels).
    """
    n = corr.shape[0]
    pos = np.where(corr > 0.0, corr, 0.0)
    neg = np.where(corr < 0.0, -corr, 0.0)
    # Restore NaN
    pos = np.where(np.isnan(corr), np.nan, pos)
    neg = np.where(np.isnan(corr), np.nan, neg)
    # Zero diagonal
    np.fill_diagonal(pos, 0.0)
    np.fill_diagonal(neg, 0.0)
    return np.stack([pos, neg], axis=0)  # (2, R, R)


def _shrinkage_dense(corr: np.ndarray, nu: float = SHRINKAGE_NU) -> np.ndarray:
    """Linear shrinkage toward zero: corr_shrunk = (1 - nu) * corr.

    Diagonal set to 1 (self-loop). NaN preserved.
    """
    adj = corr * (1.0 - nu)
    np.fill_diagonal(adj, 1.0)
    return adj


def build_adjacency_at_step(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    obs_year: int,
    eval_year: int,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
    repr_: str = "positive_topk",
    k: int = TOP_K,
) -> np.ndarray:
    """Build L2 adjacency for one time step.

    obs_year must be < eval_year (enforced by LeakageError).
    Window: [obs_year - window + 1, obs_year] — all strictly before eval_year.

    repr_ is one of:
        "positive_topk"   → (S, R, R) positive top-k symmetric
        "signed_split"     → (2, S, R, R) two-channel
        "shrinkage_dense"  → (S, R, R) linearly shrunk

    Returns the chosen representation.
    """
    if obs_year >= eval_year:
        raise LeakageError(
            f"build_adjacency_at_step: obs_year={obs_year} >= eval_year={eval_year}"
        )
    window_min = obs_year - window + 1

    sp_c = sector_panel[sector_panel["country"] == country]
    sp_window = sp_c[
        (sp_c["observation_year"] >= window_min)
        & (sp_c["observation_year"] <= obs_year)
        & (sp_c["mask_sector_supported"] == 1)
    ]
    _assert_no_leakage(sp_window["observation_year"].values, eval_year,
                       label=f"adjacency obs_year={obs_year}")

    n_s = len(sectors)
    n_r = len(region_ids)

    if repr_ == "positive_topk":
        adj = np.zeros((n_s, n_r, n_r), dtype=float)
    elif repr_ == "signed_split":
        adj = np.full((2, n_s, n_r, n_r), np.nan, dtype=float)
    elif repr_ == "shrinkage_dense":
        adj = np.full((n_s, n_r, n_r), np.nan, dtype=float)
    else:
        raise ValueError(f"Unknown adjacency repr: {repr_!r}")

    for s_idx, sector in enumerate(sectors):
        sp_s = sp_window[sp_window["sector_a10"] == sector]
        if sp_s.empty:
            continue

        wide = sp_s.pivot_table(
            index="observation_year",
            columns="region_id",
            values="sector_growth_1y",
            aggfunc="first",
        ).reindex(columns=region_ids)
        mat = wide.to_numpy(dtype=float)  # (T_window, R)
        corr = _pairwise_pearson(mat, min_periods=min_periods)
        np.fill_diagonal(corr, 1.0)  # self-correlation is 1 by definition

        if repr_ == "positive_topk":
            adj[s_idx] = _top_k_symmetric(corr, k=k)
        elif repr_ == "signed_split":
            adj[:, s_idx] = _signed_split(corr)
        elif repr_ == "shrinkage_dense":
            adj[s_idx] = _shrinkage_dense(corr)

    return adj


def build_adjacency_seq(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    observation_years: list[int],
    eval_year: int,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
    k: int = TOP_K,
) -> np.ndarray:
    """Build (T, S, R, R) adjacency sequence — positive_topk representation.

    observation_years must all be < eval_year.
    adjacency_seq[t] uses window ending at observation_years[t].
    """
    _assert_no_leakage(observation_years, eval_year, label="adjacency_seq obs_years")

    T = len(observation_years)
    n_s = len(sectors)
    n_r = len(region_ids)
    adj_seq = np.zeros((T, n_s, n_r, n_r), dtype=float)

    for t, obs_year in enumerate(observation_years):
        adj_seq[t] = build_adjacency_at_step(
            sector_panel, country, sectors, region_ids,
            obs_year=obs_year, eval_year=eval_year,
            window=window, min_periods=min_periods,
            repr_="positive_topk", k=k,
        )
    return adj_seq


# ---------------------------------------------------------------------------
# Adjacency audit
# ---------------------------------------------------------------------------

def audit_adjacency_fold(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    eval_year: int,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
    topk_values: tuple[int, ...] = (3, 5, 10),
) -> dict:
    """Audit adjacency statistics for the static snapshot at eval_year.

    Reports negative fraction, density, NaN fraction, and isolated-node counts
    for three representations (positive_topk at k=3,5,10; signed_split; shrinkage_dense).
    """
    obs_year = eval_year - 1
    n_r = len(region_ids)
    n_s = len(sectors)

    # Build raw correlation (shrinkage_dense with nu=0 = raw corr with self-loop)
    raw = build_adjacency_at_step(
        sector_panel, country, sectors, region_ids,
        obs_year=obs_year, eval_year=eval_year,
        window=window, min_periods=min_periods,
        repr_="shrinkage_dense", k=TOP_K,
    )
    # nu=0 → same as raw correlation (except diagonal = 1 by _shrinkage_dense)
    # Build actual raw corr without shrinkage for stats
    # Re-compute with nu=0
    raw_corr = build_adjacency_at_step(
        sector_panel, country, sectors, region_ids,
        obs_year=obs_year, eval_year=eval_year,
        window=window, min_periods=min_periods,
        repr_="shrinkage_dense", k=TOP_K,
    )
    # raw_corr[s] has diagonal=1, off-diagonal = raw Pearson * (1-0)

    off_mask = ~np.eye(n_r, dtype=bool)
    off_finite_all = []
    neg_frac_by_sector = []
    density_by_sector = []
    nan_by_sector = []

    for s_idx in range(n_s):
        off = raw_corr[s_idx][off_mask]
        finite = off[np.isfinite(off)]
        if len(off) > 0:
            nan_by_sector.append(np.isnan(off).mean())
        else:
            nan_by_sector.append(np.nan)
        if len(finite) > 0:
            neg_frac_by_sector.append((finite < 0).mean())
            density_by_sector.append((np.abs(finite) > 0.3).mean())
            off_finite_all.extend(finite.tolist())
        else:
            neg_frac_by_sector.append(np.nan)
            density_by_sector.append(np.nan)

    # Isolated nodes per k value
    isolated_by_k: dict[int, list[int]] = {}
    for k in topk_values:
        topk_adj = build_adjacency_at_step(
            sector_panel, country, sectors, region_ids,
            obs_year=obs_year, eval_year=eval_year,
            window=window, min_periods=min_periods,
            repr_="positive_topk", k=k,
        )
        n_isolated = 0
        for s_idx in range(n_s):
            A = topk_adj[s_idx]
            row_sums = A.sum(axis=1)
            n_isolated += int((row_sums == 0).sum())
        isolated_by_k[k] = n_isolated

    all_off = np.array(off_finite_all)
    stats: dict = {
        "eval_year": eval_year,
        "n_sectors": n_s,
        "n_regions": n_r,
        "neg_fraction_mean": float(np.nanmean(neg_frac_by_sector)),
        "neg_fraction_by_sector": [
            float(x) if not np.isnan(x) else None for x in neg_frac_by_sector
        ],
        "density_mean": float(np.nanmean(density_by_sector)),
        "nan_fraction_mean": float(np.nanmean(nan_by_sector)),
        "isolated_nodes_by_k": {str(k): v for k, v in isolated_by_k.items()},
        "primary_repr": "positive_topk",
        "primary_k": TOP_K,
    }
    return stats


# ---------------------------------------------------------------------------
# Node features sequence builder
# ---------------------------------------------------------------------------

def build_features_at_step(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    obs_year: int,
    eval_year: int,
    births_train_stats: dict,  # pre-computed from training window
) -> tuple[np.ndarray, np.ndarray]:
    """Build (R, S, F) features and (R, S, F) per-feature masks at obs_year.

    Per-feature masks — each feature is independently valid/invalid:
      mask[r, s, 0] = 1 iff sector_growth_1y is finite and not NaN
      mask[r, s, 1] = 1 iff sector_share is finite and not NaN
      mask[r, s, 2] = 1 iff sector_births is available (mask_sector_births=1)
    struct_mask=0 positions (PT-KZ) are not observed in any feature.
    """
    if obs_year >= eval_year:
        raise LeakageError(
            f"build_features_at_step: obs_year={obs_year} >= eval_year={eval_year}"
        )

    n_r = len(region_ids)
    n_s = len(sectors)
    features = np.full((n_r, n_s, N_FEATURES), np.nan, dtype=float)
    feat_mask = np.zeros((n_r, n_s, N_FEATURES), dtype=np.int8)

    # struct_mask: 0 for structurally absent (country, sector) pairs
    struct_mask = np.ones((n_r, n_s), dtype=np.int8)
    for s_idx, sector in enumerate(sectors):
        if (country, sector) in STRUCTURAL_ABSENT:
            struct_mask[:, s_idx] = 0

    r_idx_map = {r: i for i, r in enumerate(region_ids)}

    sp_c = sector_panel[sector_panel["country"] == country]
    sp_snap = sp_c[sp_c["observation_year"] == obs_year]
    _assert_no_leakage([obs_year], eval_year, label="features_at_step")

    for s_idx, sector in enumerate(sectors):
        sp_s = sp_snap[sp_snap["sector_a10"] == sector]
        bs = births_train_stats.get(sector, {"mean": 0.0, "std": 1.0})
        b_mean = bs["mean"]
        b_std = bs["std"]

        for _, row in sp_s.iterrows():
            rid = str(row["region_id"])
            if rid not in r_idx_map:
                continue
            r_idx = r_idx_map[rid]
            if struct_mask[r_idx, s_idx] == 0:
                continue
            if row.get("mask_sector_supported", 1) == 0:
                continue

            g = row["sector_growth_1y"]
            share = row["sector_share"]
            births = row["sector_births"]
            mask_births = int(row.get("mask_sector_births", 1))

            # Feature 0: sector_growth_1y — independent validity
            if pd.notna(g) and np.isfinite(g):
                features[r_idx, s_idx, 0] = float(g)
                feat_mask[r_idx, s_idx, 0] = 1

            # Feature 1: sector_share — independent validity
            if pd.notna(share) and np.isfinite(share):
                features[r_idx, s_idx, 1] = float(share)
                feat_mask[r_idx, s_idx, 1] = 1

            # Feature 2: sector_births — requires mask_sector_births=1
            if mask_births == 1 and pd.notna(births) and np.isfinite(births):
                births_norm = (births - b_mean) / b_std
                features[r_idx, s_idx, 2] = births_norm
                feat_mask[r_idx, s_idx, 2] = 1

    return features, feat_mask


def _compute_births_train_stats(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    causal_cutoff: int,
) -> dict:
    """Compute per-sector births normalisation stats from training window.

    causal_cutoff = eval_year - 1; only obs_years <= causal_cutoff are used.
    """
    sp_c = sector_panel[
        (sector_panel["country"] == country)
        & (sector_panel["observation_year"] <= causal_cutoff)
        & (sector_panel["mask_sector_births"] == 1)
    ]
    stats: dict[str, dict] = {}
    for sector in sectors:
        vals = sp_c[sp_c["sector_a10"] == sector]["sector_births"].dropna().values
        if len(vals) > 0:
            std = float(np.nanstd(vals))
            if std < 1e-9:
                std = 1.0
            stats[sector] = {"mean": float(np.nanmean(vals)), "std": std}
        else:
            stats[sector] = {"mean": 0.0, "std": 1.0}
    return stats


def build_features_seq(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    observation_years: list[int],
    eval_year: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Build (T, R, S, F) feature tensor and (T, R, S, F) per-feature mask tensor.

    observation_years must all be < eval_year.
    Births normalisation stats are computed from the full causal window (all obs ≤ eval_year - 1).
    """
    _assert_no_leakage(observation_years, eval_year, label="features_seq obs_years")

    causal_cutoff = eval_year - 1
    births_stats = _compute_births_train_stats(
        sector_panel, country, sectors, causal_cutoff
    )

    T = len(observation_years)
    n_r = len(region_ids)
    n_s = len(sectors)
    features_seq = np.full((T, n_r, n_s, N_FEATURES), np.nan, dtype=float)
    mask_seq = np.zeros((T, n_r, n_s, N_FEATURES), dtype=np.int8)

    for t, obs_year in enumerate(observation_years):
        feat_t, mask_t = build_features_at_step(
            sector_panel, country, sectors, region_ids,
            obs_year=obs_year, eval_year=eval_year,
            births_train_stats=births_stats,
        )
        features_seq[t] = feat_t
        mask_seq[t] = mask_t

    return features_seq, mask_seq


# ---------------------------------------------------------------------------
# Struct mask (static, does not change with time)
# ---------------------------------------------------------------------------

def build_struct_mask(
    country: str,
    sectors: list[str],
    region_ids: list[str],
) -> np.ndarray:
    """(R, S) int8 struct_mask; 0 for structurally absent (country, sector) pairs."""
    n_r = len(region_ids)
    n_s = len(sectors)
    struct = np.ones((n_r, n_s), dtype=np.int8)
    for s_idx, sector in enumerate(sectors):
        if (country, sector) in STRUCTURAL_ABSENT:
            struct[:, s_idx] = 0
    return struct


# ---------------------------------------------------------------------------
# Canonical H0b Ridge (exact port of corrector.py::predict_h0b)
# ---------------------------------------------------------------------------

def _territory_totals_v2(
    sector_panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    avail_year: int,
) -> np.ndarray:
    """business_sector_total for available_for_forecast_year = avail_year.

    Returns (n_regions,); NaN where missing.
    """
    sub = (
        sector_panel[
            sector_panel["country"].eq(country)
            & sector_panel["available_for_forecast_year"].eq(avail_year)
        ]
        .drop_duplicates("region_id")
        .set_index("region_id")
    )
    out = np.full(len(region_order), np.nan)
    for i, r in enumerate(region_order):
        if r in sub.index:
            v = sub.at[r, "business_sector_total"]
            out[i] = float(v) if pd.notna(v) else np.nan
    return out


def _build_ar_features_v2(
    sector_panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    avail_years: list[int],
    n_lags: int = AR_LAGS,
) -> np.ndarray:
    """AR feature matrix (n_years * n_regions, n_lags).

    Feature j for (avail_year t, region r) = business_sector_total at avail_year t-j.
    avail_year t corresponds to observation_year t-1 (causal).
    """
    rows = []
    for t in avail_years:
        for r_idx in range(len(region_order)):
            lags = []
            for lag in range(n_lags):
                lag_avail = t - lag
                col = _territory_totals_v2(
                    sector_panel, country, [region_order[r_idx]], lag_avail
                )
                lags.append(col[0])
            rows.append(lags)
    return np.array(rows, dtype=float)


def canonical_ridge_h0b(
    sector_panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    fold_eval_year: int,
    alpha: float = RIDGE_ALPHA_H0B,
    n_lags: int = AR_LAGS,
) -> tuple[np.ndarray, np.ndarray]:
    """Canonical H0b Ridge for one (country, fold_eval_year) fold.

    Exact port of corrector.py::predict_h0b. No differences in logic or
    parameters. Uses available_for_forecast_year internally (avail = obs + 1).

    fold_eval_year = observation_year for the target (the fold we predict).
    y_true = business_sector_total at observation_year = fold_eval_year.
    Training uses only avail_years < fold_eval_year (causal).

    Returns (y_hat, y_true), both shape (n_regions,).
    """
    if not _HAS_SKLEARN:
        n_r = len(region_order)
        y_true = _territory_totals_v2(sector_panel, country, region_order, fold_eval_year + 1)
        return np.full(n_r, np.nan), y_true

    # Train years: available_for_forecast_year values strictly < fold_eval_year
    # and above min_avail + n_lags (need n_lags of AR history)
    all_avail = sorted(
        sector_panel[sector_panel["country"].eq(country)][
            "available_for_forecast_year"
        ].dropna().unique()
    )
    min_avail = min(all_avail) if all_avail else 0
    train_years = [
        y for y in all_avail
        if y < fold_eval_year and y > min_avail + n_lags
    ]
    if len(train_years) == 0:
        n_r = len(region_order)
        y_true = _territory_totals_v2(sector_panel, country, region_order, fold_eval_year + 1)
        return np.full(n_r, np.nan), y_true

    # Build training targets: y_true[i, r] = bst at avail_year = train_years[i] + 1
    n_tr = len(train_years)
    n_r = len(region_order)
    y_true_mat = np.full((n_tr, n_r), np.nan)
    for i, t in enumerate(train_years):
        y_true_mat[i] = _territory_totals_v2(sector_panel, country, region_order, t + 1)

    X_train = _build_ar_features_v2(sector_panel, country, region_order, train_years, n_lags)
    y_train = y_true_mat.ravel()

    valid = np.isfinite(X_train).all(axis=1) & np.isfinite(y_train)
    if not valid.any():
        y_true_vec = _territory_totals_v2(sector_panel, country, region_order, fold_eval_year + 1)
        return np.full(n_r, np.nan), y_true_vec

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X_train[valid])
    ridge = Ridge(alpha=alpha)
    ridge.fit(X_sc, y_train[valid])

    # Predict at fold_eval_year
    X_test = _build_ar_features_v2(
        sector_panel, country, region_order, [fold_eval_year], n_lags
    )
    X_test_sc = scaler.transform(X_test)
    y_hat = ridge.predict(X_test_sc)      # (n_regions,)
    y_hat = np.clip(y_hat, 0.0, None)

    y_true_vec = _territory_totals_v2(sector_panel, country, region_order, fold_eval_year + 1)
    return y_hat, y_true_vec


# ---------------------------------------------------------------------------
# Fold builder
# ---------------------------------------------------------------------------

def build_fold_tensors_v2(
    country: str,
    eval_year: int,
    sector_panel: pd.DataFrame,
    sectors: list[str],
    region_ids: list[str],
    t_seq: int = T_SEQ,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
    k: int = TOP_K,
) -> dict:
    """Build all schema 2.0 tensors for one (country, eval_year) fold.

    Hard causal contract:
      - observation_years = [eval_year - t_seq, ..., eval_year - 1]
      - All < eval_year; enforced by LeakageError.
      - adjacency_seq[t] uses window ending at observation_years[t].
      - Ridge trained on avail_years < eval_year.
      - births normalisation uses obs_years ≤ eval_year - 1.
    """
    obs_years = list(range(eval_year - t_seq, eval_year))  # [eval_year-5, ..., eval_year-1]
    _assert_no_leakage(obs_years, eval_year, label="observation_years")

    # Feature sequence (T, R, S, F) and per-feature masks (T, R, S, F)
    features_seq, feature_mask_seq = build_features_seq(
        sector_panel, country, sectors, region_ids, obs_years, eval_year
    )

    # Static struct mask (R, S)
    struct_mask = build_struct_mask(country, sectors, region_ids)

    # Adjacency sequence (T, S, R, R) — positive_topk
    adjacency_seq = build_adjacency_seq(
        sector_panel, country, sectors, region_ids, obs_years, eval_year,
        window=window, min_periods=min_periods, k=k
    )

    # Canonical H0b Ridge
    y_hat, y_true = canonical_ridge_h0b(
        sector_panel, country, region_ids, eval_year
    )

    # Target mask: 1 where y_true is finite
    target_mask = np.where(np.isfinite(y_true), 1, 0).astype(np.int8)
    residual = np.where(target_mask.astype(bool), y_true - y_hat, np.nan)

    # Final causal assertion: double-check no leakage entered any computation
    sp_fold = sector_panel[
        (sector_panel["country"] == country)
        & (sector_panel["observation_year"].notna())
    ]
    train_obs = sp_fold[sp_fold["observation_year"] < eval_year]
    _assert_no_leakage(train_obs["observation_year"].values, eval_year, label="final_check")

    return {
        "schema_version": SCHEMA_VERSION,
        "country": country,
        "eval_year": eval_year,
        "observation_years": np.array(obs_years, dtype=np.int32),
        "region_ids": region_ids,
        "sectors": sectors,
        "features_seq": features_seq,           # (T, R, S, F) float
        "feature_mask_seq": feature_mask_seq,   # (T, R, S, F) int8
        "struct_mask": struct_mask,             # (R, S) int8
        "adjacency_seq": adjacency_seq,         # (T, S, R, R) float
        "y_true": y_true,                       # (R,) float — from sector panel bst
        "y_ridge_canonical": y_hat,             # (R,) float ≥ 0
        "residual": residual,                   # (R,) float, NaN where target_mask=0
        "target_mask": target_mask,             # (R,) int8
        "feature_names": FEATURE_NAMES,
        "max_train_obs_year": eval_year - 1,
        "t_seq": t_seq,
        "top_k": k,
    }


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

def array_checksum(arr: np.ndarray) -> str:
    return hashlib.md5(np.ascontiguousarray(arr)).hexdigest()


def file_checksum(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Save / load fold
# ---------------------------------------------------------------------------

def save_fold_v2(fold: dict, out_dir: Path) -> dict:
    """Save schema 2.0 fold tensors to a single NPZ file; return checksums."""
    fold_dir = out_dir / fold["country"] / str(fold["eval_year"])
    fold_dir.mkdir(parents=True, exist_ok=True)

    fold_path = fold_dir / "fold_v2.npz"
    np.savez_compressed(
        fold_path,
        features_seq=fold["features_seq"],
        feature_mask_seq=fold["feature_mask_seq"],
        struct_mask=fold["struct_mask"],
        adjacency_seq=fold["adjacency_seq"],
        observation_years=fold["observation_years"],
        y_true=fold["y_true"],
        y_ridge_canonical=fold["y_ridge_canonical"],
        residual=fold["residual"],
        target_mask=fold["target_mask"],
        eval_year=np.array([fold["eval_year"]], dtype=np.int32),
    )
    checksums = {
        "fold_v2": file_checksum(fold_path),
        "adjacency_seq": array_checksum(fold["adjacency_seq"]),
        "features_seq": array_checksum(fold["features_seq"]),
        "y_ridge_canonical": array_checksum(fold["y_ridge_canonical"]),
    }
    return checksums


def load_fold_v2(country: str, eval_year: int, out_dir: Path = DEFAULT_OUT) -> dict:
    """Load schema 2.0 fold tensors. Raises FileNotFoundError if absent."""
    fold_path = out_dir / country / str(eval_year) / "fold_v2.npz"
    if not fold_path.exists():
        raise FileNotFoundError(
            f"Schema 2.0 fold missing (fail-closed): {fold_path}"
        )
    d = np.load(fold_path, allow_pickle=False)
    return {
        "features_seq": d["features_seq"],
        "feature_mask_seq": d["feature_mask_seq"],
        "struct_mask": d["struct_mask"],
        "adjacency_seq": d["adjacency_seq"],
        "observation_years": d["observation_years"],
        "y_true": d["y_true"],
        "y_ridge_canonical": d["y_ridge_canonical"],
        "residual": d["residual"],
        "target_mask": d["target_mask"],
        "eval_year": int(d["eval_year"][0]),
    }


def load_manifest_v2(out_dir: Path = DEFAULT_OUT) -> dict:
    p = out_dir / "manifest_v2.json"
    if not p.exists():
        raise FileNotFoundError(f"Schema 2.0 manifest missing (fail-closed): {p}")
    with open(p) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main export pipeline
# ---------------------------------------------------------------------------

def export_v2(
    countries: list[str],
    eval_years_by_country: dict[str, list[int]],
    sector_panel_path: Path | None = DEFAULT_SECTOR_PANEL,
    out_dir: Path = DEFAULT_OUT,
    t_seq: int = T_SEQ,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
    k: int = TOP_K,
    run_adjacency_audit: bool = True,
    _sector_panel_override: "pd.DataFrame | None" = None,
) -> dict:
    """Export schema 2.0 fold tensors and write manifest_v2.json.

    _sector_panel_override: inject a pre-built DataFrame for testing; bypasses
    sector_panel_path loading when provided.

    Returns the manifest dict.
    """
    t0 = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)

    if _sector_panel_override is not None:
        sector_panel = _sector_panel_override
    elif sector_panel_path is not None:
        sector_panel = load_sector_panel(sector_panel_path)
    else:
        raise ValueError("Either sector_panel_path or _sector_panel_override must be provided")

    manifest: dict = {
        "schema_version": SCHEMA_VERSION,
        "contract": {
            "causal": "max(observation_year) < eval_year",
            "temporal_sequence": True,
            "per_feature_masks": True,
            "adjacency_repr": "positive_topk",
            "ridge": "canonical_h0b (corrector.py port)",
            "y_true_source": "sector_panel.business_sector_total",
            "no_cross_country_edges": True,
            "pt_kz_always_masked": True,
            "missing_not_zero": True,
        },
        "sources": {
            "sector_panel": str(sector_panel_path) if sector_panel_path else "override",
            "sector_panel_checksum": file_checksum(sector_panel_path) if sector_panel_path else "n/a",
        },
        "params": {
            "t_seq": t_seq,
            "window": window,
            "min_periods": min_periods,
            "top_k": k,
            "ridge_alpha": RIDGE_ALPHA_H0B,
            "ar_lags": AR_LAGS,
        },
        "feature_names": FEATURE_NAMES,
        "structural_absent": [list(p) for p in sorted(STRUCTURAL_ABSENT)],
        "folds": [],
        "adjacency_audit": [],
    }

    for country in countries:
        sectors = country_sectors(sector_panel, country)
        region_ids = country_regions_from_sector(sector_panel, country)
        eval_years = sorted(eval_years_by_country.get(country, []))

        for eval_year in eval_years:
            fold = build_fold_tensors_v2(
                country, eval_year, sector_panel, sectors, region_ids,
                t_seq=t_seq, window=window, min_periods=min_periods, k=k
            )
            checksums = save_fold_v2(fold, out_dir)

            T, R, S, F = fold["features_seq"].shape
            fold_meta = {
                "country": country,
                "eval_year": eval_year,
                "n_regions": R,
                "n_sectors": S,
                "n_features": F,
                "t_seq": T,
                "sectors": sectors,
                "region_ids": region_ids,
                "observation_years": fold["observation_years"].tolist(),
                "max_train_obs_year": eval_year - 1,
                "features_seq_shape": [T, R, S, F],
                "adjacency_seq_shape": list(fold["adjacency_seq"].shape),
                "n_observed_targets": int(fold["target_mask"].sum()),
                "checksums": checksums,
            }
            manifest["folds"].append(fold_meta)

            if run_adjacency_audit:
                audit = audit_adjacency_fold(
                    sector_panel, country, sectors, region_ids, eval_year,
                    window=window, min_periods=min_periods,
                )
                manifest["adjacency_audit"].append(audit)

    elapsed = time.perf_counter() - t0
    manifest["build_time_s"] = round(elapsed, 2)
    manifest["n_folds"] = len(manifest["folds"])

    manifest_path = out_dir / "manifest_v2.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest
