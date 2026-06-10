"""Tests for G1-L2 causal co-growth builder.

Covers leakage (eval_year never uses same-year growth), alignment
(growth matrix correctly filtered by mask), determinism, COVID exclusion
correctness, bootstrap propagation, gate fail-closed behaviour, and
no-future data guarantee.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.european_panel.build_g1_l2_cogrowth import (
    _country_pass_gate,
    bh_fdr,
    bootstrap_edge_stability,
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
    window_years_used,
)


# ---------------------------------------------------------------------------
# Minimal panel fixture
# ---------------------------------------------------------------------------

def _make_panel() -> pd.DataFrame:
    """Three-region, two-sector, nine-year panel (2010–2018) with random growth."""
    regions = ["R1", "R2", "R3"]
    sectors = ["BE", "FZ"]
    years = list(range(2010, 2019))  # 9 observation years (2010..2018)
    rng = np.random.default_rng(0)
    rows = []
    for s in sectors:
        for r in regions:
            for y in years:
                rows.append(
                    {
                        "country": "XX",
                        "region_id": r,
                        "sector_a10": s,
                        "observation_year": y,
                        "sector_growth_1y": float(rng.uniform(-0.1, 0.3)),
                        "mask_sector_supported": 1,
                    }
                )
    return pd.DataFrame(rows)


def _sector_data(panel: pd.DataFrame) -> dict:
    return {s: build_growth_matrix(panel, "XX", s) for s in ["BE", "FZ"]}


# ---------------------------------------------------------------------------
# Leakage: eval_year never in its own window
# ---------------------------------------------------------------------------

def test_no_leakage_in_window() -> None:
    """window_matrix for eval_year t must not contain t."""
    panel = _make_panel()
    region_ids, growth_years, matrix = build_growth_matrix(panel, "XX", "BE")
    for eval_year in [2015, 2016, 2017, 2018, 2019]:
        used = window_years_used(growth_years, eval_year, window=5)
        assert eval_year not in used, (
            f"eval_year {eval_year} leaked into its own window"
        )


def test_window_never_exceeds_eval_minus_1() -> None:
    growth_years = list(range(2010, 2020))
    matrix = np.ones((len(growth_years), 2))
    for t in [2015, 2016, 2019]:
        w = window_matrix(growth_years, matrix, t, window=5)
        assert w.shape[0] <= 5
        assert all(growth_years[i] < t for i in range(w.shape[0]))


def test_no_future_data_in_window() -> None:
    """No window row corresponds to observation_year >= eval_year."""
    panel = _make_panel()
    sd = _sector_data(panel)
    eval_years = eval_years_for_country(sd, ["BE", "FZ"], window=5)
    for t in eval_years:
        for sector in ["BE", "FZ"]:
            _, gy, _ = sd[sector]
            used = window_years_used(gy, t, window=5)
            assert all(y < t for y in used), (
                f"Sector {sector}, eval_year {t}: future year in window {used}"
            )


# ---------------------------------------------------------------------------
# COVID: 2020 excluded from windows but eval_year=2020 retained
# ---------------------------------------------------------------------------

def test_covid_year_never_in_window_when_excluded() -> None:
    """When exclude_years={2020}, 2020 must not appear in any window."""
    growth_years = list(range(2010, 2027))
    matrix = np.ones((len(growth_years), 2))
    for eval_year in range(2015, 2028):
        used = window_years_used(
            growth_years, eval_year, window=5, exclude_years=frozenset({2020})
        )
        assert 2020 not in used, (
            f"2020 appeared in window for eval_year={eval_year}: {used}"
        )


def test_eval_year_2020_retained_under_covid_exclusion() -> None:
    """eval_year=2020's window is [2015..2019]; 2020 is not in window regardless."""
    growth_years = list(range(2010, 2027))
    matrix = np.ones((len(growth_years), 2))
    # Without exclusion
    used_full = window_years_used(growth_years, 2020, window=5)
    assert 2020 not in used_full  # causal: window is [2015..2019]
    assert used_full == [2015, 2016, 2017, 2018, 2019]
    # With exclusion — identical, because 2020 was not in the window anyway
    used_excl = window_years_used(
        growth_years, 2020, window=5, exclude_years=frozenset({2020})
    )
    assert used_excl == used_full


