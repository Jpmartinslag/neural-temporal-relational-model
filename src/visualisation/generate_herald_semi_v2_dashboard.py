#!/usr/bin/env python3
"""Generate the HERALD Semi V2 scientific dashboard.

The dashboard is intentionally data-first:
- metrics are read from the current run JSON files;
- Semi V2 zone and A10 real-vs-predicted values are read from prediction CSVs;
- the old geo2025 dashboard is used only as a geometry/source fallback for the
  France map, V6 zone maps, and graph coordinates when those files are not
  present in the current run directory.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE = Path("/home/jpdark/Downloads/project_recomm/dataset")
DEFAULT_RUN_ROOT = BASE / "hpc_results/herald_showdown_20260504_173129"
DEFAULT_OLD_DASH = (
    BASE
    / "hpc_results/herald_semi_total_253_geo2025/reports/figures/herald_geo2025_final_dashboard.html"
)
DEFAULT_OUT = (
    BASE
    / "hpc_results/herald_semi_v2_final_20260504/reports/figures/herald_semi_v2_dashboard.html"
)
DEFAULT_OFFLINE_OUT = (
    BASE
    / "hpc_results/herald_semi_v2_final_20260504/reports/figures/herald_semi_v2_dashboard_offline.html"
)
DEFAULT_PLOTLY_BUNDLE = Path("/tmp/plotly_embedded.js")

YEARS = ["2021", "2022", "2023", "2024", "2025"]
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
SECTOR_LABELS = {
    "BE": "Industrie / énergie",
    "FZ": "Construction",
    "GI": "Commerce / transport",
    "JZ": "Information / communication",
    "KZ": "Finance / assurance",
    "LZ": "Immobilier",
    "MN": "Services aux entreprises",
    "OQ": "Services publics",
    "RU": "Arts / loisirs",
}


def read_json_value(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if len(data) == 1 and isinstance(next(iter(data.values())), dict):
        return next(iter(data.values()))
    return data


def load_runs(per_run: Path, pattern: str) -> list[dict[str, Any]]:
    runs = []
    for path in sorted(per_run.glob(pattern)):
        if path.suffix != ".json":
            continue
        runs.append(read_json_value(path))
    return runs


def safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def median_dict(runs: list[dict[str, Any]], key: str, labels: list[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for label in labels:
        vals = [safe_float((r.get(key) or {}).get(label)) for r in runs]
        vals = [v for v in vals if v is not None]
        out[label] = round(float(np.median(vals)), 6) if vals else None
    return out


def summarize_model(label: str, runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not runs:
        return None
    totals = [safe_float(r.get("total_wmape_mean")) for r in runs]
    totals = [v for v in totals if v is not None]
    vals_2025 = [
        safe_float(r.get("total_wmape_2025"))
        if safe_float(r.get("total_wmape_2025")) is not None
        else safe_float((r.get("per_year_total") or {}).get("2025"))
        for r in runs
    ]
    vals_2025 = [v for v in vals_2025 if v is not None]
    return {
        "label": label,
        "n": len(runs),
        "mean": round(float(np.mean(totals)), 6) if totals else None,
        "std": round(float(np.std(totals)), 6) if totals else None,
        "median": round(float(np.median(totals)), 6) if totals else None,
        "wmape_2025_mean": round(float(np.mean(vals_2025)), 6) if vals_2025 else None,
        "wmape_2025_median": round(float(np.median(vals_2025)), 6) if vals_2025 else None,
        "seed_2025": [round(float(v), 6) for v in vals_2025],
        "per_year": median_dict(runs, "per_year_total", YEARS),
        "sector": median_dict(runs, "sector_wmape", SECTORS),
        "alpha": median_dict(runs, "alpha_by_year", [str(y) for y in range(2012, 2026)]),
        "gate": median_dict(runs, "gate_by_year", [str(y) for y in range(2012, 2026)]),
        "gamma_geo": round(float(np.median([r["gamma_geo"] for r in runs if "gamma_geo" in r])), 6)
        if any("gamma_geo" in r for r in runs)
        else None,
        "gamma_mob": round(float(np.median([r["gamma_mob"] for r in runs if "gamma_mob" in r])), 6)
        if any("gamma_mob" in r for r in runs)
        else None,
    }


def extract_js_const(name: str, html: str) -> Any:
    match = re.search(r"const\s+" + re.escape(name) + r"\s*=\s*([\{\[])", html)
    if not match:
        return None
    start = match.start(1)
    opener = html[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(html)):
        ch = html[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return json.loads(html[start : i + 1])
    return None


def load_old_constants(old_dashboard: Path) -> dict[str, Any]:
    if not old_dashboard.exists():
        return {}
    html = old_dashboard.read_text(encoding="utf-8")
    names = [
        "GEOJSON",
        "ZE_NAMES",
        "GRAPH_DATA",
        "NEW_CONN",
        "GATE_SM",
        "ZONE_V6",
        "ZONE_V6_PREDS",
        "RIDGE_YR",
        "ARIMA_PY",
        "DCRNN_PY",
        "STGNN_PY",
    ]
    return {name: extract_js_const(name, html) for name in names}


def build_semiv2_zone_data(csv_dir: Path) -> dict[str, Any]:
    paths = sorted(csv_dir.glob("herald_semi_v2_predictions_sector_full_semiv2_full_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No Semi V2 sector prediction CSV found in {csv_dir}")

    zone_frames = []
    sector_frames = []
    zsec_frames = []
    for path in paths:
        df = pd.read_csv(path)
        df["ZE2020"] = df["ZE2020"].astype(str).str.zfill(4)
        zone = (
            df.groupby(["ZE2020", "target_year"])
            .agg(y_true=("y_true_sector", "sum"), y_pred=("y_pred_total", "first"))
            .reset_index()
        )
        zone_frames.append(zone)
        sector = (
            df.groupby(["sector", "target_year"])
            .agg(y_true=("y_true_sector", "sum"), y_pred=("y_pred_sector", "sum"))
            .reset_index()
        )
        sector_frames.append(sector)
        zsec = (
            df.groupby(["ZE2020", "target_year", "sector"])
            .agg(y_true=("y_true_sector", "first"), y_pred=("y_pred_sector", "median"))
            .reset_index()
        )
        zsec_frames.append(zsec)

    zones = (
        pd.concat(zone_frames)
        .groupby(["ZE2020", "target_year"])
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "median"))
        .reset_index()
    )
    zones["abs_error"] = (zones["y_pred"] - zones["y_true"]).abs()
    zones["wmape"] = zones["abs_error"] / zones["y_true"].replace(0, np.nan)

    sectors = (
        pd.concat(sector_frames)
        .groupby(["sector", "target_year"])
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "median"))
        .reset_index()
    )
    zsec = (
        pd.concat(zsec_frames)
        .groupby(["ZE2020", "target_year", "sector"])
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "median"))
        .reset_index()
    )

    zone_error: dict[str, dict[str, float]] = {}
    zone_pred: dict[str, dict[str, dict[str, int]]] = {}
    zone_real: dict[str, dict[str, int]] = {}
    zone_abs: dict[str, dict[str, int]] = {}
    for year in YEARS:
        part = zones[zones["target_year"] == int(year)]
        zone_error[year] = {}
        zone_pred[year] = {}
        zone_real[year] = {}
        zone_abs[year] = {}
        for row in part.itertuples(index=False):
            ze = str(row.ZE2020)
            zone_error[year][ze] = round(float(row.wmape), 6)
            zone_real[year][ze] = int(round(float(row.y_true)))
            zone_abs[year][ze] = int(round(float(row.abs_error)))
            zone_pred[year][ze] = {
                "y_true": int(round(float(row.y_true))),
                "y_pred": int(round(float(row.y_pred))),
                "abs_error": int(round(float(row.abs_error))),
            }

    sector_2025 = sectors[sectors["target_year"] == 2025].sort_values("y_true", ascending=False)
    sector_totals_2025 = {
        "sectors": sector_2025["sector"].tolist(),
        "y_true": [int(round(v)) for v in sector_2025["y_true"].tolist()],
        "y_pred": [int(round(v)) for v in sector_2025["y_pred"].tolist()],
    }

    zone_sector_pred: dict[str, dict[str, list[dict[str, int | str]]]] = {}
    for (ze, year), grp in zsec.groupby(["ZE2020", "target_year"]):
        zone_sector_pred.setdefault(str(ze), {})[str(int(year))] = [
            {"s": str(row.sector), "t": int(round(float(row.y_true))), "p": int(round(float(row.y_pred)))}
            for row in grp.sort_values("y_true", ascending=False).itertuples(index=False)
        ]

    france_year = (
        zones.groupby("target_year")
        .agg(y_true=("y_true", "sum"), y_pred=("y_pred", "sum"), abs_error=("abs_error", "sum"))
        .reset_index()
    )
    france_total = {
        str(int(row.target_year)): {
            "y_true": int(round(float(row.y_true))),
            "y_pred": int(round(float(row.y_pred))),
            "abs_error": int(round(float(row.abs_error))),
        }
        for row in france_year.itertuples(index=False)
    }

    return {
        "zone_error": zone_error,
        "zone_pred": zone_pred,
        "zone_real": zone_real,
        "zone_abs": zone_abs,
        "zone_sector_pred": zone_sector_pred,
        "sector_totals_2025": sector_totals_2025,
        "france_total": france_total,
    }


def js(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def non_null_pairs(mapping: dict[str, Any]) -> dict[str, float]:
    return {k: v for k, v in mapping.items() if v is not None}


def build_dashboard(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    per_run = run_root / "reports/per_run"
    csv_dir = run_root / "data_processed"
    out_path = Path(args.out)
    old = load_old_constants(Path(args.old_dashboard))

    models = [
        summarize_model("HERALD Semi V2 full", load_runs(per_run, "semiv2_full_*.json")),
        summarize_model("HERALD Semi V2 masked", load_runs(per_run, "semiv2_masked_variables_*.json")),
        summarize_model("HERALD V6 h64", load_runs(per_run, "v6ctrl_h64_full_*.json")),
        summarize_model("HERALD V7 fixed-alpha", load_runs(per_run, "v7_fixed_alpha_0.5_*.json")),
    ]
    models = [m for m in models if m is not None]
    by_label = {m["label"]: m for m in models}
    winner = by_label.get("HERALD Semi V2 full")
    if not winner:
        raise RuntimeError("Semi V2 full runs were not found.")

    zone_data = build_semiv2_zone_data(csv_dir)
    ridge_yr = old.get("RIDGE_YR") or {
        "2021": 0.067308,
        "2022": 0.086199,
        "2023": 0.077667,
        "2024": 0.030697,
        "2025": 0.033911,
    }
    arima_yr = old.get("ARIMA_PY") or {
        "2021": 0.125337,
        "2022": 0.097012,
        "2023": 0.037834,
        "2024": 0.08621,
        "2025": 0.034292,
    }
    dcrnn_yr = old.get("DCRNN_PY") or {"2021": 0.061726, "2022": 0.079231, "2023": 0.072603, "2024": 0.031876}
    stgnn_yr = old.get("STGNN_PY") or {"2021": 0.061086, "2022": 0.079178, "2023": 0.07253, "2024": 0.031752}

    payload = {
        "years": YEARS,
        "sectorLabels": SECTOR_LABELS,
        "models": models,
        "ridgeYear": ridge_yr,
        "arimaYear": arima_yr,
        "dcrnnYear": dcrnn_yr,
        "stgnnYear": stgnn_yr,
        "geojson": old.get("GEOJSON"),
        "zeNames": old.get("ZE_NAMES") or {},
        "graphData": old.get("GRAPH_DATA") or {},
        "newConn": old.get("NEW_CONN") or [],
        "zoneV6": old.get("ZONE_V6") or {},
        "zoneV6Preds": old.get("ZONE_V6_PREDS") or {},
        "zoneSemiError": zone_data["zone_error"],
        "zoneSemiPreds": zone_data["zone_pred"],
        "zoneSemiReal": zone_data["zone_real"],
        "zoneSemiAbs": zone_data["zone_abs"],
        "zoneSectorPreds": zone_data["zone_sector_pred"],
        "sectorTotals2025": zone_data["sector_totals_2025"],
        "franceTotal": zone_data["france_total"],
    }

    semi_2025 = winner["wmape_2025_median"]
    ridge_2025 = safe_float(ridge_yr.get("2025"))
    gain = None
    if semi_2025 is not None and ridge_2025:
        gain = 100 * (ridge_2025 - semi_2025) / ridge_2025

    plotly_script = '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
    if args.embed_plotly:
        bundle_path = Path(args.plotly_bundle)
        if not bundle_path.exists():
            raise FileNotFoundError(
                f"Plotly bundle not found: {bundle_path}. "
                "Run once with CDN or provide --plotly-bundle."
            )
        plotly_script = "<script>\n" + bundle_path.read_text(encoding="utf-8") + "\n</script>"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD Semi V2 - Dashboard scientifique</title>
{plotly_script}
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --semi:#f7834f; --v6:#4aa3ff;
    --v7:#b084f5; --ridge:#66bb6a; --bad:#ef5350; --good:#26a69a;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:Inter,Segoe UI,Arial,sans-serif; }}
  .wrap {{ max-width:1500px; margin:0 auto; padding:22px; }}
  h1 {{ margin:0 0 8px; font-size:30px; font-weight:760; letter-spacing:0; }}
  .subtitle {{ color:var(--muted); margin-bottom:18px; line-height:1.45; max-width:1100px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:12px; margin:16px 0 22px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .kpi .v {{ font-size:26px; font-weight:760; }}
  .kpi .l {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .section {{ margin-top:26px; }}
  .section-title {{ font-size:20px; font-weight:720; margin:0 0 6px; }}
  .section-note {{ color:var(--muted); font-size:14px; line-height:1.45; max-width:1200px; margin-bottom:10px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .grid-map {{ display:grid; grid-template-columns:minmax(620px,1.35fr) minmax(420px,0.9fr); gap:14px; align-items:start; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }}
  .controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:10px; }}
  select {{ background:#111525; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:7px 10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ border-bottom:1px solid var(--line); padding:7px 6px; text-align:left; }}
  th {{ color:#cbd5ff; font-weight:700; }}
  .mini {{ color:var(--muted); font-size:12px; line-height:1.4; }}
  .warn {{ color:#ffd180; }}
  @media (max-width:1000px) {{ .kpis,.grid2,.grid-map {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>HERALD Semi V2 - Dashboard scientifique</h1>
  <div class="subtitle">
    Lecture opérationnelle de la batterie Semi V2: comparaison des modèles, prévision observée vs prédite,
    erreurs territoriales, secteurs A10 et structure du graphe. Les valeurs centrales utilisent la médiane des seeds
    quand plusieurs seeds sont disponibles.
  </div>

  <div class="kpis">
    <div class="kpi"><div class="v">{semi_2025:.4f}</div><div class="l">WMAPE 2025 Semi V2 médian</div></div>
    <div class="kpi"><div class="v">{ridge_2025:.4f}</div><div class="l">WMAPE 2025 Ridge AR</div></div>
    <div class="kpi"><div class="v">{gain:.1f}%</div><div class="l">Gain Semi V2 vs Ridge en 2025</div></div>
    <div class="kpi"><div class="v">{winner['n']}</div><div class="l">Seeds Semi V2 full</div></div>
  </div>

  <div class="section">
    <div class="section-title">1. Comparaison principale des modèles</div>
    <div class="section-note">
      Ce bloc répond à la question centrale: quel modèle est le plus fiable, et surtout lequel tient en 2025.
      La barre 2025 est séparée de la moyenne historique pour éviter de cacher le problème opérationnel récent.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-model-2025" style="height:360px"></div></div>
      <div class="card"><div id="chart-model-mean" style="height:360px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">2. Erreur par année</div>
    <div class="section-note">
      Semi V2 n'est pas uniformément meilleur chaque année. Son intérêt est visible dans les années récentes,
      notamment 2024-2025, où le régime économique est le plus pertinent pour une utilisation prospective.
    </div>
    <div class="card"><div id="chart-year-lines" style="height:390px"></div></div>
  </div>

  <div class="section">
    <div class="section-title">3. Réel vs prédit - France entière</div>
    <div class="section-note">
      Ce graphique compare les volumes observés et prédits par Semi V2. Il permet de voir si une bonne WMAPE
      vient d'un vrai alignement en niveau ou seulement d'un effet relatif.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-france-real-pred" style="height:360px"></div></div>
      <div class="card"><div id="chart-seed-dist" style="height:360px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">4. Secteurs A10</div>
    <div class="section-note">
      Les secteurs sont lus en volumes et en erreur. Le volume évite l'erreur d'interprétation des cartes
      purement relatives: un secteur ou une zone bleue peut simplement avoir peu d'établissements.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-sector-volume" style="height:380px"></div></div>
      <div class="card"><div id="chart-sector-wmape" style="height:380px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">5. Carte de France interactive</div>
    <div class="section-note">
      Un seul fond de carte, avec métrique et année sélectionnables. Cliquez sur une zone pour afficher son réel
      vs prédit et sa composition A10. Les couleurs fortes indiquent les zones à auditer, pas une conclusion causale.
    </div>
    <div class="grid-map">
      <div class="card">
        <div class="controls">
          <label>Métrique <select id="map-metric" onchange="drawMap()">
            <option value="semi_error">Erreur Semi V2</option>
            <option value="diff_v6">Différence Semi V2 - V6</option>
            <option value="real_volume">Volume réel</option>
            <option value="abs_error">Erreur absolue Semi V2</option>
          </select></label>
          <label>Année <select id="map-year" onchange="drawMap()"></select></label>
        </div>
        <div id="chart-map" style="height:590px"></div>
      </div>
      <div class="card">
        <div id="zone-title" class="section-title">Sélectionnez une zone</div>
        <div class="mini">Le panneau compare l'évolution réelle et prédite de la zone, puis détaille les secteurs A10 pour l'année choisie.</div>
        <div id="chart-zone-time" style="height:280px"></div>
        <div id="chart-zone-sector" style="height:300px"></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">6. Graphe territorial appris</div>
    <div class="section-note">
      Le graphe est limité aux connexions les plus lisibles. Il sert à interpréter les relations territoriales
      apprises; il ne prouve pas seul un gain prédictif causal.
    </div>
    <div class="grid2">
      <div class="card">
        <div class="controls"><label>Année <select id="graph-year" onchange="drawGraph()"></select></label></div>
        <div id="chart-graph" style="height:540px"></div>
      </div>
      <div class="card">
        <div class="section-title">Connexions principales</div>
        <div id="conn-table"></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">7. Mécanismes internes</div>
    <div class="section-note">
      Alpha mesure le poids relatif de la composante locale dans V7/Semi V2; 1-alpha représente la contribution
      du graphe. Gamma compare l'importance apprise des priors géographique et mobilité.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-alpha" style="height:340px"></div></div>
      <div class="card"><div id="chart-gamma" style="height:340px"></div></div>
    </div>
  </div>
</div>

<script>
const DATA = {js(payload)};
const COLORS = {{
  semi:"#f7834f", masked:"#ffb074", v6:"#4aa3ff", v7:"#b084f5",
  ridge:"#66bb6a", arima:"#26a69a", dcrnn:"#ec407a", stgnn:"#ab47bc",
  real:"#e0e4f0", bad:"#ef5350", good:"#26a69a"
}};
const BASE_LAYOUT = {{
  paper_bgcolor:"#171b2d", plot_bgcolor:"#171b2d", font:{{color:"#eef2ff"}},
  margin:{{t:48,b:48,l:58,r:24}}, hoverlabel:{{bgcolor:"#111525"}}
}};

function model(label) {{ return DATA.models.find(m => m.label === label); }}
function fmt(x, d=4) {{ return x === null || x === undefined || Number.isNaN(x) ? "n/a" : Number(x).toFixed(d); }}
function zeName(ze) {{ return (DATA.zeNames && DATA.zeNames[ze]) ? DATA.zeNames[ze] : ze; }}
function pct(x) {{ return x === null || x === undefined ? "n/a" : (100*x).toFixed(2)+"%"; }}
function colorFor(label) {{
  if(label.includes("Semi V2 full")) return COLORS.semi;
  if(label.includes("masked")) return COLORS.masked;
  if(label.includes("V6")) return COLORS.v6;
  if(label.includes("V7")) return COLORS.v7;
  if(label.includes("Ridge")) return COLORS.ridge;
  if(label.includes("ARIMA")) return COLORS.arima;
  if(label.includes("DCRNN")) return COLORS.dcrnn;
  return COLORS.stgnn;
}}

function comparisonRows(metric) {{
  const rows = DATA.models.map(m => [m.label, metric === "2025" ? m.wmape_2025_median : m.mean, m.n]);
  if(metric === "2025") {{
    if(DATA.ridgeYear["2025"] !== undefined) rows.push(["Ridge AR", DATA.ridgeYear["2025"], 1]);
    if(DATA.arimaYear["2025"] !== undefined) rows.push(["ARIMA local", DATA.arimaYear["2025"], 1]);
  }} else {{
    const avg = obj => {{
      const vals = DATA.years.map(y => obj[y]).filter(v => v !== null && v !== undefined);
      return vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : null;
    }};
    rows.push(["Ridge AR", avg(DATA.ridgeYear), 1]);
    rows.push(["ARIMA local", avg(DATA.arimaYear), 1]);
    rows.push(["DCRNN", avg(DATA.dcrnnYear), 1]);
    rows.push(["Dynamic STGNN", avg(DATA.stgnnYear), 1]);
  }}
  return rows.filter(r => r[1] !== null && r[1] !== undefined).sort((a,b) => b[1]-a[1]);
}}

function drawModelBars() {{
  [["chart-model-2025","2025","WMAPE 2025"],["chart-model-mean","mean","WMAPE moyen 2021-2025"]].forEach(cfg => {{
    const rows = comparisonRows(cfg[1]);
    Plotly.newPlot(cfg[0], [{{
      type:"bar", orientation:"h", y:rows.map(r=>r[0]), x:rows.map(r=>r[1]),
      marker:{{color:rows.map(r=>colorFor(r[0]))}},
      text:rows.map(r=>fmt(r[1])), textposition:"auto",
      hovertemplate:"%{{y}}<br>"+cfg[2]+": %{{x:.4f}}<extra></extra>"
    }}], Object.assign({{}}, BASE_LAYOUT, {{
      title:cfg[2]+" - plus bas = meilleur",
      xaxis:{{title:"WMAPE", gridcolor:"#30364f"}},
      yaxis:{{automargin:true}},
    }}), {{responsive:true}});
  }});
}}

function drawYearLines() {{
  const traces = [];
  DATA.models.forEach(m => {{
    traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years,
      y:DATA.years.map(y=>m.per_year[y]), name:m.label,
      line:{{color:colorFor(m.label), width:m.label.includes("Semi V2 full") ? 4 : 2}},
      hovertemplate:"%{{x}}<br>%{{fullData.name}}: %{{y:.4f}}<extra></extra>"}});
  }});
  traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.ridgeYear[y]),
    name:"Ridge AR", line:{{color:COLORS.ridge, width:2, dash:"dash"}}}});
  traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.arimaYear[y]),
    name:"ARIMA local", line:{{color:COLORS.arima, width:2, dash:"dot"}}}});
  Plotly.newPlot("chart-year-lines", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"WMAPE par année", yaxis:{{title:"WMAPE", gridcolor:"#30364f"}}, xaxis:{{title:"Année", gridcolor:"#30364f"}},
    legend:{{orientation:"h", y:-0.25}}
  }}), {{responsive:true}});
}}

function drawFranceAndSeeds() {{
  const years = DATA.years;
  Plotly.newPlot("chart-france-real-pred", [
    {{type:"scatter", mode:"lines+markers", x:years, y:years.map(y=>DATA.franceTotal[y].y_true), name:"Réel", line:{{color:COLORS.real,width:3}}}},
    {{type:"scatter", mode:"lines+markers", x:years, y:years.map(y=>DATA.franceTotal[y].y_pred), name:"Prédit Semi V2", line:{{color:COLORS.semi,width:3}}}}
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Volumes France entière: réel vs prédit",
    yaxis:{{title:"Créations d'établissements", gridcolor:"#30364f"}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}}
  }}), {{responsive:true}});

  const seedTraces = DATA.models.filter(m=>m.seed_2025 && m.seed_2025.length).map(m => ({{
    type:"box", y:m.seed_2025, name:m.label, marker:{{color:colorFor(m.label)}}, boxmean:true
  }}));
  Plotly.newPlot("chart-seed-dist", seedTraces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"Distribution par seed - WMAPE 2025",
    yaxis:{{title:"WMAPE 2025", gridcolor:"#30364f"}}
  }}), {{responsive:true}});
}}

function drawSectorCharts() {{
  const st = DATA.sectorTotals2025;
  const labels = st.sectors.map(s => s+" - "+DATA.sectorLabels[s]);
  Plotly.newPlot("chart-sector-volume", [
    {{type:"bar", x:labels, y:st.y_true, name:"Réel", marker:{{color:COLORS.real, opacity:0.72}}}},
    {{type:"bar", x:labels, y:st.y_pred, name:"Prédit Semi V2", marker:{{color:COLORS.semi, opacity:0.82}}}}
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Volumes A10 2025: réel vs prédit",
    barmode:"group", xaxis:{{tickangle:-25, automargin:true}}, yaxis:{{title:"Établissements", gridcolor:"#30364f"}}
  }}), {{responsive:true}});

  const traces = DATA.models.filter(m => m.sector).map(m => ({{
    type:"bar", x:Object.keys(DATA.sectorLabels), y:Object.keys(DATA.sectorLabels).map(s=>m.sector[s]),
    name:m.label, marker:{{color:colorFor(m.label)}}
  }}));
  Plotly.newPlot("chart-sector-wmape", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"WMAPE sectoriel par modèle",
    barmode:"group", xaxis:{{title:"Secteur A10"}}, yaxis:{{title:"WMAPE", gridcolor:"#30364f"}}
  }}), {{responsive:true}});
}}

function mapValue(metric, year, ze) {{
  if(metric === "semi_error") return DATA.zoneSemiError[year] ? DATA.zoneSemiError[year][ze] : null;
  if(metric === "real_volume") return DATA.zoneSemiReal[year] ? DATA.zoneSemiReal[year][ze] : null;
  if(metric === "abs_error") return DATA.zoneSemiAbs[year] ? DATA.zoneSemiAbs[year][ze] : null;
  if(metric === "diff_v6") {{
    const s = DATA.zoneSemiError[year] ? DATA.zoneSemiError[year][ze] : null;
    const v = DATA.zoneV6[year] ? DATA.zoneV6[year][ze] : null;
    return (s !== null && s !== undefined && v !== null && v !== undefined) ? s - v : null;
  }}
  return null;
}}

function drawMap() {{
  const metric = document.getElementById("map-metric").value;
  const year = document.getElementById("map-year").value;
  if(!DATA.geojson) return;
  const locs = [], vals = [], texts = [];
  DATA.geojson.features.forEach(f => {{
    const ze = String((f.properties && (f.properties.ze2020 || f.properties.ZE2020)) || f.id).padStart(4,"0");
    const val = mapValue(metric, year, ze);
    locs.push(ze); vals.push(val);
    const pred = DATA.zoneSemiPreds[year] ? DATA.zoneSemiPreds[year][ze] : null;
    let base = "<b>"+zeName(ze)+"</b><br>ZE "+ze+"<br>";
    if(pred) base += "Réel: "+pred.y_true+"<br>Prédit Semi: "+pred.y_pred+"<br>Erreur abs.: "+pred.abs_error+"<br>";
    if(metric === "diff_v6") base += "Diff Semi-V6: "+pct(val);
    else if(metric === "semi_error") base += "WMAPE Semi: "+pct(val);
    else base += "Valeur: "+fmt(val,0);
    texts.push(base);
  }});
  const colorscale = metric === "diff_v6"
    ? [[0,"#26a69a"],[0.5,"#f5f5f5"],[1,"#ef5350"]]
    : [[0,"#edf8fb"],[0.35,"#b2e2e2"],[0.7,"#66c2a4"],[1,"#b2182b"]];
  Plotly.react("chart-map", [{{
    type:"choroplethmapbox", geojson:DATA.geojson, locations:locs, z:vals,
    featureidkey:"properties.ze2020", text:texts, hovertemplate:"%{{text}}<extra></extra>",
    colorscale:colorscale, marker:{{line:{{color:"#20253a", width:0.35}}}},
    colorbar:{{title:metric === "real_volume" ? "Volume" : metric === "abs_error" ? "Erreur abs." : "WMAPE"}}
  }}], {{
    paper_bgcolor:"#171b2d", plot_bgcolor:"#171b2d", font:{{color:"#eef2ff"}},
    mapbox:{{style:"carto-darkmatter", center:{{lat:46.7, lon:2.2}}, zoom:4.35}},
    margin:{{t:10,b:10,l:10,r:10}}
  }}, {{responsive:true}});
  const el = document.getElementById("chart-map");
  el.on("plotly_click", ev => {{
    if(ev.points && ev.points[0]) drawZone(ev.points[0].location, year);
  }});
}}

function drawZone(ze, year) {{
  document.getElementById("zone-title").textContent = zeName(ze)+" - ZE "+ze;
  const real = [], semi = [], v6 = [];
  DATA.years.forEach(y => {{
    const p = DATA.zoneSemiPreds[y] ? DATA.zoneSemiPreds[y][ze] : null;
    real.push(p ? p.y_true : null);
    semi.push(p ? p.y_pred : null);
    const vp = DATA.zoneV6Preds[y] ? DATA.zoneV6Preds[y][ze] : null;
    v6.push(vp ? (vp.y_pred || vp.pred || null) : null);
  }});
  const traces = [
    {{type:"scatter", mode:"lines+markers", x:DATA.years, y:real, name:"Réel", line:{{color:COLORS.real,width:3}}}},
    {{type:"scatter", mode:"lines+markers", x:DATA.years, y:semi, name:"Prédit Semi V2", line:{{color:COLORS.semi,width:3}}}}
  ];
  if(v6.some(x=>x!==null)) traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:v6, name:"Prédit V6", line:{{color:COLORS.v6,width:2,dash:"dash"}}}});
  Plotly.react("chart-zone-time", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"Zone: réel vs prédit", yaxis:{{title:"Établissements", gridcolor:"#30364f"}}, xaxis:{{gridcolor:"#30364f"}}
  }}), {{responsive:true}});

  const rows = DATA.zoneSectorPreds[ze] ? DATA.zoneSectorPreds[ze][year] : null;
  if(!rows) return;
  Plotly.react("chart-zone-sector", [
    {{type:"bar", x:rows.map(r=>r.s), y:rows.map(r=>r.t), name:"Réel", marker:{{color:COLORS.real, opacity:0.72}}}},
    {{type:"bar", x:rows.map(r=>r.s), y:rows.map(r=>r.p), name:"Prédit", marker:{{color:COLORS.semi, opacity:0.82}}}}
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"A10 dans la zone - "+year, barmode:"group",
    yaxis:{{title:"Établissements", gridcolor:"#30364f"}}
  }}), {{responsive:true}});
}}

function drawGraph() {{
  const year = document.getElementById("graph-year").value;
  const gd = DATA.graphData[year];
  if(!gd) {{ Plotly.purge("chart-graph"); document.getElementById("conn-table").innerHTML = "<div class='mini'>Aucun graphe disponible pour cette année.</div>"; return; }}
  let traces = [];
  if(Array.isArray(gd)) {{
    const edgeLon = [], edgeLat = [], nodeLon = [], nodeLat = [], nodeTxt = [];
    gd.slice(0,60).forEach(e => {{
      edgeLon.push(e.lon0, e.lon1, null); edgeLat.push(e.lat0, e.lat1, null);
      nodeLon.push(e.lon0, e.lon1); nodeLat.push(e.lat0, e.lat1);
      nodeTxt.push(e.name_i || e.ze_i || "", e.name_j || e.ze_j || "");
    }});
    traces = [
      {{type:"scattermapbox", mode:"lines", lon:edgeLon, lat:edgeLat, line:{{color:"rgba(247,131,79,0.55)",width:2}}, hoverinfo:"skip", name:"Connexions"}},
      {{type:"scattermapbox", mode:"markers", lon:nodeLon, lat:nodeLat, text:nodeTxt, hovertemplate:"%{{text}}<extra></extra>",
        marker:{{size:7,color:"#4aa3ff",opacity:0.82}}, name:"Zones"}}
    ];
    Plotly.react("chart-graph", traces, {{
      paper_bgcolor:"#171b2d", plot_bgcolor:"#171b2d", font:{{color:"#eef2ff"}},
      mapbox:{{style:"carto-darkmatter", center:{{lat:46.7, lon:2.2}}, zoom:4.25}},
      margin:{{t:10,b:10,l:10,r:10}}, showlegend:false
    }}, {{responsive:true}});
  }} else {{
    const edgeX = [], edgeY = [];
    (gd.edges || []).slice(0,80).forEach(e => {{
      edgeX.push(e.x0, e.x1, null); edgeY.push(e.y0, e.y1, null);
    }});
    const edgeTrace = {{type:"scatter", mode:"lines", x:edgeX, y:edgeY, line:{{color:"rgba(247,131,79,0.35)",width:1}}, hoverinfo:"skip"}};
    const nodeTrace = {{type:"scatter", mode:"markers+text", x:(gd.nodes||[]).map(n=>n.x), y:(gd.nodes||[]).map(n=>n.y),
      text:(gd.nodes||[]).map(n=>n.label || n.id), textposition:"top center",
      marker:{{size:(gd.nodes||[]).map(n=>n.size || 7), color:"#4aa3ff", opacity:0.82, line:{{color:"#eef2ff",width:0.4}}}},
      hovertext:(gd.nodes||[]).map(n=>n.name || n.label || n.id), hoverinfo:"text"}};
    Plotly.react("chart-graph", [edgeTrace,nodeTrace], Object.assign({{}}, BASE_LAYOUT, {{
      title:"Top connexions lisibles - "+year, xaxis:{{visible:false}}, yaxis:{{visible:false}}, showlegend:false
    }}), {{responsive:true}});
  }}

  const conns = (DATA.newConn || []).slice(0,20);
  let h = "<table><thead><tr><th>Connexion</th><th>Semi</th><th>V6</th><th>Variation</th></tr></thead><tbody>";
  conns.forEach(c => {{
    const label = c.label || ((c.from_name || c.from || "")+" → "+(c.to_name || c.to || ""));
    const semiW = c.semi_weight || c.weight_semi || c.weight;
    const v6W = c.v6_weight || c.weight_v6;
    const delta = c.delta || c.variation || (semiW !== undefined && v6W !== undefined ? semiW - v6W : null);
    h += "<tr><td>"+label+"</td><td>"+fmt(semiW,4)+"</td><td>"+fmt(v6W,4)+"</td><td>"+fmt(delta,4)+"</td></tr>";
  }});
  h += "</tbody></table>";
  document.getElementById("conn-table").innerHTML = h;
}}

function drawMechanisms() {{
  const semi = model("HERALD Semi V2 full");
  const alphaYears = Object.keys(semi.alpha || {{}}).filter(y => semi.alpha[y] !== null).sort();
  Plotly.newPlot("chart-alpha", [{{
    type:"scatter", mode:"lines+markers", x:alphaYears, y:alphaYears.map(y=>semi.alpha[y]),
    name:"Alpha local", line:{{color:COLORS.semi,width:3}}
  }}], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Alpha: poids local vs graphe", yaxis:{{title:"Alpha local", gridcolor:"#30364f", range:[0,1]}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}}
  }}), {{responsive:true}});

  const labels = DATA.models.map(m=>m.label);
  Plotly.newPlot("chart-gamma", [
    {{type:"bar", x:labels, y:DATA.models.map(m=>m.gamma_geo), name:"Gamma géographique", marker:{{color:"#4aa3ff"}}}},
    {{type:"bar", x:labels, y:DATA.models.map(m=>m.gamma_mob), name:"Gamma mobilité", marker:{{color:"#b084f5"}}}}
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Importance apprise des priors du graphe", barmode:"group",
    yaxis:{{title:"Gamma", gridcolor:"#30364f"}}, xaxis:{{tickangle:-15, automargin:true}}
  }}), {{responsive:true}});
}}

function initSelects() {{
  const my = document.getElementById("map-year");
  DATA.years.forEach(y => {{ const o=document.createElement("option"); o.value=y; o.textContent=y; my.appendChild(o); }});
  my.value = "2025";
  const gy = document.getElementById("graph-year");
  Object.keys(DATA.graphData || {{}}).sort().forEach(y => {{ const o=document.createElement("option"); o.value=y; o.textContent=y; gy.appendChild(o); }});
  if(gy.options.length) gy.value = gy.options[gy.options.length-1].value;
}}

initSelects();
drawModelBars();
drawYearLines();
drawFranceAndSeeds();
drawSectorCharts();
drawMap();
drawGraph();
drawMechanisms();
</script>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--old-dashboard", default=str(DEFAULT_OLD_DASH))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--embed-plotly", action="store_true", help="Embed Plotly in the HTML for offline sharing.")
    parser.add_argument("--plotly-bundle", default=str(DEFAULT_PLOTLY_BUNDLE))
    args = parser.parse_args()
    build_dashboard(args)


if __name__ == "__main__":
    main()
