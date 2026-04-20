import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_local_candidate_features_v0 import wmape


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_PATH = ROOT / "data" / "processed" / "residual_baseline_predictions_core_v0.csv"
METRICS_PATH = ROOT / "reports" / "residual_baseline_metrics_core_v0.json"
TARGET_HISTORY_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
ZONE_DIAGNOSTICS_PATH = ROOT / "data" / "processed" / "residual_baseline_zone_diagnostics_core_v0.csv"
QUALITY_PATH = ROOT / "reports" / "residual_baseline_diagnostics_core_v0.json"
REPORT_PATH = ROOT / "reports" / "RESIDUAL_BASELINE_DIAGNOSTICS_CORE_V0.md"


BEST_FIXED_LAMBDA = 0.5
ABLATION_MODEL_IDS = [
    "huber_absolute_local_all",
    "huber_absolute_sitadel_only",
    "huber_absolute_energy_only",
    "huber_absolute_sitadel_energy",
    "huber_absolute_lag_only",
]


def load_selected_predictions():
    predictions = pd.read_csv(PREDICTIONS_PATH, dtype={"ze2020": str})
    metrics = json.loads(METRICS_PATH.read_text())
    best = metrics["best_by_mean"][0]
    best_model_id = f"{best['model']}_{best['residual_target']}_{best['feature_group']}"
    best_lambda = float(best["lambda"])
    best_strategy = (
        f"fixed_{best_model_id}_lambda_{str(best_lambda).replace('.', '_')}"
    )

    ablation_parts = []
    for model_id in sorted(set(ABLATION_MODEL_IDS + [best_model_id])):
        part = predictions[
            (predictions["model_id"] == model_id)
            & np.isclose(
                predictions["lambda"],
                best_lambda if model_id == best_model_id else BEST_FIXED_LAMBDA,
            )
        ].copy()
        if part.empty:
            continue
        if model_id == best_model_id:
            part["selected_strategy"] = best_strategy
        else:
            part["selected_strategy"] = f"fixed_{model_id}_lambda_0_5"
        ablation_parts.append(part)
    fixed = pd.concat(ablation_parts, ignore_index=True)

    conservative_parts = []
    for selected in metrics["conservative_prior_selection"]["selected_runs"]:
        year = selected["test_year"]
        model = selected["selected_model"]
        residual = selected["selected_residual_target"]
        group = selected["selected_feature_group"]
        shrinkage = selected["selected_lambda"]
        if model == "ridge_level":
            model_id = "ridge_level_lag_only"
        elif model == "persistence":
            model_id = "persistence"
        else:
            model_id = f"{model}_{residual}_{group}"

        part = predictions[
            (predictions["test_year"] == year)
            & (predictions["model_id"] == model_id)
            & np.isclose(predictions["lambda"], shrinkage)
        ].copy()
        if part.empty:
            raise RuntimeError(f"Missing conservative predictions for {selected}")
        part["selected_strategy"] = "conservative_prior_selector"
        conservative_parts.append(part)

    conservative = pd.concat(conservative_parts, ignore_index=True)
    output = pd.concat([fixed, conservative], ignore_index=True)
    output.attrs["best_strategy"] = best_strategy
    output.attrs["best_description"] = (
        f"{best['model']} {best['residual_target']} / {best['feature_group']} / "
        f"lambda={best_lambda}"
    )
    return output


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
    zone_stats["volatility_group"] = pd.qcut(
        zone_stats["pretest_target_cv"].rank(method="first"),
        q=3,
        labels=["low_volatility", "medium_volatility", "high_volatility"],
    ).astype(str)
    return zone_stats


def add_error_columns(frame):
    frame = frame.copy()
    frame["persistence_abs_error"] = (frame["actual"] - frame["persistence"]).abs()
    frame["model_abs_error"] = (frame["actual"] - frame["prediction"]).abs()
    frame["abs_error_reduction_vs_persistence"] = (
        frame["persistence_abs_error"] - frame["model_abs_error"]
    )
    return frame


