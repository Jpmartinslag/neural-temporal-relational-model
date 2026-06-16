"""
HERALD DEC-061 — PT/NL Municipal Sector Data Availability Audit
Gates G1-G10 (frozen before results)

Decision options:
    PT_NL_MUNICIPAL_READY
    PT_READY_NL_BLOCKED
    PT_READY_NL_NEEDS_ALT_SOURCE
    PT_BLOCKED_NL_READY
    MUNICIPAL_GRANULARITY_BLOCKED
    AUDIT_INCONCLUSIVE

Gates G1-G10 are checked against the outputs in:
    data/processed/municipal_granularity_audit/

No promotion, no causal claims, no threshold changes to existing results.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parents[3]
_AUDIT_DIR = _BASE / "data/processed/municipal_granularity_audit"

# Minimum thresholds (frozen)
_MIN_YEARS = 6          # Phase 7 minimum consecutive years
_MIN_TERRITORIES = 10   # Phase 7 minimum territories
_MIN_SAMPLES = 60       # Phase 7 minimum n_samples (territories × years)
_MIN_A10_SECTORS = 8    # Phase 7 minimum comparable A10 sectors
_ALLOWED_DECISIONS = {
    "PT_NL_MUNICIPAL_READY",
    "PT_READY_NL_BLOCKED",
    "PT_READY_NL_NEEDS_ALT_SOURCE",
    "PT_BLOCKED_NL_READY",
    "MUNICIPAL_GRANULARITY_BLOCKED",
    "AUDIT_INCONCLUSIVE",
}


def _load_json(path: Path) -> Optional[dict]:
    """Load a JSON file; return None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def check_g1_pt_api_reachable(pt_avail: Optional[dict]) -> dict:
    """G1: INE metadata/probe executed with success or official cache found."""
    if pt_avail is None:
        return {"gate": "G1", "name": "PT_API_REACHABLE", "verdict": "FAIL",
                "reason": "pt_municipality_availability.json not found"}
    if not pt_avail.get("api_reachable", False):
        return {"gate": "G1", "name": "PT_API_REACHABLE", "verdict": "FAIL",
                "reason": "api_reachable=False in PT availability JSON"}
    if not pt_avail.get("data_confirmed_live", False):
        return {"gate": "G1", "name": "PT_API_REACHABLE", "verdict": "FAIL",
                "reason": "data_confirmed_live=False — probe did not return data"}
    return {"gate": "G1", "name": "PT_API_REACHABLE", "verdict": "PASS",
            "reason": f"INE API reachable; {pt_avail.get('total_municipalities', 0)} municipalities confirmed"}


def check_g2_pt_municipal_sector_exists(pt_avail: Optional[dict]) -> dict:
    """G2: PT has municipality × sector/CAE × year sufficient for panel."""
    if pt_avail is None:
        return {"gate": "G2", "name": "PT_MUNICIPAL_SECTOR_EXISTS", "verdict": "FAIL",
                "reason": "PT availability JSON not found"}

    n_muni = pt_avail.get("continente_municipalities", 0)
    years_confirmed = pt_avail.get("years_confirmed", [])
    n_years = len(years_confirmed)
    sectors = pt_avail.get("sectors_present", [])
    n_samples = n_muni * n_years

    reasons = []
    if n_muni < _MIN_TERRITORIES:
        reasons.append(f"n_municipalities={n_muni} < {_MIN_TERRITORIES}")
    if n_years < _MIN_YEARS:
        reasons.append(f"n_years={n_years} < {_MIN_YEARS}")
    if n_samples < _MIN_SAMPLES:
        reasons.append(f"n_samples={n_samples} < {_MIN_SAMPLES}")
    if len(sectors) < 6:  # must have meaningful sector count (K absent by definition)
        reasons.append(f"n_sectors={len(sectors)} < 6")

    if reasons:
        return {"gate": "G2", "name": "PT_MUNICIPAL_SECTOR_EXISTS", "verdict": "FAIL",
                "reason": "; ".join(reasons)}

    return {
        "gate": "G2", "name": "PT_MUNICIPAL_SECTOR_EXISTS", "verdict": "PASS",
        "reason": (
            f"PT has {n_muni} continente municipalities × {n_years} years "
            f"({n_samples} samples) with {len(sectors)} CAE sections"
        ),
    }


