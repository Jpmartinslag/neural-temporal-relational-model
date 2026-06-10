"""Tests for Phase 5 rolling-origin protocol: leakage, determinism, gate."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.modeles.phase5.rolling_origin import (
    leakage_audit,
    run_country,
    summarise,
    gate_h2_vs_controls,
    YearResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REGIONS = ["R1", "R2", "R3"]
YEARS = list(range(2010, 2019))
SECTORS = ["BE", "FZ"]


def make_panel() -> pd.DataFrame:
    rows = []
    for r in REGIONS:
        for s in SECTORS:
            for y in YEARS:
                growth = 0.03 * (1 + REGIONS.index(r)) if y > YEARS[0] else float("nan")
                rows.append({
                    "region_id": r,
                    "observation_year": y,
                    "available_for_forecast_year": y + 1,
                    "sector_a10": s,
                    "sector_births": 100.0 + 10 * REGIONS.index(r),
                    "sector_growth_1y": growth,
                    "country": "TS",
                    "mask_sector_supported": 1,
                    "mask_sector_births": 1,
                    "business_sector_total": float(200 + 20 * REGIONS.index(r) + 5 * (y - YEARS[0])),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# leakage_audit
# ---------------------------------------------------------------------------

def test_leakage_audit_passes_for_valid_eval_year():
    panel = make_panel()
    result = leakage_audit(panel, "TS", 2016)
    assert result["max_obs_year_lt_eval"], "max obs year must be < eval year"
    assert result["no_target_year_in_features"]


def test_leakage_audit_no_future_rows_in_avail():
    panel = make_panel()
    # available_for_forecast_year = eval_year means observation_year = eval_year - 1
    # so max_obs_year = eval_year - 1 < eval_year → should pass
    result = leakage_audit(panel, "TS", 2015)
    assert result["max_obs_year_lt_eval"]


# ---------------------------------------------------------------------------
# run_country
# ---------------------------------------------------------------------------

def test_run_country_returns_results_for_each_hypothesis():
    panel = make_panel()
    results = run_country(
        panel, "TS",
        eval_years=[2016, 2017],
        hypotheses=("H0", "H0b"),
        seed=42,
    )
    assert len(results) >= 2
    hyps = {r.hypothesis for r in results}
    assert "H0" in hyps
    assert "H0b" in hyps


def test_run_country_all_leakage_ok():
    panel = make_panel()
    results = run_country(
        panel, "TS",
        eval_years=[2016, 2017],
        hypotheses=("H0",),
        seed=42,
    )
    assert all(r.leakage_ok for r in results), "all results must pass leakage check"


def test_run_country_no_inf():
    panel = make_panel()
    results = run_country(
        panel, "TS",
        eval_years=[2016],
        hypotheses=("H0", "H0b", "H1", "H2"),
        seed=42,
    )
    for r in results:
        assert not r.any_inf, f"{r.hypothesis}/{r.eval_year} has Inf"


def test_run_country_deterministic():
    panel = make_panel()
    r1 = run_country(panel, "TS", eval_years=[2016], hypotheses=("H0", "H1"), seed=42)
    r2 = run_country(panel, "TS", eval_years=[2016], hypotheses=("H0", "H1"), seed=42)
    for a, b in zip(r1, r2):
        assert a.wmape == b.wmape or (np.isnan(a.wmape) and np.isnan(b.wmape))


def test_run_country_nonneg_wmape():
    panel = make_panel()
    results = run_country(panel, "TS", eval_years=[2016, 2017], hypotheses=("H0",), seed=42)
    for r in results:
        if np.isfinite(r.wmape):
            assert r.wmape >= 0, f"WMAPE must be non-negative, got {r.wmape}"


# ---------------------------------------------------------------------------
# summarise
# ---------------------------------------------------------------------------

def test_summarise_structure():
    results = [
        YearResult("H0", "TS", 2016, 0.10, 0.10, 0.0, 0, False, False, True),
        YearResult("H0", "TS", 2017, 0.12, 0.12, 0.0, 0, False, False, True),
        YearResult("H2", "TS", 2016, 0.08, 0.10, 0.05, 20, False, False, True),
        YearResult("H2", "TS", 2017, 0.09, 0.12, 0.04, 20, False, False, True),
    ]
    summary = summarise(results)
    assert "H0" in summary and "H2" in summary
    assert summary["H0"]["n_eval_years"] == 2
    assert summary["H2"]["mean_wmape"] == pytest.approx(0.085)
    assert summary["H0"]["all_leakage_ok"]


def test_summarise_wmape_by_year():
    results = [
        YearResult("H0", "TS", 2016, 0.10, 0.10, 0.0, 0, False, False, True),
        YearResult("H0", "TS", 2017, 0.20, 0.20, 0.0, 0, False, False, True),
    ]
    summary = summarise(results)
    assert summary["H0"]["wmape_by_year"][2016] == pytest.approx(0.10)
    assert summary["H0"]["wmape_by_year"][2017] == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# gate_h2_vs_controls
# ---------------------------------------------------------------------------

def test_gate_passes_when_h2_best():
    summary = {
        "H0":          {"mean_wmape": 0.20},
        "H0b":         {"mean_wmape": 0.18},
        "H1":          {"mean_wmape": 0.16},
        "PC-temporal": {"mean_wmape": 0.17},
        "PC-territory":{"mean_wmape": 0.19},
        "H2":          {"mean_wmape": 0.10},
    }
    gate = gate_h2_vs_controls(summary, "TS", wmape_gain_threshold=0.01)
    assert gate["gate_passed"], f"Expected gate pass, got: {gate}"


def test_gate_fails_when_h2_not_best():
    summary = {
        "H0":          {"mean_wmape": 0.10},
        "H0b":         {"mean_wmape": 0.10},
        "H1":          {"mean_wmape": 0.10},
        "PC-temporal": {"mean_wmape": 0.10},
        "PC-territory":{"mean_wmape": 0.10},
        "H2":          {"mean_wmape": 0.15},  # worse than all
    }
    gate = gate_h2_vs_controls(summary, "TS", wmape_gain_threshold=0.01)
    assert not gate["gate_passed"]


def test_gate_missing_h2_returns_not_passed():
    summary = {"H0": {"mean_wmape": 0.10}}
    gate = gate_h2_vs_controls(summary, "TS")
    assert not gate["gate_passed"]
    assert "not in results" in gate.get("reason", "")
