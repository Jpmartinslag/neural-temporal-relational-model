from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

PRED_PATH = ROOT / "data" / "processed" / "segmented_decision_rule_backtest_predictions_core_v0.csv"
METRICS_PATH = ROOT / "metadata" / "segmented_decision_rule_backtest_metrics_core_v0.csv"

FOLD_DIAG_OUT = ROOT / "metadata" / "side_backtest_fold_instability_core_v0.csv"
GROUP_DIAG_OUT = ROOT / "metadata" / "side_backtest_group_instability_core_v0.csv"
WORST_ZONE_OUT = ROOT / "metadata" / "side_backtest_worst_zones_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "side_backtest_instability_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md"

MODEL_COLUMNS = {
    "persistence": "pred_persistence",
    "ridge_autoregressive": "pred_ridge_autoregressive_fold",
    "segmented_size_volatility": "pred_segmented_size_volatility_group",
    "spatial_blend": "pred_spatial_blend_fold",
}


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def fold_diagnostics(preds: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = preds[preds["fold_role"] == "test"].copy()
    test_metrics = metrics[metrics["target_role"] == "test"].copy()
    for fold_year, frame in test.groupby("fold_validation_year"):
        target_year = int(frame["target_year"].iloc[0])
        total_y = float(frame["y_true"].sum())
        total_lag = float(frame["y_lag_0"].sum())
        aggregate_growth = (total_y - total_lag) / total_lag if total_lag else float("nan")
        fold_metrics = test_metrics[test_metrics["fold_validation_year"] == fold_year].copy()
        metric_lookup = dict(zip(fold_metrics["model"], fold_metrics["wmape"]))
        best = fold_metrics.sort_values(["wmape", "model"]).iloc[0]
        rows.append(
            {
                "fold_validation_year": int(fold_year),
                "test_target_year": target_year,
                "aggregate_y_true": total_y,
                "aggregate_y_lag_0": total_lag,
                "aggregate_growth_vs_lag_0": aggregate_growth,
                "best_test_model": str(best["model"]),
                "best_test_wmape": float(best["wmape"]),
                "persistence_wmape": float(metric_lookup.get("persistence", np.nan)),
                "ridge_wmape": float(metric_lookup.get("ridge_autoregressive", np.nan)),
                "segmented_size_volatility_wmape": float(metric_lookup.get("segmented_size_volatility", np.nan)),
                "ridge_delta_vs_persistence": float(metric_lookup.get("ridge_autoregressive", np.nan) - metric_lookup.get("persistence", np.nan)),
                "segmented_delta_vs_persistence": float(metric_lookup.get("segmented_size_volatility", np.nan) - metric_lookup.get("persistence", np.nan)),
            }
        )
    return pd.DataFrame(rows)


def group_diagnostics(preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = preds[preds["fold_role"] == "test"].copy()
    for fold_year, fold_frame in test.groupby("fold_validation_year"):
        for group_col in ["size_group", "volatility_group", "size_volatility_group"]:
            for group_value, group_frame in fold_frame.groupby(group_col, dropna=False, observed=True):
                base = wmape(group_frame["y_true"].to_numpy(float), group_frame["pred_persistence"].to_numpy(float))
                ridge = wmape(group_frame["y_true"].to_numpy(float), group_frame["pred_ridge_autoregressive_fold"].to_numpy(float))
                segmented = wmape(
                    group_frame["y_true"].to_numpy(float),
                    group_frame["pred_segmented_size_volatility_group"].to_numpy(float),
                )
                rows.append(
                    {
                        "fold_validation_year": int(fold_year),
                        "test_target_year": int(group_frame["target_year"].iloc[0]),
                        "group_type": group_col,
                        "group": str(group_value),
                        "zones": int(group_frame["ze2020"].nunique()),
                        "target_sum": float(group_frame["y_true"].sum()),
                        "aggregate_growth_vs_lag_0": float(
                            (group_frame["y_true"].sum() - group_frame["y_lag_0"].sum()) / group_frame["y_lag_0"].sum()
                        )
                        if group_frame["y_lag_0"].sum()
                        else float("nan"),
                        "persistence_wmape": base,
                        "ridge_wmape": ridge,
                        "segmented_size_volatility_wmape": segmented,
                        "ridge_delta_vs_persistence": ridge - base,
                        "segmented_delta_vs_persistence": segmented - base,
                    }
                )
    return pd.DataFrame(rows)


def worst_zones(preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = preds[preds["fold_role"] == "test"].copy()
    for fold_year, fold_frame in test.groupby("fold_validation_year"):
        frame = fold_frame.copy()
        frame["abs_error_persistence"] = (frame["y_true"] - frame["pred_persistence"]).abs()
        frame["abs_error_ridge"] = (frame["y_true"] - frame["pred_ridge_autoregressive_fold"]).abs()
        frame["abs_error_segmented"] = (frame["y_true"] - frame["pred_segmented_size_volatility_group"]).abs()
        frame["ridge_minus_persistence_abs_error"] = frame["abs_error_ridge"] - frame["abs_error_persistence"]
        frame["segmented_minus_persistence_abs_error"] = frame["abs_error_segmented"] - frame["abs_error_persistence"]
        for row in frame.sort_values("abs_error_persistence", ascending=False).head(10).itertuples(index=False):
            rows.append(
                {
                    "fold_validation_year": int(fold_year),
                    "test_target_year": int(row.target_year),
                    "ze2020": row.ze2020,
                    "libze2020": row.libze2020,
                    "size_group": row.size_group,
                    "volatility_group": row.volatility_group,
                    "y_true": float(row.y_true),
                    "y_lag_0": float(row.y_lag_0),
                    "abs_error_persistence": float(row.abs_error_persistence),
                    "abs_error_ridge": float(row.abs_error_ridge),
                    "abs_error_segmented": float(row.abs_error_segmented),
                    "ridge_minus_persistence_abs_error": float(row.ridge_minus_persistence_abs_error),
                    "segmented_minus_persistence_abs_error": float(row.segmented_minus_persistence_abs_error),
                }
            )
    return pd.DataFrame(rows)


def build_report(folds: pd.DataFrame, groups: pd.DataFrame, worst: pd.DataFrame, quality: dict) -> str:
    lines = [
        "# SIDE Backtest Instability Diagnostic Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- explicar por que a regra segmentada falha no backtest rolante",
        "- identificar anos em que ridge, persistencia ou segmentacao vencem",
        "- localizar se o problema vem de choque agregado ou grupos territoriais",
        "",
        "## Folds De Teste",
        "",
        "| val year | test year | crescimento agregado | melhor modelo | pers. WMAPE | ridge WMAPE | seg. WMAPE |",
        "|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in folds.itertuples(index=False):
        lines.append(
            "| `{}` | `{}` | `{:.3f}` | `{}` | `{:.3f}` | `{:.3f}` | `{:.3f}` |".format(
                row.fold_validation_year,
                row.test_target_year,
                row.aggregate_growth_vs_lag_0,
                row.best_test_model,
                row.persistence_wmape,
                row.ridge_wmape,
                row.segmented_size_volatility_wmape,
            )
        )

    top_bad_groups = groups.sort_values("segmented_delta_vs_persistence", ascending=False).head(8)
    lines += [
        "",
        "## Grupos Onde A Segmentacao Mais Piora Contra Persistencia",
        "",
        "| fold | grupo | zonas | crescimento | delta WMAPE seg. vs pers. |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in top_bad_groups.itertuples(index=False):
        lines.append(
            "| `{}` | `{}` | `{}` | `{:.3f}` | `{:+.3f}` |".format(
                row.fold_validation_year,
                f"{row.group_type}:{row.group}",
                row.zones,
                row.aggregate_growth_vs_lag_0,
                row.segmented_delta_vs_persistence,
            )
        )

    lines += [
        "",
        "## Piores Zonas Por Erro Absoluto Da Persistencia",
        "",
        "| fold | zona | grupo | y true | y lag | erro pers. | delta ridge | delta seg. |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in worst.head(20).itertuples(index=False):
        lines.append(
            "| `{}` | `{}` | `{}` | `{:.0f}` | `{:.0f}` | `{:.0f}` | `{:+.0f}` | `{:+.0f}` |".format(
                row.fold_validation_year,
                row.libze2020,
                f"{row.size_group}/{row.volatility_group}",
                row.y_true,
                row.y_lag_0,
                row.abs_error_persistence,
                row.ridge_minus_persistence_abs_error,
                row.segmented_minus_persistence_abs_error,
            )
        )

    lines += [
        "",
        "## Leitura",
        "",
        f"- fold mais dificil para persistencia: `{quality['worst_persistence_fold']}`",
        f"- fold onde ridge mais melhora: `{quality['best_ridge_gain_fold']}`",
        f"- fold onde ridge mais piora: `{quality['worst_ridge_loss_fold']}`",
        f"- conclusao: {quality['main_conclusion']}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    preds = pd.read_csv(PRED_PATH, dtype={"ze2020": str})
    metrics = pd.read_csv(METRICS_PATH)
    folds = fold_diagnostics(preds, metrics)
    groups = group_diagnostics(preds)
    worst = worst_zones(preds)

    worst_persistence = folds.sort_values("persistence_wmape", ascending=False).iloc[0]
    best_ridge_gain = folds.sort_values("ridge_delta_vs_persistence").iloc[0]
    worst_ridge_loss = folds.sort_values("ridge_delta_vs_persistence", ascending=False).iloc[0]
    quality = {
        "fold_count": int(folds["fold_validation_year"].nunique()),
        "worst_persistence_fold": int(worst_persistence["fold_validation_year"]),
        "worst_persistence_test_year": int(worst_persistence["test_target_year"]),
        "best_ridge_gain_fold": int(best_ridge_gain["fold_validation_year"]),
        "best_ridge_gain_delta_wmape": float(best_ridge_gain["ridge_delta_vs_persistence"]),
        "worst_ridge_loss_fold": int(worst_ridge_loss["fold_validation_year"]),
        "worst_ridge_loss_delta_wmape": float(worst_ridge_loss["ridge_delta_vs_persistence"]),
        "main_conclusion": "a instabilidade e temporal: ridge ajuda em anos de choque agregado, mas perde forte quando a persistencia ja captura bem o ano seguinte.",
    }

    FOLD_DIAG_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    folds.to_csv(FOLD_DIAG_OUT, index=False)
    groups.to_csv(GROUP_DIAG_OUT, index=False)
    worst.to_csv(WORST_ZONE_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps(quality, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(folds, groups, worst, quality), encoding="utf-8")
    print(
        json.dumps(
            {
                "fold_diagnostics": str(FOLD_DIAG_OUT.relative_to(ROOT)),
                "group_diagnostics": str(GROUP_DIAG_OUT.relative_to(ROOT)),
                "worst_zones": str(WORST_ZONE_OUT.relative_to(ROOT)),
                "quality": str(QUALITY_OUT.relative_to(ROOT)),
                "report": str(REPORT_OUT.relative_to(ROOT)),
                **quality,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
