"""
France-map dynamic graph comparison for HERALD V2.

Dependency-light implementation: reads the local ZE2020 shapefile directly
from ZIP, converts Lambert-93 to WGS84, and writes a Plotly HTML map.

Output:
  reports/figures/herald_v2_graph_model_comparison_v1.html
"""

from __future__ import annotations

import io
import json
import math
import struct
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

OUT_HTML = FIGURES / "herald_v2_graph_model_comparison_v1.html"
OUTER_ZIP = ROOT / "data" / "raw" / "territorial" / "fonds_ze2020_2026.zip"

YEARS = [2021, 2022, 2023, 2024]
SEEDS = [0, 7, 42]
MODELS = ["Ridge_AR", "DCRNN_V1", "STGNN_V1", "HERALD_V2_full"]
MODEL_LABELS = {
    "Ridge_AR": "Ridge AR",
    "DCRNN_V1": "DCRNN V1",
    "STGNN_V1": "Dynamic STGNN V1",
    "HERALD_V2_full": "HERALD V2 full",
}
GATE_LABELS = ["Self", "Geo", "Mobility", "Adaptive"]
GATE_COLORSCALE = [
    [0.00, "#5b5b5b"],
    [0.24, "#5b5b5b"],
    [0.25, "#3b6ea8"],
    [0.49, "#3b6ea8"],
    [0.50, "#3c9d65"],
    [0.74, "#3c9d65"],
    [0.75, "#d0793f"],
    [1.00, "#d0793f"],
]
ERROR_COLORSCALE = [
    [0.00, "#2166ac"],
    [0.25, "#67a9cf"],
    [0.50, "#f7f7f7"],
    [0.75, "#ef8a62"],
    [1.00, "#b2182b"],
]


def wmape(y_true, y_pred):
    denom = np.abs(np.asarray(y_true, dtype=float)).sum()
    return float(np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)).sum() / denom)


def lambert93_to_wgs84(x, y):
    # EPSG:2154 inverse projection, constants for RGF93 / Lambert-93.
    n = 0.7256077650532670
    c = 11754255.426096
    xs = 700000.0
    ys = 12655612.049876
    e = 0.0818191910428158
    lon0 = math.radians(3.0)

    r = math.hypot(x - xs, y - ys)
    gamma = math.atan((x - xs) / (ys - y))
    lon = lon0 + gamma / n
    lat_iso = -math.log(abs(r / c)) / n

    lat = 2 * math.atan(math.exp(lat_iso)) - math.pi / 2
    for _ in range(6):
        lat = 2 * math.atan(
            ((1 + e * math.sin(lat)) / (1 - e * math.sin(lat))) ** (e / 2)
            * math.exp(lat_iso)
        ) - math.pi / 2
    return math.degrees(lon), math.degrees(lat)


def read_dbf_records(dbf_bytes):
    num_records = struct.unpack("<I", dbf_bytes[4:8])[0]
    header_len = struct.unpack("<H", dbf_bytes[8:10])[0]
    rec_len = struct.unpack("<H", dbf_bytes[10:12])[0]

    fields = []
    offset = 32
    while dbf_bytes[offset] != 0x0D:
        raw = dbf_bytes[offset : offset + 32]
        name = raw[:11].split(b"\x00", 1)[0].decode("ascii")
        length = raw[16]
        fields.append((name, length))
        offset += 32

    records = []
    pos = header_len
    for _ in range(num_records):
        rec = dbf_bytes[pos : pos + rec_len]
        pos += rec_len
        if rec[:1] == b"*":
            continue
        item = {}
        field_pos = 1
        for name, length in fields:
            item[name] = rec[field_pos : field_pos + length].decode("utf-8", errors="replace").strip()
            field_pos += length
        records.append(item)
    return records


