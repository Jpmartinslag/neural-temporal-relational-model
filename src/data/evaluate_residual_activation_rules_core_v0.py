import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_local_candidate_features_v0 import wmape


ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "extended_panel_core_v0.csv"
TARGET_HISTORY_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
PREDICTIONS_PATH = ROOT / "data" / "processed" / "residual_baseline_predictions_core_v0.csv"
METRICS_PATH = ROOT / "reports" / "archive" / "diagnostics" / "residual_activation_rules_metrics_core_v0.json"
PREDICTIONS_OUT_PATH = ROOT / "data" / "processed" / "residual_activation_rules_predictions_core_v0.csv"
REPORT_PATH = ROOT / "reports" / "archive" / "diagnostics" / "RESIDUAL_ACTIVATION_RULES_CORE_V0.md"


STABLE_CONFIGS = [
    {
        "stable_model_id": "ridge_level_lag_only",
        "stable_lambda": 1.0,
        "stable_label": "ridge_level_lag_only",
    },
    {
        "stable_model_id": "persistence",
        "stable_lambda": 0.0,
        "stable_label": "persistence",
    },
]

RESIDUAL_CONFIGS = [
    {
        "residual_model_id": "huber_absolute_local_all",
        "residual_lambda": 0.5,
        "residual_label": "huber_absolute_local_all_no_rei_lambda_0_5",
    },
    {
        "residual_model_id": "huber_absolute_sitadel_energy",
        "residual_lambda": 0.5,
        "residual_label": "huber_absolute_sitadel_energy_lambda_0_5",
    },
    {
        "residual_model_id": "huber_absolute_sitadel_only",
        "residual_lambda": 0.5,
        "residual_label": "huber_absolute_sitadel_only_lambda_0_5",
    },
    {
        "residual_model_id": "huber_absolute_energy_only",
        "residual_lambda": 0.5,
        "residual_label": "huber_absolute_energy_only_lambda_0_5",
    },
]
FALLBACK_MODES = ["stable", "persistence"]
TEST_YEARS = [2021, 2022, 2023, 2024]


def load_base_predictions(stable_config, residual_config):
    predictions = pd.read_csv(PREDICTIONS_PATH, dtype={"ze2020": str})
    stable = predictions[
        (predictions["model_id"] == stable_config["stable_model_id"])
        & np.isclose(predictions["lambda"], stable_config["stable_lambda"])
    ][["test_year", "ze2020", "actual", "persistence", "prediction"]].rename(
        columns={"prediction": "stable_prediction"}
    )
    residual = predictions[
        (predictions["model_id"] == residual_config["residual_model_id"])
        & np.isclose(predictions["lambda"], residual_config["residual_lambda"])
    ][["test_year", "ze2020", "prediction"]].rename(
        columns={"prediction": "residual_prediction"}
    )
    merged = stable.merge(residual, on=["test_year", "ze2020"], how="inner")
    if merged.empty:
        raise RuntimeError("Missing stable or residual predictions. Run evaluate_residual_baselines_core_v0.py first.")
    merged["stable_label"] = stable_config["stable_label"]
    merged["residual_label"] = residual_config["residual_label"]
    return merged


def build_signals():
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    panel = panel[panel["year"].isin(TEST_YEARS)].rename(columns={"year": "test_year"})
    signals = panel[["test_year", "ze2020", "regime_signal_lag_1"]].copy()

    target = pd.read_csv(TARGET_HISTORY_PATH, dtype={"ze2020": str})
    target = target.rename(columns={"target_year": "year"})
    y_col = "side_establishment_creations_official"

    national = target.groupby("year")[y_col].sum().sort_index().reset_index()
    national["national_growth"] = national[y_col].pct_change()
    national["national_acceleration"] = national["national_growth"].diff()
    national["test_year"] = national["year"] + 1
    national = national[["test_year", "national_growth", "national_acceleration"]]
    signals = signals.merge(national, on="test_year", how="left")

    local = target[["ze2020", "year", y_col]].copy().sort_values(["ze2020", "year"])
    local["local_growth"] = local.groupby("ze2020")[y_col].pct_change()
    local["local_log"] = np.log1p(local[y_col].clip(lower=0))
    local["local_volatility_3y"] = (
        local.groupby("ze2020")["local_log"]
        .rolling(window=3, min_periods=3)
        .std()
        .reset_index(level=0, drop=True)
    )
    local["test_year"] = local["year"] + 1
    local = local[["test_year", "ze2020", "local_growth", "local_volatility_3y"]]
    signals = signals.merge(local, on=["test_year", "ze2020"], how="left")

    signals["abs_national_acceleration"] = signals["national_acceleration"].abs()
    return signals


