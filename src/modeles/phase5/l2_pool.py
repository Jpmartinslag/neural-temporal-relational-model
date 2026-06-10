"""L2 graph pooling for Phase 5 residual corrector.

Per-sector message passing on the L2 co-growth graph, followed by
masked aggregation across sectors to produce territory-level features.

Design constraints from DEC-022 / HERALD_PHASE5_HPC_SPEC.md:
- Message passing is applied separately for each A10 sector.
- Structurally absent sectors (PT KZ) are masked, never zeroed.
- Absence of mask never converts a missing value to an observed zero.
- Territory pooling is masked: only sectors present in the mask contribute.
- Graph is fixed at audit time; no re-estimation inside the evaluation loop.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.data.european_panel.build_g1_l2_cogrowth import (
    WINDOW,
    MIN_PERIODS,
    build_growth_matrix,
    eligible_sectors,
    pairwise_corr,
    window_matrix,
)

TOP_K = 5
SEED = 42


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _top_k_symmetric(corr: np.ndarray, k: int = TOP_K) -> np.ndarray:
    """Positive top-k symmetric adjacency from a correlation matrix.

    Self-loops excluded. Zero where corr ≤ 0 or outside top-k.
    """
    n = corr.shape[0]
    adj = np.zeros((n, n), dtype=float)
    for i in range(n):
        row = corr[i].copy()
        row[i] = -np.inf
        order = np.argsort(row)[::-1]
        for j in order[:k]:
            if np.isfinite(row[j]) and row[j] > 0:
                adj[i, j] = row[j]
    return np.maximum(adj, adj.T)


def build_sector_graph(
    panel: pd.DataFrame,
    country: str,
    sector: str,
    eval_year: int,
    *,
    permute_mode: str | None = None,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Build L2 sector graph for one (country, sector, eval_year).

    Returns (adj[n_regions, n_regions], region_ids).
    permute_mode: None | 'temporal' | 'territory' — null control variants.
    """
    region_ids, growth_years, matrix = build_growth_matrix(panel, country, sector)
    n = len(region_ids)

    if permute_mode == "temporal" and rng is not None:
        # shuffle year ordering within each region column — destroys cross-territory co-growth
        matrix = matrix.copy()
        for col in range(matrix.shape[1]):
            valid = np.where(np.isfinite(matrix[:, col]))[0]
            if len(valid) > 1:
                matrix[valid, col] = rng.permutation(matrix[valid, col])
    elif permute_mode == "territory" and rng is not None:
        # shuffle region ordering within each year row — destroys territorial structure
        matrix = matrix.copy()
        for row in range(matrix.shape[0]):
            matrix[row] = rng.permutation(matrix[row])

    win = window_matrix(growth_years, matrix, eval_year, WINDOW, frozenset())
    if win.shape[0] < MIN_PERIODS:
        return np.zeros((n, n), dtype=float), region_ids

    corr = pairwise_corr(win)
    adj = _top_k_symmetric(corr, k=TOP_K)
    adj = np.where(np.isfinite(adj), adj, 0.0)
    return adj, region_ids


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def sector_growth_features(
    panel: pd.DataFrame,
    country: str,
    sector: str,
    eval_year: int,
    region_order: list[str],
) -> np.ndarray:
    """Sector growth rate at observation_year = eval_year - 1 (available_for_forecast_year = eval_year).

    Returns (n_regions,); NaN where data unavailable — never converts structural
    absence to zero.
    """
    sub = panel[
        panel["country"].eq(country)
        & panel["sector_a10"].eq(sector)
        & panel["available_for_forecast_year"].eq(eval_year)
    ].drop_duplicates("region_id").set_index("region_id")

    result = np.full(len(region_order), np.nan)
    for i, r in enumerate(region_order):
        if r in sub.index:
            v = sub.at[r, "sector_growth_1y"]
            result[i] = float(v) if pd.notna(v) else np.nan
    return result


def structural_mask(
    panel: pd.DataFrame,
    country: str,
    sector: str,
    region_order: list[str],
) -> np.ndarray:
    """1.0 where sector is structurally supported; 0.0 where absent (e.g. PT KZ)."""
    sup = (
        panel[panel["country"].eq(country) & panel["sector_a10"].eq(sector)]
        .groupby("region_id")["mask_sector_supported"]
        .max()
    )
    return np.array([float(sup.get(r, 0)) for r in region_order])


# ---------------------------------------------------------------------------
# Message passing
# ---------------------------------------------------------------------------