def read_shp_polygons(shp_bytes):
    polygons = []
    offset = 100
    while offset + 8 <= len(shp_bytes):
        _rec_no, content_words = struct.unpack(">2i", shp_bytes[offset : offset + 8])
        offset += 8
        content_len = content_words * 2
        content = shp_bytes[offset : offset + content_len]
        offset += content_len
        if len(content) < 44:
            polygons.append([])
            continue
        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type == 0:
            polygons.append([])
            continue
        if shape_type not in (5, 15):
            raise ValueError(f"Unsupported shapefile shape type: {shape_type}")

        num_parts, num_points = struct.unpack("<2i", content[36:44])
        parts_start = 44
        points_start = parts_start + 4 * num_parts
        parts = list(struct.unpack(f"<{num_parts}i", content[parts_start:points_start]))
        parts.append(num_points)

        points = []
        for i in range(num_points):
            x, y = struct.unpack("<2d", content[points_start + i * 16 : points_start + (i + 1) * 16])
            points.append(lambert93_to_wgs84(x, y))

        rings = []
        for start, end in zip(parts[:-1], parts[1:]):
            ring = points[start:end]
            if len(ring) < 4:
                continue
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append([[float(lon), float(lat)] for lon, lat in ring])
        polygons.append(rings)
    return polygons


def load_ze2020_geojson():
    with zipfile.ZipFile(OUTER_ZIP) as outer:
        inner_bytes = outer.read("ze2020_2026.zip")
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
        shp_name = next(name for name in inner.namelist() if name.lower().endswith(".shp"))
        dbf_name = next(name for name in inner.namelist() if name.lower().endswith(".dbf"))
        polygons = read_shp_polygons(inner.read(shp_name))
        records = read_dbf_records(inner.read(dbf_name))

    core = pd.read_csv(PROCESSED / "graph_node_index_core_v0.csv")
    core_ids = set(core["ze2020"].astype(int))

    features = []
    rows = []
    for rec, rings in zip(records, polygons):
        ze = str(rec["ze2020"]).zfill(4)
        ze_int = int(ze)
        if ze_int not in core_ids or not rings:
            continue
        props = {
            "ze2020": ze,
            "ze2020_int": ze_int,
            "libze2020": rec["libze2020"],
            "nb_com": int(rec["nb_com"]) if str(rec["nb_com"]).isdigit() else None,
        }
        if len(rings) == 1:
            geometry = {"type": "Polygon", "coordinates": rings}
        else:
            geometry = {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}
        features.append({"type": "Feature", "id": ze, "properties": props, "geometry": geometry})
        lon = float(np.mean([point[0] for ring in rings for point in ring]))
        lat = float(np.mean([point[1] for ring in rings for point in ring]))
        rows.append({**props, "lon": lon, "lat": lat})

    return {"type": "FeatureCollection", "features": features}, pd.DataFrame(rows)


def read_adjacency(path):
    frame = pd.read_csv(path)
    if "source_idx" in frame.columns:
        frame = frame.drop(columns=["source_idx"])
    return frame.to_numpy(dtype=float)


def row_normalize(matrix):
    matrix = np.asarray(matrix, dtype=float)
    row_sum = matrix.sum(axis=1, keepdims=True)
    return np.divide(matrix, row_sum, out=np.zeros_like(matrix), where=row_sum > 0)


def top_edges_from_matrix(matrix, zones, top_k=500, min_weight=1e-12):
    rows, cols = np.where(matrix > min_weight)
    edges = []
    for i, j in zip(rows, cols):
        if i == j:
            continue
        edges.append((int(zones[i]), int(zones[j]), float(matrix[i, j])))
    edges.sort(key=lambda item: item[2], reverse=True)
    return edges[:top_k]


