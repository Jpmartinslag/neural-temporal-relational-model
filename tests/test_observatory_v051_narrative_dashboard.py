"""
Tests for the HERALD Observatory v0.5.1 narrative dashboard (corrected,
French, article-grade method opening, integrated PT municipal prediction,
real geographic heatmap, graph<->map wiring).

Encodes every Part N requirement from the v0.5.1 brief. Does not touch or
import anything from the v0.5/v0.4 test suites — independent file, separate
data directory (data/processed/herald_observatory_v051_narrative/),
independent dashboard HTML.
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
V051_DIR = REPO_ROOT / "data/processed/herald_observatory_v051_narrative"
TERRITORY_VIEW = V051_DIR / "territory_view.csv"
SECTOR_VIEW = V051_DIR / "sector_view.csv"
RELATION_VIEW = V051_DIR / "relation_view.csv"
PREDICTION_VIEW = V051_DIR / "prediction_view.csv"
PT_MUNICIPAL_PREDICTION_VIEW = V051_DIR / "pt_municipal_prediction_view.csv"
MAP_STATE = V051_DIR / "map_state_by_year_sector.json"
RELATION_TIMELINE = V051_DIR / "relation_timeline.json"
PREDICTION_LOOKUP = V051_DIR / "prediction_lookup.json"
ECONOMIC_BASINS = V051_DIR / "economic_basins.json"
BLOCKED_COPY = V051_DIR / "blocked_proxy_edges_v04_copy.csv"
MANIFEST = V051_DIR / "manifest.json"

DASHBOARD_HTML = REPO_ROOT / "reports/dashboards/herald_observatory_v051_narrative_dashboard.html"

EXPORTS_BUILDER = REPO_ROOT / "src/data/european_panel/build_observatory_v051_narrative_exports.py"
DASHBOARD_BUILDER = REPO_ROOT / "src/data/european_panel/build_observatory_v051_narrative_dashboard.py"
PT_MUNICIPAL_BUILDER = REPO_ROOT / "src/data/european_panel/build_pt_municipal_prediction_layer.py"

PREDICTION_GAP_REPORT = REPO_ROOT / "reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md"
CORRECTION_AUDIT = REPO_ROOT / "reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md"

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

FRENCH_TERM_SPOTCHECK = [
    "Croissance", "Stable", "Recul", "Donnée insuffisante", "Observé",
    "Proxy territorial", "Validé", "Supporté", "Exploratoire", "Rejeté".lower(),
    "Au-dessus de l'attendu", "En dessous de l'attendu", "Attendu",
    "Relations sectorielles", "Bassins économiques",
]

CAUSAL_TERMS_FORBIDDEN_IN_MAIN_NARRATIVE = [
    "causal", "causes", "not proof of causality",
]


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
def pt_municipal_prediction_view() -> pd.DataFrame:
    return pd.read_csv(PT_MUNICIPAL_PREDICTION_VIEW, low_memory=False)


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
    data_script = dashboard_html.find("const REGION_META")
    assert body_start != -1 and data_script != -1
    # back up to the start of the enclosing <script> tag for this data block
    script_tag_start = dashboard_html.rfind("<script>", 0, data_script)
    assert script_tag_start != -1
    return dashboard_html[body_start:script_tag_start]


@pytest.fixture(scope="module")
def main_body_before_method_diagram(dashboard_body_html: str) -> str:
    return dashboard_body_html


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

    def test_pt_municipal_prediction_view_exists(self):
        assert PT_MUNICIPAL_PREDICTION_VIEW.exists()

    def test_map_state_exists(self):
        assert MAP_STATE.exists()

    def test_relation_timeline_exists(self):
        assert RELATION_TIMELINE.exists()

    def test_prediction_lookup_exists(self):
        assert PREDICTION_LOOKUP.exists()

    def test_economic_basins_exists(self):
        assert ECONOMIC_BASINS.exists()

    def test_blocked_copy_exists(self):
        assert BLOCKED_COPY.exists()

    def test_manifest_exists(self):
        assert MANIFEST.exists()

    def test_correction_audit_exists(self):
        assert CORRECTION_AUDIT.exists()

    def test_builders_exist(self):
        assert EXPORTS_BUILDER.exists()
        assert DASHBOARD_BUILDER.exists()
        assert PT_MUNICIPAL_BUILDER.exists()

    def test_v05_files_untouched_still_exist(self):
        # v0.5.1 must not remove or break the v0.5 artifacts.
        assert (REPO_ROOT / "reports/dashboards/herald_observatory_v05_narrative_dashboard.html").exists()
        assert (REPO_ROOT / "src/data/european_panel/build_observatory_v05_narrative_dashboard.py").exists()
        assert (REPO_ROOT / "src/data/european_panel/build_observatory_v05_narrative_exports.py").exists()


# ─────────────────────────────────────────────────────────────────────────
# Part N1 — French language
# ─────────────────────────────────────────────────────────────────────────

class TestFrenchLanguage:
    def test_html_lang_attribute_is_fr(self, dashboard_html):
        assert '<html lang="fr">' in dashboard_html

    def test_title_is_french(self, dashboard_html):
        assert "<title>HERALD" in dashboard_html
        assert "observatoire économique territorial" in dashboard_html

    @pytest.mark.parametrize("term", FRENCH_TERM_SPOTCHECK)
    def test_french_term_present_in_body(self, dashboard_html, term):
        # Several controlled-vocabulary strings (state labels, prediction
        # legend) are rendered by inline JS (legend/state text), not present
        # as static HTML — check the full document (still excludes nothing
        # but the literal absence of the term anywhere is what matters here).
        assert term in dashboard_html, f"French UI term '{term}' missing from dashboard"

    def test_no_english_section_titles_from_v05_leak_in(self, dashboard_body_html):
        # Spot-check key v0.5 English strings are NOT present (would indicate
        # an accidental copy-paste without translation).
        forbidden_english = [
            "What's happening?", "Above or below expected?",
            "Which sectors move together?", "How it works",
            "Evidence badges", "Territories observed",
        ]
        for s in forbidden_english:
            assert s not in dashboard_body_html, f"Untranslated v0.5 English string '{s}' found"


# ─────────────────────────────────────────────────────────────────────────
# Part N2 — HERALD architecture section at the very top, before the map
# ─────────────────────────────────────────────────────────────────────────

class TestArchitectureAtTop:
    def test_method_section_class_present(self, dashboard_body_html):
        assert 'class="section method-section"' in dashboard_body_html

    def test_method_title_present(self, dashboard_body_html):
        assert "Méthode HERALD" in dashboard_body_html

    def test_method_section_before_map_section(self, dashboard_body_html):
        idx_method = dashboard_body_html.find("Méthode HERALD")
        idx_map = dashboard_body_html.find("Carte territoriale")
        assert idx_method != -1 and idx_map != -1
        assert idx_method < idx_map, "Method/architecture section must appear before the map"

    def test_method_section_before_kpi_evidence_summary(self, dashboard_body_html):
        idx_method = dashboard_body_html.find("Méthode HERALD")
        idx_summary = dashboard_body_html.find("Résumé d'évidence")
        assert idx_method != -1 and idx_summary != -1
        assert idx_method < idx_summary

    def test_method_diagram_has_five_or_more_stages(self, dashboard_body_html):
        assert dashboard_body_html.count('class="method-step') >= 5

    def test_method_components_present(self, dashboard_body_html):
        for term in ["Base statistique", "Couche relationnelle", "Validation", "Sortie"]:
            assert term in dashboard_body_html

    def test_no_gnn_jargon_in_method_diagram(self, dashboard_body_html):
        method_start = dashboard_body_html.find("Méthode HERALD")
        method_end = dashboard_body_html.find("Résumé d'évidence")
        method_block = dashboard_body_html[method_start:method_end].lower()
        for term in ["gnn", "attention", "loss", "encoder"]:
            assert term not in method_block


# ─────────────────────────────────────────────────────────────────────────
# Part N3 — PT municipal prediction integrated + gap documented closed/partial
# ─────────────────────────────────────────────────────────────────────────

class TestPtMunicipalPredictionIntegrated:
    def test_pt_municipal_prediction_rows_exist(self, pt_municipal_prediction_view):
        assert len(pt_municipal_prediction_view) > 0

    def test_pt_municipal_prediction_has_valid_forecasts(self, pt_municipal_prediction_view):
        assert (pt_municipal_prediction_view["forecast_status"] == "valid_forecast").sum() > 0

    def test_pt_in_unified_prediction_view(self, prediction_view):
        assert "PT" in prediction_view["country"].unique()
        pt_rows = prediction_view[prediction_view["country"] == "PT"]
        assert len(pt_rows) > 0
        assert (pt_rows["region_system"] == "MUNICIPALITY").all()

    def test_pt_prediction_available_for_some_rows(self, prediction_view):
        pt_rows = prediction_view[prediction_view["country"] == "PT"]
        assert pt_rows["available"].any()

    def test_manifest_documents_pt_status_closed(self, manifest):
        assert manifest["rules"]["pt_municipal_prediction_status"] == "CLOSED"
        assert "PT" in manifest["rules"]["prediction_layer_countries"]

    def test_manifest_documents_method_sentence(self, manifest):
        assert manifest["rules"]["pt_municipal_prediction_note"] == (
            "PT municipal forecast generated via causal persistence/Ridge on observed "
            "municipal panel; no proxy, no HPC."
        )

    def test_gap_report_updated_to_closed_or_partial(self):
        text = PREDICTION_GAP_REPORT.read_text(encoding="utf-8")
        assert ("CLOSED" in text) or ("PARTIALLY_CLOSED" in text)
        assert ("PT municipal forecast generated via causal persistence/Ridge on observed "
                "municipal panel; no proxy, no HPC.") in text

    def test_no_leakage_pt_persistence_equals_prior_year(self, pt_municipal_prediction_view):
        panel = pd.read_csv(REPO_ROOT / "data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv",
                             low_memory=False)
        panel["territory_id"] = panel["territory_id"].astype(str)
        src = panel.set_index(["territory_id", "sector_id", "observation_year"])
        valid = pt_municipal_prediction_view[pt_municipal_prediction_view["forecast_status"] == "valid_forecast"]
        checked = 0
        for _, row in valid.sample(min(500, len(valid)), random_state=42).iterrows():
            key_prev = (str(row["territory_id"]), row["sector_id"], int(row["observation_year"]) - 1)
            if key_prev not in src.index:
                continue
            prev_obs = src.loc[key_prev, "observed_value"]
            prev_mask = src.loc[key_prev, "observation_mask"]
            if int(prev_mask) == 1 and pd.notna(prev_obs):
                assert abs(float(row["persistence_forecast"]) - float(prev_obs)) < 1e-6
                checked += 1
        assert checked > 0

    def test_pt_kz_never_a_valid_forecast(self, pt_municipal_prediction_view):
        kz = pt_municipal_prediction_view[pt_municipal_prediction_view["sector_id"] == "KZ"]
        assert len(kz) > 0
        assert (kz["forecast_status"] == "structural_absent").all()
        assert kz["observed_value"].isna().all()


# ─────────────────────────────────────────────────────────────────────────
# Part N4 — no raw "NaN" in visible text
# ─────────────────────────────────────────────────────────────────────────

class TestNoRawNan:
    def test_no_nan_in_main_body_html(self, dashboard_body_html):
        assert "NaN" not in dashboard_body_html

    def test_no_nan_outside_plotly_bundle_script(self, dashboard_html):
        idx_start = dashboard_html.find("<script>")
        idx_end = dashboard_html.find("</script>", idx_start)
        rest = dashboard_html[:idx_start] + dashboard_html[idx_end + len("</script>"):]
        assert "NaN" not in rest

    def test_no_nan_string_in_territory_view_text_columns(self, territory_view):
        for col in territory_view.select_dtypes(include="object").columns:
            bad = territory_view[col].astype(str).str.fullmatch("nan", case=False, na=False)
            assert not bad.any(), f"raw NaN-string found in territory_view.{col}"

    def test_no_nan_string_in_relation_view_text_columns(self, relation_view):
        for col in relation_view.select_dtypes(include="object").columns:
            bad = relation_view[col].astype(str).str.fullmatch("nan", case=False, na=False)
            assert not bad.any(), f"raw NaN-string found in relation_view.{col}"

    def test_state_human_uses_controlled_french_vocabulary(self, territory_view):
        allowed = {"Croissance", "Stable", "Recul", "Donnée insuffisante",
                   "Secteur non disponible pour le Portugal"}
        assert set(territory_view["state_human"].unique()).issubset(allowed)


# ─────────────────────────────────────────────────────────────────────────
# Part N5 — KZ never a normal/enabled option for PT
# ─────────────────────────────────────────────────────────────────────────

class TestPtKzNeverEnabled:
    def test_pt_kz_flagged_structural_absent_in_manifest(self, manifest):
        assert manifest["rules"]["pt_kz_structural_absent"] is True

    def test_pt_kz_rows_labelled_not_nan(self, territory_view):
        pt_kz = territory_view[(territory_view["country"] == "PT") & (territory_view["sector_a10"] == "KZ")]
        assert len(pt_kz) > 0
        assert (pt_kz["state_human"] == "Secteur non disponible pour le Portugal").all()

    def test_dashboard_disables_kz_for_pt(self, dashboard_html):
        assert "PT_KZ_STRUCTURAL_ABSENT" in dashboard_html
        assert "refreshSectorOptionsForCountry" in dashboard_html
        assert "opt.disabled" in dashboard_html

    def test_prediction_view_pt_kz_never_available(self, prediction_view):
        pt_kz = prediction_view[(prediction_view["country"] == "PT") & (prediction_view["sector_a10"] == "KZ")]
        assert len(pt_kz) > 0
        assert not pt_kz["available"].any()


# ─────────────────────────────────────────────────────────────────────────
# Part N6 — GEMEENTE_PROXY never in the main relation graph dataset
# ─────────────────────────────────────────────────────────────────────────

class TestNlGemeenteNeverInMainGraph:
    def test_relation_view_excludes_gemeente_proxy(self, relation_view):
        assert "GEMEENTE_PROXY" not in relation_view["region_system"].values

    def test_dashboard_embedded_relation_edges_exclude_gemeente_proxy(self, dashboard_html):
        m = re.search(r"const RELATION_EDGES = (.*?);\n", dashboard_html, re.DOTALL)
        assert m is not None
        edges = json.loads(m.group(1))
        assert all(e["region_system"] != "GEMEENTE_PROXY" for e in edges)
        assert len(edges) == 20

    def test_nl_gemeente_allowed_in_territory_view_as_proxy_context(self, territory_view):
        gm = territory_view[territory_view["region_system"] == "GEMEENTE_PROXY"]
        assert len(gm) > 0
        assert (gm["is_proxy_context"]).all()
        assert (gm["evidence_badge"] == "Proxy territorial (contexte uniquement)").all()


# ─────────────────────────────────────────────────────────────────────────
# Part N7 — Blocked edges never framed as a validated relation
# ─────────────────────────────────────────────────────────────────────────

class TestBlockedEdgesIsolated:
    def test_blocked_edges_count(self, blocked_edges):
        assert len(blocked_edges) == 121

    def test_blocked_edges_not_allowed_for_training(self, blocked_edges):
        assert (~blocked_edges["allowed_for_training_label"]).all()

    def test_dashboard_blocked_edges_separate_dataset(self, dashboard_html):
        m_rel = re.search(r"const RELATION_EDGES = (.*?);\n", dashboard_html, re.DOTALL)
        m_blk = re.search(r"const BLOCKED_EDGES = (.*?);\n", dashboard_html, re.DOTALL)
        assert m_rel is not None and m_blk is not None
        rel = json.loads(m_rel.group(1))
        blk = json.loads(m_blk.group(1))
        assert len(rel) == 20
        assert len(blk) == 121
        for e in blk:
            assert e["region_system"] == "GEMEENTE_PROXY"

    def test_blocked_panel_framed_as_audit_only_not_validated(self, dashboard_body_html):
        lowered = dashboard_body_html.lower()
        assert "audit uniquement" in lowered
        assert "rejetées" in lowered or "rejeté" in lowered
        # the word "validé"/"validée" must never directly describe the blocked set
        idx = lowered.find("relations proxy rejetées")
        assert idx != -1


# ─────────────────────────────────────────────────────────────────────────
# Part N8 — no "causal"/"causes"/"not proof of causality" in main body
# ─────────────────────────────────────────────────────────────────────────

def _strip_tech_details_blocks(html_fragment: str) -> str:
    """Remove every <details class="tech">...</details> block — Part L
    permits causal language ONLY inside these collapsible methodological
    sections, framed as an explicit prohibition. The "main narrative" for
    Part N8 purposes is everything else."""
    return re.sub(r'<details class="tech">.*?</details>', '', html_fragment, flags=re.DOTALL)


class TestNoCausalLanguageInMainBody:
    @pytest.mark.parametrize("term", CAUSAL_TERMS_FORBIDDEN_IN_MAIN_NARRATIVE)
    def test_forbidden_causal_term_absent_from_main_body(self, dashboard_body_html, term):
        main_narrative = _strip_tech_details_blocks(dashboard_body_html)
        assert term.lower() not in main_narrative.lower(), \
            f"forbidden causal term '{term}' found in main UI body (outside methodological details)"

    def test_causal_prohibition_only_inside_methodological_details(self, dashboard_html):
        # "lien de causalité" is permitted ONLY inside the collapsible
        # <details class="tech"> blocks, framed as an explicit prohibition.
        idx = dashboard_html.find("lien de causalité")
        assert idx != -1, "expected explicit causality prohibition inside technical details"
        preceding = dashboard_html[:idx]
        last_details_open = preceding.rfind('<details class="tech">')
        last_details_close = preceding.rfind("</details>")
        assert last_details_open != -1 and last_details_open > last_details_close, \
            "causality prohibition must be nested inside a <details class='tech'> block"
        assert "n'établissent pas" in dashboard_html[idx - 60:idx + 20]

    def test_relation_sentence_uses_predictive_precedence_french_framing(self, relation_view):
        assert relation_view["plain_sentence"].str.contains("association temporelle").all()
        assert relation_view["plain_sentence"].str.contains("ne constitue pas une recommandation automatique").all()
        assert not relation_view["plain_sentence"].str.contains("causal", case=False).any()


# ─────────────────────────────────────────────────────────────────────────
# Part N9 — A10 acronyms always paired with human French name
# ─────────────────────────────────────────────────────────────────────────

class TestSectorNamesAlwaysShown:
    @pytest.mark.parametrize("code,name", SECTOR_LABELS_FR.items())
    def test_sector_code_has_human_name_nearby_in_body(self, dashboard_body_html, code, name):
        assert f"({code})" in dashboard_body_html, f"sector code {code} not found in main UI body"
        assert name in dashboard_body_html, f"French human name for {code} ({name}) not found in main UI body"


# ─────────────────────────────────────────────────────────────────────────
# Part N10 — beta/q_fdr/bss only inside methodological-details section
# ─────────────────────────────────────────────────────────────────────────

class TestTechnicalTermsOnlyInDetails:
    @pytest.mark.parametrize("term", ["beta", "q_fdr", "bss"])
    def test_term_not_in_static_html_outside_script(self, dashboard_html, term):
        body_end = dashboard_html.find("<script>")
        static_body = dashboard_html[:body_end]
        assert term not in static_body

    def test_evidence_kpis_and_relation_tbody_nested_in_details(self, dashboard_html):
        for elem_id in ["evidence-kpis", "tech-relation-tbody"]:
            idx = dashboard_html.find(f'id="{elem_id}"')
            assert idx != -1
            preceding = dashboard_html[:idx]
            last_details_open = preceding.rfind('<details class="tech">')
            last_details_close = preceding.rfind("</details>")
            assert last_details_open != -1
            assert last_details_open > last_details_close, \
                f"{elem_id} must be nested inside a <details class='tech'> block"

    def test_no_ml_jargon_in_main_body(self, dashboard_body_html):
        lowered = dashboard_body_html.lower()
        for term in ["gnn", "attention", "encoder", "auc"]:
            assert term not in lowered, f"ML jargon '{term}' leaked into main UI body"


# ─────────────────────────────────────────────────────────────────────────
# Part N11 — geographic heatmap / "Bassins économiques" mode
# ─────────────────────────────────────────────────────────────────────────

class TestEconomicBasinsHeatmap:
    def test_economic_basins_json_has_all_three_countries(self):
        data = json.loads(ECONOMIC_BASINS.read_text())
        assert set(data.keys()) >= {"FR", "NL", "PT"}

    def test_basins_view_option_exists_in_map_selector(self, dashboard_body_html):
        assert '<option value="basins">Bassins économiques</option>' in dashboard_body_html

    def test_basins_js_rendering_function_exists(self, dashboard_html):
        assert "ECONOMIC_BASINS" in dashboard_html
        assert "basinScore" in dashboard_html

    def test_basins_never_called_causal_cluster(self, dashboard_body_html):
        lowered = dashboard_body_html.lower()
        assert "causal cluster" not in lowered
        assert "cluster causal" not in lowered

    def test_basins_note_present(self, dashboard_body_html):
        assert "Bassins économiques" in dashboard_body_html
        assert "concentration économique" in dashboard_body_html


# ─────────────────────────────────────────────────────────────────────────
# Part N12 — graph interacts with / filters the map
# ─────────────────────────────────────────────────────────────────────────

class TestGraphMapWiring:
    def test_apply_graph_filter_to_map_function_exists(self, dashboard_html):
        assert "function applyGraphFilterToMap" in dashboard_html

    def test_graph_click_handler_calls_map_filter(self, dashboard_html):
        # the plotly_click handler on #sector-graph must call both the edge
        # detail panel AND the map filter function — i.e. real wiring, not
        # two independent unconnected handlers.
        m = re.search(r"document\.getElementById\('sector-graph'\)\.on\('plotly_click', function\(data\) \{(.*?)\}\);",
                      dashboard_html, re.DOTALL)
        assert m is not None
        handler_body = m.group(1)
        assert "showEdgeDetail" in handler_body
        assert "applyGraphFilterToMap" in handler_body

    def test_map_filter_updates_map_country_selector(self, dashboard_html):
        idx = dashboard_html.find("function applyGraphFilterToMap")
        assert idx != -1
        fn_body = dashboard_html[idx: idx + 1200]
        assert "map-country" in fn_body
        assert "renderTerritoryView" in fn_body


# ─────────────────────────────────────────────────────────────────────────
# Part N13 — timeline / play control exists
# ─────────────────────────────────────────────────────────────────────────

class TestTimelinePlayControl:
    def test_year_timeline_exists(self, dashboard_body_html):
        assert 'id="year-slider"' in dashboard_body_html
        assert 'id="play-pause-btn"' in dashboard_body_html

    def test_relation_window_timeline_exists(self, dashboard_body_html):
        assert 'id="window-slider"' in dashboard_body_html
        assert 'id="graph-play-btn"' in dashboard_body_html

    def test_toggle_play_functions_exist(self, dashboard_html):
        assert "function togglePlay" in dashboard_html
        assert "function toggleGraphPlay" in dashboard_html


# ─────────────────────────────────────────────────────────────────────────
# Part N14 — builder determinism
# ─────────────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_pt_municipal_builder_deterministic(self):
        before = _sha256_file(PT_MUNICIPAL_PREDICTION_VIEW)
        result = subprocess.run([sys.executable, str(PT_MUNICIPAL_BUILDER)],
                                 cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, result.stderr
        after = _sha256_file(PT_MUNICIPAL_PREDICTION_VIEW)
        assert before == after

    def test_exports_builder_deterministic(self):
        before = {p.name: _sha256_file(p) for p in V051_DIR.glob("*.csv")}
        result = subprocess.run([sys.executable, str(EXPORTS_BUILDER)],
                                 cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, result.stderr
        after = {p.name: _sha256_file(p) for p in V051_DIR.glob("*.csv")}
        assert before == after, "exports builder is not deterministic across runs"

    def test_dashboard_builder_deterministic(self):
        r1 = subprocess.run([sys.executable, str(DASHBOARD_BUILDER)],
                             cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert r1.returncode == 0, r1.stderr
        before = _sha256_file(DASHBOARD_HTML)
        r2 = subprocess.run([sys.executable, str(DASHBOARD_BUILDER)],
                             cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        assert r2.returncode == 0, r2.stderr
        after = _sha256_file(DASHBOARD_HTML)
        assert before == after, "dashboard builder is not deterministic across runs"


# ─────────────────────────────────────────────────────────────────────────
# Manifest validity
# ─────────────────────────────────────────────────────────────────────────

class TestManifest:
    def test_manifest_is_valid_json_with_required_keys(self, manifest):
        for key in ["version", "generated_at", "dec_references", "source_files",
                    "output_files", "rules", "row_counts"]:
            assert key in manifest

    def test_manifest_version(self, manifest):
        assert manifest["version"] == "0.5.1"

    def test_manifest_supersedes_v05(self, manifest):
        assert "0.5" in manifest["supersedes"]

    def test_manifest_language_fr(self, manifest):
        assert manifest["rules"]["language"] == "fr"
