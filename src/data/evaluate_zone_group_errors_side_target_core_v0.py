from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RICH_PRED = ROOT / "data" / "processed" / "side_target_baseline_predictions_core_v0.csv"
LONG_PRED = ROOT / "data" / "processed" / "long_history_side_target_baseline_predictions_core_v0.csv"
HYBRID_PRED = ROOT / "data" / "processed" / "controlled_hybrid_side_target_predictions_core_v0.csv"
TARGET_PANEL = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"

GROUP_METRICS_OUT = ROOT / "metadata" / "zone_group_error_metrics_side_target_core_v0.csv"
ZONE_PROFILE_OUT = ROOT / "metadata" / "zone_error_profile_side_target_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "zone_group_error_diagnostics_side_target_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "ZONE_GROUP_ERROR_DIAGNOSTICS_SIDE_TARGET_CORE_V0.md"


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = float(np.sum(np.abs(y_true)))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def classify_quantile(series: pd.Series, labels: list[str]) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, q=len(labels), labels=labels)


def build_zone_profile() -> pd.DataFrame:
    target = pd.read_csv(TARGET_PANEL, dtype={"ze2020": str})
    pivot = target.pivot(index=["node_idx", "ze2020", "libze2020"], columns="target_year", values="side_establishment_creations_official")
    pivot = pivot.reset_index()
    value_cols = [c for c in pivot.columns if isinstance(c, int)]
    pivot["target_mean_2012_2024"] = pivot[value_cols].mean(axis=1)
    pivot["target_std_2012_2024"] = pivot[value_cols].std(axis=1)
    pivot["target_cv_2012_2024"] = pivot["target_std_2012_2024"] / pivot["target_mean_2012_2024"].replace(0, np.nan)
    pivot["target_growth_2019_2024"] = (pivot[2024] - pivot[2019]) / pivot[2019].replace(0, np.nan)
    pivot["size_group"] = classify_quantile(
        pivot["target_mean_2012_2024"], ["small", "mid_low", "mid_high", "large"]
    )
    pivot["volatility_group"] = classify_quantile(
        pivot["target_cv_2012_2024"].fillna(0), ["low_vol", "mid_low_vol", "mid_high_vol", "high_vol"]
    )
    return pivot[
        [
            "node_idx",
            "ze2020",
            "libze2020",
            "target_mean_2012_2024",
            "target_cv_2012_2024",
            "target_growth_2019_2024",
            "size_group",
            "volatility_group",
        ]
    ]


