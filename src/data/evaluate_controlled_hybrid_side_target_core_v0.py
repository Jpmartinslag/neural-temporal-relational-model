from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
TARGET_PANEL_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "controlled_hybrid_side_target_predictions_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "controlled_hybrid_side_target_metrics_core_v0.json"
QUALITY_OUT = ROOT / "reports" / "controlled_hybrid_side_target_quality_core_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "CONTROLLED_HYBRID_SIDE_TARGET_CORE_V0.md"

TARGET_COL = "side_establishment_creations_official"
LAG_COUNT = 5
RIDGE_ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
FEATURE_GROUPS = {
    "lags_only": [],
    "lags_plus_side_stocks": ["side_stocks_et_total", "side_stocks_ul_total"],
    "lags_plus_side_stocks_flores": ["side_stocks_et_total", "side_stocks_ul_total", "flores_et_total"],
}


def split_for_target_year(target_year: int) -> str:
    if target_year <= 2022:
        return "train"
    if target_year == 2023:
        return "validation"
    if target_year == 2024:
        return "test"
    return "forecast_holdout"


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


def build_frame() -> pd.DataFrame:
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str}).sort_values("node_idx")

    target_lookup = {
        (int(row.target_year), int(row.node_idx)): float(getattr(row, TARGET_COL))
        for row in target.itertuples(index=False)
    }
    panel_lookup = {
        (int(row.year), str(row.ze2020)): row._asdict()
        for row in panel.itertuples(index=False)
    }
    target_years = sorted(int(y) for y in target["target_year"].unique())
    feature_years = [2019, 2020, 2021, 2022, 2023]

    rows = []
    for feature_year in feature_years:
        target_year = feature_year + 1
        if target_year not in target_years:
            continue
        required_lag_years = [feature_year - lag for lag in range(LAG_COUNT)]
        if any(year not in target_years for year in required_lag_years):
            continue
        for node in nodes.itertuples(index=False):
            node_idx = int(node.node_idx)
            ze2020 = str(node.ze2020)
            lag_values = [target_lookup[(feature_year - lag, node_idx)] for lag in range(LAG_COUNT)]
            y_true = target_lookup[(target_year, node_idx)]
            panel_row = panel_lookup.get((feature_year, ze2020), {})
            row = {
                "feature_year": feature_year,
                "target_year": target_year,
                "split": split_for_target_year(target_year),
                "node_idx": node_idx,
                "ze2020": ze2020,
                "libze2020": node.libze2020,
                "y_true": y_true,
                "pred_persistence": lag_values[0],
                "growth_1y": safe_growth(lag_values[0], lag_values[1]),
                "growth_2y": safe_growth(lag_values[0], lag_values[2]),
                "growth_3y": safe_growth(lag_values[0], lag_values[3]),
            }
            for lag, value in enumerate(lag_values):
                row[f"y_lag_{lag}"] = value
            for feature in sorted({f for features in FEATURE_GROUPS.values() for f in features}):
                value = panel_row.get(feature, np.nan)
                row[feature] = pd.to_numeric(value, errors="coerce")
                row[f"mask_{feature}"] = float(pd.notna(row[feature]))
            rows.append(row)
    return pd.DataFrame(rows)


def design_matrix(frame: pd.DataFrame, feature_group: list[str], train_mask: np.ndarray) -> tuple[np.ndarray, list[str], dict]:
    design = pd.DataFrame(index=frame.index)
    feature_names = []
    for lag in range(LAG_COUNT):
        col = f"log_y_lag_{lag}"
        design[col] = np.log1p(frame[f"y_lag_{lag}"].to_numpy(dtype=float))
        feature_names.append(col)
    for col in ["growth_1y", "growth_2y", "growth_3y"]:
        design[col] = frame[col].to_numpy(dtype=float)
        feature_names.append(col)

    coverage = {}
    train = frame.loc[train_mask]
    for feature in feature_group:
        observed_train = train[feature].dropna()
        coverage[feature] = {
            "train_observed_count": int(observed_train.shape[0]),
            "all_observed_count": int(frame[feature].notna().sum()),
        }
        transformed = np.log1p(frame[feature].to_numpy(dtype=float))
        design[f"log_{feature}"] = transformed
        design[f"mask_{feature}"] = frame[f"mask_{feature}"].to_numpy(dtype=float)
        feature_names.extend([f"log_{feature}", f"mask_{feature}"])

    train_design = design.loc[train_mask]
    medians = train_design.median(numeric_only=True).fillna(0.0)
    means = train_design.fillna(medians).mean().fillna(0.0)
    stds = train_design.fillna(medians).std().replace(0, 1.0).fillna(1.0)

    x = design.fillna(medians).fillna(0.0)
    x = (x - means) / stds
    x = x.replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=float)
    x = np.hstack([np.ones((x.shape[0], 1)), x])
    metadata = {
        "feature_group": feature_group,
        "design_feature_names": feature_names,
        "coverage": coverage,
        "scaling_scope": "train_split_only",
    }
    return x, feature_names, metadata


