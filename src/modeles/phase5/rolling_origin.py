"""Rolling-origin evaluation protocol for Phase 5.

For each evaluation year t:
- Training data: all (r, tau) where tau < t and data available.
- Graph edges for eval_year t: computed from window [t-5..t-1].
- No target or feature from year t enters any fitted model.

Results are per-country, never pooled across countries.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.modeles.phase5.corrector import (
    CorrectorResult,
    predict_graph_corrector,
    predict_h0,
    predict_h0b,
    wmape,
    _region_order,
    _territory_totals,
    AR_LAGS,
    RIDGE_ALPHA_CORR,
    RIDGE_ALPHA_H0B,
)


HYPOTHESES_LOCAL = ("H0", "H0b", "H1", "H2", "PC-temporal", "PC-territory")
SEED = 42


# ---------------------------------------------------------------------------
# Leakage audit
# ---------------------------------------------------------------------------

def leakage_audit(
    panel: pd.DataFrame,
    country: str,
    eval_year: int,
) -> dict[str, bool]:
    """Check that no data from eval_year leaks into the available feature set.

    Returns dict of {check: passed}.
    """
    avail = panel[
        panel["country"].eq(country)
        & panel["available_for_forecast_year"].eq(eval_year)
    ]
    has_target_year = panel[
        panel["country"].eq(country)
        & panel["observation_year"].eq(eval_year)
    ]
    max_obs = avail["observation_year"].max() if len(avail) else -1

    return {
        "max_obs_year_lt_eval": bool(max_obs < eval_year),
        "no_target_year_in_features": len(
            avail[avail["observation_year"].eq(eval_year)]
        ) == 0,
        "avail_for_forecast_is_eval": bool(
            (avail["available_for_forecast_year"] == eval_year).all()
        ) if len(avail) else True,
    }


# ---------------------------------------------------------------------------
# Rolling-origin runner
# ---------------------------------------------------------------------------

@dataclass
class YearResult:
    hypothesis: str
    country: str
    eval_year: int
    wmape: float
    wmape_baseline: float
    alpha_ratio: float
    n_train_samples: int
    any_nan: bool
    any_inf: bool
    leakage_ok: bool


def run_country(
    panel: pd.DataFrame,
    country: str,
    eval_years: list[int],
    *,
    hypotheses: tuple[str, ...] = HYPOTHESES_LOCAL,
    seed: int = SEED,
    ridge_alpha_h0b: float = RIDGE_ALPHA_H0B,
    ridge_alpha_corr: float = RIDGE_ALPHA_CORR,
    n_permutation_controls: int = 1,
) -> list[YearResult]:
    """Run all hypotheses for one country across eval_years.

    Leakage constraint: for each eval_year t, train on years where all
    data is available before t. No year-t information enters fitted models.
    """
    region_order = _region_order(panel, country)
    results: list[YearResult] = []

    # Find all available eval years in the panel
    all_avail = sorted(
        panel[panel["country"].eq(country)]["available_for_forecast_year"].unique()
    )
    # Minimum year needed: need at least AR_LAGS training years before first eval
    min_obs_year = min(all_avail)

    for eval_year in eval_years:
        # Leakage check
        leak = leakage_audit(panel, country, eval_year)
        leak_ok = all(leak.values())

        # Training years: all available years < eval_year
        train_years = [y for y in all_avail if y < eval_year and y > min_obs_year + AR_LAGS]
        if len(train_years) < 2:
            continue

        rng = np.random.default_rng(seed + eval_year)

        for hyp in hypotheses:
            try:
                if hyp == "H0":
                    y_hat, y_true = predict_h0(panel, country, region_order, eval_year)
                    y_base = y_hat.copy()
                    corr = np.zeros_like(y_hat)
                    alpha_ratio = 0.0
                    n_train = 0
                elif hyp == "H0b":
                    y_hat, y_true, _ = predict_h0b(
                        panel, country, region_order, train_years, eval_year,
                        alpha=ridge_alpha_h0b,
                    )
                    y_base = _territory_totals(panel, country, region_order, eval_year)
                    corr = np.zeros_like(y_hat)
                    alpha_ratio = 0.0
                    n_train = len(train_years) * len(region_order)
                elif hyp == "H1":
                    res = predict_graph_corrector(
                        panel, country, region_order, train_years, eval_year,
                        hypothesis="H1", identity_graph=True,
                        ridge_alpha=ridge_alpha_corr,
                    )
                    y_hat, y_true, y_base, corr = res.y_hat, res.y_true, res.y_baseline, res.correction
                    alpha_ratio, n_train = res.alpha_ratio, res.n_train_samples
                elif hyp == "H2":
                    res = predict_graph_corrector(
                        panel, country, region_order, train_years, eval_year,
                        hypothesis="H2", identity_graph=False,
                        ridge_alpha=ridge_alpha_corr,
                    )
                    y_hat, y_true, y_base, corr = res.y_hat, res.y_true, res.y_baseline, res.correction
                    alpha_ratio, n_train = res.alpha_ratio, res.n_train_samples
                elif hyp == "PC-temporal":
                    res = predict_graph_corrector(
                        panel, country, region_order, train_years, eval_year,
                        hypothesis="PC-temporal", identity_graph=False,
                        permute_mode="temporal", rng=rng,
                        ridge_alpha=ridge_alpha_corr,
                    )
                    y_hat, y_true, y_base, corr = res.y_hat, res.y_true, res.y_baseline, res.correction
                    alpha_ratio, n_train = res.alpha_ratio, res.n_train_samples
                elif hyp == "PC-territory":
                    res = predict_graph_corrector(
                        panel, country, region_order, train_years, eval_year,
                        hypothesis="PC-territory", identity_graph=False,
                        permute_mode="territory", rng=rng,
                        ridge_alpha=ridge_alpha_corr,
                    )
                    y_hat, y_true, y_base, corr = res.y_hat, res.y_true, res.y_baseline, res.correction
                    alpha_ratio, n_train = res.alpha_ratio, res.n_train_samples
                else:
                    continue

                results.append(YearResult(
                    hypothesis=hyp,
                    country=country,
                    eval_year=eval_year,
                    wmape=wmape(y_hat, y_true),
                    wmape_baseline=wmape(y_base, y_true),
                    alpha_ratio=alpha_ratio,
                    n_train_samples=n_train,
                    any_nan=bool(np.isnan(y_hat).any()),
                    any_inf=bool(np.isinf(y_hat).any()),
                    leakage_ok=leak_ok,
                ))

            except Exception as exc:
                results.append(YearResult(
                    hypothesis=hyp, country=country, eval_year=eval_year,
                    wmape=float("nan"), wmape_baseline=float("nan"),
                    alpha_ratio=float("nan"), n_train_samples=0,
                    any_nan=True, any_inf=False, leakage_ok=leak_ok,
                ))

    return results


# ---------------------------------------------------------------------------
# Audit helpers
# ---------------------------------------------------------------------------

def summarise(results: list[YearResult]) -> dict:
    df = pd.DataFrame([asdict(r) for r in results])
    summary = {}
    for hyp, grp in df.groupby("hypothesis"):
        summary[hyp] = {
            "mean_wmape": float(grp["wmape"].mean()),
            "std_wmape": float(grp["wmape"].std()),
            "mean_alpha_ratio": float(grp["alpha_ratio"].mean()),
            "any_nan_any_year": bool(grp["any_nan"].any()),
            "any_inf_any_year": bool(grp["any_inf"].any()),
            "all_leakage_ok": bool(grp["leakage_ok"].all()),
            "n_eval_years": int(len(grp)),
            "wmape_by_year": {
                int(row.eval_year): float(row.wmape)
                for row in grp.itertuples()
            },
        }
    return summary


def gate_h2_vs_controls(
    summary: dict,
    country: str,
    wmape_gain_threshold: float = 0.01,
) -> dict:
    """Check if H2 beats H0, H0b, H1, and permutation controls.

    gate_passed = H2 WMAPE < H0 WMAPE - threshold AND < H0b - threshold
                  AND < PC-temporal AND < PC-territory.
    Returns gate result dict.
    """
    if "H2" not in summary:
        return {"gate_passed": False, "reason": "H2 not in results"}

    h2 = summary["H2"]["mean_wmape"]
    results_gate = {}

    for ctrl in ("H0", "H0b", "H1", "PC-temporal", "PC-territory"):
        if ctrl not in summary:
            results_gate[ctrl] = {"beats": False, "reason": "not computed"}
            continue
        ctrl_wmape = summary[ctrl]["mean_wmape"]
        gain = ctrl_wmape - h2
        results_gate[ctrl] = {
            "h2_wmape": h2,
            "ctrl_wmape": ctrl_wmape,
            "gain": gain,
            "beats": bool(gain >= wmape_gain_threshold),
        }

    gate_passed = (
        results_gate.get("H0", {}).get("beats", False)
        and results_gate.get("H0b", {}).get("beats", False)
        and results_gate.get("PC-temporal", {}).get("beats", False)
        and results_gate.get("PC-territory", {}).get("beats", False)
    )

    return {
        "country": country,
        "gate_passed": gate_passed,
        "h2_wmape": h2,
        "controls": results_gate,
        "note": (
            "PROMOTED" if gate_passed
            else "NOT_PROMOTED — H2 does not clear all thresholds"
        ),
    }
