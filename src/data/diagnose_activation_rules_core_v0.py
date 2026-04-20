import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_local_candidate_features_v0 import wmape
from evaluate_residual_activation_rules_core_v0 import (
    TEST_YEARS,
    apply_rule,
    build_signals,
    candidate_thresholds,
    load_base_predictions,
    score_rule,
)


ROOT = Path(__file__).resolve().parents[2]
ACTIVATION_METRICS_PATH = ROOT / "reports" / "residual_activation_rules_metrics_core_v0.json"
ACTIVATION_PREDICTIONS_PATH = ROOT / "data" / "processed" / "residual_activation_rules_predictions_core_v0.csv"
TARGET_HISTORY_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
QUALITY_PATH = ROOT / "reports" / "activation_rule_diagnostics_core_v0.json"
REPORT_PATH = ROOT / "reports" / "ACTIVATION_RULE_DIAGNOSTICS_CORE_V0.md"


def load_best_rule():
    metrics = json.loads(ACTIVATION_METRICS_PATH.read_text())
    if not metrics.get("summary"):
        raise RuntimeError("No activation rule summary found. Run evaluate_residual_activation_rules_core_v0.py first.")
    best = metrics["summary"][0]
    all_runs = [
        row
        for row in metrics["all_runs"]
        if row["stable_label"] == best["stable_label"]
        and row["residual_label"] == best["residual_label"]
        and row["fallback_label"] == best["fallback_label"]
        and row["rule_name"] == best["rule_name"]
        and row["min_prior_years"] == best["min_prior_years"]
    ]
    return best, all_runs


def load_best_predictions(best):
    predictions = pd.read_csv(ACTIVATION_PREDICTIONS_PATH, dtype={"ze2020": str})
    selected = predictions[
        (predictions["stable_label"] == best["stable_label"])
        & (predictions["residual_label"] == best["residual_label"])
        & (predictions["fallback_label"] == best["fallback_label"])
        & (predictions["rule_name"] == best["rule_name"])
        & (predictions["min_prior_years"] == best["min_prior_years"])
    ].copy()
    if selected.empty:
        raise RuntimeError("Best activation rule predictions not found. Regenerate activation predictions first.")
    return selected


def build_zone_groups():
    target = pd.read_csv(TARGET_HISTORY_PATH, dtype={"ze2020": str})
    target = target.rename(columns={"target_year": "year"})
    history = target[target["year"] <= 2020].copy()
    zone_stats = (
        history.groupby(["ze2020", "libze2020"])["side_establishment_creations_official"]
        .agg(["mean", "std"])
        .reset_index()
        .rename(columns={"mean": "pretest_target_mean", "std": "pretest_target_std"})
    )
    zone_stats["pretest_target_cv"] = (
        zone_stats["pretest_target_std"] / zone_stats["pretest_target_mean"].replace(0, np.nan)
    )
    volume_rank = zone_stats["pretest_target_mean"].rank(pct=True, method="first")
    zone_stats["volume_group"] = np.select(
        [volume_rank > 0.90, volume_rank > 0.50],
        ["top_10pct", "middle_40pct"],
        default="bottom_50pct",
    )
    return zone_stats


def add_error_columns(frame):
    frame = frame.copy()
    frame["rule_abs_error"] = (frame["actual"] - frame["prediction"]).abs()
    frame["persistence_abs_error"] = (frame["actual"] - frame["persistence_prediction"]).abs()
    frame["stable_abs_error"] = (frame["actual"] - frame["stable_prediction"]).abs()
    frame["aer_vs_persistence"] = frame["persistence_abs_error"] - frame["rule_abs_error"]
    frame["aer_vs_stable"] = frame["stable_abs_error"] - frame["rule_abs_error"]
    frame["improved_vs_persistence"] = frame["aer_vs_persistence"] > 0
    frame["worsened_vs_persistence"] = frame["aer_vs_persistence"] < 0
    frame["improved_vs_stable"] = frame["aer_vs_stable"] > 0
    frame["worsened_vs_stable"] = frame["aer_vs_stable"] < 0
    return frame


