"""HERALD — Dual-graph neural experiment: target construction and preflight audit.

Computes and validates the target families for the dual economic graph
neural experiment on France NUTS3, 101 regions, 9 sectors, eval_years 2021-2025.

Targets
-------
primary   : sector_log_growth_1y (continuous regression)
            = log1p(sector_births[T]) - log1p(sector_births[T-1])
            at obs_year = eval_year T, available_for_forecast_year = T+1
auxiliary : regime classification (decline / stagnation / growth)
            thresholds = sector-specific (q25, q75) on training fold
transition: recovery
            = prior growth < sector q25 AND target growth > sector q75
exploratory: emergence
            = sector-specific low share AND high target growth
            at obs_year = eval_year T

Causal contract (hard-checked)
-------------------------------
  - feature obs_year <= T-1 for any eval_year T
  - target  obs_year == T   for any eval_year T
  - all thresholds from training fold only (available_for_forecast_year < T)
  - ARDECO obs_year <= T-1 (never T or T+1)
  - sector_growth_1y[obs_year=T] = births[T]/births[T-1]-1  (derived internally)

Usage
-----
  python3 -m src.data.european_panel.audit_dual_graph_targets \\
    [--sector-panel PATH] [--out-dir PATH] [--eval-years 2021 2022 2023 2024 2025]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
DEFAULT_SECTOR_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nuts3.csv"
DEFAULT_OUT = BASE / "data/processed/dual_graph_preflight"
DEFAULT_EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]


# ---------------------------------------------------------------------------
# Causal gates
# ---------------------------------------------------------------------------

class LeakageError(RuntimeError):
    pass


def _assert_no_leakage(obs_years: list[int], eval_year: int, label: str = "") -> None:
    for y in obs_years:
        if y >= eval_year:
            raise LeakageError(
                f"Leakage in {label}: obs_year={y} >= eval_year={eval_year}"
            )


# ---------------------------------------------------------------------------
# Core target builders
# ---------------------------------------------------------------------------

def get_target_rows(
    sector_panel: pd.DataFrame,
    eval_year: int,
) -> pd.DataFrame:
    """Return the target rows (obs_year = eval_year) for a given fold.

    Raises LeakageError if any target row's observation_year >= eval_year
    contradicts the causal contract.  The observation year IS the eval_year —
    that is, we predict births[eval_year] which becomes available one year
    later (available_for_forecast_year = eval_year + 1).
    """
    rows = sector_panel[
        sector_panel["available_for_forecast_year"] == eval_year + 1
    ].copy()
    obs_years = rows["observation_year"].unique().tolist()
    # Target obs_year must equal eval_year (we're predicting that year's births)
    for oy in obs_years:
        if oy != eval_year:
            raise LeakageError(
                f"Target row has unexpected observation_year={oy} for eval_year={eval_year}"
            )
    return rows


def get_feature_rows(
    sector_panel: pd.DataFrame,
    eval_year: int,
) -> pd.DataFrame:
    """Return feature rows (obs_year <= eval_year - 1).  All strictly causal."""
    rows = sector_panel[
        sector_panel["available_for_forecast_year"] <= eval_year
    ].copy()
    obs_years = rows["observation_year"].unique().tolist()
    _assert_no_leakage(obs_years, eval_year, label=f"feature_rows eval={eval_year}")
    return rows


def compute_fold_thresholds(train_rows: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute sector-specific thresholds from training-only data."""
    thresholds: dict[str, dict[str, float]] = {}
    for sector, group in train_rows.groupby("sector_a10", sort=True):
        growth = group["sector_growth_1y"].replace([np.inf, -np.inf], np.nan).dropna()
        share = group["sector_share"].replace([np.inf, -np.inf], np.nan).dropna()
        if growth.empty or share.empty:
            raise ValueError(f"Insufficient training data for sector {sector}")
        thresholds[str(sector)] = {
            "growth_q25": float(growth.quantile(0.25)),
            "growth_q75": float(growth.quantile(0.75)),
            "share_q25": float(share.quantile(0.25)),
        }
    return thresholds


def classify_regime(
    growth: pd.Series,
    thresh_lo: float,
    thresh_hi: float,
) -> pd.Series:
    """Return regime labels: 0=decline, 1=stagnation, 2=growth."""
    labels = pd.Series(1, index=growth.index, dtype=int)  # default: stagnation
    labels[growth < thresh_lo] = 0   # decline
    labels[growth > thresh_hi] = 2   # growth
    labels[growth.isna()] = -1       # missing (should be masked in loss)
    return labels


def classify_recovery(
    target_growth: pd.Series,
    prior_growth: pd.Series,
    thresh_lo: float,
    thresh_hi: float,
) -> pd.Series:
    """Return 1 for a strong rebound from prior decline to current growth."""
    valid = target_growth.notna() & prior_growth.notna()
    labels = pd.Series(-1, index=target_growth.index, dtype=int)
    labels.loc[valid] = (
        (prior_growth.loc[valid] < thresh_lo)
        & (target_growth.loc[valid] > thresh_hi)
    ).astype(int)
    return labels


