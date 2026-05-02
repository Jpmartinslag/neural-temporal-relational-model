"""
Interactive HERALD dashboard for fine-tuning analysis.

Reads the current HERALD V3 prediction/internals artifacts and writes one
offline Plotly HTML dashboard with:
  - annual WMAPE comparison against Ridge/DCRNN/STGNN,
  - ablation bars and seed stability,
  - France ZE2020 map with HERALD dynamic graph A_t by year,
  - gate/message-share diagnostics,
  - training loss curves when history CSVs are available.

Output:
  reports/figures/herald_v3_finetuning_dashboard_v1.html
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

import herald_map_utils as map_utils


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

OUT_HTML = FIGURES / "herald_v3_finetuning_dashboard_v1.html"

YEARS = [2021, 2022, 2023, 2024]
SEEDS = [0, 7, 42]
ABLATION_ORDER = [
    "full",
    "dynamic_adaptive_no_regime",
    "dynamic_adaptive_no_smooth",
    "static_adaptive",
    "fixed_geo_mob_only",
    "self_only",
    "dynamic_adaptive_no_quarterly",
]

MODEL_LABELS = {
    "Ridge_AR": "Ridge AR",
    "DCRNN_V1": "DCRNN",
    "STGNN_V1": "Dynamic STGNN",
    "HERALD": "HERALD",
    "full": "HERALD complet",
    "dynamic_adaptive_no_regime": "sans régime",
    "dynamic_adaptive_no_smooth": "sans lissage",
    "static_adaptive": "adaptatif statique",
    "fixed_geo_mob_only": "graphe fixe geo+mob",
    "self_only": "signal local seul",
    "dynamic_adaptive_no_quarterly": "sans trimestriel",
}

MODEL_COLORS = {
    "Ridge_AR": "#6d6d6d",
    "DCRNN_V1": "#7aa6c2",
    "STGNN_V1": "#2e6f9e",
    "HERALD": "#b75f29",
    "full": "#b75f29",
    "dynamic_adaptive_no_regime": "#c9854d",
    "dynamic_adaptive_no_smooth": "#d5a06c",
    "static_adaptive": "#7f7f9f",
    "fixed_geo_mob_only": "#709c78",
    "self_only": "#a55d66",
    "dynamic_adaptive_no_quarterly": "#9b7a3e",
}


def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 0 else np.nan


def load_baseline_predictions():
    frames = []
    base_path = PROCESSED / "dynamic_feature_panel_baseline_predictions_v1.csv"
    if base_path.exists():
        base = pd.read_csv(base_path)
        ridge = base[base["model"] == "Ridge_AR"].copy()
        if not ridge.empty:
            ridge["model"] = "Ridge_AR"
            ridge["seed"] = -1
            ridge["ablation"] = "baseline"
            frames.append(ridge)

    for seed in SEEDS:
        path = PROCESSED / f"dynamic_stgnn_model_predictions_seed_{seed}_v1.csv"
        if not path.exists():
            continue
        pred = pd.read_csv(path)
        for raw_model, model in [
            ("dcrnn_residual", "DCRNN_V1"),
            ("dynamic_stgnn_residual", "STGNN_V1"),
        ]:
            sub = pred[pred["model"] == raw_model].copy()
            if not sub.empty:
                sub["model"] = model
                sub["seed"] = seed
                sub["ablation"] = "baseline"
                frames.append(sub)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_v3_predictions():
    frames = []
    for path in sorted(glob.glob(str(PROCESSED / "herald_v3_predictions_*_v1.csv"))):
        name = Path(path).name
        match = re.match(r"herald_v3_predictions_(.*)_seed_(\d+)_v1\.csv", name)
        if not match:
            continue
        ablation, seed = match.group(1), int(match.group(2))
        frame = pd.read_csv(path)
        frame["ablation"] = ablation
        frame["seed"] = seed
        frame["model"] = "HERALD"
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def compute_metrics(pred):
    rows = []
    for keys, group in pred.groupby(["model", "ablation", "seed", "target_year"]):
        model, ablation, seed, year = keys
        rows.append({
            "model": model,
            "ablation": ablation,
            "seed": int(seed),
            "target_year": int(year),
            "wmape": wmape(group["y_true"], group["y_pred"]),
            "n": len(group),
        })
    return pd.DataFrame(rows)


def build_metrics():
    baselines = load_baseline_predictions()
    herald = load_v3_predictions()
    frames = []
    if not baselines.empty:
        frames.append(baselines)
    if not herald.empty:
        frames.append(herald)
    if not frames:
        raise FileNotFoundError("No prediction artifacts found.")
    pred = pd.concat(frames, ignore_index=True)
    metrics = compute_metrics(pred)
    return pred, metrics


def fig_model_comparison(metrics):
    rows = []
    baseline_models = ["Ridge_AR", "DCRNN_V1", "STGNN_V1"]
    for model in baseline_models:
        sub = metrics[metrics["model"] == model]
        if sub.empty:
            continue
        by_seed = sub.groupby("seed")["wmape"].mean()
        rows.append({"label": MODEL_LABELS[model], "key": model, "mean": by_seed.mean(), "std": by_seed.std(ddof=1)})

    full = metrics[(metrics["model"] == "HERALD") & (metrics["ablation"] == "full")]
    if not full.empty:
        by_seed = full.groupby("seed")["wmape"].mean()
        rows.append({"label": "HERALD", "key": "HERALD", "mean": by_seed.mean(), "std": by_seed.std(ddof=1)})

    frame = pd.DataFrame(rows).sort_values("mean")
    fig = go.Figure(go.Bar(
        x=frame["mean"],
        y=frame["label"],
        orientation="h",
        error_x=dict(type="data", array=frame["std"].fillna(0.0), visible=True),
        marker_color=[MODEL_COLORS.get(k, "#999") for k in frame["key"]],
        text=[f"{v:.4f}" for v in frame["mean"]],
        textposition="outside",
        hovertemplate="%{y}<br>WMAPE moyen : %{x:.6f}<extra></extra>",
    ))
    fig.update_layout(
        title="Comparaison principale des modèles - WMAPE moyen 2021-2024",
        template="plotly_white",
        height=310,
        margin=dict(l=125, r=30, t=60, b=40),
        xaxis_title="WMAPE",
        yaxis_title=None,
        showlegend=False,
    )
    return fig


def fig_yearly_model_comparison(metrics):
    fig = go.Figure()
    for model in ["Ridge_AR", "DCRNN_V1", "STGNN_V1"]:
        sub = metrics[metrics["model"] == model].groupby("target_year", as_index=False)["wmape"].mean()
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["target_year"],
            y=sub["wmape"],
            mode="lines+markers",
            name=MODEL_LABELS[model],
            line=dict(color=MODEL_COLORS.get(model), width=2),
        ))
    full = metrics[(metrics["model"] == "HERALD") & (metrics["ablation"] == "full")]
    if not full.empty:
        sub = full.groupby("target_year", as_index=False)["wmape"].mean()
        fig.add_trace(go.Scatter(
            x=sub["target_year"],
            y=sub["wmape"],
            mode="lines+markers",
            name="HERALD",
            line=dict(color=MODEL_COLORS["HERALD"], width=4),
        ))
    fig.update_layout(
        title="WMAPE annuel - HERALD vs modèles de référence",
        template="plotly_white",
        height=330,
        margin=dict(l=55, r=20, t=60, b=55),
        xaxis=dict(title="Année prédite", dtick=1),
        yaxis_title="WMAPE",
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def fig_ablation_bars(metrics):
    herald = metrics[metrics["model"] == "HERALD"]
    rows = []
    for ablation in ABLATION_ORDER:
        sub = herald[herald["ablation"] == ablation]
        if sub.empty:
            continue
        by_seed = sub.groupby("seed")["wmape"].mean()
        rows.append({
            "ablation": ablation,
            "label": MODEL_LABELS.get(ablation, ablation),
            "mean": by_seed.mean(),
            "std": by_seed.std(ddof=1),
        })
    frame = pd.DataFrame(rows).sort_values("mean")
    fig = go.Figure(go.Bar(
        x=frame["mean"],
        y=frame["label"],
        orientation="h",
        error_x=dict(type="data", array=frame["std"].fillna(0.0), visible=True),
        marker_color=[MODEL_COLORS.get(a, "#999") for a in frame["ablation"]],
        text=[f"{v:.4f}" for v in frame["mean"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Ablations HERALD - WMAPE moyen avec écart-type des seeds",
        template="plotly_white",
        height=380,
        margin=dict(l=165, r=30, t=60, b=40),
        xaxis_title="WMAPE",
        yaxis_title=None,
    )
    return fig


def fig_yearly_ablation_heatmap(metrics):
    herald = metrics[metrics["model"] == "HERALD"]
    pivot = (
        herald.groupby(["ablation", "target_year"])["wmape"]
        .mean()
        .unstack()
        .reindex([a for a in ABLATION_ORDER if a in herald["ablation"].unique()])
    )
    labels = [MODEL_LABELS.get(a, a) for a in pivot.index]
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=labels,
        colorscale="YlOrRd",
        text=np.vectorize(lambda x: f"{x:.4f}")(pivot.values),
        texttemplate="%{text}",
        colorbar=dict(title="WMAPE"),
    ))
    fig.update_layout(
        title="WMAPE des ablations par année",
        template="plotly_white",
        height=380,
        margin=dict(l=165, r=25, t=60, b=45),
        xaxis_title="Année prédite",
        yaxis_title=None,
    )
    return fig


def fig_seed_stability(metrics):
    herald = metrics[metrics["model"] == "HERALD"]
    rows = (
        herald.groupby(["ablation", "seed"])["wmape"]
        .mean()
        .reset_index()
    )
    fig = go.Figure()
    for ablation in ABLATION_ORDER:
        sub = rows[rows["ablation"] == ablation].sort_values("seed")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["seed"].astype(str),
            y=sub["wmape"],
            mode="lines+markers",
            name=MODEL_LABELS.get(ablation, ablation),
            line=dict(color=MODEL_COLORS.get(ablation, "#999"), width=3 if ablation == "full" else 2),
        ))
    fig.update_layout(
        title="Stabilité entre seeds - une dispersion faible est préférable",
        template="plotly_white",
        height=340,
        margin=dict(l=55, r=20, t=60, b=55),
        xaxis_title="Seed",
        yaxis_title="WMAPE moyen",
        legend=dict(orientation="h", y=-0.28),
    )
    return fig


def load_v3_graph_full_average():
    mats, gates = [], []
    years = None
    zones = None
    gammas = []
    for seed in SEEDS:
        path = PROCESSED / f"herald_v3_internals_full_seed_{seed}_v1.npz"
        if not path.exists():
            continue
        data = np.load(path, allow_pickle=True)
        mats.append(data["dynamic_adj"])
        gates.append(data["gate_values"])
        years = data["years"].astype(int).tolist()
        zones = data["node_order"].astype(int)
        gammas.append((float(data["gamma_geo"][0]), float(data["gamma_mob"][0])))
    if not mats:
        return None
    return {
        "A": np.mean(mats, axis=0),
        "gate": np.mean(gates, axis=0).squeeze(-1),
        "years": years,
        "zones": zones,
        "gammas": np.asarray(gammas),
    }


def dynamic_edges(graph, year, top_k=600):
    year_to_idx = {int(y): i for i, y in enumerate(graph["years"])}
    t = year_to_idx[int(year)]
    # g is local-share. Use (1-g) as message-share to scale dynamic edges.
    message_share = 1.0 - graph["gate"][t]
    effective = graph["A"][t] * message_share[:, None]
    return map_utils.top_edges_from_matrix(effective, graph["zones"], top_k=top_k, min_weight=1e-8)


def load_map_predictions(pred):
    full = pred[(pred["model"] == "HERALD") & (pred["ablation"] == "full")].copy()
    if full.empty:
        raise FileNotFoundError("No HERALD full predictions found.")
    full = (
        full.groupby(["target_year", "ZE2020"], as_index=False)
        .agg(y_true=("y_true", "mean"), y_pred=("y_pred", "mean"))
    )
    full["ze2020_int"] = full["ZE2020"].astype(int)
    full["signed_error_pct"] = 100.0 * (full["y_pred"] - full["y_true"]) / full["y_true"].clip(lower=1.0)
    full["abs_error"] = (full["y_pred"] - full["y_true"]).abs()
    full["model"] = "HERALD"
    return full


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
        line=dict(color="rgba(74,42,18,0.62)", width=1.45),
        name=f"HERALD V3 dynamic graph {year}",
        hoverinfo="skip",
        visible=visible,
    )


def graph_only_edge_trace(edges, zones_df, year, visible=False):
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
        line=dict(color="rgba(165,81,30,0.58)", width=1.7),
        name=f"Top dynamic edges {year}",
        hoverinfo="skip",
        visible=visible,
    )


def graph_only_node_trace(graph, zones_df, year, visible=False):
    year_to_idx = {int(y): i for i, y in enumerate(graph["years"])}
    t = year_to_idx[int(year)]
    message_share = 1.0 - graph["gate"][t]
    node_frame = pd.DataFrame({
        "ze2020_int": graph["zones"].astype(int),
        "message_share": message_share,
    })
    merged = zones_df.merge(node_frame, on="ze2020_int", how="inner")
    return go.Scattergeo(
        lon=merged["lon"],
        lat=merged["lat"],
        mode="markers",
        marker=dict(
            size=5 + 22 * merged["message_share"],
            color=merged["message_share"],
            colorscale="YlOrBr",
            cmin=0,
            cmax=max(0.25, float(np.nanpercentile(message_share, 98))),
            line=dict(width=0.45, color="rgba(60,40,24,0.55)"),
            colorbar=dict(title="Part<br>graphe"),
        ),
        customdata=np.stack(
            [
                merged["libze2020"].astype(str),
                merged["ze2020_int"],
                merged["message_share"],
            ],
            axis=1,
        ),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "ZE2020: %{customdata[1]}<br>"
            "Part graphe/message : %{customdata[2]:.3f}<extra></extra>"
        ),
        name=f"Part graphe {year}",
        visible=visible,
    )


def error_trace(geojson, zones_df, pred, year, cmax, visible=False):
    sub = pred[pred["target_year"] == year]
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
        colorscale=map_utils.ERROR_COLORSCALE,
        zmin=-cmax,
        zmax=cmax,
        marker_line_color="rgba(255,255,255,0.85)",
        marker_line_width=0.35,
        colorbar=dict(title="Erreur<br>signée %"),
        name=f"HERALD {year}",
        customdata=custom,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "ZE2020: %{location}<br>"
            "Observé : %{customdata[1]:,.0f}<br>"
            "Prédit : %{customdata[2]:,.0f}<br>"
            "Erreur signée : %{z:+.2f}%<br>"
            "Erreur absolue : %{customdata[3]:,.0f}<extra></extra>"
        ),
        visible=visible,
    )


def gate_trace(geojson, zones_df, graph, year, visible=False):
    year_to_idx = {int(y): i for i, y in enumerate(graph["years"])}
    t = year_to_idx[int(year)]
    frame = pd.DataFrame({
        "ze2020_int": graph["zones"].astype(int),
        "local_share": graph["gate"][t],
        "message_share": 1.0 - graph["gate"][t],
    })
    merged = zones_df.merge(frame, on="ze2020_int", how="left")
    custom = np.stack(
        [
            merged["libze2020"].astype(str),
            merged["local_share"].fillna(np.nan),
            merged["message_share"].fillna(np.nan),
        ],
        axis=1,
    )
    return go.Choropleth(
        geojson=geojson,
        locations=merged["ze2020"],
        z=merged["message_share"],
        featureidkey="properties.ze2020",
        colorscale="Tealgrn",
        zmin=0,
        zmax=max(0.25, float(np.nanpercentile(frame["message_share"], 98))),
        marker_line_color="rgba(255,255,255,0.85)",
        marker_line_width=0.35,
        colorbar=dict(title="Part<br>graphe"),
        name=f"Part graphe {year}",
        customdata=custom,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "ZE2020: %{location}<br>"
            "Part locale/self : %{customdata[1]:.3f}<br>"
            "Part graphe/message : %{customdata[2]:.3f}<extra></extra>"
        ),
        visible=visible,
    )


def fig_dynamic_map(pred):
    graph = load_v3_graph_full_average()
    if graph is None:
        return None, None
    geojson, zones_df = map_utils.load_ze2020_geojson()
    map_pred = load_map_predictions(pred)
    cmax = max(float(np.nanpercentile(np.abs(map_pred["signed_error_pct"]), 96)), 8.0)

    fig = go.Figure()
    meta = []
    for year in YEARS:
        visible = year == 2024
        fig.add_trace(error_trace(geojson, zones_df, map_pred, year, cmax, visible=visible))
        meta.append(("error", year))
    for year in YEARS:
        fig.add_trace(edge_trace(dynamic_edges(graph, year), zones_df, year, visible=(year == 2024)))
        meta.append(("edge", year))
    for year in YEARS:
        fig.add_trace(gate_trace(geojson, zones_df, graph, year, visible=False))
        meta.append(("gate", year))

    buttons = []
    for idx, (kind, year) in enumerate(meta):
        if kind == "edge":
            continue
        visible = [False] * len(meta)
        visible[idx] = True
        visible[meta.index(("edge", year))] = True
        if kind == "error":
            sub = map_pred[map_pred["target_year"] == year]
            title = f"HERALD V3 signed error + dynamic graph - {year} (WMAPE {wmape(sub.y_true, sub.y_pred):.4f})"
            label = f"{year} | erreur de prédiction"
        else:
            title = f"HERALD V3 - part graphe/message + graphe dynamique - {year}"
            label = f"{year} | part graphe"
        buttons.append(dict(label=label, method="update", args=[{"visible": visible}, {"title": title}]))

    fig.update_layout(
        title="HERALD V3 signed error + dynamic graph - 2024",
        geo=dict(
            fitbounds="locations",
            visible=False,
            projection_type="mercator",
            bgcolor="#f6f3ee",
            landcolor="#f6f3ee",
            lakecolor="#f6f3ee",
        ),
        updatemenus=[
            dict(buttons=buttons, direction="down", x=0.01, y=1.08, xanchor="left", yanchor="top", bgcolor="white")
        ],
        margin=dict(l=10, r=10, t=80, b=10),
        width=1120,
        height=820,
        paper_bgcolor="#f6f3ee",
        font=dict(family="Arial", color="#232323"),
    )
    return fig, graph


def fig_dynamic_graph_france(graph):
    if graph is None:
        return None
    geojson, zones_df = map_utils.load_ze2020_geojson()
    fig = go.Figure()
    meta = []

    # Pale territorial background so the graph is visible above the real France map.
    for year in YEARS:
        visible = year == 2024
        fig.add_trace(go.Choropleth(
            geojson=geojson,
            locations=zones_df["ze2020"],
            z=np.zeros(len(zones_df)),
            featureidkey="properties.ze2020",
            colorscale=[[0, "#efe6d8"], [1, "#efe6d8"]],
            showscale=False,
            marker_line_color="rgba(255,255,255,0.88)",
            marker_line_width=0.45,
            hoverinfo="skip",
            name=f"ZE2020 background {year}",
            visible=visible,
        ))
        meta.append(("background", year))

    for year in YEARS:
        visible = year == 2024
        fig.add_trace(graph_only_edge_trace(dynamic_edges(graph, year, top_k=850), zones_df, year, visible=visible))
        meta.append(("edge", year))

    for year in YEARS:
        visible = year == 2024
        fig.add_trace(graph_only_node_trace(graph, zones_df, year, visible=visible))
        meta.append(("node", year))

    buttons = []
    for year in YEARS:
        visible = [False] * len(meta)
        for idx, (_kind, trace_year) in enumerate(meta):
            if trace_year == year:
                visible[idx] = True
        buttons.append(dict(
            label=str(year),
            method="update",
            args=[{"visible": visible}, {"title": f"HERALD V3 - graphe adaptatif dynamique sur la France ZE2020 - {year}"}],
        ))

    fig.update_layout(
        title="HERALD V3 - graphe adaptatif dynamique sur la France ZE2020 - 2024",
        geo=dict(
            fitbounds="locations",
            visible=False,
            projection_type="mercator",
            bgcolor="#f6f3ee",
            landcolor="#f6f3ee",
            lakecolor="#f6f3ee",
        ),
        updatemenus=[
            dict(buttons=buttons, direction="down", x=0.01, y=1.08, xanchor="left", yanchor="top", bgcolor="white")
        ],
        annotations=[
            dict(
                text="Arêtes = principaux liens dynamiques A_t pondérés par la part graphe/message. Taille/couleur des nœuds = intensité d'utilisation du signal de graphe par HERALD.",
                x=0.5,
                y=-0.04,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=12, color="#5b4a3b"),
            )
        ],
        margin=dict(l=10, r=10, t=80, b=50),
        width=1120,
        height=860,
        paper_bgcolor="#f6f3ee",
        font=dict(family="Arial", color="#232323"),
    )
    return fig


def fig_graph_dynamics(graph):
    if graph is None:
        return None
    years = graph["years"]
    A = graph["A"]
    diffs = [np.sum((A[i] - A[i - 1]) ** 2) for i in range(1, len(A))]
    fig = go.Figure(go.Bar(
        x=[f"{years[i-1]}→{years[i]}" for i in range(1, len(years))],
        y=diffs,
        marker_color=["#b75f29" if years[i] in YEARS else "#b9a58f" for i in range(1, len(years))],
        hovertemplate="%{x}<br>||A_t - A_t-1||² : %{y:.6f}<extra></extra>",
    ))
    fig.update_layout(
        title="Mouvement du graphe dynamique par transition annuelle",
        template="plotly_white",
        height=320,
        margin=dict(l=60, r=20, t=60, b=80),
        xaxis_title="Transition",
        yaxis_title="Variation de Frobenius au carré",
    )
    return fig


def fig_gate_message_share(graph):
    if graph is None:
        return None
    rows = []
    for i, year in enumerate(graph["years"]):
        if int(year) < 2018:
            continue
        local = graph["gate"][i]
        rows.append({
            "year": int(year),
            "local_share": float(local.mean()),
            "message_share": float((1.0 - local).mean()),
            "message_p90": float(np.percentile(1.0 - local, 90)),
        })
    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["year"], y=df["local_share"], mode="lines+markers", name="Part locale/self", line=dict(color="#5b5b5b", width=3)))
    fig.add_trace(go.Scatter(x=df["year"], y=df["message_share"], mode="lines+markers", name="Part graphe/message", line=dict(color="#b75f29", width=3)))
    fig.add_trace(go.Scatter(x=df["year"], y=df["message_p90"], mode="lines+markers", name="Part graphe p90", line=dict(color="#d5a06c", width=2, dash="dot")))
    fig.update_layout(
        title="Comportement du gate dans le temps",
        template="plotly_white",
        height=320,
        margin=dict(l=55, r=20, t=60, b=55),
        xaxis=dict(title="Année", dtick=1),
        yaxis_title="Part",
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def load_training_history():
    frames = []
    for path in sorted(glob.glob(str(REPORTS / "herald_v3_training_history_*_v1.csv"))):
        frame = pd.read_csv(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fig_loss_curves():
    hist = load_training_history()
    if hist.empty:
        return None
    # Plot the latest epoch cadence compactly: mean across folds per epoch.
    agg = (
        hist.groupby(["ablation", "seed", "epoch"], as_index=False)
        .agg(loss_total=("loss_total", "mean"), loss_main=("loss_main", "mean"), loss_smooth=("loss_smooth", "mean"))
    )
    fig = go.Figure()
    for ablation in ABLATION_ORDER:
        sub = agg[agg["ablation"] == ablation]
        if sub.empty:
            continue
        by_epoch = sub.groupby("epoch", as_index=False)["loss_total"].mean()
        fig.add_trace(go.Scatter(
            x=by_epoch["epoch"],
            y=by_epoch["loss_total"],
            mode="lines",
            name=MODEL_LABELS.get(ablation, ablation),
            line=dict(color=MODEL_COLORS.get(ablation, "#999"), width=3 if ablation == "full" else 1.8),
        ))
    fig.update_layout(
        title="Training learning curves - mean total loss across folds/seeds",
        template="plotly_white",
        height=380,
        margin=dict(l=65, r=20, t=60, b=55),
        xaxis_title="Epoch",
        yaxis_title="Training loss",
        legend=dict(orientation="h", y=-0.28),
    )
    return fig


def fig_loss_components():
    hist = load_training_history()
    if hist.empty:
        return None
    full = hist[hist["ablation"] == "full"]
    if full.empty:
        return None
    agg = (
        full.groupby("epoch", as_index=False)
        .agg(loss_total=("loss_total", "mean"), loss_main=("loss_main", "mean"), loss_sector=("loss_sector", "mean"), loss_smooth=("loss_smooth", "mean"))
    )
    fig = go.Figure()
    for col, color in [("loss_total", "#b75f29"), ("loss_main", "#2e6f9e"), ("loss_sector", "#709c78"), ("loss_smooth", "#7f7f9f")]:
        fig.add_trace(go.Scatter(x=agg["epoch"], y=agg[col], mode="lines", name=col, line=dict(color=color, width=3 if col == "loss_total" else 2)))
    fig.update_layout(
        title="HERALD full loss components",
        template="plotly_white",
        height=330,
        margin=dict(l=65, r=20, t=60, b=55),
        xaxis_title="Epoch",
        yaxis_title="Loss component",
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def load_statistical_evidence():
    paths = {
        "dm": REPORTS / "herald_v3_dm_tests_v1.csv",
        "strata": REPORTS / "herald_v3_zone_strata_v1.csv",
        "gamma": REPORTS / "herald_v3_gamma_stability_v1.csv",
        "neighbors": REPORTS / "herald_v3_top_neighbors_v1.csv",
    }
    return {key: pd.read_csv(path) if path.exists() else pd.DataFrame() for key, path in paths.items()}


def fig_dm_tests(evidence):
    dm = evidence["dm"]
    if dm.empty:
        return None
    frame = dm[
        (dm["loss"] == "absolute_error")
        & (dm["comparison"].str.startswith("HERALD_full_mean_vs_Ridge_AR"))
    ].copy()
    frame["label"] = frame["comparison"].str.replace("HERALD_full_mean_vs_Ridge_AR_", "", regex=False)
    frame.loc[frame["label"] == "HERALD_full_mean_vs_Ridge_AR", "label"] = "Global"
    frame["minus_log10_p"] = -np.log10(frame["p_value_normal_approx"].clip(lower=1e-300))
    order = ["Global", "2021", "2022", "2023", "2024"]
    frame["label"] = pd.Categorical(frame["label"], categories=order, ordered=True)
    frame = frame.sort_values("label")
    fig = go.Figure(go.Bar(
        x=frame["label"].astype(str),
        y=frame["minus_log10_p"],
        marker_color="#b75f29",
        text=[f"p={p:.1e}" for p in frame["p_value_normal_approx"]],
        textposition="outside",
        hovertemplate="%{x}<br>-log10(p): %{y:.2f}<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        title="Test Diebold-Mariano vs Ridge AR - significativité du gain",
        template="plotly_white",
        height=330,
        margin=dict(l=60, r=20, t=65, b=50),
        xaxis_title="Échantillon",
        yaxis_title="-log10(p-value)",
    )
    return fig


def fig_zone_strata(evidence):
    strata = evidence["strata"]
    if strata.empty:
        return None
    frame = strata[strata["stratification"] == "size_stratum"].copy()
    order = ["small", "medium_low", "medium_high", "large"]
    labels = {
        "small": "petites ZE",
        "medium_low": "moyennes-",
        "medium_high": "moyennes+",
        "large": "grandes ZE",
    }
    frame["stratum"] = pd.Categorical(frame["stratum"], categories=order, ordered=True)
    frame = frame.sort_values("stratum")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[labels.get(stratum, stratum) for stratum in frame["stratum"].astype(str)],
        y=frame["ridge_wmape"],
        name="Ridge AR",
        marker_color=MODEL_COLORS["Ridge_AR"],
        hovertemplate="%{x}<br>Ridge WMAPE: %{y:.6f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=[labels.get(stratum, stratum) for stratum in frame["stratum"].astype(str)],
        y=frame["herald_wmape"],
        name="HERALD",
        marker_color=MODEL_COLORS["HERALD"],
        hovertemplate="%{x}<br>HERALD WMAPE: %{y:.6f}<extra></extra>",
    ))
    fig.update_layout(
        title="Généralisation par taille de zone",
        template="plotly_white",
        barmode="group",
        height=350,
        margin=dict(l=55, r=20, t=65, b=55),
        xaxis_title="Strate territoriale",
        yaxis_title="WMAPE",
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


def fig_gamma_stability(evidence):
    gamma = evidence["gamma"]
    if gamma.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=gamma["seed"].astype(str),
        y=gamma["gamma_geo"],
        name="γ géographique",
        marker_color="#7f7f9f",
    ))
    fig.add_trace(go.Bar(
        x=gamma["seed"].astype(str),
        y=gamma["gamma_mob"],
        name="γ mobilité",
        marker_color="#b75f29",
    ))
    fig.update_layout(
        title="Stabilité des priors appris : mobilité vs géographie",
        template="plotly_white",
        barmode="group",
        height=330,
        margin=dict(l=55, r=20, t=65, b=55),
        xaxis_title="Seed",
        yaxis_title="Poids appris du prior",
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


def fig_top_neighbors_table(evidence):
    neighbors = evidence["neighbors"]
    if neighbors.empty:
        return None
    frame = neighbors[(neighbors["target_year"] == 2024) & (neighbors["rank"] <= 5)].copy()
    frame = frame[["source_city", "rank", "neighbor_name", "neighbor_ze2020", "weight"]]
    frame["weight"] = frame["weight"].map(lambda value: f"{value:.4f}")
    fig = go.Figure(go.Table(
        header=dict(
            values=["Zone source", "Rang", "Voisin adaptatif", "ZE2020", "Poids"],
            fill_color="#e7d4bd",
            align="left",
            font=dict(color="#2b2118", size=12),
        ),
        cells=dict(
            values=[frame[col] for col in frame.columns],
            fill_color="#fffaf2",
            align="left",
            height=24,
            font=dict(color="#2b2118", size=11),
        ),
    ))
    fig.update_layout(
        title="Top-5 voisins adaptatifs appris en 2024",
        height=430,
        margin=dict(l=15, r=15, t=55, b=15),
    )
    return fig


def to_html(fig, include_plotlyjs=False):
    if fig is None:
        return '<div class="missing">Information indisponible pour les runs actuels. Relancer les entraînements récents si nécessaire.</div>'
    return pio.to_html(fig, full_html=False, include_plotlyjs=include_plotlyjs)


CAPTIONS = {
    "model_comparison": (
        "Ce graphique compare la performance moyenne 2021-2024 de HERALD avec les références Ridge AR, DCRNN et Dynamic STGNN.",
        "Il sert à vérifier si la nouvelle architecture apporte un gain prédictif réel par rapport aux baselines du problème."
    ),
    "yearly_model_comparison": (
        "Cette courbe montre le WMAPE année par année pour les modèles principaux.",
        "Elle permet de voir si le gain de HERALD est régulier ou concentré sur une seule année de test."
    ),
    "ablation_bars": (
        "Ce graphique compare HERALD complet avec ses ablations : sans trimestriel, sans lissage, graphe statique, graphe fixe et signal local seul.",
        "Il sert à identifier quels mécanismes de l'architecture contribuent vraiment à la performance."
    ),
    "seed_stability": (
        "Cette figure montre la dispersion du WMAPE entre les seeds 0, 7 et 42.",
        "Elle vérifie que le résultat n'est pas seulement un accident d'initialisation aléatoire."
    ),
    "yearly_ablation_heatmap": (
        "Cette carte thermique détaille le WMAPE de chaque ablation pour chaque année cible.",
        "Elle permet de repérer les années où un composant aide, échoue ou devient instable."
    ),
    "dynamic_graph_france": (
        "Cette carte montre le graphe adaptatif dynamique appris par HERALD sur les zones d'emploi françaises.",
        "Elle sert à inspecter visuellement si le modèle utilise des liens territoriaux plausibles et si ces liens changent selon l'année."
    ),
    "dynamic_map": (
        "Cette carte superpose les erreurs signées de prévision et les principaux liens dynamiques du graphe.",
        "Elle permet de vérifier si les erreurs et l'utilisation du graphe se concentrent sur certains territoires."
    ),
    "graph_dynamics": (
        "Cette barre mesure la variation de la matrice dynamique A_t entre deux années consécutives.",
        "Elle teste si le graphe appris est réellement dynamique ou presque identique d'une année à l'autre."
    ),
    "gate_message_share": (
        "Cette courbe compare la part du signal local et la part du message passing dans le temps.",
        "Elle montre si HERALD prédit surtout par dynamique locale ou s'il exploite réellement les voisins du graphe."
    ),
    "dm_tests": (
        "Ce graphique affiche la significativité du test Diebold-Mariano contre Ridge AR.",
        "Il transforme l'écart de WMAPE en preuve statistique que les erreurs de HERALD sont plus faibles."
    ),
    "zone_strata": (
        "Ce graphique compare Ridge AR et HERALD par taille de zone d'emploi.",
        "Il vérifie que le gain ne vient pas uniquement des grandes métropoles ou des hubs économiques."
    ),
    "gamma_stability": (
        "Cette figure montre les poids appris des priors géographique et mobilité pour chaque seed.",
        "Elle teste la cohérence économique du graphe : HERALD doit apprendre quel prior structure le mieux les relations territoriales."
    ),
    "top_neighbors": (
        "Ce tableau liste les voisins adaptatifs les plus importants appris en 2024 pour quelques zones majeures.",
        "Il sert à vérifier qualitativement si les connexions apprises ont du sens économique et territorial."
    ),
    "loss_curves": (
        "Cette courbe montre la loss totale d'entraînement par époque pour les variantes HERALD.",
        "Elle permet de détecter sous-apprentissage, divergence ou convergence trop instable avant le fine-tuning V4."
    ),
    "loss_components": (
        "Cette courbe décompose la loss du modèle HERALD complet entre objectif principal, auxiliaire sectoriel et lissage du graphe.",
        "Elle vérifie que le gain ne vient pas d'une seule composante qui dominerait artificiellement l'entraînement."
    ),
}


def panel(key, html):
    what, why = CAPTIONS[key]
    return (
        f'<div class="panel">{html}'
        f'<div class="caption"><b>Ce que montre le graphique :</b> {what}<br>'
        f'<b>Pourquoi il a été fait :</b> {why}</div></div>'
    )


def wide_panel(key, html):
    what, why = CAPTIONS[key]
    return (
        f'<div class="panel wide">{html}'
        f'<div class="caption"><b>Ce que montre le graphique :</b> {what}<br>'
        f'<b>Pourquoi il a été fait :</b> {why}</div></div>'
    )


def build_dashboard(figs, graph):
    first = True
    html_figs = {}
    for key, fig in figs.items():
        html_figs[key] = to_html(fig, include_plotlyjs=first)
        first = False

    if graph is not None:
        gamma = graph["gammas"]
        gamma_note = (
            f"moyenne γ_geo={gamma[:,0].mean():.3f}, moyenne γ_mob={gamma[:,1].mean():.3f}. "
            "Un γ_mob plus élevé indique que le graphe appris s'ancre davantage dans la mobilité domicile-travail que dans la contiguïté géographique."
        )
    else:
        gamma_note = "Internals du graphe HERALD V3 introuvables."

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>HERALD V3 - Tableau de bord de validation et fine-tuning</title>
<style>
body {{ margin:0; background:#f6f3ee; color:#24211d; font-family: Arial, sans-serif; }}
.wrap {{ padding:22px 26px 34px 26px; }}
h1 {{ margin:0 0 6px 0; font-size:28px; }}
h2 {{ margin:34px 0 12px 0; color:#8f3f16; border-left:5px solid #b75f29; padding-left:10px; }}
.note {{ max-width:1500px; line-height:1.45; color:#51483f; font-size:14px; margin-bottom:18px; }}
.grid {{ display:grid; grid-template-columns: repeat(2, minmax(420px, 1fr)); gap:16px; align-items:start; }}
.panel {{ background:rgba(255,255,255,0.93); border:1px solid #ded4c8; border-radius:12px; padding:14px; box-shadow:0 2px 10px rgba(50,35,20,0.07); overflow-x:auto; }}
.wide {{ grid-column:1 / -1; }}
.caption {{ margin:8px 8px 2px 8px; padding:10px 12px; border-left:4px solid #b75f29; background:#fff6ea; color:#4b3b2f; font-size:13px; line-height:1.42; border-radius:8px; }}
.missing {{ padding:22px; color:#7a4d2f; background:#fff6ec; border:1px dashed #c48b60; border-radius:8px; }}
.namebox {{ background:linear-gradient(135deg,#fff8ef,#efe3d2); border:1px solid #d8b990; border-left:6px solid #b75f29; border-radius:12px; padding:14px 18px; margin:18px 0 20px 0; max-width:1500px; box-shadow:0 2px 10px rgba(50,35,20,0.06); }}
.namebox b {{ color:#8f3f16; }}
.namebox .line {{ margin:5px 0; }}
.namebox code {{ background:#f4e5d3; padding:1px 5px; border-radius:4px; }}
.summary-grid {{ display:grid; grid-template-columns: repeat(4, minmax(210px, 1fr)); gap:14px; margin:16px 0 24px 0; }}
.summary-card {{ background:rgba(255,255,255,0.95); border:1px solid #ded4c8; border-radius:12px; padding:14px 16px; box-shadow:0 2px 10px rgba(50,35,20,0.06); }}
.summary-card h3 {{ margin:0 0 8px 0; color:#8f3f16; font-size:16px; }}
.summary-card p {{ margin:0; line-height:1.38; font-size:13px; color:#3e352d; }}
.summary-card code {{ background:#f4e5d3; padding:1px 5px; border-radius:4px; }}
@media (max-width: 1050px) {{ .grid {{ grid-template-columns:1fr; }} }}
@media (max-width: 1250px) {{ .summary-grid {{ grid-template-columns: repeat(2, minmax(260px, 1fr)); }} }}
@media (max-width: 720px) {{ .summary-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
<h1>HERALD V3 - Tableau de bord de validation et fine-tuning</h1>
<div class="note">
Ce tableau de bord consolide les validations de HERALD avant la phase V4 : performance annuelle, ablations, stabilité des seeds, carte du graphe dynamique, preuves statistiques et courbes d'apprentissage.
<br><b>Diagnostic des priors du graphe :</b> {gamma_note}
</div>
<div class="namebox">
  <div class="line"><b>HERALD</b> = <b>H</b>eterogeneous <b>E</b>conomic <b>R</b>elational <b>A</b>daptive <b>L</b>earning for territorial <b>D</b>ynamics.</div>
  <div class="line">Le nom résume l'architecture : signaux territoriaux hétérogènes, relations économiques entre zones ZE2020, apprentissage adaptatif d'un graphe dynamique et prévision annuelle des dynamiques territoriales.</div>
  <div class="line"><code>HERALD complet</code> est le modèle proposé ; les variantes <code>self_only</code>, <code>static_adaptive</code> et <code>no_quarterly</code> sont des ablations destinées à vérifier quels mécanismes apportent réellement de la valeur prédictive.</div>
</div>

<h2>Lecture synthétique du modèle</h2>
<div class="summary-grid">
  <div class="summary-card">
    <h3>Question prédite</h3>
    <p>HERALD répond à la question : combien de créations d'établissements seront observées l'année suivante dans chaque zone d'emploi ZE2020 ? La sortie principale est <code>ŷ(i,t+1)</code> pour 280 zones.</p>
  </div>
  <div class="summary-card">
    <h3>Entrées annuelles</h3>
    <p>Le modèle reçoit des signaux forecast-safe : lags SIDE, croissance passée, stocks SIDE, signaux FLORES, indicateurs URSSAF, flags de disponibilité et contexte COVID/rebond.</p>
  </div>
  <div class="summary-card">
    <h3>Entrées trimestrielles</h3>
    <p>HERALD encode les trimestres URSSAF <code>Q1-Q3</code> de l'année <code>t-1</code>. Le quatrième trimestre est exclu pour rester forecast-safe.</p>
  </div>
  <div class="summary-card">
    <h3>Graphes utilisés</h3>
    <p>Deux priors structuraux sont fournis : contiguïté géographique et mobilité domicile-travail. HERALD apprend ensuite un graphe adaptatif dynamique <code>A_t</code> par année.</p>
  </div>
  <div class="summary-card">
    <h3>Formulation résiduelle</h3>
    <p>La prédiction finale est <code>Ridge_AR + residual_neural</code>. Le réseau apprend donc à corriger le baseline autorégressif, au lieu de repartir de zéro.</p>
  </div>
  <div class="summary-card">
    <h3>Entraînement</h3>
    <p>Validation walk-forward 2021-2024 : entraînement cumulatif jusqu'à l'année précédente, normalisation par fold, seeds 0/7/42 et ablations pour isoler les mécanismes.</p>
  </div>
  <div class="summary-card">
    <h3>Ce que V3 valide</h3>
    <p>V3 valide la valeur du message passing dynamique, du signal trimestriel URSSAF et du lissage temporel du graphe. Le graphe est plus ancré dans la mobilité que dans la géographie.</p>
  </div>
  <div class="summary-card">
    <h3>Comparaison</h3>
    <p>Le tableau compare HERALD à <code>Ridge AR</code>, <code>DCRNN</code> et <code>Dynamic STGNN</code>. Les ablations HERALD testent les mécanismes internes.</p>
  </div>
</div>

<h2>Performance prédictive</h2>
<div class="grid">
{panel("model_comparison", html_figs["model_comparison"])}
{panel("yearly_model_comparison", html_figs["yearly_model_comparison"])}
{panel("ablation_bars", html_figs["ablation_bars"])}
{panel("seed_stability", html_figs["seed_stability"])}
{wide_panel("yearly_ablation_heatmap", html_figs["yearly_ablation_heatmap"])}
</div>

<h2>Graphe adaptatif dynamique</h2>
<div class="grid">
{wide_panel("dynamic_graph_france", html_figs["dynamic_graph_france"])}
{wide_panel("dynamic_map", html_figs["dynamic_map"])}
{panel("graph_dynamics", html_figs["graph_dynamics"])}
{panel("gate_message_share", html_figs["gate_message_share"])}
</div>

<h2>Validation empirique du modèle</h2>
<div class="grid">
{panel("dm_tests", html_figs["dm_tests"])}
{panel("zone_strata", html_figs["zone_strata"])}
{panel("gamma_stability", html_figs["gamma_stability"])}
{panel("top_neighbors", html_figs["top_neighbors"])}
</div>

<h2>Courbes d'apprentissage pour le fine-tuning V4</h2>
<div class="grid">
{panel("loss_curves", html_figs["loss_curves"])}
{panel("loss_components", html_figs["loss_components"])}
</div>
</div>
</body>
</html>"""


