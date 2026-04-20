from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RICH_BASELINE_METRICS = ROOT / "reports" / "side_target_baseline_metrics_core_v0.json"
RICH_FEATURE_METRICS = ROOT / "reports" / "feature_augmented_baseline_side_target_metrics_core_v0.json"
LONG_METRICS = ROOT / "reports" / "long_history_side_target_baseline_metrics_core_v0.json"
AVAILABILITY = ROOT / "metadata" / "feature_temporal_availability_core_v0.csv"

COMPARISON_CSV = ROOT / "metadata" / "rich_vs_long_side_target_comparison_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "rich_vs_long_side_target_comparison_core_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "RICH_VS_LONG_SIDE_TARGET_COMPARISON_CORE_V0.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_row(package: str, model: str, split: str, values: dict) -> dict:
    return {
        "package": package,
        "model": model,
        "split": split,
        "mae": values["mae"],
        "rmse": values["rmse"],
        "mape": values["mape"],
        "wmape": values["wmape"],
    }


def flatten_metrics(package: str, metrics: dict) -> list[dict]:
    rows = []
    for model, split_metrics in metrics.items():
        for split, values in split_metrics.items():
            rows.append(metric_row(package, model, split, values))
    return rows


def best_by_split(frame: pd.DataFrame, package: str, split: str) -> dict:
    sub = frame[(frame["package"] == package) & (frame["split"] == split)].copy()
    if sub.empty:
        return {}
    row = sub.sort_values(["wmape", "mae", "model"]).iloc[0]
    return {
        "package": package,
        "split": split,
        "model": row["model"],
        "wmape": float(row["wmape"]),
        "mae": float(row["mae"]),
    }


def main() -> None:
    rich = load_json(RICH_BASELINE_METRICS)
    rich_features = load_json(RICH_FEATURE_METRICS)
    long = load_json(LONG_METRICS)
    availability = pd.read_csv(AVAILABILITY)

    rows = []
    rows.extend(flatten_metrics("rich_temporal_baselines", rich["metrics"]))
    rows.extend(flatten_metrics("rich_feature_augmented", rich_features["metrics"]))
    rows.extend(flatten_metrics("long_history_side_lags", long["metrics"]))
    comparison = pd.DataFrame(rows).sort_values(["package", "split", "wmape", "model"])
    comparison.to_csv(COMPARISON_CSV, index=False)

    best = [
        best_by_split(comparison, "rich_temporal_baselines", "validation"),
        best_by_split(comparison, "rich_temporal_baselines", "test"),
        best_by_split(comparison, "rich_feature_augmented", "validation"),
        best_by_split(comparison, "rich_feature_augmented", "test"),
        best_by_split(comparison, "long_history_side_lags", "validation"),
        best_by_split(comparison, "long_history_side_lags", "test"),
    ]
    best = [row for row in best if row]

    feature_depth = availability[
        availability["feature_name"].isin(
            ["side_creations_et_total", "side_stocks_et_total", "side_stocks_ul_total", "flores_et_total"]
        )
    ][
        [
            "feature_name",
            "role",
            "observed_years_core",
            "observed_year_count_core",
            "train_observed_count_tensor",
            "notes",
        ]
    ].to_dict(orient="records")

    quality = {
        "comparison_file": str(COMPARISON_CSV.relative_to(ROOT)),
        "packages": {
            "rich_temporal_baselines": {
                "sample_count": rich["sample_count"],
                "split_counts": rich["split_counts"],
                "purpose": "shorter annual window, official SIDE target, temporal/spatial baselines",
            },
            "rich_feature_augmented": {
                "sample_count": rich_features["sample_count"],
                "purpose": "same rich window plus current external features and masks",
            },
            "long_history_side_lags": {
                "sample_count": long["sample_count"],
                "split_counts": long["split_counts"],
                "purpose": "longer supervised window using only official SIDE target history",
            },
        },
        "best_by_package_split": best,
        "feature_depth_highlights": feature_depth,
        "main_conclusion": (
            "Persistence remains the validation winner in both rich and long packages. "
            "The long package improves test stability but uses only target history. "
            "Current feature augmentation is not robust and should be replaced by a controlled hybrid feature set."
        ),
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


def write_report(quality: dict) -> None:
    lines = [
        "# Rich vs Long SIDE Target Comparison Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- comparar o pacote rico e o pacote longo com target oficial `SIDE`",
        "- evitar misturar profundidade de features com numero de anos supervisionados",
        "- definir o proximo baseline controlado",
        "",
        "## Pacotes",
        "",
        "| pacote | amostras | splits | papel |",
        "|---|---:|---|---|",
    ]
    for package, meta in quality["packages"].items():
        lines.append(
            f"| `{package}` | `{meta.get('sample_count', '')}` | `{meta.get('split_counts', '')}` | {meta['purpose']} |"
        )

    lines.extend(
        [
            "",
            "## Melhores Resultados Por Pacote",
            "",
            "| pacote | split | melhor modelo | WMAPE | MAE |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in quality["best_by_package_split"]:
        lines.append(
            f"| `{row['package']}` | `{row['split']}` | `{row['model']}` | `{row['wmape']:.3f}` | `{row['mae']:.3f}` |"
        )

    lines.extend(
        [
            "",
            "## Features Relevantes Para Um Hibrido Controlado",
            "",
            "| feature | papel | anos observados | obs treino | nota |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in quality["feature_depth_highlights"]:
        lines.append(
            f"| `{row['feature_name']}` | `{row['role']}` | `{row['observed_years_core']}` | `{row['train_observed_count_tensor']}` | {row['notes']} |"
        )

    lines.extend(
        [
            "",
            "## Leitura",
            "",
            "- o pacote rico preserva as features adicionadas e deve ser usado para testar covariaveis",
            "- o pacote longo aumenta anos supervisionados, mas mede memoria temporal do proprio alvo",
            "- a persistencia continua sendo o benchmark decisivo na validacao",
            "- features externas amplas continuam fracas quando entram todas juntas",
            "",
            "## Proximo Passo",
            "",
            "- construir um baseline hibrido controlado",
            "- usar `SIDE` lags como base temporal",
            "- adicionar poucas features com boa cobertura: `side_stocks_et_total`, `side_stocks_ul_total`, `flores_et_total`",
            "- manter `side_creations_et_total` explicitamente rotulado como target-history lag",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
