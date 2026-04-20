from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

PRED_PATH = ROOT / "data" / "processed" / "segmented_decision_rule_backtest_predictions_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "temporal_regime_side_baseline_predictions_core_v0.csv"
METRICS_OUT = ROOT / "metadata" / "temporal_regime_side_baseline_metrics_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "temporal_regime_side_baseline_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "TEMPORAL_REGIME_SIDE_BASELINE_CORE_V0.md"

THRESHOLD_GRID = [-0.05, -0.025, 0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15]


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def metric_block(frame: pd.DataFrame, pred_col: str) -> dict[str, float]:
    return {
        "wmape": wmape(frame["y_true"].to_numpy(float), frame[pred_col].to_numpy(float)),
        "mae": mae(frame["y_true"].to_numpy(float), frame[pred_col].to_numpy(float)),
        "rmse": rmse(frame["y_true"].to_numpy(float), frame[pred_col].to_numpy(float)),
        "rows": int(len(frame)),
        "zones": int(frame["ze2020"].nunique()),
    }


def add_observed_aggregate_growth(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    growth = (
        out.groupby(["fold_validation_year", "fold_role"], as_index=False)
        .agg(y_lag_0_sum=("y_lag_0", "sum"), y_lag_1_sum=("y_lag_1", "sum"))
    )
    growth["observed_aggregate_growth"] = (
        (growth["y_lag_0_sum"] - growth["y_lag_1_sum"]) / growth["y_lag_1_sum"].replace(0, np.nan)
    ).fillna(0.0)
    return out.merge(
        growth[["fold_validation_year", "fold_role", "observed_aggregate_growth"]],
        on=["fold_validation_year", "fold_role"],
        how="left",
    )


def regime_prediction(frame: pd.DataFrame, threshold: float) -> pd.Series:
    use_ridge = frame["observed_aggregate_growth"] >= threshold
    return pd.Series(
        np.where(use_ridge, frame["pred_ridge_autoregressive_fold"], frame["pred_persistence"]),
        index=frame.index,
        dtype=float,
    )


def select_threshold(validation: pd.DataFrame) -> tuple[float, list[dict]]:
    scores = []
    for threshold in THRESHOLD_GRID:
        pred = regime_prediction(validation, threshold)
        scores.append(
            {
                "threshold": float(threshold),
                "validation_wmape": wmape(validation["y_true"].to_numpy(float), pred.to_numpy(float)),
                "validation_mae": mae(validation["y_true"].to_numpy(float), pred.to_numpy(float)),
                "validation_uses_ridge": bool((validation["observed_aggregate_growth"] >= threshold).iloc[0]),
                "validation_observed_aggregate_growth": float(validation["observed_aggregate_growth"].iloc[0]),
            }
        )
    best = pd.DataFrame(scores).sort_values(["validation_wmape", "validation_mae", "threshold"]).iloc[0]
    return float(best["threshold"]), scores


def oracle_prediction(frame: pd.DataFrame) -> pd.Series:
    persistence_error = (frame["y_true"] - frame["pred_persistence"]).abs()
    ridge_error = (frame["y_true"] - frame["pred_ridge_autoregressive_fold"]).abs()
    return pd.Series(
        np.where(ridge_error < persistence_error, frame["pred_ridge_autoregressive_fold"], frame["pred_persistence"]),
        index=frame.index,
        dtype=float,
    )


def evaluate_fold(frame: pd.DataFrame, fold_year: int) -> tuple[pd.DataFrame, dict]:
    fold = frame[frame["fold_validation_year"] == fold_year].copy()
    validation = fold[fold["fold_role"] == "validation"].copy()
    test = fold[fold["fold_role"] == "test"].copy()
    threshold, threshold_scores = select_threshold(validation)
    fold["pred_temporal_regime"] = regime_prediction(fold, threshold)
    fold["temporal_regime_threshold"] = threshold
    fold["temporal_regime_selected_model"] = np.where(
        fold["observed_aggregate_growth"] >= threshold,
        "ridge_autoregressive",
        "persistence",
    )
    fold["pred_oracle_regime"] = oracle_prediction(fold)
    metadata = {
        "fold_validation_year": int(fold_year),
        "test_target_year": int(test["target_year"].iloc[0]),
        "selected_threshold": threshold,
        "validation_observed_aggregate_growth": float(validation["observed_aggregate_growth"].iloc[0]),
        "test_observed_aggregate_growth": float(test["observed_aggregate_growth"].iloc[0]),
        "validation_selected_model": str(fold[fold["fold_role"] == "validation"]["temporal_regime_selected_model"].iloc[0]),
        "test_selected_model": str(fold[fold["fold_role"] == "test"]["temporal_regime_selected_model"].iloc[0]),
        "threshold_scores": threshold_scores,
    }
    return fold, metadata


def summarize_metrics(preds: pd.DataFrame) -> pd.DataFrame:
    model_cols = {
        "persistence": "pred_persistence",
        "ridge_autoregressive": "pred_ridge_autoregressive_fold",
        "temporal_regime": "pred_temporal_regime",
        "oracle_regime_not_usable": "pred_oracle_regime",
    }
    rows = []
    for fold_year, fold_frame in preds.groupby("fold_validation_year"):
        for role, role_frame in fold_frame.groupby("fold_role"):
            for model_name, pred_col in model_cols.items():
                rows.append(
                    {
                        "fold_validation_year": int(fold_year),
                        "target_role": role,
                        "model": model_name,
                        "selected_model": str(role_frame["temporal_regime_selected_model"].iloc[0])
                        if model_name == "temporal_regime"
                        else "",
                        "observed_aggregate_growth": float(role_frame["observed_aggregate_growth"].iloc[0]),
                        **metric_block(role_frame, pred_col),
                    }
                )
    return pd.DataFrame(rows)


def build_report(metrics: pd.DataFrame, quality: dict) -> str:
    aggregate = (
        metrics.groupby(["target_role", "model"], as_index=False)
        .agg(wmape_mean=("wmape", "mean"), wmape_median=("wmape", "median"), folds=("fold_validation_year", "nunique"))
        .sort_values(["target_role", "wmape_mean", "model"])
    )
    test_fold_metrics = metrics[metrics["target_role"] == "test"].copy()
    lines = [
        "# Temporal Regime SIDE Baseline Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- testar regra simples entre persistencia e ridge",
        "- usar apenas crescimento agregado observado no ano de feature",
        "- manter `oracle_regime_not_usable` apenas como teto diagnostico",
        "",
        "## Resultado Agregado",
        "",
        "| papel | modelo | WMAPE medio | WMAPE mediano | folds |",
        "|---|---|---:|---:|---:|",
    ]
    for row in aggregate.itertuples(index=False):
        lines.append(
            "| `{}` | `{}` | `{:.3f}` | `{:.3f}` | `{}` |".format(
                row.target_role,
                row.model,
                row.wmape_mean,
                row.wmape_median,
                row.folds,
            )
        )
    lines += [
        "",
        "## Teste Por Fold",
        "",
        "| fold | modelo | crescimento observado | WMAPE | selecionado |",
        "|---:|---|---:|---:|---|",
    ]
    for row in test_fold_metrics.sort_values(["fold_validation_year", "model"]).itertuples(index=False):
        lines.append(
            "| `{}` | `{}` | `{:.3f}` | `{:.3f}` | `{}` |".format(
                row.fold_validation_year,
                row.model,
                row.observed_aggregate_growth,
                row.wmape,
                row.selected_model,
            )
        )
    lines += [
        "",
        "## Leitura",
        "",
        f"- melhor modelo medio no teste: `{quality['best_test_mean_model']}`",
        f"- WMAPE medio da regra temporal: `{quality['temporal_regime_test_wmape_mean']:.3f}`",
        f"- WMAPE medio da persistencia: `{quality['persistence_test_wmape_mean']:.3f}`",
        f"- WMAPE medio do ridge: `{quality['ridge_test_wmape_mean']:.3f}`",
        f"- conclusao: {quality['main_conclusion']}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    frame = pd.read_csv(PRED_PATH, dtype={"ze2020": str})
    frame = add_observed_aggregate_growth(frame)

    fold_frames = []
    fold_metadata = []
    for fold_year in sorted(frame["fold_validation_year"].unique()):
        fold_frame, metadata = evaluate_fold(frame, int(fold_year))
        fold_frames.append(fold_frame)
        fold_metadata.append(metadata)

    preds = pd.concat(fold_frames, ignore_index=True)
    metrics = summarize_metrics(preds)
    test_mean = metrics[metrics["target_role"] == "test"].groupby("model", as_index=False)["wmape"].mean()
    best_test = test_mean.sort_values(["wmape", "model"]).iloc[0]
    get_mean = lambda model: float(test_mean[test_mean["model"] == model]["wmape"].iloc[0])
    quality = {
        "folds": fold_metadata,
        "threshold_grid": [float(value) for value in THRESHOLD_GRID],
        "best_test_mean_model": str(best_test["model"]),
        "best_test_mean_wmape": float(best_test["wmape"]),
        "persistence_test_wmape_mean": get_mean("persistence"),
        "ridge_test_wmape_mean": get_mean("ridge_autoregressive"),
        "temporal_regime_test_wmape_mean": get_mean("temporal_regime"),
        "oracle_regime_test_wmape_mean": get_mean("oracle_regime_not_usable"),
        "main_conclusion": "a regra por crescimento observado ainda nao supera ridge nem persistencia de forma robusta; precisamos de sinal antecipador externo para regime.",
    }

    PRED_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    preds.to_csv(PRED_OUT, index=False)
    metrics.to_csv(METRICS_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps(quality, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(metrics, quality), encoding="utf-8")
    print(
        json.dumps(
            {
                "predictions": str(PRED_OUT.relative_to(ROOT)),
                "metrics": str(METRICS_OUT.relative_to(ROOT)),
                "quality": str(QUALITY_OUT.relative_to(ROOT)),
                "report": str(REPORT_OUT.relative_to(ROOT)),
                "best_test_mean_model": quality["best_test_mean_model"],
                "temporal_regime_test_wmape_mean": quality["temporal_regime_test_wmape_mean"],
                "main_conclusion": quality["main_conclusion"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
