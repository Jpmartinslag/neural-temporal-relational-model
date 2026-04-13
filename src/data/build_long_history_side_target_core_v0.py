from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

TARGET_PANEL_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
ADJACENCY_PATH = ROOT / "data" / "processed" / "graph_adjacency_core_v0.csv"

DATASET_OUT = ROOT / "data" / "processed" / "long_history_side_target_dataset_core_v0.csv"
PRED_OUT = ROOT / "data" / "processed" / "long_history_side_target_baseline_predictions_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "long_history_side_target_baseline_metrics_core_v0.json"
QUALITY_OUT = ROOT / "reports" / "long_history_side_target_core_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "LONG_HISTORY_SIDE_TARGET_CORE_V0.md"

TARGET_COL = "side_establishment_creations_official"
LAG_COUNT = 5
RIDGE_ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]
SPATIAL_ALPHA_GRID = np.linspace(0.0, 1.0, 21)


def split_for_target_year(target_year: int) -> str:
    if target_year <= 2021:
        return "train"
    if target_year == 2022:
        return "validation"
    if target_year in [2023, 2024]:
        return "test"
    return "forecast_holdout"


def build_row_normalized_adjacency(adjacency: np.ndarray) -> np.ndarray:
    adjacency_with_self = adjacency.astype(float).copy()
    np.fill_diagonal(adjacency_with_self, 1.0)
    row_sum = adjacency_with_self.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    return adjacency_with_self / row_sum


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


def safe_growth(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous


def ridge_fit_predict(train_x: np.ndarray, train_y: np.ndarray, pred_x: np.ndarray, alpha: float) -> np.ndarray:
    xtx = train_x.T @ train_x
    ridge = xtx + alpha * np.eye(train_x.shape[1])
    xty = train_x.T @ train_y
    beta = np.linalg.pinv(ridge) @ xty
    return pred_x @ beta


def build_dataset() -> pd.DataFrame:
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str}).sort_values("node_idx")
    adjacency = pd.read_csv(ADJACENCY_PATH).drop(columns=["source_idx"]).to_numpy(dtype=float)
    adjacency_norm = build_row_normalized_adjacency(adjacency)

    target = target.sort_values(["target_year", "node_idx"]).reset_index(drop=True)
    lookup = {
        (int(row.target_year), int(row.node_idx)): float(getattr(row, TARGET_COL))
        for row in target.itertuples(index=False)
    }
    years = sorted(int(y) for y in target["target_year"].unique())
    node_ids = nodes["node_idx"].astype(int).to_numpy()

    rows = []
    for feature_year in years:
        target_year = feature_year + 1
        if target_year not in years:
            continue
        required_lag_years = [feature_year - lag for lag in range(LAG_COUNT)]
        if any(year not in years for year in required_lag_years):
            continue

        y_t_vector = np.array([lookup[(feature_year, int(node_idx))] for node_idx in node_ids], dtype=float)
        pred_neighbor = adjacency_norm @ y_t_vector

        for node_pos, node in enumerate(nodes.itertuples(index=False)):
            node_idx = int(node.node_idx)
            lag_values = [lookup[(feature_year - lag, node_idx)] for lag in range(LAG_COUNT)]
            y_true = lookup[(target_year, node_idx)]
            row = {
                "feature_year": feature_year,
                "target_year": target_year,
                "split": split_for_target_year(target_year),
                "node_idx": node_idx,
                "ze2020": node.ze2020,
                "libze2020": node.libze2020,
                "y_true": y_true,
                "pred_persistence": lag_values[0],
                "pred_delta": max(0.0, lag_values[0] + (lag_values[0] - lag_values[1])),
                "pred_moving_average_3": float(np.mean(lag_values[:3])),
                "pred_spatial_neighbor_average": float(pred_neighbor[node_pos]),
                "growth_1y": safe_growth(lag_values[0], lag_values[1]),
                "growth_2y": safe_growth(lag_values[0], lag_values[2]),
                "growth_3y": safe_growth(lag_values[0], lag_values[3]),
            }
            for lag, value in enumerate(lag_values):
                row[f"y_lag_{lag}"] = value
            rows.append(row)
    return pd.DataFrame(rows)


