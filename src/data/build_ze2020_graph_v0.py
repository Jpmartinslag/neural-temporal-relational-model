from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTER_ZIP = ROOT / "data" / "raw" / "territorial" / "fonds_ze2020_2026.zip"
NODES_OUT = ROOT / "data" / "processed" / "graph_nodes_ze2020_v0.csv"
EDGES_OUT = ROOT / "data" / "processed" / "graph_edges_ze2020_v0.csv"
QUALITY_OUT = ROOT / "reports" / "graph_ze2020_quality_v0.json"


def load_ze2020_geometries() -> gpd.GeoDataFrame:
    with zipfile.ZipFile(OUTER_ZIP) as outer:
        inner_bytes = outer.read("ze2020_2026.zip")
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
            inner.extractall(td)
        shp = Path(td) / "ze2020_2026.shp"
        gdf = gpd.read_file(shp)
        gdf["ze2020"] = gdf["ze2020"].astype(str).str.zfill(4)
        gdf["nb_com"] = pd.to_numeric(gdf["nb_com"], errors="coerce")
        return gdf[["ze2020", "libze2020", "nb_com", "geometry"]].copy()


def main() -> None:
    gdf = load_ze2020_geometries()

    nodes = gdf.drop(columns=["geometry"]).copy()
    nodes["geometry_type"] = gdf.geom_type.astype(str)
    nodes["is_multipolygon"] = (gdf.geom_type.astype(str) == "MultiPolygon").astype(int)
    nodes.to_csv(NODES_OUT, index=False)

    # Spatial index + touches relation for adjacency by geographic contiguity.
    edge_pairs: set[tuple[str, str]] = set()
    sindex = gdf.sindex
    for idx, geom in enumerate(gdf.geometry):
        left = gdf.iloc[idx]
        candidates = list(sindex.intersection(geom.bounds))
        for cand_idx in candidates:
            if cand_idx <= idx:
                continue
            right = gdf.iloc[cand_idx]
            other = right.geometry
            if geom.touches(other):
                a = left["ze2020"]
                b = right["ze2020"]
                edge_pairs.add((a, b))
                edge_pairs.add((b, a))

    edges = pd.DataFrame(sorted(edge_pairs), columns=["source_ze2020", "target_ze2020"])
    edges["edge_type"] = "geographic_adjacency"
    edges.to_csv(EDGES_OUT, index=False)

    undirected_edge_count = len(edge_pairs) // 2
    degree = pd.concat(
        [
            edges["source_ze2020"].value_counts(),
            nodes["ze2020"].map(edges["source_ze2020"].value_counts()).fillna(0).astype(int),
        ],
        axis=1,
    )
    degree.columns = ["degree_count", "degree_count_dup"]
    isolated = sorted(nodes.loc[~nodes["ze2020"].isin(edges["source_ze2020"]), "ze2020"].tolist())

    quality = {
        "node_count": int(len(nodes)),
        "directed_edge_count": int(len(edges)),
        "undirected_edge_count": int(undirected_edge_count),
        "isolated_nodes_count": int(len(isolated)),
        "isolated_nodes": isolated,
        "crs": "EPSG:4326",
        "notes": [
            "Adjacency is defined by polygon boundary contiguity using touches().",
            "Edges are exported in directed form for graph-model convenience.",
        ],
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
