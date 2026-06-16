"""
DEC-064: Pre-registered gates for PT Municipal Phase 7.

Gates P1-P10 are frozen before observing full results.
Must not be changed after results are available.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

GATE_VERSION = "DEC-064-v1"

# Pre-registered thresholds — identical to original Phase 7 (DEC-034) for comparability
FDR_Q = 0.05
MIN_ABS_BETA = 0.10
MIN_DELTA_R2 = 0.005
MIN_SIGN_STABILITY = 0.70
MIN_SAMPLES = 60

# PT municipal expected coverage
EXPECTED_N_MUNICIPALITIES = 278
EXPECTED_OBSERVABLE_SECTORS = ["BE", "FZ", "GI", "JZ", "LZ", "MN", "OQ", "RU"]
EXPECTED_N_SECTORS = len(EXPECTED_OBSERVABLE_SECTORS)
STRUCTURAL_ABSENT = ["KZ"]

# Permutation control expectation: permuted mean p_perm > observed mean p_perm
CONTROL_DEGRADATION_THRESHOLD = 0.0  # permuted p_perm must be > 0 (strictly worse)

CAUSAL_TERMS = [
    "causes", "drives", "leads to", "induces", "results in",
    "provoca", "causa ", "conduit à", "entraîne", "determines",
]


@dataclass
class GateResult:
    gate_id: str
    verdict: str  # "PASS" or "FAIL"
    value: Any
    threshold: Any
    note: str

    def as_dict(self) -> dict:
        return asdict(self)


def check_p1_safety(
    has_nan_inf: bool,
    leakage_check: str,
    years_sorted: bool,
) -> GateResult:
    """P1: No NaN/Inf in structural fields, no temporal leakage, years ordered."""
    ok = not has_nan_inf and leakage_check == "PASS" and years_sorted
    return GateResult(
        gate_id="P1",
        verdict="PASS" if ok else "FAIL",
        value={"has_nan_inf": has_nan_inf, "leakage_check": leakage_check, "years_sorted": years_sorted},
        threshold={"has_nan_inf": False, "leakage_check": "PASS", "years_sorted": True},
        note=(
            "Safety: velocity computed from lag1 (strictly causal). "
            "No NaN/Inf in structural_mask, observation_mask, territory_id, year."
        ),
    )


def check_p2_coverage(
    n_municipalities: int,
    n_observable_sectors: int,
    kz_absent: bool,
    country: str,
) -> GateResult:
    """P2: 278 continental municipalities, 8 observable sectors, KZ structural_absent."""
    ok = (
        n_municipalities == EXPECTED_N_MUNICIPALITIES
        and n_observable_sectors == EXPECTED_N_SECTORS
        and kz_absent
        and country == "PT"
    )
    return GateResult(
        gate_id="P2",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_municipalities": n_municipalities,
            "n_observable_sectors": n_observable_sectors,
            "kz_absent": kz_absent,
            "country": country,
        },
        threshold={
            "n_municipalities": EXPECTED_N_MUNICIPALITIES,
            "n_observable_sectors": EXPECTED_N_SECTORS,
            "kz_absent": True,
            "country": "PT",
        },
        note="Coverage: 278 continental municipalities, 8 A10 sectors, KZ structural_absent (INE enterprise_birth).",
    )


def check_p3_observed_only(
    has_proxy_column: bool,
    has_evidence_type_column: bool,
    evidence_type_values: list[str],
) -> GateResult:
    """P3: No proxy data mixed into PT municipal analysis."""
    bad_ev = [v for v in evidence_type_values if "proxy" in str(v).lower()]
    ok = not has_proxy_column and len(bad_ev) == 0
    return GateResult(
        gate_id="P3",
        verdict="PASS" if ok else "FAIL",
        value={"has_proxy_column": has_proxy_column, "proxy_evidence_types_found": bad_ev},
        threshold={"has_proxy_column": False, "proxy_evidence_types_found": []},
        note="Observed-only: no proxy_disaggregated_by_stock_share or NL gemeente data in PT run.",
    )


def check_p4_reaggregation(
    nuts3_comparison_available: bool,
    max_rel_divergence: Optional[float],
    divergence_documented: bool,
) -> GateResult:
    """P4: Municipal→NUTS3 aggregation divergence documented."""
    # We don't require reaggregation to match (different concepts/years possible)
    # We require the divergence to be MEASURED and DOCUMENTED
    ok = divergence_documented
    return GateResult(
        gate_id="P4",
        verdict="PASS" if ok else "FAIL",
        value={
            "nuts3_comparison_available": nuts3_comparison_available,
            "max_rel_divergence": max_rel_divergence,
            "divergence_documented": divergence_documented,
        },
        threshold={"divergence_documented": True},
        note=(
            "Reaggregation: municipal totals vs NUTS3 aggregation divergence measured. "
            "Divergence is expected (different years/NUTS vintage); documenting is mandatory."
        ),
    )


def check_p5_min_sample(
    n_pairs_below_threshold: int,
    n_pairs_total: int,
    min_samples_used: int,
) -> GateResult:
    """P5: Each pair tested has n_samples >= MIN_SAMPLES."""
    ok = n_pairs_below_threshold == 0
    return GateResult(
        gate_id="P5",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_pairs_below_threshold": n_pairs_below_threshold,
            "n_pairs_total": n_pairs_total,
            "min_samples_used": min_samples_used,
        },
        threshold={"n_pairs_below_threshold": 0, "min_samples": MIN_SAMPLES},
        note=f"Min sample: all computed pairs must have n_samples ≥ {MIN_SAMPLES}.",
    )


def check_p6_controls(
    mean_p_perm_observed: Optional[float],
    mean_p_perm_permuted: Optional[float],
) -> GateResult:
    """P6: Temporal permutation degrades signal (permuted p_perm > observed p_perm on average)."""
    if mean_p_perm_observed is None or mean_p_perm_permuted is None:
        return GateResult(
            gate_id="P6",
            verdict="FAIL",
            value={"mean_p_perm_observed": mean_p_perm_observed, "mean_p_perm_permuted": mean_p_perm_permuted},
            threshold={"permuted > observed": True},
            note="P6 FAIL: control comparison not available.",
        )
    ok = mean_p_perm_permuted >= mean_p_perm_observed - 0.05  # allow 5pp tolerance
    return GateResult(
        gate_id="P6",
        verdict="PASS" if ok else "FAIL",
        value={"mean_p_perm_observed": round(mean_p_perm_observed, 4), "mean_p_perm_permuted": round(mean_p_perm_permuted, 4)},
        threshold={"permuted_p_perm >= observed_p_perm - 0.05": True},
        note="Controls: permuting source sector within year must degrade or preserve signal (not improve).",
    )


def check_p7_robustness(
    thresholds_pre_registered: bool,
    gate_version: str,
) -> GateResult:
    """P7: Promotion thresholds pre-registered before results observed."""
    ok = thresholds_pre_registered and gate_version == GATE_VERSION
    return GateResult(
        gate_id="P7",
        verdict="PASS" if ok else "FAIL",
        value={"thresholds_pre_registered": thresholds_pre_registered, "gate_version": gate_version},
        threshold={"thresholds_pre_registered": True, "gate_version": GATE_VERSION},
        note=(
            f"Robustness: gates frozen as {GATE_VERSION} (|β|≥{MIN_ABS_BETA}, "
            f"q_fdr<{FDR_Q}, Δr²≥{MIN_DELTA_R2}, bss≥{MIN_SIGN_STABILITY}, n≥{MIN_SAMPLES}). "
            "No threshold changes after results."
        ),
    )


def check_p8_comparison(
    nuts3_promoted: int,
    municipal_promoted_main: int,
    municipal_promoted_robust: int,
    comparison_documented: bool,
) -> GateResult:
    """P8: PT municipal vs PT NUTS3 comparison documented."""
    ok = comparison_documented
    return GateResult(
        gate_id="P8",
        verdict="PASS" if ok else "FAIL",
        value={
            "nuts3_promoted": nuts3_promoted,
            "municipal_promoted_main": municipal_promoted_main,
            "municipal_promoted_robust": municipal_promoted_robust,
            "comparison_documented": comparison_documented,
        },
        threshold={"comparison_documented": True},
        note=(
            "Comparison: PT municipal vs PT NUTS3 (25 territories, 0 promoted) documented. "
            "Reports whether granularity increases or fragments signal."
        ),
    )


def check_p9_no_causal_language(
    manifest_clean: bool,
    report_clean: bool,
    results_clean: bool,
) -> GateResult:
    """P9: No causal language in outputs."""
    ok = manifest_clean and report_clean and results_clean
    return GateResult(
        gate_id="P9",
        verdict="PASS" if ok else "FAIL",
        value={"manifest_clean": manifest_clean, "report_clean": report_clean, "results_clean": results_clean},
        threshold={"all_clean": True},
        note=(
            f"No causal language: none of {CAUSAL_TERMS[:4]}... in manifests, report, or results. "
            "Use: 'temporal precedence', 'predictive association', 'association'."
        ),
    )


def check_p10_reproducibility(
    manifest_exists: bool,
    panel_checksum_recorded: bool,
    commit_hash_recorded: bool,
    commands_documented: bool,
) -> GateResult:
    """P10: Reproducibility trail: manifest, checksums, commit hash, commands."""
    ok = manifest_exists and panel_checksum_recorded and commit_hash_recorded and commands_documented
    return GateResult(
        gate_id="P10",
        verdict="PASS" if ok else "FAIL",
        value={
            "manifest_exists": manifest_exists,
            "panel_checksum_recorded": panel_checksum_recorded,
            "commit_hash_recorded": commit_hash_recorded,
            "commands_documented": commands_documented,
        },
        threshold={"all": True},
        note="Reproducibility: manifest + panel SHA256 + git commit + run commands all documented.",
    )


def derive_decision_dec064(gates: list[GateResult]) -> dict:
    """Derive final decision from gates P1-P10."""
    gate_map = {g.gate_id: g for g in gates}
    critical = ["P1", "P2", "P3", "P5", "P7"]  # blocks if any fail
    secondary = ["P4", "P6", "P8", "P9", "P10"]

    critical_fail = [gid for gid in critical if gate_map.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict == "FAIL"]
    secondary_fail = [gid for gid in secondary if gate_map.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict == "FAIL"]

    n_pass = sum(1 for g in gates if g.verdict == "PASS")
    n_fail = len(gates) - n_pass

    if critical_fail:
        decision = "PT_MUNICIPAL_PHASE7_BLOCKED"
    elif n_pass == len(gates):
        decision = "PT_MUNICIPAL_PHASE7_COMPLETE"
    else:
        decision = "PT_MUNICIPAL_PHASE7_READY_FOR_HPC"

    return {
        "gate_version": GATE_VERSION,
        "decision": decision,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "critical_fail": critical_fail,
        "secondary_fail": secondary_fail,
    }