def load_graph_sources():
    nodes = pd.read_csv(PROCESSED / "graph_node_index_core_v0.csv").sort_values("node_idx")
    zones = nodes["ze2020"].astype(int).to_numpy()
    geo = row_normalize(read_adjacency(PROCESSED / "graph_adjacency_core_v0.csv"))
    mobility = row_normalize(read_adjacency(PROCESSED / "graph_adjacency_mobility_v0.csv"))

    adaptive_mats = []
    gate_tensors = []
    years = None
    for seed in SEEDS:
        path = PROCESSED / f"herald_v2_internals_full_seed_{seed}_v1.npz"
        if not path.exists():
            continue
        data = np.load(path, allow_pickle=True)
        adaptive_mats.append(data["adaptive_adj"])
        gate_tensors.append(data["gate_weights"])
        years = data["years_full"].astype(int).tolist()
    if not adaptive_mats:
        raise FileNotFoundError("No HERALD V2 full internals found.")
    return {
        "zones": zones,
        "years": years,
        "geo": geo,
        "mobility": mobility,
        "adaptive": row_normalize(np.mean(adaptive_mats, axis=0)),
        "gate": np.mean(gate_tensors, axis=0),
    }


def dynamic_edges_and_gates(graph_sources):
    zones = graph_sources["zones"]
    year_to_idx = {int(year): idx for idx, year in enumerate(graph_sources["years"])}
    edges_by_year = {}
    gate_rows = []
    for year in YEARS:
        t = year_to_idx[year]
        gate = graph_sources["gate"][t]
        effective = (
            graph_sources["geo"] * gate[:, 1][:, None]
            + graph_sources["mobility"] * gate[:, 2][:, None]
            + graph_sources["adaptive"] * gate[:, 3][:, None]
        )
        edges_by_year[year] = top_edges_from_matrix(effective, zones, top_k=500)
        dominant = gate.argmax(axis=1)
        for zone, dom, weights in zip(zones, dominant, gate):
            gate_rows.append(
                {
                    "ze2020_int": int(zone),
                    "target_year": year,
                    "dominant_gate_id": int(dom),
                    "dominant_gate": GATE_LABELS[int(dom)],
                    "gate_self": float(weights[0]),
                    "gate_geo": float(weights[1]),
                    "gate_mobility": float(weights[2]),
                    "gate_adaptive": float(weights[3]),
                }
            )
    return edges_by_year, pd.DataFrame(gate_rows)


def load_model_predictions():
    frames = []
    base = pd.read_csv(PROCESSED / "dynamic_feature_panel_baseline_predictions_v1.csv")
    ridge = base[base["model"] == "Ridge_AR"].copy()
    ridge["model"] = "Ridge_AR"
    frames.append(ridge)

    for seed in SEEDS:
        path = PROCESSED / f"dynamic_stgnn_model_predictions_seed_{seed}_v1.csv"
        if not path.exists():
            continue
        pred = pd.read_csv(path)
        for raw_model, label in [
            ("dcrnn_residual", "DCRNN_V1"),
            ("dynamic_stgnn_residual", "STGNN_V1"),
        ]:
            sub = pred[pred["model"] == raw_model].copy()
            if not sub.empty:
                sub["model"] = label
                frames.append(sub)

    for seed in SEEDS:
        path = PROCESSED / f"herald_v2_predictions_full_seed_{seed}_v1.csv"
        if path.exists():
            pred = pd.read_csv(path)
            pred["model"] = "HERALD_V2_full"
            frames.append(pred)

    pred = pd.concat(frames, ignore_index=True)
    pred["ze2020_int"] = pred["ZE2020"].astype(int)
    pred = (
        pred.groupby(["model", "target_year", "ze2020_int"], as_index=False)
        .agg(y_true=("y_true", "mean"), y_pred=("y_pred", "mean"))
    )
    pred["signed_error_pct"] = 100.0 * (pred["y_pred"] - pred["y_true"]) / pred["y_true"].clip(lower=1.0)
    pred["abs_error"] = (pred["y_pred"] - pred["y_true"]).abs()
    return pred


def edge_trace(edges, zones_df, year, visible=False):
    points = zones_df.set_index("ze2020_int")[["lon", "lat"]].to_dict("index")
    lons, lats = [], []
    for source, target, _weight in edges:
        if source not in points or target not in points:
            continue
        lons += [points[source]["lon"], points[target]["lon"], None]
        lats += [points[source]["lat"], points[target]["lat"], None]
    return go.Scattergeo(
        lon=lons,
        lat=lats,
        mode="lines",
        line=dict(color="rgba(32,28,24,0.36)", width=1.15),
        name=f"HERALD effective graph {year}",
        hoverinfo="skip",
        visible=visible,
    )


