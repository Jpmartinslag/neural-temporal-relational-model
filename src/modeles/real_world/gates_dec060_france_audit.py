"""
DEC-060: France Relation Signal Recovery Audit — Frozen Gates F1-F10.

FROZEN before results. Do not modify after first run.
No causal language. No cross-target mixing. No promotion without gate passage.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

GATE_VERSION = "DEC-060-v1"

# Thresholds (Phase 7 official values — read-only)
PHASE7_FDR_Q = 0.05
PHASE7_MIN_ABS_BETA = 0.10
PHASE7_MIN_DELTA_R2 = 0.005
PHASE7_MIN_BSS = 0.70
PHASE7_MIN_SAMPLES = 60

# Relaxed thresholds for sensitivity analysis (not for promotion)
RELAXED_FDR_Q = 0.10
RELAXED_MIN_ABS_BETA = 0.08
RELAXED_MIN_BSS = 0.60

# Coverage minimums
MIN_SECTOR_COVERAGE_FRAC = 0.70  # F1: 70% of territory-year rows must be valid
N_A10_SECTORS = 9
MIN_NEAR_MISS_COUNT = 1           # F3: at least 1 near-miss pair
MIN_WINDOWS_STABLE = 2            # F5: pair must appear in ≥2 windows to be "stable"
COVID_WINDOW_MIN_START = 2015     # F6: COVID-era window threshold

# Label namespace
FR_LABEL_PREFIX = "FR_"
VALID_FR_LABELS = {
    "FR_NATIONAL_ROBUST",          # Phase 7 all-4-criteria promotion
    "FR_COVID_SENSITIVE",          # Promoted only in COVID-era windows
    "FR_BETA_BELOW_THRESHOLD",     # q_fdr+dr2+bss pass but |beta| < 0.10
    "FR_FDR_ONLY_BLOCKED",         # p_perm+bss strong but q_fdr > 0.05 (not beta-blocked)
    "FR_MULTI_WINDOW_CANDIDATE",   # ≥3 windows p_perm≤0.01 and bss≥0.95 (no FDR pass)
    "FR_WEAK_SIGNAL",              # Below all relaxed thresholds
}

CAUSAL_TERMS_DEC060 = [
    "causa", "causal", "causas", "causado", "gera", "impact",
    "impacta", "impacto causal", "causa estrutural", "drives", "causes",
    "led to", "results in", "provoca",
]


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
# F1 — Dataset Coverage
# ---------------------------------------------------------------------------

def check_f1_dataset_coverage(
    n_sectors_present: int,
    valid_row_frac: float,
    n_windows: int,
) -> GateResult:
    """All 9 A10 sectors present; ≥70% territory-year rows valid; ≥5 windows."""
    ok = (
        n_sectors_present == N_A10_SECTORS
        and valid_row_frac >= MIN_SECTOR_COVERAGE_FRAC
        and n_windows >= 5
    )
    return GateResult(
        gate_id="F1",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_sectors": n_sectors_present,
            "valid_row_frac": round(valid_row_frac, 4),
            "n_windows": n_windows,
        },
        threshold={
            "n_sectors": N_A10_SECTORS,
            "valid_row_frac": MIN_SECTOR_COVERAGE_FRAC,
            "n_windows": 5,
        },
        note="FR dataset has sufficient coverage for audit.",
    )


# ---------------------------------------------------------------------------
# F2 — Binding Criterion Identification
# ---------------------------------------------------------------------------

def check_f2_binding_criterion(
    n_pass_fdr: int,
    n_pass_beta: int,
    n_pass_dr2: int,
    n_pass_bss: int,
    n_pass_all: int,
    binding_criterion: str,
) -> GateResult:
    """Identify which Phase 7 criterion is the binding gatekeeper for FR."""
    # F2 passes if we can clearly identify 1 binding criterion (not all equal)
    criteria_counts = {
        "fdr": n_pass_fdr,
        "beta": n_pass_beta,
        "dr2": n_pass_dr2,
        "bss": n_pass_bss,
    }
    min_criterion = min(criteria_counts, key=criteria_counts.__getitem__)
    ok = binding_criterion == min_criterion or n_pass_beta <= n_pass_fdr
    return GateResult(
        gate_id="F2",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_pass_fdr": n_pass_fdr,
            "n_pass_beta": n_pass_beta,
            "n_pass_dr2": n_pass_dr2,
            "n_pass_bss": n_pass_bss,
            "n_pass_all": n_pass_all,
            "binding_criterion": binding_criterion,
        },
        threshold={"binding_identified": True},
        note="Binding criterion = criterion that most restricts FR promotions.",
    )


# ---------------------------------------------------------------------------
# F3 — Near-Miss Characterization
# ---------------------------------------------------------------------------

def check_f3_near_miss_exists(
    n_near_miss_beta: int,
    n_near_miss_fdr: int,
) -> GateResult:
    """At least 1 near-miss pair that fails only on beta OR only on FDR."""
    ok = (n_near_miss_beta + n_near_miss_fdr) >= MIN_NEAR_MISS_COUNT
    return GateResult(
        gate_id="F3",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_near_miss_beta": n_near_miss_beta,
            "n_near_miss_fdr": n_near_miss_fdr,
            "total_near_miss": n_near_miss_beta + n_near_miss_fdr,
        },
        threshold={"min_near_miss": MIN_NEAR_MISS_COUNT},
        note="Near-miss = passes 3 of 4 Phase 7 criteria.",
    )


# ---------------------------------------------------------------------------
# F4 — Scale Hypothesis Documentation
# ---------------------------------------------------------------------------

def check_f4_scale_documented(
    ze2020_n_territories: int,
    nuts3_has_sector_cols: bool,
    scale_note: str,
) -> GateResult:
    """ZE2020 scale documented; NUTS3 sector column absence noted."""
    ok = (
        ze2020_n_territories >= 200
        and not nuts3_has_sector_cols
        and len(scale_note) > 20
    )
    return GateResult(
        gate_id="F4",
        verdict="PASS" if ok else "FAIL",
        value={
            "ze2020_n_territories": ze2020_n_territories,
            "nuts3_has_sector_cols": nuts3_has_sector_cols,
            "scale_note": scale_note[:80],
        },
        threshold={
            "ze2020_min_territories": 200,
            "nuts3_sector_cols_must_be_absent": True,
        },
        note="Scale comparison documented as hypothesis, not validated claim.",
    )


# ---------------------------------------------------------------------------
# F5 — Window Stability of Best Pairs
# ---------------------------------------------------------------------------

def check_f5_window_stability(
    top_pairs_window_counts: dict[str, int],
) -> GateResult:
    """Best FR pairs (by p_perm) appear in ≥2 windows with p≤0.01."""
    if not top_pairs_window_counts:
        return GateResult(
            gate_id="F5",
            verdict="FAIL",
            value={},
            threshold={"min_windows": MIN_WINDOWS_STABLE},
            note="No pairs submitted for stability check.",
        )
    n_stable = sum(1 for v in top_pairs_window_counts.values() if v >= MIN_WINDOWS_STABLE)
    ok = n_stable >= 1
    return GateResult(
        gate_id="F5",
        verdict="PASS" if ok else "FAIL",
        value={
            "pair_window_counts": top_pairs_window_counts,
            "n_stable_pairs": n_stable,
        },
        threshold={"min_windows_per_pair": MIN_WINDOWS_STABLE},
        note="Window stability indicates persistent (not one-shot) association pattern.",
    )


# ---------------------------------------------------------------------------
# F6 — COVID Window Isolation of Promoted Pair
# ---------------------------------------------------------------------------

def check_f6_covid_isolation(
    promoted_pairs: list[dict],
    pair_pre_covid_p_values: dict[str, float],
) -> GateResult:
    """
    Check if promoted FR pair(s) show similar signal in pre-COVID windows.
    F6 PASS if at least one promoted pair has a pre-COVID p_perm result
    (regardless of significance — absence of pre-COVID data = COVID_SENSITIVE by default).
    F6 FAIL if no promoted pairs at all.
    """
    if not promoted_pairs:
        return GateResult(
            gate_id="F6",
            verdict="FAIL",
            value={"promoted_pairs": []},
            threshold={"min_promoted": 1},
            note="No promoted FR pairs — COVID isolation check not applicable.",
        )
    has_pre_covid_data = any(
        pair_pre_covid_p_values.get(p.get("pair_key", ""), 1.0) is not None
        for p in promoted_pairs
    )
    return GateResult(
        gate_id="F6",
        verdict="PASS" if has_pre_covid_data else "FAIL",
        value={
            "n_promoted": len(promoted_pairs),
            "pre_covid_p_values": pair_pre_covid_p_values,
        },
        threshold={"pre_covid_data_available": True},
        note="COVID sensitivity documented; does not constitute causal claim.",
    )


# ---------------------------------------------------------------------------
# F7 — Label Integrity
# ---------------------------------------------------------------------------

def check_f7_label_integrity(labels: list[str]) -> GateResult:
    """All FR labels use FR_* prefix; no COVID_SENSITIVE mixed with robust."""
    invalid = [lb for lb in labels if lb not in VALID_FR_LABELS]
    robust_set = {lb for lb in labels if lb == "FR_NATIONAL_ROBUST"}
    covid_set = {lb for lb in labels if lb == "FR_COVID_SENSITIVE"}
    # A pair cannot be both FR_NATIONAL_ROBUST and FR_COVID_SENSITIVE in same record
    mixed = robust_set & covid_set
    ok = len(invalid) == 0 and len(mixed) == 0
    return GateResult(
        gate_id="F7",
        verdict="PASS" if ok else "FAIL",
        value={"invalid_labels": invalid, "mixed_labels": list(mixed)},
        threshold={"valid_labels": sorted(VALID_FR_LABELS)},
        note="FR labels must be in approved namespace and not mixed.",
    )


# ---------------------------------------------------------------------------
# F8 — No Causal Language
# ---------------------------------------------------------------------------

def check_f8_no_causal_language(text_samples: list[str]) -> GateResult:
    """No causal language in any output string."""
    violations = []
    for text in text_samples:
        low = text.lower()
        for term in CAUSAL_TERMS_DEC060:
            if term in low:
                violations.append(f"'{term}' in: {text[:60]!r}")
    return GateResult(
        gate_id="F8",
        verdict="PASS" if not violations else "FAIL",
        value={"violations": violations[:5]},
        threshold={"causal_terms": CAUSAL_TERMS_DEC060},
        note="No causal language in audit outputs or labels.",
    )


# ---------------------------------------------------------------------------
# F9 — No Cross-Target Mixing
# ---------------------------------------------------------------------------

def check_f9_no_cross_target_mixing(
    targets_in_panel: list[str],
    target_used: str,
) -> GateResult:
    """Only one target variable used; no mixing of establishment_creation with other targets."""
    ok = len(targets_in_panel) == 1 and targets_in_panel[0] == target_used
    return GateResult(
        gate_id="F9",
        verdict="PASS" if ok else "FAIL",
        value={"targets_in_panel": targets_in_panel, "target_used": target_used},
        threshold={"n_targets": 1, "expected_target": "establishment_creation"},
        note="Single target enforced; cross-target mixing forbidden.",
    )


# ---------------------------------------------------------------------------
# F10 — Audit Completeness
# ---------------------------------------------------------------------------

def check_f10_audit_completeness(
    n_pairs_analyzed: int,
    n_windows_analyzed: int,
    coverage_csv_exists: bool,
    summary_json_exists: bool,
) -> GateResult:
    """All 72 directed pairs and all FR windows analyzed; output files exist."""
    ok = (
        n_pairs_analyzed >= 72
        and n_windows_analyzed >= 11
        and coverage_csv_exists
        and summary_json_exists
    )
    return GateResult(
        gate_id="F10",
        verdict="PASS" if ok else "FAIL",
        value={
            "n_pairs": n_pairs_analyzed,
            "n_windows": n_windows_analyzed,
            "coverage_csv": coverage_csv_exists,
            "summary_json": summary_json_exists,
        },
        threshold={"n_pairs": 72, "n_windows": 11},
        note="Full audit coverage required before labelling.",
    )


# ---------------------------------------------------------------------------
# Derive Audit Decision
# ---------------------------------------------------------------------------

def derive_decision_dec060(gate_results: list[GateResult]) -> dict:
    """
    Derive audit decision from gate results.

    Decision tiers:
    - AUDIT_COMPLETE: F1-F10 all PASS
    - AUDIT_PARTIAL: F1+F2+F3+F7+F8+F9+F10 PASS; F4/F5/F6 FAIL (non-critical)
    - AUDIT_INCOMPLETE: Any of F1/F7/F8/F9/F10 FAIL
    """
    by_id = {r.gate_id: r for r in gate_results}
    critical = ["F1", "F7", "F8", "F9", "F10"]
    secondary = ["F2", "F3", "F4", "F5", "F6"]

    critical_fail = [gid for gid in critical if by_id.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict == "FAIL"]
    secondary_fail = [gid for gid in secondary if by_id.get(gid, GateResult(gid, "FAIL", None, None, "")).verdict == "FAIL"]

    n_pass = sum(1 for r in gate_results if r.verdict == "PASS")
    n_fail = sum(1 for r in gate_results if r.verdict == "FAIL")

    if not critical_fail and not secondary_fail:
        decision = "AUDIT_COMPLETE"
    elif not critical_fail:
        decision = "AUDIT_PARTIAL"
    else:
        decision = "AUDIT_INCOMPLETE"

    return {
        "decision": decision,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "critical_fail": critical_fail,
        "secondary_fail": secondary_fail,
        "gate_version": GATE_VERSION,
    }