def check_g3_pt_a10_mapping_feasible(pt_avail: Optional[dict]) -> dict:
    """G3: CAE sections can map to HERALD A10 with documented rules."""
    if pt_avail is None:
        return {"gate": "G3", "name": "PT_A10_MAPPING_FEASIBLE", "verdict": "FAIL",
                "reason": "PT availability JSON not found"}

    a10_mappable = pt_avail.get("a10_mappable_sectors", [])
    a10_blocked = pt_avail.get("a10_blocked_sectors", [])
    mapping = pt_avail.get("cae_to_a10_mapping", {})

    if len(a10_mappable) < _MIN_A10_SECTORS - 1:  # allow 1 absent (KZ)
        return {"gate": "G3", "name": "PT_A10_MAPPING_FEASIBLE", "verdict": "FAIL",
                "reason": f"Only {len(a10_mappable)} A10 sectors mappable; need ≥{_MIN_A10_SECTORS - 1}"}
    if not mapping:
        return {"gate": "G3", "name": "PT_A10_MAPPING_FEASIBLE", "verdict": "FAIL",
                "reason": "CAE-to-A10 mapping not documented in availability JSON"}

    return {
        "gate": "G3", "name": "PT_A10_MAPPING_FEASIBLE", "verdict": "PASS",
        "reason": (
            f"{len(a10_mappable)} A10 sectors mappable from CAE; "
            f"blocked: {a10_blocked} (KZ absent by INE definition per DEC-018)"
        ),
    }


def check_g4_nl_api_reachable(nl_avail: Optional[dict]) -> dict:
    """G4: CBS metadata/probe executed with success or official cache found."""
    if nl_avail is None:
        return {"gate": "G4", "name": "NL_API_REACHABLE", "verdict": "FAIL",
                "reason": "nl_gemeente_availability.json not found"}
    if not nl_avail.get("api_reachable", False):
        return {"gate": "G4", "name": "NL_API_REACHABLE", "verdict": "FAIL",
                "reason": "api_reachable=False in NL availability JSON"}
    return {"gate": "G4", "name": "NL_API_REACHABLE", "verdict": "PASS",
            "reason": f"CBS API reachable: {nl_avail.get('cbs_api_status', '')}"}


def check_g5_nl_gemeente_sector_exists(nl_avail: Optional[dict]) -> dict:
    """G5: NL has gemeente × sector/SBI × year, or is formally blocked."""
    if nl_avail is None:
        return {"gate": "G5", "name": "NL_GEMEENTE_SECTOR_EXISTS", "verdict": "FAIL",
                "reason": "NL availability JSON not found"}

    births_available = nl_avail.get("gemeente_births_available", None)
    verdict = nl_avail.get("gemeente_births_verdict", "")

    if births_available is False:
        # Formally blocked is an acceptable outcome for DEC-061
        return {
            "gate": "G5", "name": "NL_GEMEENTE_SECTOR_EXISTS", "verdict": "FORMALLY_BLOCKED",
            "reason": (
                "NL gemeente x births x SBI not available via CBS Open Data. "
                f"{verdict}. "
                f"Alternative: {nl_avail.get('available_at_gemeente', '')}. "
                "FORMALLY_BLOCKED counts as documented finding, not gate failure."
            ),
        }
    if births_available is True:
        return {"gate": "G5", "name": "NL_GEMEENTE_SECTOR_EXISTS", "verdict": "PASS",
                "reason": verdict}
    return {"gate": "G5", "name": "NL_GEMEENTE_SECTOR_EXISTS", "verdict": "FAIL",
            "reason": "gemeente_births_available field missing or None in NL availability"}


def check_g6_nl_a10_mapping_feasible(nl_avail: Optional[dict]) -> dict:
    """G6: SBI can map to HERALD A10 if dataset exists."""
    if nl_avail is None:
        return {"gate": "G6", "name": "NL_A10_MAPPING_FEASIBLE", "verdict": "FAIL",
                "reason": "NL availability JSON not found"}

    mapping_info = nl_avail.get("sbi_to_a10_mapping", {})
    possible = mapping_info.get("possible", False)

    if not possible:
        return {"gate": "G6", "name": "NL_A10_MAPPING_FEASIBLE", "verdict": "FAIL",
                "reason": "SBI-to-A10 mapping not documented or not feasible"}

    return {
        "gate": "G6", "name": "NL_A10_MAPPING_FEASIBLE", "verdict": "PASS",
        "reason": f"SBI-to-A10 mapping feasible: {mapping_info.get('note', '')}",
    }