def load_predictions(path: Path, package: str, model_cols: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"ze2020": str})
    rows = []
    for model_col in model_cols:
        if model_col not in frame.columns:
            continue
        sub = frame[
            ["feature_year", "target_year", "split", "node_idx", "ze2020", "libze2020", "y_true", model_col]
        ].copy()
        sub = sub.rename(columns={model_col: "y_pred"})
        sub["package"] = package
        sub["model"] = model_col.replace("pred_", "")
        rows.append(sub)
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    zone_profile = build_zone_profile()
    preds = pd.concat(
        [
            load_predictions(
                RICH_PRED,
                "rich_temporal",
                ["pred_persistence", "pred_ridge_autoregressive", "pred_spatial_blend"],
            ),
            load_predictions(
                LONG_PRED,
                "long_history",
                ["pred_persistence", "pred_ridge_autoregressive", "pred_spatial_blend"],
            ),
            load_predictions(
                HYBRID_PRED,
                "controlled_hybrid",
                [
                    "pred_persistence",
                    "pred_lags_only",
                    "pred_lags_plus_side_stocks",
                    "pred_lags_plus_side_stocks_flores",
                ],
            ),
        ],
        ignore_index=True,
    )
    preds = preds.merge(zone_profile, on=["node_idx", "ze2020", "libze2020"], how="left")
    preds["abs_error"] = (preds["y_true"] - preds["y_pred"]).abs()
    preds["ape"] = np.where(preds["y_true"] != 0, preds["abs_error"] / preds["y_true"] * 100.0, np.nan)

    group_rows = []
    for group_col in ["size_group", "volatility_group"]:
        for keys, group in preds.groupby(["package", "model", "split", group_col], dropna=False, observed=True):
            package, model, split, group_value = keys
            group_rows.append(
                {
                    "package": package,
                    "model": model,
                    "split": split,
                    "group_type": group_col,
                    "group": str(group_value),
                    "rows": int(len(group)),
                    "zones": int(group["ze2020"].nunique()),
                    "mae": mae(group["y_true"].to_numpy(float), group["y_pred"].to_numpy(float)),
                    "wmape": wmape(group["y_true"].to_numpy(float), group["y_pred"].to_numpy(float)),
                    "median_ape": float(group["ape"].median()),
                }
            )
    group_metrics = pd.DataFrame(group_rows).sort_values(["package", "model", "split", "group_type", "group"])

    worst_zones = (
        preds[(preds["package"] == "long_history") & (preds["model"] == "persistence") & (preds["split"] == "test")]
        .groupby(["ze2020", "libze2020", "size_group", "volatility_group"], as_index=False, observed=True)
        .agg(
            mean_abs_error=("abs_error", "mean"),
            mean_ape=("ape", "mean"),
            target_mean_2012_2024=("target_mean_2012_2024", "first"),
            target_cv_2012_2024=("target_cv_2012_2024", "first"),
        )
        .sort_values(["mean_abs_error", "mean_ape"], ascending=False)
        .head(20)
    )

    zone_profile.to_csv(ZONE_PROFILE_OUT, index=False)
    group_metrics.to_csv(GROUP_METRICS_OUT, index=False)

    quality = {
        "zone_profile": str(ZONE_PROFILE_OUT.relative_to(ROOT)),
        "group_metrics": str(GROUP_METRICS_OUT.relative_to(ROOT)),
        "packages_evaluated": sorted(preds["package"].unique().tolist()),
        "group_types": ["size_group", "volatility_group"],
        "worst_long_history_persistence_test_zones": worst_zones.to_dict(orient="records"),
        "main_conclusion": (
            "Group diagnostics identify whether persistence failures concentrate in large, small, or volatile zones. "
            "This should guide segmentation before adding more model complexity."
        ),
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(group_metrics, worst_zones, quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


def format_metric_rows(frame: pd.DataFrame, package: str, model: str, split: str, group_type: str) -> list[str]:
    sub = frame[
        (frame["package"] == package)
        & (frame["model"] == model)
        & (frame["split"] == split)
        & (frame["group_type"] == group_type)
    ].sort_values("group")
    rows = []
    for row in sub.itertuples(index=False):
        rows.append(f"| `{row.group}` | `{row.zones}` | `{row.wmape:.3f}` | `{row.mae:.3f}` | `{row.median_ape:.3f}` |")
    return rows


def write_report(group_metrics: pd.DataFrame, worst_zones: pd.DataFrame, quality: dict) -> None:
    lines = [
        "# Zone Group Error Diagnostics SIDE Target Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- verificar onde a persistencia falha",
        "- separar erro por tamanho e volatilidade das zonas",
        "- decidir se o proximo passo deve ser segmentacao territorial ou modelo mais complexo",
        "",
        "## Artefatos",
        "",
        f"- perfil das zonas: `{quality['zone_profile']}`",
        f"- metricas por grupo: `{quality['group_metrics']}`",
        "",
        "## Long History Persistence - Test Por Tamanho",
        "",
        "| grupo | zonas | WMAPE | MAE | mediana APE |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(format_metric_rows(group_metrics, "long_history", "persistence", "test", "size_group"))
    lines.extend(
        [
            "",
            "## Long History Persistence - Test Por Volatilidade",
            "",
            "| grupo | zonas | WMAPE | MAE | mediana APE |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    lines.extend(format_metric_rows(group_metrics, "long_history", "persistence", "test", "volatility_group"))

    lines.extend(
        [
            "",
            "## Piores Zonas No Teste",
            "",
            "| ZE2020 | zona | tamanho | volatilidade | MAE medio | APE medio |",
            "|---|---|---|---|---:|---:|",
        ]
    )
    for row in worst_zones.itertuples(index=False):
        lines.append(
            f"| `{row.ze2020}` | {row.libze2020} | `{row.size_group}` | `{row.volatility_group}` | `{row.mean_abs_error:.3f}` | `{row.mean_ape:.3f}` |"
        )

    lines.extend(
        [
            "",
            "## Leitura",
            "",
            "- se o erro estiver concentrado em zonas grandes, precisamos controlar escala e hubs economicos",
            "- se estiver concentrado em zonas pequenas/volateis, precisamos de robustez por grupo e talvez perdas ponderadas",
            "- esta etapa deve preceder qualquer STGNN, porque um modelo global pode apenas esconder erro territorial segmentado",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
