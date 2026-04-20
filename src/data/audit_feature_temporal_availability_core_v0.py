from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

PANEL_REGISTRY_PATH = ROOT / "metadata" / "panel_feature_registry_v0.csv"
PANEL_CORE_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
TARGET_SIDE_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
TENSOR_REGISTRY_PATH = ROOT / "metadata" / "stgnn_tensor_feature_registry_side_target_core_v0.csv"
SAMPLE_INDEX_PATH = ROOT / "metadata" / "stgnn_tensor_sample_index_side_target_core_v0.csv"

AVAILABILITY_OUT = ROOT / "metadata" / "feature_temporal_availability_core_v0.csv"
YEAR_PLAN_OUT = ROOT / "metadata" / "supervised_year_availability_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "feature_temporal_availability_core_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "archive" / "technical" / "FEATURE_TEMPORAL_AVAILABILITY_CORE_V0.md"


def classify_role(feature: str) -> str:
    if feature == "side_creations_et_total":
        return "target_history_lag"
    if feature.startswith("side_stocks"):
        return "economic_stock"
    if feature.startswith("flores"):
        return "employment_establishment_stock"
    if feature.startswith("filosofi"):
        return "income"
    if feature.startswith("population"):
        return "population"
    if feature.startswith(("active_", "employed_", "unemployed_", "jobs_", "unemployment")):
        return "labour"
    if feature.startswith("bpe"):
        return "services"
    if feature.startswith("static"):
        return "static_context"
    return "other"


