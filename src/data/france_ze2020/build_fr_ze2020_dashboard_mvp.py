"""
HERALD -- France ZE2020 dashboard MVP.

See reports/canonical/HERALD_22_FR_ZE2020_DASHBOARD_MVP.md. Static, self-contained
HTML (Plotly embedded locally, same technique already used by
src/data/european_panel/build_observatory_v04_dashboard.py -- duplicated here as a
small private helper rather than imported, to keep this France-only MVP decoupled
from the unrelated European Observatory track).

Shows, for a selected ZE2020: the controlled prediction (persistence/ridge,
already-audited baseline -- NEVER claimed superior), a descriptive sectoral
view, and the exploratory relational signals from HERALD_20/21. Block 1
("Arquitetura") is a deliberately EMPTY set of placeholder cards -- no
narrative is invented here; the human fills it in later.

Reads ONLY already-canonical/already-audited inputs:
  data/processed/france_ze2020/fr_ze2020_clean_panel.csv          (observed series)
  data/processed/france_ze2020/fr_ze2020_baseline_predictions_v1.csv (persistence/ridge,
    regenerable -- if missing, the prediction panel shows observed-only and says so,
    it never fabricates a predicted series)
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv          (descriptive sector shares)
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv (dominant
    sector / diversity badges)
  data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv (optional,
    sector_share predicted vs observed -- only shown if the file exists)
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv
  data/external/ze2020_geometry.geojson  (already used by Observatory v0.3/v0.4;
    280/280 join coverage against the canonical panel, verified by this builder's
    own test, not assumed)

Never dynamic_stgnn_feature_panel*, never graph_adjacency_core_v0.csv/
graph_adjacency_mobility_v0.csv, never train_herald_v6/v7/semi_v2/regime_experiment.

Output:
  reports/dashboards/fr_ze2020_dashboard_mvp.html
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
CLEAN_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
BASELINE_PREDICTIONS_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_baseline_predictions_v1.csv"
SECTOR_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
SECTOR_FEATURES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
SECTOR_GRAPH_PREDICTIONS_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv"
)
RELATION_SIGNALS_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv"
RELATION_EXAMPLES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv"
GEOMETRY_PATH = ROOT / "data/external/ze2020_geometry.geojson"

OUT_DIR = ROOT / "reports/dashboards"
OUT_PATH = OUT_DIR / "fr_ze2020_dashboard_mvp.html"

GEOMETRY_NOT_AUDITED_MESSAGE = "Geometria ZE2020 ainda não auditada."
PREDICTION_NOT_FOUND_MESSAGE = "Previsão auditada não encontrada para este grão."
RELATIONAL_CAVEAT = "Sinal exploratório, não causal."
GLOBAL_CAVEAT = "Associações exploratórias, não causalidade e não recomendação automática."

ARCHITECTURE_STEPS = [
    "Dados brutos",
    "Tratamento limpo",
    "Painel causal / model-ready",
    "Camada relacional ZE / setor",
    "Modelo / controle preditivo",
    "Sinais exploratórios",
]

RELATION_FAMILIES = [
    "ze_to_ze_similarity",
    "ze_to_ze_same_sector_signal",
    "intra_ze_sector_interaction",
    "ze_sector_specialization",
]


def _plotly_js_tag() -> tuple[str, str]:
    """Embed Plotly locally if available, else fall back to CDN (documented,
    same technique as build_observatory_v04_dashboard.py -- duplicated as a
    small utility, not imported, to avoid coupling this France-only MVP to
    the unrelated European Observatory module)."""
    try:
        import plotly as _plotly

        js_path = Path(_plotly.__file__).parent / "package_data" / "plotly.min.js"
        if js_path.exists():
            js = js_path.read_text(encoding="utf-8")
            logger.info("Embedding Plotly locally (%d KB)", len(js) // 1024)
            return f"<script>{js}</script>", "local_embedded"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load local Plotly: %s", exc)
    logger.warning("Falling back to Plotly CDN (dashboard will need internet)")
    return '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>', "cdn_fallback"


def load_clean_panel(path: Path = CLEAN_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_geometry(path: Path = GEOMETRY_PATH, panel_codes: set[str] | None = None) -> dict | None:
    """Returns the raw GeoJSON dict, filtered to the canonical 280-zone scope,
    or None if the file is missing or has zero overlap with the panel --
    never fabricates a map. Coverage is logged, not assumed."""
    if not path.exists():
        logger.warning("%s -- %s", GEOMETRY_NOT_AUDITED_MESSAGE, path)
        return None
    with open(path, encoding="utf-8") as f:
        geo = json.load(f)

    geo_codes = {feat["properties"].get("ze2020") for feat in geo["features"]}
    if panel_codes is not None:
        covered = panel_codes & geo_codes
        logger.info("Geometry coverage: %d/%d panel zones covered", len(covered), len(panel_codes))
        if not covered:
            logger.warning("%s -- zero overlap with canonical panel", GEOMETRY_NOT_AUDITED_MESSAGE)
            return None
        geo = dict(geo)
        geo["features"] = [f for f in geo["features"] if f["properties"].get("ze2020") in panel_codes]
    return geo


def load_predictions(path: Path = BASELINE_PREDICTIONS_PATH) -> pd.DataFrame | None:
    if not path.exists():
        logger.warning("%s -- %s", PREDICTION_NOT_FOUND_MESSAGE, path)
        return None
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_panel(path: Path = SECTOR_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_features(path: Path = SECTOR_FEATURES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_graph_predictions(path: Path = SECTOR_GRAPH_PREDICTIONS_PATH) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    df["year"] = df["year"].astype(int)
    return df


def load_relation_signals(path: Path = RELATION_SIGNALS_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"source_id": str, "target_id": str, "sector_code": str})


def load_relation_examples(path: Path = RELATION_EXAMPLES_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"ze2020": str, "related_ze2020": str})


def build_ze_data(
    clean_panel: pd.DataFrame,
    predictions: pd.DataFrame | None,
    sector_panel: pd.DataFrame,
    sector_features: pd.DataFrame,
    sector_graph_predictions: pd.DataFrame | None,
    relation_signals: pd.DataFrame,
    relation_examples: pd.DataFrame,
) -> dict:
    """One dict per ze2020, embedded client-side -- the dashboard never
    queries a server, every panel is a lookup into this structure."""
    zones = sorted(clean_panel["ze2020"].unique())
    labels = clean_panel[["ze2020", "ze2020_label"]].drop_duplicates().set_index("ze2020")["ze2020_label"]

    ze_data: dict[str, dict] = {}
    for ze in zones:
        series = clean_panel[clean_panel["ze2020"] == ze].sort_values("year")
        observed = {int(r.year): float(r.establishment_creations) for r in series.itertuples()}

        pred_by_model: dict[str, dict[int, float]] = {}
        if predictions is not None:
            ze_pred = predictions[predictions["ze2020"] == ze]
            for model_name, group in ze_pred.groupby("model"):
                pred_by_model[model_name] = {int(r.year): float(r.y_pred) for r in group.itertuples()}

        sector_rows = sector_panel[sector_panel["ze2020"] == ze]
        sector_by_year: dict[int, dict[str, float]] = {}
        for year, group in sector_rows.groupby("year"):
            sector_by_year[int(year)] = dict(zip(group["sector_code"], group["sector_share"]))

        feat_rows = sector_features[sector_features["ze2020"] == ze].drop_duplicates(subset=["year"])
        feat_rows = feat_rows.sort_values("year")
        dominant_sector_latest = None
        diversity_latest = None
        if not feat_rows.empty:
            last = feat_rows.iloc[-1]
            if pd.notna(last.get("dominant_sector_lag_1")):
                dominant_sector_latest = last["dominant_sector_lag_1"]
            if pd.notna(last.get("sector_diversity_lag_1")):
                diversity_latest = float(last["sector_diversity_lag_1"])

        sector_pred_compare: list[dict] = []
        if sector_graph_predictions is not None:
            ze_sg = sector_graph_predictions[sector_graph_predictions["ze2020"] == ze]
            for r in ze_sg.itertuples():
                sector_pred_compare.append(
                    {
                        "year": int(r.year),
                        "sector_code": r.sector_code,
                        "model": r.model,
                        "y_true": float(r.y_true),
                        "y_pred": float(r.y_pred),
                        "claim_status": r.claim_status,
                    }
                )

        relations: list[dict] = []
        ze_signals = relation_signals[(relation_signals["source_id"] == ze) & (relation_signals["source_type"] == "ZE2020")]
        for r in ze_signals.itertuples():
            relations.append(
                {
                    "relation_family": r.relation_family,
                    "target_id": r.target_id,
                    "target_label": r.target_label,
                    "sector_code": r.sector_code if pd.notna(r.sector_code) else "",
                    "sector_label": r.sector_label if pd.notna(r.sector_label) else "",
                    "signal_strength": float(r.signal_strength),
                    "stability_score": float(r.stability_score),
                    "interpretation_label": r.interpretation_label,
                }
            )

        examples = relation_examples[relation_examples["ze2020"] == ze]
        example_texts = examples["plain_language_interpretation"].tolist()

        ze_data[ze] = {
            "label": labels.get(ze, ""),
            "observed": observed,
            "predictions": pred_by_model,
            "sector_by_year": sector_by_year,
            "dominant_sector": dominant_sector_latest,
            "diversity": diversity_latest,
            "sector_pred_compare": sector_pred_compare,
            "relations": relations,
            "examples": example_texts,
        }
    return ze_data


def build_map_metrics(ze_data: dict, relation_signals: pd.DataFrame) -> dict:
    """Precomputed z-values for each map color-by option, keyed exactly like
    ze_data -- the map never recomputes anything client-side."""
    observed_latest: dict[str, float] = {}
    error_latest: dict[str, float] = {}
    dominant_sector: dict[str, str] = {}
    stability_avg: dict[str, float] = {}

    similarity = relation_signals[relation_signals["relation_family"] == "ze_to_ze_similarity"]
    stability_by_ze = similarity.groupby("source_id")["stability_score"].mean()

    for ze, data in ze_data.items():
        if data["observed"]:
            latest_year = max(data["observed"].keys())
            observed_latest[ze] = data["observed"][latest_year]
            if "ridge" in data["predictions"] and latest_year in data["predictions"]["ridge"]:
                error_latest[ze] = abs(data["observed"][latest_year] - data["predictions"]["ridge"][latest_year])
        dominant_sector[ze] = data["dominant_sector"] or ""
        if ze in stability_by_ze.index:
            stability_avg[ze] = float(stability_by_ze[ze])

    return {
        "observed_latest": observed_latest,
        "error_latest": error_latest,
        "dominant_sector": dominant_sector,
        "stability_avg": stability_avg,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>HERALD -- France ZE2020 (MVP exploratorio)</title>
{plotly_tag}
<style>
  body {{ font-family: -apple-system, Arial, sans-serif; margin: 0; padding: 0; background: #f7f7f8; color: #222; }}
  header {{ background: #1c2733; color: #fff; padding: 16px 24px; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .subtitle {{ font-size: 13px; color: #c7d0d8; margin-top: 4px; }}
  header .caveat {{ font-size: 12px; color: #ffcf66; margin-top: 6px; }}
  .section {{ background: #fff; margin: 16px; padding: 16px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .section h2 {{ font-size: 15px; margin: 0 0 10px 0; color: #1c2733; }}
  .caveat-line {{ font-size: 11px; color: #8a5a00; background: #fff6e5; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-bottom: 8px; }}
  .arch-row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .arch-card {{ flex: 1; min-width: 140px; border: 1px dashed #aab; border-radius: 6px; padding: 10px; text-align: center; color: #667; background: #fafbfc; }}
  .arch-card .step-no {{ font-size: 11px; color: #99a; }}
  .arch-card .step-title {{ font-size: 13px; font-weight: 600; margin-top: 4px; }}
  .arch-card .step-placeholder {{ font-size: 11px; color: #aab; margin-top: 6px; }}
  .controls {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }}
  .controls label {{ font-size: 12px; color: #556; margin-right: 4px; }}
  select {{ padding: 4px 6px; font-size: 12px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  table.rel-table {{ width: 100%; font-size: 12px; border-collapse: collapse; }}
  table.rel-table th, table.rel-table td {{ padding: 4px 6px; border-bottom: 1px solid #eee; text-align: left; }}
  .example-box {{ font-size: 12px; background: #f0f4ff; border-left: 3px solid #6677ee; padding: 8px; margin-top: 6px; }}
  .badge {{ display: inline-block; background: #eef; border-radius: 10px; padding: 2px 8px; font-size: 11px; margin-right: 6px; }}
  .geometry-blocked {{ padding: 40px; text-align: center; color: #c0392b; background: #fdf2f0; border-radius: 6px; }}
  footer {{ text-align: center; font-size: 11px; color: #999; padding: 20px; }}
</style>
</head>
<body>

<header>
  <h1>HERALD -- Franca ZE2020 (MVP exploratorio)</h1>
  <div class="subtitle">Previsao controlada e sinais relacionais exploratorios por ZE2020</div>
  <div class="caveat">{global_caveat}</div>
</header>

<div class="section">
  <h2>Arquitetura do pipeline</h2>
  <div class="arch-row">
    {architecture_cards}
  </div>
</div>

<div class="section">
  <h2>Selecao de ZE2020</h2>
  <div class="controls">
    <label>ZE2020:</label>
    <select id="ze-select" onchange="selectZone(this.value)"></select>
    <label>Cor do mapa:</label>
    <select id="map-metric-select" onchange="renderMap()">
      <option value="observed_latest">Valor observado (ultimo ano)</option>
      <option value="error_latest">Erro |observado - ridge| (ultimo ano com previsao)</option>
      <option value="dominant_sector">Setor dominante</option>
      <option value="stability_avg">Estabilidade relacional media (ze_to_ze_similarity)</option>
    </select>
  </div>
  <div id="map-container"></div>
</div>

<div class="section">
  <h2>Previsao global (controle) -- ZE selecionada</h2>
  <div class="caveat-line">Previsao e controle, nao objetivo principal desta etapa. Sem claim de previsao superior.</div>
  <div id="prediction-chart"></div>
</div>

<div class="grid2">
  <div class="section">
    <h2>Visao setorial</h2>
    <div id="sector-info"></div>
    <div id="sector-chart"></div>
    <div id="sector-pred-compare"></div>
  </div>

  <div class="section">
    <h2>Relacoes exploratorias</h2>
    <div class="caveat-line">{relational_caveat}</div>
    <div class="controls">
      <label>Familia:</label>
      <select id="family-select" onchange="renderRelations()">
        <option value="all">Todas</option>
        <option value="ze_to_ze_similarity">ze_to_ze_similarity</option>
        <option value="ze_to_ze_same_sector_signal">ze_to_ze_same_sector_signal</option>
        <option value="intra_ze_sector_interaction">intra_ze_sector_interaction</option>
        <option value="ze_sector_specialization">ze_sector_specialization</option>
      </select>
    </div>
    <div id="relation-graph"></div>
    <div id="relation-tables"></div>
    <div id="relation-examples"></div>
  </div>
</div>

<footer>
  HERALD -- France ZE2020 MVP exploratorio. {plotly_dep_note}
  Ver reports/canonical/HERALD_22_FR_ZE2020_DASHBOARD_MVP.md.
</footer>

<script>
const ZE_DATA = {ze_data_json};
const MAP_METRICS = {map_metrics_json};
const GEOMETRY = {geometry_json};
const ZONES = {zones_json};
let selectedZe = ZONES[0];

function populateZeSelect() {{
  const sel = document.getElementById('ze-select');
  ZONES.forEach(function(ze) {{
    const opt = document.createElement('option');
    opt.value = ze;
    opt.textContent = ze + ' -- ' + (ZE_DATA[ze].label || '');
    sel.appendChild(opt);
  }});
  sel.value = selectedZe;
}}

function renderMap() {{
  const metricKey = document.getElementById('map-metric-select').value;
  const metric = MAP_METRICS[metricKey];
  if (!GEOMETRY) {{
    document.getElementById('map-container').innerHTML =
      '<div class="geometry-blocked">{geometry_blocked_message}</div>';
    return;
  }}
  const locations = ZONES;
  let z, colorscale, showscale;
  if (metricKey === 'dominant_sector') {{
    const sectors = Array.from(new Set(Object.values(metric))).sort();
    const sectorIndex = {{}};
    sectors.forEach(function(s, i) {{ sectorIndex[s] = i; }});
    z = locations.map(function(ze) {{ return sectorIndex[metric[ze] || '']; }});
    colorscale = 'Portland';
    showscale = false;
  }} else {{
    z = locations.map(function(ze) {{ return (metric[ze] === undefined) ? null : metric[ze]; }});
    colorscale = metricKey === 'error_latest' ? 'Reds' : 'Blues';
    showscale = true;
  }}
  const data = [{{
    type: 'choropleth',
    geojson: GEOMETRY,
    locations: locations,
    z: z,
    featureidkey: 'properties.ze2020',
    colorscale: colorscale,
    showscale: showscale,
    marker: {{ line: {{ width: 0.4, color: '#888' }} }}
  }}];
  const layout = {{
    geo: {{ fitbounds: 'geojson', visible: false }},
    margin: {{ t: 10, b: 10, l: 10, r: 10 }},
    height: 420
  }};
  Plotly.newPlot('map-container', data, layout, {{displayModeBar: false}});
  document.getElementById('map-container').on('plotly_click', function(ev) {{
    const ze = ev.points[0].location;
    selectZone(ze);
  }});
}}

function selectZone(ze) {{
  selectedZe = ze;
  document.getElementById('ze-select').value = ze;
  renderPrediction();
  renderSector();
  renderRelations();
}}

function renderPrediction() {{
  const d = ZE_DATA[selectedZe];
  const years = Object.keys(d.observed).map(Number).sort();
  const observedVals = years.map(function(y) {{ return d.observed[y]; }});
  const traces = [{{ x: years, y: observedVals, mode: 'lines+markers', name: 'Observado', line: {{color:'#222'}} }}];
  let hasPrediction = false;
  Object.keys(d.predictions).forEach(function(model) {{
    const predYears = Object.keys(d.predictions[model]).map(Number).sort();
    if (predYears.length > 0) {{
      hasPrediction = true;
      traces.push({{
        x: predYears,
        y: predYears.map(function(y) {{ return d.predictions[model][y]; }}),
        mode: 'markers',
        name: 'Previsto (' + model + ')'
      }});
    }}
  }});
  const layout = {{ margin: {{t:20,b:30,l:40,r:10}}, height: 280, legend: {{orientation:'h'}} }};
  Plotly.newPlot('prediction-chart', traces, layout, {{displayModeBar: false}});
  if (!hasPrediction) {{
    document.getElementById('prediction-chart').insertAdjacentHTML('beforeend',
      '<div class="caveat-line">{prediction_not_found_message}</div>');
  }}
}}

function renderSector() {{
  const d = ZE_DATA[selectedZe];
  const info = document.getElementById('sector-info');
  info.innerHTML =
    (d.dominant_sector ? '<span class="badge">Setor dominante: ' + d.dominant_sector + '</span>' : '') +
    (d.diversity !== null ? '<span class="badge">Diversidade: ' + d.diversity.toFixed(2) + '</span>' : '');

  const years = Object.keys(d.sector_by_year).map(Number).sort();
  const sectors = Array.from(new Set(years.flatMap(function(y) {{ return Object.keys(d.sector_by_year[y]); }}))).sort();
  const traces = sectors.map(function(s) {{
    return {{
      x: years,
      y: years.map(function(y) {{ return d.sector_by_year[y][s] || 0; }}),
      name: s,
      type: 'bar'
    }};
  }});
  const layout = {{ barmode: 'stack', margin: {{t:20,b:30,l:40,r:10}}, height: 260, legend: {{orientation:'h', font:{{size:9}}}} }};
  Plotly.newPlot('sector-chart', traces, layout, {{displayModeBar: false}});

  const cmp = document.getElementById('sector-pred-compare');
  if (d.sector_pred_compare.length === 0) {{
    cmp.innerHTML = '<div class="caveat-line">{prediction_not_found_message}</div>';
  }} else {{
    let rows = d.sector_pred_compare.slice(0, 9).map(function(r) {{
      return '<tr><td>' + r.year + '</td><td>' + r.sector_code + '</td><td>' + r.model +
        '</td><td>' + r.y_true.toFixed(3) + '</td><td>' + r.y_pred.toFixed(3) + '</td></tr>';
    }}).join('');
    cmp.innerHTML = '<div class="caveat-line">sector_graph_smoke -- nao bateu baseline (HERALD_19)</div>' +
      '<table class="rel-table"><tr><th>Ano</th><th>Setor</th><th>Modelo</th><th>Real</th><th>Previsto</th></tr>' + rows + '</table>';
  }}
}}

function renderRelations() {{
  const d = ZE_DATA[selectedZe];
  const family = document.getElementById('family-select').value;
  let rels = d.relations;
  if (family !== 'all') {{ rels = rels.filter(function(r) {{ return r.relation_family === family; }}); }}

  const top = rels.slice().sort(function(a,b) {{ return b.signal_strength - a.signal_strength; }}).slice(0, 8);
  const angleStep = (2 * Math.PI) / Math.max(top.length, 1);
  const xs = [0], ys = [0], texts = [selectedZe];
  const edgeTraces = [];
  top.forEach(function(r, i) {{
    const angle = i * angleStep;
    const x = Math.cos(angle), y = Math.sin(angle);
    xs.push(x); ys.push(y); texts.push(r.target_id);
    edgeTraces.push({{
      x: [0, x], y: [0, y], mode: 'lines',
      line: {{ width: Math.max(1, r.signal_strength * 6), color: 'rgba(80,100,200,' + Math.max(0.15, r.stability_score) + ')' }},
      showlegend: false, hoverinfo: 'skip'
    }});
  }});
  const nodeTrace = {{ x: xs, y: ys, mode: 'markers+text', text: texts, textposition: 'top center',
    marker: {{ size: [18].concat(top.map(function() {{ return 10; }})), color: ['#222'].concat(top.map(function() {{ return '#5566cc'; }})) }} }};
  const layout = {{ margin: {{t:10,b:10,l:10,r:10}}, height: 240, xaxis: {{visible:false}}, yaxis: {{visible:false}}, showlegend: false }};
  Plotly.newPlot('relation-graph', edgeTraces.concat([nodeTrace]), layout, {{displayModeBar: false}});

  const byStability = rels.slice().sort(function(a,b) {{ return b.stability_score - a.stability_score; }}).slice(0,5);
  const byStrength = rels.slice().sort(function(a,b) {{ return b.signal_strength - a.signal_strength; }}).slice(0,5);
  function tableHtml(title, list) {{
    let rows = list.map(function(r) {{
      return '<tr><td>' + r.target_id + ' (' + (r.target_label||'') + ')</td><td>' + r.relation_family +
        '</td><td>' + r.signal_strength.toFixed(3) + '</td><td>' + r.stability_score.toFixed(2) + '</td></tr>';
    }}).join('');
    return '<b>' + title + '</b><table class="rel-table"><tr><th>Relacionado</th><th>Familia</th><th>Sinal</th><th>Estabilidade</th></tr>' + rows + '</table>';
  }}
  document.getElementById('relation-tables').innerHTML =
    tableHtml('Top por estabilidade', byStability) + tableHtml('Top por signal_strength', byStrength);

  const ex = document.getElementById('relation-examples');
  if (d.examples.length === 0) {{
    ex.innerHTML = '';
  }} else {{
    ex.innerHTML = d.examples.map(function(t) {{ return '<div class="example-box">' + t + '</div>'; }}).join('');
  }}
}}

populateZeSelect();
renderMap();
selectZone(selectedZe);
</script>

</body>
</html>
"""