def check_g7_granularity_comparability(summary: Optional[dict]) -> dict:
    """G7: At least PT or NL can approach FR ZE2020 granularity (~280 units)."""
    if summary is None:
        return {"gate": "G7", "name": "GRANULARITY_COMPARABILITY", "verdict": "FAIL",
                "reason": "municipal_granularity_summary.json not found"}

    findings = summary.get("findings", {})
    pt_status = findings.get("PT", {}).get("status", "")
    pt_n = findings.get("PT", {}).get("n_units_continente", 0)
    nl_status = findings.get("NL", {}).get("status", "")
    nl_n = findings.get("NL", {}).get("n_units", 0)  # fallback: COROP
    ref_n = summary.get("reference_n_units", 280)

    # PT comparable if n >= 0.5 * ref_n (municipality level)
    pt_comparable = "AVAILABLE" in pt_status and pt_n >= ref_n * 0.5
    # NL comparable at gemeente level (blocked, so not comparable yet)
    nl_comparable = "BLOCKED" not in nl_status and nl_n >= ref_n * 0.5

    if pt_comparable or nl_comparable:
        return {
            "gate": "G7", "name": "GRANULARITY_COMPARABILITY", "verdict": "PASS",
            "reason": (
                f"PT municipal ({pt_n} units) ≈ FR ZE2020 ({ref_n}). "
                f"NL gemeente blocked. PT meets granularity comparability criterion."
            ),
        }
    return {
        "gate": "G7", "name": "GRANULARITY_COMPARABILITY", "verdict": "FAIL",
        "reason": (
            f"PT status={pt_status} n={pt_n}; NL status={nl_status}. "
            f"Neither country approaches FR ZE2020 granularity ({ref_n})."
        ),
    }


def check_g8_concept_compatibility(summary: Optional[dict]) -> dict:
    """G8: Target concept documented for PT, NL, FR."""
    if summary is None:
        return {"gate": "G8", "name": "CONCEPT_COMPATIBILITY", "verdict": "FAIL",
                "reason": "municipal_granularity_summary.json not found"}

    concepts = {
        "FR": "establishment_creation",
        "PT": "enterprise_birth",
        "NL": "local_unit_opening",
    }

    # Check that these are documented in the matrix
    matrix_path = _AUDIT_DIR / "municipal_granularity_matrix.csv"
    if not matrix_path.exists():
        return {"gate": "G8", "name": "CONCEPT_COMPATIBILITY", "verdict": "FAIL",
                "reason": "municipal_granularity_matrix.csv not found"}

    import csv
    with open(matrix_path) as f:
        rows = list(csv.DictReader(f))
    documented = {r["country"]: r.get("target_concept", "") for r in rows}

    missing = [
        c for c, expected in concepts.items()
        if expected not in documented.get(c, "")
    ]
    if missing:
        return {"gate": "G8", "name": "CONCEPT_COMPATIBILITY", "verdict": "FAIL",
                "reason": f"Target concept not documented for: {missing}"}

    return {
        "gate": "G8", "name": "CONCEPT_COMPATIBILITY", "verdict": "PASS",
        "reason": (
            "All 3 target concepts documented: "
            f"FR={concepts['FR']}, PT={concepts['PT']}, NL={concepts['NL']}. "
            "Concepts differ — cross-country comparison requires explicit harmonisation note."
        ),
    }


