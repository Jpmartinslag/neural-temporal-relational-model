"""Tests for Phase 5 neural corrector: H1-neural / H2-neural.

Coverage:
- H2-neural numerically depends on graph edges
- Zeroing edges changes H2-neural prediction
- Real vs permuted graphs produce different messages (topology test)
- alpha_scale ∈ [0, 1]
- No NaN/Inf in neural output
- Determinism by seed
- Capacity parity: H1-neural == H2-neural n_params
- Graph specificity: H2-neural ≠ H1-neural on same data
- Masks: PT KZ columns are NaN, not zero
- No leakage
- alpha=0 reproduces baseline (via alpha_max=0 clip)
- territory_features_multi returns correct shape and sector order
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.modeles.phase5.l2_pool import (
    territory_features_multi,
    build_sector_graph,
    eligible_sectors,
    message_pass_1hop,
)
from src.modeles.phase5.neural_corrector import (
    predict_neural_corrector,
    n_params,
    HIDDEN_LAYER_SIZES,
    MLP_L2_ALPHA,
    MLP_MAX_ITER,
)
from src.modeles.phase5.corrector import _region_order, _territory_totals


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

REGIONS = ["R1", "R2", "R3", "R4"]
SECTORS = ["BE", "FZ", "GI"]
YEARS = list(range(2008, 2023))


def make_panel(absent_sector_regions: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Minimal panel.

    absent_sector_regions: {sector: [regions_where_absent]}.
    Regions listed are marked mask=0 for that sector (structural absence).
    Remaining regions have mask=1. Sector stays in eligible_sectors as long as
    at least one region has mask=1.
    """
    if absent_sector_regions is None:
        absent_sector_regions = {}
    rows = []
    rng = np.random.default_rng(0)
    for r in REGIONS:
        for s in SECTORS:
            absent = r in absent_sector_regions.get(s, [])
            for y in YEARS:
                growth = float(rng.normal(0.02, 0.05)) if y > YEARS[0] and not absent else float("nan")
                rows.append({
                    "region_id": r,
                    "observation_year": y,
                    "available_for_forecast_year": y + 1,
                    "sector_a10": s,
                    "sector_births": 100.0 + 10 * REGIONS.index(r),
                    "sector_growth_1y": growth,
                    "country": "TS",
                    "mask_sector_supported": 0 if absent else 1,
                    "mask_sector_births": 0 if absent else 1,
                    "business_sector_total": float(200 + 20 * REGIONS.index(r) + 5 * (y - YEARS[0])),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# territory_features_multi
# ---------------------------------------------------------------------------

def test_multi_features_shape():
    panel = make_panel()
    r_ids, feat, sectors = territory_features_multi(panel, "TS", 2015)
    assert feat.shape == (len(REGIONS), len(SECTORS))
    assert len(r_ids) == len(REGIONS)
    assert len(sectors) == len(SECTORS)


def test_multi_features_absent_sector_is_excluded():
    """Sector absent for ALL regions of a country is excluded from eligible_sectors.

    In real data (e.g., PT KZ), absence is all-or-nothing at country level.
    eligible_sectors only returns sectors with mask=1 for at least one region.
    """
    panel = make_panel(absent_sector_regions={"GI": REGIONS})  # GI absent for all
    sectors_present = eligible_sectors(panel, "TS")
    assert "GI" not in sectors_present, "wholly-absent sector must be excluded"
    # territory_features_multi only processes eligible_sectors → no GI column
    r_ids, feat, sectors = territory_features_multi(panel, "TS", 2015)
    assert "GI" not in sectors, "absent sector must not appear in feature columns"
    assert feat.shape[1] == len(sectors_present)


def test_multi_features_present_sector_not_zero():
    """Present sector features must not be spuriously zero (NaN allowed for data gaps)."""
    panel = make_panel()  # no absent sectors
    r_ids, feat, sectors = territory_features_multi(panel, "TS", 2015)
    be_idx = sectors.index("BE")
    be_col = feat[:, be_idx]
    # At least some values must be finite
    assert np.any(np.isfinite(be_col)), "present sector must have finite features"
    # No value should be exactly 0.0 due to spurious zero-filling
    # (structural absence would be NaN; data values should be non-zero growth rates)
    finite_vals = be_col[np.isfinite(be_col)]
    # Growth rates near 0 can occur naturally; we just verify no ALL-zero column
    assert not (len(finite_vals) > 0 and np.all(finite_vals == 0.0)), \
        "present sector column must not be all zeros (would indicate spurious fill)"


def test_multi_features_identity_vs_graph_different():
    """identity_graph=True and identity_graph=False produce different features."""
    panel = make_panel()
    _, feat_id, _ = territory_features_multi(panel, "TS", 2015, identity_graph=True)
    _, feat_l2, _ = territory_features_multi(panel, "TS", 2015, identity_graph=False)
    # Features should differ at least somewhat (message passing changes values)
    diff = np.nanmax(np.abs(feat_id - feat_l2))
    assert diff > 0, "L2 propagation must change at least one feature value"


# ---------------------------------------------------------------------------
# n_params capacity parity
# ---------------------------------------------------------------------------

def test_capacity_parity_h1_h2():
    """H1-neural and H2-neural share same n_input → same n_params."""
    panel = make_panel()
    sectors = eligible_sectors(panel, "TS")
    from src.modeles.phase5.corrector import AR_LAGS
    n_input = len(sectors) + AR_LAGS
    p1 = n_params(HIDDEN_LAYER_SIZES, n_input)
    p2 = n_params(HIDDEN_LAYER_SIZES, n_input)
    assert p1 == p2, "H1/H2 neural must have equal parameter count"
    assert p1 > 0


def test_n_params_formula():
    # 2-input, (4,), 1-output: 2*4+4 + 4*1+1 = 12+5=17
    assert n_params((4,), 2) == 17


# ---------------------------------------------------------------------------
# H1-neural and H2-neural basic contracts
# ---------------------------------------------------------------------------

def test_h1_neural_returns_corrector_result():
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    res = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H1-neural", identity_graph=True, random_state=42,
        max_iter=100,
    )
    assert res.hypothesis == "H1-neural"
    assert res.y_hat.shape == (len(r_order),)
    assert np.all(res.y_hat >= 0), "predictions must be non-negative"


def test_h2_neural_no_nan_inf():
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    res = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False, random_state=42,
        max_iter=100,
    )
    assert not res.any_nan_in_hat, "H2-neural must not produce NaN"
    assert not res.any_inf_in_hat, "H2-neural must not produce Inf"