def message_pass_1hop(
    x: np.ndarray,
    adj: np.ndarray,
    *,
    identity_graph: bool = False,
) -> np.ndarray:
    """1-hop mean aggregation over graph neighbours.

    x: (n_regions,) input features — may contain NaN.
    adj: (n_regions, n_regions) positive adjacency weights.
    identity_graph: if True h[r] = x[r] (no propagation, H1 control).

    Returns h: (n_regions,) — NaN where no valid neighbours exist.
    """
    if identity_graph:
        return x.copy()

    n = x.shape[0]
    h = np.full(n, np.nan)
    for r in range(n):
        row = adj[r]
        valid = (row > 0) & np.isfinite(x)
        if not valid.any():
            continue
        h[r] = float(np.average(x[valid], weights=row[valid]))
    return h


# ---------------------------------------------------------------------------
# Masked sector pooling
# ---------------------------------------------------------------------------

def masked_pool_sectors(
    h_by_sector: dict[str, np.ndarray],
    mask_by_sector: dict[str, np.ndarray],
    sectors: list[str],
) -> np.ndarray:
    """Masked mean across sectors.

    Sectors where mask=0 (structural absence) are excluded.
    Sectors where mask=1 but h=NaN (data gap) are excluded from the mean
    but do not trigger a zero fill.

    Returns (n_regions,) — NaN where every valid sector has NaN features.
    """
    n = next(iter(h_by_sector.values())).shape[0]
    total = np.zeros(n, dtype=float)
    count = np.zeros(n, dtype=float)

    for s in sectors:
        h = h_by_sector[s]
        m = mask_by_sector[s]
        for r in range(n):
            if m[r] > 0 and np.isfinite(h[r]):
                total[r] += h[r]
                count[r] += 1.0

    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, total / count, np.nan)


# ---------------------------------------------------------------------------
# Main public interface
# ---------------------------------------------------------------------------

def territory_features(
    panel: pd.DataFrame,
    country: str,
    eval_year: int,
    *,
    identity_graph: bool = False,
    permute_mode: str | None = None,
    rng: np.random.Generator | None = None,
) -> tuple[list[str], np.ndarray]:
    """Compute L2-pooled territory features for one (country, eval_year).

    Args:
        panel: sector panel DataFrame.
        country: ISO code.
        eval_year: forecast year t; uses only data from observation_year ≤ t-1.
        identity_graph: H1 control — no message passing between territories.
        permute_mode: 'temporal' | 'territory' | None — null controls.
        rng: RNG for permutation (required if permute_mode is not None).

    Returns:
        region_ids: sorted list of territory identifiers.
        state: (n_regions,) masked pooled graph features; NaN where unavailable.
    """
    sectors = eligible_sectors(panel, country)

    # Canonical region ordering from sector panel (sector-independent)
    region_order = sorted(
        panel[panel["country"].eq(country)]["region_id"].unique()
    )

    h_by_sector: dict[str, np.ndarray] = {}
    mask_by_sector: dict[str, np.ndarray] = {}

    for s in sectors:
        adj, _ = build_sector_graph(
            panel, country, s, eval_year,
            permute_mode=permute_mode, rng=rng,
        )
        x = sector_growth_features(panel, country, s, eval_year, region_order)
        h = message_pass_1hop(x, adj, identity_graph=identity_graph)
        m = structural_mask(panel, country, s, region_order)

        h_by_sector[s] = h
        mask_by_sector[s] = m

    state = masked_pool_sectors(h_by_sector, mask_by_sector, sectors)
    return region_order, state


def territory_features_multi(
    panel: pd.DataFrame,
    country: str,
    eval_year: int,
    *,
    identity_graph: bool = False,
    permute_mode: str | None = None,
    rng: np.random.Generator | None = None,
) -> tuple[list[str], np.ndarray, list[str]]:
    """Per-sector message-passed features WITHOUT cross-sector pooling.

    Returns:
        region_ids: sorted territory list.
        features: (n_regions, n_sectors) — each column is one A10 sector.
          Structurally absent sectors (PT KZ) → column all-NaN (never zero).
          Data gaps within supported sectors → NaN for those regions.
        sectors: ordered sector list (column names for features).

    This gives H1-neural and H2-neural the same input dimensionality while
    preserving sector-level structure that a 1-hop MLP can exploit.
    """
    sectors = eligible_sectors(panel, country)
    region_order = sorted(
        panel[panel["country"].eq(country)]["region_id"].unique()
    )
    n_r = len(region_order)
    n_s = len(sectors)
    features = np.full((n_r, n_s), np.nan)

    for si, s in enumerate(sectors):
        adj, _ = build_sector_graph(
            panel, country, s, eval_year,
            permute_mode=permute_mode, rng=rng,
        )
        x = sector_growth_features(panel, country, s, eval_year, region_order)
        h = message_pass_1hop(x, adj, identity_graph=identity_graph)
        m = structural_mask(panel, country, s, region_order)
        for r in range(n_r):
            if m[r] > 0:
                features[r, si] = h[r]  # NaN where data gap; never zero
            # m[r] == 0: structural absence, column stays NaN

    return region_order, features, sectors
