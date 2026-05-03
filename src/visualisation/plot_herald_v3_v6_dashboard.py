"""
Tableau de bord interactif de comparaison HERALD V3 vs V6.

Entrées par défaut :
  reports/herald_v3_metrics_v1.json
  hpc_results/patch_robustness_20260429/reports/herald_v6_metrics_section_E_final_ablation.json
  hpc_results/patch_robustness_20260429/reports/sector_baselines_v1.csv
  hpc_results/patch_robustness_20260429/reports/ridge_ar_official_v1.json

Sortie :
  reports/figures/herald_v3_v6_comparison_dashboard_v1.html
"""

from __future__ import annotations

import argparse
from glob import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

import plot_herald_v3_dashboard as v3dash


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

SEEDS = [0, 1, 7, 13, 42, 99, 123]
YEARS = [2021, 2022, 2023, 2024]

DEFAULT_V3 = REPORTS / "herald_v3_metrics_v1.json"
DEFAULT_HPC = ROOT / "hpc_results/patch_robustness_20260429"
DEFAULT_V6 = DEFAULT_HPC / "reports/herald_v6_metrics_section_E_final_ablation.json"
DEFAULT_V6_ABLATION = DEFAULT_HPC / "reports/herald_v6_metrics_section_E_final_ablation.json"
DEFAULT_SECTOR = DEFAULT_HPC / "reports/sector_baselines_v1.csv"
DEFAULT_RIDGE = DEFAULT_HPC / "reports/ridge_ar_official_v1.json"
DEFAULT_OUT = FIGURES / "herald_v3_v6_comparison_dashboard_v1.html"
DEFAULT_V6_DATA = DEFAULT_HPC / "section_E_final_ablation/data_processed"
DEFAULT_STGNN_GLOB = "dynamic_stgnn_model_metrics_seed_*_v1.json"
DEFAULT_TEMPORAL = ROOT / "hpc_results/final_model_comparison_20260429/temporal_baselines/reports/final_temporal_baselines_metrics_v1.json"
SECTORS_A10 = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
SECTOR_COLORS = {
    "BE": "#4c78a8",
    "FZ": "#f58518",
    "GI": "#54a24b",
    "JZ": "#e45756",
    "KZ": "#72b7b2",
    "LZ": "#b279a2",
    "MN": "#ff9da6",
    "OQ": "#9d755d",
    "RU": "#bab0ac",
}

