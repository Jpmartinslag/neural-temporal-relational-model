from __future__ import annotations

import io
import json
import tempfile
import zipfile
from collections import defaultdict, deque
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTER_ZIP = ROOT / "data" / "raw" / "territorial" / "fonds_ze2020_2026.zip"
EDGES_PATH = ROOT / "data" / "processed" / "graph_edges_ze2020_v0.csv"
HTML_OUT = ROOT / "reports" / "graph_visuals_v0" / "ze2020_graph_interactive_v0.html"
SUMMARY_OUT = ROOT / "reports" / "graph_visuals_v0" / "graph_visuals_summary_v0.json"

PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


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


def compute_components(nodes: list[str], edges: pd.DataFrame) -> tuple[dict[str, int], list[list[str]], dict[str, set[str]]]:
    adj = defaultdict(set)
    for s, t in edges[["source_ze2020", "target_ze2020"]].itertuples(index=False):
        adj[s].add(t)
        adj[t].add(s)

    seen = set()
    component_map = {}
    components = []
    for node in nodes:
        if node in seen:
            continue
        q = deque([node])
        seen.add(node)
        comp = []
        while q:
            x = q.popleft()
            comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        comp_id = len(components)
        for x in comp:
            component_map[x] = comp_id
        components.append(sorted(comp))
    return component_map, components, adj


def main() -> None:
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)

    gdf = load_geometries()
    edges = pd.read_csv(EDGES_PATH, dtype={"source_ze2020": str, "target_ze2020": str})

    component_map, components, adj = compute_components(gdf["ze2020"].tolist(), edges)
    gdf["component_id"] = gdf["ze2020"].map(component_map)
    gdf["degree"] = gdf["ze2020"].map(lambda z: len(adj[z]))
    gdf["is_isolated"] = gdf["degree"] == 0
    rep_points = gdf.to_crs(3857).set_index("ze2020").representative_point().to_crs(4326)

    # web map in WGS84
    center = [46.6, 2.4]
    m = folium.Map(location=center, zoom_start=5, tiles="CartoDB positron")

    # components polygons
    comp_layer = folium.FeatureGroup(name="ZE2020 components", show=True)
    for comp_id in sorted(gdf["component_id"].unique()):
        subset = gdf[gdf["component_id"] == comp_id]
        color = PALETTE[comp_id % len(PALETTE)]
        gj = folium.GeoJson(
            subset.to_json(),
            style_function=lambda _feature, color=color: {
                "fillColor": color,
                "color": "#333333",
                "weight": 0.6,
                "fillOpacity": 0.45,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["ze2020", "libze2020", "nb_com", "component_id", "degree"],
                aliases=["ZE2020", "Label", "Communes", "Component", "Degree"],
                localize=True,
                sticky=False,
            ),
        )
        gj.add_to(comp_layer)
    comp_layer.add_to(m)

    # explicit node layer
    node_layer = folium.FeatureGroup(name="ZE2020 nodes", show=True)
    for row in gdf.itertuples(index=False):
        pt = rep_points[row.ze2020]
        color = "#b30000" if row.is_isolated else "#1f2d3d"
        radius = 6 if row.is_isolated else 4
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=radius,
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=f"{row.ze2020} - {row.libze2020}",
            popup=(
                f"<b>{row.ze2020} - {row.libze2020}</b><br>"
                f"Communes: {row.nb_com}<br>"
                f"Component: {row.component_id}<br>"
                f"Degree: {row.degree}"
            ),
        ).add_to(node_layer)
    node_layer.add_to(m)

    # isolated nodes
    isolated_layer = folium.FeatureGroup(name="Isolated nodes", show=True)
    isolated = gdf[gdf["is_isolated"]].to_crs(3857)
    reps = isolated.representative_point().to_crs(4326)
    for (_, row), pt in zip(isolated.iterrows(), reps):
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=7,
            color="#b30000",
            fill=True,
            fill_opacity=0.95,
            popup=f"{row['ze2020']} - {row['libze2020']}",
        ).add_to(isolated_layer)
    isolated_layer.add_to(m)

    # centroid-link layer for abstract edge reading
    edge_layer = folium.FeatureGroup(name="Abstract adjacency links", show=True)
    undirected = edges[edges["source_ze2020"] < edges["target_ze2020"]]
    for row in undirected.itertuples(index=False):
        a = rep_points[row.source_ze2020]
        b = rep_points[row.target_ze2020]
        folium.PolyLine(
            locations=[(a.y, a.x), (b.y, b.x)],
            color="#3b4b5a",
            weight=1.1,
            opacity=0.35,
            popup=f"{row.source_ze2020} ↔ {row.target_ze2020}",
        ).add_to(edge_layer)
    edge_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(HTML_OUT))

    summary = json.loads(SUMMARY_OUT.read_text(encoding="utf-8")) if SUMMARY_OUT.exists() else {}
    summary["interactive_html"] = HTML_OUT.name
    summary["component_count"] = len(components)
    summary["component_sizes"] = [len(c) for c in sorted(components, key=len, reverse=True)]
    summary["isolated_nodes"] = gdf.loc[gdf["is_isolated"], ["ze2020", "libze2020"]].to_dict("records")
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"html_out": str(HTML_OUT), "component_count": len(components)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
