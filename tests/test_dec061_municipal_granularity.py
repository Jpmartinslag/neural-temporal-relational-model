"""
Tests for DEC-061 — PT/NL Municipal Sector Data Availability Audit.

Coverage:
- Matrix has FR/PT/NL rows
- PT does not include islands when continent mode requested
- PT municipality count plausible
- NL gemeente count plausible if available
- Sector A10 mapping documented
- Target concepts registered
- No READY decision if years < 6
- Raw large not listed for commit
- Manifest contains URLs/tables/params
- Gates return one of allowed decisions
"""

import csv
import json
import os
from pathlib import Path

import pytest

_BASE = Path(__file__).resolve().parents[1]
_AUDIT_DIR = _BASE / "data/processed/municipal_granularity_audit"

_ALLOWED_DECISIONS = {
    "PT_NL_MUNICIPAL_READY",
    "PT_READY_NL_BLOCKED",
    "PT_READY_NL_NEEDS_ALT_SOURCE",
    "PT_BLOCKED_NL_READY",
    "MUNICIPAL_GRANULARITY_BLOCKED",
    "AUDIT_INCONCLUSIVE",
}

_READY_DECISIONS = {
    "PT_NL_MUNICIPAL_READY",
    "PT_READY_NL_BLOCKED",
    "PT_READY_NL_NEEDS_ALT_SOURCE",
    "PT_BLOCKED_NL_READY",
}

_MIN_YEARS_FOR_READY = 6


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def matrix_rows():
    path = _AUDIT_DIR / "municipal_granularity_matrix.csv"
    assert path.exists(), f"Matrix CSV not found: {path}"
    with open(path) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def summary():
    path = _AUDIT_DIR / "municipal_granularity_summary.json"
    assert path.exists(), f"Summary JSON not found: {path}"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pt_avail():
    path = _AUDIT_DIR / "pt_municipality_availability.json"
    assert path.exists(), f"PT availability JSON not found: {path}"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def nl_avail():
    path = _AUDIT_DIR / "nl_gemeente_availability.json"
    assert path.exists(), f"NL availability JSON not found: {path}"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pt_probe_rows():
    path = _AUDIT_DIR / "pt_municipality_probe.csv"
    assert path.exists(), f"PT probe CSV not found: {path}"
    with open(path) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def nl_probe_rows():
    path = _AUDIT_DIR / "nl_gemeente_probe.csv"
    assert path.exists(), f"NL probe CSV not found: {path}"
    with open(path) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def gates_results():
    from src.data.european_panel.gates_dec061_municipal_granularity import run_all_gates
    return run_all_gates()


# ============================================================
# T01 — Matrix has FR, PT, NL rows
# ============================================================


def test_t01_matrix_has_fr(matrix_rows):
    countries = {r["country"] for r in matrix_rows}
    assert "FR" in countries, "Matrix must contain FR row"


def test_t02_matrix_has_pt(matrix_rows):
    countries = {r["country"] for r in matrix_rows}
    assert "PT" in countries, "Matrix must contain PT row"


def test_t03_matrix_has_nl(matrix_rows):
    countries = {r["country"] for r in matrix_rows}
    assert "NL" in countries, "Matrix must contain NL row"


# ============================================================
# T04 — PT does not include islands when continent requested
# ============================================================


def test_t04_pt_continente_excludes_islands(pt_avail):
    """Continente count must be less than total (islands present in total)."""
    total = pt_avail.get("total_municipalities", 0)
    continente = pt_avail.get("continente_municipalities", 0)
    assert continente < total, (
        f"continente ({continente}) must be < total ({total}); "
        "islands should be separable"
    )


def test_t05_pt_continente_not_includes_madeira(pt_avail):
    """Madeira count must be documented separately and > 0."""
    madeira = pt_avail.get("madeira_municipalities", 0)
    assert madeira > 0, "Madeira municipalities must be documented"


def test_t06_pt_continente_plausible_range(pt_avail):
    """Continente count: expect 270-285 (known: 278 continental)."""
    continente = pt_avail.get("continente_municipalities", 0)
    assert 270 <= continente <= 290, (
        f"PT continente count {continente} outside plausible range 270-290"
    )


# ============================================================
# T07 — PT municipality count plausible
# ============================================================


def test_t07_pt_total_municipalities_plausible(pt_avail):
    """Total PT municipalities: expect 300-315 (known: 308)."""
    total = pt_avail.get("total_municipalities", 0)
    assert 300 <= total <= 315, (
        f"PT total municipalities {total} outside plausible range 300-315"
    )