def error_trace(geojson, zones_df, pred, model, year, cmax, visible=False):
    sub = pred[(pred["model"] == model) & (pred["target_year"] == year)]
    merged = zones_df.merge(sub, on="ze2020_int", how="left")
    custom = np.stack(
        [
            merged["libze2020"].astype(str),
            merged["y_true"].fillna(np.nan),
            merged["y_pred"].fillna(np.nan),
            merged["abs_error"].fillna(np.nan),
        ],
        axis=1,
    )
    return go.Choropleth(
        geojson=geojson,
        locations=merged["ze2020"],
        z=merged["signed_error_pct"],
        featureidkey="properties.ze2020",
        colorscale=ERROR_COLORSCALE,
        zmin=-cmax,
        zmax=cmax,
        marker_line_color="rgba(255,255,255,0.85)",
        marker_line_width=0.35,
        colorbar=dict(title="Signed<br>error %"),
        name=f"{MODEL_LABELS[model]} {year}",
        customdata=custom,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "ZE2020: %{location}<br>"
            "True: %{customdata[1]:,.0f}<br>"
            "Pred: %{customdata[2]:,.0f}<br>"
            "Signed error: %{z:+.2f}%<br>"
            "Abs error: %{customdata[3]:,.0f}<extra></extra>"
        ),
        visible=visible,
    )


def gate_trace(geojson, zones_df, gate_df, year, visible=False):
    sub = gate_df[gate_df["target_year"] == year]
    merged = zones_df.merge(sub, on="ze2020_int", how="left")
    custom = np.stack(
        [
            merged["libze2020"].astype(str),
            merged["dominant_gate"].astype(str),
            merged["gate_self"],
            merged["gate_geo"],
            merged["gate_mobility"],
            merged["gate_adaptive"],
        ],
        axis=1,
    )
    return go.Choropleth(
        geojson=geojson,
        locations=merged["ze2020"],
        z=merged["dominant_gate_id"],
        featureidkey="properties.ze2020",
        colorscale=GATE_COLORSCALE,
        zmin=0,
        zmax=3,
        marker_line_color="rgba(255,255,255,0.85)",
        marker_line_width=0.35,
        colorbar=dict(title="Dominant<br>gate", tickmode="array", tickvals=[0, 1, 2, 3], ticktext=GATE_LABELS),
        name=f"Dominant gate {year}",
        customdata=custom,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "ZE2020: %{location}<br>"
            "Dominant: %{customdata[1]}<br>"
            "Self: %{customdata[2]:.3f}<br>"
            "Geo: %{customdata[3]:.3f}<br>"
            "Mobility: %{customdata[4]:.3f}<br>"
            "Adaptive: %{customdata[5]:.3f}<extra></extra>"
        ),
        visible=visible,
    )


