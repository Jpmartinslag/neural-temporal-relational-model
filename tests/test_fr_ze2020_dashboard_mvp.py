"""
Tests for src/data/france_ze2020/build_fr_ze2020_dashboard_mvp.py and its
output reports/dashboards/fr_ze2020_dashboard_mvp.html. See
reports/canonical/HERALD_22_FR_ZE2020_DASHBOARD_MVP.md.
"""

import ast
import base64
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src.data.france_ze2020.build_fr_ze2020_dashboard_mvp import (
    CLEAN_PANEL_PATH,
    GEOMETRY_PATH,
    OUT_PATH,
    PREDICTION_NOT_FOUND_MESSAGE,
    build_dashboard,
    build_geometry_centroids,
    build_ze_data,
    load_clean_panel,
    load_geometry,
    load_predictions,
    load_relation_examples,
    load_relation_signals,
    load_sector_features,
    load_sector_graph_predictions,
    load_sector_panel,
)

REPO_ROOT = Path(__file__).parent.parent
BUILDER_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_dashboard_mvp.py"

FORBIDDEN_WORDS = [
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
]
FORBIDDEN_CAUSAL_PHRASES = ["causal claim", "causal evidence", "proves causality"]


@pytest.fixture(scope="module")
def html():
    assert OUT_PATH.exists(), f"Dashboard not found: {OUT_PATH}"
    return OUT_PATH.read_text(encoding="utf-8")


def test_dashboard_file_exists():
    assert OUT_PATH.exists()


def test_no_forbidden_words_in_dashboard(html):
    lowered = html.lower()
    for word in FORBIDDEN_WORDS:
        assert word not in lowered, f"forbidden word '{word}' found in dashboard HTML"
    for phrase in FORBIDDEN_CAUSAL_PHRASES:
        assert phrase not in lowered


def test_dashboard_language_is_professional_french_not_draft_portuguese(html):
    forbidden_visible_terms = [
        "MVP",
        "exploratorio",
        "Previsao",
        "Previsão",
        "Observado",
        "Setor dominante",
        "conteudo",
        "Etapa",
        "sinal=",
        "estabilidade=",
        "Na ZE",
        "No setor",
        "tem trajetória",
    ]
    for term in forbidden_visible_terms:
        assert term not in html
    required_terms = [
        "France ZE2020 — Intelligence territoriale",
        "Tableau comparatif intégré",
        "Noeuds ZE x secteur",
        "Carte territoriale ZE2020",
        "Graphe des relations détectées",
        "Signaux appris par les modèles",
        "Réseau MLP relationnel",
    ]
    for term in required_terms:
        assert term in html

    assert "<h1>HERALD France" not in html
    assert "[à compléter]" not in html


def test_integrated_comparison_dashboard_is_embedded_and_renamed(html):
    match = re.search(r'const INTEGRATED_DASHBOARD_B64 = "([^"]+)";', html)
    assert match, "integrated dashboard payload missing"
    decoded = base64.b64decode(match.group(1)).decode("utf-8")

    assert "Modèle territorial" in decoded
    assert "HERALD" not in decoded
    assert "Comparaison modèles" in decoded
    assert "Carte territoriale" in html
    assert 'id="integrated-comparison-dashboard"' in html


def test_builder_reads_only_canonical_sources():
    source = BUILDER_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring
    assert "train_herald_v6" not in code_without_docstring
    assert "train_herald_v7" not in code_without_docstring
    assert "semi_v2" not in code_without_docstring
    assert "regime_experiment" not in code_without_docstring


def test_dom_ids_referenced_by_js_exist_in_html(html):
    js_ids = set(re.findall(r"getElementById\('([a-zA-Z0-9_-]+)'\)", html))
    html_ids = set(re.findall(r'id="([a-zA-Z0-9_-]+)"', html))
    assert js_ids.issubset(html_ids)


def test_plotly_targets_exist_as_html_divs(html):
    plot_targets = set(re.findall(r"Plotly\.newPlot\('([a-zA-Z0-9_-]+)'", html))
    html_ids = set(re.findall(r'id="([a-zA-Z0-9_-]+)"', html))
    assert plot_targets.issubset(html_ids)


