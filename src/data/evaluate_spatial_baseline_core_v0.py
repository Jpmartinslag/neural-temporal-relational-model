from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_core_v0.npz"
SAMPLE_INDEX_PATH = ROOT / "metadata" / "stgnn_tensor_sample_index_core_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
TARGET_PANEL_PATH = ROOT / "data" / "processed" / "graph_model_target_panel_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "spatial_baseline_predictions_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "spatial_baseline_metrics_core_v0.json"
REPORT_OUT = ROOT / "reports" / "SPATIAL_BASELINE_CORE_V0.md"

TARGET_COL = "target_proxy_establishment_creations_year"
ALPHA_GRID = np.linspace(0.0, 1.0, 21)


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
    return {
        "mae": mae(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
        "rmse": rmse(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
        "mape": mape(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
        "wmape": wmape(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
    }


def load_target_matrix(target_years: np.ndarray, node_count: int) -> dict[int, np.ndarray]:
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    target = target.sort_values(["target_year", "node_idx"]).reset_index(drop=True)
    by_year = {}
    for year in target_years:
        year_frame = target[target["target_year"] == int(year)].sort_values("node_idx")
        if len(year_frame) != node_count:
            raise ValueError(f"Target year {year} has {len(year_frame)} rows, expected {node_count}.")
        by_year[int(year)] = year_frame[TARGET_COL].to_numpy(dtype=float)
    return by_year


def build_predictions() -> tuple[pd.DataFrame, dict]:
    tensor = np.load(TENSOR_PATH, allow_pickle=True)
    sample_index = pd.read_csv(SAMPLE_INDEX_PATH)
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str}).sort_values("node_idx")

    y_true = tensor["y_raw"].astype(float)
    adjacency = tensor["adjacency_row_normalized_self_loop"].astype(float)
    feature_years = tensor["feature_year"].astype(int)
    target_years = tensor["target_year"].astype(int)
    node_ids = tensor["node_idx"].astype(int)

    target_by_year = load_target_matrix(feature_years, len(node_ids))

    rows = []
    for sample_idx, (feature_year, target_year) in enumerate(zip(feature_years, target_years)):
        y_t = target_by_year[int(feature_year)]
        pred_persistence = y_t
        pred_neighbor = adjacency @ y_t
        for node_pos, node_idx in enumerate(node_ids):
            rows.append(
                {
                    "sample_idx": int(sample_idx),
                    "feature_year": int(feature_year),
                    "target_year": int(target_year),
                    "split": sample_index.loc[sample_idx, "split"],
                    "node_idx": int(node_idx),
                    "ze2020": nodes.iloc[node_pos]["ze2020"],
                    "libze2020": nodes.iloc[node_pos]["libze2020"],
                    "y_true": float(y_true[sample_idx, node_pos]),
                    "pred_persistence": float(pred_persistence[node_pos]),
                    "pred_spatial_neighbor_average": float(pred_neighbor[node_pos]),
                }
            )

    pred = pd.DataFrame(rows)

    validation = pred[pred["split"] == "validation"]
    alpha_scores = []
    for alpha in ALPHA_GRID:
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
    pred["pred_spatial_blend"] = (
        best_alpha * pred["pred_persistence"] + (1.0 - best_alpha) * pred["pred_spatial_neighbor_average"]
    )

    metrics = {}
    for model_col in ["pred_persistence", "pred_spatial_neighbor_average", "pred_spatial_blend"]:
        model_name = model_col.replace("pred_", "")
        metrics[model_name] = {}
        for split in ["train", "validation", "test", "forecast_holdout"]:
            split_frame = pred[pred["split"] == split]
            if split_frame.empty:
                continue
            metrics[model_name][split] = metric_block(split_frame, model_col)

    quality = {
        "node_count": int(len(node_ids)),
        "sample_count": int(len(sample_index)),
        "alpha_grid": [float(x) for x in ALPHA_GRID],
        "selected_alpha": best_alpha,
        "alpha_selection_rule": "minimum validation WMAPE, then validation MAE, then lower alpha",
        "models": {
            "persistence": "y_hat_i(t+1) = y_i(t)",
            "spatial_neighbor_average": "y_hat_i(t+1) = sum_j A_norm[i,j] * y_j(t)",
            "spatial_blend": "y_hat_i(t+1) = alpha * y_i(t) + (1 - alpha) * sum_j A_norm[i,j] * y_j(t)",
        },
        "metrics": metrics,
        "interpretation_warning": (
            "This baseline tests whether graph neighborhood averaging adds signal over local persistence. "
            "It is not a causal estimate of spatial spillover."
        ),
    }
    return pred, quality


def write_report(quality: dict) -> None:
    lines = [
        "# Spatial Baseline Core v0",
        "",
        "Data: 2026-04-12",
        "",
        "Objetivo:",
        "",
        "- formalizar o primeiro baseline espacial antes de qualquer `STGNN`",
        "- testar se a vizinhanca do grafo melhora a persistencia local",
        "",
        "## Modelos",
        "",
        "- `persistence`: `y_hat_i(t+1) = y_i(t)`",
        "- `spatial_neighbor_average`: `y_hat_i(t+1) = sum_j A_norm[i,j] * y_j(t)`",
        "- `spatial_blend`: `alpha * y_i(t) + (1 - alpha) * sum_j A_norm[i,j] * y_j(t)`",
        "",
        "## Selecao de alpha",
        "",
        f"- grade: `{quality['alpha_grid']}`",
        f"- alpha selecionado: `{quality['selected_alpha']}`",
        f"- regra: `{quality['alpha_selection_rule']}`",
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
            "- este baseline define o piso minimo para justificar um modelo neural com grafo",
            "- se a media dos vizinhos ou a mistura espacial nao superar persistencia, o grafo ainda nao demonstrou ganho preditivo simples",
            "- mesmo quando houver ganho, isso nao deve ser interpretado automaticamente como efeito causal espacial",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    pred, quality = build_predictions()
    pred.to_csv(PRED_OUT, index=False)
    METRICS_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
