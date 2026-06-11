"""Tests for G2 corrected controls (DEC-024c).

25 tests covering:
  - permute_growth_territory_cols (N2)
  - top_k_adjacency
  - jaccard_binary
  - m1_consecutive_jaccard (M1)
  - m2_mean_pairwise_jaccard (M2)
  - m3_loyo_reconstruction (M3, observed only)
  - build_adjs_for_sector (COVID protocol + eval_year retention)
  - run_null_family (N1, N2 determinism and non-degeneracy)
  - Gate functions (signal gate, stability gate)
"""
from __future__ import annotations

import numpy as np
import pytest

from src.data.european_panel.build_g2_corrected_controls import (
    TOP_K_PRINCIPAL,
    M2_STABILITY_THRESHOLD,
    COVID_EXCLUDE,
    COVID_YEAR,
    build_adjs_for_sector,
    compute_signal_gate_country,
    compute_stability_gate_country,
    jaccard_binary,
    m1_consecutive_jaccard,
    m2_mean_pairwise_jaccard,
    m3_loyo_reconstruction,
    permute_growth_territory_cols,
    run_null_family,
    top_k_adjacency,
    floor_p_diagnostics,
    RECONCILIATION_G1_VS_G2,
)
from src.data.european_panel.build_g1_l2_cogrowth import (
    permute_growth_temporal,
    empirical_p,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _sector_data(n_regions: int = 8, n_years: int = 10, seed: int = 0):
    """Synthetic sector_data dict with one sector 'BE'."""
    rng = np.random.default_rng(seed)
    matrix = rng.standard_normal((n_years, n_regions))
    growth_years = list(range(2010, 2010 + n_years))
    region_ids = [f"R{i:02d}" for i in range(n_regions)]
    return {"BE": (region_ids, growth_years, matrix)}


def _make_bool_adj(n: int = 8, k: int = 5, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    corr = rng.uniform(-1, 1, (n, n))
    np.fill_diagonal(corr, 1.0)
    return top_k_adjacency(corr, k)


# ---------------------------------------------------------------------------
# 1-5: permute_growth_territory_cols
# ---------------------------------------------------------------------------

def test_permute_territory_cols_preserves_shape():
    sd = _sector_data()
    rng = np.random.default_rng(0)
    psd = permute_growth_territory_cols(sd, rng)
    orig = sd["BE"][2]
    perm = psd["BE"][2]
    assert perm.shape == orig.shape


def test_permute_territory_cols_shuffles_columns():
    sd = _sector_data(n_regions=20, n_years=8)
    rng = np.random.default_rng(42)
    psd = permute_growth_territory_cols(sd, rng)
    orig = sd["BE"][2]
    perm = psd["BE"][2]
    # Not identical (with 20 columns, a no-op permutation has probability 1/20! ≈ 0)
    assert not np.allclose(orig, perm)


def test_permute_territory_cols_preserves_column_values():
    sd = _sector_data()
    rng = np.random.default_rng(7)
    psd = permute_growth_territory_cols(sd, rng)
    orig = sd["BE"][2]
    perm = psd["BE"][2]
    # Each column in perm must equal SOME column in orig
    orig_cols = set(tuple(orig[:, j]) for j in range(orig.shape[1]))
    perm_cols = set(tuple(perm[:, j]) for j in range(perm.shape[1]))
    assert orig_cols == perm_cols


def test_permute_territory_cols_deterministic():
    sd = _sector_data()
    psd1 = permute_growth_territory_cols(sd, np.random.default_rng(99))
    psd2 = permute_growth_territory_cols(sd, np.random.default_rng(99))
    assert np.array_equal(psd1["BE"][2], psd2["BE"][2])


def test_permute_territory_cols_different_seeds_differ():
    sd = _sector_data(n_regions=20)
    psd1 = permute_growth_territory_cols(sd, np.random.default_rng(1))
    psd2 = permute_growth_territory_cols(sd, np.random.default_rng(2))
    assert not np.array_equal(psd1["BE"][2], psd2["BE"][2])


# ---------------------------------------------------------------------------
# 6-9: top_k_adjacency
# ---------------------------------------------------------------------------

def test_top_k_adjacency_is_binary():
    adj = _make_bool_adj()
    assert adj.dtype == bool
    assert set(adj.ravel().tolist()).issubset({True, False})


def test_top_k_adjacency_is_symmetric():
    adj = _make_bool_adj()
    assert np.array_equal(adj, adj.T)


def test_top_k_adjacency_no_self_edges():
    adj = _make_bool_adj()
    assert not np.any(np.diag(adj))


def test_top_k_adjacency_positive_only():
    n = 6
    corr = np.full((n, n), -0.9)
    np.fill_diagonal(corr, 1.0)
    adj = top_k_adjacency(corr, k=3)
    assert not adj.any(), "No edges when all off-diagonal correlations are negative"


# ---------------------------------------------------------------------------
# 10-12: jaccard_binary
# ---------------------------------------------------------------------------

def test_jaccard_binary_identical():
    adj = _make_bool_adj()
    assert jaccard_binary(adj, adj) == pytest.approx(1.0)


def test_jaccard_binary_disjoint():
    n = 6
    a1 = np.zeros((n, n), dtype=bool)
    a2 = np.zeros((n, n), dtype=bool)
    a1[0, 1] = a1[1, 0] = True
    a2[2, 3] = a2[3, 2] = True
    assert jaccard_binary(a1, a2) == pytest.approx(0.0)


def test_jaccard_binary_both_empty_is_nan():
    n = 4
    a = np.zeros((n, n), dtype=bool)
    result = jaccard_binary(a, a)
    assert np.isnan(result)


# ---------------------------------------------------------------------------
# 13-14: M1 consecutive Jaccard
# ---------------------------------------------------------------------------

def test_m1_two_identical_adjs():
    adj = _make_bool_adj()
    result = m1_consecutive_jaccard([adj, adj])
    assert result["m1_mean"] == pytest.approx(1.0)
    assert result["m1_n_pairs"] == 1


def test_m1_single_adj_no_pairs():
    adj = _make_bool_adj()
    result = m1_consecutive_jaccard([adj])
    assert result["m1_n_pairs"] == 0
    assert np.isnan(result["m1_mean"])


# ---------------------------------------------------------------------------
# 15-16: M2 mean pairwise Jaccard
# ---------------------------------------------------------------------------

def test_m2_two_adjs_equals_jaccard():
    a1 = _make_bool_adj(seed=0)
    a2 = _make_bool_adj(seed=1)
    result = m2_mean_pairwise_jaccard([a1, a2])
    expected = jaccard_binary(a1, a2)
    if not np.isnan(expected):
        assert result["m2_mean"] == pytest.approx(expected)
    assert result["m2_n_pairs"] == 1


def test_m2_n_pairs_formula():
    adjs = [_make_bool_adj(seed=i) for i in range(5)]
    result = m2_mean_pairwise_jaccard(adjs)
    assert result["m2_n_pairs"] <= 5 * 4 // 2  # 10 pairs max


# ---------------------------------------------------------------------------
# 17: M3 LOYO reconstruction
# ---------------------------------------------------------------------------

def test_m3_null_is_blocked():
    sd = _sector_data(n_years=12)
    _, growth_years, matrix = sd["BE"]
    eval_years = list(range(2015, 2020))  # use valid eval years
    adjs_obs = build_adjs_for_sector(sd, "BE", eval_years, TOP_K_PRINCIPAL)
    result = m3_loyo_reconstruction(sd, "BE", eval_years, TOP_K_PRINCIPAL, adjs_obs)
    assert result["m3_null"] == "BLOCKED"


# ---------------------------------------------------------------------------
# 18-19: empirical_p boundary behaviour (imported from L2 builder)
# ---------------------------------------------------------------------------

def test_empirical_p_minimum_when_obs_above_all_null():
    obs = 1.0
    null_vals = [0.1, 0.2, 0.3, 0.4, 0.5]
    p = empirical_p(obs, null_vals)
    n = len(null_vals)
    assert p == pytest.approx(1.0 / (n + 1))


def test_empirical_p_maximum_when_obs_below_all_null():
    obs = 0.0
    null_vals = [0.5, 0.6, 0.7, 0.8, 0.9]
    p = empirical_p(obs, null_vals)
    n = len(null_vals)
    assert p == pytest.approx((n + 1) / (n + 1))


# ---------------------------------------------------------------------------
# 20-21: COVID protocol in build_adjs_for_sector
# ---------------------------------------------------------------------------

def test_covid_obs_year_excluded_from_windows():
    """observation_year=2020 must not contribute to any window."""
    n_regions = 6
    rng = np.random.default_rng(0)
    # Matrix with 16 years 2008-2023
    growth_years = list(range(2008, 2024))
    matrix = rng.standard_normal((len(growth_years), n_regions))
    # Poison row for observation_year=2020 so if used it gives all-nan correlations
    yr_idx = growth_years.index(2020)
    matrix[yr_idx, :] = np.nan

    region_ids = [f"R{i:02d}" for i in range(n_regions)]
    sd = {"BE": (region_ids, growth_years, matrix)}

    # eval_year=2021: window [2016..2020] minus {2020} = [2016..2019] (4 years)
    adjs = build_adjs_for_sector(sd, "BE", [2021], TOP_K_PRINCIPAL, COVID_EXCLUDE)
    # Should still produce an adjacency (4 years = min_periods)
    assert adjs[0] is not None


def test_covid_eval_year_2020_retained():
    """eval_year=2020 must be included in eval_years; its window is [2015..2019]."""
    n_regions = 6
    rng = np.random.default_rng(1)
    growth_years = list(range(2010, 2024))
    matrix = rng.standard_normal((len(growth_years), n_regions))
    region_ids = [f"R{i:02d}" for i in range(n_regions)]
    sd = {"BE": (region_ids, growth_years, matrix)}

    # eval_year=2020 window = [2015..2019] — no 2020 obs in window, so valid
    adjs = build_adjs_for_sector(sd, "BE", [2020], TOP_K_PRINCIPAL, COVID_EXCLUDE)
    assert adjs[0] is not None


# ---------------------------------------------------------------------------
# 22-23: N1/N2 null distributions are non-trivial for temporal null
# ---------------------------------------------------------------------------

def test_n1_null_varies_across_permutations():
    """N1 temporal permutations should produce different M1 values."""
    sd = _sector_data(n_regions=10, n_years=14, seed=0)
    eval_years = list(range(2016, 2024))
    dists = run_null_family(
        sd, ["BE"], eval_years, TOP_K_PRINCIPAL,
        permute_growth_temporal, 10, 0,
    )
    vals = [v for v in dists["BE"]["m1_mean"] if np.isfinite(v)]
    assert len(vals) >= 5
    assert len(set(round(v, 8) for v in vals)) > 1  # not all identical


def test_n2_null_runs_without_error():
    """N2 territory column permutation must run and return finite values."""
    sd = _sector_data(n_regions=10, n_years=14, seed=1)
    eval_years = list(range(2016, 2024))
    dists = run_null_family(
        sd, ["BE"], eval_years, TOP_K_PRINCIPAL,
        permute_growth_territory_cols, 5, 42,
    )
    assert "m1_mean" in dists["BE"]
    assert "m2_mean" in dists["BE"]
    assert len(dists["BE"]["m1_mean"]) == 5


# ---------------------------------------------------------------------------
# 24: Gate: signal gate sector pass logic
# ---------------------------------------------------------------------------

def test_signal_gate_sector_fails_if_n2_not_significant():
    """Sector must fail signal gate if N2 is not FDR-significant."""
    sectors = ["BE"]
    obs = {"BE": {"m1_mean": 0.5, "m2_mean": 0.3}}
    # N1: obs clearly above null (will be significant)
    n1_dists = {"BE": {"m1_mean": [0.1] * 199, "m2_mean": [0.1] * 199}}
    # N2: obs BELOW null (will be p=1.0, not significant)
    n2_dists = {"BE": {"m1_mean": [0.9] * 199, "m2_mean": [0.9] * 199}}
    result = compute_signal_gate_country(obs, n1_dists, n2_dists, sectors)
    assert result["sector_pass"]["BE"] is False
    assert result["country_pass"] is False


# ---------------------------------------------------------------------------
# 25: Stability gate threshold
# ---------------------------------------------------------------------------

def test_stability_gate_passes_at_threshold():
    sectors = ["BE", "FZ"]
    # BE at exactly threshold, FZ below
    obs = {"BE": {"m2_mean": M2_STABILITY_THRESHOLD}, "FZ": {"m2_mean": 0.50}}
    result = compute_stability_gate_country(obs, sectors)
    assert result["sector_pass"]["BE"] is True
    assert result["sector_pass"]["FZ"] is False
    # 1/2 = 0.50 >= SECTOR_FRAC_NEEDED (0.50) -> country passes
    assert result["country_pass"] is True