def test_t08_pt_probe_rows_cover_multiple_years(pt_probe_rows):
    """PT probe must cover at least 6 distinct years."""
    years = {int(r["year"]) for r in pt_probe_rows}
    assert len(years) >= 6, f"PT probe covers only {len(years)} years; need ≥6"


def test_t09_pt_probe_confirms_api_reachable(pt_probe_rows):
    """At least one probe row must be confirmed live (not just cached)."""
    live = [r for r in pt_probe_rows if "CONFIRMED" in r.get("data_status", "")]
    assert len(live) >= 1, "No PT probe row has CONFIRMED status"


def test_t10_pt_no_k_sector(pt_avail):
    """K sector (finance) must be absent from PT data — confirmed by DEC-018."""
    has_k = pt_avail.get("sectors_present", [])
    assert "K" not in has_k, (
        "K sector appears in PT sectors_present; should be absent per DEC-018"
    )
    blocked = pt_avail.get("a10_blocked_sectors", [])
    assert "KZ" in blocked, "KZ must be listed in a10_blocked_sectors for PT"


# ============================================================
# T11 — NL gemeente count plausible if available
# ============================================================


def test_t11_nl_probe_tables_documented(nl_probe_rows):
    """NL probe must document at least 2 tables."""
    assert len(nl_probe_rows) >= 2, f"NL probe has only {len(nl_probe_rows)} tables"


def test_t12_nl_83631ned_no_gemeente(nl_probe_rows):
    """CBS 83631NED must be documented as having no gemeente dimension."""
    row = next((r for r in nl_probe_rows if r["table"] == "83631NED"), None)
    assert row is not None, "83631NED not found in NL probe CSV"
    has_gm = row.get("has_gemeente", "").lower()
    assert has_gm in ("false", "0", "no", ""), (
        f"83631NED documented as having gemeente={has_gm}; expected False"
    )


def test_t13_nl_81575ned_has_gemeente(nl_probe_rows):
    """CBS 81575NED (stock) must be documented as having gemeente dimension."""
    row = next((r for r in nl_probe_rows if r["table"] == "81575NED"), None)
    assert row is not None, "81575NED not found in NL probe CSV"
    has_gm = row.get("has_gemeente", "").lower()
    assert has_gm in ("true", "1", "yes"), (
        f"81575NED documented as has_gemeente={has_gm}; expected True"
    )


def test_t14_nl_gemeente_count_plausible(nl_avail):
    """If gemeente data available, count should be in plausible range 300-550."""
    births_available = nl_avail.get("gemeente_births_available", False)
    if not births_available:
        pytest.skip("NL gemeente births not available — gemeente count test skipped")
    # If somehow available, check plausibility
    tables = nl_avail.get("tables_probed", [])
    gm_counts = [t.get("gm_codes", 0) for t in tables if t.get("has_gemeente")]
    if gm_counts:
        for n in gm_counts:
            assert 300 <= n <= 600, f"NL gemeente count {n} outside plausible range"


def test_t15_nl_stock_gemeente_count_plausible(nl_probe_rows):
    """81575NED gemeente count (stock table) should be plausible (300-600)."""
    row = next((r for r in nl_probe_rows if r["table"] == "81575NED"), None)
    if row is None:
        pytest.skip("81575NED row not found")
    gm_str = row.get("gm_codes", "0")
    try:
        gm_n = int(gm_str)
    except ValueError:
        pytest.skip(f"gm_codes not integer: {gm_str}")
    assert 300 <= gm_n <= 600, (
        f"81575NED gemeente count {gm_n} outside plausible range 300-600"
    )


# ============================================================
# T16 — Sector A10 mapping documented
# ============================================================


def test_t16_pt_a10_mapping_documented(pt_avail):
    """CAE-to-A10 mapping must be present in PT availability."""
    mapping = pt_avail.get("cae_to_a10_mapping", {})
    assert len(mapping) >= 7, (
        f"PT A10 mapping has only {len(mapping)} entries; expect ≥7 A10 sectors"
    )


def test_t17_nl_sbi_a10_mapping_documented(nl_avail):
    """SBI-to-A10 mapping must be documented in NL availability."""
    mapping = nl_avail.get("sbi_to_a10_mapping", {})
    assert mapping.get("possible") is True, "NL SBI-to-A10 mapping must be documented as possible"
    assert "note" in mapping, "NL SBI-to-A10 mapping must include a note"


