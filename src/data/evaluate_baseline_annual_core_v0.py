from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "data" / "processed" / "baseline_annual_dataset_core_v0.csv"
TARGET_ANNUAL_PATH = ROOT / "data" / "processed" / "target_proxy_annual_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "baseline_annual_predictions_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "baseline_annual_metrics_core_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "BASELINE_ANNUAL_EVALUATION_V0.md"

TRAIN_YEARS = [2020, 2021, 2022]
VAL_YEARS = [2023]
TEST_YEARS = [2024]
RIDGE_ALPHA = 1.0


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def metric_block(frame: pd.DataFrame, target_col: str, pred_col: str) -> dict[str, float]:
    y_true = frame[target_col].to_numpy(dtype=float)
    y_pred = frame[pred_col].to_numpy(dtype=float)
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "wmape": wmape(y_true, y_pred),
    }


def ridge_fit_predict(
    train_X: np.ndarray, train_y: np.ndarray, pred_X: np.ndarray, alpha: float
) -> np.ndarray:
    xtx = train_X.T @ train_X
    ridge = xtx + alpha * np.eye(train_X.shape[1])
    xty = train_X.T @ train_y
    beta = np.linalg.pinv(ridge) @ xty
    return pred_X @ beta


def build_model_frame() -> pd.DataFrame:
    baseline = pd.read_csv(BASELINE_PATH, dtype={"ze2020": str})
    annual_target = pd.read_csv(TARGET_ANNUAL_PATH, dtype={"ze2020": str})
    annual_target = annual_target.rename(
        columns={
            "target_year": "feature_year",
            "target_proxy_establishment_creations_year": "target_proxy_establishment_creations_t",
        }
    )
    frame = baseline.merge(
        annual_target[["feature_year", "ze2020", "target_proxy_establishment_creations_t"]],
        on=["feature_year", "ze2020"],
        how="left",
    )
    frame["split"] = np.select(
        [
            frame["feature_year"].isin(TRAIN_YEARS),
            frame["feature_year"].isin(VAL_YEARS),
            frame["feature_year"].isin(TEST_YEARS),
        ],
        ["train", "validation", "test"],
        default="excluded",
    )
    return frame


def feature_columns(frame: pd.DataFrame) -> list[str]:
    exclude = {
        "feature_year",
        "node_idx",
        "ze2020",
        "libze2020",
        "reg",
        "anomaly_reason",
        "target_year",
        "target_proxy_establishment_creations_tplus1",
        "has_target_tplus1",
        "split",
    }
    cols = []
    for col in frame.columns:
        if col in exclude:
            continue
        if pd.api.types.is_numeric_dtype(frame[col]):
            cols.append(col)
    return cols


def write_report(metrics: dict, used_features: list[str]) -> None:
    lines = [
        "# Baseline Annual Evaluation v0",
        "",
        "Data: 2026-04-09",
        "",
        "Objetivo:",
        "",
        "- rodar o primeiro baseline anual sem grafo sobre o `core_v0`",
        "",
        "## Split temporal",
        "",
        "- treino: `2020-2022`",
        "- validacao: `2023`",
        "- teste: `2024`",
        "",
        "## Modelos avaliados",
        "",
        "- `persistence`: usa `target_t` como previsao de `target_t+1`",
        "- `ridge_linear`: regressao linear regularizada sem grafo",
        "",
        "## Features usadas na regressao linear",
        "",
    ]
    for col in used_features:
        lines.append(f"- `{col}`")

    lines.extend(
        [
            "",
            "## Metricas por split",
            "",
        ]
    )
    for model_name, model_metrics in metrics.items():
        lines.append(f"### {model_name}")
        lines.append("")
        for split_name, vals in model_metrics.items():
            lines.append(
                f"- `{split_name}`: MAE=`{vals['mae']:.3f}`, RMSE=`{vals['rmse']:.3f}`, MAPE=`{vals['mape']:.3f}`, WMAPE=`{vals['wmape']:.3f}`"
            )
        lines.append("")
    REPORT_OUT.write_text("\n".join(lines))


def main() -> None:
    frame = build_model_frame()
    used_features = feature_columns(frame)
    frame["pred_persistence"] = frame["target_proxy_establishment_creations_t"]

    train = frame[frame["split"] == "train"].copy()
    validation = frame[frame["split"] == "validation"].copy()
    test = frame[frame["split"] == "test"].copy()

    medians = train[used_features].median(numeric_only=True)
    medians = medians.fillna(0.0)
    means = train[used_features].fillna(medians).mean().fillna(0.0)
    stds = train[used_features].fillna(medians).std().replace(0, 1.0).fillna(1.0)

    def design(df: pd.DataFrame) -> np.ndarray:
        x = df[used_features].fillna(medians).fillna(0.0)
        x = (x - means) / stds
        x = x.replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=float)
        intercept = np.ones((x.shape[0], 1))
        return np.hstack([intercept, x])

    y_train = np.log1p(train["target_proxy_establishment_creations_tplus1"].to_numpy(dtype=float))
    x_train = design(train)
    for subset in [train, validation, test]:
        pred = ridge_fit_predict(x_train, y_train, design(subset), RIDGE_ALPHA)
        subset["pred_ridge_linear"] = np.expm1(pred)

    pred_frame = pd.concat([train, validation, test], ignore_index=True)
    pred_frame["pred_ridge_linear"] = pred_frame["pred_ridge_linear"].clip(lower=0.0)
    pred_frame.to_csv(PRED_OUT, index=False)

    metrics = {
        "persistence": {
            "train": metric_block(train, "target_proxy_establishment_creations_tplus1", "pred_persistence"),
            "validation": metric_block(validation, "target_proxy_establishment_creations_tplus1", "pred_persistence"),
            "test": metric_block(test, "target_proxy_establishment_creations_tplus1", "pred_persistence"),
        },
        "ridge_linear": {
            "train": metric_block(train, "target_proxy_establishment_creations_tplus1", "pred_ridge_linear"),
            "validation": metric_block(validation, "target_proxy_establishment_creations_tplus1", "pred_ridge_linear"),
            "test": metric_block(test, "target_proxy_establishment_creations_tplus1", "pred_ridge_linear"),
        },
    }

    quality = {
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "test_rows": int(len(test)),
        "used_feature_count": int(len(used_features)),
        "used_features": used_features,
        "ridge_alpha": RIDGE_ALPHA,
        "target_column": "target_proxy_establishment_creations_tplus1",
        "baseline_models": ["persistence", "ridge_linear"],
        "metrics": metrics,
    }
    pd.Series(quality).to_json(METRICS_OUT, indent=2)
    write_report(metrics, used_features)
    print(quality)


if __name__ == "__main__":
    main()