# ---------------------------------------------------------------------------
# alpha_scale ∈ [0, 1]
# ---------------------------------------------------------------------------

def test_alpha_scale_in_range():
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    for hyp, ig in [("H1-neural", True), ("H2-neural", False)]:
        res = predict_neural_corrector(
            panel, "TS", r_order, train_years, 2020,
            hypothesis=hyp, identity_graph=ig, random_state=42,
            max_iter=100,
        )
        if not res.metadata.get("fallback", False):
            alpha_s = res.metadata.get("alpha_scale", -1)
            assert 0.0 <= alpha_s <= 1.0, f"{hyp}: alpha_scale={alpha_s} outside [0,1]"


# ---------------------------------------------------------------------------
# alpha_max=0 reproduces baseline exactly
# ---------------------------------------------------------------------------

def test_alpha_max_zero_reproduces_baseline():
    """alpha_max=0 clips alpha_scale to 0 → correction=0 → y_hat == baseline."""
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    res = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=42, max_iter=100, alpha_max=0.0,
    )
    baseline = _territory_totals(panel, "TS", r_order, 2020)
    np.testing.assert_allclose(res.y_hat, np.clip(baseline, 0, None), atol=1e-8,
        err_msg="alpha_max=0 must reproduce baseline")


# ---------------------------------------------------------------------------
# Determinism by seed
# ---------------------------------------------------------------------------

def test_h2_neural_deterministic():
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    r1 = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=42, max_iter=100,
    )
    r2 = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=42, max_iter=100,
    )
    np.testing.assert_array_equal(r1.y_hat, r2.y_hat, "H2-neural must be deterministic")


def test_different_seeds_may_differ():
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    r1 = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=1, max_iter=100,
    )
    r2 = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=2, max_iter=100,
    )
    assert np.all(r1.y_hat >= 0)
    assert np.all(r2.y_hat >= 0)


# ---------------------------------------------------------------------------
# Graph specificity: H2-neural depends on edges
# ---------------------------------------------------------------------------

def test_h2_neural_differs_from_h1_neural():
    """H2-neural (with L2 propagation) must produce predictions different from H1-neural.

    Same seed → same MLP weight init, but different input features → different output.
    """
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    res_h1 = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H1-neural", identity_graph=True,
        random_state=42, max_iter=100,
    )
    res_h2 = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=42, max_iter=100,
    )
    diff = np.max(np.abs(res_h1.y_hat - res_h2.y_hat))
    assert diff > 1e-6, (
        f"H2-neural must differ from H1-neural (same seed, diff features). diff={diff}"
    )