def test_t18_fr_a10_sectors_in_matrix(matrix_rows):
    """FR row must document 9 A10 sectors."""
    fr_row = next((r for r in matrix_rows if r["country"] == "FR"), None)
    assert fr_row is not None
    sector_info = fr_row.get("sector_classification", "")
    # Should mention 9 sectors or A10
    assert "A10" in sector_info or "9 sector" in sector_info, (
        f"FR sector_classification should reference A10 or 9 sectors: {sector_info}"
    )


# ============================================================
# T19 — Target concepts registered
# ============================================================


def test_t19_fr_concept_registered(matrix_rows):
    fr_row = next((r for r in matrix_rows if r["country"] == "FR"), None)
    assert fr_row is not None
    assert "establishment_creation" in fr_row.get("target_concept", ""), (
        f"FR target_concept should be establishment_creation, got: {fr_row.get('target_concept')}"
    )


def test_t20_pt_concept_registered(matrix_rows):
    pt_row = next((r for r in matrix_rows if r["country"] == "PT"), None)
    assert pt_row is not None
    assert "enterprise_birth" in pt_row.get("target_concept", ""), (
        f"PT target_concept should be enterprise_birth, got: {pt_row.get('target_concept')}"
    )


def test_t21_nl_concept_registered(matrix_rows):
    nl_row = next((r for r in matrix_rows if r["country"] == "NL"), None)
    assert nl_row is not None
    assert "local_unit_opening" in nl_row.get("target_concept", ""), (
        f"NL target_concept should be local_unit_opening, got: {nl_row.get('target_concept')}"
    )


# ============================================================
# T22 — No READY decision if years < 6
# ============================================================


def test_t22_no_ready_if_years_insufficient(pt_avail, summary):
    """If years < 6, decision must not be a READY variant."""
    years_confirmed = pt_avail.get("years_confirmed", [])
    n_years = len(years_confirmed)
    decision = summary.get("decision", "AUDIT_INCONCLUSIVE")
    if n_years < _MIN_YEARS_FOR_READY:
        assert decision not in _READY_DECISIONS, (
            f"Decision {decision} is READY but PT only has {n_years} years"
        )


def test_t23_pt_has_sufficient_years(pt_avail):
    """PT confirmed years must be ≥ 6 for any READY outcome."""
    years = pt_avail.get("years_confirmed", [])
    assert len(years) >= _MIN_YEARS_FOR_READY, (
        f"PT has only {len(years)} confirmed years; need ≥{_MIN_YEARS_FOR_READY}"
    )


# ============================================================
# T24 — Raw large not listed for commit
# ============================================================


def test_t24_no_large_raw_in_audit_dir():
    """No file > 50MB in the audit output directory."""
    if not _AUDIT_DIR.exists():
        pytest.skip("Audit dir not found")
    large_files = [
        f for f in _AUDIT_DIR.rglob("*")
        if f.is_file() and f.stat().st_size > 50_000_000
    ]
    assert not large_files, (
        f"Large raw files found in audit dir: {[str(f) for f in large_files]}"
    )


def test_t25_probe_csv_reasonable_size():
    """PT and NL probe CSVs must be < 1MB (metadata only, not raw data)."""
    for name in ["pt_municipality_probe.csv", "nl_gemeente_probe.csv"]:
        path = _AUDIT_DIR / name
        if path.exists():
            size = path.stat().st_size
            assert size < 1_000_000, (
                f"{name} is {size} bytes; should be < 1MB (metadata probe only)"
            )


# ============================================================
# T26 — Manifest contains URLs/tables/params
# ============================================================


def test_t26_manifest_has_pt_urls(summary):
    manifest = summary.get("manifest", {})
    pt_urls = manifest.get("pt_api_urls", [])
    assert len(pt_urls) >= 1, "Manifest must contain at least 1 PT API URL"
    for url in pt_urls:
        assert "ine.pt" in url or "INE" in url.upper(), (
            f"PT URL does not reference INE: {url}"
        )


def test_t27_manifest_has_nl_urls(summary):
    manifest = summary.get("manifest", {})
    nl_urls = manifest.get("nl_api_urls", [])
    assert len(nl_urls) >= 1, "Manifest must contain at least 1 NL API URL"
    for url in nl_urls:
        assert "cbs.nl" in url or "CBS" in url.upper(), (
            f"NL URL does not reference CBS: {url}"
        )


