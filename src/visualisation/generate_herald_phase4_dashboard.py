#!/usr/bin/env python3
"""Generate HERALD Phase 4 international dashboard (NL / BE / PT).

Reads existing Phase 4 panels and produces a presentation-ready HTML dashboard.
Model results section shows a placeholder until HPC outputs are available.

Usage:
    python3 src/visualisation/generate_herald_phase4_dashboard.py --country nl
    python3 src/visualisation/generate_herald_phase4_dashboard.py --country be
    python3 src/visualisation/generate_herald_phase4_dashboard.py --country pt
    python3 src/visualisation/generate_herald_phase4_dashboard.py --country all
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path("/home/jpdark/Downloads/project_recomm/dataset")

COUNTRY_CFG = {
    "nl": {
        "name": "Pays-Bas",
        "lang": "nl",
        "n_zones": 40,
        "zones_label": "COROP",
        "window": "2016–2024",
        "eval_years": list(range(2016, 2025)),
        "tensor_label": "qtensor_jobs",
        "tensor_col": "jobs",
        "tensor_note": "CBS 83582NED — postes de travail salariés × SBI-A10 × COROP",
        "tensor_concept": "Employment stock (postes de travail)",
        "q7_equiv": True,
        "births_file": BASE / "data/external/netherlands/processed/netherlands_births_panel.csv",
        "stock_file":  BASE / "data/external/netherlands/processed/netherlands_stock_panel.csv",
        "qtensor_file": BASE / "data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv",
        "hpc_glob": "hpc_results/herald_phase4c_nl_*",
        "color": "#4aa3ff",
        "suppressed_flag": True,
    },
    "be": {
        "name": "Belgique",
        "lang": "fr",
        "n_zones": 42,
        "zones_label": "arrondissements",
        "window": "2009–2020",
        "eval_years": list(range(2009, 2021)),
        "tensor_label": "qtensor_jobs",
        "tensor_col": "jobs",
        "tensor_note": "ONSS — postes de travail × NACE-BEL-A10 × arrondissement (Q4)",
        "tensor_concept": "Employment stock (postes de travail ONSS)",
        "q7_equiv": True,
        "births_file": BASE / "data/external/belgium/processed/belgium_births_panel.csv",
        "stock_file":  BASE / "data/external/belgium/processed/belgium_stock_panel.csv",
        "qtensor_file": BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv",
        "hpc_glob": "hpc_results/herald_phase4c_be_*",
        "color": "#f7c948",
        "suppressed_flag": False,
    },
    "pt": {
        "name": "Portugal",
        "lang": "pt",
        "n_zones": 25,
        "zones_label": "NUTS3",
        "window": "2009–2022",
        "eval_years": list(range(2009, 2023)),
        "tensor_label": "sector_births_tensor",
        "tensor_col": "births",
        "tensor_note": "INE 0009703 — naissances d'entreprises × CAE-A10 × NUTS3 (⚠️ proxy — NÃO é Q7 effectifs)",
        "tensor_concept": "Entrepreneurial births by sector (proxy, not employment stock)",
        "q7_equiv": False,
        "births_file": BASE / "data/external/portugal/processed/portugal_births_panel_nuts3.csv",
        "stock_file":  BASE / "data/external/portugal/processed/portugal_stock_panel_nuts3.csv",
        "qtensor_file": BASE / "data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv",
        "hpc_glob": "hpc_results/herald_phase4c_pt_*",
        "color": "#26a69a",
        "suppressed_flag": False,
    },
}

A10_LABELS = {
    "A":   "Agriculture",
    "BE":  "Industrie / énergie",
    "FZ":  "Construction",
    "GI":  "Commerce / transport",
    "JZ":  "Information / comm.",
    "KZ":  "Finance / assurance",
    "LZ":  "Immobilier",
    "MN":  "Services aux entreprises",
    "OPQ": "Services publics",
    "RSU": "Arts / loisirs",
}

CSS = """
  :root {
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --good:#26a69a; --bad:#ef5350;
    --warn:#ffd180;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font-family:Inter,Segoe UI,Arial,sans-serif; }
  .wrap { max-width:1500px; margin:0 auto; padding:22px; }
  h1 { margin:0 0 8px; font-size:30px; font-weight:760; }
  .subtitle { color:var(--muted); margin-bottom:18px; line-height:1.45; max-width:1100px; }
  .kpis { display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:12px; margin:16px 0 22px; }
  .kpi { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }
  .kpi .v { font-size:26px; font-weight:760; }
  .kpi .l { color:var(--muted); font-size:13px; margin-top:4px; }
  .section { margin-top:26px; }
  .section-title { font-size:20px; font-weight:720; margin:0 0 6px; }
  .section-note { color:var(--muted); font-size:14px; line-height:1.45; max-width:1200px; margin-bottom:10px; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { border-bottom:1px solid var(--line); padding:7px 6px; text-align:left; }
  th { color:#cbd5ff; font-weight:700; }
  .warn { color:var(--warn); }
  .pending-box { background:var(--panel2); border:2px dashed var(--line);
                 border-radius:8px; padding:30px; text-align:center; }
  .pending-box .icon { font-size:40px; margin-bottom:12px; }
  .pending-box .msg { font-size:18px; font-weight:700; margin-bottom:8px; }
  .pending-box .sub { color:var(--muted); font-size:14px; line-height:1.5; }
  .badge { display:inline-block; border-radius:999px; padding:3px 9px; font-size:11px;
           font-weight:700; vertical-align:middle; }
  .badge-done { background:#1a3a1a; color:#66bb6a; border:1px solid #66bb6a55; }
  .badge-pend { background:#2a2a1a; color:#ffd180; border:1px solid #ffd18055; }
  .badge-warn { background:#2a1a1a; color:#ef9a9a; border:1px solid #ef5350; }
  @media (max-width:900px) { .kpis,.grid2 { grid-template-columns:1fr; } }
"""


def _load_births(cfg: dict) -> pd.DataFrame:
    return pd.read_csv(cfg["births_file"])


def _load_stock(cfg: dict) -> pd.DataFrame:
    return pd.read_csv(cfg["stock_file"])


def _load_qtensor(cfg: dict) -> pd.DataFrame:
    return pd.read_csv(cfg["qtensor_file"])


def _births_trend_js(cfg: dict, df: pd.DataFrame, color: str) -> str:
    agg = df.groupby("target_year")["y"].sum().reset_index()
    years = agg["target_year"].tolist()
    vals = [round(v) for v in agg["y"].tolist()]
    return f"""
Plotly.newPlot('chart_births_{cfg['key']}', [{{
  x: {json.dumps(years)},
  y: {json.dumps(vals)},
  type: 'scatter', mode: 'lines+markers',
  name: 'Naissances totales',
  line: {{color: '{color}', width: 2}},
  marker: {{size: 6}}
}}], {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font: {{color:'#eef2ff', size:12}},
  margin: {{t:10, b:40, l:60, r:10}},
  xaxis: {{gridcolor:'#30364f', title:'Année'}},
  yaxis: {{gridcolor:'#30364f', title:'Naissances (total zones)'}},
  showlegend: false
}}, {{responsive:true, displayModeBar:false}});
"""


def _stock_trend_js(cfg: dict, df: pd.DataFrame, color: str) -> str:
    agg = df.groupby("target_year")["stock"].sum().reset_index()
    years = agg["target_year"].tolist()
    vals = [round(v) for v in agg["stock"].tolist()]
    return f"""
Plotly.newPlot('chart_stock_{cfg['key']}', [{{
  x: {json.dumps(years)},
  y: {json.dumps(vals)},
  type: 'scatter', mode: 'lines+markers',
  name: 'Stock total',
  line: {{color: '#b084f5', width: 2}},
  marker: {{size: 6}}
}}], {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font: {{color:'#eef2ff', size:12}},
  margin: {{t:10, b:40, l:70, r:10}},
  xaxis: {{gridcolor:'#30364f', title:'Année'}},
  yaxis: {{gridcolor:'#30364f', title:'Stock total (entreprises actives)'}},
  showlegend: false
}}, {{responsive:true, displayModeBar:false}});
"""


def _qtensor_heatmap_js(cfg: dict, df: pd.DataFrame) -> str:
    col = cfg["tensor_col"]
    pivot = df.pivot_table(index="a10", columns="target_year", values=col, aggfunc="sum")
    pivot = pivot.fillna(0)
    sectors = list(pivot.index)
    years = [int(c) for c in pivot.columns]
    z = pivot.values.tolist()
    z_rounded = [[round(v, 1) for v in row] for row in z]
    sector_labels = [A10_LABELS.get(s, s) for s in sectors]
    return f"""
Plotly.newPlot('chart_qtensor_{cfg['key']}', [{{
  type: 'heatmap',
  x: {json.dumps(years)},
  y: {json.dumps(sector_labels)},
  z: {json.dumps(z_rounded)},
  colorscale: 'Blues',
  showscale: true,
  hovertemplate: '%{{y}}<br>%{{x}}: %{{z:,.0f}}<extra></extra>'
}}], {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font: {{color:'#eef2ff', size:11}},
  margin: {{t:10, b:50, l:180, r:20}},
  xaxis: {{title:'Année', gridcolor:'#30364f'}},
  yaxis: {{title:'', automargin:true}}
}}, {{responsive:true, displayModeBar:false}});
"""


def _top_zones_js(cfg: dict, df: pd.DataFrame, color: str) -> str:
    top = (df.groupby("zone_id")["y"].sum()
           .nlargest(8).index.tolist())
    traces = []
    for z in top:
        sub = df[df["zone_id"] == z].sort_values("target_year")
        traces.append({
            "name": z,
            "x": sub["target_year"].tolist(),
            "y": [round(v) for v in sub["y"].tolist()],
        })
    traces_js = ",\n".join(
        f"{{x:{json.dumps(t['x'])}, y:{json.dumps(t['y'])}, "
        f"type:'scatter', mode:'lines', name:{json.dumps(t['name'])}, "
        f"line:{{width:1.5}}}}"
        for t in traces
    )
    return f"""
Plotly.newPlot('chart_zones_{cfg['key']}', [{traces_js}], {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font: {{color:'#eef2ff', size:12}},
  margin: {{t:10, b:40, l:60, r:10}},
  xaxis: {{gridcolor:'#30364f', title:'Année'}},
  yaxis: {{gridcolor:'#30364f', title:'Naissances'}},
  legend: {{bgcolor:'#171b2d', bordercolor:'#30364f', borderwidth:1, font:{{size:11}}}}
}}, {{responsive:true, displayModeBar:false}});
"""


def _top_zones_table(cfg: dict, df: pd.DataFrame) -> str:
    top = (df.groupby("zone_id")["y"].sum()
           .nlargest(10).reset_index()
           .rename(columns={"y": "total_births", "zone_id": "Zone"}))
    rows = ""
    for _, r in top.iterrows():
        rows += f"<tr><td>{r['Zone']}</td><td>{int(r['total_births']):,}</td></tr>"
    return f"""
<table>
  <thead><tr><th>Zone</th><th>Naissances cumulées</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
"""


FRANCE_WMAPE = 0.020398

SOURCE_SHORT = {
    "nl": "CBS 83631NED",
    "be": "Statbel beSTAT",
    "pt": "INE 0009702",
}


def _architecture_svg(country_key: str, cfg: dict, hpc_results: "dict | None") -> str:
    n_zones = cfg["n_zones"]
    zones_label = cfg["zones_label"]
    window = cfg["window"]
    source_short = SOURCE_SHORT.get(country_key, "—")
    n_seeds = hpc_results["n_seeds"] if hpc_results else cfg.get("n_seeds_expected", 5)

    if hpc_results:
        configs = hpc_results["configs"]
        best_wmape = min(c["mean"] for c in configs.values())
        best_wmape_str = f"{best_wmape:.3f}"
    else:
        best_wmape_str = "—"

    return f"""<svg viewBox="0 0 1020 420" style="width:100%;max-width:1020px;display:block;margin:12px auto 4px;font-family:Inter,Arial,sans-serif" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="ah"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#9aa4bf"/></marker>
    <marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#4aa3ff"/></marker>
    <marker id="ahg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#66bb6a"/></marker>
    <marker id="aho" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#f7834f"/></marker>
  </defs>
  <rect x="188" y="10" width="640" height="380" rx="12" fill="none" stroke="#2a3050" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="508" y="27" text-anchor="middle" fill="#9aa4bf" font-size="9.5" font-weight="700" letter-spacing="2">MODÈLE HERALD</text>
  <rect x="4" y="75" width="170" height="250" rx="10" fill="#111525" stroke="#4aa3ff" stroke-width="1.5"/>
  <text x="89" y="97"  text-anchor="middle" fill="#4aa3ff" font-size="9"   font-weight="700" letter-spacing="1.2">DONNÉES NATIONALES</text>
  <text x="89" y="117" text-anchor="middle" fill="#eef2ff" font-size="14"  font-weight="700">Registre national</text>
  <line x1="18" y1="126" x2="160" y2="126" stroke="#2a3050" stroke-width="1"/>
  <rect x="16" y="138" width="142" height="58" rx="6" fill="#141830" stroke="#4aa3ff28" stroke-width="1"/>
  <text x="87" y="156" text-anchor="middle" fill="#4aa3ff" font-size="9.5" font-weight="700">&#x2460;  Niveau récent</text>
  <text x="87" y="173" text-anchor="middle" fill="#9aa4bf" font-size="9">Combien d'entreprises ont été</text>
  <text x="87" y="187" text-anchor="middle" fill="#9aa4bf" font-size="9">créées ici l'an dernier ?</text>
  <rect x="16" y="204" width="142" height="58" rx="6" fill="#141830" stroke="#4aa3ff28" stroke-width="1"/>
  <text x="87" y="222" text-anchor="middle" fill="#4aa3ff" font-size="9.5" font-weight="700">&#x2461;  Tendance</text>
  <text x="87" y="239" text-anchor="middle" fill="#9aa4bf" font-size="9">Ce territoire accélère-t-il</text>
  <text x="87" y="253" text-anchor="middle" fill="#9aa4bf" font-size="9">ou ralentit-il ?</text>
  <text x="89" y="311" text-anchor="middle" fill="#9aa4bf" font-size="8">2 variables · {n_zones} {zones_label} · {source_short}</text>
  <path d="M174 135 Q187 110 197 80" stroke="#4aa3ff" stroke-width="1.5" fill="none" marker-end="url(#ahb)"/>
  <path d="M174 230 L197 235" stroke="#4aa3ff" stroke-width="1.5" fill="none" marker-end="url(#ahb)"/>
  <rect x="200" y="30" width="215" height="128" rx="10" fill="#111525" stroke="#66bb6a" stroke-width="1.5"/>
  <text x="307" y="52"  text-anchor="middle" fill="#66bb6a" font-size="9"  font-weight="700" letter-spacing="1.2">BASELINE LINÉAIRE</text>
  <text x="307" y="75"  text-anchor="middle" fill="#eef2ff" font-size="16" font-weight="700">Ridge AR</text>
  <line x1="214" y1="84" x2="401" y2="84" stroke="#2a3050" stroke-width="1"/>
  <text x="307" y="104" text-anchor="middle" fill="#9aa4bf" font-size="10" font-style="italic">y_ridge = b * x_t</text>
  <text x="307" y="122" text-anchor="middle" fill="#9aa4bf" font-size="9">Régression pénalisée (L2)</text>
  <text x="307" y="137" text-anchor="middle" fill="#9aa4bf" font-size="9">sur les signaux annuels</text>
  <path d="M415 94 Q580 44 680 202" stroke="#66bb6a" stroke-width="1.5" stroke-dasharray="5,3" fill="none" marker-end="url(#ahg)"/>
  <text x="560" y="58" fill="#66bb6a" font-size="9.5" text-anchor="middle" font-style="italic">y_ridge</text>
  <rect x="200" y="178" width="455" height="200" rx="10" fill="#111525" stroke="#f7834f" stroke-width="1.5"/>
  <text x="427" y="199" text-anchor="middle" fill="#f7834f" font-size="9" font-weight="700" letter-spacing="1.2">RÉSEAU DE NEURONES SPATIO-TEMPOREL</text>
  <line x1="214" y1="209" x2="641" y2="209" stroke="#2a3050" stroke-width="1"/>
  <rect x="214" y="219" width="185" height="145" rx="8" fill="#171b2d" stroke="#2d3352" stroke-width="1"/>
  <text x="306" y="238" text-anchor="middle" fill="#9aa4bf" font-size="8.5" font-weight="700" letter-spacing=".8">DYNAMIQUE LOCALE</text>
  <text x="306" y="268" text-anchor="middle" fill="#eef2ff" font-size="20" font-weight="700" font-style="italic">a * e_t</text>
  <text x="306" y="291" text-anchor="middle" fill="#9aa4bf" font-size="8.5">Profil intrinsèque de la zone</text>
  <text x="306" y="306" text-anchor="middle" fill="#9aa4bf" font-size="8.5">embedding appris par le modèle</text>
  <text x="306" y="323" text-anchor="middle" fill="#b084f5" font-size="8"  font-style="italic">α ∈ [0,1] — appris par zone et par an</text>
  <text x="306" y="338" text-anchor="middle" fill="#b084f5" font-size="8"  font-style="italic">modulé par le régime temporel z_t</text>
  <circle cx="422" cy="291" r="18" fill="#141830" stroke="#f7834f" stroke-width="1.5"/>
  <text x="422" y="297" text-anchor="middle" fill="#f7834f" font-size="21" font-weight="800">+</text>
  <line x1="399" y1="291" x2="404" y2="291" stroke="#f7834f" stroke-width="1.4" marker-end="url(#aho)"/>
  <line x1="445" y1="291" x2="440" y2="291" stroke="#f7834f" stroke-width="1.4" marker-end="url(#aho)"/>
  <rect x="445" y="219" width="200" height="145" rx="8" fill="#171b2d" stroke="#2d3352" stroke-width="1"/>
  <text x="545" y="238" text-anchor="middle" fill="#9aa4bf" font-size="8.5" font-weight="700" letter-spacing=".8">INFLUENCE TERRITORIALE</text>
  <text x="545" y="267" text-anchor="middle" fill="#eef2ff" font-size="17" font-weight="700" font-style="italic">(1-a) * m_t</text>
  <text x="545" y="291" text-anchor="middle" fill="#9aa4bf" font-size="8.5">Agrégation des zones voisines</text>
  <text x="545" y="308" text-anchor="middle" fill="#9aa4bf" font-size="8"  font-style="italic">g_mob * A_mob + g_geo * A_geo</text>
  <text x="545" y="325" text-anchor="middle" fill="#9aa4bf" font-size="8">Graphe interne : mobilite + contiguite</text>
  <text x="545" y="340" text-anchor="middle" fill="#9aa4bf" font-size="8">Phase 4A : A_mob = A_geo = identité</text>
  <text x="545" y="355" text-anchor="middle" fill="#ffd180" font-size="7.5" font-style="italic">adjacence reelle → Phase 4C</text>
  <path d="M422 309 Q422 372 560 372 Q672 372 678 248" stroke="#f7834f" stroke-width="1.4" fill="none" marker-end="url(#aho)"/>
  <text x="500" y="387" fill="#f7834f" font-size="8.5" text-anchor="middle" font-style="italic">résidu neural  e = f(x_t, A_mob, A_geo)</text>
  <circle cx="700" cy="225" r="24" fill="#111525" stroke="#9aa4bf" stroke-width="1.5"/>
  <text x="700" y="232" text-anchor="middle" fill="#eef2ff" font-size="22" font-weight="800">&#8853;</text>
  <text x="700" y="264" text-anchor="middle" fill="#9aa4bf" font-size="8.5" font-style="italic">y_z = y_ridge + e * s_z</text>
  <path d="M724 225 L772 205" stroke="#9aa4bf" stroke-width="1.4" fill="none" marker-end="url(#ah)"/>
  <rect x="774" y="30" width="200" height="358" rx="10" fill="#111525" stroke="#26a69a" stroke-width="1.5"/>
  <text x="874" y="52"  text-anchor="middle" fill="#26a69a" font-size="9" font-weight="700" letter-spacing="1.5">PRÉVISIONS</text>
  <line x1="786" y1="61" x2="962" y2="61" stroke="#2a3050" stroke-width="1"/>
  <rect x="786" y="70" width="176" height="128" rx="7" fill="#171b2d" stroke="#26a69a33" stroke-width="1"/>
  <text x="874" y="91"  text-anchor="middle" fill="#26a69a" font-size="8.5" font-weight="700" letter-spacing=".8">PAR ZONE</text>
  <text x="874" y="120" text-anchor="middle" fill="#eef2ff" font-size="18" font-weight="700" font-style="italic">y_z,t</text>
  <text x="874" y="143" text-anchor="middle" fill="#9aa4bf" font-size="8.5">Créations prévues par zone</text>
  <text x="874" y="158" text-anchor="middle" fill="#9aa4bf" font-size="8.5">{n_zones} {zones_label} · {window}</text>
  <text x="874" y="177" text-anchor="middle" fill="#26a69a" font-size="9.5" font-weight="700">WMAPE moyen : {best_wmape_str}</text>
  <text x="874" y="193" text-anchor="middle" fill="#9aa4bf" font-size="8">(vs France : 0.020)</text>
  <rect x="786" y="212" width="176" height="162" rx="7" fill="#171b2d" stroke="#26a69a33" stroke-width="1"/>
  <text x="874" y="232"  text-anchor="middle" fill="#26a69a"  font-size="8.5" font-weight="700" letter-spacing=".8">DECOMPOSITION SECTORIELLE</text>
  <text x="874" y="259"  text-anchor="middle" fill="#eef2ff"  font-size="17"  font-weight="700" font-style="italic">y_z,t,s</text>
  <text x="874" y="281"  text-anchor="middle" fill="#9aa4bf"  font-size="8.5">9 secteurs A10</text>
  <line x1="796" y1="287" x2="954" y2="287" stroke="#2a3050" stroke-width="0.8"/>
  <text x="874" y="302" text-anchor="middle" fill="#9aa4bf" font-size="8">Industrie · Construction</text>
  <text x="874" y="316" text-anchor="middle" fill="#9aa4bf" font-size="8">Commerce · Finance · Services</text>
  <text x="874" y="330" text-anchor="middle" fill="#9aa4bf" font-size="8">Immobilier · Information · Arts</text>
  <line x1="796" y1="338" x2="954" y2="338" stroke="#2a3050" stroke-width="0.8"/>
  <text x="874" y="353" text-anchor="middle" fill="#9aa4bf" font-size="7.5">Incertitude entre seeds (n={n_seeds})</text>
  <text x="874" y="367" text-anchor="middle" fill="#9aa4bf" font-size="7.5">Walk-forward strict ex-ante</text>
  <text x="508" y="407" text-anchor="middle" fill="#6a7490" font-size="7.8" font-style="italic">Figure 1. x_t : signaux naissances annuels. A_mob, A_geo : graphes internes. a_z,t in [0,1] : arbitrage local/graphe appris. z_t : regime latent. s_z : écart-type de zone.</text>
</svg>"""


def _auto_detect_run_root(cfg: dict) -> "Path | None":
    import glob as globlib
    hits = sorted(globlib.glob(str(BASE / cfg["hpc_glob"])))
    for d in reversed(hits):
        p = Path(d)
        if "smoke" in p.name:
            continue
        n = len(list((p / "reports" / "per_run").glob("*.json")))
        if n >= 30:
            return p
    return None


def _load_hpc_results(run_root: Path, country_key: str) -> dict:
    jsons = list((run_root / "reports" / "per_run").glob("*.json"))
    configs: dict[str, list] = {}
    for jpath in jsons:
        data = json.loads(jpath.read_text())
        for _tag_full, rd in data.items():
            tag = rd.get("run_tag", "")
            label = tag.replace(f"phase4c_{country_key}_", "").replace(f"phase4_{country_key}_", "")
            wmape = rd.get("total_wmape_mean") or rd.get("wmape_mean")
            if wmape is None:
                continue
            configs.setdefault(label, []).append({
                "wmape": float(wmape),
                "per_year": {int(k): float(v) for k, v in (rd.get("per_year_total") or {}).items()},
                "alpha": {int(k): float(v) for k, v in (rd.get("alpha_by_year") or {}).items()},
                "seed": rd.get("seed", 0),
            })
    agg = {}
    for label, runs in configs.items():
        wmapes = [r["wmape"] for r in runs]
        all_years = sorted({y for r in runs for y in r["per_year"]})
        agg[label] = {
            "wmapes": wmapes,
            "mean": float(np.mean(wmapes)),
            "std": float(np.std(wmapes)),
            "per_year": {
                y: float(np.mean([r["per_year"][y] for r in runs if y in r["per_year"]]))
                for y in all_years
            },
            "per_year_seeds": {
                y: [r["per_year"][y] for r in runs if y in r["per_year"]]
                for y in all_years
            },
            "alpha_median": {
                y: float(np.median([r["alpha"][y] for r in runs if y in r["alpha"]]))
                for y in sorted({y for r in runs for y in r["alpha"]})
            },
            "n": len(runs),
        }
    return {
        "configs": agg,
        "n_seeds": max((len(v["wmapes"]) for v in agg.values()), default=0),
        "run_root": run_root,
    }


_CONFIG_COLORS = {
    "baseline_side2":      "#4aa3ff",
    "qtensor_jobs_lag1":   "#26a69a",
    "sector_births_lag1":  "#26a69a",
    "no_qtensor_control":  "#9e9e9e",
}


def _hpc_results_js(country_key: str, cfg: dict, results: dict) -> str:
    ck = country_key
    configs = results["configs"]
    france = FRANCE_WMAPE

    # Sorted by mean WMAPE ascending for bar chart
    sorted_configs = sorted(configs.items(), key=lambda x: x[1]["mean"])
    labels = [c[0] for c in sorted_configs]
    means  = [round(c[1]["mean"], 6) for c in sorted_configs]
    stds   = [round(c[1]["std"], 6) for c in sorted_configs]
    colors = [_CONFIG_COLORS.get(lbl, "#b084f5") for lbl in labels]

    all_years = sorted({y for c in configs.values() for y in c["per_year"]})

    # Per-year lines: one trace per config
    year_traces = []
    for lbl, cd in configs.items():
        yvals = [round(cd["per_year"].get(y, float("nan")), 6) if cd["per_year"].get(y) is not None else None for y in all_years]
        year_traces.append(
            f"{{x:{json.dumps(all_years)}, y:{json.dumps(yvals)}, "
            f"type:'scatter', mode:'lines+markers', name:{json.dumps(lbl)}, "
            f"line:{{color:'{_CONFIG_COLORS.get(lbl, '#b084f5')}', width:2}}, "
            f"marker:{{size:5}}}}"
        )

    # Seed boxplots per config
    box_traces = []
    for lbl, cd in configs.items():
        box_traces.append(
            f"{{type:'box', y:{json.dumps(cd['wmapes'])}, name:{json.dumps(lbl)}, "
            f"marker:{{color:'{_CONFIG_COLORS.get(lbl, '#b084f5')}'}}, "
            f"boxpoints:'all', jitter:0.4, pointpos:0}}"
        )

    # Alpha by year (median across seeds) per config
    alpha_traces = []
    for lbl, cd in configs.items():
        if not cd["alpha_median"]:
            continue
        ay = sorted(cd["alpha_median"])
        av = [round(cd["alpha_median"][y], 4) for y in ay]
        alpha_traces.append(
            f"{{x:{json.dumps(ay)}, y:{json.dumps(av)}, "
            f"type:'scatter', mode:'lines+markers', name:{json.dumps(lbl)}, "
            f"line:{{color:'{_CONFIG_COLORS.get(lbl, '#b084f5')}', width:2}}, "
            f"marker:{{size:5}}}}"
        )

    base_layout = (
        "paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d', "
        "font:{color:'#eef2ff', size:12}, "
        "legend:{bgcolor:'#171b2d', bordercolor:'#30364f', borderwidth:1, font:{size:11}}"
    )

    # Last eval year bar chart (mirrors France "chart-model-2025")
    last_year = max(all_years) if all_years else None
    lastyear_js = ""
    if last_year is not None:
        ly_vals = [round(configs[lbl]["per_year"].get(last_year, float("nan")), 6) for lbl in labels]
        # Replace NaN with None for JSON
        ly_vals_safe = [v if not (isinstance(v, float) and v != v) else None for v in ly_vals]
        lastyear_js = (
            f"Plotly.newPlot('chart_lastyear_{ck}', [{{"
            f"type:'bar', orientation:'h', "
            f"y:{json.dumps(labels)}, x:{json.dumps(ly_vals_safe)}, "
            f"marker:{{color:{json.dumps(colors)}}}, "
            f"text:{json.dumps([f'{v:.4f}' if v is not None else '--' for v in ly_vals_safe])}, "
            f"textposition:'outside'"
            f"}}], {{"
            f"{base_layout}, "
            f"margin:{{t:10, b:50, l:180, r:80}}, "
            f"xaxis:{{gridcolor:'#30364f', title:'WMAPE {last_year}'}}, "
            f"yaxis:{{gridcolor:'#30364f'}}, "
            f"shapes:[{{type:'line', x0:{france}, x1:{france}, y0:-0.5, y1:{len(labels)-0.5}, "
            f"line:{{color:'#ffd180', width:1.5, dash:'dot'}}}}], "
            f"annotations:[{{x:{france}, y:{len(labels)-0.5}, text:'France {france:.4f}', "
            f"showarrow:false, font:{{color:'#ffd180', size:11}}, xanchor:'left', yanchor:'bottom'}}]"
            f"}}, {{responsive:true, displayModeBar:false}});"
        )

    alpha_js = ""
    if alpha_traces:
        alpha_js = (
            f"Plotly.newPlot('chart_alpha_{ck}', [{','.join(alpha_traces)}], {{"
            f"{base_layout}, margin:{{t:10, b:50, l:60, r:10}}, "
            f"xaxis:{{gridcolor:'#30364f', title:'Annee', dtick:1}}, "
            f"yaxis:{{gridcolor:'#30364f', title:'alpha (poids local median)', range:[0,1]}}"
            f"}}, {{responsive:true, displayModeBar:false}});"
        )

    return f"""
Plotly.newPlot('chart_config_bar_{ck}', [{{
  type:'bar', orientation:'h',
  y:{json.dumps(labels)}, x:{json.dumps(means)},
  error_x:{{type:'data', array:{json.dumps(stds)}, visible:true, color:'#9aa4bf'}},
  marker:{{color:{json.dumps(colors)}}},
  text:{json.dumps([f"{v:.4f}" for v in means])},
  textposition:'outside'
}}], {{
  {base_layout},
  margin:{{t:10, b:50, l:180, r:80}},
  xaxis:{{gridcolor:'#30364f', title:'WMAPE moyen'}},
  yaxis:{{gridcolor:'#30364f'}},
  shapes:[{{type:'line', x0:{france}, x1:{france}, y0:-0.5, y1:{len(labels)-0.5},
            line:{{color:'#ffd180', width:1.5, dash:'dot'}}}}],
  annotations:[{{x:{france}, y:{len(labels)-0.5}, text:'France {france:.4f}',
                 showarrow:false, font:{{color:'#ffd180', size:11}}, xanchor:'left', yanchor:'bottom'}}]
}}, {{responsive:true, displayModeBar:false}});

{lastyear_js}

Plotly.newPlot('chart_year_lines_{ck}', [{",".join(year_traces)}], {{
  {base_layout},
  margin:{{t:10, b:50, l:60, r:10}},
  xaxis:{{gridcolor:'#30364f', title:'Annee', dtick:1}},
  yaxis:{{gridcolor:'#30364f', title:'WMAPE'}}
}}, {{responsive:true, displayModeBar:false}});

Plotly.newPlot('chart_seed_box_{ck}', [{",".join(box_traces)}], {{
  {base_layout},
  margin:{{t:10, b:50, l:60, r:10}},
  xaxis:{{gridcolor:'#30364f'}},
  yaxis:{{gridcolor:'#30364f', title:'WMAPE par seed'}}
}}, {{responsive:true, displayModeBar:false}});

{alpha_js}
"""


def _hpc_results_section(country_key: str, cfg: dict, results: dict) -> str:
    ck = country_key
    configs = results["configs"]
    n_seeds = results["n_seeds"]
    run_root = results["run_root"]
    france = FRANCE_WMAPE

    best_label, best_cfg = min(configs.items(), key=lambda x: x[1]["mean"])
    best_wmape = best_cfg["mean"]
    best_std   = best_cfg["std"]

    # Tensor gain
    baseline = configs.get("baseline_side2", {})
    tensor_config = next(
        (c for k, c in configs.items() if "qtensor" in k or "sector_births" in k), None
    )
    tensor_gain_html = ""
    if baseline and tensor_config:
        gain_pct = 100 * (baseline["mean"] - tensor_config["mean"]) / baseline["mean"]
        sign = "+" if gain_pct > 0 else ""
        color = "#26a69a" if gain_pct > 0 else "#ef5350"
        symbol = "✅" if gain_pct > 0 else "❌"
        tensor_gain_html = (
            f'<div class="kpi"><div class="v" style="color:{color}">'
            f'{symbol} {sign}{gain_pct:.1f}%</div>'
            f'<div class="l">Tensor gain vs baseline</div></div>'
        )

    vs_france_pct = 100 * (best_wmape - france) / france
    vs_france_html = (
        f'<div class="kpi"><div class="v" style="color:#ef9a9a">×{best_wmape/france:.1f}</div>'
        f'<div class="l">vs France ({france:.4f})</div></div>'
    )

    # Per-year table
    all_years = sorted({y for c in configs.values() for y in c["per_year"]})
    config_keys = sorted(configs.keys())
    header_cells = "".join(f"<th>{k[:18]}</th>" for k in config_keys)
    year_rows = ""
    for y in all_years:
        row_cells = ""
        best_val = min(
            (c["per_year"].get(y) for c in configs.values() if c["per_year"].get(y) is not None),
            default=None,
        )
        for k in config_keys:
            v = configs[k]["per_year"].get(y)
            if v is None:
                row_cells += "<td>—</td>"
            else:
                bold = " font-weight:700; color:#4aa3ff;" if v == best_val else ""
                row_cells += f'<td style="{bold}">{v:.4f}</td>'
        year_rows += f"<tr><td>{y}</td>{row_cells}</tr>"

    has_alpha = any(c["alpha_median"] for c in configs.values())
    alpha_section = ""
    if has_alpha:
        alpha_section = f"""
  <div class="section">
    <div class="section-title">Évolution α (poids local médian par config)</div>
    <div class="section-note">α proche de 1 → modèle global prédomine ; proche de 0 → signal local.</div>
    <div class="card"><div id="chart_alpha_{ck}" style="height:300px;"></div></div>
  </div>
"""

    return f"""
<div class="section">
  <div class="section-title">Résultats HERALD — {cfg['name']}
    <span class="badge badge-done">✅ {n_seeds} seeds · {len(configs)} configs</span>
  </div>
  <div class="section-note">
    Batterie Phase 4 complète · <code>{run_root.name}</code> ·
    Référence France : WMAPE <b>{france:.4f}</b> (Q7 effectifs_lag1, 20 seeds).
  </div>

  <div class="kpis">
    <div class="kpi">
      <div class="v">{best_wmape:.4f}</div>
      <div class="l">Meilleur WMAPE ({best_label})</div>
      <div style="color:var(--muted); font-size:11px; margin-top:2px;">±{best_std:.4f} std</div>
    </div>
    {vs_france_html}
    {tensor_gain_html}
    <div class="kpi">
      <div class="v">{n_seeds}</div>
      <div class="l">Seeds · {len(configs)} configs</div>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">
        WMAPE moyen par config — ligne jaune = France ({france:.4f})
      </div>
      <div id="chart_config_bar_{ck}" style="height:260px;"></div>
    </div>
    <div class="card">
      <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">
        Distribution WMAPE par seed (boxplot)
      </div>
      <div id="chart_seed_box_{ck}" style="height:260px;"></div>
    </div>
  </div>

  <div class="section" style="margin-top:14px;">
    <div class="section-title" style="font-size:17px;">WMAPE par année</div>
    <div class="card">
      <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Évolution temporelle — valeur en gras = meilleur config pour l'année</div>
      <div id="chart_year_lines_{ck}" style="height:320px;"></div>
    </div>
  </div>

  <div class="section" style="margin-top:14px;">
    <div class="section-title" style="font-size:16px;">Tableau WMAPE par année × config</div>
    <div class="card" style="overflow-x:auto;">
      <table>
        <thead><tr><th>Année</th>{header_cells}</tr></thead>
        <tbody>{year_rows}</tbody>
      </table>
    </div>
  </div>

  {alpha_section}
</div>
"""


def _hpc_pending_section(country_key: str) -> str:
    return f"""
<div class="section">
  <div class="section-title">Résultats HERALD <span class="badge badge-pend">En attente</span></div>
  <div class="pending-box">
    <div class="icon">⏳</div>
    <div class="msg">Résultats HPC en attente</div>
    <div class="sub">
      Lancer : <code>bash hpc/phase4/submit_herald_phase4_{country_key}.sh</code>
    </div>
  </div>
</div>
"""


def _summary_stats(cfg: dict, births: pd.DataFrame, stock: pd.DataFrame, qtensor: pd.DataFrame) -> dict:
    col = cfg["tensor_col"]
    return {
        "n_zones": births["zone_id"].nunique(),
        "n_years_births": births["target_year"].nunique(),
        "births_min_year": int(births["target_year"].min()),
        "births_max_year": int(births["target_year"].max()),
        "total_births": int(births["y"].sum()),
        "stock_min_year": int(stock["target_year"].min()),
        "stock_max_year": int(stock["target_year"].max()),
        "tensor_min_year": int(qtensor["target_year"].min()),
        "tensor_max_year": int(qtensor["target_year"].max()),
        "n_a10": qtensor["a10"].nunique(),
        "tensor_rows": len(qtensor),
        "suppressed_pct": (
            round(100 * qtensor.get("jobs_suppressed", pd.Series([0])).sum() / len(qtensor), 2)
            if cfg.get("suppressed_flag") and "jobs_suppressed" in qtensor.columns
            else None
        ),
    }


def _load_predictions(run_root: Path, country_key: str) -> "dict | None":
    """Load total prediction CSVs, return aggregated data for the best config."""
    import glob as globlib
    ck = country_key
    csvs = list((run_root / "data_processed").glob(f"herald_semi_v2_predictions_total_*{ck}*.csv"))
    if not csvs:
        return None
    # Detect whether this is a phase4c or phase4 run
    _sample = csvs[0].stem.replace("herald_semi_v2_predictions_total_", "")
    prefix = f"full_phase4c_{ck}_" if f"full_phase4c_{ck}_" in _sample else f"full_phase4_{ck}_"

    # Group by config label
    config_data: dict[str, list[pd.DataFrame]] = {}
    for csv_path in csvs:
        stem = csv_path.stem  # herald_semi_v2_predictions_total_full_phase4c_nl_baseline_side2_seed_0_v1
        # Strip prefix up to the config label start
        tag_part = stem.replace("herald_semi_v2_predictions_total_", "")
        if prefix not in tag_part:
            continue
        after_prefix = tag_part[len(prefix):]  # baseline_side2_seed_0_v1
        # Strip seed + version suffix: _seed_<N>_v1
        import re
        m = re.match(r"(.+?)_seed_\d+_v\d+$", after_prefix)
        if not m:
            continue
        label = m.group(1)
        df = pd.read_csv(csv_path)
        config_data.setdefault(label, []).append(df)

    if not config_data:
        return None

    # Load HPC results to determine best config
    hpc = _load_hpc_results(run_root, country_key)
    if not hpc or not hpc["configs"]:
        return None
    best_label = min(hpc["configs"].items(), key=lambda x: x[1]["mean"])[0]

    # Fall back to first config if best label not found in predictions
    if best_label not in config_data:
        best_label = next(iter(config_data))

    seed_frames = config_data[best_label]
    all_years = sorted(set(int(y) for df in seed_frames for y in df["target_year"].unique()))

    by_year: dict[int, dict] = {}
    seed_wmapes_by_year: dict[int, list] = {}

    for year in all_years:
        y_true_seeds = []
        y_pred_seeds = []
        ridge_seeds = []
        for df in seed_frames:
            sub = df[df["target_year"] == year]
            if sub.empty:
                continue
            y_true_total = sub["y_true"].sum()
            y_pred_total = sub["y_pred"].sum()
            ridge_total = sub["ridge_pred"].sum() if "ridge_pred" in sub.columns else float("nan")
            y_true_seeds.append(y_true_total)
            y_pred_seeds.append(y_pred_total)
            ridge_seeds.append(ridge_total)

            # Per-seed WMAPE for this year
            denom = sub["y_true"].sum()
            if denom > 0:
                wmape = float(sub["abs_error"].sum() / denom) if "abs_error" in sub.columns else float("nan")
            else:
                wmape = float("nan")
            seed_wmapes_by_year.setdefault(year, []).append(wmape)

        if y_true_seeds:
            by_year[year] = {
                "y_true": float(np.median(y_true_seeds)),
                "y_pred": float(np.median(y_pred_seeds)),
                "ridge": float(np.nanmedian(ridge_seeds)) if ridge_seeds else float("nan"),
            }

    return {
        "best_label": best_label,
        "by_year": by_year,
        "seed_wmapes_by_year": seed_wmapes_by_year,
        "n_seeds": len(seed_frames),
    }


def _load_sector_predictions(run_root: Path, country_key: str, best_label: str) -> "dict | None":
    """Load sector prediction CSVs for the best config, return aggregated data."""
    import re
    ck = country_key
    csvs = list((run_root / "data_processed").glob(f"herald_semi_v2_predictions_sector_*{ck}*{best_label}*.csv"))
    _sample2 = csvs[0].stem.replace("herald_semi_v2_predictions_sector_", "") if csvs else ""
    prefix = f"full_phase4c_{ck}_" if f"full_phase4c_{ck}_" in _sample2 else f"full_phase4_{ck}_"
    if not csvs:
        return None

    seed_frames = []
    for csv_path in csvs:
        stem = csv_path.stem
        tag_part = stem.replace("herald_semi_v2_predictions_sector_", "")
        if prefix not in tag_part:
            continue
        after_prefix = tag_part[len(prefix):]
        m = re.match(r"(.+?)_seed_\d+_v\d+$", after_prefix)
        if not m:
            continue
        if m.group(1) != best_label:
            continue
        seed_frames.append(pd.read_csv(csv_path))

    if not seed_frames:
        return None

    all_sectors = sorted(set(s for df in seed_frames for s in df["sector"].unique()))
    all_years = sorted(set(int(y) for df in seed_frames for y in df["target_year"].unique()))

    y_true_agg: dict[tuple, list] = {}
    y_pred_agg: dict[tuple, list] = {}

    for df in seed_frames:
        for year in all_years:
            sub = df[df["target_year"] == year]
            for sector in all_sectors:
                ssub = sub[sub["sector"] == sector]
                key = (sector, year)
                y_true_agg.setdefault(key, []).append(float(ssub["y_true_sector"].sum()) if not ssub.empty else 0.0)
                y_pred_agg.setdefault(key, []).append(float(ssub["y_pred_sector"].sum()) if not ssub.empty else 0.0)

    y_true_final = {k: float(np.median(v)) for k, v in y_true_agg.items()}
    y_pred_final = {k: float(np.median(v)) for k, v in y_pred_agg.items()}

    return {
        "sectors": all_sectors,
        "years": all_years,
        "y_true": y_true_final,
        "y_pred": y_pred_final,
    }


def _real_pred_js(country_key: str, pred_data: dict, color: str) -> str:
    """Two Plotly charts: real vs pred lines (left) + per-year seed WMAPE boxplot (right)."""
    ck = country_key
    by_year = pred_data["by_year"]
    years = sorted(by_year.keys())
    y_true = [round(by_year[y]["y_true"]) for y in years]
    y_pred = [round(by_year[y]["y_pred"]) for y in years]
    ridge = [by_year[y]["ridge"] for y in years]
    ridge_rounded = [round(v) if not (isinstance(v, float) and v != v) else None for v in ridge]
    country_name = COUNTRY_CFG[country_key]["name"]
    best_label = pred_data["best_label"]

    seed_wmapes = pred_data["seed_wmapes_by_year"]
    box_traces = []
    for y in years:
        vals = [v for v in seed_wmapes.get(y, []) if not (isinstance(v, float) and v != v)]
        if vals:
            box_traces.append(
                f"{{type:'box', y:{json.dumps(vals)}, name:'{y}', "
                f"marker:{{color:'{color}'}}, boxpoints:'all', jitter:0.4, pointpos:0}}"
            )

    base_layout = (
        "paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d', "
        "font:{color:'#eef2ff', size:12}, "
        "legend:{bgcolor:'#171b2d', bordercolor:'#30364f', borderwidth:1, font:{size:11}}"
    )

    ridge_trace = ""
    if any(v is not None for v in ridge_rounded):
        ridge_trace = (
            f",{{x:{json.dumps(years)}, y:{json.dumps(ridge_rounded)}, "
            f"type:'scatter', mode:'lines+markers', name:'Ridge AR', "
            f"line:{{color:'#66bb6a', width:2, dash:'dot'}}, marker:{{size:5}}}}"
        )

    box_js = ""
    if box_traces:
        box_js = (
            f"\nPlotly.newPlot('chart_seed_dist_{ck}', [{','.join(box_traces)}], {{"
            f"{base_layout}, "
            f"margin:{{t:10, b:50, l:60, r:10}}, "
            f"xaxis:{{gridcolor:'#30364f', title:'Annee', type:'category'}}, "
            f"yaxis:{{gridcolor:'#30364f', title:'WMAPE par seed'}}"
            f"}}, {{responsive:true, displayModeBar:false}});"
        )

    return f"""
Plotly.newPlot('chart_real_pred_{ck}', [
  {{x:{json.dumps(years)}, y:{json.dumps(y_true)}, type:'scatter', mode:'lines+markers',
   name:'Reel', line:{{color:'#ffffff', width:2}}, marker:{{size:6}}}},
  {{x:{json.dumps(years)}, y:{json.dumps(y_pred)}, type:'scatter', mode:'lines+markers',
   name:'HERALD ({best_label})', line:{{color:'{color}', width:2}}, marker:{{size:6}}}}
  {ridge_trace}
], {{
  {base_layout},
  margin:{{t:10, b:50, l:70, r:10}},
  xaxis:{{gridcolor:'#30364f', title:'Annee', dtick:1}},
  yaxis:{{gridcolor:'#30364f', title:'Naissances totales'}}
}}, {{responsive:true, displayModeBar:false}});
{box_js}
"""


def _sector_js(country_key: str, sector_data: dict, color: str) -> str:
    """Stacked bar chart: sector volume by year (y_true as reference with y_pred overlay)."""
    ck = country_key
    sectors = sector_data["sectors"]
    years = sector_data["years"]
    y_true = sector_data["y_true"]

    # Build one trace per sector for y_true (stacked reference)
    sector_colors = [
        "#4aa3ff", "#26a69a", "#f7c948", "#b084f5", "#f7834f",
        "#66bb6a", "#ef5350", "#9aa4bf", "#ffd180", "#80cbc4",
    ]
    traces = []
    for i, sector in enumerate(sectors):
        label = A10_LABELS.get(sector, sector)
        y_vals = [round(y_true.get((sector, yr), 0.0)) for yr in years]
        col = sector_colors[i % len(sector_colors)]
        traces.append(
            f"{{x:{json.dumps(years)}, y:{json.dumps(y_vals)}, "
            f"type:'bar', name:{json.dumps(label)}, "
            f"marker:{{color:'{col}', opacity:0.85}}}}"
        )

    base_layout = (
        "paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d', "
        "font:{color:'#eef2ff', size:12}, "
        "legend:{bgcolor:'#171b2d', bordercolor:'#30364f', borderwidth:1, font:{size:11}}"
    )

    return f"""
Plotly.newPlot('chart_sector_{ck}', [{','.join(traces)}], {{
  {base_layout},
  barmode: 'stack',
  margin:{{t:10, b:50, l:70, r:10}},
  xaxis:{{gridcolor:'#30364f', title:'Annee', dtick:1}},
  yaxis:{{gridcolor:'#30364f', title:'Naissances (secteurs A10)'}}
}}, {{responsive:true, displayModeBar:false}});
"""


def _protocole_section(cfg: dict, run_root: "Path | None") -> str:
    """Build walk-forward protocol table from splits.csv."""
    ck = cfg["key"]
    splits_path = BASE / f"data/processed/phase4/{ck}/splits.csv"
    if not splits_path.exists():
        return ""
    splits = pd.read_csv(splits_path)
    rows = ""
    for _, row in splits.iterrows():
        train_min = int(row["train_years_min"])
        train_max = int(row["train_years_max"])
        target = int(row["target_year"])
        rows += (
            f"<tr>"
            f"<td>{target}</td>"
            f"<td>{train_min}–{train_max}</td>"
            f"<td>walk-forward</td>"
            f"</tr>"
        )
    return f"""
  <div class="section">
    <div class="section-title">Protocole</div>
    <div class="section-note">
      Chaque annee est testee comme une vraie annee future : HERALD est entraine uniquement avec les annees
      anterieures au fold. Ce tableau rend visible les annees qui entrent dans l'entrainement et l'annee
      qui sert de comparaison au reel.
    </div>
    <div class="card">
      <table>
        <thead><tr>
          <th>Annee predite</th>
          <th>Annees utilisees pour entrainer</th>
          <th>Protocole</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>"""


def build_country_dashboard(country_key: str, out_path: Path) -> None:
    cfg = {**COUNTRY_CFG[country_key], "key": country_key}
    ck = country_key
    color = cfg["color"]

    births = _load_births(cfg)
    stock = _load_stock(cfg)
    qtensor = _load_qtensor(cfg)
    stats = _summary_stats(cfg, births, stock, qtensor)

    run_root = _auto_detect_run_root(cfg)
    hpc_results = _load_hpc_results(run_root, country_key) if run_root else None
    tensor_warn = not cfg["q7_equiv"]

    # Load prediction data for sections 3 & 4
    pred_data: "dict | None" = None
    sector_data: "dict | None" = None
    if run_root is not None:
        pred_data = _load_predictions(run_root, country_key)
        if pred_data is not None:
            sector_data = _load_sector_predictions(run_root, country_key, pred_data["best_label"])

    tensor_badge = (
        '<span class="badge badge-warn">proxy — nao e Q7 effectifs</span>'
        if tensor_warn
        else '<span class="badge badge-done">Q7-equivalent</span>'
    )

    suppressed_note = ""
    if cfg.get("suppressed_flag") and stats["suppressed_pct"] is not None:
        suppressed_note = (
            f'<div class="section-note warn">'
            f'{stats["suppressed_pct"]:.1f}% cellules supprimees CBS (divulgation statistique) '
            f'-- rempli a 0 avec flag <code>jobs_suppressed</code>.</div>'
        )

    pt_tensor_warning = ""
    if tensor_warn:
        pt_tensor_warning = (
            '<div class="card" style="border-color:#ef535066; margin-bottom:14px;">'
            '<b style="color:#ef9a9a;">Tensor framing critique -- Portugal</b><br>'
            '<span style="color:var(--muted); font-size:13px;">'
            'Le tensor <code>sector_births_tensor</code> represente des <b>naissances d\'entreprises par secteur CAE</b>, '
            'pas un stock d\'emploi (Q7 effectifs). KZ = 0 partout (le secteur financier n\'apparait pas dans les naissances INE). '
            'Les comparaisons NL/BE PT sont qualitatives uniquement. Un vrai Q7-equivalent (GEP Quadros de Pessoal) est '
            'documente mais non ingéré — prévu Phase 4B si nécessaire.'
            '</span></div>'
        )

    # Build JS blocks
    hpc_js = _hpc_results_js(country_key, cfg, hpc_results) if hpc_results else ""
    real_pred_js_block = _real_pred_js(country_key, pred_data, color) if pred_data else ""
    sector_js_block = _sector_js(country_key, sector_data, color) if sector_data else ""

    births_js = _births_trend_js(cfg, births, color)
    stock_js = _stock_trend_js(cfg, stock, color)
    qtensor_js = _qtensor_heatmap_js(cfg, qtensor)
    zones_js = _top_zones_js(cfg, births, color)
    zones_table = _top_zones_table(cfg, births)

    arch_svg = _architecture_svg(country_key, cfg, hpc_results)

    # --- KPI values ---
    if hpc_results:
        configs = hpc_results["configs"]
        n_seeds = hpc_results["n_seeds"]
        n_configs = len(configs)
        best_label, best_cfg_data = min(configs.items(), key=lambda x: x[1]["mean"])
        best_wmape = best_cfg_data["mean"]
        best_wmape_str = f"{best_wmape:.4f}"
        baseline = configs.get("baseline_side2", {})
        tensor_config_data = next(
            (c for k, c in configs.items() if "qtensor" in k or "sector_births" in k), None
        )
        if baseline and tensor_config_data:
            gain_pct = 100 * (baseline["mean"] - tensor_config_data["mean"]) / baseline["mean"]
            sign = "+" if gain_pct > 0 else ""
            gain_color = "#26a69a" if gain_pct > 0 else "#ef5350"
            gain_str = f'<div class="v" style="color:{gain_color}">{sign}{gain_pct:.1f}%</div>'
        else:
            gain_str = '<div class="v">--</div>'
        vs_ratio = best_wmape / FRANCE_WMAPE
        vs_str = f'<div class="v" style="color:#ef9a9a">x{vs_ratio:.1f}</div>'
        seeds_configs_str = f'<div class="v">{n_seeds} · {n_configs}</div>'
    else:
        best_wmape = None
        best_wmape_str = "--"
        best_label = "--"
        gain_str = '<div class="v">--</div>'
        vs_str = '<div class="v">--</div>'
        n_seeds = cfg.get("n_seeds_expected", 5)
        n_configs = 0
        seeds_configs_str = f'<div class="v">{n_seeds} · --</div>'

    eval_window = cfg["window"]
    n_eval_years = len(cfg.get("eval_years", []))

    # ---- Protocole section ----
    protocole_section = _protocole_section(cfg, run_root)

    # ---- Section 1: Comparaison ----
    if hpc_results:
        configs = hpc_results["configs"]
        n_cfgs = len(configs)
        last_eval_year = max({y for c in configs.values() for y in c["per_year"]}, default="?")
        section1 = f"""
  <div class="section">
    <div class="section-title">1. Comparaison</div>
    <div class="section-note">HERALD compare sur {n_cfgs} configurations ({cfg['window']}). Ligne jaune = France WMAPE {FRANCE_WMAPE:.4f}.</div>
    <div class="grid2">
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">WMAPE moyen (toutes annees) par config</div>
        <div id="chart_config_bar_{ck}" style="height:360px;"></div>
      </div>
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">WMAPE annee {last_eval_year} par config</div>
        <div id="chart_lastyear_{ck}" style="height:360px;"></div>
      </div>
    </div>
  </div>"""
    else:
        section1 = f"""
  <div class="section">
    <div class="section-title">1. Comparaison</div>
    <div class="section-note">Resultats HPC non disponibles — lancer <code>bash hpc/phase4/submit_herald_phase4_{ck}.sh</code></div>
    <div class="pending-box">
      <div class="icon">...</div>
      <div class="msg">Resultats HPC en attente</div>
    </div>
  </div>"""

    # ---- Section 2: Erreur par annee ----
    if hpc_results:
        section2 = f"""
  <div class="section">
    <div class="section-title">2. Erreur par année</div>
    <div class="section-note">Evolution temporelle du WMAPE par configuration ({cfg['window']}).</div>
    <div class="card">
      <div id="chart_year_lines_{ck}" style="height:390px;"></div>
    </div>
  </div>"""
    else:
        section2 = ""

    # ---- Section 3: Réel vs prédit ----
    if pred_data:
        section3 = f"""
  <div class="section">
    <div class="section-title">3. Réel vs prédit</div>
    <div class="section-note">HERALD predit les creations d'etablissements par zone, compare au reel et a la baseline Ridge AR.</div>
    <div class="grid2">
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Volume total (mediane seeds) — reel, HERALD, Ridge</div>
        <div id="chart_real_pred_{ck}" style="height:380px;"></div>
      </div>
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Distribution WMAPE par seed et par annee</div>
        <div id="chart_seed_dist_{ck}" style="height:380px;"></div>
      </div>
    </div>
  </div>"""
    else:
        section3 = f"""
  <div class="section">
    <div class="section-title">3. Réel vs prédit</div>
    <div class="pending-box">
      <div class="icon">...</div>
      <div class="msg">Predictions non disponibles</div>
      <div class="sub">Lancer la batterie HPC pour obtenir les fichiers predictions_total_*</div>
    </div>
  </div>"""

    # ---- Section 4: Secteurs A10 ----
    if sector_data:
        n_seeds_pred = pred_data["n_seeds"] if pred_data else "?"
        section4 = f"""
  <div class="section">
    <div class="section-title">4. Secteurs A10</div>
    <div class="section-note">Décomposition sectorielle A10 — meilleure configuration ({best_label}), médiane sur {n_seeds_pred} seeds.</div>
    <div class="card">
      <div id="chart_sector_{ck}" style="height:430px;"></div>
    </div>
  </div>"""
    else:
        section4 = f"""
  <div class="section">
    <div class="section-title">4. Secteurs A10</div>
    <div class="pending-box">
      <div class="icon">...</div>
      <div class="msg">Décomposition sectorielle non disponible</div>
      <div class="sub">Lancer la batterie HPC pour obtenir les fichiers predictions_sector_*</div>
    </div>
  </div>"""

    # ---- Section 5: Carte territoriale ----
    section5 = f"""
  <div class="section">
    <div class="section-title">5. Carte territoriale</div>
    <div class="pending-box">
      <div class="icon">...</div>
      <div class="msg">Carte territoriale — Phase 4C (coordonnees NUTS3/COROP en cours d'integration)</div>
      <div class="sub">Les coordonnees spatiales {cfg['zones_label']} seront integrees en Phase 4C pour produire la choropleth.</div>
    </div>
  </div>"""

    # ---- Section 6: Régimes appris ----
    section6 = ""
    if hpc_results:
        configs = hpc_results["configs"]
        has_alpha = any(c["alpha_median"] for c in configs.values())
        if has_alpha:
            all_years_alpha = sorted({y for c in configs.values() for y in c["per_year"]})
            config_keys = sorted(configs.keys())
            header_cells = "".join(f"<th>{k[:18]}</th>" for k in config_keys)
            year_rows = ""
            for y in all_years_alpha:
                best_val = min(
                    (c["per_year"].get(y) for c in configs.values() if c["per_year"].get(y) is not None),
                    default=None,
                )
                row_cells = ""
                for k in config_keys:
                    v = configs[k]["per_year"].get(y)
                    if v is None:
                        row_cells += "<td>--</td>"
                    else:
                        bold = " font-weight:700; color:#4aa3ff;" if v == best_val else ""
                        row_cells += f'<td style="{bold}">{v:.4f}</td>'
                year_rows += f"<tr><td>{y}</td>{row_cells}</tr>"
            section6 = f"""
  <div class="section">
    <div class="section-title">6. Régimes appris</div>
    <div class="section-note">α proche de 1 : dynamique locale prédomine. Proche de 0 : influence territoriale prédomine.</div>
    <div class="grid2">
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Evolution alpha (poids local median par config)</div>
        <div id="chart_alpha_{ck}" style="height:320px;"></div>
      </div>
      <div class="card" style="overflow-x:auto;">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">WMAPE par annee x config</div>
        <table>
          <thead><tr><th>Annee</th>{header_cells}</tr></thead>
          <tbody>{year_rows}</tbody>
        </table>
      </div>
    </div>
  </div>"""

    # ---- Section 7: Données ----
    section7 = f"""
  <div class="section">
    <div class="section-title">7. Données — {cfg['name']}</div>
    <div class="section-note">Naissances d'entreprises par zone · stock actif · tensor sectoriel ({cfg['window']}).</div>

    <div style="margin-top:10px; margin-bottom:4px; font-size:15px; font-weight:700; color:var(--muted);">Naissances</div>
    <div class="grid2">
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Naissances totales (toutes zones)</div>
        <div id="chart_births_{ck}" style="height:280px;"></div>
      </div>
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Top 8 zones — evolution temporelle</div>
        <div id="chart_zones_{ck}" style="height:280px;"></div>
      </div>
    </div>
    <div class="card" style="margin-top:12px;">
      <div style="color:var(--muted); font-size:12px; margin-bottom:8px;">Top 10 zones — naissances cumulees</div>
      {zones_table}
    </div>

    <div style="margin-top:16px; margin-bottom:4px; font-size:15px; font-weight:700; color:var(--muted);">Stock actif</div>
    <div class="card">
      <div id="chart_stock_{ck}" style="height:280px;"></div>
    </div>

    <div style="margin-top:16px; margin-bottom:4px; font-size:15px; font-weight:700; color:var(--muted);">Tensor sectoriel ({cfg['tensor_label']})</div>
    <div class="section-note">{cfg['tensor_note']} · {stats['tensor_rows']} lignes · {stats['n_a10']} secteurs A10 · {stats['tensor_min_year']}–{stats['tensor_max_year']}.</div>
    {suppressed_note}
    <div class="card">
      <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Heatmap — signal agrege (toutes zones) par secteur x annee</div>
      <div id="chart_qtensor_{ck}" style="height:340px;"></div>
    </div>
  </div>"""

    # ---- Section 8: Sources et protocole ----
    section8 = f"""
  <div class="section" style="margin-top:32px; border-top:1px solid var(--line); padding-top:18px;">
    <div class="section-title">8. Sources et protocole</div>
    <div class="section-note">
      Panels ingérés et validés · Preflight : <code>python3 src/data/phase4_preflight.py</code> ·
      Scripts HPC : <code>hpc/phase4/</code>
    </div>
    <table style="max-width:900px;">
      <thead><tr><th>Panel</th><th>Source</th><th>Fenêtre</th><th>Zones</th><th>Statut</th></tr></thead>
      <tbody>
        <tr>
          <td>Naissances</td>
          <td>{_source_label(country_key, 'births')}</td>
          <td>{stats['births_min_year']}–{stats['births_max_year']}</td>
          <td>{stats['n_zones']}</td>
          <td><span class="badge badge-done">ingéré</span></td>
        </tr>
        <tr>
          <td>Stock</td>
          <td>{_source_label(country_key, 'stock')}</td>
          <td>{stats['stock_min_year']}–{stats['stock_max_year']}</td>
          <td>{stats['n_zones']}</td>
          <td><span class="badge badge-done">ingéré</span></td>
        </tr>
        <tr>
          <td>Tensor ({cfg['tensor_label']})</td>
          <td>{_source_label(country_key, 'tensor')}</td>
          <td>{stats['tensor_min_year']}–{stats['tensor_max_year']}</td>
          <td>{stats['n_zones']}</td>
          <td><span class="badge badge-done">ingéré</span></td>
        </tr>
        <tr>
          <td>Resultats HERALD</td>
          <td>HPC Phase 4 · {hpc_results['run_root'].name if hpc_results else '--'}</td>
          <td>{cfg['window']}</td>
          <td>{stats['n_zones']}</td>
          <td>{"<span class='badge badge-done'>disponibles</span>" if hpc_results else "<span class='badge badge-pend'>en attente</span>"}</td>
        </tr>
      </tbody>
    </table>
  </div>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD {cfg['name']} — Phase 4</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">
  <h1>HERALD {cfg['name']} — Phase 4 Generalisation internationale</h1>
  <div class="subtitle">
    Generalisation internationale de HERALD · {cfg['n_zones']} {cfg['zones_label']} · {cfg['window']}.
    {tensor_badge}
  </div>

  <div class="kpis">
    <div class="kpi">
      <div class="v">{best_wmape_str}</div>
      <div class="l">WMAPE HERALD meilleur</div>
    </div>
    <div class="kpi">
      {gain_str}
      <div class="l">Gain tensor vs baseline</div>
    </div>
    <div class="kpi">
      {vs_str}
      <div class="l">vs France (0.0204)</div>
    </div>
    <div class="kpi">
      {seeds_configs_str}
      <div class="l">Seeds · Configs</div>
    </div>
  </div>

  {pt_tensor_warning}

  {protocole_section}

  <div class="section">
    <div class="section-title">0. Architecture HERALD</div>
    <div class="section-note">
      A partir des donnees publiques sur les creations d'etablissements, HERALD predit combien
      d'entreprises vont etre creees dans chaque territoire l'annee suivante — sans connaitre l'avenir.
      Il apprend comment les territoires s'influencent mutuellement, quelle importance donner a la
      dynamique propre de chaque zone versus l'influence des voisins.
    </div>
    <div class="kpis" style="grid-template-columns:repeat(6,minmax(140px,1fr))">
      <div class="kpi"><div class="v">walk-forward</div><div class="l">Fenêtre d'entraînement</div></div>
      <div class="kpi"><div class="v">{eval_window}</div><div class="l">Annees evaluees</div></div>
      <div class="kpi"><div class="v">{cfg['n_zones']}</div><div class="l">{cfg['zones_label']}</div></div>
      <div class="kpi"><div class="v">9 (A10)</div><div class="l">Secteurs économiques</div></div>
      <div class="kpi"><div class="v">{n_seeds}</div><div class="l">Seeds du protocole</div></div>
      <div class="kpi"><div class="v">2</div><div class="l">Entrées annuelles SIDE</div></div>
    </div>
    <div class="card" style="margin-top:8px">
      {arch_svg}
    </div>
  </div>

  {section1}

  {section2}

  {section3}

  {section4}

  {section5}

  {section6}

  {section7}

  {section8}

</div>

<script>
{births_js}
{stock_js}
{qtensor_js}
{zones_js}
{hpc_js}
{real_pred_js_block}
{sector_js_block}
</script>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[{country_key.upper()}] Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


def _source_label(country_key: str, panel: str) -> str:
    labels = {
        "nl": {
            "births": "CBS 83631NED — oprichtingen vestigingen",
            "stock":  "CBS 81578NED — vestigingen actifs",
            "tensor": "CBS 83582NED — banen werknemers × SBI-A10",
        },
        "be": {
            "births": "Statbel beSTAT — TVA primo-assujettissements",
            "stock":  "Statbel beSTAT — TVA entreprises actives",
            "tensor": "ONSS archives localunit × NACE-BEL Q4",
        },
        "pt": {
            "births": "INE 0009702 — naissances × município",
            "stock":  "INE 0009819 — stock × NUTS3",
            "tensor": "INE 0009703 — naissances × CAE-section × município",
        },
    }
    return labels.get(country_key, {}).get(panel, "—")


DEFAULT_OUTS = {
    "nl": BASE / "reports/dashboards/herald_netherlands_dashboard.html",
    "be": BASE / "reports/dashboards/herald_belgium_dashboard.html",
    "pt": BASE / "reports/dashboards/herald_portugal_dashboard.html",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--country", choices=["nl", "be", "pt", "all"], default="all",
        help="Country to generate dashboard for (default: all)",
    )
    parser.add_argument("--out", default=None, help="Output HTML path (ignored for --country all)")
    args = parser.parse_args()

    targets = list(COUNTRY_CFG.keys()) if args.country == "all" else [args.country]
    for key in targets:
        out = Path(args.out) if args.out and len(targets) == 1 else DEFAULT_OUTS[key]
        build_country_dashboard(key, out)


if __name__ == "__main__":
    main()
