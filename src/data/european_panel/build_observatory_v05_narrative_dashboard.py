"""
Build the HERALD Observatory v0.5 — layperson-friendly narrative dashboard.

Reads the standardized presentation-layer exports produced by
`build_observatory_v05_narrative_exports.py` (data/processed/
herald_observatory_v05_narrative/) plus the same geometry sources used by
v0.4 (FR ZE2020, NL COROP, PT Municipality), and emits a single
self-contained HTML file.

This builder does NOT recompute any scientific number. It only re-shapes
already-validated exports into a plain-language, map-first UI. v0.4
(`build_observatory_v04_dashboard.py` / `herald_observatory_v04_granular_dashboard.html`)
is untouched.

Hard rules (must not be violated by this builder):
  - NL gemeente proxy NEVER enters the main sector graph dataset embedded
    in this dashboard (RELATION_EDGES). It may appear on the map/context
    layer with a visible "Proxy / context" badge.
  - blocked_proxy_edges (121 rows) render only in a separate technical
    panel, never as graph edges, never framed as a "discovery".
  - No raw "NaN" string anywhere in rendered text/labels.
  - PT KZ is shown as "Sector not available for Portugal" (structural
    absence), never a bare missing-data cell, and the KZ option is
    disabled in the sector selector when country=PT.
  - No causal language in the main narrative; the single permitted
    technical footnote uses "indicates predictive precedence, not
    structural causal proof".
  - No ML jargon (GNN/attention/encoder/loss/AUC) in the main UI layer;
    such terms only appear inside the collapsible "Technical details"
    panel.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
V05_DIR = REPO_ROOT / "data/processed/herald_observatory_v05_narrative"
V04_DIR = REPO_ROOT / "data/processed/herald_observatory_v04_granular"

TERRITORY_VIEW_PATH = V05_DIR / "territory_view.csv"
SECTOR_VIEW_PATH = V05_DIR / "sector_view.csv"
RELATION_VIEW_PATH = V05_DIR / "relation_view.csv"
PREDICTION_VIEW_PATH = V05_DIR / "prediction_view.csv"
MAP_STATE_PATH = V05_DIR / "map_state_by_year_sector.json"
RELATION_TIMELINE_PATH = V05_DIR / "relation_timeline.json"
BLOCKED_PATH = V05_DIR / "blocked_proxy_edges_v04_copy.csv"
V05_MANIFEST_PATH = V05_DIR / "manifest.json"

ZE_GEOJSON_PATH = REPO_ROOT / "data/external/ze2020_geometry.geojson"
NUTS3_GEOJSON_PATH = REPO_ROOT / "data/external/nuts3_2021_eurostat.geojson"
PT_GEOJSON_PATH = REPO_ROOT / "data/processed/geometries/pt_municipalities_continental.geojson"
PT_GEOJSON_MANIFEST_PATH = REPO_ROOT / "data/processed/geometries/pt_municipalities_continental_manifest.json"

OUT_PATH = REPO_ROOT / "reports/dashboards/herald_observatory_v05_narrative_dashboard.html"

SECTOR_LABELS = {
    "BE": "Industry and energy",
    "FZ": "Construction",
    "GI": "Trade, transport and hospitality",
    "JZ": "Information and communication",
    "KZ": "Financial and insurance activities",
    "LZ": "Real estate activities",
    "MN": "Professional and administrative services",
    "OQ": "Public administration, education and health",
    "RU": "Arts and other services",
}
SECTORS_ORDER = list(SECTOR_LABELS.keys())

NL_COROP_TO_NUTS3: dict[str, str] = {
    "CR01": "NL111", "CR02": "NL112", "CR03": "NL113",
    "CR04": "NL124", "CR05": "NL125", "CR06": "NL126",
    "CR07": "NL131", "CR08": "NL132", "CR09": "NL133",
    "CR10": "NL211", "CR11": "NL212", "CR12": "NL213",
    "CR13": "NL221", "CR14": "NL225", "CR15": "NL226",
    "CR16": "NL224", "CR17": "NL310", "CR18": "NL321",
    "CR19": "NL328", "CR20": "NL323", "CR21": "NL324",
    "CR22": "NL325", "CR23": "NL329", "CR24": "NL327",
    "CR25": "NL337", "CR26": "NL332", "CR27": "NL333",
    "CR28": "NL33B", "CR29": "NL33C", "CR30": "NL33A",
    "CR31": "NL341", "CR32": "NL342", "CR33": "NL411",
    "CR34": "NL412", "CR35": "NL413", "CR36": "NL414",
    "CR37": "NL421", "CR38": "NL422", "CR39": "NL423",
    "CR40": "NL230",
}

MAP_CONFIG = {
    "FR": {"region_system": "ZE2020", "label": "France"},
    "NL": {"region_system": "COROP", "label": "Netherlands"},
    "PT": {"region_system": "MUNICIPALITY", "label": "Portugal"},
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _plotly_js_tag() -> tuple[str, str]:
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


GSAP_TAG = (
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>'
)


def _build_fr_geojson(fr_region_ids: list[str]) -> dict:
    raw = json.loads(ZE_GEOJSON_PATH.read_text(encoding="utf-8"))
    panel_set = {str(int(rid)).zfill(4): rid for rid in fr_region_ids}
    features = []
    for feat in raw["features"]:
        ze_code = feat["properties"]["ze2020"]
        if ze_code in panel_set:
            f2 = dict(feat)
            f2["properties"] = dict(feat["properties"])
            f2["properties"]["panel_id"] = panel_set[ze_code]
            f2["properties"]["territory_name"] = feat["properties"]["libze2020"]
            features.append(f2)
    return {"type": "FeatureCollection", "features": features}


def _build_nl_geojson() -> dict:
    raw = json.loads(NUTS3_GEOJSON_PATH.read_text(encoding="utf-8"))
    nuts3_by_code = {
        f["properties"]["NUTS_ID"]: f
        for f in raw["features"]
        if f["properties"]["NUTS_ID"].startswith("NL") and f["properties"]["LEVL_CODE"] == 3
    }
    nuts3_to_panel = {v: k for k, v in NL_COROP_TO_NUTS3.items()}
    features = []
    for nuts_code, panel_id in nuts3_to_panel.items():
        if nuts_code not in nuts3_by_code:
            continue
        feat = nuts3_by_code[nuts_code]
        f2 = dict(feat)
        f2["properties"] = dict(feat["properties"])
        f2["properties"]["panel_id"] = panel_id
        features.append(f2)
    return {"type": "FeatureCollection", "features": features}


def _build_pt_geojson() -> dict:
    if not PT_GEOJSON_PATH.exists():
        logger.warning("PT geojson not found — PT will fall back to table view")
        return {"type": "FeatureCollection", "features": []}
    if PT_GEOJSON_MANIFEST_PATH.exists():
        pt_manifest = json.loads(PT_GEOJSON_MANIFEST_PATH.read_text())
        if pt_manifest.get("status") != "COMPLETE_278_278":
            logger.warning("PT geojson manifest not COMPLETE_278_278 — table fallback")
            return {"type": "FeatureCollection", "features": []}
    raw = json.loads(PT_GEOJSON_PATH.read_text(encoding="utf-8"))
    return raw


def build_node_positions() -> dict:
    node_pos = {}
    for i, s in enumerate(SECTORS_ORDER):
        angle = 2 * math.pi * i / len(SECTORS_ORDER) - math.pi / 2
        node_pos[s] = {"x": round(math.cos(angle), 4), "y": round(math.sin(angle), 4)}
    return node_pos


def build_region_meta(territory_view: pd.DataFrame) -> dict:
    """{country: {region_id: {name, region_system, evidence_badge, is_proxy_context}}}"""
    out: dict = {}
    for (country, region_id), grp in territory_view.groupby(["country", "region_id"], sort=False):
        region_id = str(region_id)
        first = grp.iloc[0]
        out.setdefault(country, {})
        out[country][region_id] = {
            "name": str(first["region_name"]),
            "region_system": first["region_system"],
            "evidence_badge": first["evidence_badge"],
            "is_proxy_context": bool(first["is_proxy_context"]),
        }
    return out


def build_prediction_lookup(prediction_view: pd.DataFrame) -> dict:
    """{country: {region_id: {sector: {year: [observed, expected, difference, trend_state]}}}}
    Nested lookup (same shape family as MAP_STATE) so the dashboard does not
    need to ship one JSON record per row — much smaller than a flat list of
    dicts with repeated string keys."""
    out: dict = {}
    df = prediction_view[prediction_view["available"]]
    for (country, region_id), grp in df.groupby(["country", "region_id"], sort=False):
        region_id = str(region_id)
        out.setdefault(country, {})
        out[country].setdefault(region_id, {})
        for sector, grp_s in grp.groupby("sector_a10", sort=False):
            out[country][region_id].setdefault(sector, {})
            for _, row in grp_s.iterrows():
                out[country][region_id][sector][int(row["year"])] = [
                    None if pd.isna(row["observed_value"]) else round(float(row["observed_value"]), 2),
                    None if pd.isna(row["expected_value"]) else round(float(row["expected_value"]), 2),
                    None if pd.isna(row["difference"]) else round(float(row["difference"]), 2),
                    row["trend_state"],
                ]
    return out


def main() -> None:
    territory_view = pd.read_csv(TERRITORY_VIEW_PATH, low_memory=False)
    sector_view = pd.read_csv(SECTOR_VIEW_PATH, low_memory=False)
    relation_view = pd.read_csv(RELATION_VIEW_PATH, low_memory=False)
    prediction_view = pd.read_csv(PREDICTION_VIEW_PATH, low_memory=False)
    map_state = json.loads(MAP_STATE_PATH.read_text())
    relation_timeline = json.loads(RELATION_TIMELINE_PATH.read_text())
    blocked_edges = pd.read_csv(BLOCKED_PATH, low_memory=False)
    v05_manifest = json.loads(V05_MANIFEST_PATH.read_text())

    # Fail-closed invariants — re-asserted at the dashboard build step too,
    # so a future change to the exports cannot silently leak proxy data
    # into the rendered graph without breaking this build.
    assert "GEMEENTE_PROXY" not in relation_view["region_system"].values, \
        "FAIL_CLOSED: NL gemeente proxy must never appear in the main relation graph"
    assert (blocked_edges["allowed_for_training_label"] == False).all()

    region_meta = build_region_meta(territory_view)
    prediction_lookup = build_prediction_lookup(prediction_view)
    node_pos = build_node_positions()

    fr_ids = sorted(territory_view[territory_view["country"] == "FR"]["region_id"].astype(str).unique())
    geo_fr = _build_fr_geojson(fr_ids)
    geo_nl = _build_nl_geojson()
    geo_pt = _build_pt_geojson()
    pt_map_status = "MAP" if len(geo_pt["features"]) == 278 else "TABLE_FALLBACK"

    plotly_tag, plotly_dep = _plotly_js_tag()

    n_territories = territory_view.groupby("country")["region_id"].nunique().to_dict()
    n_valid_relations = len(relation_view)
    n_blocked_relations = len(blocked_edges)
    n_sectors_tracked = territory_view["sector_a10"].nunique()
    pt_kz_structural_absent = bool(v05_manifest["rules"]["pt_kz_structural_absent"])
    prediction_countries = v05_manifest["rules"]["prediction_layer_countries"]

    relation_edges_js = relation_view.to_dict(orient="records")
    blocked_edges_js = blocked_edges.to_dict(orient="records")
    sector_view_js = sector_view.to_dict(orient="records")

    csv_checksums = {
        "territory_view.csv": _sha256_file(TERRITORY_VIEW_PATH)[:16],
        "relation_view.csv": _sha256_file(RELATION_VIEW_PATH)[:16],
        "sector_view.csv": _sha256_file(SECTOR_VIEW_PATH)[:16],
        "prediction_view.csv": _sha256_file(PREDICTION_VIEW_PATH)[:16],
        "blocked_proxy_edges_v04_copy.csv": _sha256_file(BLOCKED_PATH)[:16],
    }

    html = _render_html(
        plotly_tag=plotly_tag, plotly_dep=plotly_dep,
        region_meta_js=json.dumps(region_meta, separators=(",", ":")),
        prediction_lookup_js=json.dumps(prediction_lookup, separators=(",", ":")),
        map_state_js=json.dumps(map_state, separators=(",", ":")),
        node_pos_js=json.dumps(node_pos),
        sector_labels_js=json.dumps(SECTOR_LABELS),
        geo_fr_js=json.dumps(geo_fr, separators=(",", ":")),
        geo_nl_js=json.dumps(geo_nl, separators=(",", ":")),
        geo_pt_js=json.dumps(geo_pt, separators=(",", ":")),
        relation_edges_js=json.dumps(relation_edges_js),
        relation_timeline_js=json.dumps(relation_timeline),
        blocked_edges_js=json.dumps(blocked_edges_js),
        sector_view_js=json.dumps(sector_view_js),
        manifest_js=json.dumps(v05_manifest),
        map_config_js=json.dumps(MAP_CONFIG),
        csv_checksums_js=json.dumps(csv_checksums),
        n_territories_js=json.dumps(n_territories),
        n_valid_relations=n_valid_relations,
        n_blocked_relations=n_blocked_relations,
        n_sectors_tracked=n_sectors_tracked,
        pt_kz_structural_absent=json.dumps(pt_kz_structural_absent),
        prediction_countries_js=json.dumps(prediction_countries),
        pt_map_status=pt_map_status,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(OUT_PATH, html)
    size_mb = OUT_PATH.stat().st_size / 1e6
    logger.info("Wrote %s (%.2f MB)", OUT_PATH, size_mb)


def _render_html(**kw) -> str:
    plotly_tag = kw["plotly_tag"]
    sector_options_html = "".join(
        f'<option value="{s}">{SECTOR_LABELS[s]} ({s})</option>' for s in SECTORS_ORDER
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD Observatory — Territories and Sectors Over Time</title>
{plotly_tag}
{GSAP_TAG}
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --good:#26a69a; --bad:#ef5350;
    --stag:#9aa4bf; --pos:#26a69a; --neg:#ef5350;
    --robust:#4aa3ff; --supported:#4aa3ff; --exploratory:#ffd180;
    --observed:#26a69a; --proxy:#b39ddb; --blocked:#5a5f78;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;font-size:14px;}}
  .wrap{{max-width:1600px;margin:0 auto;padding:20px;}}
  h1{{font-size:26px;font-weight:760;margin-bottom:6px;}}
  h2{{font-size:18px;font-weight:740;}}
  .subtitle{{color:var(--muted);font-size:14px;line-height:1.55;max-width:1000px;margin-bottom:14px;}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin:0 0 18px;}}
  .kpi{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;}}
  .kpi .v{{font-size:22px;font-weight:760;}}
  .kpi .l{{color:var(--muted);font-size:12px;margin-top:2px;}}
  .section{{margin-top:30px;}}
  .section-title{{font-size:19px;font-weight:730;margin-bottom:6px;}}
  .section-note{{color:var(--muted);font-size:13px;line-height:1.5;max-width:1000px;margin-bottom:10px;}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;}}
  .controls{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px;}}
  select,button,input{{background:var(--panel2);color:var(--text);border:1px solid var(--line);
    border-radius:6px;padding:7px 11px;font-size:13px;cursor:pointer;}}
  button.primary{{background:var(--robust);border-color:var(--robust);color:#0f1220;font-weight:700;}}
  .map-layout{{display:grid;grid-template-columns:1fr 380px;gap:14px;align-items:start;}}
  .side-panel{{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:16px;}}
  .side-panel h3{{font-size:15px;font-weight:730;margin-bottom:10px;}}
  .side-field{{display:flex;justify-content:space-between;margin-bottom:7px;font-size:13px;gap:10px;}}
  .side-field .lbl{{color:var(--muted);flex-shrink:0;}}
  .side-empty{{color:var(--muted);font-size:13px;padding:20px 0;text-align:center;}}
  .badge{{display:inline-block;border-radius:999px;padding:3px 10px;font-size:11.5px;font-weight:700;border:1px solid;}}
  .badge-observed{{color:var(--observed);border-color:var(--observed);background:#0a1e1a;}}
  .badge-proxy{{color:var(--proxy);border-color:var(--proxy);background:#1c1530;}}
  .badge-robust{{color:var(--robust);border-color:var(--robust);background:#0a1a2e;}}
  .badge-supported{{color:var(--supported);border-color:var(--supported);background:#0a1a2e;}}
  .badge-exploratory{{color:var(--exploratory);border-color:var(--exploratory);background:#1e1a0a;}}
  .badge-blocked{{color:var(--blocked);border-color:var(--blocked);background:#1a1a22;}}
  .badge-pos{{color:var(--pos);border-color:var(--pos);background:#0a1e1a;}}
  .badge-neg{{color:var(--neg);border-color:var(--neg);background:#1e0a0a;}}
  .badge-absent{{color:#8a8fa8;border-color:#4a4f6a;background:#181a26;}}
  .legend-row{{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px;font-size:12.5px;}}
  .legend-item{{display:flex;align-items:center;gap:5px;color:var(--muted);}}
  .legend-dot{{width:12px;height:12px;border-radius:50%;flex-shrink:0;}}
  .legend-line{{width:24px;height:3px;flex-shrink:0;}}
  .narrative-sentence{{background:var(--panel2);border-left:3px solid var(--robust);border-radius:6px;
    padding:12px 14px;font-size:14px;line-height:1.5;margin:10px 0;}}
  .footnote{{color:#6a7090;font-size:11px;margin-top:6px;font-style:italic;}}
  .how-steps{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:14px 0;}}
  .how-step{{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:12px 16px;
    font-size:13px;text-align:center;flex:1;min-width:140px;}}
  .how-step .n{{color:var(--robust);font-weight:760;font-size:13px;margin-bottom:4px;}}
  .how-arrow{{color:var(--muted);font-size:18px;}}
  details.tech{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin-top:10px;}}
  details.tech summary{{cursor:pointer;font-weight:700;font-size:13px;color:var(--muted);}}
  details.tech table.dense{{margin-top:10px;}}
  table.dense{{width:100%;border-collapse:collapse;font-size:12.5px;}}
  table.dense th{{text-align:left;color:var(--muted);font-weight:600;padding:6px 8px;
    border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);}}
  table.dense td{{padding:5px 8px;border-bottom:1px solid #232842;}}
  .scroll-table{{max-height:380px;overflow-y:auto;}}
  .state-growth{{color:var(--good);}}
  .state-falling{{color:var(--bad);}}
  .state-stable{{color:var(--stag);}}
  .state-noevidence{{color:#4a4f6a;}}
  .basins-note{{background:#16182a;border:1px dashed var(--line);border-radius:8px;padding:12px 14px;
    color:var(--muted);font-size:13px;margin-top:10px;}}
  .graph-layout{{display:grid;grid-template-columns:1fr 340px;gap:14px;}}
  select:disabled{{opacity:.4;cursor:not-allowed;}}
  .gap-banner{{background:#1a1206;border:1px solid #7a5c10;border-radius:8px;padding:10px 14px;
    font-size:13px;color:#ffd180;margin-bottom:10px;}}
  @media(max-width:950px){{
    .map-layout,.graph-layout{{grid-template-columns:1fr;}}
    .kpis{{grid-template-columns:repeat(2,1fr);}}
    .how-steps{{flex-direction:column;}}
    .how-arrow{{transform:rotate(90deg);}}
  }}
</style>
</head>
<body>
<div class="wrap">

<h1>HERALD Observatory — What's happening?</h1>
<div class="subtitle">
  HERALD follows territories and sectors over time to identify growth, stagnation and observed
  economic relations. A dynamic observatory showing how sectors and territories evolve, where
  there is growth or stagnation, and which sectors appear to move before others.
</div>

<div class="kpis" id="kpi-bar"></div>

<!-- ── LANDING: Dynamic map ─────────────────────────────────────────── -->
<div class="section">
  <div class="section-title">The map — territories and sectors over time</div>
  <div class="section-note">
    Pick a country, a sector and a year. The map's colour itself shows whether a territory is
    growing, stable, falling, or has no evidence yet — there is no separate heatmap chart, the
    map <em>is</em> the heatmap. Use the timeline below to play through years like a film.
  </div>
  <div class="controls">
    <label>Country
      <select id="map-country" onchange="handleCountryChange()">
        <option value="FR">France</option>
        <option value="NL">Netherlands</option>
        <option value="PT">Portugal</option>
      </select>
    </label>
    <label>Sector
      <select id="map-sector" onchange="handleMapSectorChange()">
        <option value="ALL">All sectors (strongest shown)</option>
        {sector_options_html}
      </select>
    </label>
    <label>View
      <select id="map-view" onchange="renderTerritoryView()">
        <option value="state">Economic state</option>
        <option value="velocity">Speed of change</option>
        <option value="prediction">Above / below expected</option>
        <option value="basins">Similar dynamics (territory groups)</option>
      </select>
    </label>
    <span id="map-evidence-badge"></span>
  </div>
  <div class="legend-row" id="map-legend"></div>
  <div class="map-layout">
    <div class="card" id="map-card" style="min-height:520px"><div id="map-plot" style="height:520px"></div></div>
    <div class="side-panel" id="map-side">
      <h3>Territory detail</h3>
      <div class="side-empty" id="map-side-empty">Click a territory on the map to see its sectors, trend and evidence.</div>
      <div id="map-side-content" style="display:none"></div>
    </div>
  </div>
  <div class="controls" style="margin-top:12px">
    <button id="play-pause-btn" onclick="togglePlay()">&#9654; Play</button>
    <span style="display:flex;align-items:center;gap:8px;flex:1;min-width:240px;">
      <input type="range" id="year-slider" min="0" max="0" value="0" step="1" style="flex:1" oninput="onYearSliderInput()">
      <span id="year-label" style="font-size:13px;color:var(--muted);min-width:50px;text-align:right"></span>
    </span>
  </div>
  <div id="basins-panel" class="basins-note" style="display:none"></div>
</div>

<!-- ── PREDICTION LAYER ─────────────────────────────────────────────── -->
<div class="section">
  <div class="section-title">Above or below expected?</div>
  <div class="section-note">
    For each territory and sector we compare the observed value to what a simple trend-based
    expectation would predict. This tells us if a territory is over- or under-performing its own
    recent trend — it is not a guarantee about the future.
  </div>
  <div id="prediction-gap-banner" class="gap-banner"></div>
  <div class="card scroll-table">
    <table class="dense" id="prediction-table">
      <thead><tr><th>Territory</th><th>Sector</th><th>Year</th><th>Observed</th><th>Expected</th><th>Difference</th><th>Trend</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ── SECTOR → SECTOR GRAPH (dynamic, spatial) ───────────────────────── -->
<div class="section">
  <div class="section-title">Which sectors move together?</div>
  <div class="section-note">
    Each arrow links two sectors that have been observed moving in a related way over time —
    one tends to move before the other. This reflects <strong>observed evidence</strong>, not proof
    that one sector causes the other to grow.
  </div>
  <div class="controls">
    <label>Country <select id="graph-country" onchange="renderGraph();syncMapFromGraph()">
      <option value="ALL">All countries</option>
      <option value="FR">France</option>
      <option value="NL">Netherlands</option>
      <option value="PT">Portugal</option>
    </select></label>
    <label>Evidence <select id="graph-evidence" onchange="renderGraph()">
      <option value="ALL">All evidence levels</option>
      <option value="Robust">Robust</option>
      <option value="Supported">Supported</option>
      <option value="Exploratory">Exploratory</option>
    </select></label>
    <label>Mode
      <select id="graph-mode" onchange="updateWindowLabel();renderGraph()">
        <option value="persistent">All relations (faint) + active window</option>
        <option value="current">Active window only</option>
      </select>
    </label>
    <span id="edge-count-label" style="color:var(--muted);font-size:12.5px;"></span>
  </div>
  <div class="controls">
    <button id="graph-play-btn" onclick="toggleGraphPlay()">&#9654; Play relation timeline</button>
    <span style="display:flex;align-items:center;gap:8px;flex:1;min-width:240px;">
      <input type="range" id="window-slider" min="0" max="0" value="0" step="1" style="flex:1" oninput="onWindowSliderInput()">
      <span id="window-label" style="font-size:13px;color:var(--muted);min-width:110px;text-align:right"></span>
    </span>
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:var(--pos)"></div>Moves in the same direction</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--neg)"></div>Moves in the opposite direction</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--robust)"></div>Robust</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--supported);opacity:.8"></div>Supported</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--exploratory);opacity:.55"></div>Exploratory</div>
  </div>
  <div class="graph-layout">
    <div class="card"><div id="sector-graph" style="height:480px"></div></div>
    <div class="side-panel" id="edge-panel">
      <h3>Relation detail</h3>
      <div class="side-empty" id="edge-panel-empty">Click an arrow to see the plain-language explanation and the territories involved.</div>
      <div id="edge-panel-content" style="display:none"></div>
    </div>
  </div>
  <div class="section-note" style="margin-top:14px">Support view: the same relations plotted across time windows.</div>
  <div class="card"><div id="relation-heatmap" style="height:280px"></div></div>
</div>

<!-- ── HOW IT WORKS ─────────────────────────────────────────────────── -->
<div class="section">
  <div class="section-title">How it works</div>
  <div class="section-note">From raw territorial records to the signals shown above — in five plain steps.</div>
  <div class="how-steps">
    <div class="how-step"><div class="n">1</div>Territorial data<br><span style="color:var(--muted);font-size:11.5px">business counts per territory, sector and year</span></div>
    <div class="how-arrow">&#8594;</div>
    <div class="how-step"><div class="n">2</div>Expectation<br><span style="color:var(--muted);font-size:11.5px">a simple trend tells us what was expected</span></div>
    <div class="how-arrow">&#8594;</div>
    <div class="how-step"><div class="n">3</div>Economic state<br><span style="color:var(--muted);font-size:11.5px">growing / stable / falling, from year-to-year change</span></div>
    <div class="how-arrow">&#8594;</div>
    <div class="how-step"><div class="n">4</div>Sector relations<br><span style="color:var(--muted);font-size:11.5px">which sectors tend to move before others</span></div>
    <div class="how-arrow">&#8594;</div>
    <div class="how-step"><div class="n">5</div>Evidence &amp; signals<br><span style="color:var(--muted);font-size:11.5px">how strong and how reliable each signal is</span></div>
  </div>
</div>

<!-- ── EVIDENCE BADGES EXPLAINER ───────────────────────────────────────── -->
<div class="section">
  <div class="section-title">Evidence badges</div>
  <div class="section-note">Every number on this page carries a badge that says how solid the evidence behind it is.</div>
  <div class="legend-row">
    <div class="legend-item"><span class="badge badge-observed">Observed</span> directly measured</div>
    <div class="legend-item"><span class="badge badge-proxy">Proxy / context</span> estimated, shown for context only — never used for relations</div>
    <div class="legend-item"><span class="badge badge-robust">Robust</span> strongest observed relation evidence</div>
    <div class="legend-item"><span class="badge badge-supported">Supported</span> observed, with extra robustness checks</div>
    <div class="legend-item"><span class="badge badge-exploratory">Exploratory</span> observed, weaker signal, not for decisions</div>
    <div class="legend-item"><span class="badge badge-blocked">Blocked</span> found by automated screening but methodologically invalid — kept only for audit</div>
    <div class="legend-item"><span class="badge badge-absent">Not available</span> sector structurally absent for this country</div>
  </div>
</div>

<!-- ── BLOCKED / TECHNICAL PANEL ───────────────────────────────────────── -->
<div class="section">
  <div class="section-title">Technical details</div>
  <details class="tech">
    <summary>Blocked proxy artifacts (audit only, never a discovery)</summary>
    <div class="section-note" style="margin-top:8px">
      121 Netherlands gemeente-level proxy relations were nominally flagged by automated screening
      but a structural check found the underlying estimation method injects noise unrelated to any
      real precedence between sectors. They are preserved here for audit only, are never used for
      training, and never appear in the relation graph above.
    </div>
    <div class="card scroll-table">
      <table class="dense" id="blocked-table">
        <thead><tr><th>From</th><th>To</th><th>beta</th><th>Window</th><th>Reason</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </details>
  <details class="tech">
    <summary>Statistical detail (beta, q_fdr, bss, evidence type, sources, checksums)</summary>
    <div class="kpis" id="evidence-kpis" style="margin-top:10px"></div>
    <div class="card" style="margin-top:10px">
      <div class="side-field"><span class="lbl">DEC references</span><span id="dec-refs"></span></div>
      <div class="side-field"><span class="lbl">territory_view.csv checksum (16)</span><span id="chk-territory"></span></div>
      <div class="side-field"><span class="lbl">relation_view.csv checksum (16)</span><span id="chk-relation"></span></div>
      <div class="side-field"><span class="lbl">blocked_proxy_edges checksum (16)</span><span id="chk-blocked"></span></div>
    </div>
    <table class="dense" style="margin-top:10px">
      <thead><tr><th>From&#8594;To</th><th>Country</th><th>beta</th><th>q_fdr</th><th>bss</th><th>Window</th><th>label_class</th><th>evidence_type</th><th>allowed_for_training_label</th></tr></thead>
      <tbody id="tech-relation-tbody"></tbody>
    </table>
    <div class="footnote">
      A directed relation indicates predictive precedence (one sector's lagged growth statistically
      associates with another's), not structural causal proof.
    </div>
  </details>
  <details class="tech">
    <summary>Source files / export</summary>
    <div class="links-row" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px;">
      <a href="../../data/processed/herald_observatory_v05_narrative/territory_view.csv" style="color:var(--robust);text-decoration:none;font-size:12px;border:1px solid var(--line);border-radius:5px;padding:6px 10px;background:var(--panel2);">territory_view.csv</a>
      <a href="../../data/processed/herald_observatory_v05_narrative/relation_view.csv" style="color:var(--robust);text-decoration:none;font-size:12px;border:1px solid var(--line);border-radius:5px;padding:6px 10px;background:var(--panel2);">relation_view.csv</a>
      <a href="../../data/processed/herald_observatory_v05_narrative/prediction_view.csv" style="color:var(--robust);text-decoration:none;font-size:12px;border:1px solid var(--line);border-radius:5px;padding:6px 10px;background:var(--panel2);">prediction_view.csv</a>
      <a href="../../data/processed/herald_observatory_v05_narrative/manifest.json" style="color:var(--robust);text-decoration:none;font-size:12px;border:1px solid var(--line);border-radius:5px;padding:6px 10px;background:var(--panel2);">manifest.json</a>
    </div>
    <div style="color:var(--muted);font-size:11px;margin-top:8px;">
      Plotly dependency: {kw['plotly_dep']}. {"Embedded locally — works fully offline." if kw['plotly_dep']=="local_embedded" else "CDN fallback — requires internet to render plots."}
      Animated transitions use GSAP (loaded from CDN, used only for the year/window playback and map colour transitions — not decorative).
    </div>
  </details>
</div>

</div>

<script>
const REGION_META = {kw['region_meta_js']};
const MAP_STATE = {kw['map_state_js']};
const NODE_POS = {kw['node_pos_js']};
const SECTOR_LABELS = {kw['sector_labels_js']};
const GEO_FR = {kw['geo_fr_js']};
const GEO_NL = {kw['geo_nl_js']};
const GEO_PT = {kw['geo_pt_js']};
const GEO = {{FR: GEO_FR, NL: GEO_NL, PT: GEO_PT}};
const RELATION_EDGES = {kw['relation_edges_js']};
const RELATION_TIMELINE = {kw['relation_timeline_js']};
const BLOCKED_EDGES = {kw['blocked_edges_js']};
// PREDICTION_LOOKUP[country][region_id][sector][year] = [observed, expected, difference, trend_state]
const PREDICTION_LOOKUP = {kw['prediction_lookup_js']};
const SECTOR_VIEW_ROWS = {kw['sector_view_js']};
const MANIFEST = {kw['manifest_js']};
const MAP_CONFIG = {kw['map_config_js']};
const CSV_CHECKSUMS = {kw['csv_checksums_js']};
const N_TERRITORIES = {kw['n_territories_js']};
const N_VALID_RELATIONS = {kw['n_valid_relations']};
const N_BLOCKED_RELATIONS = {kw['n_blocked_relations']};
const N_SECTORS_TRACKED = {kw['n_sectors_tracked']};
const PT_KZ_STRUCTURAL_ABSENT = {kw['pt_kz_structural_absent']};
const PREDICTION_COUNTRIES = {kw['prediction_countries_js']};
const PT_MAP_STATUS = {json.dumps(kw['pt_map_status'])};

const SECTORS = {json.dumps(SECTORS_ORDER)};
const STATE_COLORS = {{'Growing':'#26a69a','Stable':'#9aa4bf','Falling':'#ef5350',
  'No evidence':'#3a3f56','Sector not available for Portugal':'#2a2c3a'}};
const STATE_NUM = {{'Growing':1,'Stable':0,'Falling':-1,'No evidence':null,
  'Sector not available for Portugal':null}};
const BASE_LAYOUT = {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font:{{color:'#eef2ff',family:'Inter,Segoe UI,Arial,sans-serif',size:12}},
  margin:{{l:50,r:20,t:30,b:40}},
  hoverlabel:{{bgcolor:'#20253a',bordercolor:'#30364f',font:{{color:'#eef2ff'}}}},
}};

let PLAY_INTERVAL = null;
let GRAPH_PLAY_INTERVAL = null;
let HIGHLIGHT_SECTOR = null;
let YEARS_BY_COUNTRY = {{}};

// ── KPI bar ──────────────────────────────────────────────────────────
function renderKpis() {{
  const totalTerritories = Object.values(N_TERRITORIES).reduce((a,b)=>a+b,0);
  const items = [
    ['Territories observed', totalTerritories.toLocaleString()],
    ['Valid relations', N_VALID_RELATIONS],
    ['Blocked relations (audit only)', N_BLOCKED_RELATIONS],
    ['Sectors tracked', N_SECTORS_TRACKED],
  ];
  document.getElementById('kpi-bar').innerHTML = items.map(([l,v])=>
    `<div class="kpi"><div class="v">${{v}}</div><div class="l">${{l}}</div></div>`).join('');

  const evItems = [
    ['Valid relations', N_VALID_RELATIONS],
    ['Blocked (audit only)', N_BLOCKED_RELATIONS],
    ['Prediction layer countries', PREDICTION_COUNTRIES.join(', ') || 'none'],
  ];
  document.getElementById('evidence-kpis').innerHTML = evItems.map(([l,v])=>
    `<div class="kpi"><div class="v" style="font-size:15px">${{v}}</div><div class="l">${{l}}</div></div>`).join('');
  document.getElementById('dec-refs').textContent = (MANIFEST.dec_references||[]).join(', ');
  document.getElementById('chk-territory').textContent = CSV_CHECKSUMS['territory_view.csv'];
  document.getElementById('chk-relation').textContent = CSV_CHECKSUMS['relation_view.csv'];
  document.getElementById('chk-blocked').textContent = CSV_CHECKSUMS['blocked_proxy_edges_v04_copy.csv'];

  const tbody = document.getElementById('tech-relation-tbody');
  tbody.innerHTML = RELATION_EDGES.map(e => `<tr>
    <td>${{e.source_sector}}&#8594;${{e.target_sector}}</td><td>${{e.country}}</td>
    <td>${{e.beta.toFixed(4)}}</td><td>${{e.q_fdr.toFixed(3)}}</td><td>${{e.bss.toFixed(3)}}</td>
    <td>${{e.window}}</td><td>${{e.label_class}}</td><td style="font-size:10px">${{e.evidence_type}}</td>
    <td>${{e.allowed_for_training_label}}</td></tr>`).join('');
}}

// ── PT/KZ handling ──────────────────────────────────────────────────
function refreshSectorOptionsForCountry(country) {{
  const sel = document.getElementById('map-sector');
  Array.from(sel.options).forEach(opt => {{
    if (opt.value === 'KZ') {{
      const disable = country === 'PT' && PT_KZ_STRUCTURAL_ABSENT;
      opt.disabled = disable;
      opt.title = disable ? 'Not available for Portugal (structurally absent sector)' : '';
      opt.textContent = disable
        ? SECTOR_LABELS['KZ'] + ' (KZ) — not available for Portugal'
        : SECTOR_LABELS['KZ'] + ' (KZ)';
      if (disable && sel.value === 'KZ') sel.value = 'ALL';
    }}
  }});
}}

// ── Map / territory view ────────────────────────────────────────────
function populateYearOptions(country) {{
  const years = new Set();
  const regions = MAP_STATE[country] || {{}};
  Object.values(regions).forEach(secMap => Object.values(secMap).forEach(yearMap =>
    Object.keys(yearMap).forEach(y => years.add(parseInt(y)))));
  YEARS_BY_COUNTRY[country] = [...years].sort((a,b)=>a-b);
  const slider = document.getElementById('year-slider');
  slider.min = 0; slider.max = Math.max(0, YEARS_BY_COUNTRY[country].length-1);
  slider.value = slider.max;
  updateYearLabel();
}}

function currentYear() {{
  const country = document.getElementById('map-country').value;
  const idx = parseInt(document.getElementById('year-slider').value);
  const years = YEARS_BY_COUNTRY[country] || [];
  return years[idx] || years[years.length-1];
}}

function updateYearLabel() {{
  document.getElementById('year-label').textContent = currentYear() || 'n/a';
}}

function onYearSliderInput() {{ updateYearLabel(); renderTerritoryView(); }}

function togglePlay() {{
  const btn = document.getElementById('play-pause-btn');
  if (PLAY_INTERVAL) {{ clearInterval(PLAY_INTERVAL); PLAY_INTERVAL=null; btn.innerHTML='&#9654; Play'; return; }}
  btn.innerHTML = '&#10074;&#10074; Pause';
  PLAY_INTERVAL = setInterval(() => {{
    const slider = document.getElementById('year-slider');
    let idx = parseInt(slider.value) + 1;
    if (idx > parseInt(slider.max)) idx = 0;
    slider.value = idx;
    onYearSliderInput();
  }}, 1000);
}}

function handleCountryChange() {{
  const country = document.getElementById('map-country').value;
  refreshSectorOptionsForCountry(country);
  populateYearOptions(country);
  renderTerritoryView();
  document.getElementById('graph-country').value = country;
  renderGraph();
}}

function handleMapSectorChange() {{
  const sector = document.getElementById('map-sector').value;
  HIGHLIGHT_SECTOR = sector === 'ALL' ? null : sector;
  renderTerritoryView();
  renderGraph();
}}

function renderTerritoryView() {{
  const country = document.getElementById('map-country').value;
  const view = document.getElementById('map-view').value;
  document.getElementById('basins-panel').style.display = view === 'basins' ? 'block' : 'none';
  if (view === 'basins') {{
    document.getElementById('basins-panel').innerHTML =
      '<strong>Similar dynamics (coming)</strong> — grouping territories with similar temporal ' +
      'growth/decline patterns ("territories with similar dynamics") is planned but not yet computed ' +
      'for this release. It will use temporal correlation across normalised state/velocity series, ' +
      'never a causal community.';
  }}
  const isMapped = ['FR','NL','PT'].includes(country) && GEO[country] && GEO[country].features
    && GEO[country].features.length > 0;
  document.getElementById('map-card').innerHTML = isMapped
    ? '<div id="map-plot" style="height:520px"></div>'
    : '<div class="scroll-table"><table class="dense" id="territory-table"><thead><tr>'
      + '<th>Territory</th><th>Sector</th><th>State</th><th>Speed of change</th><th>Evidence</th></tr></thead><tbody></tbody></table></div>';
  if (['FR','NL','PT'].includes(country) && !isMapped) {{
    document.getElementById('map-card').insertAdjacentHTML('afterbegin',
      '<div class="gap-banner">Map geometry unavailable for this view — showing a table instead of a fabricated map.</div>');
  }}
  const badgeClass = 'badge-observed';
  document.getElementById('map-evidence-badge').innerHTML = `<span class="badge ${{badgeClass}}">Observed</span>`;
  if (isMapped) renderMap(country, view); else renderTerritoryTable(country, view);
}}

// MAP_STATE cell array layout: [state_human, velocity, value, evidence_badge]
const CELL_STATE=0, CELL_VEL=1, CELL_VALUE=2, CELL_BADGE=3;
// PREDICTION_LOOKUP cell array layout: [observed, expected, difference, trend_state]
const PRED_OBS=0, PRED_EXP=1, PRED_DIFF=2, PRED_TREND=3;

function cellForRegionSectorYear(country, rid, sector, year) {{
  const regions = MAP_STATE[country] || {{}};
  const secMap = regions[rid] || {{}};
  return (secMap[sector]||{{}})[year] || null;
}}

function bestSectorForRegion(country, rid, year) {{
  const regions = MAP_STATE[country] || {{}};
  const secMap = regions[rid] || {{}};
  let best=null, bestAbs=-1, bestCell=null;
  Object.keys(secMap).forEach(s => {{
    const cell = (secMap[s]||{{}})[year];
    if (cell && cell[CELL_VEL] != null && Math.abs(cell[CELL_VEL]) > bestAbs) {{ bestAbs=Math.abs(cell[CELL_VEL]); best=s; bestCell=cell; }}
  }});
  return [best, bestCell];
}}

function predictionLookup(country, rid, sector, year) {{
  const cell = (((PREDICTION_LOOKUP[country]||{{}})[String(rid)]||{{}})[sector]||{{}})[year];
  return cell || null;
}}

function renderMap(country, view) {{
  const year = currentYear();
  const sector = document.getElementById('map-sector').value;
  const regions = MAP_STATE[country] || {{}};
  const meta = REGION_META[country] || {{}};
  const geo = GEO[country];

  const locations=[], z=[], text=[], customdata=[];
  Object.keys(regions).forEach(rid => {{
    let shownSector = sector, cell = null;
    if (sector === 'ALL') {{ const [b,c] = bestSectorForRegion(country, rid, year); shownSector=b; cell=c; }}
    else {{ cell = cellForRegionSectorYear(country, rid, sector, year); }}
    const name = (meta[rid]||{{}}).name || rid;
    locations.push(rid);
    if (!cell) {{
      z.push(null);
      customdata.push({{rid, name, sector: shownSector, year, value:null, state:'No evidence', vel:null}});
      text.push(name + ': No evidence');
      return;
    }}
    let zval, label;
    if (view === 'velocity') {{ zval = cell[CELL_VEL]; label='speed='+(cell[CELL_VEL]!=null?cell[CELL_VEL].toFixed(3):'n/a'); }}
    else if (view === 'prediction') {{
      const pr = predictionLookup(country, rid, shownSector, year);
      zval = pr ? pr[PRED_DIFF] : null;
      label = pr ? ('diff='+pr[PRED_DIFF].toFixed(1)) : 'No prediction available';
    }} else {{ zval = STATE_NUM[cell[CELL_STATE]]; label = cell[CELL_STATE]; }}
    z.push(zval);
    customdata.push({{rid, name, sector: shownSector, year, value:cell[CELL_VALUE], state:cell[CELL_STATE], vel:cell[CELL_VEL]}});
    text.push(name + '<br>sector=' + (shownSector||'') + '<br>' + label);
  }});

  const colorscale = view==='state'
    ? [[0,'#ef5350'],[0.5,'#9aa4bf'],[1,'#26a69a']]
    : [[0,'#ef5350'],[0.5,'#171b2d'],[1,'#26a69a']];
  const trace = {{
    type:'choropleth', geojson: geo, featureidkey:'properties.panel_id',
    locations, z, text, customdata, colorscale,
    zmin: view==='state' ? -1 : undefined, zmax: view==='state' ? 1 : undefined,
    zmid: view!=='state' ? 0 : undefined,
    colorbar:{{title: view==='state'?'State':(view==='velocity'?'Speed':'Diff'), tickfont:{{color:'#eef2ff',size:10}}, thickness:14, len:0.8}},
    hovertemplate:'%{{text}}<extra></extra>',
    marker:{{line:{{width:0.5, color:'#30364f'}}}}, showscale:true,
  }};
  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    geo:{{fitbounds:'geojson', visible:false, bgcolor:'#0f1220', showframe:false, showcoastlines:false}},
    margin:{{l:0,r:0,t:30,b:0}},
    title:{{text: (MAP_CONFIG[country]||{{}}).label + ' — ' + year + ' — ' + (sector==='ALL'?'all sectors':sector),
      font:{{size:13,color:'#eef2ff'}}}},
  }});
  Plotly.newPlot('map-plot', [trace], layout, {{responsive:true, displayModeBar:false}});
  document.getElementById('map-plot').on('plotly_click', function(data) {{
    const pt = data.points[0];
    if (pt && pt.customdata) showTerritorySidePanel(country, pt.customdata);
  }});
  renderMapLegend(view);
}}

function renderTerritoryTable(country, view) {{
  const year = currentYear();
  const sector = document.getElementById('map-sector').value;
  const regions = MAP_STATE[country] || {{}};
  const meta = REGION_META[country] || {{}};
  const rows = [];
  Object.keys(regions).forEach(rid => {{
    const secMap = regions[rid];
    const m = meta[rid] || {{}};
    const sectorsToShow = sector === 'ALL' ? Object.keys(secMap) : [sector];
    sectorsToShow.forEach(s => {{
      const cell = (secMap[s]||{{}})[year];
      if (!cell) return;
      rows.push([m.name||rid, s, cell[CELL_STATE], cell[CELL_VEL], cell[CELL_BADGE]]);
    }});
  }});
  const tbody = document.querySelector('#territory-table tbody');
  tbody.innerHTML = rows.slice(0,500).map(r => {{
    const stCls = r[2]==='Growing'?'state-growth':r[2]==='Falling'?'state-falling':r[2]==='Stable'?'state-stable':'state-noevidence';
    const badgeCls = r[4]==='Proxy / context' ? 'badge-proxy' : 'badge-observed';
    return `<tr><td>${{r[0]}}</td><td>${{SECTOR_LABELS[r[1]]||r[1]}} (${{r[1]}})</td>`
      + `<td class="${{stCls}}">${{r[2]}}</td><td>${{r[3]!=null?r[3].toFixed(3):'No evidence'}}</td>`
      + `<td><span class="badge ${{badgeCls}}">${{r[4]}}</span></td></tr>`;
  }}).join('');
  renderMapLegend(view);
}}

function renderMapLegend(view) {{
  const el = document.getElementById('map-legend');
  if (view === 'state' || view === 'basins') {{
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Growing</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>Stable</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Falling</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#3a3f56"></div>No evidence</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#b39ddb"></div>Proxy / context</div>`;
  }} else {{
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Below / falling</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>~ at expectation</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Above / growing</div>`;
  }}
}}

function showTerritorySidePanel(country, cd) {{
  const meta = (REGION_META[country]||{{}})[cd.rid] || {{}};
  const badge = meta.is_proxy_context
    ? '<span class="badge badge-proxy">Proxy / context</span>' : '<span class="badge badge-observed">Observed</span>';
  const allSectors = (MAP_STATE[country]||{{}})[cd.rid] || {{}};
  const sector = cd.sector || Object.keys(allSectors)[0];
  const yearMap = allSectors[sector] || {{}};
  const seriesY = Object.keys(yearMap).map(Number).sort((a,b)=>a-b);
  const seriesV = seriesY.map(y => yearMap[y][CELL_VEL]);

  const ranking = Object.keys(allSectors).map(s => {{
    const row = (allSectors[s]||{{}})[cd.year];
    return row ? {{sector:s, vel:row[CELL_VEL], state:row[CELL_STATE]}} : null;
  }}).filter(Boolean).sort((a,b)=>(b.vel||0)-(a.vel||0));

  document.getElementById('map-side-empty').style.display = 'none';
  const content = document.getElementById('map-side-content');
  content.style.display = 'block';
  const kzNote = (country==='PT' && sector==='KZ' && PT_KZ_STRUCTURAL_ABSENT)
    ? '<div class="footnote">Finance and insurance (KZ) is structurally absent for Portugal — not a data gap.</div>' : '';
  content.innerHTML = `
    <div style="margin-bottom:8px">${{badge}}</div>
    <div class="side-field"><span class="lbl">Territory</span><span>${{cd.name}}</span></div>
    <div class="side-field"><span class="lbl">Region type</span><span>${{meta.region_system||''}}</span></div>
    <div class="side-field"><span class="lbl">Sector</span><span>${{SECTOR_LABELS[sector]||sector}} (${{sector}})</span></div>
    <div class="side-field"><span class="lbl">Year</span><span>${{cd.year}}</span></div>
    <div class="side-field"><span class="lbl">State</span><span>${{cd.state||'No evidence'}}</span></div>
    ${{kzNote}}
    <div id="ts-plot" style="height:140px;margin-top:8px"></div>
    <h3 style="margin-top:10px">Main sectors here (${{cd.year}})</h3>
    <table class="dense">${{ranking.slice(0,9).map(r=>`<tr><td>${{SECTOR_LABELS[r.sector]||r.sector}} (${{r.sector}})</td><td class="${{r.state==='Growing'?'state-growth':r.state==='Falling'?'state-falling':'state-stable'}}">${{r.state}}</td></tr>`).join('')}}</table>
  `;
  Plotly.newPlot('ts-plot', [{{x:seriesY, y:seriesV, type:'scatter', mode:'lines+markers',
    line:{{color:'#4aa3ff'}}, marker:{{size:4}}}}],
    Object.assign({{}}, BASE_LAYOUT, {{margin:{{l:30,r:10,t:10,b:20}},
      xaxis:{{tickfont:{{size:9}}}}, yaxis:{{title:'speed of change',tickfont:{{size:9}},titlefont:{{size:9}}}}}}),
    {{responsive:true, displayModeBar:false}});
}}

// ── Prediction table ─────────────────────────────────────────────────
function renderPredictionTable() {{
  const banner = document.getElementById('prediction-gap-banner');
  banner.textContent = 'Validated against expectation today for: ' + PREDICTION_COUNTRIES.join(', ') +
    '. Portugal is not yet included at this territorial detail — see the Prediction Gap report for why and what would be needed.';
  const rows = [];
  Object.keys(PREDICTION_LOOKUP).forEach(country => {{
    const regions = PREDICTION_LOOKUP[country];
    Object.keys(regions).forEach(rid => {{
      const sectors = regions[rid];
      Object.keys(sectors).forEach(sector => {{
        const years = sectors[sector];
        Object.keys(years).forEach(year => {{
          if (rows.length >= 300) return;
          const cell = years[year];
          rows.push({{country, rid, sector, year: parseInt(year), obs: cell[PRED_OBS],
            exp: cell[PRED_EXP], diff: cell[PRED_DIFF], trend: cell[PRED_TREND]}});
        }});
      }});
    }});
  }});
  const meta = REGION_META;
  document.querySelector('#prediction-table tbody').innerHTML = rows.slice(0,300).map(r => {{
    const name = (meta[r.country]?.[String(r.rid)]||{{}}).name || r.rid;
    const diffCls = r.diff > 0 ? 'state-growth' : r.diff < 0 ? 'state-falling' : 'state-stable';
    return `<tr><td>${{name}} (${{r.country}})</td><td>${{SECTOR_LABELS[r.sector]||r.sector}}</td>`
      + `<td>${{r.year}}</td><td>${{r.obs!=null?r.obs.toFixed(0):'No evidence'}}</td>`
      + `<td>${{r.exp!=null?r.exp.toFixed(0):'No evidence'}}</td>`
      + `<td class="${{diffCls}}">${{r.diff!=null?r.diff.toFixed(0):'No evidence'}}</td>`
      + `<td>${{r.trend}}</td></tr>`;
  }}).join('');
}}

// ── Sector graph ────────────────────────────────────────────────────
function populateWindowOptions() {{
  const slider = document.getElementById('window-slider');
  slider.min = 0; slider.max = Math.max(0, RELATION_TIMELINE.windows.length-1);
  slider.value = slider.max;
  updateWindowLabel();
}}
function currentWindow() {{
  const idx = parseInt(document.getElementById('window-slider').value);
  return RELATION_TIMELINE.windows[idx] || RELATION_TIMELINE.windows[RELATION_TIMELINE.windows.length-1];
}}
function updateWindowLabel() {{ document.getElementById('window-label').textContent = currentWindow() || 'n/a'; }}
function onWindowSliderInput() {{ updateWindowLabel(); renderGraph(); }}
function toggleGraphPlay() {{
  const btn = document.getElementById('graph-play-btn');
  if (GRAPH_PLAY_INTERVAL) {{ clearInterval(GRAPH_PLAY_INTERVAL); GRAPH_PLAY_INTERVAL=null; btn.innerHTML='&#9654; Play relation timeline'; return; }}
  btn.innerHTML = '&#10074;&#10074; Pause';
  GRAPH_PLAY_INTERVAL = setInterval(() => {{
    const slider = document.getElementById('window-slider');
    let idx = parseInt(slider.value) + 1;
    if (idx > parseInt(slider.max)) idx = 0;
    slider.value = idx;
    onWindowSliderInput();
  }}, 1300);
}}
function syncMapFromGraph() {{
  const c = document.getElementById('graph-country').value;
  if (['FR','NL','PT'].includes(c)) {{ document.getElementById('map-country').value = c; handleCountryChange(); }}
}}

function renderGraph() {{
  const country = document.getElementById('graph-country').value;
  const evidence = document.getElementById('graph-evidence').value;
  const mode = document.getElementById('graph-mode').value;
  const w = currentWindow();

  const baseFiltered = RELATION_EDGES.filter(e => {{
    if (country !== 'ALL' && e.country !== country) return false;
    if (evidence !== 'ALL' && e.evidence_badge !== evidence) return false;
    return true;
  }});
  const activeEdges = baseFiltered.filter(e => e.window === w);
  const faintEdges = mode === 'persistent' ? baseFiltered.filter(e => e.window !== w) : [];

  const annotations = [], edgeTraces = [];
  function drawSet(edges, faint) {{
    const pairIdx = {{}};
    edges.forEach((e) => {{
      const sp = NODE_POS[e.source_sector], tp = NODE_POS[e.target_sector];
      if (!sp || !tp) return;
      const key = e.source_sector+'->'+e.target_sector;
      pairIdx[key] = (pairIdx[key]||0)+1;
      const hasRev = edges.some(e2=>e2.source_sector===e.target_sector&&e2.target_sector===e.source_sector);
      const off = hasRev ? (pairIdx[key]%2===0?1:-1)*0.06 : 0;
      const dx=tp.x-sp.x, dy=tp.y-sp.y, dist=Math.sqrt(dx*dx+dy*dy)||1;
      const ux=dx/dist, uy=dy/dist, r=0.15;
      const px=-uy*off, py=ux*off;
      const ax=sp.x+ux*r+px, ay=sp.y+uy*r+py, x=tp.x-ux*r+px, y=tp.y-uy*r+py;
      const col = e.sign==='+' ? '#26a69a' : '#ef5350';
      const isHighlighted = !HIGHLIGHT_SECTOR || e.source_sector===HIGHLIGHT_SECTOR || e.target_sector===HIGHLIGHT_SECTOR;
      const w2 = (1+Math.abs(e.beta||0)*10) * (isHighlighted ? 1 : 0.6);
      const dash = e.evidence_badge==='Robust' ? 'solid' : e.evidence_badge==='Supported' ? 'dash' : 'dot';
      let opacity = faint ? 0.12 : (e.evidence_badge==='Robust' ? 0.95 : e.evidence_badge==='Supported' ? 0.8 : 0.45);
      if (!isHighlighted) opacity *= 0.3;
      edgeTraces.push({{
        x:[ax,x,null], y:[ay,y,null], mode:'lines', type:'scatter',
        line:{{color:col,width:w2,dash}}, opacity, hoverinfo: faint ? 'skip' : 'text',
        text:`${{e.source_sector}}\\u2192${{e.target_sector}} (${{e.country}}) ${{e.direction_human}}`,
        customdata:[RELATION_EDGES.indexOf(e)], showlegend:false, name:key,
      }});
      if (!faint) annotations.push({{x,y,ax,ay,xref:'x',yref:'y',axref:'x',ayref:'y',
        showarrow:true,arrowhead:2,arrowsize:1.1,arrowwidth:Math.max(1.3,w2*0.6),arrowcolor:col,opacity}});
    }});
  }}
  drawSet(faintEdges, true);
  drawSet(activeEdges, false);

  const nodeTrace = {{
    x:SECTORS.map(s=>NODE_POS[s].x), y:SECTORS.map(s=>NODE_POS[s].y),
    mode:'markers+text', type:'scatter',
    marker:{{size:30,color:SECTORS.map(s=>s===HIGHLIGHT_SECTOR?'#2d3a5c':'#20253a'),
      line:{{color:'#4aa3ff',width:1.5}}}},
    text:SECTORS, textfont:{{size:10,color:'#eef2ff'}}, textposition:'middle center',
    hovertext:SECTORS.map(s=>'<b>'+(SECTOR_LABELS[s]||s)+'</b> ('+s+')'),
    hovertemplate:'%{{hovertext}}<extra></extra>', name:'sectors',
  }};
  document.getElementById('edge-count-label').textContent = activeEdges.length + ' active relation(s) at ' + (w||'n/a') +
    (mode==='persistent' ? (' · ' + faintEdges.length + ' other valid relations shown faint') : '');
  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    xaxis:{{range:[-1.6,1.6],showgrid:false,zeroline:false,showticklabels:false}},
    yaxis:{{range:[-1.45,1.45],showgrid:false,zeroline:false,showticklabels:false,scaleanchor:'x'}},
    annotations, showlegend:false, hovermode:'closest',
    margin:{{l:10,r:10,t:10,b:10}},
  }});
  Plotly.newPlot('sector-graph', [...edgeTraces, nodeTrace], layout, {{responsive:true, displayModeBar:false}});
  document.getElementById('sector-graph').on('plotly_click', function(data) {{
    const pt = data.points[0];
    if (pt.data.customdata) showEdgeDetail(RELATION_EDGES[pt.data.customdata[0]]);
  }});
  renderRelationHeatmap(baseFiltered);
}}

function showEdgeDetail(e) {{
  if (!e) return;
  const badgeCls = e.evidence_badge==='Robust'?'badge-robust':e.evidence_badge==='Supported'?'badge-supported':'badge-exploratory';
  const signBadge = e.sign==='+' ? '<span class="badge badge-pos">Same direction</span>' : '<span class="badge badge-neg">Opposite direction</span>';
  document.getElementById('edge-panel-empty').style.display = 'none';
  const content = document.getElementById('edge-panel-content');
  content.style.display = 'block';
  content.innerHTML = `
    <div style="margin:0 0 8px">${{SECTOR_LABELS[e.source_sector]}} (${{e.source_sector}}) &#8594; ${{SECTOR_LABELS[e.target_sector]}} (${{e.target_sector}})</div>
    <div style="margin-bottom:10px"><span class="badge ${{badgeCls}}">${{e.evidence_badge}}</span> ${{signBadge}}</div>
    <div class="narrative-sentence">${{e.plain_sentence}}</div>
    <div class="side-field"><span class="lbl">Country</span><span>${{e.country}}</span></div>
    <div class="side-field"><span class="lbl">Window</span><span>${{e.window}}</span></div>
    <div class="footnote">Aggregated territorial context for this relation — no municipality-level attribution exists for this relation.</div>
    <h3 style="margin-top:10px">Territory context (${{e.country}}, ${{e.window_end}})</h3>
    ${{territoryContextTable(e)}}
  `;
}}

function territoryContextTable(e) {{
  const sectors = [e.source_sector, e.target_sector];
  const regions = MAP_STATE[e.country] || {{}};
  const rows = sectors.map(s => {{
    const counts = {{Growing:0, Stable:0, Falling:0, 'No evidence':0}};
    Object.keys(regions).forEach(rid => {{
      const cell = (regions[rid][s]||{{}})[e.window_end];
      const label = cell ? cell[CELL_STATE] : 'No evidence';
      counts[label] = (counts[label]||0)+1;
    }});
    return `<tr><td>${{SECTOR_LABELS[s]}} (${{s}})</td><td class="state-growth">${{counts.Growing}}</td>`+
      `<td class="state-falling">${{counts.Falling}}</td><td class="state-stable">${{counts.Stable}}</td>`+
      `<td class="state-noevidence">${{counts['No evidence']}}</td></tr>`;
  }}).join('');
  return `<table class="dense"><thead><tr><th>Sector</th><th>Growing</th><th>Falling</th><th>Stable</th><th>No evidence</th></tr></thead><tbody>${{rows}}</tbody></table>`;
}}

function renderRelationHeatmap(filtered) {{
  const pairs = [...new Set(filtered.map(e=>e.country+': '+e.source_sector+'\\u2192'+e.target_sector))].sort();
  const windows = RELATION_TIMELINE.windows;
  const z = pairs.map(p => windows.map(w => {{
    const [c, st] = p.split(': '); const [s,t] = st.split('\\u2192');
    const match = filtered.find(e=>e.country===c && e.source_sector===s && e.target_sector===t && e.window===w);
    return match ? match.beta : null;
  }}));
  const trace = {{ type:'heatmap', x: windows, y: pairs, z,
    colorscale:[[0,'#ef5350'],[0.5,'#171b2d'],[1,'#26a69a']], zmid:0,
    colorbar:{{title:'strength', tickfont:{{color:'#eef2ff',size:10}}, thickness:12}}, hoverinfo:'x+y+z' }};
  const layout = Object.assign({{}}, BASE_LAYOUT, {{margin:{{l:140,r:20,t:10,b:50}},
    xaxis:{{tickangle:-45, tickfont:{{size:9}}}}, yaxis:{{tickfont:{{size:9}}, automargin:true}}}});
  Plotly.newPlot('relation-heatmap', [trace], layout, {{responsive:true, displayModeBar:false}});
}}

function renderBlockedTable() {{
  document.querySelector('#blocked-table tbody').innerHTML = BLOCKED_EDGES.map(e => `<tr>
    <td>${{SECTOR_LABELS[e.source_sector]||e.source_sector}} (${{e.source_sector}})</td>
    <td>${{SECTOR_LABELS[e.target_sector]||e.target_sector}} (${{e.target_sector}})</td>
    <td>${{e.beta.toFixed(4)}}</td><td>${{e.window}}</td><td>${{e.reason}}</td></tr>`).join('');
}}

// ── Init ────────────────────────────────────────────────────────────
renderKpis();
refreshSectorOptionsForCountry('FR');
populateYearOptions('FR');
renderTerritoryView();
populateWindowOptions();
renderGraph();
renderPredictionTable();
renderBlockedTable();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