def build_figure(geojson, zones_df, pred, edges_by_year, gate_df):
    cmax = max(float(np.nanpercentile(np.abs(pred["signed_error_pct"]), 96)), 8.0)
    fig = go.Figure()
    trace_meta = []

    for model in MODELS:
        for year in YEARS:
            visible = model == "HERALD_V2_full" and year == 2024
            fig.add_trace(error_trace(geojson, zones_df, pred, model, year, cmax, visible))
            trace_meta.append(("error", model, year))

    for year in YEARS:
        fig.add_trace(edge_trace(edges_by_year[year], zones_df, year, visible=(year == 2024)))
        trace_meta.append(("edge", "HERALD_effective", year))

    for year in YEARS:
        fig.add_trace(gate_trace(geojson, zones_df, gate_df, year, visible=False))
        trace_meta.append(("gate", "Dominant_gate", year))

    buttons = []
    for idx, (kind, model, year) in enumerate(trace_meta):
        if kind == "edge":
            continue
        visible = [False] * len(trace_meta)
        visible[idx] = True
        edge_idx = trace_meta.index(("edge", "HERALD_effective", year))
        visible[edge_idx] = True
        if kind == "error":
            sub = pred[(pred["model"] == model) & (pred["target_year"] == year)]
            title = f"France ZE2020 - {MODEL_LABELS[model]} error + HERALD effective graph - {year} (WMAPE {wmape(sub['y_true'], sub['y_pred']):.4f})"
            label = f"{year} | {MODEL_LABELS[model]}"
        else:
            title = f"France ZE2020 - HERALD V2 dominant gate + effective graph - {year}"
            label = f"{year} | dominant gate"
        buttons.append(dict(label=label, method="update", args=[{"visible": visible}, {"title": title}]))

    fig.update_layout(
        title="France ZE2020 - HERALD V2 full error + HERALD effective graph - 2024",
        geo=dict(
            fitbounds="locations",
            visible=False,
            projection_type="mercator",
            bgcolor="#f6f3ee",
            landcolor="#f6f3ee",
            lakecolor="#f6f3ee",
        ),
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                x=0.01,
                y=1.08,
                xanchor="left",
                yanchor="top",
                bgcolor="white",
                bordercolor="#999",
            )
        ],
        margin=dict(l=10, r=10, t=80, b=10),
        width=1120,
        height=860,
        paper_bgcolor="#f6f3ee",
        font=dict(family="Arial", color="#232323"),
    )
    return fig


def build_summary(pred):
    rows = []
    for model in MODELS:
        for year in YEARS:
            sub = pred[(pred["model"] == model) & (pred["target_year"] == year)]
            rows.append({"model": model, "year": year, "wmape": wmape(sub["y_true"], sub["y_pred"])})
    per_year = pd.DataFrame(rows)
    mean = per_year.groupby("model", as_index=False)["wmape"].mean().sort_values("wmape")
    return per_year, mean


def html_table(frame):
    cols = list(frame.columns)
    rows = ["<table><thead><tr>" + "".join(f"<th>{col}</th>" for col in cols) + "</tr></thead><tbody>"]
    for row in frame.itertuples(index=False):
        cells = [f"<td>{value:.6f}</td>" if isinstance(value, float) else f"<td>{value}</td>" for value in row]
        rows.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("</tbody></table>")
    return "\n".join(rows)


def build_bar_figures(per_year, mean):
    color_map = {
        "HERALD_V2_full": "#d0793f",
        "STGNN_V1": "#3b6ea8",
        "DCRNN_V1": "#6a9fd8",
        "Ridge_AR": "#777777",
    }

    mean_plot = mean.sort_values("wmape", ascending=True).copy()
    mean_fig = go.Figure(
        go.Bar(
            x=mean_plot["wmape"],
            y=[MODEL_LABELS.get(model, model) for model in mean_plot["model"]],
            orientation="h",
            marker_color=[color_map.get(model, "#999999") for model in mean_plot["model"]],
            text=[f"{value:.4f}" for value in mean_plot["wmape"]],
            textposition="outside",
            hovertemplate="%{y}<br>Mean WMAPE: %{x:.6f}<extra></extra>",
        )
    )
    mean_fig.update_layout(
        title="Mean WMAPE",
        template="plotly_white",
        height=260,
        margin=dict(l=130, r=24, t=48, b=28),
        xaxis_title="WMAPE",
        yaxis_title=None,
        showlegend=False,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="Arial", size=12, color="#232323"),
    )

    year_fig = go.Figure()
    for model in MODELS:
        sub = per_year[per_year["model"] == model].sort_values("year")
        year_fig.add_trace(
            go.Bar(
                x=sub["year"].astype(str),
                y=sub["wmape"],
                name=MODEL_LABELS.get(model, model),
                marker_color=color_map.get(model, "#999999"),
                text=[f"{value:.3f}" for value in sub["wmape"]],
                textposition="auto",
                hovertemplate="%{x}<br>%{fullData.name}<br>WMAPE: %{y:.6f}<extra></extra>",
            )
        )
    year_fig.update_layout(
        title="WMAPE by Year",
        barmode="group",
        template="plotly_white",
        height=330,
        margin=dict(l=48, r=16, t=48, b=50),
        xaxis_title="Target year",
        yaxis_title="WMAPE",
        legend=dict(orientation="h", yanchor="bottom", y=-0.38, xanchor="left", x=0),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="Arial", size=12, color="#232323"),
    )
    return mean_fig, year_fig


