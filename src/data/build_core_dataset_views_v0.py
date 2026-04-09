from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CORE_NODES_PATH = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"

INPUTS = {
    "zones_master": ROOT / "data" / "processed" / "zones_master_annual_v0.csv",
    "panel_zones": ROOT / "data" / "processed" / "panel_zones_v0.csv",
    "population_history": ROOT / "data" / "processed" / "population_history_ze2020_v0.csv",
    "zan_ze2020": ROOT / "data" / "processed" / "zan_consumption_ze2020_v0.csv",
}

OUTPUTS = {
    "zones_master": ROOT / "data" / "processed" / "zones_master_annual_core_v0.csv",
    "panel_zones": ROOT / "data" / "processed" / "panel_zones_core_v0.csv",
    "population_history": ROOT / "data" / "processed" / "population_history_ze2020_core_v0.csv",
    "zan_ze2020": ROOT / "data" / "processed" / "zan_consumption_ze2020_core_v0.csv",
}

QUALITY_OUT = ROOT / "reports" / "core_dataset_views_quality_v0.json"


def filter_core(input_path: Path, output_path: Path, core_nodes: set[str]) -> dict[str, int]:
    df = pd.read_csv(input_path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].astype(str).str.zfill(4)
    filtered = df[df["ze2020"].isin(core_nodes)].copy()
    filtered.to_csv(output_path, index=False)
    return {
        "rows_in": int(len(df)),
        "rows_out": int(len(filtered)),
        "zones_out": int(filtered["ze2020"].nunique()),
    }


def main() -> None:
    core_nodes_df = pd.read_csv(CORE_NODES_PATH, dtype={"ze2020": str})
    core_nodes_df["ze2020"] = core_nodes_df["ze2020"].astype(str).str.zfill(4)
    core_nodes = set(core_nodes_df["ze2020"])

    quality = {
        "core_node_count": int(len(core_nodes)),
        "outputs": {},
        "notes": [
            "All core views are filtered to the largest connected component of the ZE2020 graph.",
            "These files define the territorial universe of the MVP after exclusion of Corsica and overseas components.",
        ],
    }

    for key, input_path in INPUTS.items():
        quality["outputs"][key] = filter_core(input_path, OUTPUTS[key], core_nodes)

    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