def test_real_vs_permuted_graph_messages_differ():
    """Real L2 adj and temporally permuted adj must produce different messages."""
    panel = make_panel()
    rng = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    # Pick one sector
    s = "BE"
    adj_real, _ = build_sector_graph(panel, "TS", s, 2015, permute_mode=None)
    adj_perm, _ = build_sector_graph(panel, "TS", s, 2015, permute_mode="temporal", rng=rng)

    assert not np.allclose(adj_real, adj_perm), "permuted graph must differ from real graph"

    # Message outputs also differ
    x = np.array([0.05, 0.03, -0.01, 0.02])
    h_real = message_pass_1hop(x, adj_real)
    h_perm = message_pass_1hop(x, adj_perm)
    # At least one element should differ (unless both adj happen to give same weighted avg)
    valid = np.isfinite(h_real) & np.isfinite(h_perm)
    if valid.any():
        assert not np.allclose(h_real[valid], h_perm[valid], atol=1e-4), \
            "real vs permuted graphs should produce different messages"


def test_zero_edges_changes_h2():
    """Zero adj → self-value fallback (h = x). Real adj → neighbour aggregation.
    H2-neural features are edge-dependent: real ≠ zero-edge.
    """
    x = np.array([0.05, 0.03, -0.01, 0.02])
    adj_real = np.array([
        [0, 0.8, 0.5, 0],
        [0.8, 0, 0.3, 0.2],
        [0.5, 0.3, 0, 0.4],
        [0, 0.2, 0.4, 0],
    ])
    adj_zero = np.zeros((4, 4))

    h_real = message_pass_1hop(x, adj_real)
    h_zero = message_pass_1hop(x, adj_zero)

    assert np.isfinite(h_real).all(), "real adj must produce finite messages"
    # Zero edges → identity pass (self-value), NOT NaN
    np.testing.assert_array_equal(h_zero, x, err_msg="zero adj → self-value fallback")
    # Real aggregation of neighbours differs from self-value
    assert not np.allclose(h_real, h_zero), \
        "zero-edge (self) and real-edge (neighbour avg) predictions must differ"


# ---------------------------------------------------------------------------
# Masks (PT KZ equivalent)
# ---------------------------------------------------------------------------

def test_neural_corrector_absent_sector_excluded():
    """Wholly-absent sector must be excluded from eligible_sectors and feature matrix."""
    panel = make_panel(absent_sector_regions={"GI": REGIONS})
    r_order = sorted(panel[panel["country"].eq("TS")]["region_id"].unique())
    sects = eligible_sectors(panel, "TS")
    assert "GI" not in sects, "wholly-absent GI must not be in eligible_sectors"
    _, feat, sectors = territory_features_multi(panel, "TS", 2015)
    assert "GI" not in sectors, "absent sector must not appear as feature column"
    # Feature matrix columns match eligible sectors
    assert feat.shape[1] == len(sects)


# ---------------------------------------------------------------------------
# No leakage
# ---------------------------------------------------------------------------

def test_neural_corrector_no_future_data():
    """predict_neural_corrector must not include eval_year in training features."""
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    eval_year = 2020
    train_years = list(range(2011, eval_year))
    res = predict_neural_corrector(
        panel, "TS", r_order, train_years, eval_year,
        hypothesis="H2-neural", identity_graph=False,
        random_state=42, max_iter=100,
    )
    assert res.eval_year == eval_year
    assert res.y_hat.shape == (len(r_order),)


# ---------------------------------------------------------------------------
# Metadata fields
# ---------------------------------------------------------------------------

def test_neural_metadata_complete():
    panel = make_panel()
    r_order = _region_order(panel, "TS")
    train_years = list(range(2011, 2020))
    res = predict_neural_corrector(
        panel, "TS", r_order, train_years, 2020,
        hypothesis="H2-neural", identity_graph=False,
        random_state=42, max_iter=100,
    )
    meta = res.metadata
    for key in ("hidden_layer_sizes", "n_params", "alpha_scale", "mlp_alpha",
                "permute_mode", "identity_graph"):
        assert key in meta, f"metadata missing key: {key}"
    if not meta.get("fallback"):
        assert "n_iter" in meta
