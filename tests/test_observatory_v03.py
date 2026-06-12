"""Comprehensive tests for HERALD Observatory v0.3 builder.

The builder runs once per session via a session-scoped fixture so the
expensive CSV rebuild is not repeated for each test.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(REPO_ROOT))

from src.data.european_panel.build_observatory_v03 import (
    VALID_A10,
    VALID_ECONOMIC_STATES,
    SECTOR_LABELS,
    NL_COROP_TO_NUTS3,
    build_v03,
    derive_robust_windows,
)

# ---------------------------------------------------------------------------
# Session-scoped fixture: build once, share across all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def v03_products(tmp_path_factory):
    """Run the builder once and return (panel, manifest, relations, summary, output_dir)."""
    output_dir = tmp_path_factory.mktemp("herald_observatory_v03")
    panel, manifest = build_v03(output_dir=output_dir)

    relations_path = output_dir / "herald_observatory_v03_sector_relations.json"
    summary_path = output_dir / "herald_observatory_v03_summary.json"

    relations_payload = json.loads(relations_path.read_text())
    summary = json.loads(summary_path.read_text())

    return panel, manifest, relations_payload, summary, output_dir


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


# ---------------------------------------------------------------------------
# Part A-3 fix: ROBUST_WINDOWS must be derived, not hardcoded
# ---------------------------------------------------------------------------

def test_robust_windows_not_hardcoded_constant():
    """ROBUST_WINDOWS must NOT be defined as a top-level constant in the source."""
    source = (REPO_ROOT / "src/data/european_panel/build_observatory_v03.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ROBUST_WINDOWS":
                    pytest.fail(
                        "ROBUST_WINDOWS is defined as a module-level constant. "
                        "It must be derived from covid_robust_edges.csv via derive_robust_windows()."
                    )


def test_derive_robust_windows_returns_correct_structure():
    """derive_robust_windows() must return dict with NL and PT, correct window counts."""
    windows = derive_robust_windows()
    assert isinstance(windows, dict)
    assert "NL" in windows, "NL missing from derived windows"
    assert "PT" in windows, "PT missing from derived windows"
    assert "FR" not in windows, "FR must not be in robust windows (0 robust edges)"
    # NL: 1 unique window
    assert len(windows["NL"]) == 1
    assert windows["NL"][0] == (2014, 2019)
    # PT: 3 unique windows
    assert len(windows["PT"]) == 3
    assert (2014, 2019) in windows["PT"]
    assert (2015, 2020) in windows["PT"]
    assert (2017, 2022) in windows["PT"]


def test_derive_robust_windows_fail_closed_on_wrong_counts(tmp_path):
    """derive_robust_windows() must fail closed if Phase 7 counts are inconsistent."""
    import pandas as pd
    bad_csv = tmp_path / "covid_robust_edges.csv"
    # Write a file with wrong counts (NL=2 instead of 3)
    df = pd.DataFrame({
        "country": ["NL", "NL", "PT"] * 3,
        "window_start": [2014] * 9,
        "window_end": [2019] * 9,
        "source_sector": ["FZ"] * 9,
        "target_sector": ["GI"] * 9,
        "beta_main": [0.2] * 9,
        "beta_wo20": [0.2] * 9,
    })
    bad_df = df.iloc[:4]  # NL=2, PT=2 — wrong
    bad_df.to_csv(bad_csv, index=False)
    with pytest.raises(SystemExit, match="FAIL_CLOSED"):
        derive_robust_windows(bad_csv)


def test_derive_robust_windows_fail_closed_on_empty(tmp_path):
    """derive_robust_windows() must fail closed if file is empty."""
    import pandas as pd
    empty_csv = tmp_path / "covid_robust_edges.csv"
    pd.DataFrame(columns=["country", "window_start", "window_end",
                           "source_sector", "target_sector"]).to_csv(empty_csv, index=False)
    with pytest.raises(SystemExit, match="FAIL_CLOSED"):
        derive_robust_windows(empty_csv)


def test_manifest_contains_derived_windows(v03_products):
    """Manifest must contain robust_windows derived from Phase 7 data."""
    _, manifest, *_ = v03_products
    rw = manifest.get("robust_windows", {})
    assert "NL" in rw
    assert "PT" in rw
    assert "FR" not in rw


# ---------------------------------------------------------------------------
# Part A-2 fix: Plotly dependency
# ---------------------------------------------------------------------------

DASH_PATH = REPO_ROOT / "reports" / "dashboards" / "herald_observatory_v03_dashboard.html"


def test_dashboard_plotly_dependency_declared():
    """Dashboard must either embed Plotly locally or explicitly document CDN dependency."""
    html = DASH_PATH.read_text(encoding="utf-8")
    uses_cdn = "cdn.plot.ly" in html
    if uses_cdn:
        # CDN fallback: must be documented in provenance section
        assert "CDN" in html, "CDN dependency used but not documented"
    else:
        # Local embed: verify Plotly source is present
        assert "plotly" in html[:5_000_000].lower(), "Plotly not found in embedded scripts"


def test_dashboard_no_undeclared_external_scripts():
    """Dashboard must not silently load external scripts beyond declared CDN."""
    html = DASH_PATH.read_text(encoding="utf-8")
    import re
    # Allow cdn.plot.ly (Plotly CDN fallback) — everything else external is unexpected
    external_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    for src in external_srcs:
        assert "cdn.plot.ly" in src or src.startswith("/"), \
            f"Unexpected external script: {src}"


def test_manifest_plotly_dependency_field(v03_products):
    """Manifest must record plotly_dependency field."""
    _, manifest, *_ = v03_products
    assert "plotly_dependency" in manifest
    assert manifest["plotly_dependency"] in ("local_embedded", "cdn_fallback")


# ---------------------------------------------------------------------------
# Part A-1 fix: Geographic map
# ---------------------------------------------------------------------------

def test_dashboard_has_geographic_map():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "choropleth" in html.lower(), "No choropleth trace found in dashboard"
    assert "GEO_FR" in html or "GEO_NL" in html, "No country GeoJSON embedded"


def test_dashboard_embeds_three_country_geojsons():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "GEO_FR" in html, "FR GeoJSON missing from dashboard"
    assert "GEO_NL" in html, "NL GeoJSON missing from dashboard"
    assert "GEO_PT" in html, "PT GeoJSON missing from dashboard"


def test_dashboard_has_territory_system_labels():
    """Dashboard must clearly label ZE2020, COROP, NUTS3 territorial systems."""
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "ZE2020" in html, "ZE2020 label missing"
    assert "COROP" in html, "COROP label missing"
    assert "NUTS3" in html, "NUTS3 label missing"


def test_dashboard_geographic_not_mixed_with_sector_graph():
    """Sector graph and territory map must be semantically separate (no mixing note present)."""
    html = DASH_PATH.read_text(encoding="utf-8")
    # The dashboard must warn about this distinction
    assert "not localised to individual territories" in html or \
           "not localized to individual territories" in html, \
        "Missing warning that sector→sector edges are country-level, not territory-level"


def test_nl_corop_mapping_complete():
    """NL COROP→NUTS3 mapping must cover all 40 COROP regions."""
    assert len(NL_COROP_TO_NUTS3) == 40
    panel_ids = {f"CR{str(i).zfill(2)}" for i in range(1, 41)}
    assert set(NL_COROP_TO_NUTS3.keys()) == panel_ids
    # All NUTS3 codes must start with NL
    for panel_id, nuts3 in NL_COROP_TO_NUTS3.items():
        assert nuts3.startswith("NL"), f"{panel_id} maps to non-NL code: {nuts3}"


def test_dashboard_has_year_country_filter():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "map-country" in html, "map-country filter missing"
    assert "map-year" in html, "map-year filter missing"
    assert "map-sector" in html, "map-sector filter missing"
    assert "map-metric" in html, "map-metric filter missing"


def test_dashboard_territory_click_side_panel():
    """Dashboard must have territory click handler and side panel."""
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "plotly_click" in html, "No plotly_click handler found"
    assert "map-side" in html, "map-side panel missing"


def test_portugal_map_is_mainland_only(v03_products):
    """The map excludes Azores/Madeira without deleting them from the panel."""
    panel, *_ = v03_products
    pt_ids = panel.loc[panel["country"].eq("PT"), "territory_id"].astype(str)
    assert pt_ids.str.startswith(("PT_20", "PT_30")).any()

    html = DASH_PATH.read_text(encoding="utf-8")
    assert '"panel_id": "PT_200"' not in html
    assert '"panel_id": "PT_300"' not in html
    assert "mainland territories" in html


def test_map_identifies_sector_for_each_territory():
    """Map colour must be traceable to a selected or most-dynamic sector."""
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "largest absolute change shown" in html
    assert "shownSector" in html
    assert "sector=" in html


# ---------------------------------------------------------------------------
# Part B: France ZE scale — no new HPC needed (Phase 7 already used ZE2020)
# ---------------------------------------------------------------------------

def test_france_uses_ze2020_in_panel():
    """Observatory v02 and v03 must use ZE2020 (functional zones) for France, not NUTS3."""
    panel_path = REPO_ROOT / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
    if not panel_path.exists():
        pytest.skip("v02 panel not available")
    panel = pd.read_csv(panel_path, low_memory=False,
                        usecols=["country", "region_system", "territory_id"])
    fr = panel[panel["country"] == "FR"]
    assert fr["region_system"].unique().tolist() == ["ZE2020"], \
        f"France must use ZE2020 region_system, got: {fr['region_system'].unique()}"
    assert fr["territory_id"].nunique() == 280, \
        f"Expected 280 ZEs for France, got {fr['territory_id'].nunique()}"


def test_france_ze_scale_distinct_from_nuts3():
    """ZE2020 and NUTS3 must not be mixed in the panel — each country has a single system."""
    panel_path = REPO_ROOT / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
    if not panel_path.exists():
        pytest.skip("v02 panel not available")
    panel = pd.read_csv(panel_path, low_memory=False,
                        usecols=["country", "region_system"])
    per_country = panel.groupby("country")["region_system"].nunique()
    for country, n_systems in per_country.items():
        assert n_systems == 1, f"{country} has {n_systems} region systems (must be 1)"


# ---------------------------------------------------------------------------
# Schema / correctness tests (unchanged from v0.3-initial)
# ---------------------------------------------------------------------------

REQUIRED_PANEL_COLUMNS = {
    "country", "territory_id", "meta_nuts3_code", "territory_name",
    "region_system", "sector_id", "sector_label", "target_concept",
    "source_label", "observation_year", "observed_value", "lag1_value",
    "persistence_forecast", "ridge_forecast", "forecast_lower", "forecast_upper",
    "forecast_method", "forecast_status", "economic_state", "velocity",
    "acceleration", "data_evidence_tier", "forecast_evidence_tier",
    "graph_evidence_tier", "territorial_graph_available", "sector_graph_available",
    "structural_mask", "observation_mask", "data_quality_flags",
}


def test_schema_v03_panel(v03_products):
    panel, *_ = v03_products
    missing = REQUIRED_PANEL_COLUMNS - set(panel.columns)
    assert not missing, f"Missing columns: {missing}"
    extra = set(panel.columns) - REQUIRED_PANEL_COLUMNS
    assert not extra, f"Extra columns: {extra}"


def test_panel_row_count(v03_products):
    panel, *_ = v03_products
    assert len(panel) == 45945, f"Expected 45945 rows, got {len(panel)}"


def test_determinism(tmp_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    out1.mkdir()
    out2.mkdir()
    panel1, _ = build_v03(output_dir=out1)
    panel2, _ = build_v03(output_dir=out2)
    csv1 = panel1.to_csv(index=False).encode("utf-8")
    csv2 = panel2.to_csv(index=False).encode("utf-8")
    assert _sha256_bytes(csv1) == _sha256_bytes(csv2), "Panel is not deterministic"


def test_panel_checksum_in_manifest(v03_products):
    _, manifest, _, _, output_dir = v03_products
    panel_path = output_dir / "herald_observatory_v03_panel.csv"
    actual = _sha256_file(panel_path)
    assert manifest["panel_sha256"] == actual


def test_valid_a10_codes(v03_products):
    panel, *_ = v03_products
    bad = set(panel["sector_id"].unique()) - VALID_A10
    assert not bad, f"Invalid sector_id codes: {bad}"


def test_exactly_12_robust_relations(v03_products):
    _, _, relations_payload, *_ = v03_products
    robust = [e for e in relations_payload["edges"] if e["relation_class"] == "ROBUST"]
    assert len(robust) == 12, f"Expected 12 ROBUST, got {len(robust)}"


def test_nl_3_pt_9_fr_0_robust(v03_products):
    _, _, relations_payload, *_ = v03_products
    robust = [e for e in relations_payload["edges"] if e["relation_class"] == "ROBUST"]
    nl = sum(1 for e in robust if e["country"] == "NL")
    pt = sum(1 for e in robust if e["country"] == "PT")
    fr = sum(1 for e in robust if e["country"] == "FR")
    assert nl == 3, f"Expected 3 NL, got {nl}"
    assert pt == 9, f"Expected 9 PT, got {pt}"
    assert fr == 0, f"Expected 0 FR, got {fr}"


def test_no_self_edges(v03_products):
    _, _, relations_payload, *_ = v03_products
    self_edges = [e for e in relations_payload["edges"] if e["source_sector"] == e["target_sector"]]
    assert not self_edges, f"Self-edges: {self_edges}"


def test_no_duplicate_relations(v03_products):
    _, _, relations_payload, *_ = v03_products
    seen: set[tuple] = set()
    dups: list[tuple] = []
    for e in relations_payload["edges"]:
        k = (e["country"], e["window_start"], e["window_end"], e["source_sector"], e["target_sector"])
        if k in seen:
            dups.append(k)
        seen.add(k)
    assert not dups, f"Duplicate edges: {dups}"


def test_25_total_main_edges(v03_products):
    _, _, relations_payload, *_ = v03_products
    assert len(relations_payload["edges"]) == 25
    main_only = [e for e in relations_payload["edges"] if e["relation_class"] == "MAIN_ONLY_EXPLORATORY"]
    assert len(main_only) == 13


def test_economic_states_valid(v03_products):
    panel, *_ = v03_products
    bad = set(panel["economic_state"].dropna().unique()) - VALID_ECONOMIC_STATES
    assert not bad, f"Invalid states: {bad}"


def test_sector_graph_available_fr_zero(v03_products):
    panel, *_ = v03_products
    fr = panel[panel["country"] == "FR"]
    non_zero = fr[fr["sector_graph_available"] != 0]
    assert len(non_zero) == 0


def test_sector_graph_available_nl_pt_in_windows(v03_products):
    """sector_graph_available must use derived windows, not hardcoded values."""
    panel, *_ = v03_products
    windows = derive_robust_windows()
    for country, wins in windows.items():
        sub = panel[(panel["country"] == country) & (panel["structural_mask"] == 1)].copy()
        sub["in_window"] = sub["observation_year"].apply(
            lambda y: any(s <= y <= e for s, e in wins)
        )
        wrong = sub[sub["in_window"] & (sub["sector_graph_available"] != 1)]
        assert len(wrong) == 0, f"{country}: {len(wrong)} rows in robust window with sga!=1"
        wrong_out = sub[~sub["in_window"] & (sub["sector_graph_available"] != 0)]
        assert len(wrong_out) == 0, f"{country}: {len(wrong_out)} rows outside window with sga!=0"


def test_no_causal_language(v03_products):
    """Provenance note must not contain causal language outside the approved negation."""
    _, manifest, *_ = v03_products
    note = manifest.get("provenance_note", "")
    approved = "No structural causality, mechanism, or intervention claim is supported."
    sanitised = note.replace(approved, "")
    bad = [w for w in ["causal", "causes", "Granger", "intervention"] if w.lower() in sanitised.lower()]
    assert not bad, f"Causal language found: {bad}"


def test_manifest_has_provenance(v03_products):
    _, manifest, *_ = v03_products
    assert "provenance_note" in manifest
    assert manifest["provenance_note"]


def test_manifest_has_checksums(v03_products):
    _, manifest, *_ = v03_products
    assert "panel_sha256" in manifest
    assert "v02_panel_sha256" in manifest
    assert manifest["v02_panel_sha256"] == "a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e"


def test_sector_relations_json_valid(v03_products):
    _, _, relations_payload, *_ = v03_products
    assert "edges" in relations_payload
    required = {
        "country", "window_start", "window_end",
        "source_sector", "source_label", "target_sector", "target_label",
        "beta", "delta_r2", "p_perm", "q_fdr", "bootstrap_sign_stability",
        "n_samples", "relation_class", "sign", "scenario",
    }
    for i, edge in enumerate(relations_payload["edges"]):
        missing = required - set(edge.keys())
        assert not missing, f"Edge {i} missing fields: {missing}"


def test_signs_correct(v03_products):
    _, _, relations_payload, *_ = v03_products
    covid_robust_path = REPO_ROOT / "data/processed/sector_precedence_results/covid_robust_edges.csv"
    robust_ref = pd.read_csv(covid_robust_path)
    ref_lookup = {
        (r["country"], int(r["window_start"]), int(r["window_end"]),
         r["source_sector"], r["target_sector"]): float(r["beta_main"])
        for _, r in robust_ref.iterrows()
    }
    for edge in [e for e in relations_payload["edges"] if e["relation_class"] == "ROBUST"]:
        k = (edge["country"], edge["window_start"], edge["window_end"],
             edge["source_sector"], edge["target_sector"])
        assert k in ref_lookup, f"ROBUST edge not in covid_robust_edges.csv: {k}"
        ref_beta = ref_lookup[k]
        assert (edge["beta"] >= 0) == (ref_beta >= 0), f"Sign mismatch for {k}"
        assert edge["sign"] == ("positive" if ref_beta >= 0 else "negative")


def test_no_promoted_robust_from_fr(v03_products):
    _, _, relations_payload, *_ = v03_products
    fr_robust = [e for e in relations_payload["edges"]
                 if e["country"] == "FR" and e["relation_class"] == "ROBUST"]
    assert len(fr_robust) == 0


def test_manifest_decision(v03_products):
    _, manifest, *_ = v03_products
    assert manifest.get("verdict") == "SECTOR_PRECEDENCE_PROTOTYPE_READY"


def test_summary_json_valid(v03_products):
    _, _, _, summary, _ = v03_products
    assert "state_summary" in summary
    assert "territory_summary" in summary
    assert len(summary["state_summary"]) > 0
    assert len(summary["territory_summary"]) > 0


# ── Dashboard tests ──────────────────────────────────────────────────────

def test_dashboard_file_exists():
    assert DASH_PATH.is_file()


def test_dashboard_is_valid_html():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html


def test_dashboard_has_plotly():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "plotly" in html.lower()


def test_dashboard_embeds_edges():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "ROBUST" in html
    assert "MAIN_ONLY_EXPLORATORY" in html


def test_dashboard_has_all_sections():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "Sector Precedence" in html
    assert "Economic State Timeline" in html
    assert "Territory State Distribution" in html
    assert "Territory Dynamics" in html
    assert "Territorial Map" in html


def test_dashboard_no_causal_claim():
    import re
    html = DASH_PATH.read_text(encoding="utf-8")
    # Remove embedded script blocks (Plotly JS may contain 'causes' in WebGL comments)
    no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    stripped = no_scripts.replace(
        "No structural causality, mechanism, or intervention claim is supported.", ""
    ).replace(
        "No structural causality, mechanism, or intervention claim is implied.", ""
    ).replace("Not a causal or intervention claim.", "").replace(
        "no structural causality claim", ""
    )
    for word in ["causes", "Granger causality", "intervention effect"]:
        assert word not in stripped, f"Causal language found in dashboard HTML: '{word}'"


def test_dashboard_provenance_present():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "DEC-034" in html
    assert "provenance" in html.lower() or "MANIFEST" in html


def test_dashboard_has_country_filter():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "map-country" in html or "graph-country" in html or "state-country" in html