COLORS = {
    "Naive lag-1": "#b8b8b8",
    "ARIMA local": "#8f8f8f",
    "Ridge AR": "#6d6d6d",
    "LSTM local": "#bc8f8f",
    "DCRNN residual": "#8b6f47",
    "Graph WaveNet residual": "#9a8bc2",
    "Dynamic STGNN V1": "#7a8fbd",
    "V3 full": "#2e6f9e",
    "V6 full": "#b75f29",
    "self_only": "#a55d66",
    "fixed_geo_mob_only": "#709c78",
    "no_regime_in_graph": "#9b7a3e",
    "static_adaptive": "#7f7f9f",
    "no_quarterly": "#c9854d",
    "no_sector_head": "#d5a06c",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def records_from_metrics(metrics: dict, source: str) -> pd.DataFrame:
    rows = []
    for key, value in metrics.items():
        if not isinstance(value, dict):
            continue
        wmape_value = value.get("total_wmape_mean", value.get("mean_wmape", np.nan))
        if not np.isfinite(wmape_value):
            continue
        per_year_raw = value.get("per_year_total", value.get("per_year", {}))
        if isinstance(per_year_raw, list):
            per_year = {int(row["target_year"]): row["wmape"] for row in per_year_raw}
        else:
            per_year = per_year_raw
        adj_diag = value.get("adj_diagnostics", [])
        gamma_geo = np.nan
        gamma_mob = np.nan
        if adj_diag:
            gamma_geo = adj_diag[-1].get("gamma_geo", np.nan)
            gamma_mob = adj_diag[-1].get("gamma_mob", np.nan)
        rows.append({
            "key": key,
            "source": source,
            "ablation": value.get("ablation", ""),
            "run_tag": value.get("run_tag", ""),
            "seed": value.get("seed", np.nan),
            "wmape": wmape_value,
            "sector_wmape": value.get("sector_wmape_mean", np.nan),
            "gamma_geo": value.get("gamma_geo", gamma_geo),
            "gamma_mob": value.get("gamma_mob", gamma_mob),
            "per_year_total": per_year,
            "gate_by_year": value.get("gate_by_year", value.get("gate_mean_by_year", {})),
            "adj_delta_by_year": value.get("adj_delta_by_year", []),
            "regime_delta_by_year": value.get("regime_delta_by_year", []),
        })
    return pd.DataFrame(rows)


def fold_year_frame(rows: pd.DataFrame, label: str) -> pd.DataFrame:
    out = []
    for _, row in rows.iterrows():
        per_year = row.get("per_year_total", {})
        for year in YEARS:
            value = per_year.get(str(year), per_year.get(year, np.nan))
            out.append({
                "model": label,
                "seed": int(row["seed"]),
                "year": year,
                "wmape": value,
            })
    return pd.DataFrame(out)


def load_stgnn_baselines(pattern: str = DEFAULT_STGNN_GLOB):
    summary_rows = []
    yearly_rows = []
    paths = sorted(Path(p) for p in glob(pattern)) if "/" in pattern else sorted(REPORTS.glob(pattern))
    for path in paths:
        try:
            seed = int(path.stem.split("_seed_")[1].split("_")[0])
            data = load_json(path)
        except Exception:
            continue
        for row in data.get("summary_mean_wmape", []):
            model = row.get("model")
            label = {
                "dynamic_stgnn_residual": "Dynamic STGNN V1",
                "dcrnn_residual": "DCRNN residual",
                "graph_wavenet_residual": "Graph WaveNet residual",
            }.get(model, model)
            summary_rows.append({"model": label, "seed": seed, "wmape": float(row["wmape"])})
        for row in data.get("metrics_by_model_year", []):
            model = row.get("model")
            label = {
                "dynamic_stgnn_residual": "Dynamic STGNN V1",
                "dcrnn_residual": "DCRNN residual",
                "graph_wavenet_residual": "Graph WaveNet residual",
            }.get(model, model)
            yearly_rows.append({
                "model": label,
                "seed": seed,
                "year": int(row["target_year"]),
                "wmape": float(row["wmape"]),
            })
    return (
        pd.DataFrame(summary_rows, columns=["model", "seed", "wmape"]),
        pd.DataFrame(yearly_rows, columns=["model", "seed", "year", "wmape"]),
    )


def load_temporal_baselines(path: Path):
    if not path.exists():
        return (
            pd.DataFrame(columns=["model", "seed", "wmape"]),
            pd.DataFrame(columns=["model", "seed", "year", "wmape"]),
        )
    data = load_json(path)
    label_map = {
        "naive_lag1": "Naive lag-1",
        "ridge_ar": "Ridge AR",
        "arima_local": "ARIMA local",
        "lstm_local": "LSTM local",
    }
    summary_rows = []
    for row in data.get("summary_mean_wmape", []):
        summary_rows.append({
            "model": label_map.get(row["model"], row["model"]),
            "seed": int(row.get("seed", 0)),
            "wmape": float(row.get("mean_wmape", row.get("wmape", np.nan))),
        })
    yearly_rows = []
    for row in data.get("metrics_by_model_year", []):
        yearly_rows.append({
            "model": label_map.get(row["model"], row["model"]),
            "seed": int(row.get("seed", 0)),
            "year": int(row["target_year"]),
            "wmape": float(row["wmape"]),
        })
    return (
        pd.DataFrame(summary_rows, columns=["model", "seed", "wmape"]),
        pd.DataFrame(yearly_rows, columns=["model", "seed", "year", "wmape"]),
    )


def summarize(frame: pd.DataFrame, label_col="label") -> pd.DataFrame:
    rows = []
    for label, group in frame.groupby(label_col):
        vals = group["wmape"].dropna().astype(float)
        rows.append({
            label_col: label,
            "n": len(vals),
            "mean": vals.mean(),
            "std": vals.std(ddof=0),
            "min": vals.min(),
            "max": vals.max(),
        })
    return pd.DataFrame(rows)


def fig_main_summary(v3_full, v6_final, ridge_mean, stgnn_summary, temporal_summary):
    labels = ["Ridge AR"]
    means = [ridge_mean]
    stds = [0.0]
    for label in ["Naive lag-1", "ARIMA local", "LSTM local"]:
        vals = temporal_summary[temporal_summary["model"] == label]["wmape"].astype(float)
        if not vals.empty:
            labels.append(label)
            means.append(vals.mean())
            stds.append(vals.std(ddof=0))
    for label in ["DCRNN residual", "Graph WaveNet residual", "Dynamic STGNN V1"]:
        vals = stgnn_summary[stgnn_summary["model"] == label]["wmape"].astype(float)
        if not vals.empty:
            labels.append(label)
            means.append(vals.mean())
            stds.append(vals.std(ddof=0))
    labels.extend(["V3 full", "V6 full"])
    means.extend([v3_full["wmape"].mean(), v6_final["wmape"].mean()])
    stds.extend([v3_full["wmape"].std(ddof=0), v6_final["wmape"].std(ddof=0)])
    fig = go.Figure(go.Bar(
        x=labels,
        y=means,
        error_y=dict(type="data", array=stds, visible=True),
        marker_color=[COLORS[x] for x in labels],
        text=[f"{v:.4f}" for v in means],
        textposition="outside",
        hovertemplate="%{x}<br>WMAPE moyen : %{y:.6f}<extra></extra>",
    ))
    fig.update_layout(
        title="HERALD France - comparaison principale",
        template="plotly_white",
        height=420,
        margin=dict(l=60, r=25, t=70, b=55),
        yaxis_title="WMAPE moyen en walk-forward",
    )
    return fig


def fig_seed_lines(v3_full, v6_final):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=v3_full["seed"], y=v3_full["wmape"], mode="lines+markers",
        name="V3 full", line=dict(color=COLORS["V3 full"], width=3),
    ))
    fig.add_trace(go.Scatter(
        x=v6_final["seed"], y=v6_final["wmape"], mode="lines+markers",
        name="V6 full gate=2.0", line=dict(color=COLORS["V6 full"], width=3),
    ))
    fig.update_layout(
        title="Stabilité par graine aléatoire",
        template="plotly_white",
        height=390,
        margin=dict(l=60, r=25, t=70, b=55),
        xaxis_title="Graine aléatoire",
        yaxis_title="WMAPE",
    )
    return fig


