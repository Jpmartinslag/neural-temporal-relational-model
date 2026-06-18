"""
Build the HERALD Observatory v0.5.1 dashboard — French, article-grade method
opening, integrated prediction (incl. PT municipal), real geographic
heatmap ("Bassins économiques"), graph<->map wiring, and a collapsible
"Détails méthodologiques" section.

Reads data/processed/herald_observatory_v051_narrative/ (built by
build_observatory_v051_narrative_exports.py) plus the same geometry sources
used by v0.4/v0.5 (FR ZE2020, NL COROP via NUTS3 crosswalk, PT Municipality).
Does NOT touch v0.4/v0.4.1/v0.5 files or their dashboards.
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
V051_DIR = REPO_ROOT / "data/processed/herald_observatory_v051_narrative"

TERRITORY_VIEW_PATH = V051_DIR / "territory_view.csv"
SECTOR_VIEW_PATH = V051_DIR / "sector_view.csv"
RELATION_VIEW_PATH = V051_DIR / "relation_view.csv"
PREDICTION_VIEW_PATH = V051_DIR / "prediction_view.csv"
MAP_STATE_PATH = V051_DIR / "map_state_by_year_sector.json"
RELATION_TIMELINE_PATH = V051_DIR / "relation_timeline.json"
PREDICTION_LOOKUP_PATH = V051_DIR / "prediction_lookup.json"
ECONOMIC_BASINS_PATH = V051_DIR / "economic_basins.json"
BLOCKED_PATH = V051_DIR / "blocked_proxy_edges_v04_copy.csv"
V051_MANIFEST_PATH = V051_DIR / "manifest.json"

ZE_GEOJSON_PATH = REPO_ROOT / "data/external/ze2020_geometry.geojson"
NUTS3_GEOJSON_PATH = REPO_ROOT / "data/external/nuts3_2021_eurostat.geojson"
PT_GEOJSON_PATH = REPO_ROOT / "data/processed/geometries/pt_municipalities_continental.geojson"
PT_GEOJSON_MANIFEST_PATH = REPO_ROOT / "data/processed/geometries/pt_municipalities_continental_manifest.json"

OUT_PATH = REPO_ROOT / "reports/dashboards/herald_observatory_v051_narrative_dashboard.html"

SECTOR_LABELS_FR = {
    "BE": "Industrie et énergie",
    "FZ": "Construction",
    "GI": "Commerce, transport et hébergement",
    "JZ": "Information et communication",
    "KZ": "Finance et assurance",
    "LZ": "Immobilier",
    "MN": "Services professionnels",
    "OQ": "Administration, éducation et santé",
    "RU": "Culture et autres services",
}
SECTORS_ORDER = list(SECTOR_LABELS_FR.keys())

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
    "NL": {"region_system": "COROP", "label": "Pays-Bas"},
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


def main() -> None:
    territory_view = pd.read_csv(TERRITORY_VIEW_PATH, low_memory=False)
    sector_view = pd.read_csv(SECTOR_VIEW_PATH, low_memory=False)
    relation_view = pd.read_csv(RELATION_VIEW_PATH, low_memory=False)
    prediction_view = pd.read_csv(PREDICTION_VIEW_PATH, low_memory=False)
    map_state = json.loads(MAP_STATE_PATH.read_text())
    relation_timeline = json.loads(RELATION_TIMELINE_PATH.read_text())
    prediction_lookup = json.loads(PREDICTION_LOOKUP_PATH.read_text())
    economic_basins = json.loads(ECONOMIC_BASINS_PATH.read_text())
    blocked_edges = pd.read_csv(BLOCKED_PATH, low_memory=False)
    v051_manifest = json.loads(V051_MANIFEST_PATH.read_text())

    assert "GEMEENTE_PROXY" not in relation_view["region_system"].values, \
        "FAIL_CLOSED: NL gemeente proxy must never appear in the main relation graph"
    assert (blocked_edges["allowed_for_training_label"] == False).all()

    region_meta = build_region_meta(territory_view)
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
    pt_kz_structural_absent = bool(v051_manifest["rules"]["pt_kz_structural_absent"])
    prediction_countries = v051_manifest["rules"]["prediction_layer_countries"]
    pt_municipal_rows = int(v051_manifest["row_counts"]["prediction_view_pt_municipal"])

    relation_edges_js = relation_view.to_dict(orient="records")
    blocked_edges_js = blocked_edges.to_dict(orient="records")
    # to_dict(orient="records") + json.dumps would emit literal NaN tokens
    # for missing mean_velocity values (Part N4: no raw "NaN" in rendered
    # output). Use pandas' own JSON writer, which encodes NaN as null.
    sector_view_js = json.loads(sector_view.to_json(orient="records"))

    csv_checksums = {
        "territory_view.csv": _sha256_file(TERRITORY_VIEW_PATH)[:16],
        "relation_view.csv": _sha256_file(RELATION_VIEW_PATH)[:16],
        "sector_view.csv": _sha256_file(SECTOR_VIEW_PATH)[:16],
        "prediction_view.csv": _sha256_file(PREDICTION_VIEW_PATH)[:16],
        "blocked_proxy_edges_v04_copy.csv": _sha256_file(BLOCKED_PATH)[:16],
    }

    n_fr = int(n_territories.get("FR", 0))
    n_nl = int(n_territories.get("NL", 0))
    n_pt = int(n_territories.get("PT", 0))

    html = _render_html(
        plotly_tag=plotly_tag, plotly_dep=plotly_dep,
        region_meta_js=json.dumps(region_meta, separators=(",", ":")),
        map_state_js=json.dumps(map_state, separators=(",", ":")),
        node_pos_js=json.dumps(node_pos),
        sector_labels_js=json.dumps(SECTOR_LABELS_FR),
        geo_fr_js=json.dumps(geo_fr, separators=(",", ":")),
        geo_nl_js=json.dumps(geo_nl, separators=(",", ":")),
        geo_pt_js=json.dumps(geo_pt, separators=(",", ":")),
        relation_edges_js=json.dumps(relation_edges_js),
        relation_timeline_js=json.dumps(relation_timeline),
        blocked_edges_js=json.dumps(blocked_edges_js),
        prediction_lookup_js=json.dumps(prediction_lookup, separators=(",", ":")),
        economic_basins_js=json.dumps(economic_basins, separators=(",", ":")),
        sector_view_js=json.dumps(sector_view_js),
        manifest_js=json.dumps(v051_manifest),
        map_config_js=json.dumps(MAP_CONFIG),
        csv_checksums_js=json.dumps(csv_checksums),
        n_territories_js=json.dumps(n_territories),
        n_valid_relations=n_valid_relations,
        n_blocked_relations=n_blocked_relations,
        n_sectors_tracked=n_sectors_tracked,
        pt_kz_structural_absent=json.dumps(pt_kz_structural_absent),
        prediction_countries_js=json.dumps(prediction_countries),
        pt_map_status=pt_map_status,
        n_fr=n_fr, n_nl=n_nl, n_pt=n_pt,
        pt_municipal_rows=pt_municipal_rows,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(OUT_PATH, html)
    size_mb = OUT_PATH.stat().st_size / 1e6
    logger.info("Wrote %s (%.2f MB)", OUT_PATH, size_mb)


def _render_html(**kw) -> str:
    try:
        from .build_observatory_v051_narrative_dashboard_template import render_template
    except ImportError:
        from build_observatory_v051_narrative_dashboard_template import render_template
    return render_template(SECTOR_LABELS_FR, SECTORS_ORDER, GSAP_TAG, **kw)


if __name__ == "__main__":
    main()
