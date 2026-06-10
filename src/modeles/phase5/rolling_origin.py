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
from src.modeles.phase5.neural_corrector import (
    predict_neural_corrector,
    HIDDEN_LAYER_SIZES,
    MLP_L2_ALPHA,
    MLP_MAX_ITER,
)

# Linear (Ridge) hypotheses — clearly labelled; H1/H2 kept for back-compat
HYPOTHESES_LINEAR = ("H0", "H0b", "H1-linear", "H2-linear",
                     "PC-temporal-linear", "PC-territory-linear")
# Neural (MLP) hypotheses
HYPOTHESES_NEURAL = ("H1-neural", "H2-neural",
                     "PC-temporal-neural", "PC-territory-neural")
# All hypotheses for local smoke
HYPOTHESES_LOCAL = HYPOTHESES_LINEAR + HYPOTHESES_NEURAL
SEED = 42


# Map legacy short names to canonical names
_LEGACY_MAP = {"H1": "H1-linear", "H2": "H2-linear",
               "PC-temporal": "PC-temporal-linear", "PC-territory": "PC-territory-linear"}


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
# Hypothesis dispatch helper
# ---------------------------------------------------------------------------

def _dispatch_hypothesis(
    hyp: str,
    panel: pd.DataFrame,
    country: str,
    region_order: list[str],
    train_years: list[int],
    eval_year: int,
    *,
    rng: np.random.Generator,
    seed: int,
    ridge_alpha_h0b: float,
    ridge_alpha_corr: float,
    mlp_alpha: float,
    mlp_max_iter: int,
    hidden_layer_sizes: tuple[int, ...],
) -> CorrectorResult | None:
    """Route one hypothesis to the correct predictor. Returns None to skip."""
    if hyp == "H0":
        y_hat, y_true = predict_h0(panel, country, region_order, eval_year)
        y_base = y_hat.copy()
        return CorrectorResult(
            hypothesis=hyp, country=country, eval_year=eval_year,
            y_hat=y_hat, y_true=y_true, y_baseline=y_base,
            correction=np.zeros_like(y_hat),
            wmape=wmape(y_hat, y_true), wmape_baseline=wmape(y_base, y_true),
            alpha_ratio=0.0, n_train_samples=0,
            any_nan_in_hat=bool(np.isnan(y_hat).any()),
            any_inf_in_hat=bool(np.isinf(y_hat).any()),
        )

    if hyp == "H0b":
        y_hat, y_true, _ = predict_h0b(
            panel, country, region_order, train_years, eval_year, alpha=ridge_alpha_h0b,
        )
        y_base = _territory_totals(panel, country, region_order, eval_year)
        return CorrectorResult(
            hypothesis=hyp, country=country, eval_year=eval_year,
            y_hat=y_hat, y_true=y_true, y_baseline=y_base,
            correction=np.zeros_like(y_hat),
            wmape=wmape(y_hat, y_true), wmape_baseline=wmape(y_base, y_true),
            alpha_ratio=0.0, n_train_samples=len(train_years) * len(region_order),
            any_nan_in_hat=bool(np.isnan(y_hat).any()),
            any_inf_in_hat=bool(np.isinf(y_hat).any()),
        )

    # Linear (Ridge) graph correctors
    _LINEAR_HYPS = {
        "H1-linear": (True, None),
        "H2-linear": (False, None),
        "PC-temporal-linear": (False, "temporal"),
        "PC-territory-linear": (False, "territory"),
    }
    if hyp in _LINEAR_HYPS:
        ig, pm = _LINEAR_HYPS[hyp]
        return predict_graph_corrector(
            panel, country, region_order, train_years, eval_year,
            hypothesis=hyp, identity_graph=ig,
            permute_mode=pm, rng=rng if pm else None,
            ridge_alpha=ridge_alpha_corr,
        )

    # Neural (MLP) graph correctors
    _NEURAL_HYPS = {
        "H1-neural": (True, None),
        "H2-neural": (False, None),
        "PC-temporal-neural": (False, "temporal"),
        "PC-territory-neural": (False, "territory"),
    }
    if hyp in _NEURAL_HYPS:
        ig, pm = _NEURAL_HYPS[hyp]
        return predict_neural_corrector(
            panel, country, region_order, train_years, eval_year,
            hypothesis=hyp, identity_graph=ig,
            permute_mode=pm, rng=rng if pm else None,
            hidden_layer_sizes=hidden_layer_sizes,
            mlp_alpha=mlp_alpha, max_iter=mlp_max_iter,
            random_state=seed + eval_year,
        )

    return None  # unknown hypothesis


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
    mlp_alpha: float = MLP_L2_ALPHA,
    mlp_max_iter: int = MLP_MAX_ITER,
    hidden_layer_sizes: tuple[int, ...] = HIDDEN_LAYER_SIZES,
) -> list[YearResult]:
    """Run all hypotheses for one country across eval_years.

    Leakage constraint: for each eval_year t, train on years where all
    data is available before t. No year-t information enters fitted models.

    Hypothesis names:
      Linear (Ridge): H0, H0b, H1-linear, H2-linear, PC-temporal-linear, PC-territory-linear
      Neural (MLP):   H1-neural, H2-neural, PC-temporal-neural, PC-territory-neural
    Legacy names H1/H2/PC-temporal/PC-territory are accepted (mapped to -linear).
    """
    region_order = _region_order(panel, country)
    results: list[YearResult] = []

    all_avail = sorted(
        panel[panel["country"].eq(country)]["available_for_forecast_year"].unique()
    )
    min_obs_year = min(all_avail)

    # Normalise legacy hypothesis names
    hypotheses = tuple(_LEGACY_MAP.get(h, h) for h in hypotheses)

    for eval_year in eval_years:
        leak = leakage_audit(panel, country, eval_year)
        leak_ok = all(leak.values())
        train_years = [y for y in all_avail if y < eval_year and y > min_obs_year + AR_LAGS]
        if len(train_years) < 2:
            continue

        rng = np.random.default_rng(seed + eval_year)

        for hyp in hypotheses:
            try:
                res = _dispatch_hypothesis(
                    hyp, panel, country, region_order, train_years, eval_year,
                    rng=rng, seed=seed,
                    ridge_alpha_h0b=ridge_alpha_h0b,
                    ridge_alpha_corr=ridge_alpha_corr,
                    mlp_alpha=mlp_alpha,
                    mlp_max_iter=mlp_max_iter,
                    hidden_layer_sizes=hidden_layer_sizes,
                )

                if res is None:
                    continue

                results.append(YearResult(
                    hypothesis=hyp,
                    country=country,
                    eval_year=eval_year,
                    wmape=res.wmape,
                    wmape_baseline=res.wmape_baseline,
                    alpha_ratio=res.alpha_ratio,
                    n_train_samples=res.n_train_samples,
                    any_nan=res.any_nan_in_hat,
                    any_inf=res.any_inf_in_hat,
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


def gate_h2_neural(
    summary: dict,
    country: str,
    wmape_gain_threshold: float = 0.01,
    no_regression_vs_h0b: float = 0.10,
) -> dict:
    """Local gate for H2-neural (smoke test, not final HPC gate).

    Criteria (all must pass):
    1. H2-neural in summary.
    2. H2-neural ≠ H1-neural: |mean_wmape difference| > 0.001 (graph matters).
    3. H2-neural beats PC-temporal-neural AND PC-territory-neural by ≥ threshold.
    4. H2-neural does not regress >no_regression_vs_h0b (10%) against H0b.
       (regression = H2_wmape > H0b_wmape * (1 + no_regression_vs_h0b))

    Note: beating H0b definitively is NOT required for the smoke gate;
    that comparison is confirmed in the full HPC battery.
    """
    if "H2-neural" not in summary:
        return {"gate_passed": False, "reason": "H2-neural not in results"}

    h2 = summary["H2-neural"]["mean_wmape"]
    results_gate: dict = {}

    # Check graph specificity: H2-neural must differ from H1-neural
    if "H1-neural" in summary:
        h1 = summary["H1-neural"]["mean_wmape"]
        diff = abs(h2 - h1)
        results_gate["graph_specificity"] = {
            "h2_wmape": h2, "h1_wmape": h1, "diff": diff,
            "beats": diff > 0.001,
        }
    else:
        results_gate["graph_specificity"] = {"beats": False, "reason": "H1-neural missing"}

    # H2-neural vs permuted controls
    for ctrl in ("PC-temporal-neural", "PC-territory-neural"):
        if ctrl not in summary:
            results_gate[ctrl] = {"beats": False, "reason": "not computed"}
            continue
        ctrl_wmape = summary[ctrl]["mean_wmape"]
        gain = ctrl_wmape - h2
        results_gate[ctrl] = {
            "h2_wmape": h2, "ctrl_wmape": ctrl_wmape, "gain": gain,
            "beats": bool(gain >= wmape_gain_threshold),
        }

    # H2-neural regression vs H0b
    if "H0b" in summary:
        h0b = summary["H0b"]["mean_wmape"]
        max_allowed = h0b * (1.0 + no_regression_vs_h0b)
        regression_ok = bool(h2 <= max_allowed)
        results_gate["no_regression_vs_h0b"] = {
            "h2_wmape": h2, "h0b_wmape": h0b,
            "max_allowed": max_allowed, "beats": regression_ok,
        }
    else:
        results_gate["no_regression_vs_h0b"] = {"beats": True, "reason": "H0b not computed"}

    gate_passed = all(v.get("beats", False) for v in results_gate.values())

    return {
        "country": country,
        "gate_passed": gate_passed,
        "h2_neural_wmape": h2,
        "controls": results_gate,
        "note": "HPC_READY" if gate_passed else "HPC_BLOCKED — smoke gate not cleared",
    }


def gate_h2_vs_controls(
    summary: dict,
    country: str,
    wmape_gain_threshold: float = 0.01,
) -> dict:
    """Legacy gate for H2-linear (full HPC gate, not smoke).

    Accepts both old names (H2, PC-temporal) and new names (H2-linear, etc.).
    """
    h2_key = "H2-linear" if "H2-linear" in summary else "H2"
    if h2_key not in summary:
        return {"gate_passed": False, "reason": "H2-linear not in results"}

    h2 = summary[h2_key]["mean_wmape"]
    results_gate = {}

    ctrl_map = {
        "H0": "H0", "H0b": "H0b",
        "H1-linear": "H1-linear",
        "PC-temporal-linear": "PC-temporal-linear",
        "PC-territory-linear": "PC-territory-linear",
    }
    for ctrl in ctrl_map:
        key = ctrl_map[ctrl]
        actual = key if key in summary else ctrl.replace("-linear", "")
        if actual not in summary:
            results_gate[ctrl] = {"beats": False, "reason": "not computed"}
            continue
        ctrl_wmape = summary[actual]["mean_wmape"]
        gain = ctrl_wmape - h2
        results_gate[ctrl] = {
            "h2_wmape": h2, "ctrl_wmape": ctrl_wmape, "gain": gain,
            "beats": bool(gain >= wmape_gain_threshold),
        }

    gate_passed = (
        results_gate.get("H0", {}).get("beats", False)
        and results_gate.get("H0b", {}).get("beats", False)
        and results_gate.get("PC-temporal-linear", {}).get("beats", False)
        and results_gate.get("PC-territory-linear", {}).get("beats", False)
    )

    return {
        "country": country,
        "gate_passed": gate_passed,
        "h2_wmape": h2,
        "controls": results_gate,
        "note": "PROMOTED" if gate_passed else "NOT_PROMOTED — H2 does not clear all thresholds",
    }