def fig_paired_diff(v3_full, v6_final):
    merged = v3_full[["seed", "wmape"]].merge(
        v6_final[["seed", "wmape"]], on="seed", suffixes=("_v3", "_v6")
    )
    merged["diff_v6_minus_v3"] = merged["wmape_v6"] - merged["wmape_v3"]
    colors = np.where(merged["diff_v6_minus_v3"] <= 0, "#2e6f9e", "#b75f29")
    fig = go.Figure(go.Bar(
        x=merged["seed"].astype(str),
        y=merged["diff_v6_minus_v3"],
        marker_color=colors,
        hovertemplate="graine=%{x}<br>V6 - V3 : %{y:+.6f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#333", line_width=1)
    fig.update_layout(
        title="Différence appariée par graine aléatoire : V6 - V3",
        template="plotly_white",
        height=370,
        margin=dict(l=60, r=25, t=70, b=55),
        xaxis_title="Graine aléatoire",
        yaxis_title="Delta WMAPE",
    )
    return fig


def fig_yearly(v3_full, v6_final, stgnn_yearly, temporal_yearly):
    frames = [
        temporal_yearly,
        stgnn_yearly,
        fold_year_frame(v3_full, "V3 full"),
        fold_year_frame(v6_final, "V6 full"),
    ]
    fy = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    agg = fy.groupby(["model", "year"])["wmape"].agg(["mean", "std"]).reset_index()
    fig = go.Figure()
    for model in [
        "Naive lag-1", "Ridge AR", "ARIMA local", "LSTM local",
        "DCRNN residual", "Graph WaveNet residual", "Dynamic STGNN V1",
        "V3 full", "V6 full",
    ]:
        sub = agg[agg["model"] == model]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["mean"], mode="lines+markers",
            name=model, error_y=dict(type="data", array=sub["std"], visible=True),
            line=dict(color=COLORS[model], width=3),
        ))
    fig.update_layout(
        title="WMAPE par année de test",
        template="plotly_white",
        height=390,
        margin=dict(l=60, r=25, t=70, b=55),
        xaxis_title="Année",
        yaxis_title="WMAPE",
    )
    return fig