def aggregate_metrics(frame, group_cols):
    rows = []
    for keys, group in frame.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        item = dict(zip(group_cols, keys))
        item["rows"] = int(len(group))
        item["zones"] = int(group["ze2020"].nunique())
        item["actual_sum"] = float(group["actual"].sum())
        item["rule_wmape"] = float(wmape(group["actual"], group["prediction"]))
        item["persistence_wmape"] = float(wmape(group["actual"], group["persistence_prediction"]))
        item["stable_wmape"] = float(wmape(group["actual"], group["stable_prediction"]))
        item["wmape_delta_vs_persistence"] = item["persistence_wmape"] - item["rule_wmape"]
        item["wmape_delta_vs_stable"] = item["stable_wmape"] - item["rule_wmape"]
        item["aer_vs_persistence"] = float(group["aer_vs_persistence"].sum())
        item["aer_vs_stable"] = float(group["aer_vs_stable"].sum())
        item["improved_zones_vs_persistence"] = int(
            (group.groupby("ze2020")["aer_vs_persistence"].sum() > 0).sum()
        )
        item["worsened_zones_vs_persistence"] = int(
            (group.groupby("ze2020")["aer_vs_persistence"].sum() < 0).sum()
        )
        item["improved_zones_vs_stable"] = int(
            (group.groupby("ze2020")["aer_vs_stable"].sum() > 0).sum()
        )
        item["worsened_zones_vs_stable"] = int(
            (group.groupby("ze2020")["aer_vs_stable"].sum() < 0).sum()
        )
        rows.append(item)
    return rows


def concentration_metrics(frame):
    zone = (
        frame.groupby(["ze2020", "libze2020"])
        .agg(
            actual_sum=("actual", "sum"),
            aer_vs_persistence=("aer_vs_persistence", "sum"),
            aer_vs_stable=("aer_vs_stable", "sum"),
            rule_abs_error=("rule_abs_error", "sum"),
            persistence_abs_error=("persistence_abs_error", "sum"),
            stable_abs_error=("stable_abs_error", "sum"),
        )
        .reset_index()
    )
    positive = zone[zone["aer_vs_persistence"] > 0].copy()
    total_positive = float(positive["aer_vs_persistence"].sum())
    if total_positive > 0:
        positive = positive.sort_values("aer_vs_persistence", ascending=False)
        top_1_share = float(positive.head(1)["aer_vs_persistence"].sum() / total_positive * 100)
        top_10_share = float(positive.head(10)["aer_vs_persistence"].sum() / total_positive * 100)
    else:
        top_1_share = 0.0
        top_10_share = 0.0

    return {
        "zone_rows": zone.to_dict(orient="records"),
        "top_improvements_vs_persistence": zone.sort_values(
            "aer_vs_persistence", ascending=False
        ).head(20).to_dict(orient="records"),
        "top_degradations_vs_persistence": zone.sort_values(
            "aer_vs_persistence", ascending=True
        ).head(20).to_dict(orient="records"),
        "positive_aer_top_1_share_pct": top_1_share,
        "positive_aer_top_10_share_pct": top_10_share,
    }


def loyo_threshold_audit(best):
    stable_config = {
        "stable_model_id": "ridge_level_lag_only"
        if best["stable_label"] == "ridge_level_lag_only"
        else "persistence",
        "stable_lambda": 1.0 if best["stable_label"] == "ridge_level_lag_only" else 0.0,
        "stable_label": best["stable_label"],
    }
    residual_model_id = best["residual_label"].replace("_lambda_0_5", "")
    residual_config = {
        "residual_model_id": residual_model_id,
        "residual_lambda": 0.5,
        "residual_label": best["residual_label"],
    }
    frame = load_base_predictions(stable_config, residual_config).merge(
        build_signals(),
        on=["test_year", "ze2020"],
        how="left",
    )

    rows = []
    for heldout_year in TEST_YEARS:
        train = frame[frame["test_year"] != heldout_year].copy()
        test = frame[frame["test_year"] == heldout_year].copy()
        if best["rule_name"] == "national_acceleration_abs":
            grid_values = train["abs_national_acceleration"]
        elif best["rule_name"] == "regime_signal_lag_1":
            grid_values = train["regime_signal_lag_1"]
        elif best["rule_name"] == "local_volatility_3y":
            grid_values = train["local_volatility_3y"]
        elif best["rule_name"] == "local_growth_abs":
            grid_values = train["local_growth"].abs()
        else:
            raise ValueError(best["rule_name"])

        scores = []
        for threshold in candidate_thresholds(grid_values):
            item = score_rule(train, best["rule_name"], threshold, best["fallback_label"])
            item["threshold"] = threshold
            scores.append(item)
        selected = sorted(scores, key=lambda item: (item["wmape"], -item["activation_rate"]))[0]
        pred, active = apply_rule(
            test,
            best["rule_name"],
            selected["threshold"],
            best["fallback_label"],
        )
        rows.append(
            {
                "heldout_year": int(heldout_year),
                "selected_threshold": None
                if np.isinf(selected["threshold"])
                else float(selected["threshold"]),
                "train_wmape": float(selected["wmape"]),
                "heldout_wmape": float(wmape(test["actual"], pred)),
                "heldout_activation_rate": float(active.mean()),
            }
        )
    thresholds = [
        row["selected_threshold"]
        for row in rows
        if row["selected_threshold"] is not None
    ]
    return {
        "rows": rows,
        "threshold_min": float(min(thresholds)) if thresholds else None,
        "threshold_max": float(max(thresholds)) if thresholds else None,
        "threshold_range": float(max(thresholds) - min(thresholds)) if thresholds else None,
    }


