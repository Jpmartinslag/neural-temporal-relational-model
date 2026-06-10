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
    PERSISTENCE_THRESHOLD,
    LOYO_STABILITY_MIN,
    TURNOVER_STABLE_MAX,
    WEIGHT_CHANGE_THRESHOLD,
    PT_EXCLUDED_SECTORS,
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