def main():
    geojson, zones_df = load_ze2020_geojson()
    graph_sources = load_graph_sources()
    edges_by_year, gate_df = dynamic_edges_and_gates(graph_sources)
    pred = load_model_predictions()
    per_year, mean = build_summary(pred)
    fig = build_figure(geojson, zones_df, pred, edges_by_year, gate_df)
    fig_html = pio.to_html(fig, full_html=False, include_plotlyjs=True)
    mean_bar, year_bar = build_bar_figures(per_year, mean)
    mean_bar_html = pio.to_html(mean_bar, full_html=False, include_plotlyjs=False)
    year_bar_html = pio.to_html(year_bar, full_html=False, include_plotlyjs=False)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>HERALD V2 - France Dynamic Graph Map</title>
<style>
body {{ margin:0; background:#f6f3ee; font-family: Arial, sans-serif; color:#232323; }}
.wrap {{ padding: 18px 24px 28px 24px; }}
h1 {{ margin: 0 0 6px 0; font-size: 26px; }}
.note {{ max-width: 1520px; line-height: 1.4; color:#444; font-size: 14px; margin-bottom: 14px; }}
.layout {{ display: grid; grid-template-columns: minmax(760px, 1120px) minmax(360px, 460px); gap: 18px; align-items: start; }}
.map-panel {{ min-width: 0; }}
.side-panel {{ position: sticky; top: 12px; }}
.panel {{ background: rgba(255,255,255,0.9); border:1px solid #ddd; border-radius:10px; padding:14px; margin:0 0 14px 0; max-width:1120px; box-shadow: 0 2px 8px rgba(40,30,20,0.06); }}
table {{ border-collapse: collapse; font-size: 13px; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ background:#eee6dd; }}
.legend-line {{ display:flex; gap:16px; flex-wrap:wrap; font-size:13px; }}
.swatch {{ display:inline-block; width:12px; height:12px; border-radius:2px; margin-right:4px; vertical-align:-1px; }}
@media (max-width: 1220px) {{ .layout {{ grid-template-columns: 1fr; }} .side-panel {{ position: static; }} }}
</style>
</head>
<body>
<div class="wrap">
<h1>HERALD V2 - France ZE2020 Dynamic Graph Map</h1>
<div class="note">
Use the dropdown on the map to switch year/model. Polygons are real ZE2020 geometries from the local INSEE shapefile.
Colors show signed prediction error: blue = underprediction, red = overprediction.
The line overlay is the HERALD V2 effective graph for the selected year, built from yearly gate weights.
</div>
<div class="layout">
<div class="map-panel">
{fig_html}
</div>
<aside class="side-panel">
<div class="panel">
<b>Mean WMAPE 2021-2024</b>
{mean_bar_html}
</div>
<div class="panel legend-line">
<span><span class="swatch" style="background:#5b5b5b"></span>Self gate</span>
<span><span class="swatch" style="background:#3b6ea8"></span>Geo gate</span>
<span><span class="swatch" style="background:#3c9d65"></span>Mobility gate</span>
<span><span class="swatch" style="background:#d0793f"></span>Adaptive gate</span>
</div>
<div class="panel">
<b>WMAPE by year</b>
{year_bar_html}
</div>
<div class="panel">
<b>Numeric values</b>
{html_table(per_year.pivot(index="model", columns="year", values="wmape").reset_index())}
</div>
</aside>
</div>
</div>
</body>
</html>"""
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Saved: {OUT_HTML}")
    print(mean.to_string(index=False))


if __name__ == "__main__":
    main()
