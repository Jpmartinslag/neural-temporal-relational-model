"""
DEC-063: Granular FR/PT/NL Evidence Model — Frozen Gates G1-G10.

FROZEN before results. Do not modify after first run.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

GATE_VERSION = "DEC-063-v1"

ALLOWED_DECISIONS = {
    "GRANULAR_FR_PT_NL_PREFLIGHT_READY",
    "BLOCKED_PROXY_INVALID",
    "BLOCKED_SOURCE_MISSING",
    "BLOCKED_EVIDENCE_CONTAMINATION",
    "GRANULAR_EVIDENCE_INCONCLUSIVE",
}

# Reaggregation tolerance
REAG_TOL_REL = 0.001
REAG_TOL_ABS = 5.0


@dataclass
class GateResult:
    gate_id: str
    verdict: str   # "PASS" or "FAIL"
    value: Any
    threshold: Any
    note: str

    def as_dict(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "verdict": self.verdict,
            "value": self.value,
            "threshold": self.threshold,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# G1 — Sources Accessible and Registered
# ---------------------------------------------------------------------------

def check_g1_sources_registered(
    births_exists: bool,
    stock_exists: bool,
    crosswalk_exists: bool,
    proxy_exists: bool,
) -> GateResult:
    """83631NED births, 81575NED stock, crosswalk, and proxy panel all present."""
    ok = births_exists and stock_exists and crosswalk_exists and proxy_exists
    return GateResult(
        gate_id="G1",
        verdict="PASS" if ok else "FAIL",
        value={
            "births_83631NED": births_exists,
            "stock_81575NED": stock_exists,
            "crosswalk_84721NED": crosswalk_exists,
            "proxy_panel": proxy_exists,
        },
        threshold={"all_present": True},
        note="All source files must exist before evidence model is declared ready.",
    )


# ---------------------------------------------------------------------------
# G2 — 83631NED is COROP-only (0 GM codes)
# ---------------------------------------------------------------------------

def check_g2_births_corop_only(
    n_gm_in_births: int,
    n_cr_in_births: int,
) -> GateResult:
    """83631NED contains 0 GM codes and ≥40 CR codes."""
    ok = n_gm_in_births == 0 and n_cr_in_births >= 40
    return GateResult(
        gate_id="G2",
        verdict="PASS" if ok else "FAIL",
        value={"n_gm": n_gm_in_births, "n_cr": n_cr_in_births},
        threshold={"n_gm": 0, "min_n_cr": 40},
        note="83631NED confirmed COROP-only. Cannot provide direct gemeente births.",
    )


# ---------------------------------------------------------------------------
# G3 — 81575NED is gemeente stock (not births)
# ---------------------------------------------------------------------------

def check_g3_stock_not_births(
    metric_col: str,
    evidence_type_in_panel: str,
    has_gemeente_codes: bool,
) -> GateResult:
    """81575NED metric is Vestigingen_1 (stock), evidence_type = observed_stock."""
    ok = (
        metric_col == "Vestigingen_1"
        and evidence_type_in_panel == "observed_stock"
        and has_gemeente_codes
    )
    return GateResult(
        gate_id="G3",
        verdict="PASS" if ok else "FAIL",
        value={
            "metric_col": metric_col,
            "evidence_type": evidence_type_in_panel,
            "has_gemeente": has_gemeente_codes,
        },
        threshold={
            "metric": "Vestigingen_1",
            "evidence_type": "observed_stock",
        },
        note="81575NED is establishment stock, not births. Must be marked observed_stock.",
    )


# ---------------------------------------------------------------------------
# G4 — Proxy re-aggregates to COROP births
# ---------------------------------------------------------------------------

def check_g4_proxy_reaggregates(
    reagg_status: str,
    max_abs_error: float | None,
    max_rel_error: float | None,
) -> GateResult:
    """Proxy re-aggregated by COROP must recover observed COROP births within tolerance."""
    if reagg_status == "PASS" and max_abs_error is not None and max_rel_error is not None:
        ok = max_abs_error <= REAG_TOL_ABS or max_rel_error <= REAG_TOL_REL
    else:
        ok = reagg_status == "PASS"
    return GateResult(
        gate_id="G4",
        verdict="PASS" if ok else "FAIL",
        value={
            "reagg_status": reagg_status,
            "max_abs_error": max_abs_error,
            "max_rel_error": max_rel_error,
        },
        threshold={"abs_tol": REAG_TOL_ABS, "rel_tol": REAG_TOL_REL},
        note=(
            "Proxy must re-aggregate to observed COROP births (mathematical identity). "
            "Failure = internal inconsistency in proxy construction."
        ),
    )


# ---------------------------------------------------------------------------
# G5 — FR/PT observed never receive proxy flag
# ---------------------------------------------------------------------------

def check_g5_fr_pt_not_proxy(
    fr_evidence_types: list[str],
    pt_evidence_types: list[str],
) -> GateResult:
    """FR and PT panels must not contain any proxy evidence_type."""
    bad_fr = [t for t in fr_evidence_types if "proxy" in t.lower()]
    bad_pt = [t for t in pt_evidence_types if "proxy" in t.lower()]
    ok = len(bad_fr) == 0 and len(bad_pt) == 0
    return GateResult(
        gate_id="G5",
        verdict="PASS" if ok else "FAIL",
        value={"bad_fr": bad_fr, "bad_pt": bad_pt},
        threshold={"no_proxy_in_fr_or_pt": True},
        note="FR and PT are observed_births. Proxy is NL-gemeente only.",
    )


# ---------------------------------------------------------------------------
# G6 — KZ structural_absent preserved for PT
# ---------------------------------------------------------------------------

def check_g6_pt_kz_absent(
    pt_kz_is_all_nan: bool,
    pt_kz_has_zeros: bool,
) -> GateResult:
    """PT sector_KZ must be NaN (structural_absent), never 0."""
    ok = pt_kz_is_all_nan and not pt_kz_has_zeros
    return GateResult(
        gate_id="G6",
        verdict="PASS" if ok else "FAIL",
        value={"kz_all_nan": pt_kz_is_all_nan, "kz_has_zeros": pt_kz_has_zeros},
        threshold={"kz_all_nan": True, "kz_no_zeros": True},
        note="PT KZ (Finance) definitionally excluded from INE enterprise births.",
    )


# ---------------------------------------------------------------------------
# G7 — No large raw files committed
# ---------------------------------------------------------------------------

def check_g7_no_large_raw_committed(
    no_large_stock_raw: bool,
    no_large_births_raw: bool,
    no_large_crosswalk_raw: bool,
) -> GateResult:
    """No raw API dumps >2MB committed as tracked artefacts."""
    ok = no_large_stock_raw and no_large_births_raw and no_large_crosswalk_raw
    return GateResult(
        gate_id="G7",
        verdict="PASS" if ok else "FAIL",
        value={
            "stock_raw_ok": no_large_stock_raw,
            "births_raw_ok": no_large_births_raw,
            "crosswalk_raw_ok": no_large_crosswalk_raw,
        },
        threshold={"max_raw_size_mb": 2},
        note="Raw CBS API responses must not be committed. Manifests with URLs suffice.",
    )


# ---------------------------------------------------------------------------
# G8 — Tests pass
# ---------------------------------------------------------------------------

def check_g8_tests_pass(n_tests_pass: int, n_tests_fail: int) -> GateResult:
    """All mandatory tests must pass."""
    ok = n_tests_fail == 0 and n_tests_pass > 0
    return GateResult(
        gate_id="G8",
        verdict="PASS" if ok else "FAIL",
        value={"n_pass": n_tests_pass, "n_fail": n_tests_fail},
        threshold={"n_fail": 0},
        note="tests/test_granular_fr_pt_nl_evidence_model.py must be all green.",
    )


# ---------------------------------------------------------------------------
# G9 — No causal language
# ---------------------------------------------------------------------------

def check_g9_no_causal_language(
    no_causal_in_proxy_manifest: bool,
    no_causal_in_report: bool,
) -> GateResult:
    """No causal language ('causes', 'drives', 'leads to') in manifests or reports."""
    ok = no_causal_in_proxy_manifest and no_causal_in_report
    return GateResult(
        gate_id="G9",
        verdict="PASS" if ok else "FAIL",
        value={
            "manifest_ok": no_causal_in_proxy_manifest,
            "report_ok": no_causal_in_report,
        },
        threshold={"no_causal_language": True},
        note="Language must be: 'association', 'precedence', 'predictive impact', 'proxy'.",
    )


# ---------------------------------------------------------------------------
# G10 — Documentation complete
# ---------------------------------------------------------------------------

def check_g10_documentation_complete(
    report_exists: bool,
    contract_exists: bool,
    codex_updated: bool,
    artifact_registry_updated: bool,
) -> GateResult:
    """Report, contract, CODEX_MEMORY, and artifact registry all updated."""
    ok = report_exists and contract_exists and codex_updated and artifact_registry_updated
    return GateResult(
        gate_id="G10",
        verdict="PASS" if ok else "FAIL",
        value={
            "report": report_exists,
            "contract": contract_exists,
            "codex": codex_updated,
            "registry": artifact_registry_updated,
        },
        threshold={"all_updated": True},
        note="Full documentation trail required before granular training may begin.",
    )


# ---------------------------------------------------------------------------
# Decision derivation
# ---------------------------------------------------------------------------

def derive_decision_dec063(gate_results: list[GateResult]) -> dict:
    by_id = {r.gate_id: r for r in gate_results}
    critical = ["G1", "G2", "G3", "G4", "G5", "G6", "G8"]
    secondary = ["G7", "G9", "G10"]

    def _v(gid: str) -> str:
        return by_id.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict

    critical_fail = [g for g in critical if _v(g) == "FAIL"]
    secondary_fail = [g for g in secondary if _v(g) == "FAIL"]
    n_pass = sum(1 for r in gate_results if r.verdict == "PASS")
    n_fail = sum(1 for r in gate_results if r.verdict == "FAIL")

    if not critical_fail and not secondary_fail:
        decision = "GRANULAR_FR_PT_NL_PREFLIGHT_READY"
    elif "G4" in critical_fail:
        decision = "BLOCKED_PROXY_INVALID"
    elif "G5" in critical_fail or "G6" in critical_fail:
        decision = "BLOCKED_EVIDENCE_CONTAMINATION"
    elif "G1" in critical_fail or "G2" in critical_fail or "G3" in critical_fail:
        decision = "BLOCKED_SOURCE_MISSING"
    elif critical_fail:
        decision = "GRANULAR_EVIDENCE_INCONCLUSIVE"
    else:
        decision = "GRANULAR_FR_PT_NL_PREFLIGHT_READY"

    return {
        "decision": decision,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "critical_fail": critical_fail,
        "secondary_fail": secondary_fail,
        "gate_version": GATE_VERSION,
    }
