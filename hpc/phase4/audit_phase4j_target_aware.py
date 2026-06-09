#!/usr/bin/env python3
"""Phase 4J target-aware reaggregation (no retraining).

Reads existing Phase 4J-A predictions and re-summarizes them under the Path M
protocol: per-country WMAPE labelled by target concept, yearly wins, worst year,
p90 of the yearly error, pooled only as sensitivity, and the pre-specified
tail-risk gate for the fixed 50/50 mean. Predictions are NOT recomputed; this
only changes how existing forecasts are reported.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]

# Unit-precise target concepts (Phase 4J semantic gate).
TARGET_CONCEPT = {
    "fr": "establishment_creation",
    "nl": "local_unit_opening",
    "be": "vat_first_registration",
    "pt": "enterprise_birth",
}
COMPONENTS = ("persistence", "ridge", "mean_50_50")

# Pre-specified tail-risk thresholds. Fixed BEFORE inspecting the outcome.
TAIL_RISK = {
    "mean_improves_every_country": True,
    "max_country_mean_regression_vs_persistence": 0.01,   # <= 1%
    "max_country_year_regression_vs_persistence": 0.10,   # <= 10%
    "min_country_year_win_fraction_vs_persistence": 0.50, # >= 50%
}


def wmape(frame: pd.DataFrame) -> float:
    denominator = float(frame["y_true"].abs().sum())
    if denominator <= 0:
        raise ValueError("Non-positive WMAPE denominator")
    return float((frame["y_true"] - frame["y_pred"]).abs().sum() / denominator)


def yearly_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (country, config, year), frame in predictions.groupby(
        ["country", "config", "target_year"]
    ):
        rows.append(
            {
                "country": country,
                "target_concept": TARGET_CONCEPT[country],
                "config": config,
                "target_year": int(year),
                "wmape": wmape(frame),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase4j-root",
        type=Path,
        default=Path("hpc_results/herald_phase4j_a_20260609_local_r1"),
    )
    args = parser.parse_args()
    root = (
        BASE / args.phase4j_root
        if not args.phase4j_root.is_absolute()
        else args.phase4j_root
    )
    predictions = pd.read_csv(root / "phase4j_a_predictions.csv")
    predictions = predictions[predictions["config"].isin(COMPONENTS)].copy()

    yearly = yearly_table(predictions)
    pivot = yearly.pivot_table(
        index=["country", "target_concept", "target_year"],
        columns="config",
        values="wmape",
    ).reset_index()
    pivot["reg_50_50_vs_persistence"] = (
        pivot["mean_50_50"] - pivot["persistence"]
    ) / pivot["persistence"]

    # Per-country, target-aware.
    per_country = (
        yearly.groupby(["country", "target_concept", "config"], as_index=False)
        .agg(
            mean_yearly_wmape=("wmape", "mean"),
            worst_year_wmape=("wmape", "max"),
            p90_yearly_wmape=("wmape", lambda s: float(np.quantile(s, 0.90))),
        )
        .sort_values(["country", "mean_yearly_wmape"])
    )

    # Yearly wins of fixed 50/50 vs persistence and ridge.
    win_rows = []
    for country, frame in pivot.groupby("country"):
        win_rows.append(
            {
                "country": country,
                "target_concept": TARGET_CONCEPT[country],
                "years": int(len(frame)),
                "wins_vs_persistence": int(
                    (frame["mean_50_50"] <= frame["persistence"]).sum()
                ),
                "wins_vs_ridge": int(
                    (frame["mean_50_50"] <= frame["ridge"]).sum()
                ),
                "worst_year_reg_vs_persistence": float(
                    frame["reg_50_50_vs_persistence"].max()
                ),
            }
        )
    wins = pd.DataFrame(win_rows)

    # Pooled WMAPE (sensitivity only).
    pooled = pd.DataFrame(
        [
            {"config": config, "pooled_wmape": wmape(frame)}
            for config, frame in predictions.groupby("config")
        ]
    )

    # Pre-specified tail-risk gate for fixed 50/50.
    means = per_country.pivot(
        index="country", columns="config", values="mean_yearly_wmape"
    )
    country_mean_reg = (means["mean_50_50"] / means["persistence"] - 1.0)
    n_year = len(pivot)
    year_wins = int((pivot["mean_50_50"] <= pivot["persistence"]).sum())
    checks = {
        "mean_improves_every_country": bool((country_mean_reg < 0).all()),
        "max_country_mean_regression_vs_persistence": float(country_mean_reg.max()),
        "max_country_year_regression_vs_persistence": float(
            pivot["reg_50_50_vs_persistence"].max()
        ),
        "country_year_win_fraction_vs_persistence": float(year_wins / n_year),
        "p90_yearly_wmape": {
            config: float(
                np.quantile(yearly[yearly["config"] == config]["wmape"], 0.90)
            )
            for config in COMPONENTS
        },
    }
    passes = {
        "c1_mean_improves_every_country": checks["mean_improves_every_country"],
        "c2_no_country_mean_regression_gt_1pct": bool(
            checks["max_country_mean_regression_vs_persistence"]
            <= TAIL_RISK["max_country_mean_regression_vs_persistence"]
        ),
        "c3_no_country_year_regression_gt_10pct": bool(
            checks["max_country_year_regression_vs_persistence"]
            <= TAIL_RISK["max_country_year_regression_vs_persistence"]
        ),
        "c4_country_year_wins_ge_50pct": bool(
            checks["country_year_win_fraction_vs_persistence"]
            >= TAIL_RISK["min_country_year_win_fraction_vs_persistence"]
        ),
    }
    tail_risk_pass = bool(all(passes.values()))
    decision = {
        "phase": "4J target-aware",
        "no_retraining": True,
        "protocol": "Path M — heterogeneous-target territorial transfer",
        "pre_specified_tail_risk": TAIL_RISK,
        "tail_risk_checks": checks,
        "tail_risk_pass_per_criterion": passes,
        "fixed_50_50_tail_risk_pass": tail_risk_pass,
        "promote_50_50": False,
        "decision": (
            "Fixed 50/50 fails the pre-specified worst-year tail-risk criterion. "
            "Keep as exploratory candidate; do not promote; do not search a new "
            "weight in this task."
            if not tail_risk_pass
            else "Fixed 50/50 passes the pre-specified tail-risk gate."
        ),
    }

    per_country.to_csv(root / "phase4j_target_aware_country.csv", index=False)
    wins.to_csv(root / "phase4j_target_aware_wins.csv", index=False)
    pooled.to_csv(root / "phase4j_target_aware_pooled.csv", index=False)
    (root / "phase4j_target_aware_decision.json").write_text(
        json.dumps(decision, indent=2), encoding="utf-8"
    )

    print("=== PER-COUNTRY (target-aware) ===")
    print(per_country.to_string(index=False, float_format=lambda v: f"{v:.6f}"))
    print("\n=== FIXED 50/50 WINS / WORST-YEAR ===")
    print(wins.to_string(index=False, float_format=lambda v: f"{v:.6f}"))
    print("\n=== POOLED (sensitivity only) ===")
    print(pooled.to_string(index=False, float_format=lambda v: f"{v:.6f}"))
    print("\n=== TAIL-RISK (pre-specified) ===")
    print(json.dumps(decision["tail_risk_checks"], indent=2))
    print(json.dumps(decision["tail_risk_pass_per_criterion"], indent=2))
    print("fixed_50_50_tail_risk_pass:", tail_risk_pass)
    print(
        "\nSEMANTIC WARNING: cross-country WMAPE compares heterogeneous "
        "administrative targets; not proof of one harmonized target."
    )


if __name__ == "__main__":
    main()