def test_eval_year_2020_not_removed_from_eval_years() -> None:
    """eval_years_for_country must include 2020 even when exclude_years={2020}
    is passed later to window_matrix (eval_years are determined independently)."""
    panel = _make_panel()
    # Add 2020 growth data so eval_year 2025 is possible
    extra = []
    for s in ["BE", "FZ"]:
        for r in ["R1", "R2", "R3"]:
            for y in range(2019, 2022):
                extra.append(
                    {"country": "XX", "region_id": r, "sector_a10": s,
                     "observation_year": y, "sector_growth_1y": 0.1,
                     "mask_sector_supported": 1}
                )
    panel2 = pd.concat([panel, pd.DataFrame(extra)], ignore_index=True).drop_duplicates(
        ["country", "region_id", "sector_a10", "observation_year"]
    )
    sd = {s: build_growth_matrix(panel2, "XX", s) for s in ["BE", "FZ"]}
    eval_yrs = eval_years_for_country(sd, ["BE", "FZ"], window=5)
    # eval_years_for_country never sees exclude_years, so 2020 must appear
    # if growth data covers the needed range
    # Growth years include 2019 => eval_year 2024 is min eval; 2020 in range => included
    if 2020 in range(eval_yrs[0], eval_yrs[-1] + 1):
        assert 2020 in eval_yrs, "eval_year=2020 wrongly removed"


def test_window_for_2021_loses_2020() -> None:
    """eval_year=2021 window: [2016..2020] → [2016,2017,2018,2019] when 2020 excluded."""
    growth_years = list(range(2010, 2027))
    used = window_years_used(
        growth_years, 2021, window=5, exclude_years=frozenset({2020})
    )
    assert 2020 not in used
    assert sorted(used) == [2016, 2017, 2018, 2019]


# ---------------------------------------------------------------------------
# Bootstrap propagates exclude_years
# ---------------------------------------------------------------------------

def test_bootstrap_respects_exclude_years() -> None:
    """Bootstrap windows must not use excluded years."""
    panel = _make_panel()
    # Add years 2019-2021 to the panel to make COVID windows testable
    extra = []
    for s in ["BE", "FZ"]:
        for r in ["R1", "R2", "R3"]:
            for y in range(2019, 2023):
                extra.append(
                    {"country": "XX", "region_id": r, "sector_a10": s,
                     "observation_year": y, "sector_growth_1y": float(y % 3) * 0.1,
                     "mask_sector_supported": 1}
                )
    panel2 = pd.concat([panel, pd.DataFrame(extra)], ignore_index=True).drop_duplicates(
        ["country", "region_id", "sector_a10", "observation_year"]
    )
    sd = {s: build_growth_matrix(panel2, "XX", s) for s in ["BE", "FZ"]}
    eval_yrs = eval_years_for_country(sd, ["BE", "FZ"], window=5)

    rng = np.random.default_rng(7)
    # We can't inspect internal window calls, so we verify via indirect test:
    # pairwise_corr with 3 rows (2020 excluded) vs 4 rows (2020 included)
    # For eval_year=2021: without exclusion → 5 years; with → 4 years
    _, gy, mat = sd["BE"]
    w_full = window_matrix(gy, mat, 2021, window=5)
    w_excl = window_matrix(gy, mat, 2021, window=5, exclude_years=frozenset({2020}))
    if 2020 in set(gy):
        assert w_full.shape[0] > w_excl.shape[0], "exclusion should reduce window size"
    assert 2020 not in window_years_used(gy, 2021, window=5, exclude_years=frozenset({2020}))

    # Run bootstrap and ensure it doesn't crash with exclusion
    result = bootstrap_edge_stability(
        sd, ["BE", "FZ"], eval_yrs, rng, window=5,
        n_bootstraps=5, exclude_years=frozenset({2020})
    )
    assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# Gate fail-closed
# ---------------------------------------------------------------------------

def test_gate_fail_closed_zero_stable_edges() -> None:
    """Gate fails if stable_edge_count == 0 even if q and LOYO pass."""
    row = {
        "temporal_q": 0.005,
        "territory_q": 0.005,
        "leave_one_year_direction_pass": True,
        "stable_edge_count": 0,
    }
    assert not _country_pass_gate(row)


def test_gate_fail_closed_loyo_false() -> None:
    row = {
        "temporal_q": 0.005,
        "territory_q": 0.005,
        "leave_one_year_direction_pass": False,
        "stable_edge_count": 5,
    }
    assert not _country_pass_gate(row)


def test_gate_fail_closed_high_q() -> None:
    row = {
        "temporal_q": 0.5,
        "territory_q": 0.005,
        "leave_one_year_direction_pass": True,
        "stable_edge_count": 5,
    }
    assert not _country_pass_gate(row)