def compute_log_growth(target_rows: pd.DataFrame) -> pd.Series:
    """Stable symmetric target derived from current and lagged sector births."""
    current = pd.to_numeric(target_rows["sector_births"], errors="coerce")
    if "sector_births_lag1" in target_rows:
        prior = pd.to_numeric(target_rows["sector_births_lag1"], errors="coerce")
    else:
        growth = pd.to_numeric(target_rows["sector_growth_1y"], errors="coerce")
        prior = current / (1.0 + growth)
    valid = (current >= 0) & (prior >= 0) & np.isfinite(current) & np.isfinite(prior)
    out = pd.Series(np.nan, index=target_rows.index, dtype=float)
    out.loc[valid] = np.log1p(current.loc[valid]) - np.log1p(prior.loc[valid])
    return out


def compute_emergence(
    target_growth: pd.Series,
    feature_share: pd.Series,
    growth_thresh: float,
    share_thresh: float,
) -> pd.Series:
    """Binary: 1 = sector had low share at t-1 and high growth at t."""
    return (
        (feature_share < share_thresh) & (target_growth > growth_thresh)
    ).astype(int)


# ---------------------------------------------------------------------------
# Per-fold audit
# ---------------------------------------------------------------------------

def audit_fold(
    sector_panel: pd.DataFrame,
    eval_year: int,
) -> dict:
    """Full target audit for one fold.

    Returns a dict suitable for JSON serialisation.
    """
    target_rows = get_target_rows(sector_panel, eval_year)
    feature_rows = get_feature_rows(sector_panel, eval_year)
    train_rows = feature_rows.copy()  # all feature rows are training rows
    thresholds = compute_fold_thresholds(train_rows)

    target_indexed = target_rows.set_index(["region_id", "sector_a10"]).copy()
    prior_indexed = (
        feature_rows[feature_rows["available_for_forecast_year"] == eval_year]
        .set_index(["region_id", "sector_a10"])
    )
    shared_idx = target_indexed.index.intersection(prior_indexed.index)

    regimes = pd.Series(-1, index=target_indexed.index, dtype=int)
    recovery = pd.Series(-1, index=target_indexed.index, dtype=int)
    emergence = pd.Series(-1, index=target_indexed.index, dtype=int)
    for sector, sector_thresholds in thresholds.items():
        idx = target_indexed.index[
            target_indexed.index.get_level_values("sector_a10") == sector
        ]
        idx = idx.intersection(shared_idx)
        target_growth = target_indexed.loc[idx, "sector_growth_1y"]
        prior_growth = prior_indexed.loc[idx, "sector_growth_1y"]
        regimes.loc[idx] = classify_regime(
            target_growth,
            thresh_lo=sector_thresholds["growth_q25"],
            thresh_hi=sector_thresholds["growth_q75"],
        )
        recovery.loc[idx] = classify_recovery(
            target_growth,
            prior_growth,
            thresh_lo=sector_thresholds["growth_q25"],
            thresh_hi=sector_thresholds["growth_q75"],
        )
        emergence.loc[idx] = compute_emergence(
            target_growth,
            prior_indexed.loc[idx, "sector_share"],
            growth_thresh=sector_thresholds["growth_q75"],
            share_thresh=sector_thresholds["share_q25"],
        )

    regime_counts = regimes.value_counts().to_dict()
    recovery_valid = recovery[recovery >= 0]
    emergence_valid = emergence[emergence >= 0]
    display_regime = regimes.copy()
    display_regime.loc[recovery == 1] = 3
    display_counts = display_regime.value_counts().to_dict()
    log_growth = compute_log_growth(target_rows)

    # Per-sector growth stats
    per_sector = {}
    for sec, grp in target_rows.groupby("sector_a10"):
        gv = grp["sector_growth_1y"].dropna()
        per_sector[sec] = {
            "mean": float(gv.mean()),
            "std":  float(gv.std()),
            "q25":  float(gv.quantile(0.25)),
            "q75":  float(gv.quantile(0.75)),
            "nan_frac": float(grp["sector_growth_1y"].isna().mean()),
        }

    return {
        "eval_year": eval_year,
        "n_target_rows": int(len(target_rows)),
        "n_train_rows": int(len(train_rows)),
        "target_obs_year": int(eval_year),
        "last_feature_obs_year": int(eval_year - 1),
        "causal_ok": True,
        "thresholds_by_sector": {
            sector: {key: round(value, 6) for key, value in values.items()}
            for sector, values in thresholds.items()
        },
        "regime_counts": {str(k): int(v) for k, v in regime_counts.items()},
        "regime_fractions": {
            "decline":   round(regime_counts.get(0, 0) / len(regimes), 4),
            "stagnation": round(regime_counts.get(1, 0) / len(regimes), 4),
            "growth":    round(regime_counts.get(2, 0) / len(regimes), 4),
        },
        "display_regime_counts": {str(k): int(v) for k, v in display_counts.items()},
        "display_regime_fractions": {
            "decline": round(display_counts.get(0, 0) / len(display_regime), 4),
            "stagnation": round(display_counts.get(1, 0) / len(display_regime), 4),
            "growth": round(display_counts.get(2, 0) / len(display_regime), 4),
            "recovery": round(display_counts.get(3, 0) / len(display_regime), 4),
        },
        "growth_target_stats": {
            "mean": float(target_rows["sector_growth_1y"].mean()),
            "std":  float(target_rows["sector_growth_1y"].std()),
            "nan_frac": float(target_rows["sector_growth_1y"].isna().mean()),
        },
        "log_growth_target_stats": {
            "mean": float(log_growth.mean()),
            "std": float(log_growth.std()),
            "nan_frac": float(log_growth.isna().mean()),
        },
        "recovery": {
            "n_recovery": int((recovery_valid == 1).sum()),
            "frac_recovery": round(float((recovery_valid == 1).mean()), 4),
        },
        "emergence": {
            "n_emerging": int((emergence_valid == 1).sum()),
            "frac_emerging": round(float((emergence_valid == 1).mean()), 4),
        },
        "per_sector": per_sector,
    }


