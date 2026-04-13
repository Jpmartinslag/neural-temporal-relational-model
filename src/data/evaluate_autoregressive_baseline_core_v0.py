from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

SAMPLE_INDEX_PATH = ROOT / "metadata" / "stgnn_tensor_sample_index_core_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
TARGET_PANEL_PATH = ROOT / "data" / "processed" / "graph_model_target_panel_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "autoregressive_baseline_predictions_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "autoregressive_baseline_metrics_core_v0.json"
REPORT_OUT = ROOT / "reports" / "AUTOREGRESSIVE_BASELINE_CORE_V0.md"

TARGET_COL = "target_proxy_establishment_creations_year"
RIDGE_ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]
LAG_COUNT = 5


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


def metric_block(frame: pd.DataFrame, pred_col: str) -> dict[str, float]:
    y_true = frame["y_true"].to_numpy(dtype=float)
    y_pred = frame[pred_col].to_numpy(dtype=float)
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "wmape": wmape(y_true, y_pred),
    }


def ridge_fit_predict(train_x: np.ndarray, train_y: np.ndarray, pred_x: np.ndarray, alpha: float) -> np.ndarray:
    xtx = train_x.T @ train_x
    ridge = xtx + alpha * np.eye(train_x.shape[1])
    xty = train_x.T @ train_y
    beta = np.linalg.pinv(ridge) @ xty
    return pred_x @ beta


def build_target_lookup() -> tuple[pd.DataFrame, dict[tuple[int, int], float]]:
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    target = target.sort_values(["target_year", "node_idx"]).reset_index(drop=True)
    lookup = {
        (int(row.target_year), int(row.node_idx)): float(getattr(row, TARGET_COL))
        for row in target.itertuples(index=False)
    }
    return target, lookup


def value_at(lookup: dict[tuple[int, int], float], year: int, node_idx: int) -> float:
    return lookup[(int(year), int(node_idx))]


def safe_growth(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous


def build_design_frame() -> pd.DataFrame:
    sample_index = pd.read_csv(SAMPLE_INDEX_PATH)
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str}).sort_values("node_idx")
    _, lookup = build_target_lookup()

    rows = []
    for sample in sample_index.itertuples(index=False):
        feature_year = int(sample.feature_year)
        target_year = int(sample.target_year)
        for node in nodes.itertuples(index=False):
            node_idx = int(node.node_idx)
            y_t = value_at(lookup, feature_year, node_idx)
            y_t1 = value_at(lookup, feature_year - 1, node_idx)
            y_t2 = value_at(lookup, feature_year - 2, node_idx)
            y_t3 = value_at(lookup, feature_year - 3, node_idx)
            y_t4 = value_at(lookup, feature_year - 4, node_idx)
            y_true = value_at(lookup, target_year, node_idx)

            pred_persistence = y_t
            pred_delta = max(0.0, y_t + (y_t - y_t1))
            pred_moving_average_3 = float(np.mean([y_t, y_t1, y_t2]))

            rows.append(
                {
                    "sample_idx": int(sample.sample_idx),
                    "feature_year": feature_year,
                    "target_year": target_year,
                    "split": sample.split,
                    "node_idx": node_idx,
                    "ze2020": node.ze2020,
                    "libze2020": node.libze2020,
                    "y_true": y_true,
                    "y_t": y_t,
                    "y_t_minus_1": y_t1,
                    "y_t_minus_2": y_t2,
                    "y_t_minus_3": y_t3,
                    "y_t_minus_4": y_t4,
                    "growth_1y": safe_growth(y_t, y_t1),
                    "growth_2y": safe_growth(y_t, y_t2),
                    "growth_3y": safe_growth(y_t, y_t3),
                    "pred_persistence": pred_persistence,
                    "pred_delta": pred_delta,
                    "pred_moving_average_3": pred_moving_average_3,
                }
            )
    return pd.DataFrame(rows)


def autoregressive_feature_columns() -> list[str]:
    cols = [f"log_y_t_minus_{idx}" for idx in range(LAG_COUNT)]
    cols += ["growth_1y", "growth_2y", "growth_3y"]
    return cols


