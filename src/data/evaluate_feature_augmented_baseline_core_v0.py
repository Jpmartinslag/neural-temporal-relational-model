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
FEATURE_REGISTRY_PATH = ROOT / "metadata" / "stgnn_tensor_feature_registry_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "feature_augmented_baseline_predictions_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "feature_augmented_baseline_metrics_core_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "FEATURE_AUGMENTED_BASELINE_CORE_V0.md"

TARGET_COL = "target_proxy_establishment_creations_year"
RIDGE_ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]


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


def load_target_lookup() -> dict[tuple[int, int], float]:
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    return {
        (int(row.target_year), int(row.node_idx)): float(getattr(row, TARGET_COL))
        for row in target.itertuples(index=False)
    }


def build_base_frame() -> pd.DataFrame:
    tensor = np.load(TENSOR_PATH, allow_pickle=True)
    sample_index = pd.read_csv(SAMPLE_INDEX_PATH)
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str}).sort_values("node_idx")
    target_lookup = load_target_lookup()

    y_true = tensor["y_raw"].astype(float)
    feature_years = tensor["feature_year"].astype(int)
    target_years = tensor["target_year"].astype(int)
    node_ids = tensor["node_idx"].astype(int)

    rows = []
    for sample_idx, (feature_year, target_year) in enumerate(zip(feature_years, target_years)):
        for node_pos, node_idx in enumerate(node_ids):
            y_t = target_lookup[(int(feature_year), int(node_idx))]
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
                    "y_t": float(y_t),
                    "pred_persistence": float(y_t),
                }
            )
    return pd.DataFrame(rows)


def design_from_tensor(include_target_lag: bool, include_masks: bool) -> tuple[np.ndarray, list[str], dict]:
    tensor = np.load(TENSOR_PATH, allow_pickle=True)
    registry = pd.read_csv(FEATURE_REGISTRY_PATH)

    usable = registry[registry["has_train_observation"] == True].copy()
    excluded = registry[registry["has_train_observation"] != True].copy()
    feature_indices = usable["feature_idx"].to_numpy(dtype=int)
    feature_names = usable["feature_name"].tolist()

    x = tensor["x_scaled_imputed"][:, :, feature_indices].astype(float)
    x_mask = tensor["x_mask"][:, :, feature_indices].astype(float)
    sample_count, node_count, feature_count = x.shape

    parts = [x.reshape(sample_count * node_count, feature_count)]
    names = [f"x_{name}" for name in feature_names]

    if include_masks:
        parts.append(x_mask.reshape(sample_count * node_count, feature_count))
        names.extend([f"mask_{name}" for name in feature_names])

    if include_target_lag:
        base_frame = build_base_frame()
        y_t_log = np.log1p(base_frame["y_t"].to_numpy(dtype=float)).reshape(-1, 1)
        train_mask = base_frame["split"].to_numpy() == "train"
        mean = float(y_t_log[train_mask].mean())
        std = float(y_t_log[train_mask].std())
        if std == 0:
            std = 1.0
        y_t_scaled = (y_t_log - mean) / std
        parts.insert(0, y_t_scaled)
        names.insert(0, "log_y_t_scaled")

    design = np.hstack(parts)
    metadata = {
        "usable_feature_count": int(len(feature_names)),
        "excluded_no_train_observation": excluded["feature_name"].tolist(),
        "include_target_lag": include_target_lag,
        "include_masks": include_masks,
    }
    return design, names, metadata


def add_ridge_model(frame: pd.DataFrame, model_name: str, design: np.ndarray, feature_names: list[str]) -> tuple[pd.DataFrame, dict]:
    train_mask = frame["split"].to_numpy() == "train"
    validation_mask = frame["split"].to_numpy() == "validation"
    train_x = np.hstack([np.ones((train_mask.sum(), 1)), design[train_mask]])
    train_y = np.log1p(frame.loc[train_mask, "y_true"].to_numpy(dtype=float))
    validation_x = np.hstack([np.ones((validation_mask.sum(), 1)), design[validation_mask]])
    validation_y = frame.loc[validation_mask, "y_true"].to_numpy(dtype=float)

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
    full_design = np.hstack([np.ones((len(frame), 1)), design])
    pred = np.expm1(ridge_fit_predict(train_x, train_y, full_design, best_alpha)).clip(min=0.0)
    frame[f"pred_{model_name}"] = pred

    metadata = {
        "selected_alpha": best_alpha,
        "alpha_grid": [float(alpha) for alpha in RIDGE_ALPHA_GRID],
        "alpha_selection": alpha_scores,
        "feature_count": int(len(feature_names)),
        "feature_names": feature_names,
    }
    return frame, metadata


def evaluate() -> tuple[pd.DataFrame, dict]:
    frame = build_base_frame()

    model_specs = {
        "external_features": {"include_target_lag": False, "include_masks": True},
        "target_lag_plus_external_features": {"include_target_lag": True, "include_masks": True},
    }
    model_metadata = {}
    for model_name, spec in model_specs.items():
        design, feature_names, design_metadata = design_from_tensor(**spec)
        frame, ridge_metadata = add_ridge_model(frame, model_name, design, feature_names)
        model_metadata[model_name] = {**design_metadata, **ridge_metadata}

    model_cols = [
        "pred_persistence",
        "pred_external_features",
        "pred_target_lag_plus_external_features",
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
            "external_features": "ridge regression on observed external panel features and masks, excluding features with no train observation",
            "target_lag_plus_external_features": "ridge regression on y(t), external panel features and masks",
        },
        "model_metadata": model_metadata,
        "metrics": metrics,
        "interpretation": (
            "This baseline tests whether current panel features add predictive signal over local persistence. "
            "It is still annual and non-neural; it should be beaten before any graph-temporal architecture is interpreted."
        ),
    }
    return frame, quality


def write_report(quality: dict) -> None:
    lines = [
        "# Feature-Augmented Baseline Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- testar se features externas do painel adicionam sinal sobre a persistencia local",
        "- manter a avaliacao anual e sem arquitetura neural",
        "",
        "## Modelos",
        "",
        "- `persistence`: `y_hat(t+1) = y(t)`",
        "- `external_features`: ridge com features externas e mascaras",
        "- `target_lag_plus_external_features`: ridge com `y(t)`, features externas e mascaras",
        "",
        "## Regras",
        "",
        "- features sem observacao no treino sao excluidas",
        "- mascaras entram como controles explicitos de observacao",
        "- selecao de `alpha` usa validacao temporal",
        "- nenhuma estatistica de teste ou holdout entra no treino",
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

    for model_name, metadata in quality["model_metadata"].items():
        lines.append(f"## {model_name} metadata")
        lines.append("")
        lines.append(f"- alpha selecionado: `{metadata['selected_alpha']}`")
        lines.append(f"- numero de features no design: `{metadata['feature_count']}`")
        lines.append(f"- features excluidas por falta de observacao no treino: `{metadata['excluded_no_train_observation']}`")
        lines.append("")

    lines.extend(
        [
            "## Leitura",
            "",
            "- este baseline testa se as features externas ja integradas ajudam alem de `y(t)`",
            "- se nao houver ganho robusto sobre persistencia, a proxima etapa deve priorizar qualidade/profundidade das features antes de arquitetura",
            "- qualquer ganho precisa ser avaliado em validacao e teste, nao apenas no treino",
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
