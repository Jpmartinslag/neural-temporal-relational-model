"""Comprehensive tests for HERALD Observatory v0.3 builder.

The builder runs once per session via a session-scoped fixture so the
expensive CSV rebuild is not repeated for each test.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Import builder
import sys
sys.path.insert(0, str(REPO_ROOT))

from src.data.european_panel.build_observatory_v03 import (
    VALID_A10,
    VALID_ECONOMIC_STATES,
    ROBUST_WINDOWS,
    SECTOR_LABELS,
    build_v03,
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
# Helper
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
# Tests
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
    """Run builder twice; panel checksums must match."""
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
    """Manifest must record correct SHA256 of the written v03 panel."""
    _, manifest, _, _, output_dir = v03_products
    panel_path = output_dir / "herald_observatory_v03_panel.csv"
    actual = _sha256_file(panel_path)
    assert manifest["panel_sha256"] == actual


def test_valid_a10_codes(v03_products):
    panel, *_ = v03_products
    bad = set(panel["sector_id"].unique()) - VALID_A10
    assert not bad, f"Invalid sector_id codes in panel: {bad}"


def test_exactly_12_robust_relations(v03_products):
    _, _, relations_payload, *_ = v03_products
    robust = [e for e in relations_payload["edges"] if e["relation_class"] == "ROBUST"]
    assert len(robust) == 12, f"Expected 12 ROBUST edges, got {len(robust)}"


def test_nl_3_pt_9_fr_0_robust(v03_products):
    _, _, relations_payload, *_ = v03_products
    robust = [e for e in relations_payload["edges"] if e["relation_class"] == "ROBUST"]
    nl = sum(1 for e in robust if e["country"] == "NL")
    pt = sum(1 for e in robust if e["country"] == "PT")
    fr = sum(1 for e in robust if e["country"] == "FR")
    assert nl == 3, f"Expected 3 NL ROBUST, got {nl}"
    assert pt == 9, f"Expected 9 PT ROBUST, got {pt}"
    assert fr == 0, f"Expected 0 FR ROBUST, got {fr}"


def test_no_self_edges(v03_products):
    _, _, relations_payload, *_ = v03_products
    self_edges = [
        e for e in relations_payload["edges"]
        if e["source_sector"] == e["target_sector"]
    ]
    assert not self_edges, f"Self-edges found: {self_edges}"


def test_no_duplicate_relations(v03_products):
    _, _, relations_payload, *_ = v03_products
    seen: set[tuple] = set()
    duplicates: list[tuple] = []
    for e in relations_payload["edges"]:
        k = (e["country"], e["window_start"], e["window_end"], e["source_sector"], e["target_sector"])
        if k in seen:
            duplicates.append(k)
        seen.add(k)
    assert not duplicates, f"Duplicate edges: {duplicates}"


def test_25_total_main_edges(v03_products):
    _, _, relations_payload, *_ = v03_products
    edges = relations_payload["edges"]
    assert len(edges) == 25, f"Expected 25 total main edges, got {len(edges)}"
    main_only = [e for e in edges if e["relation_class"] == "MAIN_ONLY_EXPLORATORY"]
    assert len(main_only) == 13, f"Expected 13 MAIN_ONLY_EXPLORATORY, got {len(main_only)}"


def test_economic_states_valid(v03_products):
    panel, *_ = v03_products
    bad = set(panel["economic_state"].dropna().unique()) - VALID_ECONOMIC_STATES
    assert not bad, f"Invalid economic states: {bad}"


def test_sector_graph_available_fr_zero(v03_products):
    panel, *_ = v03_products
    fr = panel[panel["country"] == "FR"]
    non_zero = fr[fr["sector_graph_available"] != 0]
    assert len(non_zero) == 0, f"FR has {len(non_zero)} rows with sector_graph_available != 0"


def test_sector_graph_available_nl_pt_in_windows(v03_products):
    """NL/PT rows with structural_mask=1 that fall inside a robust window must have sga=1."""
    panel, *_ = v03_products

    for country, windows in ROBUST_WINDOWS.items():
        sub = panel[(panel["country"] == country) & (panel["structural_mask"] == 1)].copy()
        sub["in_window"] = sub["observation_year"].apply(
            lambda y: any(s <= y <= e for s, e in windows)
        )
        in_window = sub[sub["in_window"]]
        wrong = in_window[in_window["sector_graph_available"] != 1]
        assert len(wrong) == 0, (
            f"{country}: {len(wrong)} rows in robust window have sector_graph_available != 1"
        )

        # Outside robust window: sga must be 0
        out_window = sub[~sub["in_window"]]
        wrong_out = out_window[out_window["sector_graph_available"] != 0]
        assert len(wrong_out) == 0, (
            f"{country}: {len(wrong_out)} rows outside robust window have sector_graph_available != 0"
        )


def test_no_causal_language(v03_products):
    """Provenance note must not contain causal language except in the approved negation phrase.

    The full negation clause is: "No structural causality, mechanism, or intervention
    claim is supported." — the entire clause is approved as an explicit disclaimer.
    """
    _, manifest, *_ = v03_products
    note = manifest.get("provenance_note", "")
    # Remove the approved negation clause before checking for forbidden words
    approved_negation = "No structural causality, mechanism, or intervention claim is supported."
    sanitised = note.replace(approved_negation, "")
    bad_words = ["causal", "causes", "Granger", "intervention"]
    found = [w for w in bad_words if w.lower() in sanitised.lower()]
    assert not found, f"Causal language found in provenance_note: {found}\nNote: {note}"


def test_manifest_has_provenance(v03_products):
    _, manifest, *_ = v03_products
    assert "provenance_note" in manifest, "manifest missing 'provenance_note' key"
    assert manifest["provenance_note"], "provenance_note is empty"


def test_manifest_has_checksums(v03_products):
    _, manifest, *_ = v03_products
    assert "panel_sha256" in manifest, "manifest missing 'panel_sha256'"
    assert "v02_panel_sha256" in manifest, "manifest missing 'v02_panel_sha256'"
    assert manifest["v02_panel_sha256"] == "a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e"


def test_sector_relations_json_valid(v03_products):
    """JSON is parseable, has 'edges' key, each edge has required fields."""
    _, _, relations_payload, *_ = v03_products
    assert "edges" in relations_payload, "sector_relations JSON missing 'edges' key"

    required_edge_fields = {
        "country", "window_start", "window_end",
        "source_sector", "source_label", "target_sector", "target_label",
        "beta", "delta_r2", "p_perm", "q_fdr", "bootstrap_sign_stability",
        "n_samples", "relation_class", "sign", "scenario",
    }
    for i, edge in enumerate(relations_payload["edges"]):
        missing = required_edge_fields - set(edge.keys())
        assert not missing, f"Edge {i} missing fields: {missing}"


def test_signs_correct(v03_products):
    """For each ROBUST edge, sign of beta must match the sign in covid_robust_edges.csv."""
    _, _, relations_payload, *_ = v03_products

    covid_robust_path = REPO_ROOT / "data/processed/sector_precedence_results/covid_robust_edges.csv"
    robust_ref = pd.read_csv(covid_robust_path)

    # Build lookup: (country, window_start, window_end, source, target) -> beta_main
    ref_lookup: dict[tuple, float] = {}
    for _, row in robust_ref.iterrows():
        k = (row["country"], int(row["window_start"]), int(row["window_end"]),
             row["source_sector"], row["target_sector"])
        ref_lookup[k] = float(row["beta_main"])

    robust_edges = [e for e in relations_payload["edges"] if e["relation_class"] == "ROBUST"]
    for edge in robust_edges:
        k = (edge["country"], edge["window_start"], edge["window_end"],
             edge["source_sector"], edge["target_sector"])
        assert k in ref_lookup, f"ROBUST edge not found in covid_robust_edges.csv: {k}"
        ref_beta = ref_lookup[k]
        edge_beta = edge["beta"]
        assert (edge_beta >= 0) == (ref_beta >= 0), (
            f"Sign mismatch for {k}: edge beta={edge_beta}, ref beta={ref_beta}"
        )
        expected_sign = "positive" if ref_beta >= 0 else "negative"
        assert edge["sign"] == expected_sign, (
            f"sign field mismatch for {k}: got '{edge['sign']}', expected '{expected_sign}'"
        )


def test_no_promoted_in_relations_from_fr(v03_products):
    """FR has 0 ROBUST relations."""
    _, _, relations_payload, *_ = v03_products
    fr_robust = [
        e for e in relations_payload["edges"]
        if e["country"] == "FR" and e["relation_class"] == "ROBUST"
    ]
    assert len(fr_robust) == 0, f"FR has {len(fr_robust)} ROBUST edges (expected 0)"


def test_manifest_decision(v03_products):
    _, manifest, *_ = v03_products
    assert manifest.get("verdict") == "SECTOR_PRECEDENCE_PROTOTYPE_READY"


def test_summary_json_valid(v03_products):
    """Summary JSON is parseable and has required top-level keys."""
    _, _, _, summary, _ = v03_products
    assert "state_summary" in summary, "summary JSON missing 'state_summary'"
    assert "territory_summary" in summary, "summary JSON missing 'territory_summary'"
    assert isinstance(summary["state_summary"], list)
    assert isinstance(summary["territory_summary"], list)
    assert len(summary["state_summary"]) > 0, "state_summary is empty"
    assert len(summary["territory_summary"]) > 0, "territory_summary is empty"


# ── Dashboard tests ─────────────────────────────────────────────────────────

DASH_PATH = REPO_ROOT / "reports" / "dashboards" / "herald_observatory_v03_dashboard.html"


def test_dashboard_file_exists():
    assert DASH_PATH.is_file(), "herald_observatory_v03_dashboard.html not found"


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


def test_dashboard_no_causal_claim():
    html = DASH_PATH.read_text(encoding="utf-8")
    # Strip approved negation phrases before checking
    stripped = html.replace(
        "No structural causality, mechanism, or intervention claim is supported.", ""
    ).replace(
        "No structural causality, mechanism, or intervention claim is implied.", ""
    ).replace("Not a causal or intervention claim.", "")
    for word in ["causes", "Granger causality", "intervention effect"]:
        assert word not in stripped, f"Causal language found in dashboard: '{word}'"


def test_dashboard_provenance_present():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "DEC-034" in html
    assert "provenance" in html.lower() or "MANIFEST" in html


def test_dashboard_has_country_filter():
    html = DASH_PATH.read_text(encoding="utf-8")
    assert "graph-country" in html or "state-country" in html
