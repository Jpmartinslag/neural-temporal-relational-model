#!/usr/bin/env python3
"""Phase 4J-B: stability and exploratory rolling conformal audit.

Intervals use only earlier outer-country forecast errors. Nonconformity scores
are normalized by side_lag_1, which is available at forecast time. Temporal and
spatial dependence invalidate a strong finite-sample coverage claim; outputs
are diagnostics only.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
CONFIGS = ("persistence", "ridge", "mean_50_50")
ALPHAS = (0.20, 0.10)


def wmape(frame: pd.DataFrame) -> float:
    denominator = float(frame["y_true"].abs().sum())
    if denominator <= 0:
        raise ValueError("Non-positive WMAPE denominator")
    return float((frame["y_true"] - frame["y_pred"]).abs().sum() / denominator)


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    if len(scores) == 0:
        raise ValueError("At least one calibration score is required")
    probability = min(1.0, math.ceil((len(scores) + 1) * (1.0 - alpha)) / len(scores))
    return float(np.quantile(scores, probability, method="higher"))


def stability_table(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    yearly_rows = []
    for (country, config, year), frame in predictions.groupby(
        ["country", "config", "target_year"]
    ):
        yearly_rows.append(
            {
                "country": country,
                "config": config,
                "target_year": int(year),
                "wmape": wmape(frame),
            }
        )
    yearly = pd.DataFrame(yearly_rows)
    pivot = yearly.pivot(
        index=["country", "target_year"],
        columns="config",
        values="wmape",
    ).reset_index()
    pivot["best_component"] = pivot[["persistence", "ridge"]].min(axis=1)
    pivot["delta_vs_persistence"] = pivot["mean_50_50"] - pivot["persistence"]
    pivot["delta_vs_ridge"] = pivot["mean_50_50"] - pivot["ridge"]
    pivot["delta_vs_best_component"] = (
        pivot["mean_50_50"] - pivot["best_component"]
    )
    summary = (
        pivot.groupby("country", as_index=False)
        .agg(
            years=("target_year", "size"),
            wins_vs_persistence=("delta_vs_persistence", lambda x: int((x <= 0).sum())),
            wins_vs_ridge=("delta_vs_ridge", lambda x: int((x <= 0).sum())),
            wins_vs_best_component=(
                "delta_vs_best_component",
                lambda x: int((x <= 0).sum()),
            ),
            mean_delta_vs_persistence=("delta_vs_persistence", "mean"),
            mean_delta_vs_best_component=("delta_vs_best_component", "mean"),
            worst_delta_vs_best_component=("delta_vs_best_component", "max"),
        )
    )
    return pivot, summary


def rolling_conformal(
    predictions: pd.DataFrame,
    panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lag = panel[
        ["country", "target_year", "ZE2020", "side_lag_1"]
    ].drop_duplicates()
    work = predictions.merge(
        lag,
        on=["country", "target_year", "ZE2020"],
        how="left",
        validate="many_to_one",
    )
    if work["side_lag_1"].isna().any():
        raise RuntimeError("Missing side_lag_1 after panel merge")
    work["scale"] = work["side_lag_1"].abs().clip(lower=1.0)
    work["score"] = (work["y_true"] - work["y_pred"]).abs() / work["scale"]

    interval_rows = []
    for (country, config), frame in work.groupby(["country", "config"]):
        frame = frame.sort_values(["target_year", "ZE2020"])
        for year in sorted(frame["target_year"].unique()):
            calibration = frame[frame["target_year"] < year]
            test = frame[frame["target_year"] == year]
            if calibration.empty:
                continue
            scores = calibration["score"].to_numpy(dtype=float)
            for alpha in ALPHAS:
                quantile = conformal_quantile(scores, alpha)
                half_width = quantile * test["scale"].to_numpy(dtype=float)
                lower = np.maximum(test["y_pred"].to_numpy(dtype=float) - half_width, 0.0)
                upper = test["y_pred"].to_numpy(dtype=float) + half_width
                truth = test["y_true"].to_numpy(dtype=float)
                covered = (truth >= lower) & (truth <= upper)
                for row, lo, hi, is_covered in zip(
                    test.itertuples(index=False),
                    lower,
                    upper,
                    covered,
                ):
                    interval_rows.append(
                        {
                            "country": country,
                            "config": config,
                            "target_year": int(year),
                            "ZE2020": int(row.ZE2020),
                            "alpha": alpha,
                            "nominal_coverage": 1.0 - alpha,
                            "calibration_rows": int(len(calibration)),
                            "quantile": quantile,
                            "y_true": float(row.y_true),
                            "y_pred": float(row.y_pred),
                            "lower": float(lo),
                            "upper": float(hi),
                            "covered": bool(is_covered),
                            "relative_width": float((hi - lo) / max(abs(row.side_lag_1), 1.0)),
                        }
                    )
    intervals = pd.DataFrame(interval_rows)
    summary = (
        intervals.groupby(
            ["country", "config", "alpha", "nominal_coverage"],
            as_index=False,
        )
        .agg(
            observed_coverage=("covered", "mean"),
            mean_relative_width=("relative_width", "mean"),
            evaluated_rows=("covered", "size"),
            evaluated_years=("target_year", "nunique"),
        )
    )
    return intervals, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase4j-root",
        type=Path,
        default=Path("hpc_results/herald_phase4j_a_20260609_local_r1"),
    )
    parser.add_argument(
        "--panel",
        type=Path,
        default=Path("data/processed/phase4g/joint/panel_ze2020.csv"),
    )
    args = parser.parse_args()
    root = (
        BASE / args.phase4j_root
        if not args.phase4j_root.is_absolute()
        else args.phase4j_root
    )
    panel_path = BASE / args.panel if not args.panel.is_absolute() else args.panel
    predictions = pd.read_csv(root / "phase4j_a_predictions.csv")
    predictions = predictions[predictions["config"].isin(CONFIGS)].copy()
    panel = pd.read_csv(panel_path)

    yearly, stability = stability_table(predictions)
    intervals, conformal = rolling_conformal(predictions, panel)
    yearly.to_csv(root / "phase4j_b_stability_yearly.csv", index=False)
    stability.to_csv(root / "phase4j_b_stability_country.csv", index=False)
    intervals.to_csv(root / "phase4j_b_conformal_intervals.csv", index=False)
    conformal.to_csv(root / "phase4j_b_conformal_summary.csv", index=False)

    fixed = conformal[conformal["config"] == "mean_50_50"]
    decision = {
        "phase": "4J-B",
        "status": "exploratory",
        "formal_coverage_claim": False,
        "fixed_mean_country_year_stability": stability.to_dict(orient="records"),
        "fixed_mean_conformal": fixed.to_dict(orient="records"),
        "decision": (
            "Use fixed 50/50 as a candidate only; do not promote until semantic "
            "target audit and explicit tail-risk criterion are complete."
        ),
    }
    (root / "phase4j_b_decision.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )
    print("=== STABILITY ===")
    print(stability.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("\n=== EXPLORATORY CONFORMAL: FIXED 50/50 ===")
    print(fixed.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("\nNo formal coverage claim.")


if __name__ == "__main__":
    main()
