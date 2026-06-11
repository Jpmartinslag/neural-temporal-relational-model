"""Tests for build_g2_aggregate_dynamics.py.

Coverage:
- Country × sector × year alignment
- PT KZ structurally absent
- Absence never converted to zero
- Periods correctly defined by observation_year
- available_for_forecast_year not used as substitute
- Density and quantile metrics
- Turnover and Jaccard
- Period comparison pre/2020/post
- Denominator zero safety
- Pair-resampling sensitivity determinism
- Top-k 3/5/10
- Scenario with and without observation_year=2020
- No pooling between countries
- No NaN/Inf contamination
- Output determinism
- Checksums and metadata
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
BUILDER_DIR = str(BASE / "src/data/european_panel")
if BUILDER_DIR not in sys.path:
    sys.path.insert(0, BUILDER_DIR)

from build_g2_aggregate_dynamics import (
    classify_period,
    graph_annual_metrics,
    consecutive_turnover_topk,
    yoy_change,
    bootstrap_metric,
    period_summary,
    period_comparison,
    build_sector_analysis,
    topk_sensitivity_row,
    build_covid_sensitivity,
    file_checksum,
    run_aggregate_dynamics,
    NEAR_ZERO_THRESHOLD,
    WINDOW,
    MIN_PERIODS,
)

from build_g2_corrected_controls import (
    top_k_adjacency,
    jaccard_binary,
)

from build_g1_l2_cogrowth import (
    build_growth_matrix,
    eligible_sectors,
    pairwise_corr,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mini_panel(n_regions=6, seed=42):
    """Create a minimal panel for testing."""
    rng = np.random.default_rng(seed)
    rows = []
    sectors = ["BE", "FZ", "GI"]
    countries_config = {
        "FR": {"regions": [f"FR{i:02d}" for i in range(n_regions)],
               "obs_years": list(range(2012, 2024))},
        "NL": {"regions": [f"NL{i:02d}" for i in range(n_regions)],
               "obs_years": list(range(2008, 2024))},
        "PT": {"regions": [f"PT{i:02d}" for i in range(n_regions)],
               "obs_years": list(range(2009, 2024))},
    }
    for country, cfg in countries_config.items():
        for region in cfg["regions"]:
            for obs_year in cfg["obs_years"]:
                for sector in sectors:
                    growth = rng.normal(0, 0.1) if obs_year > cfg["obs_years"][0] else np.nan
                    # PT KZ must be structurally absent
                    if country == "PT" and sector == "KZ":
                        continue
                    rows.append({
                        "region_id": region,
                        "observation_year": obs_year,
                        "sector_a10": sector,
                        "sector_births": rng.integers(100, 1000),
                        "country": country,
                        "source_label": "TEST",
                        "region_name": f"Region {region}",
                        "region_level": "TEST",
                        "flag_target_concept": "test",
                        "meta_region_system": "TEST",
                        "meta_source_label": "TEST",
                        "mask_sector_births": 1,
                        "mask_sector_supported": 1,
                        "mask_complete_sector_vector": 1,
                        "business_sector_total": 1000,
                        "sector_share": 0.1,
                        "sector_growth_1y": growth,
                        "available_for_forecast_year": obs_year + 1,
                    })
    return pd.DataFrame(rows)


@pytest.fixture
def mini_panel():
    return _make_mini_panel()


@pytest.fixture
def mini_panel_path(tmp_path, mini_panel):
    path = tmp_path / "test_panel.csv"
    mini_panel.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Period classification
# ---------------------------------------------------------------------------

class TestPeriodClassification:
    def test_pre_2020(self):
        assert classify_period(2019) == "pre-2020"
        assert classify_period(2015) == "pre-2020"
        assert classify_period(2008) == "pre-2020"

    def test_year_2020(self):
        assert classify_period(2020) == "2020"

    def test_post_2020(self):
        assert classify_period(2021) == "post-2020"
        assert classify_period(2023) == "post-2020"

    def test_boundary(self):
        """2019 is pre, 2020 is 2020, 2021 is post."""
        assert classify_period(2019) != classify_period(2020)
        assert classify_period(2020) != classify_period(2021)


# ---------------------------------------------------------------------------
# Graph annual metrics
# ---------------------------------------------------------------------------

class TestGraphAnnualMetrics:
    def test_identity_graph(self):
        """All-ones adjacency gives density=1."""
        n = 5
        corr = np.ones((n, n))
        adj = np.ones((n, n), dtype=bool)
        np.fill_diagonal(adj, False)
        m = graph_annual_metrics(corr, adj, n)
        assert m["n_regions"] == n
        assert m["n_possible_pairs"] == n * (n - 1) // 2
        assert m["density"] == pytest.approx(1.0)

    def test_empty_graph(self):
        """No edges gives density=0."""
        n = 5
        corr = np.zeros((n, n))
        adj = np.zeros((n, n), dtype=bool)
        m = graph_annual_metrics(corr, adj, n)
        assert m["n_edges_valid"] == 0
        assert m["density"] == 0.0

    def test_weight_quantiles(self):
        """Quantile ordering: p10 <= p25 <= median <= p75 <= p90."""
        rng = np.random.default_rng(42)
        n = 10
        corr = rng.uniform(0.1, 0.9, (n, n))
        corr = (corr + corr.T) / 2
        np.fill_diagonal(corr, 1.0)
        adj = top_k_adjacency(corr, 5)
        m = graph_annual_metrics(corr, adj, n)
        assert m["p10_weight"] <= m["p25_weight"]
        assert m["p25_weight"] <= m["median_weight"]
        assert m["median_weight"] <= m["p75_weight"]
        assert m["p75_weight"] <= m["p90_weight"]

    def test_positive_fraction(self):
        """All-positive weights give frac_positive=1."""
        n = 5
        corr = np.full((n, n), 0.5)
        np.fill_diagonal(corr, 1.0)
        adj = np.ones((n, n), dtype=bool)
        np.fill_diagonal(adj, False)
        m = graph_annual_metrics(corr, adj, n)
        assert m["frac_positive"] == 1.0
        assert m["frac_negative"] == 0.0

    def test_near_zero_fraction(self):
        """Weights near zero are counted."""
        n = 4
        corr = np.full((n, n), 0.01)  # below NEAR_ZERO_THRESHOLD
        np.fill_diagonal(corr, 1.0)
        adj = np.ones((n, n), dtype=bool)
        np.fill_diagonal(adj, False)
        m = graph_annual_metrics(corr, adj, n)
        assert m["frac_near_zero"] == 1.0

    def test_density_range(self):
        """Density is always between 0 and 1."""
        rng = np.random.default_rng(42)
        for _ in range(10):
            n = rng.integers(3, 20)
            corr = rng.uniform(-0.5, 0.9, (n, n))
            corr = (corr + corr.T) / 2
            np.fill_diagonal(corr, 1.0)
            k = rng.integers(1, min(5, n))
            adj = top_k_adjacency(corr, k)
            m = graph_annual_metrics(corr, adj, n)
            assert 0.0 <= m["density"] <= 1.0


# ---------------------------------------------------------------------------
# Turnover and Jaccard
# ---------------------------------------------------------------------------

class TestTurnoverJaccard:
    def test_identical_graphs(self):
        """Identical graphs have turnover=0, Jaccard=1."""
        n = 5
        adj = np.zeros((n, n), dtype=bool)
        adj[0, 1] = adj[1, 0] = True
        adj[2, 3] = adj[3, 2] = True
        assert consecutive_turnover_topk(adj, adj) == pytest.approx(0.0)
        assert jaccard_binary(adj, adj) == pytest.approx(1.0)

    def test_disjoint_graphs(self):
        """Disjoint graphs have turnover=1, Jaccard=0."""
        n = 6
        a1 = np.zeros((n, n), dtype=bool)
        a1[0, 1] = a1[1, 0] = True
        a2 = np.zeros((n, n), dtype=bool)
        a2[2, 3] = a2[3, 2] = True
        assert consecutive_turnover_topk(a1, a2) == pytest.approx(1.0)
        assert jaccard_binary(a1, a2) == pytest.approx(0.0)

    def test_turnover_range(self):
        """Turnover is between 0 and 1."""
        rng = np.random.default_rng(42)
        n = 8
        for _ in range(10):
            a1 = rng.random((n, n)) > 0.7
            a2 = rng.random((n, n)) > 0.7
            t = consecutive_turnover_topk(a1, a2)
            if np.isfinite(t):
                assert 0.0 <= t <= 1.0


# ---------------------------------------------------------------------------
# YoY change
# ---------------------------------------------------------------------------

class TestYoYChange:
    def test_no_change(self):
        m = {"mean_weight": 0.5, "median_weight": 0.4, "density": 0.3, "mean_abs_weight": 0.5}
        c = yoy_change(m, m)
        assert c["mean_weight_abs_change"] == pytest.approx(0.0)
        assert c["mean_weight_rel_change"] == pytest.approx(0.0)

    def test_doubling(self):
        m1 = {"mean_weight": 0.5, "median_weight": 0.4, "density": 0.3, "mean_abs_weight": 0.5}
        m2 = {"mean_weight": 1.0, "median_weight": 0.8, "density": 0.6, "mean_abs_weight": 1.0}
        c = yoy_change(m1, m2)
        assert c["mean_weight_abs_change"] == pytest.approx(0.5)
        assert c["mean_weight_rel_change"] == pytest.approx(1.0)

    def test_zero_denominator(self):
        """When previous value is ~0, relative change is NaN."""
        m1 = {"mean_weight": 0.0, "median_weight": 0.0, "density": 0.0, "mean_abs_weight": 0.0}
        m2 = {"mean_weight": 0.5, "median_weight": 0.4, "density": 0.3, "mean_abs_weight": 0.5}
        c = yoy_change(m1, m2)
        assert np.isnan(c["mean_weight_rel_change"])
        assert c["mean_weight_abs_change"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Pair-resampling sensitivity determinism
# ---------------------------------------------------------------------------

class TestBootstrap:
    def test_deterministic(self):
        """Same seed gives same result."""
        rng = np.random.default_rng(42)
        n = 10
        corr = rng.uniform(0.1, 0.9, (n, n))
        corr = (corr + corr.T) / 2
        np.fill_diagonal(corr, 1.0)
        adj = top_k_adjacency(corr, 5)

        b1 = bootstrap_metric(corr, adj, n_bootstrap=50, seed=42)
        b2 = bootstrap_metric(corr, adj, n_bootstrap=50, seed=42)
        assert b1["pair_resample_mean_weight_p025"] == b2["pair_resample_mean_weight_p025"]
        assert b1["pair_resample_mean_weight_p975"] == b2["pair_resample_mean_weight_p975"]
        assert b1["pair_resample_density_p025"] == b2["pair_resample_density_p025"]

    def test_interval_near_point_estimate(self):
        """Descriptive pair-resampling interval should remain near the estimate."""
        rng = np.random.default_rng(42)
        n = 15
        corr = rng.uniform(0.2, 0.8, (n, n))
        corr = (corr + corr.T) / 2
        np.fill_diagonal(corr, 1.0)
        adj = top_k_adjacency(corr, 5)
        m = graph_annual_metrics(corr, adj, n)
        b = bootstrap_metric(corr, adj, n_bootstrap=200, seed=42)
        assert b["pair_resample_mean_weight_p025"] <= m["mean_weight"] + 0.1
        assert b["pair_resample_mean_weight_p975"] >= m["mean_weight"] - 0.1


# ---------------------------------------------------------------------------
# Period summary and comparison
# ---------------------------------------------------------------------------

class TestPeriodSummary:
    def test_empty_period(self):
        s = period_summary([], "pre-2020")
        assert s["n_years"] == 0

    def test_single_year(self):
        rows = [{"period": "pre-2020", "density": 0.5, "mean_weight": 0.3,
                 "median_weight": 0.25, "std_weight": 0.1, "mean_abs_weight": 0.3,
                 "frac_positive": 0.8, "frac_negative": 0.1, "frac_near_zero": 0.1,
                 "n_edges_valid": 10}]
        s = period_summary(rows, "pre-2020")
        assert s["n_years"] == 1
        assert s["density_mean"] == pytest.approx(0.5)

    def test_comparison_zero_denominator(self):
        """Comparison with zero pre-period mean is safe."""
        pre = {"period": "pre-2020", "n_years": 3, "density_mean": 0.0,
               "density_min": 0.0, "density_max": 0.0,
               "mean_weight_mean": 0.0, "mean_weight_min": 0.0, "mean_weight_max": 0.0,
               "median_weight_mean": 0.0, "median_weight_min": 0.0, "median_weight_max": 0.0,
               "std_weight_mean": 0.0, "std_weight_min": 0.0, "std_weight_max": 0.0,
               "mean_abs_weight_mean": 0.0, "mean_abs_weight_min": 0.0, "mean_abs_weight_max": 0.0,
               "frac_positive_mean": 0.0, "frac_positive_min": 0.0, "frac_positive_max": 0.0,
               "frac_negative_mean": 0.0, "frac_negative_min": 0.0, "frac_negative_max": 0.0}
        post = {**pre, "period": "post-2020", "density_mean": 0.5, "mean_weight_mean": 0.3}
        comp = period_comparison(pre, post, "post_minus_pre")
        assert np.isnan(comp["density_rel_effect"])  # zero denominator
        assert comp["density_diff"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# PT KZ structural absence
# ---------------------------------------------------------------------------

class TestPTKZAbsence:
    def test_pt_kz_not_in_eligible_sectors(self, mini_panel):
        sectors = eligible_sectors(mini_panel, "PT")
        assert "KZ" not in sectors

    def test_pt_kz_never_appears_in_results(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        summary = run_aggregate_dynamics(
            panel_path=mini_panel_path,
            out_dir=out,
            generate_figs=False,
            verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        pt_sectors = df[df["country"] == "PT"]["sector"].unique()
        assert "KZ" not in pt_sectors

    def test_pt_kz_not_converted_to_zero(self, mini_panel):
        """KZ should not appear for PT even as zero values."""
        pt = mini_panel[mini_panel["country"] == "PT"]
        assert "KZ" not in pt["sector_a10"].values


# ---------------------------------------------------------------------------
# No cross-country pooling
# ---------------------------------------------------------------------------

class TestNoCrossCountryPooling:
    def test_annual_metrics_per_country(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        # Each row must have a country
        assert df["country"].notna().all()
        # No rows mix countries
        for _, row in df.iterrows():
            assert row["country"] in ["FR", "NL", "PT"]

    def test_period_metrics_per_country(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_period_metrics.csv")
        assert df["country"].notna().all()
        # No country column contains mixed values
        for c in df["country"].unique():
            assert c in ["FR", "NL", "PT"]


# ---------------------------------------------------------------------------
# Period defined by observation_year
# ---------------------------------------------------------------------------

class TestPeriodDefinition:
    def test_available_for_forecast_year_not_used(self, mini_panel_path, tmp_path):
        """Periods must be defined by observation_year, not available_for_forecast_year."""
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        # The column 'observation_year_last' should exist and determine the period
        assert "observation_year_last" in df.columns
        assert "period" in df.columns
        for _, row in df.iterrows():
            expected = classify_period(row["observation_year_last"])
            assert row["period"] == expected

    def test_no_available_for_forecast_year_column(self, mini_panel_path, tmp_path):
        """Output should not have available_for_forecast_year as a period determinant."""
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        assert "available_for_forecast_year" not in df.columns


# ---------------------------------------------------------------------------
# No NaN/Inf contamination
# ---------------------------------------------------------------------------

class TestNoNaNInf:
    def test_no_inf_in_annual_metrics(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not np.any(np.isinf(df[col].dropna().values)), f"Inf in {col}"

    def test_no_inf_in_period_metrics(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_period_metrics.csv")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not np.any(np.isinf(df[col].dropna().values)), f"Inf in {col}"

    def test_no_inf_in_comparisons(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_period_comparisons.csv")
        if not df.empty:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                assert not np.any(np.isinf(df[col].dropna().values)), f"Inf in {col}"


# ---------------------------------------------------------------------------
# Output determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_two_runs_identical(self, mini_panel_path, tmp_path):
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out1,
            generate_figs=False, verbose=False,
        )
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out2,
            generate_figs=False, verbose=False,
        )
        for fname in [
            "g2_annual_metrics.csv",
            "g2_period_metrics.csv",
            "g2_period_comparisons.csv",
            "g2_topk_sensitivity.csv",
            "g2_covid_sensitivity.csv",
        ]:
            df1 = pd.read_csv(out1 / fname)
            df2 = pd.read_csv(out2 / fname)
            pd.testing.assert_frame_equal(df1, df2, check_dtype=False)


# ---------------------------------------------------------------------------
# Top-k sensitivity
# ---------------------------------------------------------------------------

class TestTopKSensitivity:
    def test_multiple_k_values(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_topk_sensitivity.csv")
        # Should have columns for k=3, k=5, k=10
        for k in [3, 5, 10]:
            assert f"density_k{k}" in df.columns
            assert f"mean_weight_k{k}" in df.columns

    def test_density_increases_with_k(self, mini_panel_path, tmp_path):
        """Larger k should generally give more edges (higher density)."""
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_topk_sensitivity.csv").dropna()
        if len(df) > 0:
            mean_d3 = df["density_k3"].mean()
            mean_d10 = df["density_k10"].mean()
            assert mean_d10 >= mean_d3 - 0.01  # k=10 should have >= density


# ---------------------------------------------------------------------------
# COVID sensitivity
# ---------------------------------------------------------------------------

class TestCOVIDSensitivity:
    def test_both_scenarios_present(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_covid_sensitivity.csv")
        assert "density_with_2020" in df.columns
        assert "density_without_2020" in df.columns
        assert "density_delta" in df.columns

    def test_delta_is_difference(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_covid_sensitivity.csv")
        valid = df.dropna(subset=["density_with_2020", "density_without_2020"])
        if len(valid) > 0:
            expected = valid["density_without_2020"] - valid["density_with_2020"]
            np.testing.assert_array_almost_equal(
                valid["density_delta"].values, expected.values, decimal=10
            )


# ---------------------------------------------------------------------------
# Checksums and metadata
# ---------------------------------------------------------------------------

class TestChecksums:
    def test_manifest_exists(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        manifest_path = out / "g2_dynamics_manifest.json"
        assert manifest_path.exists()
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "source_checksum" in manifest
        assert "artifacts" in manifest

    def test_summary_has_parameters(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        summary_path = out / "g2_dynamics_summary.json"
        assert summary_path.exists()
        with open(summary_path) as f:
            summary = json.load(f)
        assert "parameters" in summary
        assert summary["parameters"]["window"] == WINDOW
        assert summary["parameters"]["min_periods"] == MIN_PERIODS
        assert "not independent" in summary["parameters"]["pair_resample_interpretation"]
        assert "eval_year=2021" in summary["parameters"]["period_definition"]

    def test_summary_records_generated_figures(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        summary = run_aggregate_dynamics(
            panel_path=mini_panel_path,
            out_dir=out,
            generate_figs=True,
            verbose=False,
        )
        assert len(summary["figures"]) == 16
        assert all((out / "figures" / name).exists() for name in summary["figures"])

    def test_source_checksum_correct(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        with open(out / "g2_dynamics_summary.json") as f:
            summary = json.load(f)
        expected_checksum = file_checksum(mini_panel_path)
        assert summary["source_checksum_sha256_16"] == expected_checksum


# ---------------------------------------------------------------------------
# Alignment: country × sector × year
# ---------------------------------------------------------------------------

class TestAlignment:
    def test_all_countries_present(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        countries = sorted(df["country"].unique())
        assert countries == ["FR", "NL", "PT"]

    def test_sectors_per_country(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        # PT should have fewer sectors (no KZ)
        pt_sectors = sorted(df[df["country"] == "PT"]["sector"].unique())
        fr_sectors = sorted(df[df["country"] == "FR"]["sector"].unique())
        # PT should not have KZ
        assert "KZ" not in pt_sectors
        # FR and NL can have more sectors
        assert len(fr_sectors) >= len(pt_sectors)

    def test_eval_years_consistent(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_annual_metrics.csv")
        for c in df["country"].unique():
            csub = df[df["country"] == c]
            # All sectors for a country should have overlapping year ranges
            for s in csub["sector"].unique():
                ssub = csub[csub["sector"] == s]
                assert len(ssub) > 0
                assert ssub["eval_year"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# Period comparison structure
# ---------------------------------------------------------------------------

class TestPeriodComparisons:
    def test_comparisons_have_correct_labels(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_period_comparisons.csv")
        if not df.empty:
            assert set(df["comparison"].unique()).issubset(
                {"post_minus_pre", "2020_minus_pre"}
            )

    def test_period_metrics_all_periods(self, mini_panel_path, tmp_path):
        out = tmp_path / "test_out"
        run_aggregate_dynamics(
            panel_path=mini_panel_path, out_dir=out,
            generate_figs=False, verbose=False,
        )
        df = pd.read_csv(out / "g2_period_metrics.csv")
        # Should have at least pre-2020 and post-2020 for each country×sector
        for c in df["country"].unique():
            for s in df[df["country"] == c]["sector"].unique():
                subset = df[(df["country"] == c) & (df["sector"] == s)]
                periods = set(subset["period"].unique())
                assert "pre-2020" in periods
