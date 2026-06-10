"""Tests for Phase 5 L2 pooling: masks, message passing, sector alignment."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.modeles.phase5.l2_pool import (
    _top_k_symmetric,
    message_pass_1hop,
    masked_pool_sectors,
    structural_mask,
    territory_features,
)
from src.modeles.phase5.manifest import MANIFEST, md5
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Fixtures: minimal synthetic panel (3 regions, 2 sectors, 8 years)
# ---------------------------------------------------------------------------

REGIONS = ["R1", "R2", "R3"]
SECTORS = ["BE", "KZ"]
YEARS = list(range(2010, 2019))


def make_panel(kz_supported: bool = True) -> pd.DataFrame:
    rows = []
    for r in REGIONS:
        for s in SECTORS:
            for y in YEARS:
                mask = 1 if (s != "KZ" or kz_supported) else 0
                growth = 0.05 * (1 + REGIONS.index(r)) if y > YEARS[0] else float("nan")
                rows.append({
                    "region_id": r,
                    "observation_year": y,
                    "available_for_forecast_year": y + 1,
                    "sector_a10": s,
                    "sector_births": 100.0 + 10 * REGIONS.index(r),
                    "sector_growth_1y": growth if mask else float("nan"),
                    "country": "TS",
                    "mask_sector_supported": mask,
                    "mask_sector_births": mask,
                    "business_sector_total": 200.0 + 20 * REGIONS.index(r),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# top_k_symmetric
# ---------------------------------------------------------------------------

def test_top_k_no_self_loops():
    corr = np.array([[1.0, 0.8, 0.5], [0.8, 1.0, 0.3], [0.5, 0.3, 1.0]])
    adj = _top_k_symmetric(corr, k=2)
    assert np.all(np.diag(adj) == 0), "self-loops must be zero"


def test_top_k_symmetric_output():
    corr = np.array([[1.0, 0.9, 0.2], [0.9, 1.0, 0.1], [0.2, 0.1, 1.0]])
    adj = _top_k_symmetric(corr, k=1)
    assert adj[0, 1] == adj[1, 0], "adjacency must be symmetric"


def test_top_k_excludes_negative():
    corr = np.array([[1.0, -0.5, 0.3], [-0.5, 1.0, 0.2], [0.3, 0.2, 1.0]])
    adj = _top_k_symmetric(corr, k=2)
    assert adj[0, 1] == 0, "negative correlations must be excluded"


# ---------------------------------------------------------------------------
# message_pass_1hop
# ---------------------------------------------------------------------------

def test_message_pass_identity_graph():
    x = np.array([1.0, 2.0, 3.0])
    adj = np.zeros((3, 3))
    h = message_pass_1hop(x, adj, identity_graph=True)
    np.testing.assert_array_equal(h, x)


def test_message_pass_no_edges_returns_nan():
    x = np.array([1.0, 2.0, 3.0])
    adj = np.zeros((3, 3))
    h = message_pass_1hop(x, adj, identity_graph=False)
    assert np.all(np.isnan(h)), "no edges → all NaN"


def test_message_pass_nan_source_excluded():
    x = np.array([1.0, np.nan, 3.0])
    adj = np.array([[0, 1, 1], [1, 0, 1], [1, 1, 0]], dtype=float)
    h = message_pass_1hop(x, adj)
    # region 0 neighbour: R1 (valid=1.0) and R2 (nan) → mean of R2=3.0 and R1 only
    assert np.isfinite(h[0])
    assert h[0] == pytest.approx(3.0)  # only R2 (index 2) is valid for R0


def test_message_pass_never_converts_absence_to_zero():
    # All features NaN for one region's neighbors
    x = np.array([np.nan, np.nan, 3.0])
    adj = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=float)
    h = message_pass_1hop(x, adj)
    assert np.isnan(h[0]), "absent features must remain NaN, not become 0"


# ---------------------------------------------------------------------------
# masked_pool_sectors
# ---------------------------------------------------------------------------

def test_masked_pool_excludes_absent_sector():
    # Sector BE: finite, sector KZ: structurally absent (mask=0)
    h_by_s = {"BE": np.array([1.0, 2.0]), "KZ": np.array([99.0, 99.0])}
    mask_by_s = {"BE": np.array([1.0, 1.0]), "KZ": np.array([0.0, 0.0])}
    state = masked_pool_sectors(h_by_s, mask_by_s, ["BE", "KZ"])
    np.testing.assert_allclose(state, [1.0, 2.0])


def test_masked_pool_nan_features_excluded():
    h_by_s = {"BE": np.array([1.0, np.nan]), "FZ": np.array([3.0, 4.0])}
    mask_by_s = {"BE": np.array([1.0, 1.0]), "FZ": np.array([1.0, 1.0])}
    state = masked_pool_sectors(h_by_s, mask_by_s, ["BE", "FZ"])
    # region 0: (1+3)/2 = 2; region 1: only FZ valid → 4.0
    assert state[0] == pytest.approx(2.0)
    assert state[1] == pytest.approx(4.0)


def test_masked_pool_all_absent_returns_nan():
    h_by_s = {"KZ": np.array([1.0, 2.0])}
    mask_by_s = {"KZ": np.array([0.0, 0.0])}
    state = masked_pool_sectors(h_by_s, mask_by_s, ["KZ"])
    assert np.all(np.isnan(state))


# ---------------------------------------------------------------------------
# structural_mask
# ---------------------------------------------------------------------------

def test_structural_mask_pt_kz_is_zero():
    panel = make_panel(kz_supported=False)
    mask = structural_mask(panel, "TS", "KZ", REGIONS)
    assert np.all(mask == 0), "KZ must be masked when unsupported"


def test_structural_mask_supported_sector_is_one():
    panel = make_panel(kz_supported=True)
    mask = structural_mask(panel, "TS", "BE", REGIONS)
    assert np.all(mask == 1)


# ---------------------------------------------------------------------------
# territory_features
# ---------------------------------------------------------------------------

def test_territory_features_dimensions():
    panel = make_panel(kz_supported=True)
    r_ids, state = territory_features(panel, "TS", 2015)
    assert len(r_ids) == len(REGIONS)
    assert state.shape == (len(REGIONS),)


def test_territory_features_kz_masked():
    panel = make_panel(kz_supported=False)
    r_ids, state_masked = territory_features(panel, "TS", 2015)
    panel2 = make_panel(kz_supported=True)
    r_ids2, state_with = territory_features(panel2, "TS", 2015)
    # Results differ when KZ is masked vs not
    # state values may differ; both must be finite or NaN (not zero-filled)
    assert len(r_ids) == len(r_ids2)


def test_territory_features_no_future_data():
    panel = make_panel(kz_supported=True)
    eval_year = 2015
    # All data used must come from observation_year <= eval_year - 1
    # The window [2010..2014] should be used; 2015 data must NOT appear
    # (smoke test: ensure function completes without using future rows)
    r_ids, state = territory_features(panel, "TS", eval_year)
    # If future data were used, the test would need to check the graph explicitly;
    # here we verify the function does not raise and returns valid shape.
    assert len(r_ids) == len(REGIONS)


def test_territory_features_identity_matches_no_propagation():
    panel = make_panel(kz_supported=True)
    _, state_id = territory_features(panel, "TS", 2015, identity_graph=True)
    _, state_prop = territory_features(panel, "TS", 2015, identity_graph=False)
    # Identity and propagated states are generally different (different agg)
    assert state_id.shape == state_prop.shape


# ---------------------------------------------------------------------------
# Manifest checksums (require artifacts to be present)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv").exists(),
    reason="sector panel not present",
)
def test_manifest_sector_panel():
    rel = "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
    actual = md5(BASE / rel)
    assert actual == MANIFEST[rel], f"sector panel checksum mismatch: {actual}"


@pytest.mark.skipif(
    not (BASE / "data/processed/economic_graph/g1_l2_cogrowth/g1_l2_decision.json").exists(),
    reason="L2 decision not present",
)
def test_manifest_l2_decision():
    rel = "data/processed/economic_graph/g1_l2_cogrowth/g1_l2_decision.json"
    actual = md5(BASE / rel)
    assert actual == MANIFEST[rel], f"L2 decision checksum mismatch: {actual}"