def format_table(rows, columns):
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join([":---"] * len(columns)) + " |")
    for row in rows:
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                value = f"{value:.3f}"
            if value is None:
                value = "NA"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_report(output):
    best = output["best_rule"]
    report = f"""# Activation Rule Diagnostics Core v0

Data: 2026-04-20

## Objective

Audit the current best no-REI activation rule as a diagnostic artifact, not as an operational baseline.

Best rule audited:

- Stable side: `{best['stable_label']}`
- Residual side: `{best['residual_label']}`
- Fallback: `{best['fallback_label']}`
- Rule: `{best['rule_name']}`
- Min prior years: `{best['min_prior_years']}`

## Per-Year Threshold Trace

{format_table(output["best_rule_year_trace"], ["test_year", "threshold", "activation_rate", "wmape", "reason"])}

## Leave-One-Year-Out Threshold Audit

{format_table(output["loyo"]["rows"], ["heldout_year", "selected_threshold", "train_wmape", "heldout_wmape", "heldout_activation_rate"])}

Threshold range: `{output["loyo"]["threshold_range"]}`.

## Volume Stratification

{format_table(output["by_volume"], ["volume_group", "rule_wmape", "persistence_wmape", "stable_wmape", "aer_vs_persistence", "aer_vs_stable", "improved_zones_vs_persistence", "worsened_zones_vs_persistence"])}

## Per-Year Comparison

{format_table(output["by_year"], ["test_year", "rule_wmape", "persistence_wmape", "stable_wmape", "aer_vs_persistence", "aer_vs_stable"])}

## Concentration Risk

- Positive AER top-1 share vs persistence: `{output["concentration"]["positive_aer_top_1_share_pct"]:.3f}%`
- Positive AER top-10 share vs persistence: `{output["concentration"]["positive_aer_top_10_share_pct"]:.3f}%`

## Decision

- This diagnostic must compare against both persistence and the stable side.
- A future activation rule must show positive AER vs persistence in at least two volume groups.
- A future activation rule must keep Paris/top-zone concentration below the project threshold.
- A future activation rule must have a stable LOYO threshold trace.
- The current `5.49%` activation result remains downgraded to stress-test diagnostic until these criteria are met.
"""
    REPORT_PATH.write_text(report)


def diagnose_activation_rule():
    best, best_rows = load_best_rule()
    predictions = load_best_predictions(best)
    zone_groups = build_zone_groups()
    frame = predictions.merge(zone_groups, on="ze2020", how="left")
    if frame["volume_group"].isna().any():
        missing = int(frame["volume_group"].isna().sum())
        raise RuntimeError(f"Missing zone group metadata for {missing} prediction rows.")
    frame = add_error_columns(frame)

    concentration = concentration_metrics(frame)
    output = {
        "best_rule": best,
        "best_rule_year_trace": best_rows,
        "loyo": loyo_threshold_audit(best),
        "by_year": aggregate_metrics(frame, ["test_year"]),
        "by_volume": aggregate_metrics(frame, ["volume_group"]),
        "by_year_volume": aggregate_metrics(frame, ["test_year", "volume_group"]),
        "concentration": concentration,
        "methodological_status": (
            "diagnostic_only; audits existing no-REI activation predictions; "
            "does not train or select a new model"
        ),
    }

    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    QUALITY_PATH.write_text(json.dumps(output, indent=2, default=json_default))
    write_report(output)
    print(json.dumps({
        "best_rule": output["best_rule"],
        "loyo": output["loyo"],
        "by_volume": output["by_volume"],
        "concentration": {
            "positive_aer_top_1_share_pct": concentration["positive_aer_top_1_share_pct"],
            "positive_aer_top_10_share_pct": concentration["positive_aer_top_10_share_pct"],
        },
    }, indent=2, default=json_default))
    print(f"Saved activation diagnostics to {QUALITY_PATH}")
    print(f"Saved activation diagnostic report to {REPORT_PATH}")


if __name__ == "__main__":
    diagnose_activation_rule()