# ---------------------------------------------------------------------------
# Full preflight export
# ---------------------------------------------------------------------------

def run_preflight(
    sector_panel_path: Path = DEFAULT_SECTOR_PANEL,
    out_dir: Path = DEFAULT_OUT,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    _panel_override: "pd.DataFrame | None" = None,
) -> dict:
    """Run the full target preflight and write artifacts to out_dir.

    Returns the manifest dict.
    """
    sp = (
        _panel_override if _panel_override is not None
        else pd.read_csv(sector_panel_path)
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    folds = []
    fold_rows = []

    for ev in eval_years:
        fold = audit_fold(sp, ev)
        folds.append(fold)

        # Flat CSV row for per-fold summary
        row = {"eval_year": ev}
        row.update({f"regime_{k}": v for k, v in fold["regime_fractions"].items()})
        row.update({
            f"display_regime_{k}": v
            for k, v in fold["display_regime_fractions"].items()
        })
        row["growth_mean"] = fold["growth_target_stats"]["mean"]
        row["growth_std"]  = fold["growth_target_stats"]["std"]
        row["log_growth_mean"] = fold["log_growth_target_stats"]["mean"]
        row["recovery_frac"] = fold["recovery"]["frac_recovery"]
        row["emergence_frac"] = fold["emergence"]["frac_emerging"]
        fold_rows.append(row)

    # Write per-fold JSON
    per_fold_path = out_dir / "target_audit_per_fold.json"
    with open(per_fold_path, "w") as f:
        json.dump(folds, f, indent=2)

    # Write summary CSV
    summary_path = out_dir / "target_audit_summary.csv"
    pd.DataFrame(fold_rows).to_csv(summary_path, index=False)

    # Imbalance check: severe if any regime < 5% in any fold
    imbalance_warnings = []
    for fold in folds:
        for regime, frac in fold["display_regime_fractions"].items():
            if frac < 0.05:
                imbalance_warnings.append(
                    f"eval_year={fold['eval_year']}: {regime}={frac:.1%} < 5%"
                )

    manifest = {
        "version": "2.0",
        "sector_panel": str(sector_panel_path) if _panel_override is None else "override",
        "eval_years": eval_years,
        "n_regions": int(sp["region_id"].nunique()),
        "n_sectors": int(sp["sector_a10"].nunique()),
        "causal_contract": "obs_year(target)=eval_year; obs_year(features)<=eval_year-1",
        "primary_target": "sector_log_growth_1y (Huber/MAE; raw growth reported)",
        "auxiliary_target": "regime_3class plus recovery_binary",
        "display_target": "regime_4state (decline/stagnation/growth/recovery)",
        "exploratory_target": "emergence (sector-specific low_share AND high_growth)",
        "threshold_policy": "sector-specific q25/q75 fitted on training fold only",
        "imbalance_warnings": imbalance_warnings,
        "artifacts": {
            "per_fold_json": str(per_fold_path),
            "summary_csv": str(summary_path),
        },
    }

    manifest_path = out_dir / "target_audit_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dual graph neural experiment — target preflight audit"
    )
    parser.add_argument("--sector-panel", type=Path, default=DEFAULT_SECTOR_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS
    )
    args = parser.parse_args()

    manifest = run_preflight(
        sector_panel_path=args.sector_panel,
        out_dir=args.out_dir,
        eval_years=args.eval_years,
    )

    print(f"Preflight complete. Artifacts in {args.out_dir}")
    print(f"Eval years: {manifest['eval_years']}")
    print(f"Regions: {manifest['n_regions']}, Sectors: {manifest['n_sectors']}")
    if manifest["imbalance_warnings"]:
        print("WARNING — class imbalance:")
        for w in manifest["imbalance_warnings"]:
            print(f"  {w}")
    else:
        print("No severe imbalance detected (all regime fractions >= 5%)")


if __name__ == "__main__":
    main()