def test_event_handlers_reference_defined_functions(html):
    handlers = set(re.findall(r'on(?:change|click|input)="([a-zA-Z0-9_]+)\(', html))
    funcs_defined = set(re.findall(r"function ([a-zA-Z0-9_]+)\(", html))
    assert handlers.issubset(funcs_defined)


def test_embedded_ze_data_is_valid_json_and_complete(html):
    match = re.search(r"const ZE_DATA = (.*?);\nconst MAP_METRICS", html, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))
    assert len(data) == 280


def test_ze2020_keys_are_zero_padded_4char_strings(html):
    match = re.search(r"const ZONES = (.*?);\n", html)
    zones = json.loads(match.group(1))
    assert len(zones) == 280
    assert all(isinstance(z, str) and len(z) == 4 for z in zones)


def test_years_include_2025():
    panel = load_clean_panel()
    assert 2025 in panel["year"].unique()


def test_geometry_coverage_documented_when_present():
    panel = load_clean_panel()
    panel_codes = set(panel["ze2020"].unique())
    geo = load_geometry(panel_codes=panel_codes)
    assert geo is not None
    geo_codes = {f["properties"]["ze2020"] for f in geo["features"]}
    assert panel_codes.issubset(geo_codes)
    assert len(geo["features"]) == len(panel_codes)


def test_geometry_centroids_cover_all_dashboard_zones():
    panel = load_clean_panel()
    panel_codes = set(panel["ze2020"].unique())
    geo = load_geometry(panel_codes=panel_codes)
    centroids = build_geometry_centroids(geo)
    assert set(centroids) == panel_codes
    assert all({"lon", "lat"}.issubset(v) for v in centroids.values())


def test_dashboard_has_annual_slider_and_spatial_graph_layer(html):
    assert 'id="year-slider"' in html
    assert 'const CENTROIDS = ' in html
    assert "type: 'scattergeo'" in html
    assert 'id="map-family-select"' in html
    assert 'id="relation-map-list"' in html


def test_dashboard_has_dynamic_year_relation_mode_and_dark_map(html):
    assert 'id="play-year-btn"' in html
    assert "function toggleYearPlayback()" in html
    assert 'id="relation-mode-select"' in html
    assert "Signaux moyens récurrents" in html
    assert "Signaux forts peu stables" in html
    assert "bgcolor: '#171b2d'" in html
    year_slider = re.search(r'id="year-slider" type="range" min="(\d+)" max="(\d+)"', html)
    assert year_slider is not None
    assert int(year_slider.group(1)) >= 2017
    assert int(year_slider.group(2)) == 2025


def test_dashboard_has_indirect_relation_layer(html):
    assert 'id="graph-depth-select"' in html
    assert "1 pas" in html
    assert "2 pas" in html
    assert "3 pas" in html
    assert "4 pas" in html
    assert "5 pas" in html
    assert "6 pas, réseau élargi" in html
    assert "function graphPathsForSelected(maxDepth)" in html
    assert "Chemins relationnels indirects" in html
    assert "chemin relationnel" in html
    assert "dash: 'dot'" in html
    assert "zone pont" in html
    assert "Tous les signaux détectés" in html
    assert 'id="edge-legend"' in html
    assert "Chemin indirect" in html


def test_dashboard_has_simple_network_mode_buttons(html):
    assert 'id="mode-btns"' in html
    assert "setNetworkMode('clear')" in html
    assert "setNetworkMode('strong')" in html
    assert "setNetworkMode('medium')" in html
    assert "setNetworkMode('full')" in html
    assert "Vue claire" in html
    assert "Relations fortes" in html
    assert "Relations moyennes" in html
    assert "Réseau complet" in html
    assert "function setNetworkMode(mode)" in html
    assert "const NETWORK_MODES = " in html


def test_dashboard_has_advanced_controls_collapsed_by_default(html):
    assert '<details class="advanced-controls">' in html
    assert "Mode avancé" in html
    assert 'id="map-family-select"' in html
    assert 'id="min-signal-slider"' in html
    assert 'id="min-stability-slider"' in html
    assert "function setSignalThreshold" in html
    assert "function setStabilityThreshold" in html
    assert '<option value="200">200</option>' in html
    assert "minSignal" in html
    assert "minStability" in html
    assert "function signalBand(value, stability)" in html


