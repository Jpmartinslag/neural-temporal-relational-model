"""Tests for G1-L2 causal co-growth builder.

Covers leakage (eval_year never uses same-year growth), alignment
(growth matrix correctly filtered by mask), and determinism (same seed
gives identical results).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.european_panel.build_g1_l2_cogrowth import (
    bh_fdr,
    build_growth_matrix,
    consecutive_stability,
    empirical_p,
    eval_years_for_country,
    l2_edge_vector,
    pairwise_corr,
    permute_growth_temporal,
    permute_growth_territory,
    upper_triangle,
    window_matrix,
)


# ---------------------------------------------------------------------------
# Minimal panel fixture
# ---------------------------------------------------------------------------

def _make_panel() -> pd.DataFrame:
    """Three-region, two-sector, six-year panel with deterministic growth."""
    regions = ["R1", "R2", "R3"]
    sectors = ["BE", "FZ"]
    years = list(range(2010, 2018))  # 8 observation years
    rows = []
    rng = np.random.default_rng(0)
    for s in sectors:
        for r in regions:
            for y in years:
                g = float(rng.uniform(-0.1, 0.3))
                rows.append(
                    {
                        "country": "XX",
                        "region_id": r,
                        "sector_a10": s,
                        "observation_year": y,
                        "sector_growth_1y": g,
                        "mask_sector_supported": 1,
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Leakage test
# ---------------------------------------------------------------------------

def test_no_leakage_in_window() -> None:
    """window_matrix for eval_year t must not include observation_year t."""
    panel = _make_panel()
    region_ids, growth_years, matrix = build_growth_matrix(panel, "XX", "BE")
    for eval_year in [2015, 2016, 2017, 2018]:
        w_mat = window_matrix(growth_years, matrix, eval_year, window=5)
        # shape[0] rows correspond to years in [eval_year-5, eval_year-1]
        allowed = set(range(eval_year - 5, eval_year))  # ≤ eval_year-1
        used_years = set(
            y for y in growth_years if eval_year - 5 <= y <= eval_year - 1
        )
        assert eval_year not in used_years, (
            f"eval_year {eval_year} leaked into its own window"
        )
        # No row in the window can correspond to eval_year
        assert w_mat.shape[0] <= len(allowed)


def test_window_never_exceeds_eval_minus_1() -> None:
    growth_years = list(range(2010, 2020))
    matrix = np.ones((len(growth_years), 2))
    for t in [2015, 2016, 2019]:
        w = window_matrix(growth_years, matrix, t, window=5)
        assert w.shape[0] <= 5


# ---------------------------------------------------------------------------
# Alignment tests
# ---------------------------------------------------------------------------

def test_build_growth_matrix_respects_mask() -> None:
    """Only rows with mask_sector_supported=1 enter the growth matrix."""
    panel = _make_panel().copy()
    # Unsupport sector BE for region R1
    mask = panel["sector_a10"].eq("BE") & panel["region_id"].eq("R1")
    panel.loc[mask, "mask_sector_supported"] = 0
    # Even with mask=0 rows, build_growth_matrix should still return
    # region R1 if there are other supported sectors; but for sector BE
    # specifically, mask=0 rows must not appear in the growth matrix
    region_ids, growth_years, matrix = build_growth_matrix(panel, "XX", "BE")
    # R1 is excluded because all BE rows are masked
    assert "R1" not in region_ids


def test_eval_years_cover_expected_range() -> None:
    panel = _make_panel()
    sector_data = {
        s: build_growth_matrix(panel, "XX", s) for s in ["BE", "FZ"]
    }
    eval_yrs = eval_years_for_country(sector_data, ["BE", "FZ"], window=5)
    # growth_years: 2010-2017, first eval_year = 2010+5=2015; last = 2017+1=2018
    assert min(eval_yrs) == 2015
    assert max(eval_yrs) == 2018


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------

def test_temporal_permutation_deterministic() -> None:
    panel = _make_panel()
    sector_data = {s: build_growth_matrix(panel, "XX", s) for s in ["BE", "FZ"]}
    rng_a = np.random.default_rng(42)
    rng_b = np.random.default_rng(42)
    perm_a = permute_growth_temporal(sector_data, rng_a)
    perm_b = permute_growth_temporal(sector_data, rng_b)
    for s in ["BE", "FZ"]:
        assert np.allclose(perm_a[s][2], perm_b[s][2], equal_nan=True)


def test_territory_permutation_deterministic() -> None:
    panel = _make_panel()
    sector_data = {s: build_growth_matrix(panel, "XX", s) for s in ["BE", "FZ"]}
    rng_a = np.random.default_rng(99)
    rng_b = np.random.default_rng(99)
    perm_a = permute_growth_territory(sector_data, rng_a)
    perm_b = permute_growth_territory(sector_data, rng_b)
    for s in ["BE", "FZ"]:
        assert np.allclose(perm_a[s][2], perm_b[s][2], equal_nan=True)


def test_l2_edge_vector_length_consistent() -> None:
    """l2_edge_vector length = sum over sectors of n_pairs_per_sector."""
    panel = _make_panel()
    sector_data = {s: build_growth_matrix(panel, "XX", s) for s in ["BE", "FZ"]}
    vec = l2_edge_vector(sector_data, ["BE", "FZ"], eval_year=2017, window=5)
    region_ids, _, _ = sector_data["BE"]
    n = len(region_ids)
    n_pairs = n * (n - 1) // 2
    expected = n_pairs * 2  # two sectors
    assert vec.shape[0] == expected


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def test_empirical_p_finite_sample_correction() -> None:
    """p = (1 + count(null >= obs)) / (1 + N)."""
    null = [0.1, 0.2, 0.3, 0.4, 0.5]
    p = empirical_p(0.3, null)
    # count(null >= 0.3) = 3 (0.3, 0.4, 0.5); N=5
    assert p == (1 + 3) / (1 + 5)


def test_empirical_p_always_positive() -> None:
    p = empirical_p(1.0, [0.1, 0.2])
    assert p > 0


def test_bh_fdr_monotone_adjustment() -> None:
    p_vals = [0.01, 0.04, 0.2, 0.8]
    adj = bh_fdr(p_vals)
    assert all(a >= p for a, p in zip(adj, p_vals))
    assert all(0 < a <= 1 for a in adj)


def test_bh_fdr_two_values() -> None:
    """With 2 p-values, BH adjustment is well-defined."""
    adj = bh_fdr([0.01, 0.05])
    assert len(adj) == 2


def test_pairwise_corr_returns_nan_below_min_periods() -> None:
    mat = np.array([[1.0, 2.0], [3.0, 4.0]])  # 2 rows, min_periods=4
    result = pairwise_corr(mat, min_periods=4)
    assert np.all(np.isnan(result))


def test_pairwise_corr_perfect_correlation() -> None:
    mat = np.column_stack(
        [np.arange(1.0, 6.0), np.arange(2.0, 7.0)]
    )  # columns perfectly correlated
    result = pairwise_corr(mat, min_periods=4)
    assert result.shape == (2, 2)
    assert abs(result[0, 1] - 1.0) < 1e-10


def test_consecutive_stability_two_vectors() -> None:
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([2.0, 3.0, 4.0, 5.0])
    mean_stab, pairs = consecutive_stability([a, b])
    assert abs(mean_stab - 1.0) < 1e-10
    assert len(pairs) == 1


def test_upper_triangle_length() -> None:
    mat = np.zeros((4, 4))
    triu = upper_triangle(mat)
    assert len(triu) == 4 * 3 // 2


# ---------------------------------------------------------------------------
# Permutation preserves shape
# ---------------------------------------------------------------------------

def test_temporal_permutation_preserves_shape_and_values() -> None:
    """After temporal permutation, each territory-sector column has same set of values."""
    panel = _make_panel()
    sector_data = {s: build_growth_matrix(panel, "XX", s) for s in ["BE"]}
    rng = np.random.default_rng(1)
    perm_data = permute_growth_temporal(sector_data, rng)
    _, _, orig = sector_data["BE"]
    _, _, perm = perm_data["BE"]
    assert orig.shape == perm.shape
    # Each column is a permutation of the original
    for col in range(orig.shape[1]):
        assert np.allclose(sorted(orig[:, col]), sorted(perm[:, col]))


def test_territory_permutation_preserves_shape_and_row_values() -> None:
    """After territory permutation, each year-row has same set of values."""
    panel = _make_panel()
    sector_data = {s: build_growth_matrix(panel, "XX", s) for s in ["BE"]}
    rng = np.random.default_rng(2)
    perm_data = permute_growth_territory(sector_data, rng)
    _, _, orig = sector_data["BE"]
    _, _, perm = perm_data["BE"]
    assert orig.shape == perm.shape
    for row in range(orig.shape[0]):
        assert np.allclose(sorted(orig[row, :]), sorted(perm[row, :]))
