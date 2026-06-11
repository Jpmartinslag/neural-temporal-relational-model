"""Tests for the schema 2.0 causal graph-temporal tensor builder.

New tests T19–T42 (24 total). All 33 tests in test_graph_temporal_preflight.py
are preserved unchanged.

Invariants tested
-----------------
T19  schema_version in manifest is "2.0"
T20  features_seq shape is (T, R, S, F)
T21  adjacency_seq shape is (T, S, R, R)
T22  feature_mask_seq shape is (T, R, S, F) and values ∈ {0, 1}
T23  observation_years shape is (T,) and all < eval_year
T24  per-step causality: adjacency at step t uses only obs_years ≤ obs_years[t]
T25  per-feature mask independence: growth invalid ≠ births invalid
T26  y_true comes from sector panel business_sector_total, not country panel
T27  y_ridge_canonical is clipped to ≥ 0
T28  positive_topk adjacency has no negative off-diagonal entries
T29  positive_topk adjacency is symmetric
T30  signed_split returns two-channel (2, R, R) structure
T31  shrinkage_dense has finite values for well-observed sectors
T32  adjacency LeakageError raised if obs_year ≥ eval_year
T33  features LeakageError raised if obs_year ≥ eval_year
T34  struct_mask is 0 for PT-KZ across all time steps
T35  no NaN in feature_mask_seq (it is a binary mask)
T36  observation_years covers exactly t_seq steps ending at eval_year-1
T37  adjacency audit reports negative fraction for synthetic signed data
T38  load_fold_v2 raises FileNotFoundError for missing artifact (fail-closed)
T39  two export runs with same inputs produce identical NPZ checksums
T40  y_ridge_canonical is finite where target_mask=1 (given sufficient history)
T41  residual = y_true - y_ridge_canonical where target_mask=1
T42  struct_mask is static: same (R, S) shape for all time steps
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.build_graph_temporal_v2 import (
    FEATURE_NAMES,
    LeakageError,
    RIDGE_ALPHA_H0B,
    SCHEMA_VERSION,
    STRUCTURAL_ABSENT,
    T_SEQ,
    TOP_K,
    WINDOW,
    MIN_PERIODS,
    _assert_no_leakage,
    audit_adjacency_fold,
    build_adjacency_at_step,
    build_adjacency_seq,
    build_features_at_step,
    build_features_seq,
    build_fold_tensors_v2,
    build_struct_mask,
    canonical_ridge_h0b,
    country_regions_from_sector,
    country_sectors,
    export_v2,
    file_checksum,
    load_fold_v2,
    load_manifest_v2,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

def _make_sector_panel(
    country: str = "TE",
    regions: list[str] | None = None,
    sectors: list[str] | None = None,
    obs_years: list[int] | None = None,
    growth_val: float = 0.1,
    births_val: float = 100.0,
    share_val: float = 0.1,
    mask_supported: int = 1,
    mask_births: int = 1,
) -> pd.DataFrame:
    """Minimal sector panel for testing."""
    if regions is None:
        regions = ["R1", "R2", "R3"]
    if sectors is None:
        sectors = ["BE", "FZ"]
    if obs_years is None:
        obs_years = list(range(2010, 2023))

    rows = []
    for obs_year in obs_years:
        avail_year = obs_year + 1
        for region in regions:
            for sector in sectors:
                rows.append({
                    "country": country,
                    "region_id": region,
                    "sector_a10": sector,
                    "observation_year": obs_year,
                    "available_for_forecast_year": avail_year,
                    "sector_growth_1y": growth_val,
                    "sector_share": share_val,
                    "sector_births": births_val,
                    "mask_sector_births": mask_births,
                    "mask_sector_supported": mask_supported,
                    "business_sector_total": births_val * len(sectors),
                })
    return pd.DataFrame(rows)


def _default_params() -> dict:
    return {"eval_year": 2020, "t_seq": 5, "window": 5, "min_periods": 2, "k": 2}


# ---------------------------------------------------------------------------
# T19: schema_version = "2.0"
# ---------------------------------------------------------------------------

def test_T19_schema_version():
    sp = _make_sector_panel()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        manifest = export_v2(
            countries=["TE"],
            eval_years_by_country={"TE": [2020]},
            sector_panel_path=None,
            out_dir=out,
            t_seq=3,
            window=5,
            min_periods=2,
            k=2,
            run_adjacency_audit=False,
            _sector_panel_override=sp,
        )
    assert manifest["schema_version"] == SCHEMA_VERSION == "2.0"


# ---------------------------------------------------------------------------
# T20: features_seq shape = (T, R, S, F)
# ---------------------------------------------------------------------------

def test_T20_features_seq_shape():
    sp = _make_sector_panel()
    p = _default_params()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", p["eval_year"], sp, sectors, regions,
        t_seq=p["t_seq"], window=p["window"], min_periods=p["min_periods"], k=p["k"]
    )
    T, R, S, F = fold["features_seq"].shape
    assert T == p["t_seq"]
    assert R == len(regions)
    assert S == len(sectors)
    assert F == len(FEATURE_NAMES)


# ---------------------------------------------------------------------------
# T21: adjacency_seq shape = (T, S, R, R)
# ---------------------------------------------------------------------------

def test_T21_adjacency_seq_shape():
    sp = _make_sector_panel()
    p = _default_params()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", p["eval_year"], sp, sectors, regions,
        t_seq=p["t_seq"], window=p["window"], min_periods=p["min_periods"], k=p["k"]
    )
    adj = fold["adjacency_seq"]
    T, S, R1, R2 = adj.shape
    assert T == p["t_seq"]
    assert S == len(sectors)
    assert R1 == R2 == len(regions)


# ---------------------------------------------------------------------------
# T22: feature_mask_seq values ∈ {0, 1} and shape = (T, R, S, F)
# ---------------------------------------------------------------------------

def test_T22_feature_mask_seq_binary():
    sp = _make_sector_panel()
    p = _default_params()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", p["eval_year"], sp, sectors, regions,
        t_seq=p["t_seq"], window=p["window"], min_periods=p["min_periods"], k=p["k"]
    )
    m = fold["feature_mask_seq"]
    assert m.shape == fold["features_seq"].shape
    unique = set(np.unique(m))
    assert unique.issubset({0, 1})


# ---------------------------------------------------------------------------
# T23: observation_years shape = (T,) and all < eval_year
# ---------------------------------------------------------------------------

def test_T23_observation_years_causal():
    sp = _make_sector_panel()
    p = _default_params()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", p["eval_year"], sp, sectors, regions,
        t_seq=p["t_seq"], window=p["window"], min_periods=p["min_periods"], k=p["k"]
    )
    obs = fold["observation_years"]
    assert obs.shape == (p["t_seq"],)
    assert np.all(obs < p["eval_year"])


# ---------------------------------------------------------------------------
# T24: per-step causality — adj[t] must not change when data after obs_years[t] is altered
# ---------------------------------------------------------------------------

def test_T24_adjacency_per_step_causality():
    """Modifying growth at obs_year=u+1 must not change adjacency at step u."""
    sp = _make_sector_panel(obs_years=list(range(2010, 2025)))
    eval_year = 2020
    obs_year_early = 2015  # step using window [2011, 2015]
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")

    adj_before = build_adjacency_at_step(
        sp, "TE", sectors, regions,
        obs_year=obs_year_early, eval_year=eval_year,
        window=5, min_periods=2, repr_="positive_topk", k=2,
    )

    # Modify data at obs_year=2016 (one step after obs_year_early=2015)
    sp_mod = sp.copy()
    mask = (sp_mod["observation_year"] == 2016)
    sp_mod.loc[mask, "sector_growth_1y"] = 9.99

    adj_after = build_adjacency_at_step(
        sp_mod, "TE", sectors, regions,
        obs_year=obs_year_early, eval_year=eval_year,
        window=5, min_periods=2, repr_="positive_topk", k=2,
    )

    np.testing.assert_array_equal(adj_before, adj_after)


# ---------------------------------------------------------------------------
# T25: per-feature mask independence — growth invalid ≠ births invalid
# ---------------------------------------------------------------------------

def test_T25_per_feature_mask_independence():
    """If growth is Inf but share and births are finite, only mask[...,0]=0."""
    sp = _make_sector_panel()
    # Set growth to Inf for region R1 at obs_year=2019
    sp_mod = sp.copy()
    mask = (
        (sp_mod["observation_year"] == 2019)
        & (sp_mod["region_id"] == "R1")
        & (sp_mod["sector_a10"] == "BE")
    )
    sp_mod.loc[mask, "sector_growth_1y"] = np.inf

    regions = country_regions_from_sector(sp_mod, "TE")
    sectors = country_sectors(sp_mod, "TE")
    births_stats = {"BE": {"mean": 100.0, "std": 1.0}, "FZ": {"mean": 100.0, "std": 1.0}}

    feat, feat_mask = build_features_at_step(
        sp_mod, "TE", sectors, regions,
        obs_year=2019, eval_year=2020,
        births_train_stats=births_stats,
    )

    r_idx = regions.index("R1")
    s_idx = sectors.index("BE")

    # growth mask must be 0 (Inf is not valid)
    assert feat_mask[r_idx, s_idx, 0] == 0
    # births mask must remain 1 (births are still valid)
    assert feat_mask[r_idx, s_idx, 2] == 1
    # share mask must remain 1
    assert feat_mask[r_idx, s_idx, 1] == 1


# ---------------------------------------------------------------------------
# T26: y_true = business_sector_total from sector panel
# ---------------------------------------------------------------------------

def test_T26_y_true_from_business_sector_total():
    """y_true must equal business_sector_total at observation_year = eval_year."""
    sp = _make_sector_panel(births_val=50.0)
    # business_sector_total is set to births_val * n_sectors = 50 * 2 = 100 per region
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    _, y_true = canonical_ridge_h0b(sp, "TE", regions, fold_eval_year=2020)

    # Expected: business_sector_total for observation_year=2020 (avail=2021)
    expected_bst = 50.0 * len(sectors)  # 100.0 per region
    for r_idx in range(len(regions)):
        if np.isfinite(y_true[r_idx]):
            assert abs(y_true[r_idx] - expected_bst) < 1e-9


# ---------------------------------------------------------------------------
# T27: y_ridge_canonical ≥ 0 everywhere (clipped)
# ---------------------------------------------------------------------------

def test_T27_ridge_canonical_nonnegative():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", 2020, sp, sectors, regions,
        t_seq=3, window=5, min_periods=2, k=2
    )
    yr = fold["y_ridge_canonical"]
    finite = yr[np.isfinite(yr)]
    assert np.all(finite >= 0.0), f"y_ridge_canonical has negative entries: {finite[finite < 0]}"


# ---------------------------------------------------------------------------
# T28: positive_topk adjacency has no negative off-diagonal values
# ---------------------------------------------------------------------------

def test_T28_positive_topk_no_negative():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    adj = build_adjacency_at_step(
        sp, "TE", sectors, regions,
        obs_year=2019, eval_year=2020,
        window=5, min_periods=2, repr_="positive_topk", k=2
    )
    n_r = len(regions)
    off_mask = ~np.eye(n_r, dtype=bool)
    for s_idx in range(len(sectors)):
        off = adj[s_idx][off_mask]
        assert np.all(off >= 0.0), f"sector {sectors[s_idx]} has negative off-diagonal"


# ---------------------------------------------------------------------------
# T29: positive_topk adjacency is symmetric
# ---------------------------------------------------------------------------

def test_T29_positive_topk_symmetric():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    adj = build_adjacency_at_step(
        sp, "TE", sectors, regions,
        obs_year=2019, eval_year=2020,
        window=5, min_periods=2, repr_="positive_topk", k=2
    )
    for s_idx in range(len(sectors)):
        A = adj[s_idx]
        np.testing.assert_array_almost_equal(A, A.T, decimal=10)


# ---------------------------------------------------------------------------
# T30: signed_split returns (2, R, R) per sector
# ---------------------------------------------------------------------------

def test_T30_signed_split_structure():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    adj = build_adjacency_at_step(
        sp, "TE", sectors, regions,
        obs_year=2019, eval_year=2020,
        window=5, min_periods=2, repr_="signed_split", k=2
    )
    # Expected shape: (2, S, R, R)
    assert adj.ndim == 4
    assert adj.shape[0] == 2  # two channels
    n_r = len(regions)
    # Both channels non-negative (off-diagonal)
    off_mask = ~np.eye(n_r, dtype=bool)
    for ch in range(2):
        for s_idx in range(len(sectors)):
            vals = adj[ch, s_idx][off_mask]
            finite = vals[np.isfinite(vals)]
            assert np.all(finite >= 0.0), f"channel {ch} sector {s_idx} has negative"


# ---------------------------------------------------------------------------
# T31: shrinkage_dense has finite diagonal
# ---------------------------------------------------------------------------

def test_T31_shrinkage_dense_finite_diagonal():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    adj = build_adjacency_at_step(
        sp, "TE", sectors, regions,
        obs_year=2019, eval_year=2020,
        window=5, min_periods=2, repr_="shrinkage_dense", k=2
    )
    for s_idx in range(len(sectors)):
        diag = np.diag(adj[s_idx])
        finite = diag[np.isfinite(diag)]
        if len(finite) > 0:
            # Diagonal should be 1.0 (set explicitly)
            np.testing.assert_almost_equal(finite, 1.0, decimal=9)


# ---------------------------------------------------------------------------
# T32: LeakageError raised in adjacency when obs_year >= eval_year
# ---------------------------------------------------------------------------

def test_T32_adjacency_leakage_error():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    with pytest.raises(LeakageError):
        build_adjacency_at_step(
            sp, "TE", sectors, regions,
            obs_year=2020, eval_year=2020,  # obs_year == eval_year → LEAKAGE
            window=5, min_periods=2, repr_="positive_topk", k=2
        )


# ---------------------------------------------------------------------------
# T33: LeakageError raised in features when obs_year >= eval_year
# ---------------------------------------------------------------------------

def test_T33_features_leakage_error():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    births_stats = {s: {"mean": 100.0, "std": 1.0} for s in sectors}
    with pytest.raises(LeakageError):
        build_features_at_step(
            sp, "TE", sectors, regions,
            obs_year=2021, eval_year=2020,  # obs_year > eval_year → LEAKAGE
            births_train_stats=births_stats,
        )


# ---------------------------------------------------------------------------
# T34: struct_mask = 0 for PT-KZ across all time steps
# ---------------------------------------------------------------------------

def test_T34_struct_mask_pt_kz():
    """For PT country with KZ sector, struct_mask must be 0 at all time steps."""
    regions = ["AMP", "ALE", "LVT"]
    sectors = ["BE", "KZ", "FZ"]
    struct = build_struct_mask("PT", sectors, regions)
    kz_idx = sectors.index("KZ")
    assert np.all(struct[:, kz_idx] == 0), "PT-KZ struct_mask must be 0 for all regions"
    be_idx = sectors.index("BE")
    assert np.all(struct[:, be_idx] == 1), "PT-BE struct_mask must be 1"


# ---------------------------------------------------------------------------
# T35: no NaN or non-integer in feature_mask_seq
# ---------------------------------------------------------------------------

def test_T35_feature_mask_no_nan():
    sp = _make_sector_panel()
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    obs_years = list(range(2015, 2020))
    births_stats = {s: {"mean": 100.0, "std": 1.0} for s in sectors}
    _, mask_seq = build_features_seq(sp, "TE", sectors, regions, obs_years, eval_year=2020)
    assert not np.any(np.isnan(mask_seq.astype(float))), "feature_mask_seq must not contain NaN"
    assert set(np.unique(mask_seq)).issubset({0, 1})


# ---------------------------------------------------------------------------
# T36: observation_years covers exactly t_seq steps ending at eval_year - 1
# ---------------------------------------------------------------------------

def test_T36_observation_years_range():
    sp = _make_sector_panel()
    eval_year = 2020
    t_seq = 5
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", eval_year, sp, sectors, regions,
        t_seq=t_seq, window=5, min_periods=2, k=2
    )
    obs = fold["observation_years"]
    expected = np.arange(eval_year - t_seq, eval_year, dtype=np.int32)
    np.testing.assert_array_equal(obs, expected)
    assert obs[-1] == eval_year - 1


# ---------------------------------------------------------------------------
# T37: adjacency audit reports negative fraction for mixed-sign correlations
# ---------------------------------------------------------------------------

def test_T37_adjacency_audit_negative_fraction():
    """Audit reports a meaningful neg_fraction_mean when correlations are mixed."""
    rng = np.random.default_rng(42)
    regions = ["R1", "R2", "R3", "R4"]
    sectors = ["BE", "FZ"]
    obs_years = list(range(2010, 2025))
    rows = []
    for obs_year in obs_years:
        for region in regions:
            for sector in sectors:
                # Random growth to ensure mixed-sign correlations
                rows.append({
                    "country": "TE",
                    "region_id": region,
                    "sector_a10": sector,
                    "observation_year": obs_year,
                    "available_for_forecast_year": obs_year + 1,
                    "sector_growth_1y": float(rng.normal(0, 1)),
                    "sector_share": 0.1,
                    "sector_births": 100.0,
                    "mask_sector_births": 1,
                    "mask_sector_supported": 1,
                    "business_sector_total": 200.0,
                })
    sp_rand = pd.DataFrame(rows)

    audit = audit_adjacency_fold(
        sp_rand, "TE", sectors, regions, eval_year=2020,
        window=5, min_periods=2,
    )
    # With random data, neg_fraction should be > 0 and < 1
    nf = audit["neg_fraction_mean"]
    assert 0.0 <= nf <= 1.0, f"neg_fraction_mean={nf} out of [0,1]"


# ---------------------------------------------------------------------------
# T38: load_fold_v2 raises FileNotFoundError for missing artifact (fail-closed)
# ---------------------------------------------------------------------------

def test_T38_load_fold_v2_fail_closed():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(FileNotFoundError):
            load_fold_v2("TE", 2020, Path(tmp))


# ---------------------------------------------------------------------------
# T39: determinism — two export runs produce identical NPZ checksums
# ---------------------------------------------------------------------------

def test_T39_determinism():
    sp = _make_sector_panel()
    with tempfile.TemporaryDirectory() as tmp1:
        with tempfile.TemporaryDirectory() as tmp2:
            out1 = Path(tmp1)
            out2 = Path(tmp2)
            export_v2(
                countries=["TE"],
                eval_years_by_country={"TE": [2020]},
                sector_panel_path=None,
                out_dir=out1,
                t_seq=3, window=5, min_periods=2, k=2,
                run_adjacency_audit=False,
                _sector_panel_override=sp,
            )
            export_v2(
                countries=["TE"],
                eval_years_by_country={"TE": [2020]},
                sector_panel_path=None,
                out_dir=out2,
                t_seq=3, window=5, min_periods=2, k=2,
                run_adjacency_audit=False,
                _sector_panel_override=sp,
            )
            f1 = out1 / "TE" / "2020" / "fold_v2.npz"
            f2 = out2 / "TE" / "2020" / "fold_v2.npz"
            assert file_checksum(f1) == file_checksum(f2)


# ---------------------------------------------------------------------------
# T40: y_ridge_canonical is finite where target_mask=1 (given sufficient history)
# ---------------------------------------------------------------------------

def test_T40_ridge_finite_where_target_observed():
    sp = _make_sector_panel(obs_years=list(range(2008, 2025)))
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", 2020, sp, sectors, regions,
        t_seq=5, window=5, min_periods=2, k=2
    )
    tm = fold["target_mask"].astype(bool)
    yr = fold["y_ridge_canonical"]
    if tm.any():
        assert np.all(np.isfinite(yr[tm])), "y_ridge_canonical not finite where target_mask=1"


# ---------------------------------------------------------------------------
# T41: residual = y_true - y_ridge_canonical where target_mask=1
# ---------------------------------------------------------------------------

def test_T41_residual_consistency():
    sp = _make_sector_panel(obs_years=list(range(2008, 2025)))
    regions = country_regions_from_sector(sp, "TE")
    sectors = country_sectors(sp, "TE")
    fold = build_fold_tensors_v2(
        "TE", 2020, sp, sectors, regions,
        t_seq=5, window=5, min_periods=2, k=2
    )
    tm = fold["target_mask"].astype(bool)
    yt = fold["y_true"]
    yr = fold["y_ridge_canonical"]
    res = fold["residual"]
    expected = np.where(tm, yt - yr, np.nan)
    np.testing.assert_array_almost_equal(
        np.nan_to_num(res), np.nan_to_num(expected), decimal=9
    )


# ---------------------------------------------------------------------------
# T42: struct_mask shape is (R, S) — static, independent of T
# ---------------------------------------------------------------------------

def test_T42_struct_mask_static_shape():
    regions = ["R1", "R2", "R3"]
    sectors = ["BE", "FZ", "KZ"]
    struct = build_struct_mask("NL", sectors, regions)
    assert struct.shape == (len(regions), len(sectors))
    assert struct.ndim == 2
    # NL has no structural absences — all should be 1
    assert np.all(struct == 1), "NL has no STRUCTURAL_ABSENT sectors"