def group_wmape(frame, group_cols):
    rows = []
    for keys, group in frame.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        item = dict(zip(group_cols, keys))
        item["actual_sum"] = float(group["actual"].sum())
        item["persistence_wmape"] = float(wmape(group["actual"], group["persistence"]))
        item["model_wmape"] = float(wmape(group["actual"], group["prediction"]))
        item["wmape_delta_vs_persistence"] = item["persistence_wmape"] - item["model_wmape"]
        item["abs_error_reduction_sum"] = float(group["abs_error_reduction_vs_persistence"].sum())
        item["rows"] = int(len(group))
        rows.append(item)
    return rows


def top_zone_changes(frame, n=20):
    zone = (
        frame.groupby(["selected_strategy", "ze2020", "libze2020"])
        .agg(
            actual_sum=("actual", "sum"),
            persistence_abs_error=("persistence_abs_error", "sum"),
            model_abs_error=("model_abs_error", "sum"),
            abs_error_reduction_vs_persistence=("abs_error_reduction_vs_persistence", "sum"),
        )
        .reset_index()
    )
    zone["persistence_wmape"] = zone["persistence_abs_error"] / zone["actual_sum"] * 100
    zone["model_wmape"] = zone["model_abs_error"] / zone["actual_sum"] * 100
    zone["wmape_delta_vs_persistence"] = zone["persistence_wmape"] - zone["model_wmape"]
    best = (
        zone.sort_values("abs_error_reduction_vs_persistence", ascending=False)
        .groupby("selected_strategy")
        .head(n)
        .to_dict(orient="records")
    )
    worst = (
        zone.sort_values("abs_error_reduction_vs_persistence", ascending=True)
        .groupby("selected_strategy")
        .head(n)
        .to_dict(orient="records")
    )
    return zone, best, worst


def format_table(rows, columns):
    out = []
    out.append("| " + " | ".join(columns) + " |")
    out.append("| " + " | ".join([":---"] * len(columns)) + " |")
    for row in rows:
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value))
        out.append("| " + " | ".join(values) + " |")
    return "\n".join(out)


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_report(summary):
    best_strategy = summary["best_strategy"]
    best_description = summary["best_description"]
    fixed_years = [
        row for row in summary["by_year"]
        if row["selected_strategy"] == best_strategy
    ]
    conservative_years = [
        row for row in summary["by_year"]
        if row["selected_strategy"] == "conservative_prior_selector"
    ]
    fixed_volume = [
        row for row in summary["by_volume"]
        if row["selected_strategy"] == best_strategy
    ]
    fixed_volatility = [
        row for row in summary["by_volatility"]
        if row["selected_strategy"] == best_strategy
    ]
    fixed_top = [
        row for row in summary["top_zone_improvements"]
        if row["selected_strategy"] == best_strategy
    ]
    zone_count = summary["zone_counts_by_strategy"][best_strategy]
    total_reduction = sum(
        row["abs_error_reduction_sum"]
        for row in fixed_years
    )
    top_1_share = fixed_top[0]["abs_error_reduction_vs_persistence"] / total_reduction * 100
    top_10_share = (
        sum(row["abs_error_reduction_vs_persistence"] for row in fixed_top[:10])
        / total_reduction
        * 100
    )

    report = f"""# Residual Baseline Diagnostics Core v0

Data: 2026-04-17

## Objective

Audit whether the residual improvement is broad or concentrated in a few high-volume or high-volatility `ZE2020` zones.

Strategies audited:

- Best fixed no-REI residual after audit: `{best_description}`.
- Conservative selector: `ridge_level` until two prior test years exist, then prior-best residual model.

## Per-Year Behavior

Best fixed no-REI residual:

{format_table(fixed_years, ["test_year", "persistence_wmape", "model_wmape", "wmape_delta_vs_persistence", "abs_error_reduction_sum"])}

Conservative selector:

{format_table(conservative_years, ["test_year", "persistence_wmape", "model_wmape", "wmape_delta_vs_persistence", "abs_error_reduction_sum"])}

## Volume Stratification

Best fixed no-REI residual:

{format_table(fixed_volume, ["volume_group", "persistence_wmape", "model_wmape", "wmape_delta_vs_persistence", "actual_sum"])}

## Volatility Stratification

Best fixed no-REI residual:

{format_table(fixed_volatility, ["volatility_group", "persistence_wmape", "model_wmape", "wmape_delta_vs_persistence", "actual_sum"])}

## Interpretation

- The fixed residual model improves `2021` and `2024` versus persistence, but worsens `2022` and `2023`.
- The average gain is driven by large improvements in shock/rebound years, especially `2021` and `2024`.
- The fixed residual model improves all volume groups, including the top 10% by pre-test volume.
- The fixed residual model improves all volatility groups, with strongest relative value in high-volatility zones.
- The gain improves `{zone_count["improved_zones"]}` zones and worsens `{zone_count["worsened_zones"]}`, but is concentrated in magnitude: Paris alone contributes `{top_1_share:.1f}%` of total absolute-error reduction, and the top 10 improving zones contribute `{top_10_share:.1f}%`.
- The conservative selector still suffers in `2022` because it defaults to `ridge_level` before enough prior test years exist.
- Region-level clustering is not audited here because region metadata is not included in the prediction artifact.

## Decision

REI-backed residuals are excluded here. The best remaining fixed residual is weaker and remains exploratory.

The conservative selector is the more defensible operational protocol, but it still needs more test years or a stronger prior selection rule.

Next step:

- Inspect top improving and worsening zones manually.
- Keep REI banned from candidate baselines until timing/vintage and aggregation issues are resolved.
- Keep `STGNN` postponed.
"""
    REPORT_PATH.write_text(report)