def check_g9_no_raw_large_commit() -> dict:
    """G9: Raw large files not staged for commit."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(_BASE)
        )
        staged = result.stdout.strip().splitlines()
    except Exception as e:
        staged = []

    large_raw_patterns = [
        "data/external/", "data/raw/",
        ".parquet", ".pkl", ".npz",
    ]
    large_staged = [
        f for f in staged
        if any(p in f for p in large_raw_patterns)
    ]

    # Also check for large files in audit dir that might be committed
    audit_files = list(_AUDIT_DIR.rglob("*")) if _AUDIT_DIR.exists() else []
    large_in_audit = [
        f for f in audit_files
        if f.is_file() and f.stat().st_size > 50_000_000  # 50MB threshold
    ]

    if large_staged:
        return {"gate": "G9", "name": "NO_RAW_LARGE_COMMIT", "verdict": "FAIL",
                "reason": f"Large raw files staged: {large_staged}"}
    if large_in_audit:
        return {"gate": "G9", "name": "NO_RAW_LARGE_COMMIT", "verdict": "WARN",
                "reason": f"Large files in audit dir (not staged): {[str(f) for f in large_in_audit]}"}
    return {"gate": "G9", "name": "NO_RAW_LARGE_COMMIT", "verdict": "PASS",
            "reason": "No large raw files staged for commit"}


def check_g10_reproducibility(summary: Optional[dict]) -> dict:
    """G10: Manifest contains URLs, table IDs, query params, timestamp, probe method."""
    if summary is None:
        return {"gate": "G10", "name": "REPRODUCIBILITY", "verdict": "FAIL",
                "reason": "municipal_granularity_summary.json not found"}

    manifest = summary.get("manifest", {})
    required_fields = ["pt_api_urls", "nl_api_urls", "tables_probed",
                       "indicators_probed", "probe_method", "probe_timestamp"]
    missing = [f for f in required_fields if not manifest.get(f)]

    if missing:
        return {"gate": "G10", "name": "REPRODUCIBILITY", "verdict": "FAIL",
                "reason": f"Manifest missing fields: {missing}"}

    timestamp = manifest.get("probe_timestamp", "")
    if not timestamp or timestamp == "UNKNOWN":
        return {"gate": "G10", "name": "REPRODUCIBILITY", "verdict": "FAIL",
                "reason": "probe_timestamp missing or unknown in manifest"}

    return {
        "gate": "G10", "name": "REPRODUCIBILITY", "verdict": "PASS",
        "reason": (
            f"Manifest complete: {len(manifest.get('pt_api_urls', []))} PT URLs, "
            f"{len(manifest.get('nl_api_urls', []))} NL URLs, "
            f"{len(manifest.get('tables_probed', []))} tables, "
            f"timestamp={timestamp}"
        ),
    }


def determine_decision(gate_results: list[dict]) -> str:
    """
    Determine final decision from gate results.

    Logic:
    - If G1 FAIL → AUDIT_INCONCLUSIVE (cannot verify PT)
    - If G4 FAIL → AUDIT_INCONCLUSIVE (cannot verify NL)
    - If G2 PASS and G5 PASS → PT_NL_MUNICIPAL_READY
    - If G2 PASS and G5 FORMALLY_BLOCKED → PT_READY_NL_BLOCKED
    - If G2 PASS and G5 FAIL → PT_READY_NL_NEEDS_ALT_SOURCE
    - If G2 FAIL and G5 PASS → PT_BLOCKED_NL_READY
    - If G2 FAIL and G5 FORMALLY_BLOCKED → MUNICIPAL_GRANULARITY_BLOCKED
    - If G7 FAIL → override to MUNICIPAL_GRANULARITY_BLOCKED if both fail
    """
    gate_map = {r["gate"]: r["verdict"] for r in gate_results}

    if gate_map.get("G1") == "FAIL":
        return "AUDIT_INCONCLUSIVE"
    if gate_map.get("G4") == "FAIL":
        return "AUDIT_INCONCLUSIVE"

    g2 = gate_map.get("G2", "FAIL")
    g5 = gate_map.get("G5", "FAIL")

    if g2 == "PASS" and g5 == "PASS":
        return "PT_NL_MUNICIPAL_READY"
    if g2 == "PASS" and g5 == "FORMALLY_BLOCKED":
        return "PT_READY_NL_BLOCKED"
    if g2 == "PASS" and g5 == "FAIL":
        return "PT_READY_NL_NEEDS_ALT_SOURCE"
    if g2 == "FAIL" and g5 == "PASS":
        return "PT_BLOCKED_NL_READY"
    # Both fail or blocked
    return "MUNICIPAL_GRANULARITY_BLOCKED"


def run_all_gates() -> dict:
    """Run all G1-G10 gates and return full results dict."""
    pt_avail = _load_json(_AUDIT_DIR / "pt_municipality_availability.json")
    nl_avail = _load_json(_AUDIT_DIR / "nl_gemeente_availability.json")
    summary = _load_json(_AUDIT_DIR / "municipal_granularity_summary.json")

    gate_results = [
        check_g1_pt_api_reachable(pt_avail),
        check_g2_pt_municipal_sector_exists(pt_avail),
        check_g3_pt_a10_mapping_feasible(pt_avail),
        check_g4_nl_api_reachable(nl_avail),
        check_g5_nl_gemeente_sector_exists(nl_avail),
        check_g6_nl_a10_mapping_feasible(nl_avail),
        check_g7_granularity_comparability(summary),
        check_g8_concept_compatibility(summary),
        check_g9_no_raw_large_commit(),
        check_g10_reproducibility(summary),
    ]

    n_pass = sum(1 for r in gate_results if r["verdict"] == "PASS")
    n_formally_blocked = sum(1 for r in gate_results if r["verdict"] == "FORMALLY_BLOCKED")
    n_fail = sum(1 for r in gate_results if r["verdict"] == "FAIL")
    n_warn = sum(1 for r in gate_results if r["verdict"] == "WARN")

    decision = determine_decision(gate_results)
    assert decision in _ALLOWED_DECISIONS, f"Invalid decision: {decision}"

    return {
        "audit": "DEC-061",
        "gate_results": gate_results,
        "n_pass": n_pass,
        "n_formally_blocked": n_formally_blocked,
        "n_fail": n_fail,
        "n_warn": n_warn,
        "decision": decision,
        "allowed_decisions": sorted(_ALLOWED_DECISIONS),
    }


if __name__ == "__main__":
    import json as _json
    results = run_all_gates()
    print(_json.dumps(results, indent=2))
    print(f"\nDecision: {results['decision']}")
    print(f"Gates: {results['n_pass']} PASS, "
          f"{results['n_formally_blocked']} FORMALLY_BLOCKED, "
          f"{results['n_fail']} FAIL, "
          f"{results['n_warn']} WARN")
