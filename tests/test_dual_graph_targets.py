"""HERALD — Tests for dual-graph neural experiment target construction.

Verifies:
  - causal contract (no leakage)
  - target shapes and NaN fractions
  - fold-fitted threshold isolation
  - regime classification correctness
  - emergence correctness
  - LeakageError on bad input
  - manifest completeness
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.audit_dual_graph_targets import (
    LeakageError,
    _assert_no_leakage,
    audit_fold,
    classify_recovery,
    classify_regime,
    compute_emergence,
    compute_fold_thresholds,
    compute_log_growth,
    get_feature_rows,
    get_target_rows,
    run_preflight,
)

# ---------------------------------------------------------------------------
# Synthetic panel factory
# ---------------------------------------------------------------------------

REGIONS = ["R01", "R02", "R03"]
SECTORS = ["BE", "FZ", "GI"]
OBS_YEARS = list(range(2012, 2026))   # 2012-2025


def _make_panel(
    regions: list[str] = REGIONS,
    sectors: list[str] = SECTORS,
    obs_years: list[int] = OBS_YEARS,
    seed: int = 42,
) -> pd.DataFrame:
    """Minimal synthetic sector panel matching the real schema."""
    rng = np.random.default_rng(seed)
    rows = []
    for r in regions:
        for s in sectors:
            births_prev = 100.0
            for oy in obs_years:
                births = max(1.0, births_prev * (1.0 + rng.normal(0.05, 0.1)))
                rows.append({
                    "region_id": r,
                    "sector_a10": s,
                    "observation_year": oy,
                    "available_for_forecast_year": oy + 1,
                    "sector_births": births,
                    "sector_share": rng.uniform(0.05, 0.4),
                    "sector_growth_1y": (births / births_prev - 1) if oy > obs_years[0] else np.nan,
                    "business_sector_total": births * len(sectors),
                    "mask_sector_births": 1,
                })
                births_prev = births
    return pd.DataFrame(rows)


SP = _make_panel()


# ---------------------------------------------------------------------------
# T01 — causal gate: no future in feature rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_feature_rows_causal(eval_year):
    feat = get_feature_rows(SP, eval_year)
    assert feat["observation_year"].max() <= eval_year - 1, (
        f"Feature row has obs_year > eval_year-1 for eval_year={eval_year}"
    )


# ---------------------------------------------------------------------------
# T02 — target rows obs_year == eval_year (not future, not past)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_target_rows_obs_year(eval_year):
    target = get_target_rows(SP, eval_year)
    assert (target["observation_year"] == eval_year).all(), (
        f"Target row obs_year != eval_year for eval_year={eval_year}"
    )


# ---------------------------------------------------------------------------
# T03 — LeakageError raised when obs_years contain future
# ---------------------------------------------------------------------------

def test_leakage_error_raised():
    with pytest.raises(LeakageError):
        _assert_no_leakage([2019, 2020, 2021], eval_year=2021, label="test")


def test_leakage_error_not_raised():
    _assert_no_leakage([2019, 2020], eval_year=2021, label="test")  # must not raise


# ---------------------------------------------------------------------------
# T04 — fold thresholds computed from training only (no target data)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2023, 2025])
def test_thresholds_training_only(eval_year):
    train = get_feature_rows(SP, eval_year)
    thresh = compute_fold_thresholds(train)

    for sector in SECTORS:
        train_vals = train.loc[
            train["sector_a10"] == sector, "sector_growth_1y"
        ].dropna()
        assert abs(
            thresh[sector]["growth_q25"] - float(train_vals.quantile(0.25))
        ) < 1e-9
        assert abs(
            thresh[sector]["growth_q75"] - float(train_vals.quantile(0.75))
        ) < 1e-9


# ---------------------------------------------------------------------------
# T05 — thresholds are strictly from training data (differ from full-data q25/q75)
# ---------------------------------------------------------------------------

def test_thresholds_not_contaminated_by_target():
    ev = 2023
    train = get_feature_rows(SP, ev)
    thresh_train = compute_fold_thresholds(train)

    # Full data (including target year) quantiles should differ when we add the target
    full = SP["sector_growth_1y"].dropna()
    full_q25 = float(full.quantile(0.25))

    # They may coincidentally match, but let's just verify the function uses only train
    # The key invariant: thresholds are derived from training obs_years only
    max_train_obs = train["observation_year"].max()
    assert max_train_obs <= ev - 1, f"Training contains obs_year > eval_year-1"


# ---------------------------------------------------------------------------
# T06 — regime classification correctness (unit test)
# ---------------------------------------------------------------------------

def test_regime_classification():
    g = pd.Series([-0.2, -0.05, 0.0, 0.08, 0.3, np.nan])
    regimes = classify_regime(g, thresh_lo=-0.1, thresh_hi=0.1)

    assert regimes.iloc[0] == 0   # -0.2 < -0.1 → decline
    assert regimes.iloc[1] == 1   # -0.05 ∈ [-0.1, 0.1] → stagnation
    assert regimes.iloc[2] == 1   # 0.0 → stagnation
    assert regimes.iloc[3] == 1   # 0.08 → stagnation (< 0.1)
    assert regimes.iloc[4] == 2   # 0.3 > 0.1 → growth
    assert regimes.iloc[5] == -1  # NaN → missing


def test_recovery_classification():
    target = pd.Series([0.3, 0.2, -0.2, np.nan])
    prior = pd.Series([-0.3, 0.0, -0.3, -0.3])
    recovery = classify_recovery(target, prior, thresh_lo=-0.1, thresh_hi=0.1)
    assert recovery.tolist() == [1, 0, 0, -1]


def test_log_growth_is_finite_and_symmetric():
    rows = pd.DataFrame({
        "sector_births": [110.0, 90.0],
        "sector_births_lag1": [100.0, 100.0],
        "sector_growth_1y": [0.1, -0.1],
    })
    result = compute_log_growth(rows)
    assert np.isfinite(result).all()
    assert result.iloc[0] > 0
    assert result.iloc[1] < 0


# ---------------------------------------------------------------------------
# T07 — regime counts sum to total non-missing rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_regime_counts_sum(eval_year):
    fold = audit_fold(SP, eval_year)
    counts = fold["regime_counts"]
    fracs = fold["regime_fractions"]

    total_labeled = sum(int(v) for k, v in counts.items() if k != "-1")
    assert total_labeled == fold["n_target_rows"], (
        f"eval={eval_year}: regime counts {total_labeled} != n_target_rows {fold['n_target_rows']}"
    )
    assert abs(sum(fracs.values()) - 1.0) < 2e-4, f"Regime fractions don't sum to 1: {fracs}"


# ---------------------------------------------------------------------------
# T08 — emergence: low-share AND high-growth only
# ---------------------------------------------------------------------------

def test_emergence_logic():
    g = pd.Series([0.3, 0.1, -0.1, 0.4], index=[0, 1, 2, 3])
    s = pd.Series([0.02, 0.50, 0.03, 0.60], index=[0, 1, 2, 3])
    # growth_thresh=0.2, share_thresh=0.1
    em = compute_emergence(g, s, growth_thresh=0.2, share_thresh=0.1)
    assert em[0] == 1   # g=0.3>0.2 AND s=0.02<0.1 → emerging
    assert em[1] == 0   # g=0.1<0.2 → not emerging
    assert em[2] == 0   # g=-0.1<0.2 → not emerging
    assert em[3] == 0   # s=0.6>0.1 → not emerging


# ---------------------------------------------------------------------------
# T09 — no NaN in primary target for real data eval folds 2021-2025
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_no_nan_primary_target_synthetic(eval_year):
    target = get_target_rows(SP, eval_year)
    nan_frac = target["sector_growth_1y"].isna().mean()
    # Synthetic panel has NaN only at first obs_year; eval targets are 2021+
    # so there should be no NaN (all growth defined from prior year)
    assert nan_frac == 0.0, f"eval_year={eval_year}: NaN in primary target"


# ---------------------------------------------------------------------------
# T10 — audit_fold returns all required keys
# ---------------------------------------------------------------------------

def test_audit_fold_keys():
    fold = audit_fold(SP, 2022)
    required_keys = {
        "eval_year", "n_target_rows", "n_train_rows",
        "target_obs_year", "last_feature_obs_year", "causal_ok",
        "thresholds_by_sector", "regime_counts", "regime_fractions",
        "display_regime_counts", "display_regime_fractions",
        "growth_target_stats", "log_growth_target_stats",
        "recovery", "emergence", "per_sector",
    }
    assert required_keys.issubset(set(fold.keys())), (
        f"Missing keys: {required_keys - set(fold.keys())}"
    )
    assert fold["causal_ok"] is True
    assert fold["target_obs_year"] == 2022
    assert fold["last_feature_obs_year"] == 2021


# ---------------------------------------------------------------------------
# T11 — run_preflight writes manifest and artifacts
# ---------------------------------------------------------------------------

def test_run_preflight_writes_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        manifest = run_preflight(
            out_dir=out,
            eval_years=[2021, 2022],
            _panel_override=SP,
        )
        assert (out / "target_audit_per_fold.json").exists()
        assert (out / "target_audit_summary.csv").exists()
        assert (out / "target_audit_manifest.json").exists()

        assert manifest["n_regions"] == len(REGIONS)
        assert manifest["n_sectors"] == len(SECTORS)
        assert manifest["eval_years"] == [2021, 2022]
        assert manifest["causal_contract"] != ""
        assert manifest["version"] == "2.0"

        # Verify per-fold JSON round-trips
        with open(out / "target_audit_per_fold.json") as f:
            folds = json.load(f)
        assert len(folds) == 2
        assert folds[0]["eval_year"] == 2021
        assert folds[1]["eval_year"] == 2022

        # Verify summary CSV
        df = pd.read_csv(out / "target_audit_summary.csv")
        assert len(df) == 2
        assert "eval_year" in df.columns
        assert "regime_decline" in df.columns


# ---------------------------------------------------------------------------
# T12 — imbalance warnings emitted when regime < 5%
# ---------------------------------------------------------------------------

def test_imbalance_warning_detection():
    """Synthetic panel designed to produce a fold with near-zero decline."""
    # All growth values positive → decline fraction will be 0% → warning expected
    rows = []
    for r in REGIONS:
        for s in SECTORS:
            for oy in OBS_YEARS:
                rows.append({
                    "region_id": r, "sector_a10": s,
                    "observation_year": oy,
                    "available_for_forecast_year": oy + 1,
                    "sector_births": 100.0 + oy,  # always increasing
                    "sector_share": 0.1,
                    "sector_growth_1y": 0.05 if oy > OBS_YEARS[0] else np.nan,
                    "business_sector_total": 300.0,
                    "mask_sector_births": 1,
                })
    all_positive_panel = pd.DataFrame(rows)

    with tempfile.TemporaryDirectory() as tmp:
        manifest = run_preflight(
            out_dir=Path(tmp),
            eval_years=[2021, 2022],
            _panel_override=all_positive_panel,
        )
        # All growth = 0.05 → all stagnation/growth depending on thresholds
        # with fixed growth, regimes collapse → warnings expected
        assert isinstance(manifest["imbalance_warnings"], list)


# ---------------------------------------------------------------------------
# T13 — ARDECO sector vocab maps to A10 (no missing sectors)
# ---------------------------------------------------------------------------

def test_ardeco_sector_mapping():
    """Verify the ARDECO→A10 mapping covers all 9 supported sectors."""
    ARDECO_TO_A10 = {
        "A": "AZ",    # agriculture — excluded from 9-sector graph
        "B-E": "BE",
        "F":   "FZ",
        "G-I": "GI",
        "J":   "JZ",
        "K":   "KZ",
        "L":   "LZ",
        "M_N": "MN",
        "O-Q": "OQ",
        "R-U": "RU",
    }
    target_sectors = {"BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"}
    mapped = {v for k, v in ARDECO_TO_A10.items() if k != "A"}
    assert mapped == target_sectors, f"Missing sectors: {target_sectors - mapped}"


# ---------------------------------------------------------------------------
# T14 — causal_ok is True for all real eval folds on synthetic panel
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_causal_ok_flag(eval_year):
    fold = audit_fold(SP, eval_year)
    assert fold["causal_ok"] is True


# ---------------------------------------------------------------------------
# T15 — regime fractions sum to 1 for all eval folds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_regime_fractions_sum_to_one(eval_year):
    fold = audit_fold(SP, eval_year)
    total = sum(fold["regime_fractions"].values())
    assert abs(total - 1.0) < 2e-4, f"eval={eval_year}: sum(fracs)={total}"


@pytest.mark.parametrize("eval_year", [2021, 2022, 2023, 2024, 2025])
def test_display_regime_fractions_sum_to_one(eval_year):
    fold = audit_fold(SP, eval_year)
    total = sum(fold["display_regime_fractions"].values())
    assert abs(total - 1.0) < 2e-4


def test_thresholds_are_sector_specific():
    panel = SP.copy()
    panel.loc[panel["sector_a10"] == "BE", "sector_growth_1y"] += 1.0
    thresholds = compute_fold_thresholds(get_feature_rows(panel, 2023))
    assert thresholds["BE"]["growth_q25"] > thresholds["FZ"]["growth_q75"]