def diagnose_residual_baseline():
    selected = load_selected_predictions()
    best_strategy = selected.attrs["best_strategy"]
    best_description = selected.attrs["best_description"]
    zone_groups = build_zone_groups()
    selected = selected.merge(zone_groups, on="ze2020", how="left")
    selected = add_error_columns(selected)

    zone_summary, top_improvements, top_worsening = top_zone_changes(selected)
    zone_summary.to_csv(ZONE_DIAGNOSTICS_PATH, index=False)
    zone_counts = {}
    for strategy, group in zone_summary.groupby("selected_strategy"):
        zone_counts[strategy] = {
            "improved_zones": int((group["abs_error_reduction_vs_persistence"] > 0).sum()),
            "worsened_zones": int((group["abs_error_reduction_vs_persistence"] < 0).sum()),
            "unchanged_zones": int((group["abs_error_reduction_vs_persistence"] == 0).sum()),
        }

    summary = {
        "best_strategy": best_strategy,
        "best_description": best_description,
        "zone_counts_by_strategy": zone_counts,
        "by_year": group_wmape(selected, ["selected_strategy", "test_year"]),
        "by_volume": group_wmape(selected, ["selected_strategy", "volume_group"]),
        "by_volatility": group_wmape(selected, ["selected_strategy", "volatility_group"]),
        "top_zone_improvements": top_improvements,
        "top_zone_worsening": top_worsening,
        "methodology": (
            "Volume and volatility groups are defined using target history up to 2020 only. "
            "Diagnostics compare model absolute error against persistence absolute error."
        ),
    }

    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    os.makedirs(ZONE_DIAGNOSTICS_PATH.parent, exist_ok=True)
    QUALITY_PATH.write_text(json.dumps(summary, indent=2, default=json_default))
    write_report(summary)

    print(json.dumps({
        "by_year": summary["by_year"],
        "by_volume": summary["by_volume"],
        "by_volatility": summary["by_volatility"],
    }, indent=2, default=json_default))
    print(f"Saved zone diagnostics to {ZONE_DIAGNOSTICS_PATH}")
    print(f"Saved diagnostic summary to {QUALITY_PATH}")
    print(f"Saved diagnostic report to {REPORT_PATH}")


if __name__ == "__main__":
    diagnose_residual_baseline()
