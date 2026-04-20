from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TARGET_MONTHLY_PATH = ROOT / "data" / "processed" / "target_proxy_candidate_core_v0.csv"
PRE_STGNN_PATH = ROOT / "data" / "processed" / "pre_stgnn_dataset_core_v0.csv"

TARGET_ANNUAL_OUT = ROOT / "data" / "processed" / "target_proxy_annual_core_v0.csv"
BASELINE_OUT = ROOT / "data" / "processed" / "baseline_annual_dataset_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "baseline_annual_target_core_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "BASELINE_ANNUAL_TARGET_CORE_V0.md"


def build_target_annual() -> pd.DataFrame:
    monthly = pd.read_csv(TARGET_MONTHLY_PATH, dtype={"ze2020": str})
    monthly["target_year"] = monthly["year_month"].str.slice(0, 4).astype(int)
    annual = (
        monthly.groupby(["target_year", "ze2020"], as_index=False)["target_proxy_establishment_creations_count"]
        .sum()
        .rename(columns={"target_proxy_establishment_creations_count": "target_proxy_establishment_creations_year"})
        .sort_values(["target_year", "ze2020"])
        .reset_index(drop=True)
    )
    return annual


def build_baseline_dataset(annual_target: pd.DataFrame) -> pd.DataFrame:
    features = pd.read_csv(PRE_STGNN_PATH, dtype={"ze2020": str})
    features = features.rename(columns={"year": "feature_year"})
    target_next = annual_target.rename(
        columns={
            "target_year": "target_year",
            "target_proxy_establishment_creations_year": "target_proxy_establishment_creations_tplus1",
        }
    )
    features["target_year"] = features["feature_year"] + 1
    baseline = features.merge(target_next, on=["ze2020", "target_year"], how="left")
    baseline["has_target_tplus1"] = baseline["target_proxy_establishment_creations_tplus1"].notna().astype(int)
    return baseline


def write_report(annual_target: pd.DataFrame, baseline: pd.DataFrame, quality: dict) -> None:
    totals = (
        annual_target.groupby("target_year")["target_proxy_establishment_creations_year"]
        .sum()
        .reset_index()
        .sort_values("target_year")
    )
    lines = [
        "# Baseline Annual Target Core v0",
        "",
        "Data: 2026-04-09",
        "",
        "Objetivo:",
        "",
        "- alinhar o target proxy mensal a um recorte anual coerente com o painel atual",
        "",
        "## Regra de alinhamento",
        "",
        "- features observadas em `t`",
        "- target observado em `t+1`",
        "- isso produz um primeiro dataset de baseline anual sem forcar mensalizacao artificial das features",
        "",
        "## Cobertura",
        "",
        f"- linhas do target anual: `{quality['annual_target_rows']}`",
        f"- anos do target anual: `{quality['annual_target_min_year']} -> {quality['annual_target_max_year']}`",
        f"- zonas no target anual: `{quality['annual_target_zones']}`",
        f"- linhas do baseline anual: `{quality['baseline_rows']}`",
        f"- linhas com `target_tplus1`: `{quality['baseline_rows_with_target_tplus1']}`",
        f"- anos de feature no baseline: `{quality['baseline_feature_min_year']} -> {quality['baseline_feature_max_year']}`",
        "",
        "## Totais anuais do target proxy",
        "",
    ]
    for row in totals.itertuples(index=False):
        lines.append(f"- `{row.target_year}`: `{int(row.target_proxy_establishment_creations_year)}` criacoes")
    REPORT_OUT.write_text("\n".join(lines) + "\n")


def main() -> None:
    annual_target = build_target_annual()
    baseline = build_baseline_dataset(annual_target)

    annual_target.to_csv(TARGET_ANNUAL_OUT, index=False)
    baseline.to_csv(BASELINE_OUT, index=False)

    quality = {
        "annual_target_rows": int(len(annual_target)),
        "annual_target_zones": int(annual_target["ze2020"].nunique()),
        "annual_target_min_year": int(annual_target["target_year"].min()),
        "annual_target_max_year": int(annual_target["target_year"].max()),
        "baseline_rows": int(len(baseline)),
        "baseline_rows_with_target_tplus1": int(baseline["has_target_tplus1"].sum()),
        "baseline_feature_min_year": int(baseline["feature_year"].min()),
        "baseline_feature_max_year": int(baseline["feature_year"].max()),
        "baseline_target_min_year": int(baseline["target_year"].min()),
        "baseline_target_max_year": int(baseline["target_year"].max()),
        "target_column": "target_proxy_establishment_creations_tplus1",
        "baseline_definition": "annual_features_t_to_annual_target_tplus1",
    }
    pd.Series(quality).to_json(QUALITY_OUT, indent=2)
    write_report(annual_target, baseline, quality)
    print(quality)


if __name__ == "__main__":
    main()
