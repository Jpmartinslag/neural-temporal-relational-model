from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

TARGET_PANEL_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
LONG_PRED_PATH = ROOT / "data" / "processed" / "long_history_side_target_baseline_predictions_core_v0.csv"

PRED_OUT = ROOT / "data" / "processed" / "segmented_side_target_predictions_core_v0.csv"
PROFILE_OUT = ROOT / "metadata" / "segmented_zone_profile_side_target_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "segmented_side_target_metrics_core_v0.json"
QUALITY_OUT = ROOT / "reports" / "segmented_side_target_quality_core_v0.json"
REPORT_OUT = ROOT / "reports" / "SEGMENTED_SIDE_TARGET_BASELINE_CORE_V0.md"

TARGET_COL = "side_establishment_creations_official"
PROFILE_HISTORY_MAX_YEAR = 2021
CANDIDATE_PREDICTIONS = {
    "persistence": "pred_persistence",
    "delta": "pred_delta",
    "moving_average_3": "pred_moving_average_3",
    "ridge_autoregressive": "pred_ridge_autoregressive",
    "spatial_blend": "pred_spatial_blend",
}


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
        "rows": int(len(frame)),
        "zones": int(frame["ze2020"].nunique()),
    }


def assign_quantile_group(series: pd.Series, labels: list[str]) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, q=len(labels), labels=labels, duplicates="drop").astype("string")


def build_train_scope_profile() -> pd.DataFrame:
    target = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    history = target[target["target_year"] <= PROFILE_HISTORY_MAX_YEAR].copy()
    profile = (
        history.groupby(["node_idx", "ze2020", "libze2020"], as_index=False)[TARGET_COL]
        .agg(["mean", "std"])
        .reset_index()
        .rename(columns={"mean": "profile_target_mean_train_scope", "std": "profile_target_std_train_scope"})
    )
    profile["profile_target_cv_train_scope"] = (
        profile["profile_target_std_train_scope"] / profile["profile_target_mean_train_scope"].replace(0, np.nan)
    ).fillna(0.0)

    first_last = (
        history.sort_values(["node_idx", "target_year"])
        .groupby(["node_idx", "ze2020", "libze2020"], as_index=False)
        .agg(first_year=("target_year", "first"), last_year=("target_year", "last"), first_value=(TARGET_COL, "first"), last_value=(TARGET_COL, "last"))
    )
    profile = profile.merge(first_last, on=["node_idx", "ze2020", "libze2020"], how="left")
    profile["profile_growth_train_scope"] = (
        (profile["last_value"] - profile["first_value"]) / profile["first_value"].replace(0, np.nan)
    ).fillna(0.0)

    profile["size_group_train_scope"] = assign_quantile_group(
        profile["profile_target_mean_train_scope"],
        ["small", "mid_low", "mid_high", "large"],
    )
    profile["volatility_group_train_scope"] = assign_quantile_group(
        profile["profile_target_cv_train_scope"],
        ["low_vol", "mid_low_vol", "mid_high_vol", "high_vol"],
    )
    profile["size_volatility_group_train_scope"] = (
        profile["size_group_train_scope"].astype(str) + "__" + profile["volatility_group_train_scope"].astype(str)
    )
    return profile


def select_models_by_group(frame: pd.DataFrame, group_col: str) -> tuple[pd.DataFrame, dict]:
    validation = frame[frame["split"] == "validation"].copy()
    selections = []
    for group_value, group_frame in validation.groupby(group_col, dropna=False, observed=True):
        group_name = str(group_value)
        scores = []
        for model_name, pred_col in CANDIDATE_PREDICTIONS.items():
            scores.append(
                {
                    "group": group_name,
                    "model": model_name,
                    "pred_col": pred_col,
                    "validation_wmape": wmape(
                        group_frame["y_true"].to_numpy(dtype=float),
                        group_frame[pred_col].to_numpy(dtype=float),
                    ),
                    "validation_mae": mae(
                        group_frame["y_true"].to_numpy(dtype=float),
                        group_frame[pred_col].to_numpy(dtype=float),
                    ),
                    "validation_rows": int(len(group_frame)),
                    "validation_zones": int(group_frame["ze2020"].nunique()),
                }
            )
        best = pd.DataFrame(scores).sort_values(["validation_wmape", "validation_mae", "model"]).iloc[0].to_dict()
        selections.append(best)

    selection_frame = pd.DataFrame(selections)
    selection_map = dict(zip(selection_frame["group"], selection_frame["pred_col"]))
    model_map = dict(zip(selection_frame["group"], selection_frame["model"]))

    pred_col_name = f"pred_segmented_by_{group_col.replace('_train_scope', '')}"
    model_col_name = f"selected_model_by_{group_col.replace('_train_scope', '')}"
    out = frame.copy()
    out[pred_col_name] = [
        row[selection_map.get(str(row[group_col]), "pred_persistence")]
        for _, row in out.iterrows()
    ]
    out[model_col_name] = [model_map.get(str(value), "persistence") for value in out[group_col]]
    return out, {
        "group_col": group_col,
        "prediction_col": pred_col_name,
        "selected_model_col": model_col_name,
        "selections": selection_frame.to_dict(orient="records"),
    }


def evaluate_predictions(frame: pd.DataFrame, prediction_cols: dict[str, str]) -> dict:
    metrics: dict[str, dict] = {}
    for model_name, pred_col in prediction_cols.items():
        metrics[model_name] = {}
        for split in ["train", "validation", "test"]:
            split_frame = frame[frame["split"] == split]
            if split_frame.empty:
                continue
            metrics[model_name][split] = metric_block(split_frame, pred_col)
    return metrics


