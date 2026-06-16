"""
DEC-062: Granular Phase 7 Preflight — Frozen Gates H1-H10.

FROZEN before results. Do not modify after first run.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

GATE_VERSION = "DEC-062-v1"

N_CONTINENTAL_MUNICIPALITIES_PT = 278   # confirmed via geocod[0]=='1'
N_EXPECTED_A10_OBSERVABLE = 8           # KZ structurally absent for PT
SECTOR_KZ_STATUS = "structural_absent"
MIN_YEARS = 6
MIN_N_REGIONS = 10

ALLOWED_DECISIONS = {
    "PT_PANEL_READY_NL_OPEN_DATA_BLOCKED",
    "PT_PANEL_READY_NL_SOURCE_FOUND",
    "PT_PANEL_BLOCKED_NL_BLOCKED",
    "GRANULAR_PREFLIGHT_INCONCLUSIVE",
}


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
# H1 — DEC-061 Review Complete
# ---------------------------------------------------------------------------

def check_h1_dec061_review_complete(
    review_exists: bool,
    continental_filter_corrected: bool,
    acores_geocod_documented: bool,
) -> GateResult:
    """DEC-061 reviewed; continental filter corrected (geocod[0]=='1', not '1 or 2')."""
    ok = review_exists and continental_filter_corrected and acores_geocod_documented
    return GateResult(
        gate_id="H1",
        verdict="PASS" if ok else "FAIL",
        value={
            "review_exists": review_exists,
            "continental_filter_corrected": continental_filter_corrected,
            "acores_geocod_documented": acores_geocod_documented,
        },
        threshold={"all_true": True},
        note="DEC-061 used prefix '1 or 2' for continental — Açores (prefix '2') incorrectly included. Corrected to geocod[0]=='1'.",
    )


# ---------------------------------------------------------------------------
# H2 — PT Panel Built
# ---------------------------------------------------------------------------

def check_h2_pt_panel_built(
    csv_exists: bool,
    manifest_exists: bool,
    n_rows: int,
) -> GateResult:
    """pt_municipal_sector_panel.csv created with valid content."""
    ok = csv_exists and manifest_exists and n_rows > 1000
    return GateResult(
        gate_id="H2",
        verdict="PASS" if ok else "FAIL",
        value={"csv_exists": csv_exists, "manifest_exists": manifest_exists, "n_rows": n_rows},
        threshold={"min_rows": 1000},
        note="Panel must exist and have minimum content.",
    )


# ---------------------------------------------------------------------------
# H3 — PT Continental Filter Valid
# ---------------------------------------------------------------------------

def check_h3_pt_continent_filter(
    n_continental: int,
    filter_rule_documented: str,
    no_acores_in_continent: bool,
    no_madeira_in_continent: bool,
) -> GateResult:
    """Continental filter produces ~278 municipalities; Açores and Madeira excluded."""
    ok = (
        abs(n_continental - N_CONTINENTAL_MUNICIPALITIES_PT) <= 2  # allow ±2 for boundary mergers
        and len(filter_rule_documented) > 10
        and no_acores_in_continent
        and no_madeira_in_continent
    )
    return GateResult(
        gate_id="H3",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_continental": n_continental,
            "filter_rule": filter_rule_documented,
            "no_acores": no_acores_in_continent,
            "no_madeira": no_madeira_in_continent,
        },
        threshold={
            "n_continental": N_CONTINENTAL_MUNICIPALITIES_PT,
            "tolerance": 2,
        },
        note="Filter: geocod[0]=='1'. Açores=prefix '2', Madeira=prefix '3'. DEC-061 had a 297 vs 278 discrepancy.",
    )


# ---------------------------------------------------------------------------
# H4 — PT A10 Valid
# ---------------------------------------------------------------------------

def check_h4_pt_a10_valid(
    n_sectors_observable: int,
    kz_status: str,
    sectors_present: list[str],
) -> GateResult:
    """8/9 A10 sectors observable; KZ structural_absent recorded."""
    ok = (
        n_sectors_observable == N_EXPECTED_A10_OBSERVABLE
        and kz_status == SECTOR_KZ_STATUS
    )
    return GateResult(
        gate_id="H4",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_sectors_observable": n_sectors_observable,
            "kz_status": kz_status,
            "sectors_present": sectors_present,
        },
        threshold={
            "n_sectors": N_EXPECTED_A10_OBSERVABLE,
            "kz_status": SECTOR_KZ_STATUS,
        },
        note="KZ (Finance) definitionally excluded from INE enterprise births per DEC-018.",
    )


# ---------------------------------------------------------------------------
# H5 — PT No Missing/Zero Confusion
# ---------------------------------------------------------------------------

def check_h5_pt_no_missing_zero_confusion(
    has_explicit_na_policy: bool,
    zero_documented: bool,
    structural_absent_documented: bool,
) -> GateResult:
    """
    Missing, zero, and structural_absent are distinguishable.
    - Zero (ind_string='0', valor='0'): genuine zero births
    - Missing (valor=''/'NA'): suppressed or absent
    - structural_absent: KZ always NaN by definition
    """
    ok = has_explicit_na_policy and zero_documented and structural_absent_documented
    return GateResult(
        gate_id="H5",
        verdict="PASS" if ok else "FAIL",
        value={
            "explicit_na_policy": has_explicit_na_policy,
            "zero_documented": zero_documented,
            "structural_absent_documented": structural_absent_documented,
        },
        threshold={"all_documented": True},
        note="INE uses valor='0' for genuine zeros; valor='' for suppressed/missing. KZ=NaN by definition.",
    )


# ---------------------------------------------------------------------------
# H6 — NL Search Complete
# ---------------------------------------------------------------------------

def check_h6_nl_search_complete(
    n_tables_evaluated: int,
    search_terms_used: list[str],
    output_csv_exists: bool,
    output_json_exists: bool,
) -> GateResult:
    """CBS catalog searched; all candidates documented."""
    ok = n_tables_evaluated >= 4 and len(search_terms_used) >= 5 and output_csv_exists and output_json_exists
    return GateResult(
        gate_id="H6",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_tables": n_tables_evaluated,
            "n_search_terms": len(search_terms_used),
            "output_csv": output_csv_exists,
            "output_json": output_json_exists,
        },
        threshold={"min_tables": 4, "min_search_terms": 5},
        note="CBS Open Data catalog must be systematically searched.",
    )


# ---------------------------------------------------------------------------
# H7 — NL Decision Conservative
# ---------------------------------------------------------------------------

def check_h7_nl_decision_conservative(
    nl_decision: str,
    no_stock_promoted: bool,
    no_corop_as_gemeente: bool,
) -> GateResult:
    """
    If no gemeente births table found: decision is BLOCKED, not substituted.
    Stock data must not be used as births proxy.
    COROP must not be presented as gemeente.
    """
    ok = no_stock_promoted and no_corop_as_gemeente
    return GateResult(
        gate_id="H7",
        verdict="PASS" if ok else "FAIL",
        value={
            "nl_decision": nl_decision,
            "no_stock_promoted": no_stock_promoted,
            "no_corop_as_gemeente": no_corop_as_gemeente,
        },
        threshold={"conservative": True},
        note="Cannot substitute stock (81575NED) for births, or COROP for gemeente.",
    )


# ---------------------------------------------------------------------------
# H8 — Granular Phase 7 Preflight Generated
# ---------------------------------------------------------------------------

def check_h8_granular_preflight(
    readiness_json_exists: bool,
    has_fr_entry: bool,
    has_pt_entry: bool,
    has_nl_entry: bool,
) -> GateResult:
    """Readiness JSON covers FR, PT, and NL (at appropriate level)."""
    ok = readiness_json_exists and has_fr_entry and has_pt_entry and has_nl_entry
    return GateResult(
        gate_id="H8",
        verdict="PASS" if ok else "FAIL",
        value={
            "readiness_json": readiness_json_exists,
            "has_FR": has_fr_entry,
            "has_PT": has_pt_entry,
            "has_NL": has_nl_entry,
        },
        threshold={"all_countries_covered": True},
        note="Readiness assessment needed for each country at target granularity.",
    )


# ---------------------------------------------------------------------------
# H9 — No Unauthorized Training
# ---------------------------------------------------------------------------

def check_h9_no_unauthorized_training(
    no_model_trained: bool,
    no_phase7_full_run: bool,
) -> GateResult:
    """No neural model trained; no full Phase 7 run executed."""
    ok = no_model_trained and no_phase7_full_run
    return GateResult(
        gate_id="H9",
        verdict="PASS" if ok else "FAIL",
        value={"no_model": no_model_trained, "no_phase7_full": no_phase7_full_run},
        threshold={"no_unauthorized_runs": True},
        note="DEC-062 scope: data audit and preflight only.",
    )


# ---------------------------------------------------------------------------
# H10 — Reproducibility
# ---------------------------------------------------------------------------

def check_h10_reproducibility(
    manifest_has_urls: bool,
    manifest_has_table_ids: bool,
    manifest_has_query_params: bool,
) -> GateResult:
    """Manifests contain URLs, table IDs, and query params for reproducibility."""
    ok = manifest_has_urls and manifest_has_table_ids and manifest_has_query_params
    return GateResult(
        gate_id="H10",
        verdict="PASS" if ok else "FAIL",
        value={
            "has_urls": manifest_has_urls,
            "has_table_ids": manifest_has_table_ids,
            "has_query_params": manifest_has_query_params,
        },
        threshold={"all_documented": True},
        note="All data sources must be reproducible from manifest.",
    )


# ---------------------------------------------------------------------------
# Decision derivation
# ---------------------------------------------------------------------------

def derive_decision_dec062(
    gate_results: list[GateResult],
    pt_ready: bool,
    nl_blocked: bool,
) -> dict:
    by_id = {r.gate_id: r for r in gate_results}
    critical = ["H1", "H2", "H3", "H4", "H5", "H7", "H9", "H10"]
    secondary = ["H6", "H8"]

    critical_fail = [gid for gid in critical if by_id.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict == "FAIL"]
    secondary_fail = [gid for gid in secondary if by_id.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict == "FAIL"]

    n_pass = sum(1 for r in gate_results if r.verdict == "PASS")
    n_fail = sum(1 for r in gate_results if r.verdict == "FAIL")

    if critical_fail:
        decision = "GRANULAR_PREFLIGHT_INCONCLUSIVE"
    elif not pt_ready:
        decision = "PT_PANEL_BLOCKED_NL_BLOCKED"
    elif nl_blocked:
        decision = "PT_PANEL_READY_NL_OPEN_DATA_BLOCKED"
    else:
        decision = "PT_PANEL_READY_NL_SOURCE_FOUND"

    return {
        "decision": decision,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "critical_fail": critical_fail,
        "secondary_fail": secondary_fail,
        "gate_version": GATE_VERSION,
    }