def test_t28_manifest_has_tables(summary):
    manifest = summary.get("manifest", {})
    tables = manifest.get("tables_probed", [])
    assert len(tables) >= 2, "Manifest must list ≥2 tables probed"
    assert "83631NED" in tables, "83631NED must be in probed tables"


def test_t29_manifest_has_indicators(summary):
    manifest = summary.get("manifest", {})
    indicators = manifest.get("indicators_probed", [])
    assert len(indicators) >= 2, "Manifest must list ≥2 INE indicators probed"
    assert "0009703" in indicators, "0009703 must be in probed indicators"


def test_t30_manifest_has_timestamp(summary):
    manifest = summary.get("manifest", {})
    ts = manifest.get("probe_timestamp", "")
    assert ts and ts != "UNKNOWN", f"Manifest probe_timestamp missing or unknown: {ts}"
    # Must look like an ISO timestamp
    assert "2026" in ts or "2025" in ts, f"Probe timestamp looks wrong: {ts}"


# ============================================================
# T31 — Gates return allowed decision
# ============================================================


def test_t31_gates_return_allowed_decision(gates_results):
    decision = gates_results.get("decision", "")
    assert decision in _ALLOWED_DECISIONS, (
        f"Decision '{decision}' not in allowed set: {_ALLOWED_DECISIONS}"
    )


def test_t32_gates_all_have_verdict(gates_results):
    for g in gates_results.get("gate_results", []):
        assert "verdict" in g, f"Gate {g.get('gate')} missing verdict"
        assert g["verdict"] in {"PASS", "FAIL", "WARN", "FORMALLY_BLOCKED"}, (
            f"Gate {g.get('gate')} has invalid verdict: {g['verdict']}"
        )


def test_t33_gates_count_ten(gates_results):
    assert len(gates_results.get("gate_results", [])) == 10, (
        "Expected exactly 10 gates (G1-G10)"
    )


def test_t34_g1_passes(gates_results):
    """G1 (PT API reachable) must PASS given confirmed live data."""
    gate_map = {r["gate"]: r["verdict"] for r in gates_results["gate_results"]}
    assert gate_map.get("G1") == "PASS", (
        f"G1 PT_API_REACHABLE failed: {gate_map.get('G1')}"
    )


def test_t35_g2_passes(gates_results):
    """G2 (PT municipal sector exists) must PASS given confirmed data."""
    gate_map = {r["gate"]: r["verdict"] for r in gates_results["gate_results"]}
    assert gate_map.get("G2") == "PASS", (
        f"G2 PT_MUNICIPAL_SECTOR_EXISTS failed: {gate_map.get('G2')}"
    )


def test_t36_g4_passes(gates_results):
    """G4 (NL API reachable) must PASS given confirmed CBS access."""
    gate_map = {r["gate"]: r["verdict"] for r in gates_results["gate_results"]}
    assert gate_map.get("G4") == "PASS", (
        f"G4 NL_API_REACHABLE failed: {gate_map.get('G4')}"
    )


def test_t37_g5_formally_blocked(gates_results):
    """G5 (NL gemeente births) must be FORMALLY_BLOCKED — no CBS table exists."""
    gate_map = {r["gate"]: r["verdict"] for r in gates_results["gate_results"]}
    assert gate_map.get("G5") == "FORMALLY_BLOCKED", (
        f"G5 NL_GEMEENTE_SECTOR_EXISTS should be FORMALLY_BLOCKED; got {gate_map.get('G5')}"
    )


def test_t38_g8_concept_compatibility_passes(gates_results):
    """G8 (concept compatibility) must PASS — all 3 concepts documented."""
    gate_map = {r["gate"]: r["verdict"] for r in gates_results["gate_results"]}
    assert gate_map.get("G8") == "PASS", (
        f"G8 CONCEPT_COMPATIBILITY failed: {gate_map.get('G8')}"
    )


def test_t39_decision_is_pt_ready_nl_blocked(gates_results):
    """Expected decision: PT_READY_NL_BLOCKED."""
    assert gates_results["decision"] == "PT_READY_NL_BLOCKED", (
        f"Expected PT_READY_NL_BLOCKED, got {gates_results['decision']}"
    )


def test_t40_no_causal_language_in_summary(summary):
    """Summary JSON must not contain causal language."""
    text = json.dumps(summary).lower()
    forbidden = ["causes", "effect of", "granger", "causal attribution"]
    for word in forbidden:
        assert word not in text, (
            f"Causal language '{word}' found in summary JSON"
        )