def build_report(metrics: dict, metadata: dict) -> str:
    lines = [
        "# Segmented SIDE Target Baseline Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- testar se escolher modelos diferentes por perfil de zona melhora a persistencia",
        "- evitar vazamento: os grupos usam apenas historico ate 2021",
        "- decidir se segmentacao territorial deve vir antes de STGNN",
        "",
        "## Escopo",
        "",
        f"- perfil das zonas calculado com `target_year <= {PROFILE_HISTORY_MAX_YEAR}`",
        "- selecao de modelo feita na validacao",
        "- teste permanece fora da selecao",
        "",
        "## Metricas Principais",
        "",
        "| modelo | validation WMAPE | test WMAPE | test MAE |",
        "|---|---:|---:|---:|",
    ]
    for model_name, split_metrics in metrics.items():
        if "validation" not in split_metrics or "test" not in split_metrics:
            continue
        lines.append(
            "| `{}` | `{:.3f}` | `{:.3f}` | `{:.3f}` |".format(
                model_name,
                split_metrics["validation"]["wmape"],
                split_metrics["test"]["wmape"],
                split_metrics["test"]["mae"],
            )
        )

    lines += [
        "",
        "## Selecoes Por Grupo",
        "",
    ]
    for item in metadata["segmentation"]:
        lines.append(f"### {item['group_col']}")
        lines.append("")
        lines.append("| grupo | modelo selecionado | validation WMAPE | zonas |")
        lines.append("|---|---|---:|---:|")
        for row in item["selections"]:
            lines.append(
                "| `{}` | `{}` | `{:.3f}` | `{}` |".format(
                    row["group"],
                    row["model"],
                    row["validation_wmape"],
                    row["validation_zones"],
                )
            )
        lines.append("")

    best_validation = min(
        ((name, values["validation"]["wmape"]) for name, values in metrics.items() if "validation" in values),
        key=lambda item: item[1],
    )
    best_test = min(
        ((name, values["test"]["wmape"]) for name, values in metrics.items() if "test" in values),
        key=lambda item: item[1],
    )
    lines += [
        "## Leitura",
        "",
        f"- melhor validacao: `{best_validation[0]}` com WMAPE `{best_validation[1]:.3f}`",
        f"- melhor teste: `{best_test[0]}` com WMAPE `{best_test[1]:.3f}`",
        "- se a segmentacao nao vencer na validacao, ela fica como diagnostico e nao como novo baseline principal",
        "- se vencer apenas no teste, o resultado e hipotese, nao evidencia suficiente para substituir persistencia",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    profile = build_train_scope_profile()
    preds = pd.read_csv(LONG_PRED_PATH, dtype={"ze2020": str})
    frame = preds.merge(
        profile[
            [
                "node_idx",
                "ze2020",
                "size_group_train_scope",
                "volatility_group_train_scope",
                "size_volatility_group_train_scope",
            ]
        ],
        on=["node_idx", "ze2020"],
        how="left",
    )

    metadata = {
        "profile_history_max_year": PROFILE_HISTORY_MAX_YEAR,
        "candidate_predictions": CANDIDATE_PREDICTIONS,
        "segmentation": [],
    }
    prediction_cols = {
        "persistence": "pred_persistence",
        "ridge_autoregressive": "pred_ridge_autoregressive",
        "moving_average_3": "pred_moving_average_3",
    }
    for group_col in [
        "size_group_train_scope",
        "volatility_group_train_scope",
        "size_volatility_group_train_scope",
    ]:
        frame, selection_metadata = select_models_by_group(frame, group_col)
        metadata["segmentation"].append(selection_metadata)
        prediction_cols[selection_metadata["prediction_col"].replace("pred_", "")] = selection_metadata["prediction_col"]

    metrics = evaluate_predictions(frame, prediction_cols)
    quality = {
        **metadata,
        "rows": int(len(frame)),
        "zones": int(frame["ze2020"].nunique()),
        "target_years": sorted(int(year) for year in frame["target_year"].unique()),
        "splits": {split: int(count) for split, count in frame["split"].value_counts().sort_index().items()},
        "metrics": metrics,
        "main_conclusion": "Segmented baselines are valid only if they beat persistence on validation; test-only improvements are treated as hypotheses.",
    }

    PRED_OUT.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PRED_OUT, index=False)
    profile.to_csv(PROFILE_OUT, index=False)
    METRICS_OUT.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    QUALITY_OUT.write_text(json.dumps(quality, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(metrics, metadata), encoding="utf-8")
    print(
        json.dumps(
            {
                "predictions": str(PRED_OUT.relative_to(ROOT)),
                "profile": str(PROFILE_OUT.relative_to(ROOT)),
                "metrics": str(METRICS_OUT.relative_to(ROOT)),
                "report": str(REPORT_OUT.relative_to(ROOT)),
                "best_validation": min(
                    (
                        {"model": name, "wmape": values["validation"]["wmape"]}
                        for name, values in metrics.items()
                        if "validation" in values
                    ),
                    key=lambda item: item["wmape"],
                ),
                "best_test": min(
                    (
                        {"model": name, "wmape": values["test"]["wmape"]}
                        for name, values in metrics.items()
                        if "test" in values
                    ),
                    key=lambda item: item["wmape"],
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
