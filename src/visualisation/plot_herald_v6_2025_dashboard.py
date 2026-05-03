"""
Tableau de bord HERALD V6 pour validation 2025 observee.

Usage:
  python3 src/data/plot_herald_v6_2025_dashboard.py \
    --hpc-path hpc_results/herald_v6_observed2025_YYYYMMDD_HHMMSS

The script is deliberately output-root agnostic: it reads the metrics and
predictions produced by run_herald_v6_2025_observed.sh, whatever run-tag was
used, and writes one offline Plotly HTML dashboard.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HPC = ROOT / "hpc_results/herald_v6_observed2025_20260430_142920"
DEFAULT_OUT = ROOT / "reports/figures/herald_v6_observed2025_dashboard_v1.html"
SEEDS = [0, 1, 7, 13, 42, 99, 123]
YEARS = [2021, 2022, 2023, 2024, 2025]
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


def wmape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 0 else np.nan


def load_metrics(hpc_path: Path) -> dict:
    candidates = sorted((hpc_path / "reports").glob("*observed2025*metrics*.json"))
    if not candidates:
        candidates = sorted((hpc_path / "reports").glob("herald_v6*_metrics*.json"))
    if not candidates:
        raise FileNotFoundError(f"Aucun JSON de metriques trouve dans {hpc_path / 'reports'}")
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def records_from_metrics(metrics: dict) -> pd.DataFrame:
    rows = []
    for key, value in metrics.items():
        if not isinstance(value, dict):
            continue
        per_year = value.get("per_year_total", {})
        rows.append(
            {
                "key": key,
                "seed": int(value.get("seed", -1)),
                "run_tag": value.get("run_tag", ""),
                "wmape": float(value.get("total_wmape_mean", np.nan)),
                "sector_wmape": float(value.get("sector_wmape_mean", np.nan)),
                "gamma_geo": float(value.get("gamma_geo", np.nan)),
                "gamma_mob": float(value.get("gamma_mob", np.nan)),
                "gate_by_year": value.get("gate_by_year", {}),
                "adj_delta_by_year": value.get("adj_delta_by_year", []),
                "regime_delta_by_year": value.get("regime_delta_by_year", []),
                **{f"wmape_{year}": float(per_year.get(str(year), np.nan)) for year in YEARS},
            }
        )
    return pd.DataFrame(rows).sort_values("seed")


def load_total_predictions(hpc_path: Path) -> pd.DataFrame:
    frames = []
    for path in sorted((hpc_path / "data_processed").glob("herald_v6_predictions_total_full_*_seed_*_v1.csv")):
        frame = pd.read_csv(path)
        frame["seed"] = int(path.name.split("_seed_")[1].split("_")[0])
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_sector_predictions(hpc_path: Path) -> pd.DataFrame:
    frames = []
    for path in sorted((hpc_path / "data_processed").glob("herald_v6_predictions_sector_full_*_seed_*_v1.csv")):
        frame = pd.read_csv(path)
        frame["seed"] = int(path.name.split("_seed_")[1].split("_")[0])
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def ensemble_predictions(pred: pd.DataFrame) -> pd.DataFrame:
    if pred.empty:
        return pred
    out = (
        pred.groupby(["target_year", "ZE2020"], as_index=False)
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "mean"))
    )
    out["abs_error"] = (out["y_pred"] - out["y_true"]).abs()
    out["signed_error"] = out["y_pred"] - out["y_true"]
    out["ape"] = out["abs_error"] / out["y_true"].clip(lower=1.0)
    return out


def yearly_from_ensemble(ens: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in ens.groupby("target_year"):
        rows.append(
            {
                "year": int(year),
                "wmape": wmape(group["y_true"], group["y_pred"]),
                "observed": float(group["y_true"].sum()),
                "predicted": float(group["y_pred"].sum()),
                "bias": float(group["y_pred"].sum() - group["y_true"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("year")


def sector_2025_from_ensemble(sector_pred: pd.DataFrame) -> pd.DataFrame:
    if sector_pred.empty:
        return pd.DataFrame()
    ens = (
        sector_pred.groupby(["target_year", "ZE2020", "sector"], as_index=False)
        .agg(y_true_sector=("y_true_sector", "first"), y_pred_sector=("y_pred_sector", "mean"))
    )
    ens["abs_error"] = (ens["y_pred_sector"] - ens["y_true_sector"]).abs()
    rows = []
    for sector, group in ens[ens["target_year"] == 2025].groupby("sector"):
        rows.append({"sector": sector, "wmape": wmape(group["y_true_sector"], group["y_pred_sector"])})
    return pd.DataFrame(rows).sort_values("wmape")


def graph_transition_frame(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    years = list(range(2013, 2026))
    for row in runs.itertuples(index=False):
        adj = row.adj_delta_by_year if isinstance(row.adj_delta_by_year, list) else []
        reg = row.regime_delta_by_year if isinstance(row.regime_delta_by_year, list) else []
        for i, value in enumerate(adj[: len(years)]):
            rows.append(
                {
                    "seed": row.seed,
                    "transition": f"{years[i] - 1}->{years[i]}",
                    "to_year": years[i],
                    "adj_delta": float(value),
                    "regime_delta": float(reg[i]) if i < len(reg) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def top_errors_2025(ens: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    if ens.empty:
        return ens
    sub = ens[ens["target_year"] == 2025].copy()
    names_path = ROOT / "data/processed/graph_node_index_core_v0.csv"
    if names_path.exists():
        names = pd.read_csv(names_path)[["ze2020", "libze2020"]].rename(columns={"ze2020": "ZE2020"})
        sub = sub.merge(names, on="ZE2020", how="left")
    else:
        sub["libze2020"] = sub["ZE2020"].astype(str)
    return sub.sort_values("abs_error", ascending=False).head(top_n)


def load_forecast_data(forecast_data_dir: Path | None) -> pd.DataFrame:
    """Load all herald_v6_forecast_* CSVs from the given directory."""
    if forecast_data_dir is None or not forecast_data_dir.exists():
        return pd.DataFrame()
    frames = []
    for path in sorted(forecast_data_dir.glob("herald_v6_forecast_*_v1.csv")):
        frames.append(pd.read_csv(path))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def forecast_aggregates(forecast_df: pd.DataFrame) -> pd.DataFrame:
    """National aggregate forecast per year with seed uncertainty."""
    if forecast_df.empty:
        return pd.DataFrame()
    rows = []
    for year, grp in forecast_df.groupby("target_year"):
        by_seed = grp.groupby("seed")["y_pred"].sum()
        rows.append({
            "year":   int(year),
            "mean":   float(by_seed.mean()),
            "std":    float(by_seed.std(ddof=0)),
            "min":    float(by_seed.min()),
            "max":    float(by_seed.max()),
            "n_seeds": int(len(by_seed)),
        })
    return pd.DataFrame(rows).sort_values("year")


def build_dashboard(hpc_path: Path, forecast_data_dir: Path | None = None) -> go.Figure:
    metrics = load_metrics(hpc_path)
    runs = records_from_metrics(metrics)
    forecast_df  = load_forecast_data(forecast_data_dir or hpc_path / "data_processed")
    forecast_agg = forecast_aggregates(forecast_df)
    total_pred = load_total_predictions(hpc_path)
    sector_pred = load_sector_predictions(hpc_path)
    ens = ensemble_predictions(total_pred)
    yearly_ens = yearly_from_ensemble(ens)
    sector_2025 = sector_2025_from_ensemble(sector_pred)
    trans = graph_transition_frame(runs)
    top_err = top_errors_2025(ens)

    year_cols = [f"wmape_{year}" for year in YEARS]
    by_year_seed = pd.DataFrame(
        {
            "year": YEARS,
            "mean": [runs[c].mean() for c in year_cols],
            "std": [runs[c].std(ddof=0) for c in year_cols],
        }
    )

    n_rows = 5 if not forecast_agg.empty else 4
    subplot_titles = [
        "WMAPE par annee - moyenne des seeds",
        "WMAPE par annee - ensemble des 7 seeds",
        "Biais national 2025 et annees precedentes",
        "Distribution WMAPE par seed",
        "Graphe dynamique - changement d'adjacence",
        "Poids appris des priors du graphe",
        "Secteurs A10 en 2025",
        "Plus grands ecarts absolus en 2025",
    ]
    if n_rows == 5:
        subplot_titles += [
            "Prevision prospective 2026-2027 — agregat national",
            "Incertitude par seed (2026-2027)",
        ]
    fig = make_subplots(
        rows=n_rows,
        cols=2,
        subplot_titles=subplot_titles,
        vertical_spacing=0.09,
        horizontal_spacing=0.10,
    )

    fig.add_trace(
        go.Scatter(
            x=by_year_seed["year"],
            y=by_year_seed["mean"],
            error_y=dict(type="data", array=by_year_seed["std"], visible=True),
            mode="lines+markers",
            line=dict(color="#b75f29", width=3),
            marker=dict(size=8),
            name="Moyenne seeds",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=yearly_ens["year"],
            y=yearly_ens["wmape"],
            marker_color=["#b75f29" if y == 2025 else "#7a8fbd" for y in yearly_ens["year"]],
            text=[f"{v:.4f}" for v in yearly_ens["wmape"]],
            textposition="outside",
            name="Ensemble",
        ),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Bar(
            x=yearly_ens["year"],
            y=yearly_ens["bias"],
            marker_color=["#2e8b57" if v >= 0 else "#b75f29" for v in yearly_ens["bias"]],
            text=[f"{v/1000:+.1f}k" for v in yearly_ens["bias"]],
            textposition="outside",
            name="Biais",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Box(
            y=runs["wmape"],
            boxpoints="all",
            jitter=0.28,
            marker_color="#2e6f9e",
            name="Seeds",
            customdata=runs[["seed"]],
            hovertemplate="Seed %{customdata[0]}<br>WMAPE: %{y:.4f}<extra></extra>",
        ),
        row=2,
        col=2,
    )

    if not trans.empty:
        trans_mean = trans.groupby("transition", as_index=False).agg(adj_delta=("adj_delta", "mean"), to_year=("to_year", "first"))
        fig.add_trace(
            go.Bar(
                x=trans_mean["transition"],
                y=trans_mean["adj_delta"],
                marker_color=["#b75f29" if y in [2021, 2022] else "#9a9a9a" for y in trans_mean["to_year"]],
                name="Adj delta",
            ),
            row=3,
            col=1,
        )

    gamma = pd.DataFrame(
        {
            "prior": ["geographie", "mobilite"],
            "mean": [runs["gamma_geo"].mean(), runs["gamma_mob"].mean()],
            "std": [runs["gamma_geo"].std(ddof=0), runs["gamma_mob"].std(ddof=0)],
        }
    )
    fig.add_trace(
        go.Bar(
            x=gamma["prior"],
            y=gamma["mean"],
            error_y=dict(type="data", array=gamma["std"], visible=True),
            marker_color=["#8f8f8f", "#b75f29"],
            text=[f"{v:.3f}" for v in gamma["mean"]],
            textposition="outside",
        ),
        row=3,
        col=2,
    )

    if not sector_2025.empty:
        fig.add_trace(
            go.Bar(
                x=sector_2025["sector"],
                y=sector_2025["wmape"],
                marker_color=[SECTOR_COLORS.get(s, "#999999") for s in sector_2025["sector"]],
                text=[f"{v:.3f}" for v in sector_2025["wmape"]],
                textposition="outside",
            ),
            row=4,
            col=1,
        )

    if not top_err.empty:
        labels = top_err["libze2020"].fillna(top_err["ZE2020"].astype(str)).astype(str)
        fig.add_trace(
            go.Bar(
                x=top_err["abs_error"],
                y=labels,
                orientation="h",
                marker_color="#b75f29",
                customdata=np.stack([top_err["y_true"], top_err["y_pred"], top_err["ape"]], axis=1),
                hovertemplate=(
                    "%{y}<br>Observe: %{customdata[0]:,.0f}<br>"
                    "Predit: %{customdata[1]:,.0f}<br>"
                    "Erreur absolue: %{x:,.0f}<br>"
                    "Erreur relative: %{customdata[2]:.2%}<extra></extra>"
                ),
            ),
            row=4,
            col=2,
        )

    # ── row 5: prospective 2026-2027 forecast (only if data available) ──────────
    if not forecast_agg.empty:
        # Left: national aggregate with historical context + prospective bars
        hist_years = yearly_ens["year"].tolist() if not yearly_ens.empty else []
        hist_obs   = yearly_ens["observed"].tolist() if not yearly_ens.empty else []
        hist_pred  = yearly_ens["predicted"].tolist() if not yearly_ens.empty else []

        if hist_obs:
            fig.add_trace(
                go.Scatter(
                    x=hist_years, y=hist_obs,
                    mode="lines+markers",
                    name="Observe (2021-2025)",
                    line=dict(color="#2e6f9e", width=2),
                    marker=dict(size=7),
                ),
                row=5, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=hist_years, y=hist_pred,
                    mode="lines+markers",
                    name="Predit (eval)",
                    line=dict(color="#b75f29", dash="dot", width=2),
                    marker=dict(size=7),
                ),
                row=5, col=1,
            )

        fig.add_trace(
            go.Bar(
                x=forecast_agg["year"],
                y=forecast_agg["mean"],
                error_y=dict(
                    type="data",
                    array=forecast_agg["std"].tolist(),
                    visible=True,
                ),
                marker_color="#54a24b",
                text=[f"{v/1000:.1f}k" for v in forecast_agg["mean"]],
                textposition="outside",
                name="Prevision prospective",
                hovertemplate=(
                    "%{x}<br>Prevision: %{y:,.0f}<br>"
                    "Incertitude (sd): %{error_y.array:,.0f}<extra></extra>"
                ),
            ),
            row=5, col=1,
        )

        # Right: seed distribution box plots for each forecast year
        for yr, grp in forecast_df.groupby("target_year"):
            by_seed = grp.groupby("seed")["y_pred"].sum().reset_index()
            fig.add_trace(
                go.Box(
                    y=by_seed["y_pred"],
                    x=[str(int(yr))] * len(by_seed),
                    name=str(int(yr)),
                    boxpoints="all",
                    jitter=0.3,
                    marker_color="#54a24b",
                    showlegend=False,
                ),
                row=5, col=2,
            )

    run_tag = ", ".join(sorted(runs["run_tag"].dropna().unique())) or "run-tag inconnu"
    if not yearly_ens.empty and 2025 in yearly_ens["year"].values:
        row_2025 = yearly_ens[yearly_ens["year"] == 2025].iloc[0]
        subtitle = (
            f"Run-tag: {run_tag} | Ensemble 2025 WMAPE={row_2025.wmape:.4f} | "
            f"biais national={row_2025.bias:,.0f}"
        )
    else:
        subtitle = f"Run-tag: {run_tag}"

    dashboard_height = 1900 if not forecast_agg.empty else 1500
    fig.update_layout(
        title=f"HERALD V6 - validation observee 2025 + prevision prospective<br><sup>{subtitle}</sup>",
        template="plotly_white",
        height=dashboard_height,
        showlegend=False,
        margin=dict(l=90, r=35, t=110, b=60),
        font=dict(family="Arial", size=12),
    )
    fig.update_yaxes(title_text="WMAPE", row=1, col=1)
    fig.update_yaxes(title_text="WMAPE", row=1, col=2)
    fig.update_yaxes(title_text="Predit - observe", row=2, col=1)
    fig.update_yaxes(title_text="WMAPE", row=2, col=2)
    fig.update_yaxes(title_text="||A_t - A_{t-1}||", row=3, col=1)
    fig.update_yaxes(title_text="Poids moyen", row=3, col=2)
    fig.update_yaxes(title_text="WMAPE sectoriel", row=4, col=1)
    fig.update_yaxes(title_text=None, row=4, col=2, autorange="reversed")
    if not forecast_agg.empty:
        fig.update_yaxes(title_text="Creations (nationales)", row=5, col=1)
        fig.update_yaxes(title_text="Creations (nationales)", row=5, col=2)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hpc-path", type=Path, default=DEFAULT_HPC)
    parser.add_argument("--forecast-data-dir", type=Path, default=None,
                        help="Directory containing herald_v6_forecast_*_v1.csv files. "
                             "Defaults to <hpc-path>/data_processed.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.hpc_path.exists():
        raise SystemExit(f"Results path not found: {args.hpc_path}")
    fig = build_dashboard(args.hpc_path, forecast_data_dir=args.forecast_data_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(args.out))
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
