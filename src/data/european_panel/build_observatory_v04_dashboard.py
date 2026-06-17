"""
DEC-065 consolidation: build the HERALD Observatory v0.4 granular dashboard.

Reads the validated exports from data/processed/herald_observatory_v04_granular/
(territory state panel, relation edges, blocked proxy edges, manifest) and emits
a single self-contained HTML dashboard.

Hard rules (must not be violated by this builder):
  - NL gemeente proxy edges NEVER enter the sector->sector relation graph.
    The graph is built ONLY from granular_relation_edges.csv, which by
    construction contains FR ZE2020 / PT Municipality / NL COROP observed only.
  - blocked_proxy_edges.csv (121 NL gemeente proxy edges) renders in a separate
    "Blocked proxy artifacts" panel only, never as graph edges.
  - NL gemeente proxy territory rows carry a visible "proxy/context" badge in
    the territorial map/table; they may never be styled identically to observed
    sources.
  - No structural-causal language anywhere in the generated HTML.

Reused patterns from build_observatory_v03.py: local Plotly embedding,
FR ZE2020 / NL COROP geojson construction (NL_COROP_TO_NUTS3 crosswalk),
circular sector-graph layout, dark theme CSS.
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
DATA_DIR = REPO_ROOT / "data/processed/herald_observatory_v04_granular"
TERRITORY_PATH = DATA_DIR / "granular_territory_state_panel.csv"
RELATION_PATH = DATA_DIR / "granular_relation_edges.csv"
BLOCKED_PATH = DATA_DIR / "blocked_proxy_edges.csv"
MANIFEST_PATH = DATA_DIR / "manifest.json"

ZE_GEOJSON_PATH = REPO_ROOT / "data/external/ze2020_geometry.geojson"
NUTS3_GEOJSON_PATH = REPO_ROOT / "data/external/nuts3_2021_eurostat.geojson"

OUT_PATH = REPO_ROOT / "reports/dashboards/herald_observatory_v04_granular_dashboard.html"

SECTOR_LABELS = {
    "BE": "Industry (mining, energy, waste)",
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

# Region systems rendered with real geometry vs table fallback
MAPPED_SYSTEMS = {"ZE2020", "COROP"}
TABLE_SYSTEMS = {"MUNICIPALITY", "GEMEENTE_PROXY"}

MAP_CONFIG = {
    "FR": {"region_system": "ZE2020", "label": "France — ZE2020 (observed)",
           "note": "France uses functional employment zones (ZE2020, n=280)."},
    "NL": {"region_system": "COROP", "label": "Netherlands — COROP (observed)",
           "note": "Netherlands uses COROP regions (n=40), NUTS3-equivalent."},
}
TABLE_CONFIG = {
    "PT": {"region_system": "MUNICIPALITY", "label": "Portugal — Municipality (observed)",
           "badge": "observed"},
    "NL_GEMEENTE": {"region_system": "GEMEENTE_PROXY",
                     "label": "Netherlands — Gemeente (proxy/context)",
                     "badge": "proxy"},
}

# NL COROP panel territory_id -> NUTS3 geometry NUTS_ID (reused from build_observatory_v03.py)
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

STATE_NUM = {"DECLINE": -1, "STAGNATION": 0, "GROWTH": 1}


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


def _plotly_js_tag() -> str:
    """Return <script> tag embedding Plotly locally, or CDN fallback (documented)."""
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
    logger.info("FR GeoJSON: %d features", len(features))
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
            logger.warning("NL NUTS3 code %s not in geojson", nuts_code)
            continue
        feat = nuts3_by_code[nuts_code]
        f2 = dict(feat)
        f2["properties"] = dict(feat["properties"])
        f2["properties"]["panel_id"] = panel_id
        features.append(f2)
    logger.info("NL GeoJSON: %d features", len(features))
    return {"type": "FeatureCollection", "features": features}


def build_territory_data(panel: pd.DataFrame) -> tuple[dict, dict]:
    """Nested {country: {region_id: {sector: {year: [value, state_num, velocity]}}}}
    plus per-region metadata, deduplicated (not per-row) to keep payload small."""
    territory_data: dict = {}
    region_meta: dict = {}

    for (country, region_id), grp in panel.groupby(["country", "region_id"], sort=False):
        region_id = str(region_id)
        first = grp.iloc[0]
        territory_data.setdefault(country, {})
        territory_data[country].setdefault(region_id, {})
        region_meta.setdefault(country, {})
        region_meta[country][region_id] = {
            "name": str(first.get("region_name", "") or region_id),
            "region_system": first["region_system"],
            "evidence_type": first["evidence_type"],
            "source_table": first["source_table"],
            "allowed_use": first["allowed_use"],
        }
        for sector, grp_s in grp.groupby("sector_a10", sort=False):
            territory_data[country][region_id].setdefault(sector, {})
            for _, row in grp_s.iterrows():
                state_num = STATE_NUM.get(row["state"])  # None => insufficient data
                vel = row["velocity"]
                val = row["value"]
                territory_data[country][region_id][sector][int(row["year"])] = [
                    None if pd.isna(val) else round(float(val), 3),
                    state_num,
                    None if pd.isna(vel) else round(float(vel), 4),
                ]
    return territory_data, region_meta


def build_node_positions() -> dict:
    node_pos = {}
    for i, s in enumerate(SECTORS_ORDER):
        angle = 2 * math.pi * i / len(SECTORS_ORDER) - math.pi / 2
        node_pos[s] = {"x": round(math.cos(angle), 4), "y": round(math.sin(angle), 4)}
    return node_pos


def main() -> None:
    panel = pd.read_csv(TERRITORY_PATH, low_memory=False)
    relation_edges = pd.read_csv(RELATION_PATH)
    blocked_edges = pd.read_csv(BLOCKED_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text())

    # Hard invariant checks (fail closed, must never regress)
    assert "GEMEENTE_PROXY" not in relation_edges["region_system"].values, \
        "FAIL_CLOSED: NL gemeente proxy must never appear in relation edges"
    assert relation_edges["evidence_type"].eq("observed_births").all(), \
        "FAIL_CLOSED: relation edges must be observed_births only"
    assert (blocked_edges["allowed_for_training_label"] == False).all(), \
        "FAIL_CLOSED: blocked proxy edges must have allowed_for_training_label=false"

    territory_data, region_meta = build_territory_data(panel)
    node_pos = build_node_positions()

    fr_ids = sorted(panel[panel["country"] == "FR"]["region_id"].astype(str).unique())
    geo_fr = _build_fr_geojson(fr_ids)
    geo_nl = _build_nl_geojson()

    plotly_tag, plotly_dep = _plotly_js_tag()

    # ── Evidence counts (Section 5) ──────────────────────────────────────
    label_counts = relation_edges["label_class"].value_counts().to_dict()
    n_observed_relation_edges = len(relation_edges)
    n_proxy_context_rows = int((panel["evidence_type"] == "proxy_disaggregated_by_stock_share").sum())
    n_blocked = len(blocked_edges)

    relation_edges_js = relation_edges.to_dict(orient="records")
    blocked_edges_js = blocked_edges.to_dict(orient="records")

    csv_checksums = {
        "granular_territory_state_panel.csv": _sha256_file(TERRITORY_PATH)[:16],
        "granular_relation_edges.csv": _sha256_file(RELATION_PATH)[:16],
        "blocked_proxy_edges.csv": _sha256_file(BLOCKED_PATH)[:16],
    }

    html = _render_html(
        plotly_tag=plotly_tag,
        plotly_dep=plotly_dep,
        territory_data_js=json.dumps(territory_data, separators=(",", ":")),
        region_meta_js=json.dumps(region_meta, separators=(",", ":")),
        node_pos_js=json.dumps(node_pos),
        sector_labels_js=json.dumps(SECTOR_LABELS),
        geo_fr_js=json.dumps(geo_fr, separators=(",", ":")),
        geo_nl_js=json.dumps(geo_nl, separators=(",", ":")),
        relation_edges_js=json.dumps(relation_edges_js),
        blocked_edges_js=json.dumps(blocked_edges_js),
        manifest_js=json.dumps(manifest),
        map_config_js=json.dumps(MAP_CONFIG),
        table_config_js=json.dumps(TABLE_CONFIG),
        label_counts_js=json.dumps(label_counts),
        csv_checksums_js=json.dumps(csv_checksums),
        n_observed_relation_edges=n_observed_relation_edges,
        n_proxy_context_rows=n_proxy_context_rows,
        n_blocked=n_blocked,
        n_territory_rows=len(panel),
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(OUT_PATH, html)
    size_mb = OUT_PATH.stat().st_size / 1e6
    logger.info("Wrote %s (%.2f MB)", OUT_PATH, size_mb)
    if size_mb > 20:
        logger.warning("Dashboard exceeds 20 MB (%.2f MB) — document in report", size_mb)


def _render_html(**kw) -> str:
    plotly_tag = kw["plotly_tag"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD Observatory v0.4 — Granular</title>
{plotly_tag}
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --good:#26a69a; --bad:#ef5350;
    --stag:#9aa4bf; --pos:#26a69a; --neg:#ef5350;
    --robust:#4aa3ff; --fine:#b084f5; --explor:#ffd180;
    --observed:#26a69a; --proxy:#ffb74d;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;font-size:14px;}}
  .wrap{{max-width:1600px;margin:0 auto;padding:20px;}}
  h1{{font-size:24px;font-weight:760;margin-bottom:6px;}}
  .subtitle{{color:var(--muted);font-size:13px;line-height:1.5;max-width:1100px;margin-bottom:10px;}}
  .header-badges{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;}}
  .decision-badge{{display:inline-block;background:#0a2e1a;border:1px solid var(--good);
    color:var(--good);border-radius:6px;padding:4px 10px;font-size:12px;font-weight:700;}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:0 0 18px;}}
  .kpi{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;}}
  .kpi .v{{font-size:20px;font-weight:760;}}
  .kpi .l{{color:var(--muted);font-size:11px;margin-top:2px;}}
  .section{{margin-top:24px;}}
  .section-title{{font-size:17px;font-weight:720;margin-bottom:4px;}}
  .section-note{{color:var(--muted);font-size:12px;line-height:1.45;max-width:1100px;margin-bottom:8px;}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px;}}
  .controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;}}
  select,button,input{{background:var(--panel2);color:var(--text);border:1px solid var(--line);
    border-radius:5px;padding:5px 9px;font-size:12px;cursor:pointer;}}
  .map-layout{{display:grid;grid-template-columns:1fr 360px;gap:12px;align-items:start;}}
  .side-panel{{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:14px;}}
  .side-panel h3{{font-size:14px;font-weight:720;margin-bottom:8px;}}
  .side-field{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:12px;gap:8px;}}
  .side-field .lbl{{color:var(--muted);flex-shrink:0;}}
  .side-empty{{color:var(--muted);font-size:12px;padding:16px 0;text-align:center;}}
  .badge{{display:inline-block;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:700;border:1px solid;}}
  .badge-observed{{color:var(--observed);border-color:var(--observed);background:#0a1e1a;}}
  .badge-proxy{{color:var(--proxy);border-color:var(--proxy);background:#241a0a;}}
  .badge-robust{{color:var(--robust);border-color:var(--robust);background:#0a1a2e;}}
  .badge-fine{{color:var(--fine);border-color:var(--fine);background:#1a0a2e;}}
  .badge-explor{{color:var(--explor);border-color:var(--explor);background:#1e1a0a;}}
  .badge-pos{{color:var(--pos);border-color:var(--pos);background:#0a1e1a;}}
  .badge-neg{{color:var(--neg);border-color:var(--neg);background:#1e0a0a;}}
  .badge-blocked{{color:var(--bad);border-color:var(--bad);background:#1e0a0a;}}
  .graph-layout{{display:grid;grid-template-columns:1fr 320px;gap:12px;}}
  .legend-row{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:7px;font-size:12px;}}
  .legend-item{{display:flex;align-items:center;gap:4px;color:var(--muted);}}
  .legend-dot{{width:11px;height:11px;border-radius:50%;flex-shrink:0;}}
  .legend-line{{width:22px;height:3px;flex-shrink:0;}}
  .warn-box{{background:#1a1206;border:1px solid #7a5c10;border-radius:6px;padding:8px 12px;
    font-size:12px;color:#ffd180;margin-bottom:8px;}}
  .blocked-box{{background:#1e0a0a;border:1px solid #7a1010;border-radius:6px;padding:10px 12px;
    font-size:12px;color:#ffb3ab;margin-bottom:8px;}}
  table.dense{{width:100%;border-collapse:collapse;font-size:12px;}}
  table.dense th{{text-align:left;color:var(--muted);font-weight:600;padding:6px 8px;
    border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);cursor:pointer;}}
  table.dense td{{padding:5px 8px;border-bottom:1px solid #232842;}}
  table.dense tbody tr:hover{{background:var(--panel2);}}
  .scroll-table{{max-height:420px;overflow-y:auto;}}
  .state-growth{{color:var(--good);}}
  .state-decline{{color:var(--bad);}}
  .state-stagnation{{color:var(--stag);}}
  .state-insufficient{{color:#4a4f6a;}}
  .modal-overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:50;
    align-items:center;justify-content:center;}}
  .modal-overlay.open{{display:flex;}}
  .modal-box{{background:var(--panel);border:1px solid var(--line);border-radius:8px;
    padding:16px;max-width:700px;max-height:80vh;overflow:auto;}}
  .modal-box pre{{font-size:11px;white-space:pre-wrap;color:var(--muted);}}
  .links-row{{display:flex;flex-wrap:wrap;gap:8px;}}
  .links-row a{{color:var(--robust);text-decoration:none;font-size:12px;border:1px solid var(--line);
    border-radius:5px;padding:6px 10px;background:var(--panel2);}}
  @media(max-width:950px){{
    .map-layout,.graph-layout{{grid-template-columns:1fr;}}
    .kpis{{grid-template-columns:repeat(2,1fr);}}
  }}
</style>
</head>
<body>
<div class="wrap">

<h1>HERALD Observatory <span style="color:var(--robust);font-size:15px">v0.4</span> — Granular Territorial Economic Dynamics</h1>
<div class="subtitle">
  FR ZE2020 / PT Municipality / NL COROP observed evidence, plus NL gemeente proxy territorial context.
  Sector relations express <em>statistical association / predictive precedence</em> only — no structural-causal claim.
  See <code>reports/HERALD_GRANULAR_EVIDENCE_POLICY.md</code> and DEC-063/064/065/066.
</div>
<div class="header-badges">
  <span class="badge badge-observed">FR ZE2020 observed</span>
  <span class="badge badge-observed">PT municipality observed</span>
  <span class="badge badge-observed">NL COROP observed</span>
  <span class="badge badge-proxy">NL gemeente proxy/context</span>
  <span class="decision-badge">GRANULAR_OBSERVATORY_V04_DATA_READY</span>
</div>

<div class="kpis" id="kpi-bar"></div>

<!-- ── SECTION 1: Territorial Map ─────────────────────────────────────── -->
<div class="section">
  <div class="section-title">1. Territorial Map / State</div>
  <div class="section-note">
    FR (ZE2020) and NL (COROP) render as a choropleth map (geometry available).
    PT (Municipality) and NL gemeente have no embedded municipal/gemeente geometry —
    they render as a sortable, colour-coded table (state heatmap), not a fabricated map.
    NL gemeente rows always carry a <span class="badge badge-proxy" style="padding:1px 6px">proxy/context</span>
    badge — they are a territorial estimate, never observed evidence.
  </div>
  <div class="controls">
    <label>Source
      <select id="map-source" onchange="handleSourceChange()">
        <option value="FR">France — ZE2020 (observed, map)</option>
        <option value="NL">Netherlands — COROP (observed, map)</option>
        <option value="PT">Portugal — Municipality (observed, table)</option>
        <option value="NL_GEMEENTE">Netherlands — Gemeente (proxy/context, table)</option>
      </select>
    </label>
    <label>Year <select id="map-year" onchange="renderTerritoryView()"></select></label>
    <label>Sector
      <select id="map-sector" onchange="renderTerritoryView()">
        <option value="ALL">All sectors (dominant shown)</option>
        {"".join(f'<option value="{s}">{s} — {SECTOR_LABELS[s]}</option>' for s in SECTORS_ORDER)}
      </select>
    </label>
    <label>Metric
      <select id="map-metric" onchange="renderTerritoryView()">
        <option value="state">State</option>
        <option value="velocity">Velocity</option>
      </select>
    </label>
    <span id="map-evidence-badge"></span>
    <span id="map-terr-count" style="color:var(--muted);font-size:12px;"></span>
  </div>
  <div class="legend-row" id="map-legend"></div>
  <div class="map-layout">
    <div class="card" id="map-card" style="min-height:520px"><div id="map-plot" style="height:520px"></div></div>
    <div class="side-panel" id="map-side">
      <h3>Territory detail</h3>
      <div class="side-empty" id="map-side-empty">Select a territory to see its sector trajectory and ranking.</div>
      <div id="map-side-content" style="display:none"></div>
    </div>
  </div>
</div>

<!-- ── SECTION 2: Sector Relation Graph ───────────────────────────────── -->
<div class="section">
  <div class="section-title">2. Sector → Sector Relation Graph (observed evidence only)</div>
  <div class="section-note">
    Source: <code>granular_relation_edges.csv</code> ONLY — FR ZE2020 / PT Municipality / NL COROP
    observed evidence. NL gemeente proxy edges are structurally excluded from this graph (see Section 3).
    A directed edge A → B expresses statistical association / predictive precedence between lagged
    growth in A and growth in B, not a structural-causal mechanism.
  </div>
  <div class="warn-box">
    Style: solid = ROBUST_ORIGINAL, dashed = FINE_GRAIN_SUPPORTED, dotted/low-opacity = EXPLORATORY_FINE_GRAIN (not a training label).
    Colour: positive association = blue/green, negative association = red/orange. Width ∝ |β|.
  </div>
  <div class="controls">
    <label>Country <select id="graph-country" onchange="renderGraph()">
      <option value="ALL">All countries</option>
      <option value="FR">France</option>
      <option value="NL">Netherlands</option>
      <option value="PT">Portugal</option>
    </select></label>
    <label>Region system <select id="graph-region-system" onchange="renderGraph()">
      <option value="ALL">All</option>
      <option value="ZE2020">ZE2020</option>
      <option value="COROP">COROP</option>
      <option value="MUNICIPALITY">Municipality</option>
    </select></label>
    <label>Label class <select id="graph-label-class" onchange="renderGraph()">
      <option value="ALL">All</option>
      <option value="ROBUST_ORIGINAL">ROBUST_ORIGINAL</option>
      <option value="FINE_GRAIN_SUPPORTED">FINE_GRAIN_SUPPORTED</option>
      <option value="EXPLORATORY_FINE_GRAIN">EXPLORATORY_FINE_GRAIN</option>
    </select></label>
    <label>Window <select id="graph-window" onchange="renderGraph()"><option value="ALL">All windows</option></select></label>
    <span id="edge-count-label" style="color:var(--muted);font-size:12px;"></span>
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:var(--pos)"></div>Positive</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--neg)"></div>Negative</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--robust)"></div>ROBUST_ORIGINAL</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--fine);opacity:.8"></div>FINE_GRAIN_SUPPORTED</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--explor);opacity:.5"></div>EXPLORATORY_FINE_GRAIN</div>
  </div>
  <div class="graph-layout">
    <div class="card"><div id="sector-graph" style="height:480px"></div></div>
    <div class="side-panel" id="edge-panel">
      <h3>Edge detail</h3>
      <div class="side-empty" id="edge-panel-empty">Click an edge or node to see detail.</div>
      <div id="edge-panel-content" style="display:none"></div>
    </div>
  </div>
</div>

<!-- ── SECTION 3: Blocked proxy artifacts ─────────────────────────────── -->
<div class="section">
  <div class="section-title">3. Blocked Proxy Artifacts (NL gemeente proxy)</div>
  <div class="blocked-box">
    DEC-065: 121 NL gemeente proxy edges were nominally promoted by automated gate-counts but
    are structurally invalid — the stock-share weighting term injects cross-sector-correlated
    noise unrelated to births precedence (decomposition regression: share_velocity coefficient
    ≈13.0 vs corop_velocity ≈1.33; cross-sector correlation 0.34–0.82). These edges are
    <strong>preserved for audit only and are not used for training or claims.</strong>
    They never appear in the Section 2 relation graph.
  </div>
  <div class="controls">
    <span class="badge badge-blocked">BLOCKED_PROXY_ARTIFACT — {kw['n_blocked']} edges</span>
    <span style="color:var(--muted);font-size:12px;">reason = stock_share_induced_artifact · allowed_for_training_label = false</span>
  </div>
  <div class="card scroll-table">
    <table class="dense" id="blocked-table">
      <thead><tr><th>source_sector</th><th>target_sector</th><th>beta</th><th>window</th><th>reason</th><th>allowed_for_training_label</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ── SECTION 4: Evidence panel ───────────────────────────────────────── -->
<div class="section">
  <div class="section-title">4. Evidence Summary</div>
  <div class="kpis" id="evidence-kpis"></div>
  <div class="card">
    <div class="side-field"><span class="lbl">DEC references</span><span id="dec-refs"></span></div>
    <div class="side-field"><span class="lbl">territory_state_panel checksum (16)</span><span id="chk-territory"></span></div>
    <div class="side-field"><span class="lbl">relation_edges checksum (16)</span><span id="chk-relation"></span></div>
    <div class="side-field"><span class="lbl">blocked_proxy_edges checksum (16)</span><span id="chk-blocked"></span></div>
  </div>
</div>

<!-- ── SECTION 5: Export / sources ─────────────────────────────────────── -->
<div class="section">
  <div class="section-title">5. Sources / Export</div>
  <div class="links-row">
    <a href="../../data/processed/herald_observatory_v04_granular/granular_territory_state_panel.csv">granular_territory_state_panel.csv</a>
    <a href="../../data/processed/herald_observatory_v04_granular/granular_relation_edges.csv">granular_relation_edges.csv</a>
    <a href="../../data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv">blocked_proxy_edges.csv</a>
    <a href="../../data/processed/herald_observatory_v04_granular/manifest.json">manifest.json</a>
    <button onclick="openManifestModal()">Show manifest (embedded)</button>
  </div>
  <div style="color:var(--muted);font-size:11px;margin-top:8px;">
    Plotly dependency: {kw['plotly_dep']}.
    {"Embedded locally — works fully offline." if kw['plotly_dep']=="local_embedded" else "CDN fallback — requires internet to render plots."}
  </div>
</div>

</div>

<div class="modal-overlay" id="manifest-modal" onclick="if(event.target===this) closeManifestModal()">
  <div class="modal-box">
    <h3 style="margin-bottom:8px">manifest.json</h3>
    <pre id="manifest-pre"></pre>
    <button onclick="closeManifestModal()" style="margin-top:8px">Close</button>
  </div>
</div>

<script>
const TERRITORY_DATA = {kw['territory_data_js']};
const REGION_META = {kw['region_meta_js']};
const NODE_POS = {kw['node_pos_js']};
const SECTOR_LABELS = {kw['sector_labels_js']};
const GEO_FR = {kw['geo_fr_js']};
const GEO_NL = {kw['geo_nl_js']};
const GEO = {{FR: GEO_FR, NL: GEO_NL}};
const RELATION_EDGES = {kw['relation_edges_js']};
const BLOCKED_EDGES = {kw['blocked_edges_js']};
const MANIFEST = {kw['manifest_js']};
const MAP_CONFIG = {kw['map_config_js']};
const TABLE_CONFIG = {kw['table_config_js']};
const LABEL_COUNTS = {kw['label_counts_js']};
const CSV_CHECKSUMS = {kw['csv_checksums_js']};
const N_OBSERVED_RELATION_EDGES = {kw['n_observed_relation_edges']};
const N_PROXY_CONTEXT_ROWS = {kw['n_proxy_context_rows']};
const N_BLOCKED = {kw['n_blocked']};
const N_TERRITORY_ROWS = {kw['n_territory_rows']};

const SECTORS = {json.dumps(SECTORS_ORDER)};
const STATE_COLORS = {{1:'#26a69a', 0:'#9aa4bf', '-1':'#ef5350'}};
const STATE_LABELS = {{1:'GROWTH', 0:'STAGNATION', '-1':'DECLINE'}};
const STATE_COLORSCALE = [[0,'#ef5350'],[0.5,'#9aa4bf'],[1,'#26a69a']];
const VEL_COLORSCALE = [[0,'#ef5350'],[0.5,'#9aa4bf'],[1,'#26a69a']];
const BASE_LAYOUT = {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font:{{color:'#eef2ff',family:'Inter,Segoe UI,Arial,sans-serif',size:12}},
  margin:{{l:50,r:20,t:30,b:40}},
  hoverlabel:{{bgcolor:'#20253a',bordercolor:'#30364f',font:{{color:'#eef2ff'}}}},
}};

// ── KPI bar ──────────────────────────────────────────────────────────────
function renderKpis() {{
  const items = [
    ['Territory rows', N_TERRITORY_ROWS.toLocaleString()],
    ['Observed relation edges', N_OBSERVED_RELATION_EDGES],
    ['Proxy context rows', N_PROXY_CONTEXT_ROWS.toLocaleString()],
    ['Blocked proxy edges', N_BLOCKED],
  ];
  document.getElementById('kpi-bar').innerHTML = items.map(([l,v])=>
    `<div class="kpi"><div class="v">${{v}}</div><div class="l">${{l}}</div></div>`).join('');

  const evItems = [
    ['Observed relation edges', N_OBSERVED_RELATION_EDGES],
    ['Proxy context rows', N_PROXY_CONTEXT_ROWS.toLocaleString()],
    ['Blocked proxy edges', N_BLOCKED],
    ['ROBUST_ORIGINAL', LABEL_COUNTS['ROBUST_ORIGINAL']||0],
    ['FINE_GRAIN_SUPPORTED', LABEL_COUNTS['FINE_GRAIN_SUPPORTED']||0],
    ['EXPLORATORY_FINE_GRAIN', LABEL_COUNTS['EXPLORATORY_FINE_GRAIN']||0],
  ];
  document.getElementById('evidence-kpis').innerHTML = evItems.map(([l,v])=>
    `<div class="kpi"><div class="v">${{v}}</div><div class="l">${{l}}</div></div>`).join('');

  document.getElementById('dec-refs').textContent = (MANIFEST.dec_references||[]).join(', ');
  document.getElementById('chk-territory').textContent = CSV_CHECKSUMS['granular_territory_state_panel.csv'];
  document.getElementById('chk-relation').textContent = CSV_CHECKSUMS['granular_relation_edges.csv'];
  document.getElementById('chk-blocked').textContent = CSV_CHECKSUMS['blocked_proxy_edges.csv'];
}}

// ── Section 1: Territory map / table ────────────────────────────────────
function populateYearOptions(source) {{
  const yearSel = document.getElementById('map-year');
  const years = new Set();
  const regions = TERRITORY_DATA[source==='NL_GEMEENTE' ? 'NL' : source] || {{}};
  Object.values(regions).forEach(secMap => Object.values(secMap).forEach(yearMap =>
    Object.keys(yearMap).forEach(y => years.add(parseInt(y)))));
  const sorted = [...years].sort((a,b)=>b-a);
  yearSel.innerHTML = sorted.map(y=>`<option value="${{y}}">${{y}}</option>`).join('');
}}

function regionsForSource(source) {{
  // NL_GEMEENTE and NL (COROP) share country key 'NL' in TERRITORY_DATA; disambiguate by region_system
  const country = source === 'NL_GEMEENTE' ? 'NL' : source;
  const all = TERRITORY_DATA[country] || {{}};
  const wantSystem = source === 'NL_GEMEENTE' ? 'GEMEENTE_PROXY'
    : (source === 'NL' ? 'COROP' : (MAP_CONFIG[source]||{{}}).region_system || (TABLE_CONFIG[source]||{{}}).region_system);
  const metaAll = REGION_META[country] || {{}};
  const out = {{}};
  Object.keys(all).forEach(rid => {{
    if ((metaAll[rid]||{{}}).region_system === wantSystem) out[rid] = all[rid];
  }});
  return out;
}}

function handleSourceChange() {{
  const source = document.getElementById('map-source').value;
  populateYearOptions(source);
  renderTerritoryView();
}}

function renderTerritoryView() {{
  const source = document.getElementById('map-source').value;
  const isMapped = source === 'FR' || source === 'NL';
  document.getElementById('map-card').innerHTML = isMapped
    ? '<div id="map-plot" style="height:520px"></div>'
    : '<div class="scroll-table"><table class="dense" id="territory-table"><thead><tr>'
      + '<th onclick="sortTable(0)">region_id</th><th onclick="sortTable(1)">name</th>'
      + '<th onclick="sortTable(2)">sector</th><th onclick="sortTable(3)">value</th>'
      + '<th onclick="sortTable(4)">state</th><th onclick="sortTable(5)">velocity</th>'
      + '<th>evidence_type</th><th>allowed_use</th></tr></thead><tbody></tbody></table></div>';

  const cfg = MAP_CONFIG[source] || TABLE_CONFIG[source];
  const badgeClass = (TABLE_CONFIG[source]||{{}}).badge === 'proxy' || source==='NL_GEMEENTE' ? 'badge-proxy' : 'badge-observed';
  const badgeText = badgeClass === 'badge-proxy' ? 'proxy/context — not valid for relation labels' : 'observed';
  document.getElementById('map-evidence-badge').innerHTML = `<span class="badge ${{badgeClass}}">${{badgeText}}</span>`;

  if (isMapped) renderMap(source); else renderTerritoryTable(source);
}}

function renderMap(source) {{
  const year = parseInt(document.getElementById('map-year').value);
  const sector = document.getElementById('map-sector').value;
  const metric = document.getElementById('map-metric').value;
  const regions = regionsForSource(source);
  const meta = REGION_META[source] || {{}};
  const geo = GEO[source];

  const locations = [], z = [], text = [], customdata = [];
  Object.keys(regions).forEach(rid => {{
    const secMap = regions[rid];
    let shownSector = sector, cell = null;
    if (sector === 'ALL') {{
      let best = null, bestAbs = -1;
      Object.keys(secMap).forEach(s => {{
        const yd = secMap[s][year];
        if (yd && yd[2] != null && Math.abs(yd[2]) > bestAbs) {{ bestAbs = Math.abs(yd[2]); best = s; cell = yd; }}
      }});
      shownSector = best;
    }} else {{
      cell = (secMap[sector]||{{}})[year];
    }}
    locations.push(rid);
    const name = (meta[rid]||{{}}).name || rid;
    if (!cell) {{
      z.push(null);
      customdata.push({{rid, name, sector: shownSector, year, value:null, state:null, vel:null,
        evidence_type:(meta[rid]||{{}}).evidence_type, source_table:(meta[rid]||{{}}).source_table,
        allowed_use:(meta[rid]||{{}}).allowed_use}});
      text.push(name + ': no data');
      return;
    }}
    const [value, stateNum, vel] = cell;
    z.push(metric === 'state' ? stateNum : vel);
    customdata.push({{rid, name, sector: shownSector, year, value, state: STATE_LABELS[stateNum], vel,
      evidence_type:(meta[rid]||{{}}).evidence_type, source_table:(meta[rid]||{{}}).source_table,
      allowed_use:(meta[rid]||{{}}).allowed_use}});
    text.push(name + '<br>sector=' + (shownSector||'') + '<br>state=' + (STATE_LABELS[stateNum]||'n/a')
      + (vel!=null ? '<br>vel=' + vel.toFixed(3) : ''));
  }});

  const colorscale = metric === 'state' ? STATE_COLORSCALE : VEL_COLORSCALE;

  const trace = {{
    type:'choropleth', geojson: geo, featureidkey:'properties.panel_id',
    locations, z, text, customdata, colorscale,
    zmin: metric==='state' ? -1 : undefined, zmax: metric==='state' ? 1 : undefined,
    zmid: metric==='velocity' ? 0 : undefined,
    colorbar:{{title: metric==='state' ? 'State' : 'Velocity', tickfont:{{color:'#eef2ff',size:10}}, thickness:14, len:0.8}},
    hovertemplate:'%{{text}}<extra></extra>',
    marker:{{line:{{width:0.5, color:'#30364f'}}}}, showscale:true,
  }};
  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    geo:{{fitbounds:'geojson', visible:false, bgcolor:'#0f1220', showframe:false, showcoastlines:false}},
    margin:{{l:0,r:0,t:30,b:0}},
    title:{{text: source + ' — ' + year + ' — ' + (sector==='ALL'?'all sectors':sector) + ' — ' + metric,
      font:{{size:13,color:'#eef2ff'}}}},
  }});
  Plotly.newPlot('map-plot', [trace], layout, {{responsive:true, displayModeBar:false}});
  document.getElementById('map-plot').on('plotly_click', function(data) {{
    const pt = data.points[0];
    if (pt && pt.customdata) showTerritorySidePanel(source, pt.customdata);
  }});
  renderMapLegend(metric);
  document.getElementById('map-terr-count').textContent = locations.length + ' territories';
}}

function renderTerritoryTable(source) {{
  const year = parseInt(document.getElementById('map-year').value);
  const sector = document.getElementById('map-sector').value;
  const regions = regionsForSource(source);
  const meta = REGION_META[source==='NL_GEMEENTE'?'NL':source] || {{}};
  const rows = [];
  Object.keys(regions).forEach(rid => {{
    const secMap = regions[rid];
    const m = meta[rid] || {{}};
    const sectorsToShow = sector === 'ALL' ? Object.keys(secMap) : [sector];
    sectorsToShow.forEach(s => {{
      const cell = (secMap[s]||{{}})[year];
      if (!cell) return;
      const [value, stateNum, vel] = cell;
      rows.push([rid, m.name||rid, s, value, STATE_LABELS[stateNum]||'INSUFFICIENT', vel, m.evidence_type, m.allowed_use]);
    }});
  }});
  rows.sort((a,b)=> (b[3]||0)-(a[3]||0));
  const tbody = document.querySelector('#territory-table tbody');
  tbody.innerHTML = rows.slice(0,500).map(r => {{
    const stCls = r[4]==='GROWTH'?'state-growth':r[4]==='DECLINE'?'state-decline':r[4]==='STAGNATION'?'state-stagnation':'state-insufficient';
    return `<tr onclick='showTerritorySidePanel(${{JSON.stringify(source)}},{{rid:${{JSON.stringify(r[0])}},name:${{JSON.stringify(r[1])}},sector:${{JSON.stringify(r[2])}},year:${{year}},value:${{r[3]}},state:${{JSON.stringify(r[4])}},vel:${{r[5]}},evidence_type:${{JSON.stringify(r[6])}},source_table:"",allowed_use:${{JSON.stringify(r[7])}}}})'>`
      + `<td>${{r[0]}}</td><td>${{r[1]}}</td><td>${{r[2]}}</td><td>${{r[3]!=null?r[3].toFixed(1):''}}</td>`
      + `<td class="${{stCls}}">${{r[4]}}</td><td>${{r[5]!=null?r[5].toFixed(3):''}}</td>`
      + `<td>${{r[6]}}</td><td>${{r[7]}}</td></tr>`;
  }}).join('');
  document.getElementById('map-terr-count').textContent = rows.length + ' rows (showing up to 500, sorted by value desc)';
  renderMapLegend(document.getElementById('map-metric').value);
}}

let SORT_DIR = {{}};
function sortTable(colIdx) {{
  const tbody = document.querySelector('#territory-table tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const dir = SORT_DIR[colIdx] = !SORT_DIR[colIdx];
  rows.sort((a,b) => {{
    const av = a.children[colIdx].textContent, bv = b.children[colIdx].textContent;
    const an = parseFloat(av), bn = parseFloat(bv);
    const cmp = (!isNaN(an) && !isNaN(bn)) ? an-bn : av.localeCompare(bv);
    return dir ? cmp : -cmp;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

function renderMapLegend(metric) {{
  const el = document.getElementById('map-legend');
  if (metric === 'state') {{
    el.innerHTML = Object.entries(STATE_LABELS).map(([k,s])=>
      `<div class="legend-item"><div class="legend-dot" style="background:${{STATE_COLORS[k]}}"></div>${{s}}</div>`).join('')
      + `<div class="legend-item"><div class="legend-dot" style="background:#4a4f6a"></div>INSUFFICIENT_DATA</div>`;
  }} else {{
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Negative</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>~0</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Positive</div>`;
  }}
}}

function showTerritorySidePanel(source, cd) {{
  const country = source === 'NL_GEMEENTE' ? 'NL' : source;
  const regions = regionsForSource(source);
  const secMap = regions[cd.rid] || {{}};
  const meta = (REGION_META[country]||{{}})[cd.rid] || {{}};
  const badge = meta.evidence_type === 'proxy_disaggregated_by_stock_share'
    ? '<span class="badge badge-proxy">proxy/context</span>' : '<span class="badge badge-observed">observed</span>';

  // Time series for selected sector
  const sector = cd.sector || Object.keys(secMap)[0];
  const years = Object.keys(secMap[sector]||{{}}).map(Number).sort();
  const seriesY = years, seriesV = years.map(y => secMap[sector][y][2]);

  // Ranking of sectors in this territory for the displayed year
  const ranking = Object.keys(secMap).map(s => {{
    const cell = secMap[s][cd.year];
    return cell ? {{sector:s, vel:cell[2]}} : null;
  }}).filter(Boolean).sort((a,b)=>(b.vel||0)-(a.vel||0));

  document.getElementById('map-side-empty').style.display = 'none';
  const content = document.getElementById('map-side-content');
  content.style.display = 'block';
  content.innerHTML = `
    <div style="margin-bottom:8px">${{badge}}</div>
    <div class="side-field"><span class="lbl">Territory</span><span>${{cd.name}}</span></div>
    <div class="side-field"><span class="lbl">Region system</span><span>${{meta.region_system||''}}</span></div>
    <div class="side-field"><span class="lbl">Sector</span><span>${{sector}} — ${{SECTOR_LABELS[sector]||''}}</span></div>
    <div class="side-field"><span class="lbl">Year</span><span>${{cd.year}}</span></div>
    <div class="side-field"><span class="lbl">Value</span><span>${{cd.value!=null?cd.value:'n/a'}}</span></div>
    <div class="side-field"><span class="lbl">State</span><span>${{cd.state||'n/a'}}</span></div>
    <div class="side-field"><span class="lbl">Velocity</span><span>${{cd.vel!=null?cd.vel.toFixed(3):'n/a'}}</span></div>
    <div class="side-field"><span class="lbl">Source dataset</span><span style="font-size:10px">${{meta.source_table||''}}</span></div>
    <div class="side-field"><span class="lbl">Allowed use</span><span style="font-size:10px">${{meta.allowed_use||''}}</span></div>
    <div id="ts-plot" style="height:140px;margin-top:8px"></div>
    <h3 style="margin-top:10px">Sector ranking (this territory, ${{cd.year}})</h3>
    <table class="dense">${{ranking.map(r=>`<tr><td>${{r.sector}}</td><td>${{r.vel!=null?r.vel.toFixed(3):'n/a'}}</td></tr>`).join('')}}</table>
  `;
  Plotly.newPlot('ts-plot', [{{x:seriesY, y:seriesV, type:'scatter', mode:'lines+markers',
    line:{{color:'#4aa3ff'}}, marker:{{size:4}}}}],
    Object.assign({{}}, BASE_LAYOUT, {{margin:{{l:30,r:10,t:10,b:20}},
      xaxis:{{tickfont:{{size:9}}}}, yaxis:{{title:'velocity',tickfont:{{size:9}},titlefont:{{size:9}}}}}}),
    {{responsive:true, displayModeBar:false}});
}}

// ── Section 2: Sector graph ──────────────────────────────────────────────
function populateWindowOptions() {{
  const windows = [...new Set(RELATION_EDGES.map(e=>e.window))].sort();
  const sel = document.getElementById('graph-window');
  sel.innerHTML = '<option value="ALL">All windows</option>' + windows.map(w=>`<option value="${{w}}">${{w}}</option>`).join('');
}}

function renderGraph() {{
  const country = document.getElementById('graph-country').value;
  const regionSystem = document.getElementById('graph-region-system').value;
  const labelClass = document.getElementById('graph-label-class').value;
  const window_ = document.getElementById('graph-window').value;

  const filtered = RELATION_EDGES.filter(e => {{
    if (country !== 'ALL' && e.country !== country) return false;
    if (regionSystem !== 'ALL' && e.region_system !== regionSystem) return false;
    if (labelClass !== 'ALL' && e.label_class !== labelClass) return false;
    if (window_ !== 'ALL' && e.window !== window_) return false;
    return true;
  }});

  const pairIdx = {{}};
  const annotations = [], edgeTraces = [];
  filtered.forEach((e,i) => {{
    const sp = NODE_POS[e.source_sector], tp = NODE_POS[e.target_sector];
    if (!sp || !tp) return;
    const key = e.source_sector+'->'+e.target_sector;
    pairIdx[key] = (pairIdx[key]||0)+1;
    const hasRev = filtered.some(e2=>e2.source_sector===e.target_sector&&e2.target_sector===e.source_sector);
    const off = hasRev ? (pairIdx[key]%2===0?1:-1)*0.06 : 0;
    const dx=tp.x-sp.x, dy=tp.y-sp.y, dist=Math.sqrt(dx*dx+dy*dy)||1;
    const ux=dx/dist, uy=dy/dist, r=0.15;
    const px=-uy*off, py=ux*off;
    const ax=sp.x+ux*r+px, ay=sp.y+uy*r+py, x=tp.x-ux*r+px, y=tp.y-uy*r+py;
    const col = e.sign==='+' ? '#26a69a' : '#ef5350';
    const w = 1+Math.abs(e.beta||0)*10;
    const dash = e.label_class==='ROBUST_ORIGINAL' ? 'solid' : e.label_class==='FINE_GRAIN_SUPPORTED' ? 'dash' : 'dot';
    const opacity = e.label_class==='ROBUST_ORIGINAL' ? 0.95 : e.label_class==='FINE_GRAIN_SUPPORTED' ? 0.8 : 0.45;
    edgeTraces.push({{
      x:[ax,x,null], y:[ay,y,null], mode:'lines', type:'scatter',
      line:{{color:col,width:w,dash}}, opacity,
      hovertemplate:`<b>${{e.source_sector}}→${{e.target_sector}}</b> (${{e.country}}/${{e.region_system}})<br>`+
        `β=${{e.beta.toFixed(3)}} sign=${{e.sign}}<br>q_fdr=${{e.q_fdr.toFixed(3)}} bss=${{e.bss.toFixed(3)}}<br>`+
        `window=${{e.window}}<br>label_class=${{e.label_class}}<br>evidence_type=${{e.evidence_type}}<br>`+
        `allowed_for_training_label=${{e.allowed_for_training_label}}<extra></extra>`,
      customdata:[i], showlegend:false, name:key,
    }});
    annotations.push({{x,y,ax,ay,xref:'x',yref:'y',axref:'x',ayref:'y',
      showarrow:true,arrowhead:2,arrowsize:1.1,arrowwidth:Math.max(1.3,w*0.6),
      arrowcolor:col,opacity}});
  }});

  const nodeTrace = {{
    x:SECTORS.map(s=>NODE_POS[s].x), y:SECTORS.map(s=>NODE_POS[s].y),
    mode:'markers+text', type:'scatter',
    marker:{{size:28,color:'#20253a',line:{{color:'#4aa3ff',width:1.5}}}},
    text:SECTORS, textfont:{{size:10,color:'#eef2ff'}}, textposition:'middle center',
    hovertext:SECTORS.map(s=>'<b>'+s+'</b><br>'+(SECTOR_LABELS[s]||s)),
    hovertemplate:'%{{hovertext}}<extra></extra>', name:'sectors',
  }};

  document.getElementById('edge-count-label').textContent = filtered.length + ' edge(s)';
  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    xaxis:{{range:[-1.6,1.6],showgrid:false,zeroline:false,showticklabels:false}},
    yaxis:{{range:[-1.45,1.45],showgrid:false,zeroline:false,showticklabels:false,scaleanchor:'x'}},
    annotations, showlegend:false, hovermode:'closest',
    margin:{{l:10,r:10,t:10,b:10}}, paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  }});
  Plotly.newPlot('sector-graph', [...edgeTraces, nodeTrace], layout, {{responsive:true, displayModeBar:false}});
  document.getElementById('sector-graph').on('plotly_click', function(data) {{
    const pt = data.points[0];
    if (pt.data.customdata) showEdgeDetail(filtered[pt.data.customdata[0]]);
  }});
}}

function showEdgeDetail(e) {{
  if (!e) return;
  const lcBadge = e.label_class==='ROBUST_ORIGINAL' ? '<span class="badge badge-robust">ROBUST_ORIGINAL</span>'
    : e.label_class==='FINE_GRAIN_SUPPORTED' ? '<span class="badge badge-fine">FINE_GRAIN_SUPPORTED</span>'
    : '<span class="badge badge-explor">EXPLORATORY_FINE_GRAIN</span>';
  const signBadge = e.sign==='+' ? '<span class="badge badge-pos">Positive ↑</span>' : '<span class="badge badge-neg">Negative ↓</span>';
  document.getElementById('edge-panel-empty').style.display = 'none';
  const content = document.getElementById('edge-panel-content');
  content.style.display = 'block';
  content.innerHTML = `
    <h3>${{e.source_sector}} → ${{e.target_sector}}</h3>
    <div style="margin:8px 0">${{lcBadge}} ${{signBadge}}</div>
    <div class="side-field"><span class="lbl">Country / system</span><span>${{e.country}} / ${{e.region_system}}</span></div>
    <div class="side-field"><span class="lbl">beta</span><span>${{e.beta.toFixed(4)}}</span></div>
    <div class="side-field"><span class="lbl">q_fdr</span><span>${{e.q_fdr.toFixed(4)}}</span></div>
    <div class="side-field"><span class="lbl">bss</span><span>${{e.bss.toFixed(3)}}</span></div>
    <div class="side-field"><span class="lbl">window</span><span>${{e.window}}</span></div>
    <div class="side-field"><span class="lbl">evidence_type</span><span style="font-size:10px">${{e.evidence_type}}</span></div>
    <div class="side-field"><span class="lbl">allowed_for_training_label</span><span>${{e.allowed_for_training_label}}</span></div>
  `;
}}

// ── Section 3: Blocked proxy table ──────────────────────────────────────
function renderBlockedTable() {{
  const tbody = document.querySelector('#blocked-table tbody');
  tbody.innerHTML = BLOCKED_EDGES.map(e => `<tr>
    <td>${{e.source_sector}}</td><td>${{e.target_sector}}</td><td>${{e.beta.toFixed(4)}}</td>
    <td>${{e.window}}</td><td>${{e.reason}}</td><td>${{e.allowed_for_training_label}}</td></tr>`).join('');
}}

// ── Section 5: manifest modal ────────────────────────────────────────────
function openManifestModal() {{
  document.getElementById('manifest-pre').textContent = JSON.stringify(MANIFEST, null, 2);
  document.getElementById('manifest-modal').classList.add('open');
}}
function closeManifestModal() {{
  document.getElementById('manifest-modal').classList.remove('open');
}}

// ── Init ─────────────────────────────────────────────────────────────────
renderKpis();
populateYearOptions('FR');
renderTerritoryView();
populateWindowOptions();
renderGraph();
renderBlockedTable();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