def render_dashboard(
    ze_data: dict,
    map_metrics: dict,
    geometry: dict | None,
) -> str:
    architecture_cards = "\n".join(
        f'<div class="arch-card"><div class="step-no">Etapa {i + 1}</div>'
        f'<div class="step-title">{step}</div>'
        f'<div class="step-placeholder">[conteudo a definir]</div></div>'
        for i, step in enumerate(ARCHITECTURE_STEPS)
    )

    plotly_tag, plotly_dep = _plotly_js_tag()
    plotly_dep_note = (
        "Plotly embarcado localmente, funciona offline."
        if plotly_dep == "local_embedded"
        else "Plotly via CDN, requer internet."
    )

    zones = sorted(ze_data.keys())

    return HTML_TEMPLATE.format(
        plotly_tag=plotly_tag,
        plotly_dep_note=plotly_dep_note,
        global_caveat=GLOBAL_CAVEAT,
        relational_caveat=RELATIONAL_CAVEAT,
        geometry_blocked_message=GEOMETRY_NOT_AUDITED_MESSAGE,
        prediction_not_found_message=PREDICTION_NOT_FOUND_MESSAGE,
        architecture_cards=architecture_cards,
        ze_data_json=json.dumps(ze_data),
        map_metrics_json=json.dumps(map_metrics),
        geometry_json=json.dumps(geometry) if geometry is not None else "null",
        zones_json=json.dumps(zones),
    )


def build_dashboard() -> str:
    clean_panel = load_clean_panel()
    panel_codes = set(clean_panel["ze2020"].unique())

    predictions = load_predictions()
    sector_panel = load_sector_panel()
    sector_features = load_sector_features()
    sector_graph_predictions = load_sector_graph_predictions()
    relation_signals = load_relation_signals()
    relation_examples = load_relation_examples()
    geometry = load_geometry(panel_codes=panel_codes)

    ze_data = build_ze_data(
        clean_panel,
        predictions,
        sector_panel,
        sector_features,
        sector_graph_predictions,
        relation_signals,
        relation_examples,
    )
    map_metrics = build_map_metrics(ze_data, relation_signals)

    return render_dashboard(ze_data, map_metrics, geometry)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = build_dashboard()
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Saved: {OUT_PATH} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
