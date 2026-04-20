from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PRE_STGNN_PATH = ROOT / "data" / "processed" / "pre_stgnn_dataset_core_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
EDGE_INDEX_PATH = ROOT / "data" / "processed" / "graph_edge_index_core_v0.csv"
TARGET_ANNUAL_PATH = ROOT / "data" / "processed" / "target_proxy_annual_core_v0.csv"

FEATURE_PANEL_OUT = ROOT / "data" / "processed" / "graph_model_feature_panel_core_v0.csv"
TARGET_PANEL_OUT = ROOT / "data" / "processed" / "graph_model_target_panel_core_v0.csv"
ADJACENCY_OUT = ROOT / "data" / "processed" / "graph_adjacency_core_v0.csv"
PACKAGE_SUMMARY_OUT = ROOT / "reports" / "graph_model_annual_package_core_quality_v0.json"
PACKAGE_REPORT_OUT = ROOT / "reports" / "archive" / "graph_tensor" / "GRAPH_MODEL_ANNUAL_PACKAGE_CORE_V0.md"


def feature_columns(frame: pd.DataFrame) -> list[str]:
    static = [
        "static_nb_com",
        "static_pop_growth_2021_2023",
        "static_pop_growth_2018_2023",
        "static_zan_artif_per_pop21",
        "static_zan_artif_per_surface",
        "static_zan_communes_count",
    ]
    dynamic = [
        "filosofi_s_hh_tax_weighted_proxy",
        "filosofi_s_dir_tax_di_weighted_proxy",
        "population_total",
        "active_lr_total",
        "employed_lr_total",
        "unemployed_lr_total",
        "unemployment_rate_est",
        "jobs_lt_total",
        "jobs_lt_per_1000_pop",
        "side_stocks_et_total",
        "side_stocks_ul_total",
        "side_stocks_et_per_1000_pop",
        "bpe_facilities_total",
        "bpe_facilities_per_1000_pop",
        "bpe_evolution_commune_type_presence_total",
        "flores_presential_unit_loc_total",
        "flores_productive_unit_loc_total",
        "flores_et_total",
        "side_creations_et_total",
    ]
    return dynamic + static


def build_package() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    features = pd.read_csv(PRE_STGNN_PATH, dtype={"ze2020": str})
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGE_INDEX_PATH, dtype={"source_ze2020": str, "target_ze2020": str})
    target = pd.read_csv(TARGET_ANNUAL_PATH, dtype={"ze2020": str})

    feature_cols = feature_columns(features)

    feature_panel = features[
        ["year", "node_idx", "ze2020", "libze2020", "reg"] + feature_cols
    ].copy()
    feature_panel = feature_panel.rename(columns={"year": "feature_year"})
    feature_panel = feature_panel.sort_values(["feature_year", "node_idx"]).reset_index(drop=True)

    target_panel = target.merge(nodes[["node_idx", "ze2020", "libze2020"]], on="ze2020", how="left")
    target_panel = target_panel.rename(
        columns={
            "target_year": "target_year",
            "target_proxy_establishment_creations_year": "target_proxy_establishment_creations_year",
        }
    ).sort_values(["target_year", "node_idx"]).reset_index(drop=True)

    adjacency = pd.DataFrame(0, index=nodes["node_idx"], columns=nodes["node_idx"], dtype=int)
    for row in edges.itertuples(index=False):
        adjacency.at[row.source_idx, row.target_idx] = 1
    adjacency.index.name = "source_idx"

    summary = {
        "node_count": int(nodes["node_idx"].nunique()),
        "edge_count_directed": int(len(edges)),
        "feature_years": sorted(feature_panel["feature_year"].unique().tolist()),
        "target_years": sorted(target_panel["target_year"].unique().tolist()),
        "feature_row_count": int(len(feature_panel)),
        "target_row_count": int(len(target_panel)),
        "feature_count": int(len(feature_cols)),
        "adjacency_density_directed": float(edges.shape[0] / (len(nodes) * len(nodes))),
        "gwn_readiness_note": (
            f"Annual package is structurally ready, but the observed feature timeline is only {feature_panel['feature_year'].nunique()} years "
            f"({int(feature_panel['feature_year'].min())}-{int(feature_panel['feature_year'].max())}), which is still shallow for Graph WaveNet."
        ),
    }
    return feature_panel, target_panel, adjacency, summary


def write_report(summary: dict) -> None:
    feature_years = summary["feature_years"]
    feature_year_count = len(feature_years)
    lines = [
        "# Graph Model Annual Package Core v0",
        "",
        "Data: 2026-04-09",
        "",
        "Objetivo:",
        "",
        "- preparar o pacote anual de modelagem com grafo no `core_v0`",
        "",
        "## Estrutura produzida",
        "",
        f"- nos: `{summary['node_count']}`",
        f"- arestas direcionadas: `{summary['edge_count_directed']}`",
        f"- anos de features: `{summary['feature_years']}`",
        f"- anos de target: `{summary['target_years']}`",
        f"- linhas de features: `{summary['feature_row_count']}`",
        f"- linhas de target: `{summary['target_row_count']}`",
        f"- numero de features: `{summary['feature_count']}`",
        "",
        "## Leitura metodologica",
        "",
        "- o pacote anual com grafo esta estruturalmente pronto",
        "- mas a profundidade temporal observada de features ainda e muito curta para um Graph WaveNet confiavel",
        f"- hoje o projeto tem apenas `{feature_year_count}` anos efetivos de features (`{feature_years[0]}-{feature_years[-1]}`)",
        "- isso e suficiente para organizacao do pacote, mas fraco para treinamento serio de um modelo spatio-temporal profundo",
        "",
        "## Conclusao",
        "",
        "- antes do Graph WaveNet anual, o projeto deve decidir se aceita um experimento estritamente demonstrativo ou se amplia a profundidade temporal das features",
    ]
    PACKAGE_REPORT_OUT.write_text("\n".join(lines) + "\n")


def main() -> None:
    feature_panel, target_panel, adjacency, summary = build_package()
    feature_panel.to_csv(FEATURE_PANEL_OUT, index=False)
    target_panel.to_csv(TARGET_PANEL_OUT, index=False)
    adjacency.to_csv(ADJACENCY_OUT)
    pd.Series(summary).to_json(PACKAGE_SUMMARY_OUT, indent=2)
    write_report(summary)
    print(summary)


if __name__ == "__main__":
    main()