def test_gate_pass_all_criteria_met() -> None:
    row = {
        "temporal_q": 0.005,
        "territory_q": 0.005,
        "leave_one_year_direction_pass": True,
        "stable_edge_count": 3,
    }
    assert _country_pass_gate(row)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_temporal_permutation_deterministic() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    rng_a = np.random.default_rng(42)
    rng_b = np.random.default_rng(42)
    perm_a = permute_growth_temporal(sd, rng_a)
    perm_b = permute_growth_temporal(sd, rng_b)
    for s in ["BE", "FZ"]:
        assert np.allclose(perm_a[s][2], perm_b[s][2], equal_nan=True)


def test_territory_permutation_deterministic() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    rng_a = np.random.default_rng(99)
    rng_b = np.random.default_rng(99)
    perm_a = permute_growth_territory(sd, rng_a)
    perm_b = permute_growth_territory(sd, rng_b)
    for s in ["BE", "FZ"]:
        assert np.allclose(perm_a[s][2], perm_b[s][2], equal_nan=True)


def test_bootstrap_deterministic_with_same_seed() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    eval_yrs = eval_years_for_country(sd, ["BE", "FZ"], window=5)
    rng_a = np.random.default_rng(42)
    rng_b = np.random.default_rng(42)
    r_a = bootstrap_edge_stability(sd, ["BE", "FZ"], eval_yrs, rng_a, n_bootstraps=10)
    r_b = bootstrap_edge_stability(sd, ["BE", "FZ"], eval_yrs, rng_b, n_bootstraps=10)
    assert r_a.shape == r_b.shape
    if not r_a.empty:
        assert (
            r_a.sort_values(["sector", "source_region", "target_region"]).reset_index(drop=True)
            .equals(r_b.sort_values(["sector", "source_region", "target_region"]).reset_index(drop=True))
        )


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def test_build_growth_matrix_respects_mask() -> None:
    """Only rows with mask_sector_supported=1 enter the growth matrix."""
    panel = _make_panel().copy()
    mask = panel["sector_a10"].eq("BE") & panel["region_id"].eq("R1")
    panel.loc[mask, "mask_sector_supported"] = 0
    region_ids, _, _ = build_growth_matrix(panel, "XX", "BE")
    assert "R1" not in region_ids


def test_eval_years_cover_expected_range() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    eval_yrs = eval_years_for_country(sd, ["BE", "FZ"], window=5)
    # growth years 2010-2018; first eval = 2010+5=2015; last = 2018+1=2019
    assert min(eval_yrs) == 2015
    assert max(eval_yrs) == 2019


def test_l2_edge_vector_length_consistent() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    vec = l2_edge_vector(sd, ["BE", "FZ"], eval_year=2017, window=5)
    n = len(sd["BE"][0])
    expected = n * (n - 1) // 2 * 2
    assert vec.shape[0] == expected


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def test_empirical_p_finite_sample_correction() -> None:
    null = [0.1, 0.2, 0.3, 0.4, 0.5]
    p = empirical_p(0.3, null)
    assert p == (1 + 3) / (1 + 5)


def test_empirical_p_always_positive() -> None:
    assert empirical_p(1.0, [0.1, 0.2]) > 0


def test_bh_fdr_monotone_adjustment() -> None:
    p_vals = [0.01, 0.04, 0.2, 0.8]
    adj = bh_fdr(p_vals)
    assert all(a >= p for a, p in zip(adj, p_vals))
    assert all(0 < a <= 1 for a in adj)


def test_pairwise_corr_returns_nan_below_min_periods() -> None:
    mat = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = pairwise_corr(mat, min_periods=4)
    assert np.all(np.isnan(result))


def test_pairwise_corr_perfect_correlation() -> None:
    mat = np.column_stack([np.arange(1.0, 6.0), np.arange(2.0, 7.0)])
    result = pairwise_corr(mat, min_periods=4)
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
    assert len(triu) == 6  # 4*(4-1)/2


# ---------------------------------------------------------------------------
# Permutation preserves structure
# ---------------------------------------------------------------------------

def test_temporal_permutation_preserves_column_values() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    rng = np.random.default_rng(1)
    perm_data = permute_growth_temporal(sd, rng)
    _, _, orig = sd["BE"]
    _, _, perm = perm_data["BE"]
    assert orig.shape == perm.shape
    for col in range(orig.shape[1]):
        assert np.allclose(sorted(orig[:, col]), sorted(perm[:, col]))


def test_territory_permutation_preserves_row_values() -> None:
    panel = _make_panel()
    sd = _sector_data(panel)
    rng = np.random.default_rng(2)
    perm_data = permute_growth_territory(sd, rng)
    _, _, orig = sd["BE"]
    _, _, perm = perm_data["BE"]
    assert orig.shape == perm.shape
    for row in range(orig.shape[0]):
        assert np.allclose(sorted(orig[row, :]), sorted(perm[row, :]))