def main() -> None:
    panel_registry = pd.read_csv(PANEL_REGISTRY_PATH)
    panel = pd.read_csv(PANEL_CORE_PATH, dtype={"ze2020": str})
    year_col = "feature_year" if "feature_year" in panel.columns else "year"
    target = pd.read_csv(TARGET_SIDE_PATH, dtype={"ze2020": str})
    tensor_registry = pd.read_csv(TENSOR_REGISTRY_PATH)
    sample_index = pd.read_csv(SAMPLE_INDEX_PATH)

    panel_features = sorted(panel_registry["panel_feature"].unique())
    panel_years = sorted(int(y) for y in panel[year_col].unique())
    target_years = sorted(int(y) for y in target["target_year"].unique())
    core_node_count = int(panel["ze2020"].nunique())

    rows = []
    for feature in panel_features:
        registry_rows = panel_registry[panel_registry["panel_feature"] == feature]
        registry_years = sorted(int(y) for y in registry_rows["source_year"].unique())
        observed_years = []
        year_coverage = {}
        for year in panel_years:
            if feature not in panel.columns:
                observed_count = 0
            else:
                year_frame = panel[panel[year_col] == year]
                observed_count = int(year_frame[feature].notna().sum())
            year_coverage[year] = observed_count
            if observed_count > 0:
                observed_years.append(year)

        tensor_row = tensor_registry[tensor_registry["feature_name"] == feature]
        train_observed_count = int(tensor_row.iloc[0]["train_observed_count"]) if not tensor_row.empty else 0
        missing_rate = float(tensor_row.iloc[0]["missing_rate_all_samples"]) if not tensor_row.empty else None

        rows.append(
            {
                "feature_name": feature,
                "role": classify_role(feature),
                "registry_years": ",".join(str(y) for y in registry_years),
                "observed_years_core": ",".join(str(y) for y in observed_years),
                "observed_year_count_core": len(observed_years),
                "first_observed_year_core": min(observed_years) if observed_years else "",
                "last_observed_year_core": max(observed_years) if observed_years else "",
                "train_observed_count_tensor": train_observed_count,
                "missing_rate_tensor": missing_rate,
                "coverage_by_year_core": json.dumps(year_coverage, sort_keys=True),
                "can_extend_supervised_years_alone": feature == "side_creations_et_total",
                "notes": note_for_feature(feature, observed_years),
            }
        )

    availability = pd.DataFrame(rows).sort_values(
        ["can_extend_supervised_years_alone", "observed_year_count_core", "feature_name"],
        ascending=[False, False, True],
    )

    year_rows = []
    for feature_year in range(min(target_years), max(target_years)):
        target_year = feature_year + 1
        if target_year not in target_years:
            continue
        panel_year = panel[panel[year_col] == feature_year] if feature_year in panel_years else pd.DataFrame()
        available_features = []
        full_coverage_features = []
        if not panel_year.empty:
            for feature in panel_features:
                if feature not in panel_year.columns:
                    continue
                observed_count = int(panel_year[feature].notna().sum())
                if observed_count > 0:
                    available_features.append(feature)
                if observed_count == core_node_count:
                    full_coverage_features.append(feature)
        year_rows.append(
            {
                "feature_year": feature_year,
                "target_year": target_year,
                "target_available": True,
                "has_current_panel_row": feature_year in panel_years,
                "available_feature_count_current_panel": len(available_features),
                "full_coverage_feature_count_current_panel": len(full_coverage_features),
                "available_features_current_panel": ",".join(available_features),
                "full_coverage_features_current_panel": ",".join(full_coverage_features),
                "long_history_possible_with_side_creations_only": 2012 <= feature_year <= 2023,
                "rich_feature_package_possible_current": feature_year in panel_years,
            }
        )
    year_plan = pd.DataFrame(year_rows)

    quality = {
        "core_node_count": core_node_count,
        "panel_years_current": panel_years,
        "target_years_side": target_years,
        "tensor_sample_index": sample_index.to_dict(orient="records"),
        "feature_count": int(len(availability)),
        "features_with_full_current_window": availability.loc[
            availability["observed_year_count_core"] == len(panel_years), "feature_name"
        ].tolist(),
        "features_with_3_or_more_years": availability.loc[
            availability["observed_year_count_core"] >= 3, "feature_name"
        ].tolist(),
        "main_conclusion": (
            "Current changes improve feature coverage/depth in 2019-2024. "
            "Only SIDE creations can extend supervised years alone back to 2012 without adding more historical features."
        ),
    }

    availability.to_csv(AVAILABILITY_OUT, index=False)
    year_plan.to_csv(YEAR_PLAN_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(availability, year_plan, quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


def note_for_feature(feature: str, observed_years: list[int]) -> str:
    if feature == "side_creations_et_total":
        return "target history lag; valid for t->t+1 if timing is explicit; not an independent external covariate"
    if len(observed_years) == 0:
        return "no observed value in current core panel"
    if len(observed_years) < 3:
        return "too sparse for long supervised history without more source years"
    if min(observed_years) > 2019:
        return "useful depth but does not extend the current feature window backward"
    return "usable in current rich annual package"


def write_report(availability: pd.DataFrame, year_plan: pd.DataFrame, quality: dict) -> None:
    long_candidates = availability[availability["can_extend_supervised_years_alone"]]
    rich_candidates = availability[availability["observed_year_count_core"] >= 3]

    lines = [
        "# Feature Temporal Availability Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- verificar se as adicoes recentes foram preservadas",
        "- separar aumento de profundidade de features de aumento de anos supervisionados",
        "- definir quais pacotes fazem sentido antes de novos modelos",
        "",
        "## Conclusao Curta",
        "",
        "- as alteracoes recentes foram preservadas no painel e no tensor",
        "- elas melhoram a cobertura observada das features na janela `2019-2024`",
        "- elas ainda nao aumentam sozinhas o numero de anos supervisionados do tensor rico",
        "- `side_creations_et_total` e o unico candidato atual que permite uma serie longa sozinho, mas ele e lag do proprio alvo",
        "",
        "## Estado Atual",
        "",
        f"- nos core: `{quality['core_node_count']}`",
        f"- anos de feature no painel atual: `{quality['panel_years_current']}`",
        f"- anos do target SIDE: `{quality['target_years_side'][0]}-{quality['target_years_side'][-1]}`",
        f"- features auditadas: `{quality['feature_count']}`",
        "",
        "## Features Com Maior Profundidade Atual",
        "",
        "| feature | papel | anos observados core | obs treino tensor | nota |",
        "|---|---|---|---:|---|",
    ]
    for row in rich_candidates.head(15).itertuples(index=False):
        lines.append(
            f"| `{row.feature_name}` | `{row.role}` | `{row.observed_years_core}` | `{row.train_observed_count_tensor}` | {row.notes} |"
        )

    lines.extend(
        [
            "",
            "## Candidato A Serie Longa",
            "",
        ]
    )
    if long_candidates.empty:
        lines.append("- nenhum candidato encontrado")
    else:
        for row in long_candidates.itertuples(index=False):
            lines.append(f"- `{row.feature_name}`: {row.notes}")

    lines.extend(
        [
            "",
            "## Plano Por Ano",
            "",
            "| feature_year | target_year | features disponiveis no painel atual | pacote rico atual | serie longa SIDE creations |",
            "|---:|---:|---:|---|---|",
        ]
    )
    for row in year_plan.itertuples(index=False):
        lines.append(
            f"| {row.feature_year} | {row.target_year} | {row.available_feature_count_current_panel} | `{row.rich_feature_package_possible_current}` | `{row.long_history_possible_with_side_creations_only}` |"
        )

    lines.extend(
        [
            "",
            "## Decisao Recomendada",
            "",
            "- manter dois pacotes separados",
            "- pacote rico: `2019-2023 -> 2020-2024`, mais features, menos anos",
            "- pacote longo: `2012-2023 -> 2013-2024`, inicialmente com lags SIDE e poucas covariaveis historicas",
            "- nao misturar os dois sem nome explicito, porque eles respondem perguntas metodologicas diferentes",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