def candidate_thresholds(values):
    clean = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return [np.inf]
    quantiles = clean.quantile([0.0, 0.25, 0.5, 0.75, 0.9]).tolist()
    thresholds = sorted({float(value) for value in quantiles})
    thresholds.append(np.inf)
    return thresholds


def apply_rule(frame, rule_name, threshold, fallback_mode="stable"):
    if rule_name == "national_acceleration_abs":
        signal = frame["abs_national_acceleration"]
        active = signal > threshold
    elif rule_name == "regime_signal_lag_1":
        signal = frame["regime_signal_lag_1"]
        active = signal > threshold
    elif rule_name == "local_volatility_3y":
        signal = frame["local_volatility_3y"]
        active = signal > threshold
    elif rule_name == "local_growth_abs":
        signal = frame["local_growth"].abs()
        active = signal > threshold
    else:
        raise ValueError(f"Unknown rule: {rule_name}")

    active = active.fillna(False).to_numpy()
    fallback_prediction_col = "persistence" if fallback_mode == "persistence" else "stable_prediction"
    pred = np.where(active, frame["residual_prediction"], frame[fallback_prediction_col])
    return pred, active


def score_rule(frame, rule_name, threshold, fallback_mode):
    pred, active = apply_rule(frame, rule_name, threshold, fallback_mode)
    return {
        "wmape": float(wmape(frame["actual"].to_numpy(), pred)),
        "activation_rate": float(active.mean()),
    }


def evaluate_prior_selected_rule(frame, rule_name, min_prior_years, fallback_mode):
    selected_rows = []
    prediction_rows = []

    for test_year in TEST_YEARS:
        prior_years = [year for year in TEST_YEARS if year < test_year]
        test = frame[frame["test_year"] == test_year].copy()
        if len(prior_years) < min_prior_years:
            threshold = np.inf
            reason = f"default_stable_until_{min_prior_years}_prior_years"
        else:
            prior = frame[frame["test_year"].isin(prior_years)].copy()
            if rule_name == "national_acceleration_abs":
                grid_values = prior["abs_national_acceleration"]
            elif rule_name == "regime_signal_lag_1":
                grid_values = prior["regime_signal_lag_1"]
            elif rule_name == "local_volatility_3y":
                grid_values = prior["local_volatility_3y"]
            elif rule_name == "local_growth_abs":
                grid_values = prior["local_growth"].abs()
            else:
                raise ValueError(rule_name)

            scores = []
            for threshold_candidate in candidate_thresholds(grid_values):
                item = score_rule(prior, rule_name, threshold_candidate, fallback_mode)
                item["threshold"] = threshold_candidate
                scores.append(item)
            best = sorted(scores, key=lambda item: (item["wmape"], -item["activation_rate"]))[0]
            threshold = best["threshold"]
            reason = "best_prior_wmape"

        pred, active = apply_rule(test, rule_name, threshold, fallback_mode)
        year_score = float(wmape(test["actual"].to_numpy(), pred))
        selected_rows.append(
            {
                "stable_label": str(test["stable_label"].iloc[0]),
                "residual_label": str(test["residual_label"].iloc[0]),
                "fallback_label": fallback_mode,
                "rule_name": rule_name,
                "min_prior_years": int(min_prior_years),
                "test_year": int(test_year),
                "threshold": None if np.isinf(threshold) else float(threshold),
                "activation_rate": float(active.mean()),
                "wmape": year_score,
                "reason": reason,
            }
        )
        for ze2020, actual, stable, persistence, residual, prediction, activated in zip(
            test["ze2020"],
            test["actual"],
            test["stable_prediction"],
            test["persistence"],
            test["residual_prediction"],
            pred,
            active,
        ):
            prediction_rows.append(
                {
                    "rule_name": rule_name,
                    "stable_label": str(test["stable_label"].iloc[0]),
                    "residual_label": str(test["residual_label"].iloc[0]),
                    "fallback_label": fallback_mode,
                    "min_prior_years": int(min_prior_years),
                    "test_year": int(test_year),
                    "ze2020": ze2020,
                    "threshold": None if np.isinf(threshold) else float(threshold),
                    "activated_residual": bool(activated),
                    "actual": float(actual),
                    "stable_prediction": float(stable),
                    "persistence_prediction": float(persistence),
                    "residual_prediction": float(residual),
                    "prediction": float(prediction),
                }
            )

    return selected_rows, prediction_rows