def test_indirect_paths_use_bridge_geometry_not_direct_line_only(html):
    assert "r.path.map(function(ze) { return CENTROIDS[ze].lon; })" in html
    assert "r.path.map(function(ze) { return CENTROIDS[ze].lat; })" in html
    assert "r.path.slice(1, -1)" in html
    assert "origine → zone pont → zone atteinte" in html


def test_a10_sector_chart_is_selected_year_bar_with_labels(html):
    assert "orientation: 'h'" in html
    assert "d.sector_labels" in html
    assert "Secteur dominant:" in html
    assert "Structure sectorielle" in html


def test_dominant_sector_map_has_color_legend(html):
    assert 'id="map-legend"' in html
    assert 'id="sector-legend"' in html
    assert "function renderSectorLegend" in html
    assert "legend-chip" in html
    assert "SECTOR_COLORS" in html
    assert "SECTOR_COLOR_INDEX" in html
    assert "sectorLabel(s)" in html


def test_sector_codes_are_embedded_and_colors_are_consistent(html):
    match = re.search(r"const SECTOR_CODES_ALL = (.*?);\n", html)
    assert match is not None
    codes = json.loads(match.group(1))
    assert len(codes) > 0
    assert codes == sorted(codes)


def test_relation_family_labels_are_translated_for_display(html):
    assert "const FAMILY_LABELS_FR" in html
    assert "function familyLabel(code)" in html
    assert "Similarité ZE-ZE" in html
    assert "Spécialisation sectorielle" in html


def test_dashboard_does_not_use_forbidden_draft_terms():
    """Checked against the builder's own HTML_TEMPLATE source rather than the
    rendered output, which also embeds the (vendor, noisy) Plotly library --
    e.g. the CSS color "whitesmoke" or Plotly's own debug hooks would cause
    false positives there."""
    source = BUILDER_PATH.read_text().lower()
    for term in ["smoke", "debug", "prototype"]:
        assert re.search(rf"\b{term}\b", source) is None, (
            f"forbidden draft term '{term}' found in builder source"
        )


def test_geometry_missing_does_not_fabricate_a_map(tmp_path):
    missing_path = tmp_path / "does_not_exist.geojson"
    result = load_geometry(path=missing_path, panel_codes={"0051"})
    assert result is None


def test_predictions_missing_does_not_fabricate_a_series(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"
    result = load_predictions(path=missing_path)
    assert result is None


def test_ze_data_has_no_predictions_when_predictions_file_absent():
    """If predictions is None, build_ze_data must leave predictions empty
    per zone rather than inventing a forecast series."""
    clean_panel = load_clean_panel()
    sector_panel = load_sector_panel()
    sector_features = load_sector_features()
    relation_signals = load_relation_signals()
    relation_examples = load_relation_examples()

    ze_data = build_ze_data(
        clean_panel,
        None,
        sector_panel,
        sector_features,
        None,
        relation_signals,
        relation_examples,
    )
    sample = ze_data["0051"]
    assert sample["predictions"] == {}
    assert sample["sector_pred_compare"] == []


def test_prediction_not_found_message_is_present_in_dashboard(html):
    assert PREDICTION_NOT_FOUND_MESSAGE in html


def test_dashboard_does_not_modify_input_panels():
    before = CLEAN_PANEL_PATH.read_bytes()
    build_dashboard()
    after = CLEAN_PANEL_PATH.read_bytes()
    assert before == after


def test_relation_entries_in_dashboard_match_only_documented_families(html):
    match = re.search(r"const ZE_DATA = (.*?);\nconst MAP_METRICS", html, re.DOTALL)
    data = json.loads(match.group(1))
    expected = {
        "ze_to_ze_similarity",
        "ze_to_ze_same_sector_signal",
        "intra_ze_sector_interaction",
        "ze_sector_specialization",
    }
    families_seen = set()
    for ze_entry in data.values():
        for r in ze_entry["relations"]:
            families_seen.add(r["relation_family"])
    assert families_seen.issubset(expected)