def add_ridge_predictions(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    model_frame = frame.copy()
    feature_cols = []
    for lag in range(LAG_COUNT):
        col = f"log_y_lag_{lag}"
        model_frame[col] = np.log1p(model_frame[f"y_lag_{lag}"].to_numpy(dtype=float))
        feature_cols.append(col)
    feature_cols += ["growth_1y", "growth_2y", "growth_3y"]

    train = model_frame[model_frame["split"] == "train"].copy()
    validation = model_frame[model_frame["split"] == "validation"].copy()
    medians = train[feature_cols].median(numeric_only=True).fillna(0.0)
    means = train[feature_cols].fillna(medians).mean().fillna(0.0)
    stds = train[feature_cols].fillna(medians).std().replace(0, 1.0).fillna(1.0)

    def design(df: pd.DataFrame) -> np.ndarray:
        x = df[feature_cols].fillna(medians).fillna(0.0)
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
    model_frame["pred_ridge_autoregressive"] = np.expm1(
        ridge_fit_predict(train_x, train_y, design(model_frame), best_alpha)
    ).clip(min=0.0)
    return model_frame, {
        "selected_ridge_alpha": best_alpha,
        "ridge_alpha_grid": [float(alpha) for alpha in RIDGE_ALPHA_GRID],
        "ridge_alpha_selection": alpha_scores,
        "used_features": feature_cols,
        "scaling_scope": "train_split_only",
    }


def add_spatial_blend(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    validation = frame[frame["split"] == "validation"].copy()
    alpha_scores = []
    for alpha in SPATIAL_ALPHA_GRID:
        blended = alpha * validation["pred_persistence"] + (1.0 - alpha) * validation["pred_spatial_neighbor_average"]
        alpha_scores.append(
            {
                "alpha": float(alpha),
                "validation_wmape": wmape(validation["y_true"].to_numpy(dtype=float), blended.to_numpy(dtype=float)),
                "validation_mae": mae(validation["y_true"].to_numpy(dtype=float), blended.to_numpy(dtype=float)),
            }
        )
    alpha_frame = pd.DataFrame(alpha_scores).sort_values(["validation_wmape", "validation_mae", "alpha"])
    best_alpha = float(alpha_frame.iloc[0]["alpha"])
    frame = frame.copy()
    frame["pred_spatial_blend"] = (
        best_alpha * frame["pred_persistence"] + (1.0 - best_alpha) * frame["pred_spatial_neighbor_average"]
    )
    return frame, {
        "selected_spatial_alpha": best_alpha,
        "spatial_alpha_grid": [float(alpha) for alpha in SPATIAL_ALPHA_GRID],
        "spatial_alpha_selection": alpha_scores,
    }


def evaluate(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    frame, ridge_metadata = add_ridge_predictions(frame)
    frame, spatial_metadata = add_spatial_blend(frame)

    model_cols = [
        "pred_persistence",
        "pred_delta",
        "pred_moving_average_3",
        "pred_ridge_autoregressive",
        "pred_spatial_neighbor_average",
        "pred_spatial_blend",
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
        "target_column": TARGET_COL,
        "lag_count": LAG_COUNT,
        "node_count": int(frame["node_idx"].nunique()),
        "row_count": int(len(frame)),
        "sample_count": int(frame[["feature_year", "target_year"]].drop_duplicates().shape[0]),
        "feature_years": sorted(int(y) for y in frame["feature_year"].unique()),
        "target_years": sorted(int(y) for y in frame["target_year"].unique()),
        "split_counts": {
            k: int(v)
            for k, v in frame[["feature_year", "target_year", "split"]]
            .drop_duplicates()["split"]
            .value_counts()
            .sort_index()
            .to_dict()
            .items()
        },
        "models": {
            "persistence": "y_hat(t+1) = y(t)",
            "delta": "y_hat(t+1) = max(0, y(t) + y(t) - y(t-1))",
            "moving_average_3": "y_hat(t+1) = mean(y(t), y(t-1), y(t-2))",
            "ridge_autoregressive": "ridge on 5 target lags and recent growth rates",
            "spatial_neighbor_average": "row-normalized geographic adjacency applied to y(t)",
            "spatial_blend": "validated blend between persistence and geographic neighbor average",
        },
        "ridge_metadata": ridge_metadata,
        "spatial_metadata": spatial_metadata,
        "metrics": metrics,
        "interpretation": (
            "This long-history package increases supervised annual samples by using only official SIDE target history. "
            "It is intentionally separate from the richer feature tensor."
        ),
    }
    return frame, quality


def write_report(quality: dict) -> None:
    lines = [
        "# Long History SIDE Target Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- criar um pacote longo separado usando historico oficial `SIDE`",
        "- aumentar anos supervisionados sem misturar com o pacote rico de features",
        "- testar baselines longos antes de qualquer arquitetura complexa",
        "",
        "## Estrutura",
        "",
        f"- target: `{quality['target_column']}`",
        f"- lags usados: `{quality['lag_count']}`",
        f"- nos: `{quality['node_count']}`",
        f"- anos de feature: `{quality['feature_years']}`",
        f"- anos de target: `{quality['target_years']}`",
        f"- amostras anuais: `{quality['sample_count']}`",
        f"- splits: `{quality['split_counts']}`",
        f"- alpha espacial selecionado: `{quality['spatial_metadata']['selected_spatial_alpha']}`",
        f"- alpha ridge selecionado: `{quality['ridge_metadata']['selected_ridge_alpha']}`",
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
            "- este pacote aumenta os anos supervisionados, mas usa apenas historico do proprio target",
            "- portanto ele testa memoria temporal do fenomeno, nao efeito de covariaveis externas",
            "- deve ser comparado ao pacote rico, nao fundido com ele sem nome explicito",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    dataset = build_dataset()
    dataset.to_csv(DATASET_OUT, index=False)
    pred, quality = evaluate(dataset)
    pred.to_csv(PRED_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps({k: v for k, v in quality.items() if k != "metrics"}, ensure_ascii=False, indent=2), encoding="utf-8")
    METRICS_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