def add_ridge_predictions(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    model_frame = frame.copy()
    for idx in range(LAG_COUNT):
        source_col = "y_t" if idx == 0 else f"y_t_minus_{idx}"
        model_frame[f"log_y_t_minus_{idx}"] = np.log1p(model_frame[source_col].to_numpy(dtype=float))

    used_features = autoregressive_feature_columns()
    train = model_frame[model_frame["split"] == "train"].copy()
    validation = model_frame[model_frame["split"] == "validation"].copy()

    medians = train[used_features].median(numeric_only=True).fillna(0.0)
    means = train[used_features].fillna(medians).mean().fillna(0.0)
    stds = train[used_features].fillna(medians).std().replace(0, 1.0).fillna(1.0)

    def design(df: pd.DataFrame) -> np.ndarray:
        x = df[used_features].fillna(medians).fillna(0.0)
        x = (x - means) / stds
        x = x.replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=float)
        return np.hstack([np.ones((x.shape[0], 1)), x])

    train_x = design(train)
    train_y = np.log1p(train["y_true"].to_numpy(dtype=float))
    validation_x = design(validation)
    validation_y = validation["y_true"].to_numpy(dtype=float)

    alpha_scores = []
    for alpha in RIDGE_ALPHA_GRID:
        pred_validation = np.expm1(ridge_fit_predict(train_x, train_y, validation_x, alpha)).clip(min=0.0)
        alpha_scores.append(
            {
                "alpha": float(alpha),
                "validation_wmape": wmape(validation_y, pred_validation),
                "validation_mae": mae(validation_y, pred_validation),
            }
        )
    alpha_frame = pd.DataFrame(alpha_scores).sort_values(["validation_wmape", "validation_mae", "alpha"])
    best_alpha = float(alpha_frame.iloc[0]["alpha"])

    pred = np.expm1(ridge_fit_predict(train_x, train_y, design(model_frame), best_alpha)).clip(min=0.0)
    model_frame["pred_ridge_autoregressive"] = pred

    metadata = {
        "selected_ridge_alpha": best_alpha,
        "ridge_alpha_grid": [float(alpha) for alpha in RIDGE_ALPHA_GRID],
        "ridge_alpha_selection": alpha_scores,
        "used_features": used_features,
        "scaling_scope": "train_split_only",
    }
    return model_frame, metadata


def evaluate() -> tuple[pd.DataFrame, dict]:
    frame = build_design_frame()
    frame, model_metadata = add_ridge_predictions(frame)

    model_cols = [
        "pred_persistence",
        "pred_delta",
        "pred_moving_average_3",
        "pred_ridge_autoregressive",
    ]
    metrics = {}
    for pred_col in model_cols:
        model_name = pred_col.replace("pred_", "")
        metrics[model_name] = {}
        for split in ["train", "validation", "test", "forecast_holdout"]:
            split_frame = frame[frame["split"] == split]
            if split_frame.empty:
                continue
            metrics[model_name][split] = metric_block(split_frame, pred_col)

    quality = {
        "node_count": int(frame["node_idx"].nunique()),
        "row_count": int(len(frame)),
        "sample_count": int(frame["sample_idx"].nunique()),
        "models": {
            "persistence": "y_hat(t+1) = y(t)",
            "delta": "y_hat(t+1) = max(0, y(t) + y(t) - y(t-1))",
            "moving_average_3": "y_hat(t+1) = mean(y(t), y(t-1), y(t-2))",
            "ridge_autoregressive": "ridge regression on log lags and recent growth rates, trained only on train split",
        },
        "model_metadata": model_metadata,
        "metrics": metrics,
        "interpretation": (
            "This baseline tests whether the annual internal history of each ZE2020 is enough to predict the next "
            "target year before adding external features, graph propagation or neural architectures."
        ),
    }
    return frame, quality


def write_report(quality: dict) -> None:
    lines = [
        "# Autoregressive Baseline Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- testar a dinamica anual interna da propria zona antes de arquitetura complexa",
        "- comparar persistencia, extrapolacao simples, media movel e regressao autoregressiva",
        "",
        "## Modelos",
        "",
        "- `persistence`: `y_hat(t+1) = y(t)`",
        "- `delta`: `max(0, y(t) + y(t) - y(t-1))`",
        "- `moving_average_3`: media de `y(t)`, `y(t-1)` e `y(t-2)`",
        "- `ridge_autoregressive`: regressao ridge com lags em log e taxas recentes de crescimento",
        "",
        "## Ridge",
        "",
        f"- alpha selecionado: `{quality['model_metadata']['selected_ridge_alpha']}`",
        f"- features: `{quality['model_metadata']['used_features']}`",
        "- normalizacao calculada apenas no split de treino",
        "",
        "## Metricas",
        "",
    ]
    for model_name, model_metrics in quality["metrics"].items():
        lines.append(f"### {model_name}")
        lines.append("")
        for split_name, vals in model_metrics.items():
            lines.append(
                f"- `{split_name}`: MAE=`{vals['mae']:.3f}`, RMSE=`{vals['rmse']:.3f}`, MAPE=`{vals['mape']:.3f}`, WMAPE=`{vals['wmape']:.3f}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Leitura",
            "",
            "- este baseline mede a forca da dinamica intra-zona",
            "- se ele superar os modelos espaciais simples, a arquitetura futura deve preservar um componente local forte",
            "- qualquer modelo com grafo ou agentes deve ser comparado contra este piso antes de ser interpretado",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    pred, quality = evaluate()
    pred.to_csv(PRED_OUT, index=False)
    METRICS_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