def baseline_rows(frame):
    rows = []
    for (stable_label, residual_label, test_year), group in frame.groupby(
        ["stable_label", "residual_label", "test_year"]
    ):
        rows.append(
            {
                "stable_label": str(stable_label),
                "residual_label": str(residual_label),
                "test_year": int(test_year),
                "persistence_wmape": float(wmape(group["actual"], group["persistence"])),
                "stable_wmape": float(wmape(group["actual"], group["stable_prediction"])),
                "residual_wmape": float(wmape(group["actual"], group["residual_prediction"])),
            }
        )
    return rows


def summarize_results(rows):
    frame = pd.DataFrame(rows)
    summary = (
        frame.groupby(["stable_label", "residual_label", "fallback_label", "rule_name", "min_prior_years"])
        .agg(
            mean_wmape=("wmape", "mean"),
            max_wmape=("wmape", "max"),
            mean_activation_rate=("activation_rate", "mean"),
        )
        .reset_index()
        .sort_values(["mean_wmape", "max_wmape"])
    )
    return summary.to_dict(orient="records")


def write_report(output):
    best_summary = output["summary"][:12]
    best_rule = output["summary"][0]
    best_rule_rows = [
        row
        for row in output["all_runs"]
        if row["stable_label"] == best_rule["stable_label"]
        and row["residual_label"] == best_rule["residual_label"]
        and row["fallback_label"] == best_rule["fallback_label"]
        and row["rule_name"] == best_rule["rule_name"]
        and row["min_prior_years"] == best_rule["min_prior_years"]
    ]
    baseline_focus = [
        row
        for row in output["baselines_by_year"]
        if row["stable_label"] == "ridge_level_lag_only"
        and row["residual_label"] == "huber_absolute_local_all_no_rei_lambda_0_5"
    ]
    lines = [
        "# Residual Activation Rules Core v0",
        "",
        "Data: 2026-04-17",
        "",
        "## Objective",
        "",
        "Test leakage-safe rules that activate the residual model only when a pre-test signal suggests shock/acceleration.",
        "",
        "Stable models tested: `ridge_level_lag_only` and `persistence`.",
        "",
        "Residual models tested: `HuberRegressor`, absolute residual, `lambda=0.5`, with REI excluded until publication-lag and vintage risks are resolved.",
        "",
        "## Baselines By Year: No-REI Local Residual With Ridge Stable Side",
        "",
        "| Year | Persistence | Stable Ridge | Fixed Residual |",
        "| :---: | ---: | ---: | ---: |",
    ]
    for row in baseline_focus:
        lines.append(
            f"| {row['test_year']} | {row['persistence_wmape']:.3f} | "
            f"{row['stable_wmape']:.3f} | {row['residual_wmape']:.3f} |"
        )

    lines.extend([
        "",
        "## Activation Rule Summary",
        "",
        "| Stable | Residual | Fallback | Rule | Min prior years | Mean WMAPE | Max WMAPE | Mean activation |",
        "| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: |",
    ])
    for row in best_summary:
        lines.append(
            f"| {row['stable_label']} | {row['residual_label']} | "
            f"{row['fallback_label']} | "
            f"{row['rule_name']} | {row['min_prior_years']} | "
            f"{row['mean_wmape']:.3f} | {row['max_wmape']:.3f} | "
            f"{row['mean_activation_rate']:.3f} |"
        )

    lines.extend([
        "",
        "## Best Rule Threshold Trace",
        "",
        "This table is mandatory for auditing whether the activation rule is learning a stable decision boundary or memorizing an early shock.",
        "",
        "| Year | Threshold | Activation rate | WMAPE | Selection reason |",
        "| :---: | ---: | ---: | ---: | :--- |",
    ])
    for row in best_rule_rows:
        threshold = "NA" if row["threshold"] is None else f"{row['threshold']:.6f}"
        lines.append(
            f"| {row['test_year']} | {threshold} | {row['activation_rate']:.3f} | "
            f"{row['wmape']:.3f} | {row['reason']} |"
        )

    lines.extend([
        "",
        "## Fallback Check",
        "",
        "- `persistence` fallback was tested as a safer early-year default.",
        "- It improves the intuition for stable years like 2022, but it collapses on 2021 because persistence misses the post-COVID rebound.",
        "- Therefore, persistence fallback does not replace the current best experimental rule.",
        "- `min_prior_years=1` remains numerically best but threshold-fragile; `min_prior_years=2` remains more cautious but still unstable.",
        "- A rule whose threshold remains fixed after one shock year must be treated as a stress-test diagnostic, not as a deployable selector.",
        "",
        "## Decision",
        "",
        "- Activation rules are experimental.",
        "- The rule must beat `ridge_lag_only` and avoid unstable threshold overfitting.",
        "- The best no-REI rule is downgraded to a stress-test diagnostic, not an operational benchmark.",
        "- REI-backed residuals are excluded from candidate activation rules until the REI timing/vintage audit is resolved.",
        "- `STGNN` remains postponed.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def evaluate_activation_rules():
    signals = build_signals()
    all_rows = []
    all_predictions = []
    baseline_frame_parts = []
    for stable_config in STABLE_CONFIGS:
        for residual_config in RESIDUAL_CONFIGS:
            frame = load_base_predictions(stable_config, residual_config).merge(
                signals,
                on=["test_year", "ze2020"],
                how="left",
            )
            baseline_frame_parts.append(frame)
            for rule_name in [
                "national_acceleration_abs",
                "regime_signal_lag_1",
                "local_volatility_3y",
                "local_growth_abs",
            ]:
                for min_prior_years in [1, 2]:
                    for fallback_mode in FALLBACK_MODES:
                        rows, preds = evaluate_prior_selected_rule(
                            frame,
                            rule_name,
                            min_prior_years,
                            fallback_mode,
                        )
                        all_rows.extend(rows)
                        all_predictions.extend(preds)

    baseline_frame = pd.concat(baseline_frame_parts, ignore_index=True)

    output = {
        "baselines_by_year": baseline_rows(baseline_frame),
        "summary": summarize_results(all_rows),
        "all_runs": all_rows,
        "methodology": (
            "For each test year, choose an activation threshold using prior test years only. "
            "If prior years are insufficient, evaluate both configured stable-side and persistence fallbacks. "
            "Residual side variants are fixed Huber absolute models with lambda=0.5."
        ),
    }

    os.makedirs(METRICS_PATH.parent, exist_ok=True)
    os.makedirs(PREDICTIONS_OUT_PATH.parent, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(output, indent=2))
    pd.DataFrame(all_predictions).to_csv(PREDICTIONS_OUT_PATH, index=False)
    write_report(output)

    print(json.dumps({
        "baselines_by_year": output["baselines_by_year"],
        "summary": output["summary"],
    }, indent=2))
    print(f"Saved activation metrics to {METRICS_PATH}")
    print(f"Saved activation predictions to {PREDICTIONS_OUT_PATH}")
    print(f"Saved activation report to {REPORT_PATH}")


if __name__ == "__main__":
    evaluate_activation_rules()
