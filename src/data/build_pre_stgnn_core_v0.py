from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
NODES_PATH = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"
EDGES_PATH = ROOT / "data" / "processed" / "graph_edges_ze2020_core_v0.csv"
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
POP_PATH = ROOT / "data" / "processed" / "population_history_ze2020_core_v0.csv"
ZAN_PATH = ROOT / "data" / "processed" / "zan_consumption_ze2020_core_v0.csv"

NODE_INDEX_OUT = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
EDGE_INDEX_OUT = ROOT / "data" / "processed" / "graph_edge_index_core_v0.csv"
DATASET_OUT = ROOT / "data" / "processed" / "pre_stgnn_dataset_core_v0.csv"
MASK_OUT = ROOT / "data" / "processed" / "pre_stgnn_feature_masks_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "pre_stgnn_core_quality_v0.json"
FEATURE_REGISTRY_OUT = ROOT / "metadata" / "pre_stgnn_feature_registry_core_v0.csv"


DYNAMIC_FEATURES = [
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
]

STATIC_CONTEXT_FEATURES = [
    "static_nb_com",
    "static_pop_growth_2021_2023",
    "static_pop_growth_2018_2023",
    "static_zan_artif_per_pop21",
    "static_zan_artif_per_surface",
    "static_zan_communes_count",
]


def main() -> None:
    nodes = pd.read_csv(NODES_PATH, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_PATH, dtype={"source_ze2020": str, "target_ze2020": str})
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    pop = pd.read_csv(POP_PATH, dtype={"ze2020": str})
    zan = pd.read_csv(ZAN_PATH, dtype={"ze2020": str})

    for df in [nodes, edges, panel, pop, zan]:
        for col in [c for c in df.columns if "ze2020" in c]:
            df[col] = df[col].astype(str).str.zfill(4)

    nodes = nodes.sort_values("ze2020").reset_index(drop=True)
    nodes["node_idx"] = range(len(nodes))
    node_lookup = nodes.set_index("ze2020")["node_idx"].to_dict()

    node_index = nodes[["node_idx", "ze2020", "libze2020", "nb_com"]].copy()
    node_index.to_csv(NODE_INDEX_OUT, index=False)

    edge_index = edges.copy()
    edge_index["source_idx"] = edge_index["source_ze2020"].map(node_lookup)
    edge_index["target_idx"] = edge_index["target_ze2020"].map(node_lookup)
    edge_index = edge_index[["source_idx", "target_idx", "source_ze2020", "target_ze2020", "edge_type"]]
    edge_index.to_csv(EDGE_INDEX_OUT, index=False)

    pop["static_pop_growth_2021_2023"] = (
        (pd.to_numeric(pop["PMUN2023"], errors="coerce") - pd.to_numeric(pop["PMUN2021"], errors="coerce"))
        / pd.to_numeric(pop["PMUN2021"], errors="coerce")
    )
    pop["static_pop_growth_2018_2023"] = (
        (pd.to_numeric(pop["PMUN2023"], errors="coerce") - pd.to_numeric(pop["PMUN2018"], errors="coerce"))
        / pd.to_numeric(pop["PMUN2018"], errors="coerce")
    )

    static_context = (
        nodes[["ze2020", "nb_com"]]
        .rename(columns={"nb_com": "static_nb_com"})
        .merge(pop[["ze2020", "static_pop_growth_2021_2023", "static_pop_growth_2018_2023"]], on="ze2020", how="left")
        .merge(
            zan[["ze2020", "zan_artif_per_pop21", "zan_artif_per_surface", "communes_count"]].rename(
                columns={
                    "zan_artif_per_pop21": "static_zan_artif_per_pop21",
                    "zan_artif_per_surface": "static_zan_artif_per_surface",
                    "communes_count": "static_zan_communes_count",
                }
            ),
            on="ze2020",
            how="left",
        )
    )

    dataset = panel.merge(node_index[["node_idx", "ze2020", "libze2020"]], on=["ze2020", "libze2020"], how="left")
    dataset = dataset.merge(static_context, on="ze2020", how="left")
    dataset = dataset.sort_values(["year", "node_idx"]).reset_index(drop=True)

    keep_cols = [
        "year",
        "node_idx",
        "ze2020",
        "libze2020",
        "reg",
        "is_structural_anomaly",
        "anomaly_reason",
        "is_source_year_row",
        "is_training_eligible_panel_v0",
        "observed_feature_count",
        "has_any_feature_value",
        *DYNAMIC_FEATURES,
        *STATIC_CONTEXT_FEATURES,
    ]
    dataset = dataset[keep_cols].copy()

    masks = dataset[["year", "node_idx", "ze2020"]].copy()
    for col in DYNAMIC_FEATURES + STATIC_CONTEXT_FEATURES:
        masks[f"mask_{col}"] = dataset[col].notna().astype(int)
    masks.to_csv(MASK_OUT, index=False)
    dataset.to_csv(DATASET_OUT, index=False)

    feature_rows = []
    for col in DYNAMIC_FEATURES:
        feature_rows.append(
            {
                "feature_name": col,
                "feature_group": "dynamic_panel",
                "temporal_role": "year_specific",
                "included_in_core_v0": 1,
                "notes": "Observed only in source year rows; no temporal imputation applied.",
            }
        )
    for col in STATIC_CONTEXT_FEATURES:
        feature_rows.append(
            {
                "feature_name": col,
                "feature_group": "static_context",
                "temporal_role": "repeated_static",
                "included_in_core_v0": 1,
                "notes": "Repeated across years as structural context.",
            }
        )
    feature_registry = pd.DataFrame(feature_rows)
    feature_registry.to_csv(FEATURE_REGISTRY_OUT, index=False)

    quality = {
        "node_count": int(nodes["node_idx"].nunique()),
        "edge_count_directed": int(len(edge_index)),
        "dataset_rows": int(len(dataset)),
        "years": sorted([int(y) for y in dataset["year"].unique().tolist()]),
        "dynamic_feature_count": len(DYNAMIC_FEATURES),
        "static_context_feature_count": len(STATIC_CONTEXT_FEATURES),
        "target_status": "not_defined_yet",
        "notes": [
            "This is a pre-STGNN structural package for core_v0 only.",
            "No target column is included yet; the package is intended to stabilize nodes, edges, features and masks before forecasting target freeze.",
        ],
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