def fig_v6_ablation(v6, run_tag: str):
    order = [
        "full", "self_only", "fixed_geo_mob_only", "no_regime_in_graph",
        "no_quarterly", "static_adaptive", "no_sector_head",
    ]
    frame = v6[v6["run_tag"] == run_tag].copy()
    rows = []
    for ablation in order:
        vals = frame[frame["ablation"] == ablation]["wmape"].astype(float)
        if vals.empty:
            continue
        rows.append({
            "ablation": ablation,
            "mean": vals.mean(),
            "std": vals.std(ddof=0),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return None
    fig = go.Figure(go.Bar(
        x=df["ablation"], y=df["mean"], error_y=dict(type="data", array=df["std"], visible=True),
        marker_color=[COLORS.get(a, "#999") for a in df["ablation"]],
        text=[f"{v:.4f}" for v in df["mean"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="V6 gate=2.0 - ablations finales",
        template="plotly_white",
        height=430,
        margin=dict(l=60, r=25, t=70, b=95),
        yaxis_title="WMAPE moyen",
        xaxis_tickangle=-25,
    )
    return fig


def fig_v6_pairwise(v6, run_tag: str):
    seeds = sorted(v6[(v6["ablation"] == "full") & (v6["run_tag"] == run_tag)]["seed"].dropna().astype(int))
    if not seeds:
        return None
    full = {
        int(r.seed): float(r.wmape)
        for r in v6[(v6["ablation"] == "full") & (v6["run_tag"] == run_tag)].itertuples(index=False)
    }
    ablations = ["self_only", "fixed_geo_mob_only", "no_regime_in_graph", "no_quarterly", "static_adaptive"]
    rows = []
    for ablation in ablations:
        runs = {
            int(r.seed): float(r.wmape)
            for r in v6[(v6["ablation"] == ablation) & (v6["run_tag"] == run_tag)].itertuples(index=False)
        }
        diffs = np.array([runs[s] - full[s] for s in seeds if s in runs and s in full])
        if len(diffs) == 0:
            continue
        rows.append({
            "ablation": ablation,
            "mean_diff": diffs.mean(),
            "wins": int((diffs > 0).sum()),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return None
    fig = go.Figure(go.Bar(
        x=df["ablation"], y=df["mean_diff"],
        marker_color=[COLORS.get(a, "#999") for a in df["ablation"]],
        text=[f"{w}/7" for w in df["wins"]],
        textposition="outside",
        hovertemplate="%{x}<br>ablation - full : %{y:+.6f}<br>victoires du full : %{text}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#333", line_width=1)
    fig.update_layout(
        title="V6 - gain apparié du modèle full sur les ablations",
        template="plotly_white",
        height=390,
        margin=dict(l=60, r=25, t=70, b=90),
        yaxis_title="WMAPE(ablation) - WMAPE(full)",
        xaxis_tickangle=-25,
    )
    return fig


def fig_graph_diagnostics(v6_full):
    rows = []
    for row in v6_full.itertuples(index=False):
        adj = row.adj_delta_by_year or []
        reg = row.regime_delta_by_year or []
        if len(adj) < 10:
            continue
        corr = np.corrcoef(adj, reg)[0, 1] if len(adj) == len(reg) and np.std(adj) > 0 and np.std(reg) > 0 else np.nan
        rows.append({
            "seed": int(row.seed),
            "adj_2019_2020": adj[7],
            "adj_2020_2021": adj[8],
            "adj_2021_2022": adj[9],
            "corr_regime_adj": corr,
            "gamma_geo": row.gamma_geo,
            "gamma_mob": row.gamma_mob,
        })
    df = pd.DataFrame(rows)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Variation d'adjacence par transition", "Priors appris"))
    for col, label, color in [
        ("adj_2019_2020", "2019->2020", "#999999"),
        ("adj_2020_2021", "2020->2021", "#b75f29"),
        ("adj_2021_2022", "2021->2022", "#d5a06c"),
    ]:
        fig.add_trace(go.Bar(x=df["seed"].astype(str), y=df[col], name=label, marker_color=color), row=1, col=1)
    fig.add_trace(go.Bar(x=df["seed"].astype(str), y=df["gamma_geo"], name="gamma_geo", marker_color="#7f7f9f"), row=1, col=2)
    fig.add_trace(go.Bar(x=df["seed"].astype(str), y=df["gamma_mob"], name="gamma_mob", marker_color="#2e6f9e"), row=1, col=2)
    fig.update_layout(
        title=f"Diagnostic du graphe V6 : corrélation moyenne régime/adjacence = {df['corr_regime_adj'].mean():.3f}",
        template="plotly_white",
        barmode="group",
        height=450,
        margin=dict(l=60, r=25, t=85, b=55),
    )
    fig.update_xaxes(title_text="Graine aléatoire")
    fig.update_yaxes(title_text="Delta", row=1, col=1)
    fig.update_yaxes(title_text="Poids appris", row=1, col=2)
    return fig


def fig_sector_baselines(sector_csv: Path, v6_full):
    if not sector_csv.exists():
        return None
    sector = pd.read_csv(sector_csv)
    rows = []
    for baseline, group in sector.groupby("baseline"):
        fold_vals = []
        for _, fold in group.groupby("target_year"):
            fold_vals.append(fold.groupby("sector")["wmape"].first().mean())
        rows.append({"label": baseline, "wmape": float(np.mean(fold_vals))})
    rows.append({"label": "Tête sectorielle HERALD", "wmape": float(v6_full["sector_wmape"].mean())})
    df = pd.DataFrame(rows).sort_values("wmape")
    fig = go.Figure(go.Bar(
        x=df["label"], y=df["wmape"],
        marker_color=["#709c78" if x == "Tête sectorielle HERALD" else "#9a9a9a" for x in df["label"]],
        text=[f"{v:.3f}" for v in df["wmape"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Secteurs A10 - HERALD vs références simples",
        template="plotly_white",
        height=410,
        margin=dict(l=60, r=25, t=70, b=95),
        yaxis_title="WMAPE sectoriel",
        xaxis_tickangle=-20,
    )
    return fig


def figure_to_div(fig):
    return pio.to_html(localize_figure(fig), include_plotlyjs=False, full_html=False)


TEXT_REPLACEMENTS = {
    "Seed": "Graine aléatoire",
    "seed": "graine",
    "Epoch": "Époque",
    "Training learning curves - mean total loss across folds/seeds": "Courbes d'apprentissage - perte totale moyenne sur les folds et graines",
    "Training loss": "Perte d'entraînement",
    "HERALD full loss components": "Composantes de la perte du modèle HERALD full",
    "Loss component": "Composante de perte",
    "loss_total": "perte totale",
    "loss_main": "perte principale",
    "loss_sector": "perte sectorielle",
    "loss_smooth": "perte de lissage",
    "HERALD V3 signed error + dynamic graph": "HERALD V3 - erreur signée + graphe dynamique",
    "HERALD V3 dynamic graph": "Graphe dynamique HERALD V3",
    "Top dynamic edges": "Principales arêtes dynamiques",
    "ZE2020 background": "Fond ZE2020",
    "signed error": "erreur signée",
    "dynamic graph": "graphe dynamique",
    "Top adaptive neighbors learned in 2024": "Top-5 des voisins adaptatifs appris en 2024",
    "learning rate": "taux d'apprentissage",
    "Learning rate": "Taux d'apprentissage",
    "baseline": "référence",
    "baselines": "références",
}


def _replace_text(value):
    if isinstance(value, str):
        out = value
        for old, new in TEXT_REPLACEMENTS.items():
            out = out.replace(old, new)
        return out
    if isinstance(value, list):
        return [_replace_text(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_replace_text(v) for v in value)
    if isinstance(value, dict):
        return {k: _replace_text(v) for k, v in value.items()}
    return value


def localize_figure(fig):
    if fig is None:
        return None
    return go.Figure(_replace_text(fig.to_plotly_json()))


def load_v6_predictions(data_dir: Path, run_tag: str) -> pd.DataFrame:
    frames = []
    for path in sorted(data_dir.glob(f"herald_v6_predictions_total_full_{run_tag}_seed_*_v1.csv")):
        frame = pd.read_csv(path)
        frame["model"] = "HERALD_V6"
        frame["ablation"] = "full"
        frame["seed"] = int(path.name.split("_seed_")[1].split("_")[0])
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_v6_sector_predictions(data_dir: Path, run_tag: str) -> pd.DataFrame:
    frames = []
    for path in sorted(data_dir.glob(f"herald_v6_predictions_sector_full_{run_tag}_seed_*_v1.csv")):
        frame = pd.read_csv(path)
        frame["seed"] = int(path.name.split("_seed_")[1].split("_")[0])
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)
    avg = (
        raw.groupby(["target_year", "ZE2020", "sector"], as_index=False)
        .agg(
            y_true_sector=("y_true_sector", "mean"),
            y_pred_sector=("y_pred_sector", "mean"),
            y_pred_total=("y_pred_total", "mean"),
            prop_pred=("prop_pred", "mean"),
        )
    )
    avg["ze2020_int"] = avg["ZE2020"].astype(int)
    avg["signed_error_pct"] = 100.0 * (
        avg["y_pred_sector"] - avg["y_true_sector"]
    ) / avg["y_true_sector"].clip(lower=1.0)
    avg["abs_error"] = (avg["y_pred_sector"] - avg["y_true_sector"]).abs()
    return avg


def load_v6_graph_average(data_dir: Path, run_tag: str):
    mats, gates = [], []
    years = None
    zones = None
    gammas = []
    for seed in SEEDS:
        path = data_dir / f"herald_v6_internals_full_{run_tag}_seed_{seed}_v1.npz"
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


def load_map_predictions_generic(pred: pd.DataFrame) -> pd.DataFrame:
    full = pred.copy()
    if full.empty:
        return pd.DataFrame()
    if "model" in full.columns:
        herald = full[full["model"].astype(str).str.contains("HERALD", case=False, na=False)]
        if not herald.empty:
            full = herald
    if "ablation" in full.columns:
        full_ablation = full[full["ablation"].astype(str).eq("full")]
        if not full_ablation.empty:
            full = full_ablation
    full = (
        full.groupby(["target_year", "ZE2020"], as_index=False)
        .agg(y_true=("y_true", "mean"), y_pred=("y_pred", "mean"))
    )
    full["ze2020_int"] = full["ZE2020"].astype(int)
    full["signed_error_pct"] = 100.0 * (full["y_pred"] - full["y_true"]) / full["y_true"].clip(lower=1.0)
    full["abs_error"] = (full["y_pred"] - full["y_true"]).abs()
    return full


def absolute_error_trace(geojson, zones_df, pred, year, cmax, visible=False):
    sub = pred[pred["target_year"] == year]
    merged = zones_df.merge(sub, on="ze2020_int", how="left")
    custom = np.stack(
        [
            merged["libze2020"].astype(str),
            merged["y_true"].fillna(np.nan),
            merged["y_pred"].fillna(np.nan),
            merged["signed_error_pct"].fillna(np.nan),
        ],
        axis=1,
    )
    return go.Choropleth(
        geojson=geojson,
        locations=merged["ze2020"],
        z=merged["abs_error"],
        featureidkey="properties.ze2020",
        colorscale="YlOrRd",
        zmin=0,
        zmax=cmax,
        marker_line_color="rgba(255,255,255,0.85)",
        marker_line_width=0.35,
        colorbar=dict(title="Erreur<br>absolue"),
        name=f"Erreur absolue {year}",
        customdata=custom,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "ZE2020: %{location}<br>"
            "Observé : %{customdata[1]:,.0f}<br>"
            "Prédit : %{customdata[2]:,.0f}<br>"
            "Erreur absolue : %{z:,.0f}<br>"
            "Erreur signée relative : %{customdata[3]:+.2f}%<extra></extra>"
        ),
        visible=visible,
    )


def fig_dynamic_map_generic(pred: pd.DataFrame, graph, title_prefix: str):
    if graph is None or pred.empty:
        return None
    geojson, zones_df = v3dash.map_utils.load_ze2020_geojson()
    map_pred = load_map_predictions_generic(pred)
    cmax_pct = max(float(np.nanpercentile(np.abs(map_pred["signed_error_pct"]), 96)), 8.0)
    cmax_abs = max(float(np.nanpercentile(map_pred["abs_error"], 96)), 1.0)
    fig = go.Figure()
    meta = []
    for year in YEARS:
        visible = year == 2024
        fig.add_trace(v3dash.error_trace(geojson, zones_df, map_pred, year, cmax_pct, visible=visible))
        meta.append(("error_pct", year))
    for year in YEARS:
        fig.add_trace(absolute_error_trace(geojson, zones_df, map_pred, year, cmax_abs, visible=False))
        meta.append(("error_abs", year))
    for year in YEARS:
        fig.add_trace(v3dash.edge_trace(v3dash.dynamic_edges(graph, year), zones_df, year, visible=(year == 2024)))
        meta.append(("edge", year))
    for year in YEARS:
        fig.add_trace(v3dash.gate_trace(geojson, zones_df, graph, year, visible=False))
        meta.append(("gate", year))
    buttons = []
    for idx, (kind, year) in enumerate(meta):
        if kind == "edge":
            continue
        visible = [False] * len(meta)
        visible[idx] = True
        visible[meta.index(("edge", year))] = True
        if kind == "error_pct":
            sub = map_pred[map_pred["target_year"] == year]
            title = f"{title_prefix} - erreur relative signée + graphe dynamique - {year} (WMAPE {v3dash.wmape(sub.y_true, sub.y_pred):.4f})"
            label = f"{year} | erreur relative (%)"
        elif kind == "error_abs":
            sub = map_pred[map_pred["target_year"] == year]
            title = f"{title_prefix} - erreur absolue + graphe dynamique - {year} (WMAPE {v3dash.wmape(sub.y_true, sub.y_pred):.4f})"
            label = f"{year} | erreur absolue"
        else:
            title = f"{title_prefix} - part graphe/message + graphe dynamique - {year}"
            label = f"{year} | part graphe"
        buttons.append(dict(label=label, method="update", args=[{"visible": visible}, {"title": title}]))
    fig.update_layout(
        title=f"{title_prefix} - erreur relative signée + graphe dynamique - 2024",
        geo=dict(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="#f6f3ee"),
        updatemenus=[dict(buttons=buttons, direction="down", x=0.01, y=1.08, xanchor="left", yanchor="top", bgcolor="white")],
        margin=dict(l=10, r=10, t=80, b=10),
        width=1120,
        height=820,
        paper_bgcolor="#f6f3ee",
        font=dict(family="Arial", color="#232323"),
    )
    return fig


def pale_background_trace(geojson, zones_df, year, visible=False):
    return go.Choropleth(
        geojson=geojson,
        locations=zones_df["ze2020"],
        z=np.zeros(len(zones_df)),
        featureidkey="properties.ze2020",
        colorscale=[[0, "#efe6d8"], [1, "#efe6d8"]],
        showscale=False,
        marker_line_color="rgba(255,255,255,0.88)",
        marker_line_width=0.45,
        hoverinfo="skip",
        name=f"Fond ZE2020 {year}",
        visible=visible,
    )


def a10_top_sector_traces(sector_pred: pd.DataFrame, zones_df: pd.DataFrame, year: int, top_n: int, visible=False):
    sub = sector_pred[sector_pred["target_year"] == year].copy()
    if sub.empty:
        return []
    sub = sub.sort_values("y_pred_sector", ascending=False).head(top_n)
    merged = sub.merge(zones_df[["ze2020_int", "ze2020", "libze2020", "lon", "lat"]], on="ze2020_int", how="left")
    max_volume = max(float(merged["y_pred_sector"].max()), 1.0)
    traces = []
    for sector in SECTORS_A10:
        part = merged[merged["sector"] == sector]
        if part.empty:
            continue
        sizes = 7.0 + 22.0 * np.sqrt(part["y_pred_sector"].clip(lower=0.0) / max_volume)
        custom = np.stack(
            [
                part["libze2020"].astype(str),
                part["ze2020"].astype(str),
                part["sector"].astype(str),
                part["y_true_sector"].fillna(np.nan),
                part["y_pred_sector"].fillna(np.nan),
                part["prop_pred"].fillna(np.nan),
                part["signed_error_pct"].fillna(np.nan),
                part["abs_error"].fillna(np.nan),
            ],
            axis=1,
        )
        traces.append(go.Scattergeo(
            lon=part["lon"],
            lat=part["lat"],
            mode="markers",
            marker=dict(
                size=sizes,
                color=SECTOR_COLORS[sector],
                opacity=0.82,
                line=dict(width=0.7, color="rgba(35,35,35,0.45)"),
            ),
            customdata=custom,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "ZE2020 : %{customdata[1]}<br>"
                "Secteur A10 : %{customdata[2]}<br>"
                "Observé secteur : %{customdata[3]:,.0f}<br>"
                "Prédit secteur : %{customdata[4]:,.0f}<br>"
                "Part sectorielle prédite : %{customdata[5]:.3f}<br>"
                "Erreur relative : %{customdata[6]:+.2f}%<br>"
                "Erreur absolue : %{customdata[7]:,.0f}<extra></extra>"
            ),
            name=f"{sector} - top A10",
            legendgroup=f"A10-{sector}",
            showlegend=(year == 2024),
            visible=visible,
        ))
    return traces


def fig_v6_integrated_map(pred: pd.DataFrame, graph, sector_pred: pd.DataFrame, top_n: int = 90):
    if graph is None or pred.empty:
        return None
    geojson, zones_df = v3dash.map_utils.load_ze2020_geojson()
    map_pred = load_map_predictions_generic(pred)
    cmax_pct = max(float(np.nanpercentile(np.abs(map_pred["signed_error_pct"]), 96)), 8.0)
    cmax_abs = max(float(np.nanpercentile(map_pred["abs_error"], 96)), 1.0)

    fig = go.Figure()
    trace_meta = []

    def add_trace(trace, layer, year):
        fig.add_trace(trace)
        trace_meta.append((layer, year))

    for year in YEARS:
        add_trace(absolute_error_trace(geojson, zones_df, map_pred, year, cmax_abs, visible=(year == 2024)), "Erreur absolue", year)
        edge = v3dash.edge_trace(v3dash.dynamic_edges(graph, year), zones_df, year, visible=(year == 2024))
        edge.name = f"Graphe dynamique {year}"
        add_trace(edge, "Erreur absolue", year)

    for year in YEARS:
        add_trace(v3dash.error_trace(geojson, zones_df, map_pred, year, cmax_pct, visible=False), "Erreur relative", year)
        edge = v3dash.edge_trace(v3dash.dynamic_edges(graph, year), zones_df, year, visible=False)
        edge.name = f"Graphe dynamique {year}"
        add_trace(edge, "Erreur relative", year)

    for year in YEARS:
        add_trace(pale_background_trace(geojson, zones_df, year, visible=False), "Graphe", year)
        edge = v3dash.graph_only_edge_trace(v3dash.dynamic_edges(graph, year, top_k=850), zones_df, year, visible=False)
        edge.name = f"Arêtes principales {year}"
        add_trace(edge, "Graphe", year)
        node = v3dash.graph_only_node_trace(graph, zones_df, year, visible=False)
        node.name = f"Part graphe {year}"
        add_trace(node, "Graphe", year)

    if not sector_pred.empty:
        for year in YEARS:
            add_trace(pale_background_trace(geojson, zones_df, year, visible=False), "Top A10", year)
            for trace in a10_top_sector_traces(sector_pred, zones_df, year, top_n, visible=False):
                add_trace(trace, "Top A10", year)

    buttons = []
    for layer in ["Erreur absolue", "Erreur relative", "Graphe", "Top A10"]:
        if layer == "Top A10" and sector_pred.empty:
            continue
        for year in YEARS:
            visible = [(meta_layer == layer and meta_year == year) for meta_layer, meta_year in trace_meta]
            if not any(visible):
                continue
            if layer == "Erreur absolue":
                sub = map_pred[map_pred["target_year"] == year]
                title = f"HERALD V6 - erreur absolue + graphe dynamique - {year} (WMAPE {v3dash.wmape(sub.y_true, sub.y_pred):.4f})"
                label = f"{year} | erreur absolue"
            elif layer == "Erreur relative":
                sub = map_pred[map_pred["target_year"] == year]
                title = f"HERALD V6 - erreur relative signée + graphe dynamique - {year} (WMAPE {v3dash.wmape(sub.y_true, sub.y_pred):.4f})"
                label = f"{year} | erreur relative"
            elif layer == "Graphe":
                title = f"HERALD V6 - graphe dynamique et part message - {year}"
                label = f"{year} | graphe"
            else:
                title = f"HERALD V6 - top {top_n} couples territoire-secteur A10 - {year}"
                label = f"{year} | top A10"
            buttons.append(dict(label=label, method="update", args=[{"visible": visible}, {"title": title}]))

    fig.update_layout(
        title="HERALD V6 - erreur absolue + graphe dynamique - 2024",
        geo=dict(
            fitbounds="locations",
            visible=False,
            projection_type="mercator",
            bgcolor="#f6f3ee",
            landcolor="#f6f3ee",
            lakecolor="#f6f3ee",
        ),
        updatemenus=[dict(buttons=buttons, direction="down", x=0.01, y=1.08, xanchor="left", yanchor="top", bgcolor="white")],
        margin=dict(l=10, r=10, t=80, b=10),
        width=1120,
        height=820,
        paper_bgcolor="#f6f3ee",
        font=dict(family="Arial", color="#232323"),
        legend=dict(orientation="h", y=-0.03, x=0.01),
    )
    return fig


def fig_dynamic_graph_france_generic(graph, title_prefix: str):
    fig = v3dash.fig_dynamic_graph_france(graph)
    if fig is not None:
        fig.update_layout(title=f"{title_prefix} - graphe adaptatif dynamique sur la France ZE2020 - 2024")
    return fig


def wmape_np(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 0 else np.nan


def fig_v6_a10_sector_heatmap(sector_pred: pd.DataFrame):
    if sector_pred.empty:
        return None
    z = []
    for sector in SECTORS_A10:
        row = []
        for year in YEARS:
            sub = sector_pred[(sector_pred["sector"] == sector) & (sector_pred["target_year"] == year)]
            row.append(wmape_np(sub["y_true_sector"], sub["y_pred_sector"]))
        z.append(row)
    fig = go.Figure(go.Heatmap(
        z=z,
        x=YEARS,
        y=SECTORS_A10,
        colorscale="YlOrRd",
        colorbar=dict(title="WMAPE"),
        text=[[f"{v:.3f}" for v in row] for row in z],
        texttemplate="%{text}",
        hovertemplate="Secteur %{y}<br>Année %{x}<br>WMAPE: %{z:.4f}<extra></extra>",
    ))
    fig.update_layout(
        title="V6 A10 - erreurs sectorielles par année",
        template="plotly_white",
        height=430,
        margin=dict(l=65, r=25, t=70, b=55),
        xaxis_title="Année",
        yaxis_title="Secteur A10",
    )
    return fig


def plot_block(fig, note: str):
    return {"fig": fig, "note": note}


def build_html(figs, summary_html):
    blocks = []
    for item in figs:
        if item is None:
            continue
        if isinstance(item, dict):
            fig = item.get("fig")
            note = item.get("note", "")
        else:
            fig = item
            note = ""
        if fig is None:
            continue
        note_html = f'<p class="note">{note}</p>' if note else ""
        blocks.append(f"<section>{note_html}{figure_to_div(fig)}</section>")
    divs = "\n".join(blocks)
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Tableau de bord HERALD V3/V6</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin: 0; background: #f7f3ee; color: #2b2118; }}
    header {{ padding: 28px 34px 18px; background: #2b2118; color: #fffaf2; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .sub {{ color: #e7d4bd; font-size: 14px; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 22px; }}
    section {{ background: white; border: 1px solid #e2d8cd; border-radius: 8px; margin: 18px 0; padding: 10px; }}
    .note {{ margin: 8px 12px 0; color: #5b4a3b; font-size: 14px; line-height: 1.45; }}
    .summary {{ background: #fffaf2; border: 1px solid #e2d8cd; border-radius: 8px; padding: 16px 20px; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e2d8cd; padding: 7px 9px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
  </style>
</head>
<body>
  <header>
    <h1>HERALD France - comparaison V3/V6</h1>
    <div class="sub">Walk-forward 2021-2024, 7 graines aléatoires lorsque disponibles. Une WMAPE plus basse indique une meilleure prévision.</div>
  </header>
  <main>
    <div class="summary">{summary_html}</div>
    {divs}
  </main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-json", type=Path, default=DEFAULT_V3)
    parser.add_argument("--v6-json", type=Path, default=DEFAULT_V6)
    parser.add_argument("--v6-ablation-json", type=Path, default=DEFAULT_V6_ABLATION)
    parser.add_argument("--v6-run-tag", default="final_gate2.0")
    parser.add_argument("--ridge-json", type=Path, default=DEFAULT_RIDGE)
    parser.add_argument("--sector-csv", type=Path, default=DEFAULT_SECTOR)
    parser.add_argument("--v6-data-dir", type=Path, default=DEFAULT_V6_DATA)
    parser.add_argument("--stgnn-glob", default=DEFAULT_STGNN_GLOB)
    parser.add_argument("--temporal-json", type=Path, default=DEFAULT_TEMPORAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    v3 = records_from_metrics(load_json(args.v3_json), "v3")
    v6 = records_from_metrics(load_json(args.v6_json), "v6")
    v6_ablation = records_from_metrics(load_json(args.v6_ablation_json), "v6_ablation") if args.v6_ablation_json.exists() else v6
    stgnn_summary, stgnn_yearly = load_stgnn_baselines(args.stgnn_glob)
    temporal_summary, temporal_yearly = load_temporal_baselines(args.temporal_json)
    ridge = load_json(args.ridge_json) if args.ridge_json.exists() else {}
    ridge_mean = ridge.get("ridge_ar_official", {}).get("mean", 0.066794)
    temporal_ridge = temporal_summary[temporal_summary["model"] == "Ridge AR"]["wmape"].astype(float)
    if not temporal_ridge.empty:
        ridge_mean = float(temporal_ridge.mean())

    v3_full = v3[(v3["ablation"] == "full") & (v3["seed"].isin(SEEDS))].copy()
    v6_full = v6[(v6["ablation"] == "full") & (v6["run_tag"] == args.v6_run_tag) & (v6["seed"].isin(SEEDS))].copy()
    v3_full["seed"] = v3_full["seed"].astype(int)
    v6_full["seed"] = v6_full["seed"].astype(int)
    v3_full = v3_full.sort_values("seed")
    v6_full = v6_full.sort_values("seed")

    summary_rows = [{"Modèle": "Ridge AR", "N": 1, "WMAPE moyen": ridge_mean, "Écart-type": np.nan}]
    for label in ["Naive lag-1", "ARIMA local", "LSTM local"]:
        vals = temporal_summary[temporal_summary["model"] == label]["wmape"].astype(float)
        if not vals.empty:
            summary_rows.append({
                "Modèle": label,
                "N": len(vals),
                "WMAPE moyen": vals.mean(),
                "Écart-type": vals.std(ddof=0),
            })
    for label in ["DCRNN residual", "Graph WaveNet residual", "Dynamic STGNN V1"]:
        vals = stgnn_summary[stgnn_summary["model"] == label]["wmape"].astype(float)
        if not vals.empty:
            summary_rows.append({
                "Modèle": label,
                "N": len(vals),
                "WMAPE moyen": vals.mean(),
                "Écart-type": vals.std(ddof=0),
            })
    summary_rows.extend([
        {"Modèle": "V3 full", "N": len(v3_full), "WMAPE moyen": v3_full["wmape"].mean(), "Écart-type": v3_full["wmape"].std(ddof=0)},
        {"Modèle": "V6 full gate=2.0", "N": len(v6_full), "WMAPE moyen": v6_full["wmape"].mean(), "Écart-type": v6_full["wmape"].std(ddof=0)},
    ])
    summary = pd.DataFrame(summary_rows)
    summary_html = summary.to_html(index=False, float_format=lambda x: f"{x:.6f}")

    print("Construction des figures de comparaison...")
    figs = [
        plot_block(fig_main_summary(v3_full, v6_full, ridge_mean, stgnn_summary, temporal_summary),
                   "Lecture : ce graphique compare l'erreur moyenne WMAPE. Plus la barre est basse, meilleure est la prévision. Les références statistiques, LSTM, DCRNN et Dynamic STGNN sont incluses quand leurs rapports existent."),
        plot_block(fig_yearly(v3_full, v6_full, stgnn_yearly, temporal_yearly),
                   "Lecture : montre les années/folds où chaque modèle est robuste ou fragile. Les barres d'erreur indiquent la dispersion entre graines lorsque plusieurs seeds existent."),
        plot_block(fig_paired_diff(v3_full, v6_full) if len(v3_full) and len(v6_full) else None,
                   "Lecture : valeur négative = V6 bat V3 sur cette graine ; valeur positive = V3 reste meilleur. C'est la comparaison la plus honnête quand les mêmes graines existent."),
        plot_block(fig_seed_lines(v3_full, v6_full),
                   "Lecture : chaque point est une graine aléatoire. Une courbe stable signifie que le modèle dépend peu de l'initialisation aléatoire."),
        plot_block(fig_v6_ablation(v6_ablation, args.v6_run_tag),
                   "Lecture : chaque ablation retire un composant. Si une ablation est plus mauvaise que full, le composant retiré apporte de l'information."),
        plot_block(fig_v6_pairwise(v6_ablation, args.v6_run_tag),
                   "Lecture : différence positive = l'ablation est pire que full. Le texte indique dans combien de graines le full gagne."),
        plot_block(fig_graph_diagnostics(v6_full),
                   "Lecture : à gauche, le mouvement du graphe pendant les transitions économiques ; à droite, les poids appris des priors géographie et mobilité. γ mobilité plus grand signifie que les flux domicile-travail structurent mieux le territoire que la simple proximité."),
    ]

    print("Construction de la carte intégrée V6 et des diagnostics dynamiques...")
    v6_pred = load_v6_predictions(args.v6_data_dir, args.v6_run_tag)
    v6_sector_pred = load_v6_sector_predictions(args.v6_data_dir, args.v6_run_tag)
    v6_graph = load_v6_graph_average(args.v6_data_dir, args.v6_run_tag)
    figs.extend([
        plot_block(fig_v6_integrated_map(v6_pred, v6_graph, v6_sector_pred),
                   "Lecture : carte unique V6. Le menu choisit l'année et la couche : erreur absolue, erreur relative, graphe, ou top A10. Pour éviter une carte illisible, la couche A10 affiche seulement les principaux couples territoire-secteur par volume prédit."),
        plot_block(v3dash.fig_gate_message_share(v6_graph),
                   "Lecture : comportement du gate V6. La part locale montre combien le modèle s'appuie sur la zone elle-même ; la part graphe montre l'information venue des voisins."),
        plot_block(v3dash.fig_graph_dynamics(v6_graph),
                   "Lecture : mouvement annuel du graphe V6. Les transitions COVID/rebound doivent apparaître comme des pics si le régime économique influence la topologie."),
        plot_block(fig_sector_baselines(args.sector_csv, v6_full),
                   "Lecture : compare la tête sectorielle A10 de HERALD à des références simples. Si HERALD est au-dessus d'une référence, il est moins bon que cette référence."),
        plot_block(fig_v6_a10_sector_heatmap(v6_sector_pred),
                   "Lecture : heatmap A10 de V6. Les cellules les plus foncées indiquent les secteurs/années où la décomposition sectorielle est la moins précise."),
    ])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_html(figs, summary_html), encoding="utf-8")
    print(f"Saved: {args.out}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
