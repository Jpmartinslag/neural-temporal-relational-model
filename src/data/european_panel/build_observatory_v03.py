"""Build HERALD Observatory v0.3 exports.

Adds sector-to-sector precedence graph layer to the v0.2 panel and generates
a self-contained geographic dashboard.

Products:
  herald_observatory_v03_panel.csv          — v02 panel with updated sector_graph_available
  herald_observatory_v03_sector_relations.json — 25 main edges with relation_class
  herald_observatory_v03_manifest.json      — provenance / checksums / derived windows
  herald_observatory_v03_summary.json       — aggregated state/territory summaries

Edges are predictive associations (observational precedence). No structural
causality, mechanism, or intervention claim is supported. DEC-034 (2026-06-12).

Changes vs v0.3-initial (DEC-036):
  - ROBUST_WINDOWS derived from covid_robust_edges.csv (not hardcoded).
  - Plotly JS embedded locally (truly self-contained HTML).
  - Dashboard includes a choropleth geographic map as primary element.
  - France territorial system (ZE2020) documented explicitly.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]

V02_PANEL_PATH = REPO_ROOT / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
PHASE7_DIR = REPO_ROOT / "data/processed/sector_precedence_results"
ALL_EDGES_PATH = PHASE7_DIR / "all_edges.csv"
COVID_ROBUST_PATH = PHASE7_DIR / "covid_robust_edges.csv"
LATEST_PATH = PHASE7_DIR / "latest.csv"
DECISION_PATH = PHASE7_DIR / "decision.json"
ZE_GEOJSON_PATH = REPO_ROOT / "data/external/ze2020_geometry.geojson"
NUTS3_GEOJSON_PATH = REPO_ROOT / "data/external/nuts3_2021_eurostat.geojson"

OUTPUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v03"

# ---------------------------------------------------------------------------
# Constants (ROBUST_WINDOWS is NOT defined here — derived from covid_robust_edges.csv)
# ---------------------------------------------------------------------------
V02_PANEL_SHA256 = "a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e"

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

VALID_A10 = frozenset(SECTOR_LABELS.keys())

VALID_ECONOMIC_STATES = frozenset({
    "growth",
    "acceleration",
    "deceleration",
    "stagnation",
    "decline",
    "recovery",
    "insufficient_history",
})

PROVENANCE_NOTE = (
    "Edges are predictive associations (observational precedence). "
    "No structural causality, mechanism, or intervention claim is supported. "
    "DEC-034 (2026-06-12)."
)

# NL COROP panel territory_id → NUTS3 geometry NUTS_ID (name-matched)
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

# Map center / zoom per country for choropleth
MAP_CONFIG: dict[str, dict] = {
    "FR": {"lat": 46.5, "lon": 2.5, "zoom": 4.5,
           "system": "ZE2020", "system_label": "Zones d'Emploi 2020",
           "note": "France uses functional employment zones (ZE2020, n=280), not NUTS3."},
    "NL": {"lat": 52.3, "lon": 5.2, "zoom": 6.4,
           "system": "COROP", "system_label": "COROP regions (NUTS3)",
           "note": "Netherlands uses COROP regions (n=40), equivalent to NUTS3 level 3."},
    "PT": {"lat": 39.5, "lon": -8.1, "zoom": 5.6,
           "system": "NUTS3", "system_label": "NUTS3 2021",
           "note": "Portugal uses NUTS3 2021 regions (n=25)."},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _year_in_any_window(year: int, windows: list[tuple[int, int]]) -> bool:
    return any(start <= year <= end for start, end in windows)


# ---------------------------------------------------------------------------
# Derive robust windows (replaces hardcoded ROBUST_WINDOWS constant)
# ---------------------------------------------------------------------------

def derive_robust_windows(covid_robust_path: Path | None = None) -> dict[str, list[tuple[int, int]]]:
    """Derive per-country robust windows from covid_robust_edges.csv.

    Fails closed if file is missing, empty, or inconsistent with DEC-034 counts.

    Returns:
        {country: [(window_start, window_end), ...]} sorted by window.
    """
    path = covid_robust_path or COVID_ROBUST_PATH
    if not path.exists():
        raise SystemExit(f"FAIL_CLOSED: covid_robust_edges.csv not found at {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise SystemExit("FAIL_CLOSED: covid_robust_edges.csv is empty")

    # Phase 7 consistency checks (immutable DEC-034 gate)
    nl_count = (df["country"] == "NL").sum()
    pt_count = (df["country"] == "PT").sum()
    fr_count = (df["country"] == "FR").sum()
    if nl_count != 3 or pt_count != 9 or fr_count != 0:
        raise SystemExit(
            f"FAIL_CLOSED: Phase 7 consistency check failed. "
            f"Expected NL=3, PT=9, FR=0 robust edges. "
            f"Got NL={nl_count}, PT={pt_count}, FR={fr_count}. "
            "Do not modify covid_robust_edges.csv without a new DEC-* entry."
        )

    windows: dict[str, set[tuple[int, int]]] = {}
    for _, row in df.iterrows():
        country = str(row["country"])
        w = (int(row["window_start"]), int(row["window_end"]))
        windows.setdefault(country, set()).add(w)

    result: dict[str, list[tuple[int, int]]] = {
        c: sorted(wset) for c, wset in sorted(windows.items())
    }
    logger.info("Derived robust windows: %s", result)
    return result


# ---------------------------------------------------------------------------
# GeoJSON preparation for embedded map
# ---------------------------------------------------------------------------

def _build_fr_geojson(
    fr_territory_ids: list[str],
    ze_geojson_path: Path,
) -> dict:
    """Build FR GeoJSON subset with panel_id property matching territory_id."""
    raw = json.loads(ze_geojson_path.read_text(encoding="utf-8"))
    # panel territory_id may be unpadded; geometry ze2020 is zero-padded to 4 chars
    panel_set = {str(int(tid)).zfill(4): tid for tid in fr_territory_ids}
    features = []
    for feat in raw["features"]:
        ze_code = feat["properties"]["ze2020"]  # e.g. "1109" or "0051"
        if ze_code in panel_set:
            f2 = dict(feat)
            f2["properties"] = dict(feat["properties"])
            f2["properties"]["panel_id"] = panel_set[ze_code]
            f2["properties"]["territory_name"] = feat["properties"]["libze2020"]
            features.append(f2)
    logger.info("FR GeoJSON: %d features", len(features))
    return {"type": "FeatureCollection", "features": features}


def _build_nl_geojson(
    nl_territory_names: dict[str, str],  # territory_id -> territory_name
    nuts3_geojson_path: Path,
) -> dict:
    """Build NL GeoJSON with panel_id = CR01, ..., CR40."""
    raw = json.loads(nuts3_geojson_path.read_text(encoding="utf-8"))
    nuts3_by_code = {
        f["properties"]["NUTS_ID"]: f
        for f in raw["features"]
        if f["properties"]["NUTS_ID"].startswith("NL")
        and f["properties"]["LEVL_CODE"] == 3
    }
    # Reverse mapping: NUTS3 code → panel territory_id
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
        f2["properties"]["territory_name"] = nl_territory_names.get(panel_id, panel_id)
        features.append(f2)
    logger.info("NL GeoJSON: %d features", len(features))
    return {"type": "FeatureCollection", "features": features}


def _build_pt_geojson(
    pt_territory_ids: list[str],
    nuts3_geojson_path: Path,
) -> dict:
    """Build PT GeoJSON with panel_id = PT_111 etc. from PT111 geometry."""
    raw = json.loads(nuts3_geojson_path.read_text(encoding="utf-8"))
    # panel territory_id = PT_111; geometry NUTS_ID = PT111
    panel_set = {tid.replace("_", ""): tid for tid in pt_territory_ids}
    features = []
    for feat in raw["features"]:
        nuts_id = feat["properties"]["NUTS_ID"]
        if nuts_id in panel_set and feat["properties"]["LEVL_CODE"] == 3:
            f2 = dict(feat)
            f2["properties"] = dict(feat["properties"])
            f2["properties"]["panel_id"] = panel_set[nuts_id]
            f2["properties"]["territory_name"] = feat["properties"]["NAME_LATN"]
            features.append(f2)
    logger.info("PT GeoJSON: %d features", len(features))
    return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_v03(output_dir: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Build v0.3 exports. Returns (panel_df, manifest_dict)."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Derive robust windows from Phase 7 results (fail-closed)
    robust_windows = derive_robust_windows()

    # 2. Load inputs
    logger.info("Loading v02 panel …")
    panel = pd.read_csv(
        V02_PANEL_PATH,
        dtype={"territory_id": str, "meta_nuts3_code": str},
        low_memory=False,
    )

    logger.info("Loading phase-7 edge files …")
    covid_robust = pd.read_csv(COVID_ROBUST_PATH)
    latest = pd.read_csv(LATEST_PATH)
    decision = json.loads(DECISION_PATH.read_text())

    # 3. Verify v02 panel checksum
    actual_sha = _sha256_file(V02_PANEL_PATH)
    if actual_sha != V02_PANEL_SHA256:
        raise RuntimeError(
            f"v02 panel checksum mismatch: expected {V02_PANEL_SHA256}, got {actual_sha}"
        )

    # 4. Classify edges
    robust_keys = set(
        zip(
            covid_robust["country"],
            covid_robust["window_start"],
            covid_robust["window_end"],
            covid_robust["source_sector"],
            covid_robust["target_sector"],
        )
    )

    relations: list[dict] = []
    for _, row in latest.iterrows():
        key = (
            row["country"],
            int(row["window_start"]),
            int(row["window_end"]),
            row["source_sector"],
            row["target_sector"],
        )
        relation_class = "ROBUST" if key in robust_keys else "MAIN_ONLY_EXPLORATORY"
        beta = float(row["beta"])
        relations.append({
            "country": row["country"],
            "window_start": int(row["window_start"]),
            "window_end": int(row["window_end"]),
            "source_sector": row["source_sector"],
            "source_label": SECTOR_LABELS[row["source_sector"]],
            "target_sector": row["target_sector"],
            "target_label": SECTOR_LABELS[row["target_sector"]],
            "beta": beta,
            "delta_r2": float(row["delta_r2"]),
            "p_perm": float(row["p_perm"]),
            "q_fdr": float(row["q_fdr"]),
            "bootstrap_sign_stability": float(row["bootstrap_sign_stability"]),
            "n_samples": int(row["n_samples"]),
            "relation_class": relation_class,
            "sign": "positive" if beta >= 0 else "negative",
            "scenario": "main",
        })

    # 5. Compute sector_graph_available using derived windows
    def _sga(row: pd.Series) -> int:
        if row["structural_mask"] != 1:
            return 0
        country = row["country"]
        if country not in robust_windows:
            return 0
        year = int(row["observation_year"])
        return 1 if _year_in_any_window(year, robust_windows[country]) else 0

    panel["sector_graph_available"] = panel.apply(_sga, axis=1)

    # 6. Build aggregated summaries
    structural = panel[panel["structural_mask"] == 1].copy()

    def _dominant_state(states: pd.Series) -> str:
        counts = states.value_counts()
        return counts.index[0] if len(counts) > 0 else "insufficient_history"

    state_grp = structural.groupby(["country", "observation_year", "sector_id"])
    state_records: list[dict] = []
    for (country, year, sector), grp in state_grp:
        n = len(grp)
        dominant = _dominant_state(grp["economic_state"])
        pct = (grp["economic_state"].value_counts() / n).to_dict()
        velocities = grp["velocity"].dropna()
        finite_vel = velocities[np.isfinite(velocities)]
        avg_vel = float(finite_vel.mean()) if len(finite_vel) > 0 else None
        state_records.append({
            "country": country,
            "observation_year": int(year),
            "sector_id": sector,
            "dominant_state": dominant,
            "n_territories": n,
            "pct_with_state": pct,
            "avg_velocity": avg_vel,
        })

    terr_grp = structural.groupby(["territory_id", "observation_year"])
    terr_records: list[dict] = []
    for (territory_id, year), grp in terr_grp:
        country = grp["country"].iloc[0]
        dominant_state = _dominant_state(grp["economic_state"])
        velocities = grp["velocity"].dropna()
        finite_vel = velocities[np.isfinite(velocities)]
        avg_vel = float(finite_vel.mean()) if len(finite_vel) > 0 else None
        terr_records.append({
            "territory_id": territory_id,
            "observation_year": int(year),
            "country": country,
            "state": dominant_state,
            "avg_velocity": avg_vel,
            "sector_count": len(grp),
            "territory_name": str(grp["territory_name"].iloc[0]),
        })

    summary = {
        "state_summary": state_records,
        "territory_summary": terr_records,
        "meta": {
            "version": "0.3",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_state_records": len(state_records),
            "n_territory_records": len(terr_records),
        },
    }

    # 7. Validate
    _validate(panel, relations, decision)

    # 8. Write outputs
    panel_path = output_dir / "herald_observatory_v03_panel.csv"
    panel_bytes = panel.to_csv(index=False).encode("utf-8")
    _atomic_write_bytes(panel_path, panel_bytes)
    panel_sha256 = _sha256_bytes(panel_bytes)

    relations_path = output_dir / "herald_observatory_v03_sector_relations.json"
    relations_payload = {"edges": relations}
    _atomic_write_text(relations_path, json.dumps(relations_payload, indent=2, ensure_ascii=False))

    summary_path = output_dir / "herald_observatory_v03_summary.json"
    _atomic_write_text(summary_path, json.dumps(summary, indent=2, ensure_ascii=False))

    robust_by_country: dict[str, int] = {}
    for r in relations:
        if r["relation_class"] == "ROBUST":
            robust_by_country[r["country"]] = robust_by_country.get(r["country"], 0) + 1

    manifest = {
        "version": "0.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision.get("verdict", ""),
        "verdict": decision.get("verdict", ""),
        "provenance_note": PROVENANCE_NOTE,
        "v02_panel_sha256": V02_PANEL_SHA256,
        "panel_sha256": panel_sha256,
        "edge_counts": {
            "total_main": len(relations),
            "robust": sum(1 for r in relations if r["relation_class"] == "ROBUST"),
            "main_only_exploratory": sum(
                1 for r in relations if r["relation_class"] == "MAIN_ONLY_EXPLORATORY"
            ),
            "robust_by_country": robust_by_country,
        },
        "panel_rows": len(panel),
        "countries": sorted(panel["country"].unique().tolist()),
        "gate_thresholds": decision.get("gate_thresholds", {}),
        "robust_windows": {k: [list(w) for w in v] for k, v in robust_windows.items()},
        "plotly_dependency": "local_embedded",
    }

    manifest_path = output_dir / "herald_observatory_v03_manifest.json"
    _atomic_write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    logger.info(
        "Done. Panel: %d rows, %d ROBUST edges, %d MAIN_ONLY edges.",
        len(panel),
        manifest["edge_counts"]["robust"],
        manifest["edge_counts"]["main_only_exploratory"],
    )

    return panel, manifest


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(panel: pd.DataFrame, relations: list[dict], decision: dict) -> None:
    errors: list[str] = []

    robust = [r for r in relations if r["relation_class"] == "ROBUST"]
    main_only = [r for r in relations if r["relation_class"] == "MAIN_ONLY_EXPLORATORY"]

    if len(robust) != 12:
        errors.append(f"Expected 12 ROBUST edges, got {len(robust)}")
    if len(main_only) != 13:
        errors.append(f"Expected 13 MAIN_ONLY_EXPLORATORY edges, got {len(main_only)}")

    nl_robust = sum(1 for r in robust if r["country"] == "NL")
    pt_robust = sum(1 for r in robust if r["country"] == "PT")
    fr_robust = sum(1 for r in robust if r["country"] == "FR")
    if nl_robust != 3:
        errors.append(f"Expected 3 NL ROBUST, got {nl_robust}")
    if pt_robust != 9:
        errors.append(f"Expected 9 PT ROBUST, got {pt_robust}")
    if fr_robust != 0:
        errors.append(f"Expected 0 FR ROBUST, got {fr_robust}")

    self_edges = [r for r in relations if r["source_sector"] == r["target_sector"]]
    if self_edges:
        errors.append(f"Self-edges found: {self_edges}")

    seen_keys: set[tuple] = set()
    for r in relations:
        k = (r["country"], r["window_start"], r["window_end"], r["source_sector"], r["target_sector"])
        if k in seen_keys:
            errors.append(f"Duplicate edge: {k}")
        seen_keys.add(k)

    bad_src = {r["source_sector"] for r in relations if r["source_sector"] not in VALID_A10}
    bad_tgt = {r["target_sector"] for r in relations if r["target_sector"] not in VALID_A10}
    if bad_src or bad_tgt:
        errors.append(f"Invalid sector codes: src={bad_src}, tgt={bad_tgt}")

    if len(panel) != 45945:
        errors.append(f"Expected 45945 panel rows, got {len(panel)}")

    bad_sector_ids = set(panel["sector_id"].unique()) - VALID_A10
    if bad_sector_ids:
        errors.append(f"Panel contains invalid sector_id codes: {bad_sector_ids}")

    bad_states = set(panel["economic_state"].dropna().unique()) - VALID_ECONOMIC_STATES
    if bad_states:
        errors.append(f"Invalid economic states: {bad_states}")

    if errors:
        for e in errors:
            logger.error("VALIDATION ERROR: %s", e)
        raise SystemExit(f"Validation failed with {len(errors)} error(s):\n" + "\n".join(errors))

    logger.info("All validation checks passed.")


# ---------------------------------------------------------------------------
# Plotly JS embedding
# ---------------------------------------------------------------------------

def _plotly_js_tag() -> str:
    """Return <script> tag embedding Plotly locally, or CDN fallback."""
    try:
        import plotly as _plotly
        js_path = Path(_plotly.__file__).parent / "package_data" / "plotly.min.js"
        if js_path.exists():
            js = js_path.read_text(encoding="utf-8")
            logger.info("Embedding Plotly locally (%d KB)", len(js) // 1024)
            return f"<script>{js}</script>"
    except Exception as exc:
        logger.warning("Could not load local Plotly: %s", exc)
    logger.warning("Falling back to Plotly CDN (dashboard will need internet)")
    return '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'


# ---------------------------------------------------------------------------
# Dashboard generation
# ---------------------------------------------------------------------------

def generate_dashboard(v03_dir: Path, output_path: Path) -> None:
    """Generate self-contained Observatory v0.3 HTML dashboard with geographic map."""
    v03_dir = Path(v03_dir)

    rel = json.loads((v03_dir / "herald_observatory_v03_sector_relations.json").read_text())
    summary = json.loads((v03_dir / "herald_observatory_v03_summary.json").read_text())
    manifest = json.loads((v03_dir / "herald_observatory_v03_manifest.json").read_text())

    # Load the v02 panel to get territory metadata
    panel = pd.read_csv(
        V02_PANEL_PATH,
        dtype={"territory_id": str, "meta_nuts3_code": str},
        low_memory=False,
        usecols=["country", "territory_id", "territory_name", "region_system"],
    ).drop_duplicates("territory_id")

    # Build per-country territory metadata for GeoJSON
    fr_ids = panel[panel["country"] == "FR"]["territory_id"].tolist()
    nl_names = dict(zip(panel[panel["country"] == "NL"]["territory_id"],
                        panel[panel["country"] == "NL"]["territory_name"]))
    pt_ids = panel[panel["country"] == "PT"]["territory_id"].tolist()

    # Build country GeoJSONs (embedded in dashboard)
    fr_geo = _build_fr_geojson(fr_ids, ZE_GEOJSON_PATH)
    nl_geo = _build_nl_geojson(nl_names, NUTS3_GEOJSON_PATH)
    pt_geo = _build_pt_geojson(pt_ids, NUTS3_GEOJSON_PATH)

    # Node positions for sector graph (circular layout)
    sectors_order = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
    node_pos: dict[str, dict] = {}
    for i, s in enumerate(sectors_order):
        angle = 2 * math.pi * i / len(sectors_order) - math.pi / 2
        node_pos[s] = {"x": round(math.cos(angle), 4), "y": round(math.sin(angle), 4)}

    # Encode embedded data
    edges_js = json.dumps(rel["edges"])
    state_summary_js = json.dumps(summary["state_summary"])
    territory_summary_js = json.dumps(summary["territory_summary"])
    node_pos_js = json.dumps(node_pos)
    sector_labels_js = json.dumps(SECTOR_LABELS)
    map_config_js = json.dumps(MAP_CONFIG)
    manifest_js = json.dumps({
        "version": manifest.get("version"),
        "generated_at": manifest.get("generated_at"),
        "verdict": manifest.get("verdict"),
        "provenance_note": manifest.get("provenance_note"),
        "robust_windows": manifest.get("robust_windows", {}),
        "edge_counts": manifest.get("edge_counts", {}),
        "plotly_dependency": manifest.get("plotly_dependency", "local_embedded"),
    })
    fr_geo_js = json.dumps(fr_geo)
    nl_geo_js = json.dumps(nl_geo)
    pt_geo_js = json.dumps(pt_geo)

    plotly_tag = _plotly_js_tag()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD Economic Observatory v0.3</title>
{plotly_tag}
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --good:#26a69a; --bad:#ef5350;
    --accel:#4aa3ff; --decel:#ffd180; --recov:#b084f5; --stag:#9aa4bf;
    --pos:#26a69a; --neg:#ef5350; --robust:#4aa3ff; --explor:#ffd180;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;font-size:14px;}}
  .wrap{{max-width:1600px;margin:0 auto;padding:20px;}}
  h1{{font-size:26px;font-weight:760;margin-bottom:4px;}}
  .subtitle{{color:var(--muted);font-size:13px;line-height:1.5;max-width:1000px;margin-bottom:16px;}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:0 0 18px;}}
  .kpi{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;}}
  .kpi .v{{font-size:22px;font-weight:760;}}
  .kpi .l{{color:var(--muted);font-size:11px;margin-top:2px;}}
  .section{{margin-top:24px;}}
  .section-title{{font-size:17px;font-weight:720;margin-bottom:4px;}}
  .section-note{{color:var(--muted);font-size:12px;line-height:1.45;max-width:1100px;margin-bottom:8px;}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px;}}
  .controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;}}
  select,button{{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:5px;padding:5px 9px;font-size:12px;cursor:pointer;}}
  .map-layout{{display:grid;grid-template-columns:1fr 360px;gap:12px;align-items:start;}}
  .side-panel{{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:14px;}}
  .side-panel h3{{font-size:14px;font-weight:720;margin-bottom:8px;}}
  .side-field{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:12px;}}
  .side-field .lbl{{color:var(--muted);}}
  .side-empty{{color:var(--muted);font-size:12px;padding:16px 0;text-align:center;}}
  .side-note{{margin-top:10px;color:var(--muted);font-size:11px;line-height:1.4;border-top:1px solid var(--line);padding-top:7px;}}
  .badge{{display:inline-block;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:700;border:1px solid;}}
  .badge-ze{{color:#b084f5;border-color:#b084f5;background:#16102a;}}
  .badge-nuts3{{color:#26a69a;border-color:#26a69a;background:#0a1e1a;}}
  .badge-corop{{color:#4aa3ff;border-color:#4aa3ff;background:#0a1a2e;}}
  .badge-robust{{color:var(--robust);border-color:var(--robust);background:#0a1a2e;}}
  .badge-explor{{color:var(--explor);border-color:var(--explor);background:#1e1a0a;}}
  .badge-pos{{color:var(--pos);border-color:var(--pos);background:#0a1e1a;}}
  .badge-neg{{color:var(--neg);border-color:var(--neg);background:#1e0a0a;}}
  .graph-layout{{display:grid;grid-template-columns:1fr 320px;gap:12px;}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
  .legend-row{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:7px;font-size:12px;}}
  .legend-item{{display:flex;align-items:center;gap:4px;color:var(--muted);}}
  .legend-dot{{width:11px;height:11px;border-radius:50%;flex-shrink:0;}}
  .legend-line{{width:22px;height:3px;flex-shrink:0;}}
  .assoc-warn{{background:#1a1206;border:1px solid #7a5c10;border-radius:6px;padding:8px 12px;font-size:12px;color:#ffd180;margin-bottom:8px;}}
  @media(max-width:950px){{
    .map-layout,.graph-layout,.grid2{{grid-template-columns:1fr;}}
    .kpis{{grid-template-columns:repeat(2,1fr);}}
  }}
</style>
</head>
<body>
<div class="wrap">

<h1>HERALD Economic Observatory <span style="color:var(--accel);font-size:16px">v0.3</span></h1>
<div class="subtitle">
  Sector enterprise-birth dynamics — FR (ZE2020, n=280) / NL (COROP, n=40) / PT (NUTS3, n=25).
  Sector precedence associations validated in Phase 7 (DEC-034, 2026-06-12).
  Edges express <em>predictive precedence</em> (observational associations only).
  No structural causality, mechanism, or intervention claim is supported.
</div>

<div class="kpis" id="kpi-bar"></div>

<!-- ── SECTION 1: Geographic Map (main element) ───────────────────────────── -->
<div class="section">
  <div class="section-title">1. Territorial Map</div>
  <div class="section-note">
    Dominant economic state per territory per year, aggregated over all sectors.
    Select a territory on the map to view its economic trajectory.
    Territorial systems differ by country: France uses functional employment zones (ZE2020),
    Netherlands uses COROP regions (NUTS3), Portugal uses NUTS3 2021.
  </div>
  <div class="assoc-warn">
    ⚠ Associations between sector graph and map are descriptive. Sector→sector edges show
    predictive precedence at the country level; they are not localized to individual territories.
    Do not interpret sector arrows as geographic flows between regions.
  </div>
  <div class="controls">
    <label>Country
      <select id="map-country" onchange="handleMapCountryChange()">
        <option value="FR">France (ZE2020)</option>
        <option value="NL">Netherlands (COROP)</option>
        <option value="PT">Portugal (NUTS3)</option>
      </select>
    </label>
    <label>Year
      <select id="map-year" onchange="renderMap()"></select>
    </label>
    <label>Metric
      <select id="map-metric" onchange="renderMap()">
        <option value="state">Dominant state</option>
        <option value="velocity">Average velocity</option>
      </select>
    </label>
    <span id="map-system-badge"></span>
    <span id="map-terr-count" style="color:var(--muted);font-size:12px;"></span>
  </div>
  <div class="legend-row" id="map-legend"></div>
  <div class="map-layout">
    <div class="card" style="min-height:520px"><div id="map-plot" style="height:520px"></div></div>
    <div class="side-panel" id="map-side">
      <h3>Territory detail</h3>
      <div class="side-empty" id="map-side-empty">Click a territory on the map to see its economic trajectory.</div>
      <div id="map-side-content" style="display:none"></div>
    </div>
  </div>
</div>

<!-- ── SECTION 2: Sector Precedence Graph (complementary) ─────────────────── -->
<div class="section">
  <div class="section-title">2. Sector Precedence Associations</div>
  <div class="section-note">
    A directed edge A → B indicates that lagged growth in sector A associates with enterprise-birth
    growth in sector B after controlling for B's own lag and removing territory/year fixed effects.
    <strong style="color:var(--robust)">ROBUST</strong> = promoted in main AND COVID-19 sensitivity scenario, same sign.
    <strong style="color:var(--explor)">Exploratory</strong> = main scenario only (hidden by default).
    This graph is valid at the country level; edges are not localised to individual territories.
  </div>
  <div class="controls">
    <label>Country <select id="graph-country" onchange="renderGraph()">
      <option value="NL">Netherlands</option>
      <option value="PT">Portugal</option>
      <option value="FR">France</option>
    </select></label>
    <label><input type="checkbox" id="show-explor" onchange="renderGraph()" style="margin-right:4px">Show exploratory edges</label>
    <span id="edge-count-label" style="color:var(--muted);font-size:12px;"></span>
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:var(--pos)"></div>Positive</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--neg)"></div>Negative</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--robust)"></div>ROBUST</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--explor);opacity:.6"></div>Exploratory</div>
  </div>
  <div class="graph-layout">
    <div class="card"><div id="sector-graph" style="height:480px"></div></div>
    <div class="side-panel" id="edge-panel">
      <h3>Edge detail</h3>
      <div class="side-empty">Click an edge to see details.</div>
    </div>
  </div>
</div>

<!-- ── SECTION 3: Economic State Timeline ─────────────────────────────────── -->
<div class="section">
  <div class="section-title">3. Economic State Timeline</div>
  <div class="section-note">
    Dominant economic state per sector per year, aggregated over all territories.
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:#4aa3ff"></div>Acceleration</div>
    <div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Growth</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ffd180"></div>Deceleration</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>Stagnation</div>
    <div class="legend-item"><div class="legend-dot" style="background:#b084f5"></div>Recovery</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Decline</div>
  </div>
  <div class="controls">
    <label>Country <select id="state-country" onchange="renderStateHeatmap()">
      <option value="FR">France</option>
      <option value="NL">Netherlands</option>
      <option value="PT">Portugal</option>
    </select></label>
  </div>
  <div class="card"><div id="state-heatmap" style="height:380px"></div></div>
</div>

<!-- ── SECTION 4: Territory State Distribution ────────────────────────────── -->
<div class="section">
  <div class="section-title">4. Territory State Distribution</div>
  <div class="controls">
    <label>Country <select id="dist-country" onchange="renderStateDistribution()">
      <option value="FR">France</option>
      <option value="NL">Netherlands</option>
      <option value="PT">Portugal</option>
    </select></label>
    <label>Sector <select id="dist-sector" onchange="renderStateDistribution()">
      <option value="ALL">All sectors</option>
      <option value="BE">BE — Industry</option>
      <option value="FZ">FZ — Construction</option>
      <option value="GI">GI — Trade &amp; transport</option>
      <option value="JZ">JZ — ICT</option>
      <option value="LZ">LZ — Real estate</option>
      <option value="MN">MN — Professional services</option>
      <option value="OQ">OQ — Public &amp; health</option>
      <option value="RU">RU — Arts &amp; other</option>
    </select></label>
  </div>
  <div class="card"><div id="state-dist" style="height:360px"></div></div>
</div>

<!-- ── SECTION 5: Territory Dynamics ─────────────────────────────────────── -->
<div class="section">
  <div class="section-title">5. Territory Dynamics (velocity heatmap)</div>
  <div class="controls">
    <label>Country <select id="terr-country" onchange="renderTerritoryHeatmap()">
      <option value="NL">Netherlands</option>
      <option value="PT">Portugal</option>
      <option value="FR">France (first 80)</option>
    </select></label>
  </div>
  <div class="card"><div id="terr-heatmap" style="height:480px"></div></div>
</div>

<!-- ── SECTION 6: Provenance ──────────────────────────────────────────────── -->
<div class="section" style="margin-top:32px;margin-bottom:20px;">
  <div class="section-title" style="font-size:14px;color:var(--muted)">Provenance</div>
  <div id="provenance-block" style="color:var(--muted);font-size:12px;line-height:1.7;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:6px;"></div>
</div>

</div><!-- /wrap -->

<script>
// ── Embedded data ─────────────────────────────────────────────────────────
const EDGES = {edges_js};
const STATE_SUMMARY = {state_summary_js};
const TERRITORY_SUMMARY = {territory_summary_js};
const NODE_POS = {node_pos_js};
const SECTOR_LABELS = {sector_labels_js};
const MANIFEST = {manifest_js};
const MAP_CONFIG = {map_config_js};
const GEO_FR = {fr_geo_js};
const GEO_NL = {nl_geo_js};
const GEO_PT = {pt_geo_js};
const GEO = {{FR: GEO_FR, NL: GEO_NL, PT: GEO_PT}};

// ── Constants ─────────────────────────────────────────────────────────────
const SECTORS = ['BE','FZ','GI','JZ','KZ','LZ','MN','OQ','RU'];
const STATE_COLORS = {{
  'growth':'#26a69a','acceleration':'#4aa3ff','deceleration':'#ffd180',
  'stagnation':'#9aa4bf','decline':'#ef5350','recovery':'#b084f5',
  'insufficient_history':'#1e2640'
}};
const STATE_NUM = {{
  'acceleration':3,'growth':2,'deceleration':1,'stagnation':0,
  'recovery':-1,'decline':-2,'insufficient_history':-3
}};
const STATE_COLORSCALE = [
  [0,'#1e2640'],[1/6,'#ef5350'],[2/6,'#b084f5'],
  [3/6,'#9aa4bf'],[4/6,'#ffd180'],[5/6,'#26a69a'],[1,'#4aa3ff']
];
const VEL_COLORSCALE = [
  [0,'#ef5350'],[0.3,'#b084f5'],[0.45,'#9aa4bf'],
  [0.5,'#1e2640'],[0.55,'#9aa4bf'],[0.7,'#26a69a'],[1,'#4aa3ff']
];
const BASE_LAYOUT = {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font:{{color:'#eef2ff',family:'Inter,Segoe UI,Arial,sans-serif',size:12}},
  margin:{{l:50,r:20,t:30,b:40}},
  hoverlabel:{{bgcolor:'#20253a',bordercolor:'#30364f',font:{{color:'#eef2ff'}}}},
}};

// ── Pre-index territory data ───────────────────────────────────────────────
const TERR_IDX = {{}};
TERRITORY_SUMMARY.forEach(r => {{
  if (!TERR_IDX[r.country]) TERR_IDX[r.country] = {{}};
  if (!TERR_IDX[r.country][r.territory_id]) TERR_IDX[r.country][r.territory_id] = {{}};
  TERR_IDX[r.country][r.territory_id][r.observation_year] = {{
    state: r.state, vel: r.avg_velocity, name: r.territory_name
  }};
}});

// ── Pre-index GeoJSON feature panel_id → feature name ────────────────────
const GEO_NAMES = {{}};
['FR','NL','PT'].forEach(c => {{
  GEO[c].features.forEach(f => {{
    GEO_NAMES[f.properties.panel_id] = f.properties.territory_name || f.properties.panel_id;
  }});
}});

// ── KPI bar ───────────────────────────────────────────────────────────────
function renderKPIs() {{
  const ec = MANIFEST.edge_counts || {{}};
  const kpiData = [
    {{v: 3, l:'Countries (FR/NL/PT)'}},
    {{v: 345, l:'Territories total'}},
    {{v: 9, l:'Sectors (A10 NACE)'}},
    {{v: ec.robust||12, l:'ROBUST associations', cls:'color:var(--robust)'}},
    {{v: ec.main_only_exploratory||13, l:'Exploratory (main only)', cls:'color:var(--explor)'}},
    {{v: MANIFEST.verdict==='SECTOR_PRECEDENCE_PROTOTYPE_READY' ? '✓ READY' : 'PENDING',
      l:'Prototype status', cls:'color:var(--good)'}},
  ];
  document.getElementById('kpi-bar').innerHTML = kpiData.map(k=>
    `<div class="kpi"><div class="v" style="${{k.cls||''}}">${{k.v}}</div><div class="l">${{k.l}}</div></div>`
  ).join('');
}}

// ── Geographic map ────────────────────────────────────────────────────────
let currentTerritory = null;

function getMapYears(country) {{
  const ys = new Set();
  TERRITORY_SUMMARY.forEach(r => {{ if (r.country===country) ys.add(r.observation_year); }});
  return [...ys].sort((a,b)=>a-b);
}}

function populateMapYearSelect(country) {{
  const sel = document.getElementById('map-year');
  const years = getMapYears(country);
  sel.innerHTML = years.map(y=>`<option value="${{y}}">${{y}}</option>`).join('');
  sel.value = years[years.length-1];
}}

function handleMapCountryChange() {{
  const country = document.getElementById('map-country').value;
  populateMapYearSelect(country);
  updateMapSystemBadge(country);
  clearMapSidePanel();
  renderMap();
}}

function updateMapSystemBadge(country) {{
  const cfg = MAP_CONFIG[country];
  const cls = country==='FR' ? 'ze' : country==='NL' ? 'corop' : 'nuts3';
  document.getElementById('map-system-badge').innerHTML =
    `<span class="badge badge-${{cls}}">${{cfg.system}}: ${{cfg.system_label}}</span>`;
  const n = country==='FR' ? 280 : country==='NL' ? 40 : 25;
  document.getElementById('map-terr-count').textContent = n + ' territories';
}}

function renderMap() {{
  const country = document.getElementById('map-country').value;
  const year = parseInt(document.getElementById('map-year').value);
  const metric = document.getElementById('map-metric').value;
  const cfg = MAP_CONFIG[country];
  const geo = GEO[country];
  if (!geo || !geo.features || !geo.features.length) return;

  const ctData = TERR_IDX[country] || {{}};
  const locations = [], z = [], customdata = [], text = [];
  geo.features.forEach(f => {{
    const pid = f.properties.panel_id;
    const name = f.properties.territory_name || pid;
    const yd = (ctData[pid]||{{}})[year];
    if (!yd) {{
      locations.push(pid); z.push(null);
      customdata.push({{pid, name, state:'no data', vel:null, year}});
      text.push(name + ': no data');
      return;
    }}
    locations.push(pid);
    if (metric === 'state') {{
      z.push(STATE_NUM[yd.state] ?? 0);
    }} else {{
      z.push(yd.vel != null ? yd.vel : null);
    }}
    customdata.push({{pid, name, state: yd.state, vel: yd.vel, year}});
    text.push(name + '<br>' + (yd.state||'').replace('_',' ')
      + (yd.vel != null ? '<br>vel=' + yd.vel.toFixed(3) : ''));
  }});

  const colorscale = metric === 'state' ? STATE_COLORSCALE : VEL_COLORSCALE;
  const zmin = metric === 'state' ? -3 : undefined;
  const zmax = metric === 'state' ? 3 : undefined;

  const trace = {{
    type: 'choropleth',
    geojson: geo,
    featureidkey: 'properties.panel_id',
    locations: locations,
    z: z,
    text: text,
    customdata: customdata,
    colorscale: colorscale,
    zmin: zmin, zmax: zmax, zmid: metric==='velocity' ? 0 : undefined,
    colorbar: {{
      title: metric==='state' ? 'State' : 'Velocity',
      tickfont: {{color:'#eef2ff',size:10}},
      thickness: 14, len: 0.8,
    }},
    hovertemplate: '%{{text}}<extra></extra>',
    marker: {{line: {{width: 0.5, color: '#30364f'}}}},
    showscale: true,
  }};

  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    geo: {{
      fitbounds: 'geojson',
      visible: false,
      bgcolor: '#0f1220',
      showframe: false,
      showcoastlines: false,
    }},
    margin: {{l:0,r:0,t:30,b:0}},
    title: {{
      text: country + ' — ' + year + ' — ' + metric,
      font: {{size:13, color:'#eef2ff'}},
    }},
  }});

  Plotly.newPlot('map-plot', [trace], layout, {{responsive:true, displayModeBar:false}});

  document.getElementById('map-plot').on('plotly_click', function(data) {{
    const pt = data.points[0];
    if (pt && pt.customdata) {{
      showTerritorySidePanel(pt.customdata);
    }}
  }});
  renderMapLegend(metric);
}}

function renderMapLegend(metric) {{
  const el = document.getElementById('map-legend');
  if (metric === 'state') {{
    el.innerHTML = Object.entries(STATE_COLORS).map(([s,c])=>
      `<div class="legend-item"><div class="legend-dot" style="background:${{c}}"></div>${{s.replace('_',' ')}}</div>`
    ).join('');
  }} else {{
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Contraction</div>
    <div class="legend-item"><div class="legend-dot" style="background:#1e2640"></div>Neutral (0)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Expansion</div>`;
  }}
}}

function showTerritorySidePanel(d) {{
  const country = document.getElementById('map-country').value;
  document.getElementById('map-side-empty').style.display = 'none';
  const content = document.getElementById('map-side-content');
  content.style.display = 'block';
  const timeData = TERR_IDX[country]?.[d.pid] || {{}};
  const years = Object.keys(timeData).map(Number).sort((a,b)=>a-b);
  const states = years.map(y => timeData[y].state || 'insufficient_history');
  const vels = years.map(y => timeData[y].vel);

  const cfg = MAP_CONFIG[country];
  const cls = country==='FR'?'ze':country==='NL'?'corop':'nuts3';

  content.innerHTML = `
    <div style="font-size:13px;font-weight:700;margin-bottom:8px">${{d.name}}</div>
    <div style="margin-bottom:8px"><span class="badge badge-${{cls}}">${{cfg.system}}</span></div>
    <div class="side-field"><span class="lbl">Territory ID</span><span class="val">${{d.pid}}</span></div>
    <div class="side-field"><span class="lbl">Country</span><span class="val">${{country}}</span></div>
    <div class="side-field"><span class="lbl">Selected year</span><span class="val">${{d.year}}</span></div>
    <div class="side-field"><span class="lbl">State (${{d.year}})</span><span class="val" style="color:${{STATE_COLORS[d.state]||'#eef2ff'}}">${{(d.state||'—').replace('_',' ')}}</span></div>
    <div class="side-field"><span class="lbl">Avg velocity (${{d.year}})</span><span class="val">${{d.vel!=null ? d.vel.toFixed(4) : '—'}}</span></div>
    <div style="margin-top:10px;font-size:11px;color:var(--muted)">Economic state over time:</div>
    <div id="terr-mini-plot" style="height:130px;margin-top:4px"></div>
    <div style="margin-top:6px;font-size:11px;color:var(--muted)">Velocity over time:</div>
    <div id="terr-vel-plot" style="height:110px;margin-top:4px"></div>
    <div class="side-note">Sector→sector associations are country-level. They are not
      localised to this territory. Associations only — no structural causality claim.</div>
  `;

  // Mini state bar chart
  Plotly.newPlot('terr-mini-plot', [{{
    type:'bar', x:years, y:years.map(y => STATE_NUM[timeData[y].state]??0),
    text:states.map(s=>s.replace('_',' ')),
    marker:{{color:states.map(s=>STATE_COLORS[s]||'#9aa4bf')}},
    hovertemplate:'%{{x}}: <b>%{{text}}</b><extra></extra>',
  }}], Object.assign({{}}, BASE_LAYOUT, {{
    margin:{{l:30,r:10,t:5,b:30}},
    xaxis:{{tickmode:'linear',dtick:2,tickfont:{{size:9}},tickangle:-45}},
    yaxis:{{showticklabels:false,zeroline:false}},
  }}), {{responsive:true,displayModeBar:false,staticPlot:true}});

  // Mini velocity line
  Plotly.newPlot('terr-vel-plot', [{{
    type:'scatter', mode:'lines+markers', x:years, y:vels,
    line:{{color:'#4aa3ff',width:1.5}}, marker:{{size:4}},
    hovertemplate:'%{{x}}: vel=%{{y:.4f}}<extra></extra>',
  }}], Object.assign({{}}, BASE_LAYOUT, {{
    margin:{{l:35,r:10,t:5,b:30}},
    xaxis:{{tickmode:'linear',dtick:2,tickfont:{{size:9}},tickangle:-45}},
    yaxis:{{tickfont:{{size:9}},zeroline:true,zerolinecolor:'#30364f'}},
    shapes:[{{type:'line',x0:years[0],x1:years[years.length-1],y0:0,y1:0,
      line:{{color:'#30364f',width:1,dash:'dot'}}}}],
  }}), {{responsive:true,displayModeBar:false,staticPlot:true}});
}}

function clearMapSidePanel() {{
  document.getElementById('map-side-empty').style.display = '';
  document.getElementById('map-side-content').style.display = 'none';
  document.getElementById('map-side-content').innerHTML = '';
}}

// ── Sector graph ──────────────────────────────────────────────────────────
function renderGraph() {{
  const country = document.getElementById('graph-country').value;
  const showExplor = document.getElementById('show-explor').checked;
  const filtered = EDGES.filter(e => {{
    if (e.country !== country) return false;
    if (e.relation_class === 'ROBUST') return true;
    return e.relation_class === 'MAIN_ONLY_EXPLORATORY' && showExplor;
  }});

  const pairIdx = {{}};
  const annotations = [], edgeTraces = [];
  filtered.forEach((e,i) => {{
    const sp = NODE_POS[e.source_sector], tp = NODE_POS[e.target_sector];
    if (!sp || !tp) return;
    const key = e.source_sector+'->'+e.target_sector;
    pairIdx[key] = (pairIdx[key]||0)+1;
    const hasRev = EDGES.some(e2=>e2.country===country&&e2.source_sector===e.target_sector&&e2.target_sector===e.source_sector);
    const off = hasRev ? (pairIdx[key]%2===0?1:-1)*0.06 : 0;
    const dx=tp.x-sp.x, dy=tp.y-sp.y, dist=Math.sqrt(dx*dx+dy*dy)||1;
    const ux=dx/dist, uy=dy/dist, r=0.15;
    const px=-uy*off, py=ux*off;
    const ax=sp.x+ux*r+px, ay=sp.y+uy*r+py, x=tp.x-ux*r+px, y=tp.y-uy*r+py;
    const isR = e.relation_class==='ROBUST';
    const col = e.sign==='positive'?'#26a69a':'#ef5350';
    const w = 1+Math.abs(e.beta||0)*10;
    edgeTraces.push({{
      x:[ax,x,null],y:[ay,y,null],mode:'lines',type:'scatter',
      line:{{color:col,width:w,dash:isR?'solid':'dash'}},opacity:isR?0.9:0.5,
      hovertemplate:`<b>${{e.source_sector}}→${{e.target_sector}}</b><br>β=${{e.beta.toFixed(3)}}<br>Δr²=${{e.delta_r2.toFixed(4)}}<br>q=${{e.q_fdr.toFixed(3)}}<br>Class:${{e.relation_class}}<extra></extra>`,
      customdata:[i],showlegend:false,name:e.source_sector+'→'+e.target_sector,
    }});
    annotations.push({{x,y,ax,ay,xref:'x',yref:'y',axref:'x',ayref:'y',
      showarrow:true,arrowhead:2,arrowsize:1.2,arrowwidth:Math.max(1.5,w*0.7),
      arrowcolor:col,opacity:isR?0.9:0.5}});
  }});

  const nodeTrace = {{
    x:SECTORS.map(s=>NODE_POS[s].x), y:SECTORS.map(s=>NODE_POS[s].y),
    mode:'markers+text',type:'scatter',
    marker:{{size:28,color:'#20253a',line:{{color:'#4aa3ff',width:1.5}}}},
    text:SECTORS, textfont:{{size:10,color:'#eef2ff'}}, textposition:'middle center',
    hovertext:SECTORS.map(s=>'<b>'+s+'</b><br>'+(SECTOR_LABELS[s]||s)),
    hovertemplate:'%{{hovertext}}<extra></extra>',name:'sectors',
  }};

  document.getElementById('edge-count-label').textContent =
    filtered.length + ' edge(s) — '+country;

  const layout = Object.assign({{}},BASE_LAYOUT,{{
    xaxis:{{range:[-1.6,1.6],showgrid:false,zeroline:false,showticklabels:false}},
    yaxis:{{range:[-1.45,1.45],showgrid:false,zeroline:false,showticklabels:false,scaleanchor:'x'}},
    annotations, showlegend:false, hovermode:'closest',
    margin:{{l:10,r:10,t:10,b:10}},paper_bgcolor:'#171b2d',plot_bgcolor:'#171b2d',
  }});

  Plotly.newPlot('sector-graph',[...edgeTraces,nodeTrace],layout,{{responsive:true,displayModeBar:false}});
  document.getElementById('sector-graph').on('plotly_click',function(data){{
    const pt=data.points[0];
    if (pt.data.customdata) showEdgeDetail(filtered[pt.data.customdata[0]]);
  }});
}}

function showEdgeDetail(e) {{
  if (!e) return;
  const cB = e.relation_class==='ROBUST'
    ?'<span class="badge badge-robust">ROBUST</span>'
    :'<span class="badge badge-explor">Exploratory</span>';
  const sB = e.sign==='positive'
    ?'<span class="badge badge-pos">Positive ↑</span>'
    :'<span class="badge badge-neg">Negative ↓</span>';
  document.getElementById('edge-panel').innerHTML = `
    <h3>${{e.source_sector}} → ${{e.target_sector}}</h3>
    <div style="margin-bottom:8px">${{cB}} ${{sB}}</div>
    <div class="side-field"><span class="lbl">Country</span><span class="val">${{e.country}}</span></div>
    <div class="side-field"><span class="lbl">Window</span><span class="val">${{e.window_start}}–${{e.window_end}}</span></div>
    <div class="side-field"><span class="lbl">Source</span><span class="val">${{e.source_label}}</span></div>
    <div class="side-field"><span class="lbl">Target</span><span class="val">${{e.target_label}}</span></div>
    <div class="side-field"><span class="lbl">β</span><span class="val">${{e.beta.toFixed(4)}}</span></div>
    <div class="side-field"><span class="lbl">Δr²</span><span class="val">${{e.delta_r2.toFixed(5)}}</span></div>
    <div class="side-field"><span class="lbl">p_perm</span><span class="val">${{e.p_perm.toFixed(3)}}</span></div>
    <div class="side-field"><span class="lbl">q_fdr</span><span class="val">${{e.q_fdr.toFixed(3)}}</span></div>
    <div class="side-field"><span class="lbl">Sign stability</span><span class="val">${{(e.bootstrap_sign_stability*100).toFixed(0)}}%</span></div>
    <div class="side-field"><span class="lbl">n</span><span class="val">${{e.n_samples}}</span></div>
    <div class="side-note">
      Predictive precedence: lagged ${{e.source_sector}} growth associates with ${{e.target_sector}}
      enterprise-birth growth after controlling for own lag. Country-level association, not localised
      to individual territories. Not a causal or intervention claim.
    </div>
  `;
}}

// ── Economic state heatmap ────────────────────────────────────────────────
function renderStateHeatmap() {{
  const country = document.getElementById('state-country').value;
  const rows = STATE_SUMMARY.filter(r=>r.country===country);
  const sectors = [...new Set(rows.map(r=>r.sector_id))].sort();
  const years = [...new Set(rows.map(r=>r.observation_year))].sort((a,b)=>a-b);
  const zM = sectors.map(s=>years.map(y=>{{
    const r=rows.find(r=>r.sector_id===s&&r.observation_year===y);
    return r?(STATE_NUM[r.dominant_state]??null):null;
  }}));
  const tM = sectors.map(s=>years.map(y=>{{
    const r=rows.find(r=>r.sector_id===s&&r.observation_year===y);
    return r?r.dominant_state.replace('_',' '):'';
  }}));
  Plotly.newPlot('state-heatmap',[{{
    type:'heatmap',z:zM,x:years,y:sectors,text:tM,
    hovertemplate:'%{{y}} %{{x}}: <b>%{{text}}</b><extra></extra>',
    colorscale:STATE_COLORSCALE,zmin:-3,zmax:3,showscale:false,xgap:1.5,ygap:1.5,
  }}],Object.assign({{}},BASE_LAYOUT,{{
    xaxis:{{tickmode:'linear',dtick:1,tickangle:-45}},
    yaxis:{{autorange:'reversed'}},
    title:{{text:'Economic states — '+country,font:{{size:13}}}},
    margin:{{l:50,r:20,t:40,b:60}},
  }}),{{responsive:true,displayModeBar:false}});
}}

// ── State distribution ────────────────────────────────────────────────────
function renderStateDistribution() {{
  const country=document.getElementById('dist-country').value;
  const sector=document.getElementById('dist-sector').value;
  let traces;
  if (sector==='ALL') {{
    const rows=TERRITORY_SUMMARY.filter(r=>r.country===country);
    const byYear={{}};
    rows.forEach(r=>{{const k=r.observation_year;if(!byYear[k])byYear[k]={{}};byYear[k][r.state]=(byYear[k][r.state]||0)+1;}});
    const years=Object.keys(byYear).map(Number).sort((a,b)=>a-b);
    traces=Object.entries(STATE_COLORS).map(([st,c])=>{{return{{type:'bar',name:st,x:years,y:years.map(y=>(byYear[y]?.[st]||0)),marker:{{color:c}}}};}});
  }} else {{
    const rows=STATE_SUMMARY.filter(r=>r.country===country&&r.sector_id===sector);
    const years=[...new Set(rows.map(r=>r.observation_year))].sort((a,b)=>a-b);
    traces=Object.entries(STATE_COLORS).map(([st,c])=>{{
      const vals=years.map(y=>{{const r=rows.find(r=>r.observation_year===y);return r?Math.round((r.pct_with_state[st]||0)*r.n_territories):0;}});
      return{{type:'bar',name:st,x:years,y:vals,marker:{{color:c}}}};
    }});
  }}
  Plotly.newPlot('state-dist',traces,Object.assign({{}},BASE_LAYOUT,{{
    barmode:'stack',title:{{text:'Territory states — '+country+(sector!=='ALL'?' / '+sector:''),font:{{size:13}}}},
    xaxis:{{tickmode:'linear',dtick:1,tickangle:-45}},margin:{{l:50,r:20,t:40,b:60}},
  }}),{{responsive:true,displayModeBar:false}});
}}

// ── Territory velocity heatmap ────────────────────────────────────────────
function renderTerritoryHeatmap() {{
  const country=document.getElementById('terr-country').value;
  let rows=TERRITORY_SUMMARY.filter(r=>r.country===country);
  let territories=[...new Set(rows.map(r=>r.territory_id))].sort();
  const years=[...new Set(rows.map(r=>r.observation_year))].sort((a,b)=>a-b);
  const capped=country==='FR'&&territories.length>80;
  if(capped) territories=territories.slice(0,80);
  const zM=territories.map(t=>years.map(y=>{{const r=rows.find(r=>r.territory_id===t&&r.observation_year===y);return(r&&r.avg_velocity!=null)?r.avg_velocity:null;}}));
  const tM=territories.map(t=>years.map(y=>{{const r=rows.find(r=>r.territory_id===t&&r.observation_year===y);return r?(r.state||'').replace('_',' ')+(r.avg_velocity!=null?'(v='+r.avg_velocity.toFixed(3)+')':''):'';}}));
  const h=Math.max(350,Math.min(700,territories.length*12+80));
  document.getElementById('terr-heatmap').style.height=h+'px';
  Plotly.newPlot('terr-heatmap',[{{
    type:'heatmap',z:zM,x:years,y:territories,text:tM,
    hovertemplate:'%{{y}} %{{x}}: %{{text}}<extra></extra>',
    colorscale:VEL_COLORSCALE,zmid:0,
    colorbar:{{title:'Velocity',tickfont:{{color:'#eef2ff',size:10}},thickness:14}},
    xgap:1,ygap:0.5,
  }}],Object.assign({{}},BASE_LAYOUT,{{
    xaxis:{{tickmode:'linear',dtick:2,tickangle:-45}},
    yaxis:{{autorange:'reversed',tickfont:{{size:9}}}},
    title:{{text:'Territory velocity — '+country+(capped?' (first 80)':''),font:{{size:13}}}},
    margin:{{l:70,r:80,t:40,b:60}},
  }}),{{responsive:true,displayModeBar:false}});
}}

// ── Provenance ────────────────────────────────────────────────────────────
function renderProvenance() {{
  const rw = MANIFEST.robust_windows || {{}};
  const rwStr = Object.entries(rw).map(([c,ws])=>c+': '+ws.map(w=>w[0]+'–'+w[1]).join(', ')).join('; ');
  const dep = MANIFEST.plotly_dependency === 'local_embedded'
    ? '📦 Plotly embedded locally (self-contained, no CDN dependency)'
    : '🌐 Plotly loaded from CDN (requires internet: cdn.plot.ly)';
  document.getElementById('provenance-block').innerHTML =
    `<b>Version:</b> Observatory v${{MANIFEST.version||'0.3'}} &nbsp;|&nbsp;
    <b>Generated:</b> ${{MANIFEST.generated_at||'—'}} &nbsp;|&nbsp;
    <b>Verdict:</b> ${{MANIFEST.verdict||'—'}} &nbsp;|&nbsp;
    <b>Dependency:</b> ${{dep}}<br>
    <b>Robust windows (derived from Phase 7):</b> ${{rwStr||'—'}}<br>
    <b>Note:</b> ${{MANIFEST.provenance_note||''}}`;
}}

// ── Init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {{
  renderKPIs();
  populateMapYearSelect('FR');
  updateMapSystemBadge('FR');
  renderMap();
  renderGraph();
  renderStateHeatmap();
  renderStateDistribution();
  renderTerritoryHeatmap();
  renderProvenance();
}});
</script>
</body>
</html>"""

    _atomic_write_text(output_path, html)
    logger.info("Dashboard written: %s (%d KB)", output_path, len(html.encode("utf-8")) // 1024)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        panel, manifest = build_v03()
        dash_path = (
            REPO_ROOT / "reports/dashboards/herald_observatory_v03_dashboard.html"
        )
        generate_dashboard(OUTPUT_DIR, dash_path)
    except SystemExit:
        raise
    except Exception as exc:
        logger.exception("Build failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