def add_model(frame: pd.DataFrame, model_name: str, feature_group: list[str]) -> tuple[pd.DataFrame, dict]:
    train_mask = frame["split"].to_numpy() == "train"
    validation_mask = frame["split"].to_numpy() == "validation"
    x, _, metadata = design_matrix(frame, feature_group, train_mask)
    train_x = x[train_mask]
    train_y = np.log1p(frame.loc[train_mask, "y_true"].to_numpy(dtype=float))
    validation_x = x[validation_mask]
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
    frame = frame.copy()
    frame[f"pred_{model_name}"] = np.expm1(ridge_fit_predict(train_x, train_y, x, best_alpha)).clip(min=0.0)
    metadata.update(
        {
            "selected_alpha": best_alpha,
            "alpha_grid": [float(alpha) for alpha in RIDGE_ALPHA_GRID],
            "alpha_selection": alpha_scores,
        }
    )
    return frame, metadata


def evaluate() -> tuple[pd.DataFrame, dict]:
    frame = build_frame()
    model_metadata = {}
    for model_name, feature_group in FEATURE_GROUPS.items():
        frame, metadata = add_model(frame, model_name, feature_group)
        model_metadata[model_name] = metadata

    model_cols = ["pred_persistence"] + [f"pred_{name}" for name in FEATURE_GROUPS]
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
            "lags_only": "ridge on official SIDE target lags and growth",
            "lags_plus_side_stocks": "lags plus SIDE stock ET/UL features and masks",
            "lags_plus_side_stocks_flores": "lags plus SIDE stock ET/UL and FLORES ET features and masks",
        },
        "model_metadata": model_metadata,
        "metrics": metrics,
        "interpretation": (
            "This controlled hybrid tests a small, high-coverage feature set instead of all available external features."
        ),
    }
    return frame, quality


def write_report(quality: dict) -> None:
    lines = [
        "# Controlled Hybrid SIDE Target Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- testar um hibrido controlado entre lags `SIDE` e poucas features de boa cobertura",
        "- evitar o baseline amplo que misturava todas as features externas",
        "",
        "## Estrutura",
        "",
        f"- target: `{quality['target_column']}`",
        f"- amostras anuais: `{quality['sample_count']}`",
        f"- feature years: `{quality['feature_years']}`",
        f"- target years: `{quality['target_years']}`",
        f"- splits: `{quality['split_counts']}`",
        "",
        "## Modelos",
        "",
        "- `persistence`: persistencia local",
        "- `lags_only`: 5 lags oficiais `SIDE` + crescimentos recentes",
        "- `lags_plus_side_stocks`: lags + `side_stocks_et_total`, `side_stocks_ul_total`",
        "- `lags_plus_side_stocks_flores`: lags + SIDE stocks + `flores_et_total`",
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
            "- o teste e conservador: poucas features, com mascaras explicitas",
            "- um hibrido so sera aceito se bater persistencia na validacao e nao degradar teste",
            "- `side_creations_et_total` permanece tratado como lag/historico do target, nao covariavel externa independente",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    pred, quality = evaluate()
    pred.to_csv(PRED_OUT, index=False)
    METRICS_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    QUALITY_OUT.write_text(
        json.dumps({k: v for k, v in quality.items() if k != "metrics"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