def main():
    print("Loading prediction metrics...")
    pred, metrics = build_metrics()

    print("Building performance figures...")
    figs = {
        "model_comparison": fig_model_comparison(metrics),
        "yearly_model_comparison": fig_yearly_model_comparison(metrics),
        "ablation_bars": fig_ablation_bars(metrics),
        "seed_stability": fig_seed_stability(metrics),
        "yearly_ablation_heatmap": fig_yearly_ablation_heatmap(metrics),
    }

    print("Building dynamic graph figures...")
    dynamic_map, graph = fig_dynamic_map(pred)
    figs["dynamic_map"] = dynamic_map
    figs["dynamic_graph_france"] = fig_dynamic_graph_france(graph)
    figs["graph_dynamics"] = fig_graph_dynamics(graph)
    figs["gate_message_share"] = fig_gate_message_share(graph)

    print("Building loss figures...")
    figs["loss_curves"] = fig_loss_curves()
    figs["loss_components"] = fig_loss_components()

    print("Building statistical validation figures...")
    evidence = load_statistical_evidence()
    figs["dm_tests"] = fig_dm_tests(evidence)
    figs["zone_strata"] = fig_zone_strata(evidence)
    figs["gamma_stability"] = fig_gamma_stability(evidence)
    figs["top_neighbors"] = fig_top_neighbors_table(evidence)

    OUT_HTML.write_text(build_dashboard(figs, graph), encoding="utf-8")
    print(f"Saved: {OUT_HTML}")


if __name__ == "__main__":
    main()
