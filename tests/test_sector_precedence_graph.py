import numpy as np
import pandas as pd

from src.data.european_panel.build_sector_precedence_graph import (
    bh_fdr,
    empirical_p,
    fit_partial_edge,
    pair_samples,
    permute_source_within_year,
    two_way_demean,
)


def synthetic_samples(beta: float = 0.7, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for territory in range(30):
        own = rng.normal(size=6)
        source = rng.normal(size=6)
        target = 0.4 * own + beta * source + rng.normal(scale=0.1, size=6)
        for year in range(2015, 2021):
            i = year - 2015
            rows.append({
                "territory_id": str(territory),
                "observation_year": year,
                "target_growth": target[i],
                "target_lag": own[i],
                "source_lag": source[i],
            })
    return pd.DataFrame(rows)


def test_partial_edge_recovers_positive_and_negative_sign():
    assert fit_partial_edge(synthetic_samples(0.7))["beta"] > 0.5
    assert fit_partial_edge(synthetic_samples(-0.7))["beta"] < -0.5


def test_partial_edge_controls_own_lag():
    result = fit_partial_edge(synthetic_samples(0.0))
    assert abs(result["beta"]) < 0.1
    assert result["delta_r2"] < 0.02


def test_two_way_demean_removes_group_means():
    x = np.arange(24, dtype=float).reshape(12, 2)
    territories = np.repeat(["a", "b", "c"], 4)
    years = np.tile([2017, 2018, 2019, 2020], 3)
    out = two_way_demean(x, territories, years)
    for labels in (territories, years):
        for label in np.unique(labels):
            assert np.allclose(out[labels == label].mean(axis=0), 0, atol=1e-8)


def test_permutation_preserves_year_distribution_and_changes_alignment():
    samples = synthetic_samples()
    permuted = permute_source_within_year(samples, np.random.default_rng(1))
    for year in samples.observation_year.unique():
        before = np.sort(samples.loc[samples.observation_year.eq(year), "source_lag"])
        after = np.sort(permuted.loc[permuted.observation_year.eq(year), "source_lag"])
        assert np.array_equal(before, after)
    assert not np.array_equal(samples["source_lag"], permuted["source_lag"])


def test_empirical_p_has_nonzero_floor():
    assert empirical_p(10, [0, 1, 2, 3]) == 0.2


def test_bh_fdr_monotonic_and_bounded():
    q = bh_fdr(pd.Series([0.001, 0.01, 0.2, np.nan]))
    assert q.iloc[0] <= q.iloc[1] <= q.iloc[2] <= 1
    assert np.isnan(q.iloc[3])


def test_pair_samples_uses_lagged_source_not_current():
    rows = []
    for sector in ["BE", "FZ"]:
        for year in range(2015, 2021):
            rows.append({
                "country": "XX",
                "territory_id": "r1",
                "observation_year": year,
                "sector_id": sector,
                "velocity": year * (1 if sector == "BE" else 10),
                "observation_mask": 1,
                "structural_mask": 1,
            })
    panel = pd.DataFrame(rows)
    samples = pair_samples(panel, "BE", "FZ", 2017, 2020)
    row = samples[samples.observation_year.eq(2018)].iloc[0]
    assert row.source_lag == 2017
    assert row.target_lag == 20170
    assert row.target_growth == 20180


def test_excluded_year_is_not_used_as_source_or_target():
    rows = []
    for territory in range(10):
        for sector in ["BE", "FZ"]:
            for year in range(2015, 2022):
                rows.append({
                    "territory_id": str(territory),
                    "observation_year": year,
                    "sector_id": sector,
                    "velocity": float(year),
                    "observation_mask": 1,
                    "structural_mask": 1,
                })
    samples = pair_samples(
        pd.DataFrame(rows), "BE", "FZ", 2017, 2021, frozenset({2020})
    )
    assert 2020 not in set(samples.observation_year)
    assert 2021 not in set(samples.observation_year)
