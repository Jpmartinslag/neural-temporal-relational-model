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
        "hpc_glob": "hpc_results/herald_phase4_nl_*",
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
        "hpc_glob": "hpc_results/herald_phase4_be_*",
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
        "hpc_glob": "hpc_results/herald_phase4_pt_*",
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


def _check_hpc_results(cfg: dict) -> bool:
    import glob as globlib
    hits = globlib.glob(str(BASE / cfg["hpc_glob"]))
    return len(hits) > 0


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


def build_country_dashboard(country_key: str, out_path: Path) -> None:
    cfg = {**COUNTRY_CFG[country_key], "key": country_key}
    color = cfg["color"]

    births = _load_births(cfg)
    stock = _load_stock(cfg)
    qtensor = _load_qtensor(cfg)
    stats = _summary_stats(cfg, births, stock, qtensor)

    hpc_ready = _check_hpc_results(cfg)
    tensor_warn = not cfg["q7_equiv"]

    tensor_badge = (
        '<span class="badge badge-warn">⚠️ proxy — não é Q7 effectifs</span>'
        if tensor_warn
        else '<span class="badge badge-done">✅ Q7-equivalent</span>'
    )

    suppressed_note = ""
    if cfg.get("suppressed_flag") and stats["suppressed_pct"] is not None:
        suppressed_note = f'<div class="section-note warn">⚠️ {stats["suppressed_pct"]:.1f}% cellules supprimées CBS (divulgation statistique) — rempli à 0 avec flag <code>jobs_suppressed</code>.</div>'

    pt_tensor_warning = ""
    if tensor_warn:
        pt_tensor_warning = """
<div class="card" style="border-color:#ef535066; margin-bottom:14px;">
  <b style="color:#ef9a9a;">⚠️ Tensor framing critique — Portugal</b><br>
  <span style="color:var(--muted); font-size:13px;">
    Le tensor <code>sector_births_tensor</code> représente des <b>naissances d'entreprises par secteur CAE</b>,
    pas un stock d'emploi (Q7 effectifs). KZ = 0 partout (le secteur financier n'apparaît pas dans les naissances INE).
    Les comparaisons NL/BE↔PT sont qualitatives uniquement. Un vrai Q7-équivalent (GEP Quadros de Pessoal) est
    documenté mais non ingéré — prévu Phase 4B si nécessaire.
  </span>
</div>
"""

    hpc_section = ""
    if hpc_ready:
        hpc_section = f"""
<div class="section">
  <div class="section-title">Résultats HERALD — {cfg['name']}</div>
  <div class="section-note">Résultats HPC disponibles. Lancer avec <code>--run-root</code> pour intégrer les métriques.</div>
  <div class="pending-box">
    <div class="icon">📊</div>
    <div class="msg">Résultats détectés</div>
    <div class="sub">Relancer avec <code>--run-root hpc_results/...</code> pour afficher les métriques et comparaisons.</div>
  </div>
</div>
"""
    else:
        hpc_section = f"""
<div class="section">
  <div class="section-title">Résultats HERALD — {cfg['name']} <span class="badge badge-pend">En attente</span></div>
  <div class="section-note">
    Les batteries HPC Phase 4 n'ont pas encore été lancées pour ce pays.
    Ce dashboard sera mis à jour après réception des résultats.
  </div>
  <div class="pending-box">
    <div class="icon">⏳</div>
    <div class="msg">Résultats HPC en attente</div>
    <div class="sub">
      Lancer la batterie : <code>bash hpc/phase4/submit_herald_phase4_{country_key}.sh</code><br>
      Puis relancer ce script avec <code>--run-root hpc_results/&lt;OUT_ROOT&gt;</code>
    </div>
  </div>
</div>
"""

    births_js = _births_trend_js(cfg, births, color)
    stock_js = _stock_trend_js(cfg, stock, color)
    qtensor_js = _qtensor_heatmap_js(cfg, qtensor)
    zones_js = _top_zones_js(cfg, births, color)
    zones_table = _top_zones_table(cfg, births)

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
  <h1>HERALD {cfg['name']} — Phase 4 Généralisation internationale</h1>
  <div class="subtitle">
    Panels de données {cfg['name']} : naissances d'entreprises, stock actif, tensor sectoriel.
    Fenêtre de modélisation : <b>{cfg['window']}</b> · {cfg['n_zones']} {cfg['zones_label']}.
    {tensor_badge}
  </div>

  <div class="kpis">
    <div class="kpi">
      <div class="v">{stats['n_zones']}</div>
      <div class="l">Zones ({cfg['zones_label']})</div>
    </div>
    <div class="kpi">
      <div class="v">{cfg['window']}</div>
      <div class="l">Fenêtre de modélisation</div>
    </div>
    <div class="kpi">
      <div class="v">{stats['births_min_year']}–{stats['births_max_year']}</div>
      <div class="l">Panel naissances</div>
    </div>
    <div class="kpi">
      <div class="v">{stats['tensor_min_year']}–{stats['tensor_max_year']}</div>
      <div class="l">Panel tensor ({cfg['tensor_label']})</div>
    </div>
  </div>

  {pt_tensor_warning}

  <div class="section">
    <div class="section-title">1. Naissances d'entreprises — {cfg['name']}</div>
    <div class="section-note">
      Évolution agrégée des naissances sur toutes les zones {cfg['zones_label']} ({stats['births_min_year']}–{stats['births_max_year']}).
    </div>
    <div class="grid2">
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Naissances totales (toutes zones)</div>
        <div id="chart_births_{country_key}" style="height:280px;"></div>
      </div>
      <div class="card">
        <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Top 8 zones — évolution temporelle</div>
        <div id="chart_zones_{country_key}" style="height:280px;"></div>
      </div>
    </div>
    <div class="card" style="margin-top:12px;">
      <div style="color:var(--muted); font-size:12px; margin-bottom:8px;">Top 10 zones — naissances cumulées</div>
      {zones_table}
    </div>
  </div>

  <div class="section">
    <div class="section-title">2. Stock d'entreprises actives — {cfg['name']}</div>
    <div class="section-note">
      Stock total actif sur toutes les zones ({stats['stock_min_year']}–{stats['stock_max_year']}).
    </div>
    <div class="card">
      <div id="chart_stock_{country_key}" style="height:280px;"></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">3. Tensor sectoriel — {cfg['tensor_label']}</div>
    <div class="section-note">
      {cfg['tensor_note']}
      · {stats['tensor_rows']} lignes · {stats['n_a10']} secteurs A10 · {stats['tensor_min_year']}–{stats['tensor_max_year']}.
    </div>
    {suppressed_note}
    <div class="card">
      <div style="color:var(--muted); font-size:12px; margin-bottom:6px;">Heatmap — signal agrégé (toutes zones) par secteur × année</div>
      <div id="chart_qtensor_{country_key}" style="height:340px;"></div>
    </div>
  </div>

  {hpc_section}

  <div class="section" style="margin-top:32px; border-top:1px solid var(--line); padding-top:18px;">
    <div class="section-title">Sources et protocole</div>
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
          <td><span class="badge badge-done">✅ ingéré</span></td>
        </tr>
        <tr>
          <td>Stock</td>
          <td>{_source_label(country_key, 'stock')}</td>
          <td>{stats['stock_min_year']}–{stats['stock_max_year']}</td>
          <td>{stats['n_zones']}</td>
          <td><span class="badge badge-done">✅ ingéré</span></td>
        </tr>
        <tr>
          <td>Tensor ({cfg['tensor_label']})</td>
          <td>{_source_label(country_key, 'tensor')}</td>
          <td>{stats['tensor_min_year']}–{stats['tensor_max_year']}</td>
          <td>{stats['n_zones']}</td>
          <td><span class="badge badge-done">✅ ingéré</span></td>
        </tr>
        <tr>
          <td>Résultats HERALD</td>
          <td>HPC Phase 4</td>
          <td>{cfg['window']}</td>
          <td>{stats['n_zones']}</td>
          <td><span class="badge badge-pend">⏳ en attente</span></td>
        </tr>
      </tbody>
    </table>
  </div>

</div>

<script>
{births_js}
{stock_js}
{qtensor_js}
{zones_js}
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
