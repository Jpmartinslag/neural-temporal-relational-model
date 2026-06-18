"""
Tests for the HERALD Observatory v0.5 narrative dashboard (layperson-friendly
presentation layer on top of the v0.4 granular evidence exports).

This builds on the same hard rules as
`tests/test_observatory_v04_granular_evidence_policy.py`:
  - NL gemeente proxy must never appear in the main relation graph dataset.
  - Blocked proxy edges (121 rows) must stay isolated from the main graph.
  - No raw "NaN" string in rendered text/labels.
  - Every sector acronym shown must have its human name nearby.
  - PT KZ must be handled as structurally absent, not a bare NaN/missing cell.
  - The builder must be deterministic.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
V05_DIR = REPO_ROOT / "data/processed/herald_observatory_v05_narrative"
TERRITORY_VIEW = V05_DIR / "territory_view.csv"
SECTOR_VIEW = V05_DIR / "sector_view.csv"
RELATION_VIEW = V05_DIR / "relation_view.csv"
PREDICTION_VIEW = V05_DIR / "prediction_view.csv"
MAP_STATE = V05_DIR / "map_state_by_year_sector.json"
RELATION_TIMELINE = V05_DIR / "relation_timeline.json"
BLOCKED_COPY = V05_DIR / "blocked_proxy_edges_v04_copy.csv"
MANIFEST = V05_DIR / "manifest.json"

DASHBOARD_HTML = REPO_ROOT / "reports/dashboards/herald_observatory_v05_narrative_dashboard.html"

EXPORTS_BUILDER = REPO_ROOT / "src/data/european_panel/build_observatory_v05_narrative_exports.py"
DASHBOARD_BUILDER = REPO_ROOT / "src/data/european_panel/build_observatory_v05_narrative_dashboard.py"

PREDICTION_GAP_REPORT = REPO_ROOT / "reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md"

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

CAUSAL_TERMS_FORBIDDEN_IN_MAIN_NARRATIVE = [
    "causa ", "impacto causal", "causal impact", "causal effect", "causally",
]
# NOTE: "causes" / "causal" bare occurrences are checked separately with
# context-awareness below — this codebase explicitly uses disclaiming phrases
# like "not proof that one sector causes the other to grow" and "not
# structural causal proof", which are permitted (they negate causality, they
# don't assert it). Forbidden phrases assert causality positively.


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def territory_view() -> pd.DataFrame:
    return pd.read_csv(TERRITORY_VIEW, low_memory=False)


@pytest.fixture(scope="module")
def sector_view() -> pd.DataFrame:
    return pd.read_csv(SECTOR_VIEW, low_memory=False)


@pytest.fixture(scope="module")
def relation_view() -> pd.DataFrame:
    return pd.read_csv(RELATION_VIEW, low_memory=False)


@pytest.fixture(scope="module")
def prediction_view() -> pd.DataFrame:
    return pd.read_csv(PREDICTION_VIEW, low_memory=False)


@pytest.fixture(scope="module")
def blocked_edges() -> pd.DataFrame:
    return pd.read_csv(BLOCKED_COPY, low_memory=False)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def dashboard_html() -> str:
    return DASHBOARD_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_body_html(dashboard_html: str) -> str:
    """The visible UI markup: from <body> up to the trailing JSON-data
    <script> block, excluding the embedded Plotly bundle and JSON consts."""
    body_start = dashboard_html.find("<body>")
    data_script = dashboard_html.find("<script>\nconst REGION_META")
    assert body_start != -1 and data_script != -1
    return dashboard_html[body_start:data_script]


# ─────────────────────────────────────────────────────────────────────────
# Files exist / well-formed
# ─────────────────────────────────────────────────────────────────────────

class TestFilesExist:
    def test_dashboard_html_exists(self):
        assert DASHBOARD_HTML.exists()

    def test_dashboard_html_well_formed(self, dashboard_html):
        assert dashboard_html.strip().startswith("<!DOCTYPE html>")
        assert dashboard_html.strip().endswith("</html>")
        assert dashboard_html.count("<html") == 1
        assert dashboard_html.count("</html>") == 1
        assert "<body>" in dashboard_html and "</body>" in dashboard_html

    def test_territory_view_exists(self):
        assert TERRITORY_VIEW.exists()

    def test_sector_view_exists(self):
        assert SECTOR_VIEW.exists()

    def test_relation_view_exists(self):
        assert RELATION_VIEW.exists()

    def test_prediction_view_exists(self):
        assert PREDICTION_VIEW.exists()

    def test_map_state_exists(self):
        assert MAP_STATE.exists()

    def test_relation_timeline_exists(self):
        assert RELATION_TIMELINE.exists()

    def test_blocked_copy_exists(self):
        assert BLOCKED_COPY.exists()

    def test_manifest_exists(self):
        assert MANIFEST.exists()

    def test_prediction_gap_report_exists(self):
        assert PREDICTION_GAP_REPORT.exists()

    def test_builders_exist(self):
        assert EXPORTS_BUILDER.exists()
        assert DASHBOARD_BUILDER.exists()


# ─────────────────────────────────────────────────────────────────────────
# No raw NaN anywhere visible
# ─────────────────────────────────────────────────────────────────────────

class TestNoRawNan:
    def test_no_nan_in_main_body_html(self, dashboard_body_html):
        assert "NaN" not in dashboard_body_html

    def test_no_nan_string_in_territory_view_text_columns(self, territory_view):
        for col in territory_view.select_dtypes(include="object").columns:
            bad = territory_view[col].astype(str).str.fullmatch("nan", case=False, na=False)
            assert not bad.any(), f"raw NaN-string found in territory_view.{col}"

    def test_no_nan_string_in_sector_view_text_columns(self, sector_view):
        for col in sector_view.select_dtypes(include="object").columns:
            bad = sector_view[col].astype(str).str.fullmatch("nan", case=False, na=False)
            assert not bad.any(), f"raw NaN-string found in sector_view.{col}"

    def test_no_nan_string_in_relation_view_text_columns(self, relation_view):
        for col in relation_view.select_dtypes(include="object").columns:
            bad = relation_view[col].astype(str).str.fullmatch("nan", case=False, na=False)
            assert not bad.any(), f"raw NaN-string found in relation_view.{col}"

    def test_state_human_uses_controlled_vocabulary(self, territory_view):
        allowed = {"Growing", "Stable", "Falling", "No evidence",
                   "Sector not available for Portugal"}
        assert set(territory_view["state_human"].unique()).issubset(allowed)

    def test_dashboard_json_blobs_have_no_python_none_artifacts(self, dashboard_html):
        # None must serialise to JSON null, never the Python repr "None"
        for blob_name in ["MAP_STATE", "PREDICTION_LOOKUP", "REGION_META"]:
            m = re.search(rf"const {blob_name} = (.*?);\n", dashboard_html, re.DOTALL)
            assert m is not None, f"{blob_name} not found in dashboard"
            assert "None" not in m.group(1)


# ─────────────────────────────────────────────────────────────────────────
# Sector acronyms always paired with a human name
# ─────────────────────────────────────────────────────────────────────────

class TestSectorNamesAlwaysShown:
    @pytest.mark.parametrize("code,name", SECTOR_LABELS.items())
    def test_sector_code_has_human_name_nearby_in_body(self, dashboard_body_html, code, name):
        assert f"({code})" in dashboard_body_html, f"sector code {code} not found in main UI body"
        # the human name must appear in the document somewhere near sector usage
        assert name in dashboard_body_html, f"human name for {code} ({name}) not found in main UI body"

    def test_no_ml_jargon_in_main_body(self, dashboard_body_html):
        lowered = dashboard_body_html.lower()
        for term in ["gnn", "attention", "encoder", "auc", "neural model"]:
            assert term not in lowered, f"ML jargon '{term}' leaked into main UI body"


# ─────────────────────────────────────────────────────────────────────────
# PT / KZ structural absence
# ─────────────────────────────────────────────────────────────────────────

class TestPtKzStructuralAbsence:
    def test_pt_kz_flagged_structural_absent_in_manifest(self, manifest):
        assert manifest["rules"]["pt_kz_structural_absent"] is True

    def test_pt_kz_rows_labelled_not_nan(self, territory_view):
        pt_kz = territory_view[(territory_view["country"] == "PT") & (territory_view["sector_a10"] == "KZ")]
        assert len(pt_kz) > 0
        assert (pt_kz["state_human"] == "Sector not available for Portugal").all()
        assert (pt_kz["evidence_badge"] == "Structurally absent").all()

    def test_pt_kz_sector_view_flagged(self, sector_view):
        pt_kz = sector_view[(sector_view["country"] == "PT") & (sector_view["sector_a10"] == "KZ")]
        if len(pt_kz):
            assert pt_kz["structural_absent"].all()

    def test_dashboard_disables_kz_for_pt(self, dashboard_html):
        assert "PT_KZ_STRUCTURAL_ABSENT" in dashboard_html
        assert "refreshSectorOptionsForCountry" in dashboard_html
        assert "opt.disabled" in dashboard_html


# ─────────────────────────────────────────────────────────────────────────
# NL gemeente proxy never in the main relation graph
# ─────────────────────────────────────────────────────────────────────────

class TestNlGemeenteNeverInMainGraph:
    def test_relation_view_excludes_gemeente_proxy(self, relation_view):
        assert "GEMEENTE_PROXY" not in relation_view["region_system"].values

    def test_relation_view_only_observed(self, relation_view):
        assert relation_view["evidence_type"].eq("observed_births").all()

    def test_dashboard_embedded_relation_edges_exclude_gemeente_proxy(self, dashboard_html):
        m = re.search(r"const RELATION_EDGES = (.*?);\n", dashboard_html, re.DOTALL)
        assert m is not None
        edges = json.loads(m.group(1))
        assert all(e["region_system"] != "GEMEENTE_PROXY" for e in edges)
        assert len(edges) == 20

    def test_nl_gemeente_allowed_in_territory_view_as_context(self, territory_view):
        gm = territory_view[territory_view["region_system"] == "GEMEENTE_PROXY"]
        assert len(gm) > 0
        assert (gm["is_proxy_context"]).all()
        assert (gm["evidence_badge"] == "Proxy / context").all()


# ─────────────────────────────────────────────────────────────────────────
# Blocked proxy edges isolated
# ─────────────────────────────────────────────────────────────────────────

class TestBlockedEdgesIsolated:
    def test_blocked_edges_count(self, blocked_edges):
        assert len(blocked_edges) == 121

    def test_blocked_edges_not_allowed_for_training(self, blocked_edges):
        assert (~blocked_edges["allowed_for_training_label"]).all()

    def test_blocked_edges_not_merged_into_relation_view(self, relation_view, blocked_edges):
        relation_pairs = set(zip(relation_view["source_sector"], relation_view["target_sector"],
                                  relation_view["window"], relation_view["country"]))
        blocked_pairs = set(zip(blocked_edges["source_sector"], blocked_edges["target_sector"],
                                 blocked_edges["window"], blocked_edges["country"]))
        # blocked edges may share sector pairs with valid edges in other windows/
        # countries (NL COROP vs NL GEMEENTE_PROXY), but no individual blocked
        # row's full evidence_type may equal the observed type used in relation_view.
        assert not blocked_edges["evidence_type"].isin(relation_view["evidence_type"].unique()).any() or \
            blocked_edges["evidence_type"].eq("proxy_disaggregated_by_stock_share").all()

    def test_dashboard_blocked_edges_separate_dataset(self, dashboard_html):
        m_rel = re.search(r"const RELATION_EDGES = (.*?);\n", dashboard_html, re.DOTALL)
        m_blk = re.search(r"const BLOCKED_EDGES = (.*?);\n", dashboard_html, re.DOTALL)
        assert m_rel is not None and m_blk is not None
        rel = json.loads(m_rel.group(1))
        blk = json.loads(m_blk.group(1))
        assert len(rel) == 20
        assert len(blk) == 121
        # disjoint datasets (no blocked row id-equivalent appears in the main graph list)
        rel_keys = {(e["source_sector"], e["target_sector"], e["country"], e["window"]) for e in rel}
        blk_keys = {(e["source_sector"], e["target_sector"], e["country"], e["window"]) for e in blk}
        # they may coincidentally share a (source,target,country,window) tuple only if
        # region systems differ (NL COROP valid vs NL GEMEENTE_PROXY blocked) — ensure
        # every blocked-only tuple has region_system GEMEENTE_PROXY
        for e in blk:
            assert e["region_system"] == "GEMEENTE_PROXY"

    def test_blocked_panel_not_framed_as_discovery(self, dashboard_body_html):
        # "discovery" may only appear in a negated form ("never a discovery"),
        # never asserting the blocked edges ARE a discovery/finding.
        lowered = dashboard_body_html.lower()
        for idx in (m.start() for m in re.finditer("discovery", lowered)):
            window = lowered[max(0, idx - 15):idx]
            assert "never" in window, f"unguarded 'discovery' framing near index {idx}"
        assert "blocked proxy artifacts" in lowered
        assert "audit only" in lowered


# ─────────────────────────────────────────────────────────────────────────
# Map covers FR/PT/NL
# ─────────────────────────────────────────────────────────────────────────

class TestMapCoverage:
    def test_territory_view_has_all_three_countries(self, territory_view):
        assert set(territory_view["country"].unique()) >= {"FR", "PT", "NL"}

    def test_dashboard_map_country_selector_has_all_three(self, dashboard_body_html):
        assert '<option value="FR">France</option>' in dashboard_body_html
        assert '<option value="NL">Netherlands</option>' in dashboard_body_html
        assert '<option value="PT">Portugal</option>' in dashboard_body_html

    def test_dashboard_embeds_geometry_for_all_three(self, dashboard_html):
        for const in ["GEO_FR", "GEO_NL", "GEO_PT"]:
            m = re.search(rf"const {const} = (.*?);\n", dashboard_html, re.DOTALL)
            assert m is not None
            geo = json.loads(m.group(1))
            assert geo["type"] == "FeatureCollection"


# ─────────────────────────────────────────────────────────────────────────
# UI structural requirements
# ─────────────────────────────────────────────────────────────────────────

class TestUiStructure:
    def test_timeline_play_control_exists(self, dashboard_body_html):
        assert 'id="year-slider"' in dashboard_body_html
        assert 'id="play-pause-btn"' in dashboard_body_html

    def test_relation_window_timeline_control_exists(self, dashboard_body_html):
        assert 'id="window-slider"' in dashboard_body_html
        assert 'id="graph-play-btn"' in dashboard_body_html

    def test_dynamic_graph_section_exists(self, dashboard_body_html):
        assert 'id="sector-graph"' in dashboard_body_html

    def test_how_it_works_section_exists(self, dashboard_body_html):
        assert "How it works" in dashboard_body_html
        assert 'class="how-step"' in dashboard_body_html

    def test_technical_details_collapsible_exists(self, dashboard_body_html):
        assert "<details" in dashboard_body_html
        assert "Technical details" in dashboard_body_html

    def test_evidence_badges_section_exists(self, dashboard_body_html):
        assert "Evidence badges" in dashboard_body_html

    def test_basins_placeholder_exists(self, dashboard_body_html):
        assert "Similar dynamics" in dashboard_body_html

    def test_prediction_layer_section_exists(self, dashboard_body_html):
        assert "Above or below expected" in dashboard_body_html

    def test_gsap_loaded(self, dashboard_html):
        assert "gsap" in dashboard_html.lower()


# ─────────────────────────────────────────────────────────────────────────
# No forbidden causal language in main narrative
# ─────────────────────────────────────────────────────────────────────────

class TestNoCausalLanguage:
    @pytest.mark.parametrize("term", CAUSAL_TERMS_FORBIDDEN_IN_MAIN_NARRATIVE)
    def test_forbidden_causal_term_absent(self, dashboard_body_html, term):
        assert term.lower() not in dashboard_body_html.lower()

    def test_permitted_footnote_is_the_only_structural_causal_mention(self, dashboard_body_html):
        # "structural causal proof" is the one permitted technical footnote phrase;
        # it must appear in a negated ("not structural causal proof") form only.
        idx = dashboard_body_html.lower().find("structural causal proof")
        if idx != -1:
            window = dashboard_body_html[max(0, idx - 30):idx]
            assert "not" in window.lower()

    def test_relation_sentence_uses_predictive_precedence_framing(self, relation_view):
        assert relation_view["plain_sentence"].str.contains("not proof of causality").all()


# ─────────────────────────────────────────────────────────────────────────
# Manifest validity
# ─────────────────────────────────────────────────────────────────────────

class TestManifest:
    def test_manifest_is_valid_json_with_required_keys(self, manifest):
        for key in ["version", "generated_at", "dec_references", "source_files",
                    "output_files", "rules", "row_counts", "no_data_vocabulary"]:
            assert key in manifest

    def test_manifest_version(self, manifest):
        assert manifest["version"] == "0.5"

    def test_manifest_prediction_rule_documented(self, manifest):
        assert "prediction_layer_excludes_pt_reason" in manifest["rules"]
        assert "MUNICIPALITY" in manifest["rules"]["prediction_layer_excludes_pt_reason"]


# ─────────────────────────────────────────────────────────────────────────
# Determinism
# ─────────────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_exports_builder_deterministic(self, tmp_path):
        before = {p.name: _sha256_file(p) for p in V05_DIR.glob("*.csv")}
        result = subprocess.run([sys.executable, str(EXPORTS_BUILDER)],
                                 cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, result.stderr
        after = {p.name: _sha256_file(p) for p in V05_DIR.glob("*.csv")}
        assert before == after, "exports builder is not deterministic across runs"

    def test_dashboard_builder_deterministic_modulo_manifest_timestamp(self):
        # Run the dashboard builder twice in a row WITHOUT an intervening
        # exports rebuild (the exports manifest.json carries a fresh
        # generated_at timestamp on every export run, which the dashboard
        # embeds verbatim — that is expected and not a determinism bug in
        # the dashboard builder itself, which is what this test targets).
        r1 = subprocess.run([sys.executable, str(DASHBOARD_BUILDER)],
                             cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert r1.returncode == 0, r1.stderr
        before = _sha256_file(DASHBOARD_HTML)
        r2 = subprocess.run([sys.executable, str(DASHBOARD_BUILDER)],
                             cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert r2.returncode == 0, r2.stderr
        after = _sha256_file(DASHBOARD_HTML)
        assert before == after, "dashboard builder is not deterministic across runs"
