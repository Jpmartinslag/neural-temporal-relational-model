from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

TARGET_PANEL_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
LONG_DATASET_PATH = ROOT / "data" / "processed" / "long_history_side_target_dataset_core_v0.csv"
ADJACENCY_PATH = ROOT / "data" / "processed" / "graph_adjacency_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "segmented_decision_rule_backtest_predictions_core_v0.csv"
METRICS_OUT = ROOT / "metadata" / "segmented_decision_rule_backtest_metrics_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "segmented_decision_rule_backtest_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md"

TARGET_COL = "side_establishment_creations_official"
LAG_COUNT = 5
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0]
SPATIAL_ALPHA_GRID = np.linspace(0.0, 1.0, 21)
CANDIDATE_PREDICTIONS = {
    "persistence": "pred_persistence",
    "delta": "pred_delta",
    "moving_average_3": "pred_moving_average_3",
    "ridge_autoregressive": "pred_ridge_autoregressive_fold",
    "spatial_blend": "pred_spatial_blend_fold",
}
FOLD_VALIDATION_YEARS = [2020, 2021, 2022, 2023]


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def metric_block(frame: pd.DataFrame, pred_col: str) -> dict[str, float]:
    return {
        "wmape": wmape(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
        "mae": mae(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
        "rmse": rmse(frame["y_true"].to_numpy(dtype=float), frame[pred_col].to_numpy(dtype=float)),
        "rows": int(len(frame)),
        "zones": int(frame["ze2020"].nunique()),
    }


def ridge_fit_predict(train_x: np.ndarray, train_y: np.ndarray, pred_x: np.ndarray, alpha: float) -> np.ndarray:
    xtx = train_x.T @ train_x
    beta = np.linalg.pinv(xtx + alpha * np.eye(train_x.shape[1])) @ (train_x.T @ train_y)
    return pred_x @ beta


def design_matrix(frame: pd.DataFrame, medians: pd.Series, means: pd.Series, stds: pd.Series, feature_cols: list[str]) -> np.ndarray:
    x = frame[feature_cols].fillna(medians).fillna(0.0)
    x = (x - means) / stds
    x = x.replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=float)
    return np.hstack([np.ones((x.shape[0], 1)), x])


def add_fold_ridge_predictions(fold: pd.DataFrame, train: pd.DataFrame, validation: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    feature_cols = []
    fold = fold.copy()
    train = train.copy()
    validation = validation.copy()
    for lag in range(LAG_COUNT):
        col = f"log_y_lag_{lag}"
        for part in [fold, train, validation]:
            part[col] = np.log1p(part[f"y_lag_{lag}"].to_numpy(dtype=float))
        feature_cols.append(col)
    feature_cols += ["growth_1y", "growth_2y", "growth_3y"]

    medians = train[feature_cols].median(numeric_only=True).fillna(0.0)
    means = train[feature_cols].fillna(medians).mean().fillna(0.0)
    stds = train[feature_cols].fillna(medians).std().replace(0, 1.0).fillna(1.0)

    train_x = design_matrix(train, medians, means, stds, feature_cols)
    train_y = np.log1p(train["y_true"].to_numpy(dtype=float))
    validation_x = design_matrix(validation, medians, means, stds, feature_cols)
    validation_y = validation["y_true"].to_numpy(dtype=float)

    scores = []
    for alpha in RIDGE_ALPHA_GRID:
        pred_validation = np.expm1(ridge_fit_predict(train_x, train_y, validation_x, alpha)).clip(min=0.0)
        scores.append(
            {
                "alpha": float(alpha),
                "validation_wmape": wmape(validation_y, pred_validation),
                "validation_mae": mae(validation_y, pred_validation),
            }
        )
    best_alpha = float(pd.DataFrame(scores).sort_values(["validation_wmape", "validation_mae", "alpha"]).iloc[0]["alpha"])
    fold["pred_ridge_autoregressive_fold"] = np.expm1(
        ridge_fit_predict(train_x, train_y, design_matrix(fold, medians, means, stds, feature_cols), best_alpha)
    ).clip(min=0.0)
    return fold, {"selected_ridge_alpha": best_alpha, "ridge_alpha_selection": scores}


def add_fold_spatial_blend(fold: pd.DataFrame, validation: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    scores = []
    y_true = validation["y_true"].to_numpy(dtype=float)
    for alpha in SPATIAL_ALPHA_GRID:
        pred = alpha * validation["pred_persistence"] + (1.0 - alpha) * validation["pred_spatial_neighbor_average"]
        scores.append(
            {
                "alpha": float(alpha),
                "validation_wmape": wmape(y_true, pred.to_numpy(dtype=float)),
                "validation_mae": mae(y_true, pred.to_numpy(dtype=float)),
            }
        )
    best_alpha = float(pd.DataFrame(scores).sort_values(["validation_wmape", "validation_mae", "alpha"]).iloc[0]["alpha"])
    fold = fold.copy()
    fold["pred_spatial_blend_fold"] = (
        best_alpha * fold["pred_persistence"] + (1.0 - best_alpha) * fold["pred_spatial_neighbor_average"]
    )
    return fold, {"selected_spatial_alpha": best_alpha, "spatial_alpha_selection": scores}


def assign_quantile_group(series: pd.Series, labels: list[str]) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, q=len(labels), labels=labels, duplicates="drop").astype("string")


def build_fold_profile(target: pd.DataFrame, max_year: int) -> pd.DataFrame:
    history = target[target["target_year"] <= max_year].copy()
    profile = (
        history.groupby(["node_idx", "ze2020", "libze2020"], as_index=False)[TARGET_COL]
        .agg(["mean", "std"])
        .reset_index()
        .rename(columns={"mean": "profile_target_mean", "std": "profile_target_std"})
    )
    profile["profile_target_cv"] = (profile["profile_target_std"] / profile["profile_target_mean"].replace(0, np.nan)).fillna(0.0)
    profile["size_group"] = assign_quantile_group(profile["profile_target_mean"], ["small", "mid_low", "mid_high", "large"])
    profile["volatility_group"] = assign_quantile_group(profile["profile_target_cv"], ["low_vol", "mid_low_vol", "mid_high_vol", "high_vol"])
    profile["size_volatility_group"] = profile["size_group"].astype(str) + "__" + profile["volatility_group"].astype(str)
    return profile[["node_idx", "ze2020", "size_group", "volatility_group", "size_volatility_group"]]


def select_group_models(validation: pd.DataFrame, group_col: str) -> dict[str, str]:
    selections = {}
    for group_value, group_frame in validation.groupby(group_col, dropna=False, observed=True):
        scores = []
        for model_name, pred_col in CANDIDATE_PREDICTIONS.items():
            scores.append(
                {
                    "model": model_name,
                    "pred_col": pred_col,
                    "validation_wmape": wmape(group_frame["y_true"].to_numpy(dtype=float), group_frame[pred_col].to_numpy(dtype=float)),
                    "validation_mae": mae(group_frame["y_true"].to_numpy(dtype=float), group_frame[pred_col].to_numpy(dtype=float)),
                }
            )
        best = pd.DataFrame(scores).sort_values(["validation_wmape", "validation_mae", "model"]).iloc[0]
        selections[str(group_value)] = str(best["pred_col"])
    return selections


def apply_segmented_prediction(frame: pd.DataFrame, group_col: str, selections: dict[str, str]) -> pd.Series:
    return pd.Series(
        [row[selections.get(str(row[group_col]), "pred_persistence")] for _, row in frame.iterrows()],
        index=frame.index,
        dtype=float,
    )


def evaluate_fold(dataset: pd.DataFrame, target: pd.DataFrame, validation_year: int) -> tuple[pd.DataFrame, dict]:
    test_year = validation_year + 1
    train = dataset[dataset["target_year"] < validation_year].copy()
    validation = dataset[dataset["target_year"] == validation_year].copy()
    test = dataset[dataset["target_year"] == test_year].copy()
    fold = dataset[dataset["target_year"].isin([validation_year, test_year])].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError(f"Invalid fold for validation_year={validation_year}")

    profile = build_fold_profile(target, max_year=validation_year - 1)
    fold = fold.merge(profile, on=["node_idx", "ze2020"], how="left")
    validation = fold[fold["target_year"] == validation_year].copy()
    test = fold[fold["target_year"] == test_year].copy()

    fold, ridge_metadata = add_fold_ridge_predictions(fold, train, validation)
    validation = fold[fold["target_year"] == validation_year].copy()
    fold, spatial_metadata = add_fold_spatial_blend(fold, validation)
    validation = fold[fold["target_year"] == validation_year].copy()
    test = fold[fold["target_year"] == test_year].copy()

    segmentation_metadata = {}
    for group_col in ["size_group", "volatility_group", "size_volatility_group"]:
        selections = select_group_models(validation, group_col)
        pred_col = f"pred_segmented_{group_col}"
        selected_col = f"selected_model_{group_col}"
        fold[pred_col] = apply_segmented_prediction(fold, group_col, selections)
        fold[selected_col] = [selections.get(str(value), "pred_persistence").replace("pred_", "") for value in fold[group_col]]
        segmentation_metadata[group_col] = selections

    fold["fold_validation_year"] = validation_year
    fold["fold_role"] = np.where(fold["target_year"] == validation_year, "validation", "test")
    metadata = {
        "validation_year": validation_year,
        "test_year": test_year,
        "train_target_years": sorted(int(year) for year in train["target_year"].unique()),
        "ridge": ridge_metadata,
        "spatial": spatial_metadata,
        "segmentation": segmentation_metadata,
    }
    return fold, metadata


def summarize_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    model_cols = {
        "persistence": "pred_persistence",
        "ridge_autoregressive": "pred_ridge_autoregressive_fold",
        "spatial_blend": "pred_spatial_blend_fold",
        "segmented_size": "pred_segmented_size_group",
        "segmented_volatility": "pred_segmented_volatility_group",
        "segmented_size_volatility": "pred_segmented_size_volatility_group",
    }
    rows = []
    for fold_year, fold_frame in predictions.groupby("fold_validation_year"):
        for role, role_frame in fold_frame.groupby("fold_role"):
            for model_name, pred_col in model_cols.items():
                metrics = metric_block(role_frame, pred_col)
                rows.append(
                    {
                        "fold_validation_year": int(fold_year),
                        "target_role": role,
                        "model": model_name,
                        **metrics,
                    }
                )
    return pd.DataFrame(rows)


def build_report(metrics: pd.DataFrame, quality: dict) -> str:
    aggregate = (
        metrics.groupby(["target_role", "model"], as_index=False)
        .agg(wmape_mean=("wmape", "mean"), wmape_median=("wmape", "median"), folds=("fold_validation_year", "nunique"))
        .sort_values(["target_role", "wmape_mean", "model"])
    )
    lines = [
        "# Segmented Decision Rule Backtest Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- testar estabilidade temporal da regra segmentada",
        "- selecionar no ano de validacao e testar no ano seguinte",
        "- evitar salto prematuro para arquitetura grafo-temporal",
        "",
        "## Agregado Por Papel Temporal",
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
        "## Leitura",
        "",
        f"- melhor modelo medio no teste rolante: `{quality['best_test_mean_model']}`",
        f"- persistencia WMAPE medio no teste rolante: `{quality['persistence_test_wmape_mean']:.3f}`",
        f"- segmentacao tamanho+volatilidade WMAPE medio no teste rolante: `{quality['segmented_size_volatility_test_wmape_mean']:.3f}`",
        f"- conclusao: {quality['main_conclusion']}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    dataset = pd.read_csv(LONG_DATASET_PATH, dtype={"ze2020": str})
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})

    fold_predictions = []
    fold_metadata = []
    for validation_year in FOLD_VALIDATION_YEARS:
        fold_frame, metadata = evaluate_fold(dataset, target, validation_year)
        fold_predictions.append(fold_frame)
        fold_metadata.append(metadata)

    predictions = pd.concat(fold_predictions, ignore_index=True)
    metrics = summarize_metrics(predictions)
    test_metrics = metrics[metrics["target_role"] == "test"]
    mean_test = test_metrics.groupby("model", as_index=False)["wmape"].mean().sort_values(["wmape", "model"])
    best_test = mean_test.iloc[0]
    persistence_mean = float(mean_test[mean_test["model"] == "persistence"]["wmape"].iloc[0])
    segmented_mean = float(mean_test[mean_test["model"] == "segmented_size_volatility"]["wmape"].iloc[0])
    main_conclusion = (
        "a regra segmentada permanece candidata no backtest rolante"
        if segmented_mean < persistence_mean
        else "a regra segmentada nao supera a persistencia no backtest rolante"
    )
    quality = {
        "fold_validation_years": FOLD_VALIDATION_YEARS,
        "folds": fold_metadata,
        "rows": int(len(predictions)),
        "best_test_mean_model": str(best_test["model"]),
        "best_test_mean_wmape": float(best_test["wmape"]),
        "persistence_test_wmape_mean": persistence_mean,
        "segmented_size_volatility_test_wmape_mean": segmented_mean,
        "main_conclusion": main_conclusion,
    }

    PRED_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PRED_OUT, index=False)
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
                "best_test_mean_wmape": quality["best_test_mean_wmape"],
                "main_conclusion": quality["main_conclusion"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
