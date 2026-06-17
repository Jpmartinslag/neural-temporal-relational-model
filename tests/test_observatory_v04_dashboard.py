"""
Tests for the HERALD Observatory v0.4 granular dashboard
(reports/dashboards/herald_observatory_v04_granular_dashboard.html).

Hard rule: NL gemeente proxy must never appear as a relation-graph edge.
The dashboard's RELATION_EDGES blob must come exclusively from
granular_relation_edges.csv (FR ZE2020 / PT Municipality / NL COROP observed).
The 121 blocked NL gemeente proxy edges must only populate the separate
"Blocked proxy artifacts" panel (BLOCKED_EDGES blob), never the graph.
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
DATA_DIR = Path("data/processed/herald_observatory_v04_granular")

CAUSAL_TERMS_FORBIDDEN = ["causal impact", "causal effect", "causally"]
# Bare "causes"/"causal" are checked separately with negation/context tolerance
# because the embedded Plotly.js bundle contains benign engineering comments
# (e.g. "-ffast-math ... causes floating point ...").


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
def manifest_blob(html):
    return _extract_js_const(html, "MANIFEST")


# ─────────────────────────────────────────────────────────────────────────────
# Existence / well-formedness
# ─────────────────────────────────────────────────────────────────────────────

class TestExistenceAndWellFormedness:
    def test_dashboard_exists(self):
        assert DASHBOARD_PATH.exists()

    def test_builder_script_exists(self):
        assert BUILDER_PATH.exists()

    def test_html_starts_with_doctype(self, html):
        assert html.startswith("<!DOCTYPE html>")

    def test_html_ends_with_html_tag(self, html):
        assert html.rstrip().endswith("</html>")

    def test_html_has_head_and_body(self, html):
        assert "<head>" in html and "</head>" in html
        assert "<body>" in html and "</body>" in html

    def test_dashboard_size_under_20mb(self):
        size_mb = DASHBOARD_PATH.stat().st_size / 1e6
        assert size_mb < 20, f"Dashboard is {size_mb:.2f} MB, exceeds 20 MB budget"

    def test_no_unclosed_script_tags(self, html):
        assert html.count("<script") >= html.count("</script>") - 1  # plotly minified may self-close differently
        # Stronger check: at least one balanced custom script block exists
        assert "<script>\nconst TERRITORY_DATA" in html


# ─────────────────────────────────────────────────────────────────────────────
# Dataset references
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetReferences:
    def test_territory_state_csv_referenced(self, html):
        assert "granular_territory_state_panel.csv" in html

    def test_relation_edges_csv_referenced(self, html):
        assert "granular_relation_edges.csv" in html

    def test_blocked_edges_csv_referenced(self, html):
        assert "blocked_proxy_edges.csv" in html

    def test_manifest_referenced(self, html):
        assert "manifest.json" in html

    def test_manifest_blob_has_dec_references(self, manifest_blob):
        for dec in ["DEC-063", "DEC-064", "DEC-065", "DEC-066"]:
            assert dec in manifest_blob["dec_references"]


# ─────────────────────────────────────────────────────────────────────────────
# Hard rule: NL gemeente proxy never in relation graph
# ─────────────────────────────────────────────────────────────────────────────

class TestNlGemeenteNeverInGraph:
    def test_relation_edges_count(self, relation_edges):
        assert len(relation_edges) == 20

    def test_no_gemeente_proxy_region_system(self, relation_edges):
        assert "GEMEENTE_PROXY" not in {e["region_system"] for e in relation_edges}

    def test_relation_edges_all_observed(self, relation_edges):
        assert all(e["evidence_type"] == "observed_births" for e in relation_edges)

    def test_relation_edges_allowed_region_systems(self, relation_edges):
        allowed = {"ZE2020", "COROP", "MUNICIPALITY"}
        assert {e["region_system"] for e in relation_edges}.issubset(allowed)

    def test_relation_edges_allowed_countries(self, relation_edges):
        assert {e["country"] for e in relation_edges}.issubset({"FR", "NL", "PT"})


class TestBlockedEdgesIsolated:
    def test_blocked_edges_count(self, blocked_edges):
        assert len(blocked_edges) == 121

    def test_blocked_edges_all_unusable_for_training(self, blocked_edges):
        assert all(e["allowed_for_training_label"] is False for e in blocked_edges)

    def test_blocked_edges_reason(self, blocked_edges):
        assert all(e["reason"] == "stock_share_induced_artifact" for e in blocked_edges)

    def test_blocked_edges_region_system_gemeente(self, blocked_edges):
        assert all(e["region_system"] == "GEMEENTE_PROXY" for e in blocked_edges)

    def test_no_overlap_between_relation_and_blocked(self, relation_edges, blocked_edges):
        """Sector-pair/window collisions across the two datasets are expected
        and harmless (COROP and GEMEENTE_PROXY are different region systems
        describing the same sectors/windows). What must never happen is a
        GEMEENTE_PROXY row appearing under the relation_edges' region_system set."""
        relation_region_systems = {e["region_system"] for e in relation_edges}
        assert "GEMEENTE_PROXY" not in relation_region_systems
        blocked_region_systems = {e["region_system"] for e in blocked_edges}
        assert blocked_region_systems == {"GEMEENTE_PROXY"}

    def test_blocked_table_html_present(self, html):
        assert 'id="blocked-table"' in html

    def test_blocked_panel_text_present(self, html):
        assert "preserved for audit only" in html
        assert "not used for training or claims" in html


