from __future__ import annotations

import io
import json
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTER_ZIP = ROOT / "data" / "raw" / "territorial" / "fonds_ze2020_2026.zip"
CORE_NODES = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"
CORE_EDGES = ROOT / "data" / "processed" / "graph_edges_ze2020_core_v0.csv"
HTML_OUT = ROOT / "reports" / "graph_visuals_v0" / "ze2020_graph_core_interactive_v0.html"
SUMMARY_OUT = ROOT / "reports" / "graph_visuals_v0" / "graph_core_visuals_summary_v0.json"


def load_geometries() -> gpd.GeoDataFrame:
    with zipfile.ZipFile(OUTER_ZIP) as outer:
        inner_bytes = outer.read("ze2020_2026.zip")
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
            inner.extractall(td)
        gdf = gpd.read_file(Path(td) / "ze2020_2026.shp")
    gdf["ze2020"] = gdf["ze2020"].astype(str).str.zfill(4)
    gdf["nb_com"] = pd.to_numeric(gdf["nb_com"], errors="coerce")
    return gdf[["ze2020", "libze2020", "nb_com", "geometry"]].copy()


def main() -> None:
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    gdf = load_geometries()
    nodes = pd.read_csv(CORE_NODES, dtype={"ze2020": str})
    edges = pd.read_csv(CORE_EDGES, dtype={"source_ze2020": str, "target_ze2020": str})
    nodes["ze2020"] = nodes["ze2020"].astype(str).str.zfill(4)

    gdf = gdf[gdf["ze2020"].isin(set(nodes["ze2020"]))].copy()

    adj = defaultdict(set)
    for s, t in edges[["source_ze2020", "target_ze2020"]].itertuples(index=False):
        adj[s].add(t)
        adj[t].add(s)
    gdf["degree"] = gdf["ze2020"].map(lambda z: len(adj[z]))

    rep_points = gdf.to_crs(3857).set_index("ze2020").representative_point().to_crs(4326)

    # no basemap: only metropolitan France graph
    m = folium.Map(location=[46.6, 2.4], zoom_start=6, tiles=None)

    poly_layer = folium.FeatureGroup(name="Core ZE2020 polygons", show=True)
    folium.GeoJson(
        gdf.to_json(),
        style_function=lambda _feature: {
            "fillColor": "#bdd7ee",
            "color": "#3b3b3b",
            "weight": 0.5,
            "fillOpacity": 0.35,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["ze2020", "libze2020", "nb_com", "degree"],
            aliases=["ZE2020", "Label", "Communes", "Degree"],
            localize=True,
            sticky=False,
        ),
    ).add_to(poly_layer)
    poly_layer.add_to(m)

    edge_layer = folium.FeatureGroup(name="Adjacency edges", show=True)
    undirected = edges[edges["source_ze2020"] < edges["target_ze2020"]]
    for row in undirected.itertuples(index=False):
        a = rep_points[row.source_ze2020]
        b = rep_points[row.target_ze2020]
        folium.PolyLine(
            locations=[(a.y, a.x), (b.y, b.x)],
            color="#2f4858",
            weight=1.1,
            opacity=0.32,
        ).add_to(edge_layer)
    edge_layer.add_to(m)

    node_layer = folium.FeatureGroup(name="Core nodes", show=True)
    for row in gdf.itertuples(index=False):
        pt = rep_points[row.ze2020]
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=3.5,
            color="#0b1f33",
            weight=0.8,
            fill=True,
            fill_color="#0b1f33",
            fill_opacity=0.9,
            tooltip=f"{row.ze2020} - {row.libze2020}",
            popup=(
                f"<b>{row.ze2020} - {row.libze2020}</b><br>"
                f"Communes: {row.nb_com}<br>"
                f"Degree: {row.degree}"
            ),
        ).add_to(node_layer)
    node_layer.add_to(m)

    bounds = gdf.total_bounds  # minx, miny, maxx, maxy
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(HTML_OUT))

    summary = {
        "html_out": HTML_OUT.name,
        "node_count": int(len(nodes)),
        "undirected_edge_count": int(len(undirected)),
        "notes": [
            "Interactive HTML restricted to the core_v0 graph only.",
            "No external basemap is used, so the visual focuses on metropolitan France graph structure only.",
        ],
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
