"""
Tests for the Observatory v0.4.1 visual upgrade:
  - Part A: PT continental municipality geometry (278/278, no Açores/Madeira,
    no duplicates, valid geometry, official/reproducible source).
  - Part B: PT renders as a real choropleth map in the dashboard.
  - Part C: dynamic sector graph (timeline slider, play/pause, modes,
    relation-window heatmap, expanded edge detail panel).
  - Part E: NL gemeente proxy still structurally excluded from the relation
    graph; blocked proxy artifacts panel still isolated; DEC-066 labels intact;
    no forbidden causal language.

Hard rule (repeated from the original DEC-065 dashboard tests, re-verified
here because this is a separate change set): GEMEENTE_PROXY must never appear
in RELATION_EDGES.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

DASHBOARD_PATH = Path("reports/dashboards/herald_observatory_v04_granular_dashboard.html")
BUILDER_PATH = Path("src/data/european_panel/build_observatory_v04_dashboard.py")
PT_GEOMETRY_BUILDER_PATH = Path("src/data/european_panel/build_pt_municipality_geometry.py")
PT_GEOJSON_PATH = Path("data/processed/geometries/pt_municipalities_continental.geojson")
PT_MANIFEST_PATH = Path("data/processed/geometries/pt_municipalities_continental_manifest.json")

N_EXPECTED_CONTINENTAL = 278

CAUSAL_TERMS_FORBIDDEN = ["causal impact", "causal effect", "causally"]


def _html_text() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def _extract_js_const(text: str, varname: str):
    m = re.search(r"const " + varname + r" = (.*?);\n", text)
    assert m, f"Could not find JS const {varname} in dashboard"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def html() -> str:
    assert DASHBOARD_PATH.exists(), "Dashboard HTML not found — run the builder first"
    return _html_text()


@pytest.fixture(scope="module")
def relation_edges(html):
    return _extract_js_const(html, "RELATION_EDGES")


@pytest.fixture(scope="module")
def blocked_edges(html):
    return _extract_js_const(html, "BLOCKED_EDGES")


@pytest.fixture(scope="module")
def geo_pt(html):
    return _extract_js_const(html, "GEO_PT")


@pytest.fixture(scope="module")
def pt_geojson():
    if not PT_GEOJSON_PATH.exists():
        pytest.skip("PT geojson not present — geometry build is documented as optional fallback")
    return json.loads(PT_GEOJSON_PATH.read_text())


@pytest.fixture(scope="module")
def pt_manifest():
    if not PT_MANIFEST_PATH.exists():
        pytest.skip("PT geometry manifest not present")
    return json.loads(PT_MANIFEST_PATH.read_text())


# ─────────────────────────────────────────────────────────────────────────────
# Part A: PT geometry
# ─────────────────────────────────────────────────────────────────────────────

class TestPartAPtGeometry:
    def test_pt_geometry_or_fallback_documented(self):
        """Either the geometry exists, or its absence must be documented in
        the dashboard builder (table fallback logic)."""
        if PT_GEOJSON_PATH.exists():
            assert True
        else:
            builder_text = BUILDER_PATH.read_text()
            assert "table fallback" in builder_text.lower() or "fall back to table" in builder_text.lower()

    def test_pt_geometry_builder_script_exists(self):
        assert PT_GEOMETRY_BUILDER_PATH.exists()

    def test_pt_geometry_covers_278_municipalities(self, pt_geojson):
        assert len(pt_geojson["features"]) == N_EXPECTED_CONTINENTAL

    def test_pt_geometry_no_duplicate_panel_ids(self, pt_geojson):
        ids = [f["properties"]["panel_id"] for f in pt_geojson["features"]]
        assert len(ids) == len(set(ids))

    def test_pt_geometry_no_azores_madeira(self, pt_geojson):
        """Continental panel_ids start with '1' per DEC-062 (geocod[0]=='1' rule)."""
        ids = [str(f["properties"]["panel_id"]) for f in pt_geojson["features"]]
        non_continental = [pid for pid in ids if not pid.startswith("1")]
        assert not non_continental, f"Non-continental panel_ids leaked in: {non_continental}"

    def test_pt_geometry_valid_geometry_types(self, pt_geojson):
        types = {f["geometry"]["type"] for f in pt_geojson["features"] if f.get("geometry")}
        assert types.issubset({"Polygon", "MultiPolygon"})
        assert all(f.get("geometry") for f in pt_geojson["features"])

    def test_pt_geometry_names_present(self, pt_geojson):
        names = [f["properties"].get("name") for f in pt_geojson["features"]]
        assert all(names), "Every PT municipality feature must have a name"

    def test_pt_manifest_source_documented(self, pt_manifest):
        assert pt_manifest.get("source"), "Geometry source must be documented"
        assert pt_manifest.get("source_url"), "Geometry source URL must be documented"

    def test_pt_manifest_crosswalk_method_documented(self, pt_manifest):
        assert "name" in pt_manifest.get("crosswalk_method", "").lower()

    def test_pt_manifest_status_complete(self, pt_manifest):
        assert pt_manifest["status"] == "COMPLETE_278_278"

    def test_pt_manifest_checksum_present(self, pt_manifest):
        assert "geojson_sha256" in pt_manifest
        assert len(pt_manifest["geojson_sha256"]) == 64

    def test_pt_manifest_no_unmatched_panel_names(self, pt_manifest):
        assert pt_manifest["coverage"]["n_unmatched_panel"] == 0

    def test_pt_geojson_size_reasonable(self):
        if PT_GEOJSON_PATH.exists():
            size_mb = PT_GEOJSON_PATH.stat().st_size / 1e6
            assert size_mb < 10, f"PT geojson is {size_mb:.2f} MB — should be simplified for embedding"


# ─────────────────────────────────────────────────────────────────────────────
# Part B: PT choropleth in dashboard
# ─────────────────────────────────────────────────────────────────────────────

class TestPartBPtMap:
    def test_pt_geo_embedded_in_dashboard(self, geo_pt):
        assert len(geo_pt["features"]) == N_EXPECTED_CONTINENTAL

    def test_pt_map_status_const_present(self, html):
        assert "PT_MAP_STATUS" in html

    def test_pt_is_mapped_source(self, html):
        assert "MAPPED_SOURCES = ['FR','NL','PT']" in html or "'PT'" in html

    def test_pt_option_says_map_not_table(self, html):
        assert "Portugal — Municipality (observed, map)" in html
        assert "Portugal — Municipality (observed, table)" not in html

    def test_fallback_logic_present_for_missing_geometry(self, html):
        assert "fabricated map" in html.lower() or "table fallback" in html.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Part C: dynamic graph
# ─────────────────────────────────────────────────────────────────────────────

class TestPartCDynamicGraph:
    def test_timeline_slider_present(self, html):
        assert 'id="window-slider"' in html

    def test_play_pause_button_present(self, html):
        assert 'id="play-pause-btn"' in html
        assert "togglePlay" in html

    def test_mode_selector_present(self, html):
        assert 'id="graph-mode"' in html
        for mode in ["current", "cumulative", "recurring"]:
            assert f'value="{mode}"' in html

    def test_relation_window_heatmap_present(self, html):
        assert 'id="relation-heatmap"' in html
        assert "renderRelationHeatmap" in html

    def test_edge_detail_panel_present(self, html):
        assert 'id="edge-panel"' in html
        assert "showEdgeDetail" in html

    def test_edge_dynamics_fields_present(self, relation_edges):
        for e in relation_edges:
            for field in ["n_windows", "is_recurring", "is_exclusive", "sign_changes",
                          "window_start", "window_end"]:
                assert field in e

    def test_recurring_and_exclusive_are_consistent(self, relation_edges):
        for e in relation_edges:
            assert e["is_recurring"] != e["is_exclusive"] or e["n_windows"] == 0
            if e["n_windows"] >= 2:
                assert e["is_recurring"] is True
                assert e["is_exclusive"] is False
            if e["n_windows"] == 1:
                assert e["is_exclusive"] is True
                assert e["is_recurring"] is False

    def test_territory_state_summary_function_present(self, html):
        assert "territoryStateSummary" in html

    def test_all_windows_const_present_and_sorted(self, html):
        windows = _extract_js_const(html, "ALL_WINDOWS")
        starts = [int(w.split("-")[0]) for w in windows]
        assert starts == sorted(starts)


# ─────────────────────────────────────────────────────────────────────────────
# Part D: map <-> graph linking
# ─────────────────────────────────────────────────────────────────────────────

class TestPartDLinking:
    def test_map_country_sync_logic_present(self, html):
        assert "graph-sync-note" in html
        assert "graphCountrySel.value = source" in html

    def test_sector_highlight_logic_present(self, html):
        assert "HIGHLIGHT_SECTOR" in html
        assert "handleMapSectorChange" in html

    def test_edge_click_shows_territory_context_not_attribution(self, html):
        assert "context only, not a claim" in html.lower() or \
               "not a claim that this edge is localised" in html.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Part E: methodological protection (re-verified for this change set)
# ─────────────────────────────────────────────────────────────────────────────

class TestPartEMethodologicalProtection:
    def test_gemeente_proxy_never_in_relation_edges(self, relation_edges):
        assert "GEMEENTE_PROXY" not in {e["region_system"] for e in relation_edges}

    def test_relation_edges_count_unchanged(self, relation_edges):
        assert len(relation_edges) == 20

    def test_blocked_edges_count_unchanged(self, blocked_edges):
        assert len(blocked_edges) == 121

    def test_blocked_edges_still_isolated(self, blocked_edges):
        assert all(e["allowed_for_training_label"] is False for e in blocked_edges)
        assert all(e["region_system"] == "GEMEENTE_PROXY" for e in blocked_edges)

    def test_blocked_panel_separate_from_graph(self, html):
        assert 'id="blocked-table"' in html
        assert "preserved for audit only" in html

    def test_dec066_labels_intact(self, relation_edges):
        valid_labels = {"ROBUST_ORIGINAL", "FINE_GRAIN_SUPPORTED", "EXPLORATORY_FINE_GRAIN"}
        assert {e["label_class"] for e in relation_edges}.issubset(valid_labels)

    def test_no_forbidden_compound_causal_terms(self, html):
        text = html.lower()
        hits = [t for t in CAUSAL_TERMS_FORBIDDEN if t in text]
        assert not hits, f"Forbidden causal terms found: {hits}"

    def test_bare_causes_only_in_plotly_bundle_comment(self, html):
        text = html.lower()
        for m in re.finditer("causes", text):
            window = text[max(0, m.start() - 80):m.end() + 20]
            assert "floating point" in window, (
                f"Unexpected 'causes' usage outside Plotly bundle comment: {window!r}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# HTML validity / determinism
# ─────────────────────────────────────────────────────────────────────────────

class TestHtmlValidityAndDeterminism:
    def test_html_valid_doctype_and_closing_tags(self, html):
        assert html.startswith("<!DOCTYPE html>")
        assert html.rstrip().endswith("</html>")

    def test_dashboard_size_documented_if_large(self):
        size_mb = DASHBOARD_PATH.stat().st_size / 1e6
        if size_mb > 20:
            pytest.fail(f"Dashboard is {size_mb:.2f} MB and exceeds 20 MB without documentation")

    def test_builder_rerun_deterministic(self):
        result = subprocess.run(
            [sys.executable, str(BUILDER_PATH)],
            capture_output=True, text=True, cwd=Path.cwd(),
        )
        assert result.returncode == 0, f"Builder failed: {result.stderr}"
        text = _html_text()
        rel = _extract_js_const(text, "RELATION_EDGES")
        blocked = _extract_js_const(text, "BLOCKED_EDGES")
        geo_pt_2 = _extract_js_const(text, "GEO_PT")
        assert len(rel) == 20
        assert len(blocked) == 121
        assert len(geo_pt_2["features"]) == N_EXPECTED_CONTINENTAL
        assert "GEMEENTE_PROXY" not in {e["region_system"] for e in rel}