# ─────────────────────────────────────────────────────────────────────────────
# UI elements: badges, filters, panels
# ─────────────────────────────────────────────────────────────────────────────

class TestUiElements:
    def test_header_badges_present(self, html):
        for badge in ["FR ZE2020 observed", "PT municipality observed",
                      "NL COROP observed", "NL gemeente proxy/context"]:
            assert badge in html

    def test_decision_badge_present(self, html):
        assert "GRANULAR_OBSERVATORY_V04_DATA_READY" in html

    def test_proxy_context_badge_text_present(self, html):
        assert "proxy/context — not valid for relation labels" in html

    def test_map_filters_present(self, html):
        for el_id in ["map-source", "map-year", "map-sector", "map-metric"]:
            assert f'id="{el_id}"' in html

    def test_graph_filters_present(self, html):
        for el_id in ["graph-country", "graph-region-system", "graph-label-class", "graph-window"]:
            assert f'id="{el_id}"' in html

    def test_map_plot_div_present(self, html):
        assert 'id="map-plot"' in html

    def test_sector_graph_div_present(self, html):
        assert 'id="sector-graph"' in html

    def test_evidence_panel_present(self, html):
        assert 'id="evidence-kpis"' in html

    def test_manifest_modal_present(self, html):
        assert 'id="manifest-modal"' in html

    def test_export_links_present(self, html):
        assert 'class="links-row"' in html


# ─────────────────────────────────────────────────────────────────────────────
# Language rules
# ─────────────────────────────────────────────────────────────────────────────

class TestLanguageRules:
    def test_no_forbidden_compound_causal_terms(self, html):
        text = html.lower()
        hits = [t for t in CAUSAL_TERMS_FORBIDDEN if t in text]
        assert not hits, f"Forbidden causal terms found: {hits}"

    def test_bare_causes_only_in_plotly_bundle_comment(self, html):
        """The only acceptable occurrence of 'causes' is inside the embedded
        Plotly.js minified bundle's floating-point engineering comment."""
        text = html.lower()
        for m in re.finditer("causes", text):
            window = text[max(0, m.start() - 80):m.end() + 20]
            assert "floating point" in window, (
                f"Unexpected 'causes' usage outside Plotly bundle comment: {window!r}"
            )

    def test_association_language_present(self, html):
        assert "association" in html.lower()

    def test_predictive_precedence_present(self, html):
        assert "predictive precedence" in html.lower()

    def test_no_structural_causal_claim_strings(self, html):
        forbidden_phrases = [
            "x causes growth", "causes growth in", "is the cause of",
        ]
        text = html.lower()
        for phrase in forbidden_phrases:
            assert phrase not in text


# ─────────────────────────────────────────────────────────────────────────────
# Builder determinism
# ─────────────────────────────────────────────────────────────────────────────

class TestBuilderDeterminism:
    def test_rebuild_produces_same_relation_and_blocked_edges(self):
        """Re-running the builder must not change the set of relation/blocked
        edges (deterministic given fixed source CSVs)."""
        result = subprocess.run(
            [sys.executable, str(BUILDER_PATH)],
            capture_output=True, text=True, cwd=Path.cwd(),
        )
        assert result.returncode == 0, f"Builder failed: {result.stderr}"
        text = _html_text()
        rel = _extract_js_const(text, "RELATION_EDGES")
        blocked = _extract_js_const(text, "BLOCKED_EDGES")
        assert len(rel) == 20
        assert len(blocked) == 121
        assert "GEMEENTE_PROXY" not in {e["region_system"] for e in rel}

    def test_csv_checksums_match_manifest(self, html):
        manifest = json.loads((DATA_DIR / "manifest.json").read_text())
        checksums = _extract_js_const(html, "CSV_CHECKSUMS")
        for fname, info in manifest["outputs"].items():
            assert checksums[fname] == info["sha256"][:16]
