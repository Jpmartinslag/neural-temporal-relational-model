"""Tests for G2 temporal preflight metrics.

Validates: top-k construction, persistence, turnover, LOYO, COVID comparison,
falsifiable-criteria thresholds, PT KZ exclusion, no causal claims.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.build_g2_temporal_preflight import (
    _top_k_symmetric,
    _adj_matrix,
    jaccard_adjacency,
    pearson_adj,
    run_preflight,
    TOP_K_DEFAULT,
    TOP_K_VARIANTS,
    PERSISTENCE_THRESHOLD,
    LOYO_STABILITY_MIN,
    TURNOVER_STABLE_MAX,
    WEIGHT_CHANGE_THRESHOLD,
    PT_EXCLUDED_SECTORS,
    _bh_fdr_reject,
    _loyo_jaccard_binary,
    _pivot_weights_mat,
    _reconstruct_adjs_from_W,
    _permute_W,
    _evaluate_neg_ctrl_gate,
    run_negative_control,
    NEG_CTRL_FDR_Q,
    NEG_CTRL_COUNTRIES_NEEDED,
    NEG_CTRL_SECTOR_FRAC_NEEDED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_edges(
    countries=("NL",),
    sectors=("BE",),
    years=(2018, 2019, 2020, 2021),
    n_regions=5,
    weight_fn=None,
):
    """Synthetic edge dataframe (all pairs, directed)."""
    rows = []
    regions = [f"R{i:02d}" for i in range(n_regions)]
    for c in countries:
        for s in sectors:
            if c == "PT" and s in PT_EXCLUDED_SECTORS:
                continue
            for yr in years:
                for i, r1 in enumerate(regions):
                    for j, r2 in enumerate(regions):
                        if i == j:
                            continue
                        w = 0.5 if weight_fn is None else weight_fn(i, j, yr)
                        rows.append({
                            "country": c, "sector": s,
                            "available_for_forecast_year": yr,
                            "source_region": r1,
                            "target_region": r2,
                            "weight_cogrowth": w,
                        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# top-k construction
# ---------------------------------------------------------------------------

def test_top_k_symmetric_positive_only():
    n = 5
    corr = np.random.default_rng(0).uniform(-1, 1, (n, n))
    np.fill_diagonal(corr, 1.0)
    adj = _top_k_symmetric(corr, k=2)
    assert (adj >= 0).all(), "adj must be non-negative"
    assert np.allclose(adj, adj.T), "adj must be symmetric"
    # All non-zero entries must have been positive in corr
    mask = adj > 0
    for i, j in zip(*np.where(mask)):
        assert corr[i, j] > 0 or corr[j, i] > 0


def test_top_k_symmetric_zero_when_all_negative():
    n = 4
    corr = np.full((n, n), -0.5)
    np.fill_diagonal(corr, 1.0)
    adj = _top_k_symmetric(corr, k=2)
    upper = np.triu(adj, k=1)
    assert upper.sum() == 0.0, "all-negative corr → zero adj"


def test_top_k_respects_k():
    n = 8
    corr = np.random.default_rng(7).uniform(0.1, 0.9, (n, n))
    np.fill_diagonal(corr, 1.0)
    adj = _top_k_symmetric(corr, k=3)
    for i in range(n):
        assert (adj[i] > 0).sum() <= 2 * 3, f"row {i} has too many positive entries"


def test_adj_matrix_correct_shape():
    regions = ["R0", "R1", "R2"]
    n = len(regions)
    edges = make_edges(n_regions=n, years=[2020])
    sub = edges[edges["available_for_forecast_year"] == 2020]
    adj = _adj_matrix(sub, regions, k=2)
    assert adj.shape == (n, n)
    assert np.allclose(adj, adj.T)


# ---------------------------------------------------------------------------
# Jaccard and Pearson
# ---------------------------------------------------------------------------

def test_jaccard_identical():
    # Use adj with actual off-diagonal edges (eye has no upper-triangle edges)
    adj = np.array([[0, 0.5, 0, 0.3], [0.5, 0, 0.4, 0],
                    [0, 0.4, 0, 0.6], [0.3, 0, 0.6, 0]], dtype=float)
    assert jaccard_adjacency(adj, adj) == pytest.approx(1.0)


def test_jaccard_disjoint():
    a1 = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=float)
    a2 = np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]], dtype=float)
    assert jaccard_adjacency(a1, a2) == pytest.approx(0.0)


def test_jaccard_partial():
    a1 = np.array([[0, 1, 1], [1, 0, 0], [1, 0, 0]], dtype=float)
    a2 = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)
    j = jaccard_adjacency(a1, a2)
    assert 0.0 < j < 1.0


def test_pearson_identical():
    adj = np.array([[0, 0.3, 0.7], [0.3, 0, 0.5], [0.7, 0.5, 0]])
    p = pearson_adj(adj, adj)
    assert p == pytest.approx(1.0, abs=1e-6)


def test_pearson_constant_returns_nan():
    adj = np.zeros((3, 3))
    p = pearson_adj(adj, adj)
    assert np.isnan(p)


# ---------------------------------------------------------------------------
# run_preflight structural checks
# ---------------------------------------------------------------------------

def test_run_preflight_returns_all_keys():
    edges = make_edges(years=[2018, 2019, 2020, 2021, 2022])
    dfs = run_preflight(edges)
    for key in ["inventory", "density", "persistence", "turnover",
                "variation", "topk_sensitivity", "loyo", "covid_comparison"]:
        assert key in dfs, f"missing key: {key}"


def test_run_preflight_inventory_counts_correct():
    years = [2018, 2019, 2020]
    edges = make_edges(countries=["NL", "FR"], sectors=["BE", "FZ"], years=years)
    dfs = run_preflight(edges)
    inv = dfs["inventory"]
    # 2 countries × 2 sectors = 4 combos
    assert len(inv) == 4
    assert set(inv["country"]) == {"NL", "FR"}


def test_run_preflight_pt_excludes_kz():
    edges = make_edges(countries=["PT"], sectors=["BE", "KZ"], years=[2019, 2020, 2021, 2022])
    dfs = run_preflight(edges)
    sectors_seen = set(dfs["inventory"]["sector"])
    assert "KZ" not in sectors_seen, "KZ must be excluded for PT"


def test_run_preflight_no_nan_in_density():
    edges = make_edges(years=[2018, 2019, 2020, 2021])
    dfs = run_preflight(edges)
    for col in ["n_edges_topk5", "density"]:
        assert not dfs["density"][col].isna().any(), f"{col} must not be NaN"


def test_persistence_fraction_in_unit_interval():
    edges = make_edges(years=[2018, 2019, 2020, 2021, 2022])
    dfs = run_preflight(edges)
    pers = dfs["persistence"]
    assert ((pers["persistence"] >= 0) & (pers["persistence"] <= 1)).all()


def test_persistence_threshold_applied():
    # With constant weight=0.5 all pairs top-k same every year → persistence=1.0
    edges = make_edges(n_regions=4, years=[2018, 2019, 2020, 2021, 2022])
    dfs = run_preflight(edges)
    pers = dfs["persistence"]
    assert pers["persistent"].any(), "some edges should be persistent with constant weights"


def test_turnover_in_unit_interval():
    edges = make_edges(years=[2018, 2019, 2020, 2021])
    dfs = run_preflight(edges)
    turn = dfs["turnover"]
    assert ((turn["mean_turnover"] >= 0) & (turn["mean_turnover"] <= 1)).all()


def test_loyo_computed_for_sufficient_years():
    # Weights vary by (i,j,yr) to ensure non-zero Pearson between year adj matrices.
    # yr coefficient must be small (e.g. 0.02 per year-offset) to stay in [-0.9, 0.9].
    rng = np.random.default_rng(42)
    def wfn(i, j, yr):
        base = 0.1 * (i - j)  # pair-specific offset
        return float(np.clip(base + 0.02 * (yr - 2019) + 0.05 * rng.standard_normal(),
                             -0.9, 0.9))
    edges = make_edges(n_regions=6, years=[2017, 2018, 2019, 2020, 2021, 2022], weight_fn=wfn)
    dfs = run_preflight(edges)
    assert len(dfs["loyo"]) > 0, "LOYO should be computed with ≥4 years and varying weights"


def test_loyo_pearson_in_neg1_to_1():
    edges = make_edges(years=[2018, 2019, 2020, 2021, 2022])
    dfs = run_preflight(edges)
    loyo = dfs["loyo"]
    if loyo.empty:
        pytest.skip("no LOYO rows")
    assert ((loyo["mean_loyo_pearson"] >= -1) & (loyo["mean_loyo_pearson"] <= 1)).all()


def test_topk_sensitivity_jaccard_in_unit_interval():
    edges = make_edges(years=[2019, 2020])
    dfs = run_preflight(edges)
    topo = dfs["topk_sensitivity"]
    for col in ["jaccard_k3_k5", "jaccard_k5_k10"]:
        valid = topo[col].dropna()
        assert ((valid >= 0) & (valid <= 1)).all(), f"{col} out of [0,1]"


def test_covid_comparison_pre_post_difference():
    # Weight increases post-COVID
    def wfn(i, j, yr):
        return 0.3 if yr < 2021 else 0.7
    edges = make_edges(years=[2018, 2019, 2020, 2021, 2022, 2023], weight_fn=wfn)
    dfs = run_preflight(edges)
    cov = dfs["covid_comparison"]
    if cov.empty:
        pytest.skip("no covid comparison rows")
    row = cov.iloc[0]
    assert row["post_w_mean"] > row["pre_w_mean"], "post-COVID weight should be higher"


def test_no_country_pooling():
    edges = make_edges(countries=["NL", "FR"], years=[2019, 2020, 2021])
    dfs = run_preflight(edges)
    for name, df in dfs.items():
        if "country" in df.columns:
            assert len(df["country"].unique()) == 2, \
                f"{name}: country pooling detected"


# ---------------------------------------------------------------------------
# Falsifiable criteria constants
# ---------------------------------------------------------------------------

def test_falsifiable_criteria_values():
    assert 0 < PERSISTENCE_THRESHOLD <= 1
    assert 0 < WEIGHT_CHANGE_THRESHOLD <= 1
    assert 0 < LOYO_STABILITY_MIN <= 1
    assert 0 < TURNOVER_STABLE_MAX <= 1
    assert "KZ" in PT_EXCLUDED_SECTORS


# ---------------------------------------------------------------------------
# Negative control — unit tests
# ---------------------------------------------------------------------------

def make_nc_edges(n_regions=8, years=(2015, 2016, 2017, 2018, 2019, 2021),
                  weight_fn=None, countries=("NL",), sectors=("BE",)):
    """Synthetic edges for negative control tests (larger n_regions for stability)."""
    rows = []
    regions = [f"R{i:02d}" for i in range(n_regions)]
    for c in countries:
        for s in sectors:
            for yr in years:
                for i, r1 in enumerate(regions):
                    for j, r2 in enumerate(regions):
                        if i == j:
                            continue
                        w = 0.5 if weight_fn is None else weight_fn(i, j, yr)
                        rows.append({
                            "country": c, "sector": s,
                            "available_for_forecast_year": yr,
                            "source_region": r1, "target_region": r2,
                            "weight_cogrowth": w,
                        })
    return pd.DataFrame(rows)


def test_bh_fdr_all_significant():
    p = np.array([0.001, 0.002, 0.003, 0.004])
    reject = _bh_fdr_reject(p, q=0.05)
    assert reject.all(), "all small p-values should be rejected"


def test_bh_fdr_none_significant():
    p = np.array([0.9, 0.95, 0.99])
    reject = _bh_fdr_reject(p, q=0.05)
    assert not reject.any(), "large p-values should not be rejected"


def test_bh_fdr_partial():
    # 1 small + 3 large → only 1 rejected
    p = np.array([0.001, 0.5, 0.6, 0.8])
    reject = _bh_fdr_reject(p, q=0.05)
    assert reject.sum() == 1
    assert reject[0]


def test_bh_fdr_empty():
    reject = _bh_fdr_reject(np.array([]), q=0.05)
    assert len(reject) == 0


def test_loyo_jaccard_binary_too_few_years():
    B = np.zeros((3, 10), dtype=bool)
    assert _loyo_jaccard_binary(B) is None


def test_loyo_jaccard_binary_identical_graphs():
    # All years have the same binary adjacency → Jaccard=1.0
    B = np.ones((5, 20), dtype=bool)
    val = _loyo_jaccard_binary(B)
    assert val is not None
    assert val == pytest.approx(1.0)


def test_loyo_jaccard_binary_disjoint_graphs():
    # Each year has a unique non-overlapping edge set → all pairwise Jaccard=0
    n_years, edges_per_year = 5, 2
    B = np.zeros((n_years, n_years * edges_per_year), dtype=bool)
    for yi in range(n_years):
        B[yi, yi * edges_per_year: (yi + 1) * edges_per_year] = True
    val = _loyo_jaccard_binary(B)
    assert val is not None
    assert val == pytest.approx(0.0)


def test_pivot_weights_mat_shape():
    n_r = 5
    years = [2019, 2020, 2021]
    edges = make_nc_edges(n_regions=n_r, years=years)
    regions = [f"R{i:02d}" for i in range(n_r)]
    se = edges[(edges.country == "NL") & (edges.sector == "BE")]
    W = _pivot_weights_mat(se, regions, years)
    n_pairs = n_r * (n_r - 1) // 2
    assert W.shape == (n_pairs, len(years))


def test_pivot_weights_mat_mask_preserved_with_nan():
    """NaN introduced by dropping one year for one pair must survive pivot."""
    n_r = 4
    regions = [f"R{i:02d}" for i in range(n_r)]
    years = [2019, 2020, 2021]
    edges = make_nc_edges(n_regions=n_r, years=years)
    # Drop year 2020 for pair R00-R01
    mask = ~(
        (edges.source_region.isin(["R00", "R01"]))
        & (edges.target_region.isin(["R00", "R01"]))
        & (edges.available_for_forecast_year == 2020)
    )
    se = edges[mask & (edges.country == "NL") & (edges.sector == "BE")]
    W = _pivot_weights_mat(se, regions, years)
    year_idx_2020 = years.index(2020)
    pair_idx_01 = 0  # R00-R01 is first pair in upper triangle (i=0,j=1)
    assert np.isnan(W[pair_idx_01, year_idx_2020]), "missing pair-year should be NaN"
    # Other entries should be finite
    assert np.isfinite(W[pair_idx_01, years.index(2019)])


def test_permute_W_preserves_nan_mask():
    rng = np.random.default_rng(99)
    W = np.array([[0.1, np.nan, 0.3], [0.4, 0.5, 0.6]], dtype=float)
    W_p = _permute_W(W, rng)
    assert W_p.shape == W.shape
    # NaN positions must be preserved
    assert np.isnan(W_p[0, 1])
    # Non-NaN positions must remain non-NaN
    assert np.isfinite(W_p[0, 0]) and np.isfinite(W_p[0, 2])


def test_permute_W_marginal_distribution_preserved():
    rng = np.random.default_rng(7)
    W = np.arange(12, dtype=float).reshape(3, 4)
    W_p = _permute_W(W, rng)
    # Each row: same values, different order
    for row in range(3):
        assert sorted(W[row].tolist()) == sorted(W_p[row].tolist())


def test_reconstruct_adjs_from_W_shape():
    n_r = 5
    years = [2019, 2020, 2021, 2022]
    edges = make_nc_edges(n_regions=n_r, years=years)
    regions = [f"R{i:02d}" for i in range(n_r)]
    se = edges[(edges.country == "NL") & (edges.sector == "BE")]
    W = _pivot_weights_mat(se, regions, years)
    triu_i, triu_j = np.triu_indices(n_r, k=1)
    B = _reconstruct_adjs_from_W(W, n_r, years, k=3, triu_i=triu_i, triu_j=triu_j)
    n_pairs = n_r * (n_r - 1) // 2
    assert B.shape == (len(years), n_pairs), "B must be [n_years, n_pairs]"
    assert B.dtype == bool


def test_pvalue_never_zero():
    """With N permutations, minimum p = 1/(N+1) > 0."""
    edges = make_nc_edges(n_regions=6, years=[2015, 2016, 2017, 2018, 2019, 2021])
    nc = run_negative_control(edges, n_permutations=19, seed=0)
    if nc["results"].empty:
        pytest.skip("no results")
    assert (nc["results"]["p_value"] > 0).all(), "p-value must be strictly positive"


def test_pvalue_formula_correct():
    """p = (1 + count(null>=obs)) / (N+1): verify with known null."""
    # Build edges where weights vary with year so obs LOYO ≠ 0
    rng_w = np.random.default_rng(123)
    def wfn(i, j, yr):
        base = 0.3 * (i - j) / 10
        return float(np.clip(base + 0.01 * (yr - 2017) + 0.05 * rng_w.standard_normal(), -0.9, 0.9))
    edges = make_nc_edges(n_regions=6, years=[2015, 2016, 2017, 2018, 2019, 2021], weight_fn=wfn)
    nc = run_negative_control(edges, n_permutations=19, seed=42)
    if nc["results"].empty:
        pytest.skip("no results")
    for _, row in nc["results"].iterrows():
        # p must satisfy: 1/(N+1) ≤ p ≤ 1.0
        assert row["p_value"] >= 1 / (row["n_permutations_valid"] + 1), "p too small"
        assert row["p_value"] <= 1.0, "p > 1"


def test_determinism():
    edges = make_nc_edges(n_regions=6, years=[2015, 2016, 2017, 2018, 2019, 2021])
    nc1 = run_negative_control(edges, n_permutations=9, seed=77)
    nc2 = run_negative_control(edges, n_permutations=9, seed=77)
    if nc1["results"].empty:
        pytest.skip("no results")
    pd.testing.assert_frame_equal(nc1["results"], nc2["results"])


def test_gate_fail_closed_one_country():
    """Gate fails if only 1 country passes."""
    # Manufacture a DataFrame where only NL passes
    df = pd.DataFrame([
        {"country": "NL", "sector": "BE", "obs_loyo_jaccard": 0.5,
         "null_median": 0.1, "fdr_reject": True, "positive_effect": True},
        {"country": "NL", "sector": "FZ", "obs_loyo_jaccard": 0.5,
         "null_median": 0.1, "fdr_reject": True, "positive_effect": True},
        {"country": "FR", "sector": "BE", "obs_loyo_jaccard": 0.1,
         "null_median": 0.15, "fdr_reject": False, "positive_effect": False},
    ])
    gate, verdict = _evaluate_neg_ctrl_gate(df)
    assert not gate["pass"], "gate must fail with 1/3 countries"
    assert verdict == "G2_EDGE_DYNAMICS_NOT_SUPPORTED"


def test_gate_passes_two_countries():
    sectors = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
    rows = []
    for c in ["FR", "NL"]:
        for s in sectors:
            rows.append({"country": c, "sector": s,
                         "obs_loyo_jaccard": 0.5, "null_median": 0.1,
                         "fdr_reject": True, "positive_effect": True})
    for s in sectors:
        rows.append({"country": "PT", "sector": s,
                     "obs_loyo_jaccard": 0.1, "null_median": 0.2,
                     "fdr_reject": False, "positive_effect": False})
    df = pd.DataFrame(rows)
    gate, verdict = _evaluate_neg_ctrl_gate(df)
    assert gate["pass"], "gate must pass with 2/3 countries"
    assert verdict == "G2_EDGE_DYNAMICS_SUPPORTED"


def test_neg_ctrl_pt_excludes_kz():
    edges = make_nc_edges(countries=["PT"], sectors=["BE", "KZ"],
                          years=[2015, 2016, 2017, 2018, 2019, 2021])
    nc = run_negative_control(edges, n_permutations=9, seed=1)
    if nc["results"].empty:
        pytest.skip("no results")
    assert "KZ" not in nc["results"]["sector"].values, "KZ must be excluded for PT"


def test_neg_ctrl_topk_sensitivity():
    """run_negative_control produces sensitivity rows for k≠primary_k."""
    edges = make_nc_edges(n_regions=6, years=[2015, 2016, 2017, 2018, 2019, 2021])
    nc = run_negative_control(edges, n_permutations=9, top_k_list=[3, 5, 10], seed=2)
    if nc["sensitivity"].empty:
        pytest.skip("no sensitivity rows")
    k_vals = set(nc["sensitivity"]["top_k"].unique())
    assert k_vals <= {3, 10}, "sensitivity must cover k=3 and k=10 (not primary k=5)"


def test_neg_ctrl_no_nan_in_pvalue():
    edges = make_nc_edges(n_regions=6, years=[2015, 2016, 2017, 2018, 2019, 2021])
    nc = run_negative_control(edges, n_permutations=9, seed=3)
    if nc["results"].empty:
        pytest.skip("no results")
    assert not nc["results"]["p_value"].isna().any(), "p_value must not contain NaN"
    assert not nc["results"]["obs_loyo_jaccard"].isna().any()
    assert not nc["results"]["null_mean"].isna().any()


def test_neg_ctrl_country_sector_alignment():
    """Each result row has correct country/sector from input data."""
    edges = make_nc_edges(countries=["NL", "FR"], sectors=["BE"],
                          years=[2015, 2016, 2017, 2018, 2019, 2021])
    nc = run_negative_control(edges, n_permutations=9, seed=4)
    if nc["results"].empty:
        pytest.skip("no results")
    assert set(nc["results"]["country"].unique()) <= {"NL", "FR"}
    assert set(nc["results"]["sector"].unique()) <= {"BE"}
