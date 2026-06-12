"""Build HERALD Observatory v0.3 exports.

Adds sector-to-sector precedence graph layer to the v0.2 panel.

Products:
  herald_observatory_v03_panel.csv          — v02 panel with updated sector_graph_available
  herald_observatory_v03_sector_relations.json — 25 main edges with relation_class
  herald_observatory_v03_manifest.json      — provenance / checksums
  herald_observatory_v03_summary.json       — aggregated state/territory summaries

Edges are predictive associations (observational precedence). No structural
causality, mechanism, or intervention claim is supported. DEC-034 (2026-06-12).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mode as _mode
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

OUTPUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v03"

# ---------------------------------------------------------------------------
# Constants
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

# Robust windows per country: country -> list of (start, end) inclusive year ranges
ROBUST_WINDOWS = {
    "NL": [(2014, 2019)],
    "PT": [(2014, 2019), (2015, 2020), (2017, 2022)],
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
    """Write text to path atomically via a .tmp sibling."""
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
# Core builder
# ---------------------------------------------------------------------------

def build_v03(output_dir: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Build v0.3 exports. Returns (panel_df, manifest_dict).

    Parameters
    ----------
    output_dir:
        Directory to write outputs. Defaults to OUTPUT_DIR. Pass a tmp_path
        in tests to avoid writing to the real output tree.
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load inputs
    # ------------------------------------------------------------------
    logger.info("Loading v02 panel …")
    panel = pd.read_csv(
        V02_PANEL_PATH,
        dtype={"territory_id": str, "meta_nuts3_code": str},
        low_memory=False,
    )

    logger.info("Loading phase-7 edge files …")
    all_edges = pd.read_csv(ALL_EDGES_PATH)
    covid_robust = pd.read_csv(COVID_ROBUST_PATH)
    latest = pd.read_csv(LATEST_PATH)
    decision = json.loads(DECISION_PATH.read_text())

    # ------------------------------------------------------------------
    # 2. Verify v02 panel checksum
    # ------------------------------------------------------------------
    logger.info("Verifying v02 panel checksum …")
    actual_sha = _sha256_file(V02_PANEL_PATH)
    if actual_sha != V02_PANEL_SHA256:
        raise RuntimeError(
            f"v02 panel checksum mismatch: expected {V02_PANEL_SHA256}, got {actual_sha}"
        )

    # ------------------------------------------------------------------
    # 3. Classify edges
    # ------------------------------------------------------------------
    # Key for matching: country, window_start, window_end, source_sector, target_sector
    robust_keys = set(
        zip(
            covid_robust["country"],
            covid_robust["window_start"],
            covid_robust["window_end"],
            covid_robust["source_sector"],
            covid_robust["target_sector"],
        )
    )

    # latest.csv contains the 25 promoted main edges
    relations = []
    for _, row in latest.iterrows():
        key = (
            row["country"],
            int(row["window_start"]),
            int(row["window_end"]),
            row["source_sector"],
            row["target_sector"],
        )
        if key in robust_keys:
            relation_class = "ROBUST"
        else:
            relation_class = "MAIN_ONLY_EXPLORATORY"

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

    # ------------------------------------------------------------------
    # 4. Compute sector_graph_available for v03
    #    1 if structural_mask=1 AND country in {NL, PT}
    #      AND year falls in at least one robust window for that country
    # ------------------------------------------------------------------
    logger.info("Recomputing sector_graph_available …")

    def _sga(row: pd.Series) -> int:
        if row["structural_mask"] != 1:
            return 0
        country = row["country"]
        if country not in ROBUST_WINDOWS:
            return 0
        year = int(row["observation_year"])
        return 1 if _year_in_any_window(year, ROBUST_WINDOWS[country]) else 0

    panel["sector_graph_available"] = panel.apply(_sga, axis=1)

    # ------------------------------------------------------------------
    # 5. Build aggregated summaries
    # ------------------------------------------------------------------
    logger.info("Building aggregated summaries …")

    structural = panel[panel["structural_mask"] == 1].copy()

    # state_summary: country × year × sector_id
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

    # territory_summary: territory_id × year
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

    # ------------------------------------------------------------------
    # 6. Validate before writing
    # ------------------------------------------------------------------
    logger.info("Validating …")
    _validate(panel, relations, decision)

    # ------------------------------------------------------------------
    # 7. Write outputs (atomic)
    # ------------------------------------------------------------------
    logger.info("Writing outputs …")

    # Panel CSV
    panel_path = output_dir / "herald_observatory_v03_panel.csv"
    panel_bytes = panel.to_csv(index=False).encode("utf-8")
    _atomic_write_bytes(panel_path, panel_bytes)
    panel_sha256 = _sha256_bytes(panel_bytes)

    # Sector relations JSON
    relations_path = output_dir / "herald_observatory_v03_sector_relations.json"
    relations_payload = {"edges": relations}
    _atomic_write_text(relations_path, json.dumps(relations_payload, indent=2, ensure_ascii=False))

    # Summary JSON
    summary_path = output_dir / "herald_observatory_v03_summary.json"
    _atomic_write_text(summary_path, json.dumps(summary, indent=2, ensure_ascii=False))

    # Manifest JSON (last — contains checksums of the above)
    robust_by_country = {}
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
        "robust_windows": {k: [list(w) for w in v] for k, v in ROBUST_WINDOWS.items()},
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

    # Edge counts
    robust = [r for r in relations if r["relation_class"] == "ROBUST"]
    main_only = [r for r in relations if r["relation_class"] == "MAIN_ONLY_EXPLORATORY"]

    if len(robust) != 12:
        errors.append(f"Expected 12 ROBUST edges, got {len(robust)}")
    if len(main_only) != 13:
        errors.append(f"Expected 13 MAIN_ONLY_EXPLORATORY edges, got {len(main_only)}")

    # Robust by country
    nl_robust = sum(1 for r in robust if r["country"] == "NL")
    pt_robust = sum(1 for r in robust if r["country"] == "PT")
    fr_robust = sum(1 for r in robust if r["country"] == "FR")
    if nl_robust != 3:
        errors.append(f"Expected 3 NL ROBUST edges, got {nl_robust}")
    if pt_robust != 9:
        errors.append(f"Expected 9 PT ROBUST edges, got {pt_robust}")
    if fr_robust != 0:
        errors.append(f"Expected 0 FR ROBUST edges, got {fr_robust}")

    # No self-edges
    self_edges = [r for r in relations if r["source_sector"] == r["target_sector"]]
    if self_edges:
        errors.append(f"Self-edges found: {self_edges}")

    # No duplicates
    seen_keys: set[tuple] = set()
    for r in relations:
        k = (r["country"], r["window_start"], r["window_end"], r["source_sector"], r["target_sector"])
        if k in seen_keys:
            errors.append(f"Duplicate edge: {k}")
        seen_keys.add(k)

    # All sector codes valid
    bad_src = {r["source_sector"] for r in relations if r["source_sector"] not in VALID_A10}
    bad_tgt = {r["target_sector"] for r in relations if r["target_sector"] not in VALID_A10}
    if bad_src or bad_tgt:
        errors.append(f"Invalid sector codes: src={bad_src}, tgt={bad_tgt}")

    # Panel row count
    if len(panel) != 45945:
        errors.append(f"Expected 45945 panel rows, got {len(panel)}")

    # Panel sector codes
    bad_sector_ids = set(panel["sector_id"].unique()) - VALID_A10
    if bad_sector_ids:
        errors.append(f"Panel contains invalid sector_id codes: {bad_sector_ids}")

    # Economic states
    bad_states = set(panel["economic_state"].dropna().unique()) - VALID_ECONOMIC_STATES
    if bad_states:
        errors.append(f"Invalid economic states: {bad_states}")

    if errors:
        for e in errors:
            logger.error("VALIDATION ERROR: %s", e)
        raise SystemExit(f"Validation failed with {len(errors)} error(s):\n" + "\n".join(errors))

    logger.info("All validation checks passed.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def generate_dashboard(v03_dir: Path, output_path: Path) -> None:
    """Generate the self-contained Observatory v0.3 HTML dashboard."""
    import math

    rel = json.loads((v03_dir / "herald_observatory_v03_sector_relations.json").read_text())
    summary = json.loads((v03_dir / "herald_observatory_v03_summary.json").read_text())
    manifest = json.loads((v03_dir / "herald_observatory_v03_manifest.json").read_text())

    # Node positions (circle layout, top = BE)
    sectors_order = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
    node_pos: dict[str, dict[str, float]] = {}
    for i, s in enumerate(sectors_order):
        angle = 2 * math.pi * i / len(sectors_order) - math.pi / 2
        node_pos[s] = {"x": round(math.cos(angle), 4), "y": round(math.sin(angle), 4)}

    # Encode embedded data
    edges_js = json.dumps(rel["edges"])
    state_summary_js = json.dumps(summary["state_summary"])
    territory_summary_js = json.dumps(summary["territory_summary"])
    node_pos_js = json.dumps(node_pos)
    sector_labels_js = json.dumps(SECTOR_LABELS)
    manifest_js = json.dumps({
        "version": manifest.get("version"),
        "generated_at": manifest.get("generated_at"),
        "verdict": manifest.get("verdict"),
        "robust_count": manifest.get("robust_count"),
        "main_only_exploratory_count": manifest.get("main_only_exploratory_count"),
        "n_countries": manifest.get("n_countries"),
        "n_territories": manifest.get("n_territories"),
        "provenance_note": manifest.get("provenance_note"),
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD Economic Observatory v0.3</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --good:#26a69a; --bad:#ef5350;
    --accel:#4aa3ff; --decel:#ffd180; --recov:#b084f5; --stag:#9aa4bf;
    --pos:#26a69a; --neg:#ef5350; --robust:#4aa3ff; --explor:#ffd180;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:Inter,Segoe UI,Arial,sans-serif; }}
  .wrap {{ max-width:1500px; margin:0 auto; padding:22px; }}
  h1 {{ font-size:28px; font-weight:760; margin-bottom:6px; }}
  .subtitle {{ color:var(--muted); font-size:14px; line-height:1.5; max-width:1000px; margin-bottom:18px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; margin:0 0 20px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .kpi .v {{ font-size:24px; font-weight:760; }}
  .kpi .l {{ color:var(--muted); font-size:12px; margin-top:3px; }}
  .section {{ margin-top:28px; }}
  .section-title {{ font-size:19px; font-weight:720; margin-bottom:6px; }}
  .section-note {{ color:var(--muted); font-size:13px; line-height:1.45; max-width:1100px; margin-bottom:10px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }}
  .controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:10px; }}
  select, button {{ background:var(--panel2); color:var(--text); border:1px solid var(--line); border-radius:6px; padding:6px 10px; font-size:13px; cursor:pointer; }}
  select:focus, button:focus {{ outline:1px solid var(--accel); }}
  .badge {{ display:inline-block; border-radius:999px; padding:2px 9px; font-size:11px; font-weight:700; border:1px solid; }}
  .badge-robust {{ color:var(--robust); border-color:var(--robust); background:#0a1a2e; }}
  .badge-explor {{ color:var(--explor); border-color:var(--explor); background:#1e1a0a; }}
  .badge-pos {{ color:var(--pos); border-color:var(--pos); background:#0a1e1a; }}
  .badge-neg {{ color:var(--neg); border-color:var(--neg); background:#1e0a0a; }}
  .graph-layout {{ display:grid; grid-template-columns:1fr 340px; gap:14px; }}
  .side-panel {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:16px; }}
  .side-panel h3 {{ font-size:15px; font-weight:720; margin-bottom:10px; color:var(--text); }}
  .side-field {{ display:flex; justify-content:space-between; margin-bottom:7px; font-size:13px; }}
  .side-field .lbl {{ color:var(--muted); }}
  .side-field .val {{ font-weight:600; }}
  .side-empty {{ color:var(--muted); font-size:13px; padding:20px 0; text-align:center; }}
  .side-note {{ margin-top:12px; color:var(--muted); font-size:11px; line-height:1.5; border-top:1px solid var(--line); padding-top:8px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .legend-row {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:8px; font-size:12px; }}
  .legend-item {{ display:flex; align-items:center; gap:5px; color:var(--muted); }}
  .legend-dot {{ width:12px; height:12px; border-radius:50%; flex-shrink:0; }}
  .legend-line {{ width:24px; height:3px; flex-shrink:0; }}
  @media(max-width:900px) {{
    .graph-layout {{ grid-template-columns:1fr; }}
    .grid2 {{ grid-template-columns:1fr; }}
    .kpis {{ grid-template-columns:repeat(2,1fr); }}
  }}
</style>
</head>
<body>
<div class="wrap">

<h1>HERALD Economic Observatory <span style="color:var(--accel);font-size:18px">v0.3</span></h1>
<div class="subtitle">
  Sector enterprise-birth dynamics for FR / NL / PT &mdash; validated sector precedence associations (DEC-034, 2026-06-12).
  Edges express <em>predictive precedence</em> (observational associations). No structural causality, mechanism, or intervention claim is implied.
</div>

<div class="kpis" id="kpi-bar"></div>

<!-- ── Section 1: Sector Precedence Graph ─────────────────────────────── -->
<div class="section">
  <div class="section-title">1. Sector Precedence Associations</div>
  <div class="section-note">
    A directed edge from A to B indicates that lagged growth in sector A associates with current enterprise-birth growth in sector B,
    after controlling for B's own lag and removing territory/year fixed effects.
    <strong style="color:var(--robust)">ROBUST</strong> = promoted in main scenario AND COVID-19 sensitivity scenario, same sign.
    <strong style="color:var(--explor)">Exploratory</strong> = promoted in main scenario only.
    Not shown by default: edges that did not pass statistical gates.
  </div>
  <div class="controls">
    <label>Country <select id="graph-country" onchange="renderGraph()">
      <option value="NL">Netherlands (NL)</option>
      <option value="PT">Portugal (PT)</option>
      <option value="FR">France (FR)</option>
    </select></label>
    <label><input type="checkbox" id="show-explor" onchange="renderGraph()" style="margin-right:4px">Show exploratory edges</label>
    <span id="edge-count-label" style="color:var(--muted);font-size:13px;margin-left:6px;"></span>
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:var(--pos)"></div>Positive association</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--neg)"></div>Negative association</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--robust)"></div>ROBUST</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--explor);opacity:.6"></div>Exploratory</div>
  </div>
  <div class="graph-layout">
    <div class="card"><div id="sector-graph" style="height:520px"></div></div>
    <div class="side-panel" id="edge-panel">
      <h3>Edge detail</h3>
      <div class="side-empty">Click an edge or node label to see details.</div>
    </div>
  </div>
</div>

<!-- ── Section 2: Economic State Timeline ─────────────────────────────── -->
<div class="section">
  <div class="section-title">2. Economic State Timeline</div>
  <div class="section-note">
    Dominant economic state per sector per year, aggregated over all territories in the selected country.
    States are derived from observed enterprise-birth velocity: growth, acceleration, deceleration, stagnation, decline, recovery.
    Colour scale runs from expansion (blue/teal) to contraction (red/purple).
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:#4aa3ff"></div>Acceleration</div>
    <div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Growth</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ffd180"></div>Deceleration</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>Stagnation</div>
    <div class="legend-item"><div class="legend-dot" style="background:#b084f5"></div>Recovery</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Decline</div>
    <div class="legend-item"><div class="legend-dot" style="background:#1e2640"></div>Insufficient history</div>
  </div>
  <div class="controls">
    <label>Country <select id="state-country" onchange="renderStateHeatmap()">
      <option value="FR">France (FR)</option>
      <option value="NL">Netherlands (NL)</option>
      <option value="PT">Portugal (PT)</option>
    </select></label>
  </div>
  <div class="card"><div id="state-heatmap" style="height:400px"></div></div>
</div>

<!-- ── Section 3: Territory State Distribution ────────────────────────── -->
<div class="section">
  <div class="section-title">3. Territory State Distribution</div>
  <div class="section-note">
    Annual breakdown of territory states across all sectors. Shows how many territories are in each economic state per year.
  </div>
  <div class="controls">
    <label>Country <select id="dist-country" onchange="renderStateDistribution()">
      <option value="FR">France (FR)</option>
      <option value="NL">Netherlands (NL)</option>
      <option value="PT">Portugal (PT)</option>
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
  <div class="card"><div id="state-dist" style="height:380px"></div></div>
</div>

<!-- ── Section 4: Territory State Heatmap ─────────────────────────────── -->
<div class="section">
  <div class="section-title">4. Territory Dynamics</div>
  <div class="section-note">
    Average velocity (year-on-year enterprise-birth growth rate, averaged over sectors) per territory per year.
    Red = contraction, teal = expansion.
  </div>
  <div class="controls">
    <label>Country <select id="terr-country" onchange="renderTerritoryHeatmap()">
      <option value="NL">Netherlands (NL)</option>
      <option value="PT">Portugal (PT)</option>
      <option value="FR">France (FR — aggregated)</option>
    </select></label>
  </div>
  <div class="card"><div id="terr-heatmap" style="height:480px"></div></div>
</div>

<!-- ── Section 5: Provenance ──────────────────────────────────────────── -->
<div class="section" style="margin-top:36px;margin-bottom:24px;">
  <div class="section-title" style="font-size:15px;color:var(--muted)">Provenance</div>
  <div id="provenance-block" style="color:var(--muted);font-size:12px;line-height:1.7;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;margin-top:8px;"></div>
</div>

</div><!-- /wrap -->

<script>
// ── Embedded data ──────────────────────────────────────────────────────────
const EDGES = {edges_js};
const STATE_SUMMARY = {state_summary_js};
const TERRITORY_SUMMARY = {territory_summary_js};
const NODE_POS = {node_pos_js};
const SECTOR_LABELS = {sector_labels_js};
const MANIFEST = {manifest_js};

// ── Constants ──────────────────────────────────────────────────────────────
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
const COLORSCALE = [
  [0,'#1e2640'],[1/6,'#ef5350'],[2/6,'#b084f5'],
  [3/6,'#9aa4bf'],[4/6,'#ffd180'],[5/6,'#26a69a'],[1,'#4aa3ff']
];
const BASE_LAYOUT = {{
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font:{{color:'#eef2ff',family:'Inter,Segoe UI,Arial,sans-serif',size:12}},
  margin:{{l:50,r:20,t:30,b:40}},
  hoverlabel:{{bgcolor:'#20253a',bordercolor:'#30364f',font:{{color:'#eef2ff'}}}},
}};

// ── KPI bar ────────────────────────────────────────────────────────────────
function renderKPIs() {{
  const robustCount = EDGES.filter(e=>e.relation_class==='ROBUST').length;
  const explorCount = EDGES.filter(e=>e.relation_class==='MAIN_ONLY_EXPLORATORY').length;
  const kpiData = [
    {{v: MANIFEST.n_countries||3, l:'Countries (FR/NL/PT)'}},
    {{v: MANIFEST.n_territories||345, l:'Territories (NUTS3)'}},
    {{v: '9', l:'Sectors (A10 NACE)'}},
    {{v: robustCount, l:'ROBUST associations', cls:'color:var(--robust)'}},
    {{v: explorCount, l:'Exploratory (main only)', cls:'color:var(--explor)'}},
    {{v: MANIFEST.verdict==='SECTOR_PRECEDENCE_PROTOTYPE_READY' ? '✓ READY' : 'PENDING', l:'Prototype status', cls:'color:var(--good)'}},
  ];
  document.getElementById('kpi-bar').innerHTML = kpiData.map(k=>
    `<div class="kpi"><div class="v" style="${{k.cls||''}}">${{k.v}}</div><div class="l">${{k.l}}</div></div>`
  ).join('');
}}

// ── Sector graph ───────────────────────────────────────────────────────────
let selectedEdge = null;
const NODE_R = 0.15;

function getNodePos(sector) {{
  return NODE_POS[sector] || {{x:0, y:0}};
}}

function edgeOffset(sx, sy, tx, ty, offsetSign) {{
  const dx = tx-sx, dy = ty-sy;
  const dist = Math.sqrt(dx*dx+dy*dy) || 1;
  const ux = dx/dist, uy = dy/dist;
  // perpendicular offset for bidirectional edges
  const px = -uy * 0.06 * offsetSign, py = ux * 0.06 * offsetSign;
  return {{
    ax: sx + ux*NODE_R + px, ay: sy + uy*NODE_R + py,
    x:  tx - ux*NODE_R + px, y:  ty - uy*NODE_R + py,
  }};
}}

function renderGraph() {{
  const country = document.getElementById('graph-country').value;
  const showExplor = document.getElementById('show-explor').checked;

  const filteredEdges = EDGES.filter(e => {{
    if (e.country !== country) return false;
    if (e.relation_class === 'ROBUST') return true;
    if (e.relation_class === 'MAIN_ONLY_EXPLORATORY' && showExplor) return true;
    return false;
  }});

  // Count bidirectional pairs for offset
  const pairCount = {{}};
  filteredEdges.forEach(e => {{
    const fwd = e.source_sector+'->'+e.target_sector;
    const rev = e.target_sector+'->'+e.source_sector;
    pairCount[fwd] = (pairCount[fwd]||0)+1;
    if (!pairCount[rev]) pairCount[rev]=0;
  }});
  const pairIdx = {{}};

  // Node trace
  const nodeX = SECTORS.map(s => getNodePos(s).x);
  const nodeY = SECTORS.map(s => getNodePos(s).y);
  const nodeText = SECTORS.map(s => s + '<br><span style="font-size:9px">' + (SECTOR_LABELS[s]||s).split(' ')[0]+'</span>');
  const nodeHover = SECTORS.map(s => '<b>'+s+'</b><br>'+SECTOR_LABELS[s]);

  const nodeTrace = {{
    x: nodeX, y: nodeY,
    mode: 'markers+text',
    type: 'scatter',
    marker: {{size:30, color:'#20253a', line:{{color:'#4aa3ff', width:1.5}}}},
    text: SECTORS,
    textfont: {{size:11, color:'#eef2ff'}},
    textposition: 'middle center',
    hovertext: nodeHover,
    hovertemplate: '%{{hovertext}}<extra></extra>',
    name: 'sectors',
  }};

  // Annotations (arrows) for edges
  const annotations = [];
  const edgeTraces = [];
  filteredEdges.forEach((e,i) => {{
    const sp = getNodePos(e.source_sector), tp = getNodePos(e.target_sector);
    const key = e.source_sector+'->'+e.target_sector;
    pairIdx[key] = (pairIdx[key]||0)+1;
    const hasReverse = EDGES.some(e2=>e2.country===country&&e2.source_sector===e.target_sector&&e2.target_sector===e.source_sector);
    const offsetSign = hasReverse ? (pairIdx[key]%2===0 ? 1 : -1) : 0;
    const {{ax, ay, x, y}} = edgeOffset(sp.x, sp.y, tp.x, tp.y, offsetSign);
    const isRobust = e.relation_class === 'ROBUST';
    const color = e.sign==='positive' ? '#26a69a' : '#ef5350';
    const width = 1 + Math.abs(e.beta||0) * 10;
    const opacity = isRobust ? 0.9 : 0.5;

    // Line trace for hover
    edgeTraces.push({{
      x:[ax, x, null], y:[ay, y, null],
      mode:'lines', type:'scatter',
      line:{{color:color, width:width, dash: isRobust ? 'solid' : 'dash'}},
      opacity: opacity,
      hovertemplate: `<b>${{e.source_sector}} → ${{e.target_sector}}</b><br>`+
        `Country: ${{e.country}}<br>Window: ${{e.window_start}}–${{e.window_end}}<br>`+
        `β=${{e.beta.toFixed(3)}}, Δr²=${{e.delta_r2.toFixed(4)}}<br>`+
        `p_perm=${{e.p_perm.toFixed(3)}}, q_fdr=${{e.q_fdr.toFixed(3)}}<br>`+
        `Sign stability=${{e.bootstrap_sign_stability.toFixed(2)}}<br>`+
        `n=${{e.n_samples}}, Class: ${{e.relation_class}}<extra></extra>`,
      name: e.source_sector+'→'+e.target_sector,
      customdata: [i],
      showlegend: false,
    }});

    annotations.push({{
      x, y, ax, ay,
      xref:'x', yref:'y', axref:'x', ayref:'y',
      showarrow: true, arrowhead: 2,
      arrowsize: 1.2, arrowwidth: Math.max(1.5, width*0.7),
      arrowcolor: color,
      opacity: opacity,
    }});
  }});

  document.getElementById('edge-count-label').textContent =
    filteredEdges.length + ' edge(s) shown for ' + country;

  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    xaxis:{{range:[-1.6,1.6], showgrid:false, zeroline:false, showticklabels:false}},
    yaxis:{{range:[-1.45,1.45], showgrid:false, zeroline:false, showticklabels:false, scaleanchor:'x'}},
    annotations: annotations,
    showlegend: false,
    hovermode: 'closest',
    margin: {{l:10,r:10,t:10,b:10}},
    paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
    font:{{color:'#eef2ff',size:12}},
  }});

  const allTraces = [...edgeTraces, nodeTrace];
  Plotly.newPlot('sector-graph', allTraces, layout, {{responsive:true, displayModeBar:false}});

  // Click handler for edge detail
  document.getElementById('sector-graph').on('plotly_click', function(data) {{
    const pt = data.points[0];
    if (pt.data.customdata) {{
      const idx = pt.data.customdata[0];
      showEdgeDetail(filteredEdges[idx]);
    }}
  }});
}}

function showEdgeDetail(e) {{
  if (!e) {{
    document.getElementById('edge-panel').querySelector('.side-empty') &&
      (document.getElementById('edge-panel').innerHTML = '<h3>Edge detail</h3><div class="side-empty">Click an edge to see details.</div>');
    return;
  }}
  const classBadge = e.relation_class==='ROBUST'
    ? '<span class="badge badge-robust">ROBUST</span>'
    : '<span class="badge badge-explor">Exploratory</span>';
  const signBadge = e.sign==='positive'
    ? '<span class="badge badge-pos">Positive ↑</span>'
    : '<span class="badge badge-neg">Negative ↓</span>';
  document.getElementById('edge-panel').innerHTML = `
    <h3>${{e.source_sector}} → ${{e.target_sector}}</h3>
    <div style="margin-bottom:10px;">${{classBadge}} ${{signBadge}}</div>
    <div class="side-field"><span class="lbl">Country</span><span class="val">${{e.country}}</span></div>
    <div class="side-field"><span class="lbl">Window</span><span class="val">${{e.window_start}}–${{e.window_end}}</span></div>
    <div class="side-field"><span class="lbl">Source</span><span class="val">${{e.source_label}}</span></div>
    <div class="side-field"><span class="lbl">Target</span><span class="val">${{e.target_label}}</span></div>
    <div class="side-field"><span class="lbl">β (standardised)</span><span class="val">${{e.beta.toFixed(4)}}</span></div>
    <div class="side-field"><span class="lbl">Δr²</span><span class="val">${{e.delta_r2.toFixed(5)}}</span></div>
    <div class="side-field"><span class="lbl">p (permutation)</span><span class="val">${{e.p_perm.toFixed(3)}}</span></div>
    <div class="side-field"><span class="lbl">q (BH/FDR)</span><span class="val">${{e.q_fdr.toFixed(3)}}</span></div>
    <div class="side-field"><span class="lbl">Sign stability</span><span class="val">${{(e.bootstrap_sign_stability*100).toFixed(0)}}%</span></div>
    <div class="side-field"><span class="lbl">n (observations)</span><span class="val">${{e.n_samples}}</span></div>
    <div class="side-note">
      This edge expresses <em>predictive precedence</em>: lagged ${{e.source_sector}} growth
      associates with ${{e.target_sector}} enterprise-birth growth after controlling for own lag
      and removing territory/year fixed effects. Not a causal or intervention claim.
    </div>
  `;
}}

// ── Economic state heatmap ─────────────────────────────────────────────────
function renderStateHeatmap() {{
  const country = document.getElementById('state-country').value;
  const rows = STATE_SUMMARY.filter(r=>r.country===country);

  const sectors = [...new Set(rows.map(r=>r.sector_id))].sort();
  const years = [...new Set(rows.map(r=>r.observation_year))].sort((a,b)=>a-b);

  const zMatrix = sectors.map(sec =>
    years.map(yr => {{
      const row = rows.find(r=>r.sector_id===sec && r.observation_year===yr);
      return row ? (STATE_NUM[row.dominant_state]??null) : null;
    }})
  );
  const textMatrix = sectors.map(sec =>
    years.map(yr => {{
      const row = rows.find(r=>r.sector_id===sec && r.observation_year===yr);
      return row ? row.dominant_state.replace('_',' ') : '';
    }})
  );

  const trace = {{
    type:'heatmap', z:zMatrix, x:years, y:sectors,
    text:textMatrix, hovertemplate:'%{{y}} %{{x}}: <b>%{{text}}</b><extra></extra>',
    colorscale:COLORSCALE,
    zmin:-3, zmax:3,
    showscale:false, xgap:1.5, ygap:1.5,
  }};

  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    xaxis:{{tickmode:'linear', dtick:1, tickangle:-45}},
    yaxis:{{autorange:'reversed'}},
    title:{{text:'Economic states — '+country, font:{{size:14}}}},
    margin:{{l:50,r:20,t:40,b:60}},
  }});

  Plotly.newPlot('state-heatmap', [trace], layout, {{responsive:true, displayModeBar:false}});
}}

// ── State distribution (stacked bar) ──────────────────────────────────────
function renderStateDistribution() {{
  const country = document.getElementById('dist-country').value;
  const sector = document.getElementById('dist-sector').value;

  let rows;
  if (sector === 'ALL') {{
    // Use territory summary: one state per territory×year
    rows = TERRITORY_SUMMARY.filter(r=>r.country===country);
    // Group by year × state
    const byYear = {{}};
    rows.forEach(r => {{
      const k = r.observation_year;
      if (!byYear[k]) byYear[k]={{}};
      byYear[k][r.state] = (byYear[k][r.state]||0)+1;
    }});
    const years = Object.keys(byYear).map(Number).sort((a,b)=>a-b);
    const states = Object.keys(STATE_COLORS).filter(s=>s!=='insufficient_history');
    const traces = states.map(st => ({{
      type:'bar', name:st, x:years,
      y:years.map(yr=>(byYear[yr]?.[st]||0)),
      marker:{{color:STATE_COLORS[st]}},
    }}));
    traces.push({{
      type:'bar', name:'insuff.history', x:years,
      y:years.map(yr=>(byYear[yr]?.insufficient_history||0)),
      marker:{{color:STATE_COLORS['insufficient_history']}},
    }});
    const layout = Object.assign({{}}, BASE_LAYOUT, {{
      barmode:'stack', title:{{text:'Territory states — '+country+' (all sectors)',font:{{size:14}}}},
      xaxis:{{tickmode:'linear',dtick:1,tickangle:-45}}, margin:{{l:50,r:20,t:40,b:60}},
    }});
    Plotly.newPlot('state-dist', traces, layout, {{responsive:true, displayModeBar:false}});
  }} else {{
    // Use state_summary for specific sector
    rows = STATE_SUMMARY.filter(r=>r.country===country && r.sector_id===sector);
    const years = [...new Set(rows.map(r=>r.observation_year))].sort((a,b)=>a-b);
    const states = Object.keys(STATE_COLORS).filter(s=>s!=='insufficient_history');
    const traces = states.map(st => {{
      const vals = years.map(yr => {{
        const row = rows.find(r=>r.observation_year===yr);
        return row ? Math.round((row.pct_with_state[st]||0)*row.n_territories) : 0;
      }});
      return {{type:'bar', name:st, x:years, y:vals, marker:{{color:STATE_COLORS[st]}}}};
    }});
    const layout = Object.assign({{}}, BASE_LAYOUT, {{
      barmode:'stack', title:{{text:'Territory states — '+country+' / '+sector+' ('+SECTOR_LABELS[sector]+')',font:{{size:14}}}},
      xaxis:{{tickmode:'linear',dtick:1,tickangle:-45}}, margin:{{l:50,r:20,t:40,b:60}},
    }});
    Plotly.newPlot('state-dist', traces, layout, {{responsive:true, displayModeBar:false}});
  }}
}}

// ── Territory velocity heatmap ─────────────────────────────────────────────
function renderTerritoryHeatmap() {{
  const country = document.getElementById('terr-country').value;
  let rows = TERRITORY_SUMMARY.filter(r=>r.country===country);

  let territories = [...new Set(rows.map(r=>r.territory_id))].sort();
  const years = [...new Set(rows.map(r=>r.observation_year))].sort((a,b)=>a-b);

  // For FR (280 territories) cap at first 80 for readability
  const capped = country==='FR' && territories.length>80;
  if (capped) territories = territories.slice(0,80);

  const zMatrix = territories.map(t =>
    years.map(yr => {{
      const row = rows.find(r=>r.territory_id===t && r.observation_year===yr);
      return (row && row.avg_velocity!=null) ? row.avg_velocity : null;
    }})
  );
  const textMatrix = territories.map(t =>
    years.map(yr => {{
      const row = rows.find(r=>r.territory_id===t && r.observation_year===yr);
      return row ? (row.state||'').replace('_',' ') + (row.avg_velocity!=null ? ' (v='+row.avg_velocity.toFixed(3)+')' : '') : '';
    }})
  );

  const trace = {{
    type:'heatmap', z:zMatrix, x:years, y:territories,
    text:textMatrix, hovertemplate:'%{{y}} %{{x}}: <b>%{{text}}</b><extra></extra>',
    colorscale:[
      [0,'#ef5350'],[0.3,'#b084f5'],[0.45,'#9aa4bf'],
      [0.5,'#1e2640'],[0.55,'#9aa4bf'],[0.7,'#26a69a'],[1,'#4aa3ff']
    ],
    zmid:0, colorbar:{{title:'Velocity', tickfont:{{color:'#eef2ff'}}}},
    xgap:1, ygap:0.5,
  }};

  const h = Math.max(350, Math.min(700, territories.length * 12 + 80));
  document.getElementById('terr-heatmap').style.height = h+'px';

  const layout = Object.assign({{}}, BASE_LAYOUT, {{
    xaxis:{{tickmode:'linear',dtick:2,tickangle:-45}},
    yaxis:{{autorange:'reversed', tickfont:{{size:9}}}},
    title:{{text:'Territory velocity — '+country+(capped?' (first 80)':''), font:{{size:14}}}},
    margin:{{l:70,r:80,t:40,b:60}},
  }});

  Plotly.newPlot('terr-heatmap', [trace], layout, {{responsive:true, displayModeBar:false}});
}}

// ── Provenance ─────────────────────────────────────────────────────────────
function renderProvenance() {{
  document.getElementById('provenance-block').innerHTML =
    `<b>Version:</b> Observatory v${{MANIFEST.version || '0.3'}} &nbsp;|&nbsp;
    <b>Generated:</b> ${{MANIFEST.generated_at||'—'}} &nbsp;|&nbsp;
    <b>Verdict:</b> ${{MANIFEST.verdict||'—'}}<br>
    <b>Note:</b> ${{MANIFEST.provenance_note||''}}`;
}}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {{
  renderKPIs();
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
    logger.info("Dashboard written: %s (%d bytes)", output_path, len(html.encode("utf-8")))


def main() -> None:
    try:
        panel, manifest = build_v03()
        # Generate dashboard
        v03_dir = OUTPUT_DIR
        dash_path = (
            Path(__file__).resolve().parents[3]
            / "reports/dashboards/herald_observatory_v03_dashboard.html"
        )
        generate_dashboard(v03_dir, dash_path)
    except SystemExit:
        raise
    except Exception as exc:
        logger.exception("Build failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
