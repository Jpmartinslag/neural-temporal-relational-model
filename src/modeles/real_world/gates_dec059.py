"""
gates_dec059.py — Gate definitions M1-M10 for DEC-059 (frozen before results).

DEC-059: Rigorous revalidation of weak-label tuning from DEC-058.

FROZEN: All thresholds set before any experiment is run.
DEC-058 decision corrected to REAL_WEAK_LABEL_TUNING_PARTIAL because
W2 failed (country-shuffled C2=0.688 >= V1=0.667).

Key changes vs DEC-058:
  - M2 requires V1 to beat ALL controls C1-C6, not just C1/C2.
  - M3 requires multi-window stability (n_windows >= 3, sign_consistency >= 0.60).
  - M4 requires INSUFFICIENT_EVIDENCE to be used.
  - M5 marks LOW_EVIDENCE folds separately; they cannot drive claims.
  - Decision ceiling is PARTIAL unless M2 passes.

Scientific scope: association/precedence only. No causal claims.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class GateResult:
    gate_id: str
    description: str
    verdict: str          # PASS / FAIL / NOT_EVALUATED / LOW_EVIDENCE
    evidence: dict = field(default_factory=dict)
    notes: str = ""


# ── Thresholds (frozen) ────────────────────────────────────────────────────────
MIN_WINDOWS = 3              # M3: min windows for a stable relation
SIGN_CONSISTENCY_THRESHOLD = 0.60  # M3: fraction of windows with same sign
CONTROL_MARGIN = 0.05        # M2: V1 must exceed each control by this margin
LOW_EVIDENCE_LABEL_THRESHOLD = 3   # M5: LOCO fold with < N labels = LOW_EVIDENCE
ABSTENTION_MIN_RATE = 0.10   # M4: at least 10% of pairs must be INSUFFICIENT_EVIDENCE

CAUSAL_TERMS_DEC059 = [
    "causes", "caused by", "causal", "causality", "causation",
    "Granger cause", "drives", "effect of", "impact of", "leads to",
    "structural effect", "structural cause",
    "impacta", "impacto causal", "causa estrutural",
]


def scan_causal_terms_dec059(text: str) -> list[str]:
    text_lower = text.lower()
    return [t for t in CAUSAL_TERMS_DEC059 if t.lower() in text_lower]


# ── M1: Safety ────────────────────────────────────────────────────────────────

def check_m1_safety(results: dict) -> GateResult:
    """M1: No NaN/Inf, no leakage, schema valid, PT KZ excluded."""
    issues = []
    ev: dict = {
        "nan_count": results.get("nan_count", 0),
        "inf_count": results.get("inf_count", 0),
        "leakage_check": results.get("leakage_check", True),
        "schema_valid": results.get("schema_valid", True),
        "pt_kz_excluded": results.get("pt_kz_excluded", True),
    }
    if ev["nan_count"] > 0:
        issues.append(f"NaN in outputs: {ev['nan_count']}")
    if ev["inf_count"] > 0:
        issues.append(f"Inf in outputs: {ev['inf_count']}")
    if not ev["leakage_check"]:
        issues.append("Leakage detected")
    if not ev["schema_valid"]:
        issues.append("Schema broken")
    if not ev["pt_kz_excluded"]:
        issues.append("PT KZ not excluded")
    return GateResult("M1", "Safety: no NaN/Inf/leakage/schema-break/PT-KZ",
                      "PASS" if not issues else "FAIL",
                      {**ev, "issues": issues})


# ── M2: Control Dominance ─────────────────────────────────────────────────────

def check_m2_control_dominance(results: dict) -> GateResult:
    """
    M2: V1 (real weak labels) must exceed ALL controls C1-C6 by >= CONTROL_MARGIN
    in mean LOCO sign concordance.
    If any control ties or exceeds V1, gate FAILS.
    """
    v1 = results.get("v1_sign_concordance_mean", float("nan"))

    if math.isnan(v1):
        return GateResult("M2", f"V1 must beat all controls C1-C6 by >= {CONTROL_MARGIN}",
                          "NOT_EVALUATED", {"reason": "V1 not computed"})

    controls = {
        "C1_permuted_labels": results.get("c1_sign_concordance_mean", float("nan")),
        "C2_country_shuffled": results.get("c2_sign_concordance_mean", float("nan")),
        "C3_sector_shuffled": results.get("c3_sign_concordance_mean", float("nan")),
        "C4_sign_flipped": results.get("c4_sign_concordance_mean", float("nan")),
        "C5_window_shuffled": results.get("c5_sign_concordance_mean", float("nan")),
        "C6_random_labels": results.get("c6_sign_concordance_mean", float("nan")),
    }
    ev = {"v1": v1, "controls": controls, "required_margin": CONTROL_MARGIN}
    failures = []
    for ctrl_name, ctrl_val in controls.items():
        if math.isnan(ctrl_val):
            continue
        gap = v1 - ctrl_val
        if gap < CONTROL_MARGIN:
            failures.append(f"V1({v1:.3f}) - {ctrl_name}({ctrl_val:.3f}) = {gap:.3f} < {CONTROL_MARGIN}")

    ev["failures"] = failures
    # Decision ceiling rule: if M2 fails, maximum outcome = REAL_WEAK_LABEL_TUNING_PARTIAL
    return GateResult(
        "M2", f"V1 > all controls C1-C6 by >= {CONTROL_MARGIN} (ceiling: PARTIAL if fails)",
        "PASS" if not failures else "FAIL", ev,
        notes="If FAIL: decision ceiling = REAL_WEAK_LABEL_TUNING_PARTIAL"
    )


# ── M3: Multi-window Stability ─────────────────────────────────────────────────

def check_m3_multiwindow_stability(results: dict) -> GateResult:
    """
    M3: Promoted relations must have n_windows >= MIN_WINDOWS AND
    sign_consistency >= SIGN_CONSISTENCY_THRESHOLD.
    Relations with insufficient windows must not be promoted.
    """
    n_stable = results.get("n_stable_relations", 0)   # passed n_windows and sign_consistency
    n_promoted = results.get("n_replicated_associations", 0)
    n_unstable_promoted = results.get("n_unstable_promoted", 0)  # promoted but unstable

    ev = {
        "n_stable_relations": n_stable,
        "n_replicated_associations": n_promoted,
        "n_unstable_promoted": n_unstable_promoted,
        "min_windows": MIN_WINDOWS,
        "sign_consistency_threshold": SIGN_CONSISTENCY_THRESHOLD,
    }
    issues = []
    if n_unstable_promoted > 0:
        issues.append(f"{n_unstable_promoted} promoted relations have unstable multi-window scores")
    if n_promoted > 0 and n_stable == 0:
        issues.append("No stable multi-window relations found despite promoted associations")

    return GateResult(
        "M3", f"Promoted relations: n_windows >= {MIN_WINDOWS} AND sign_consistency >= {SIGN_CONSISTENCY_THRESHOLD}",
        "PASS" if not issues else "FAIL", ev
    )


# ── M4: Abstention ────────────────────────────────────────────────────────────

def check_m4_abstention(results: dict) -> GateResult:
    """
    M4: INSUFFICIENT_EVIDENCE must be used for genuinely uncertain pairs.
    Minimum abstention rate: ABSTENTION_MIN_RATE of all evaluated pairs.
    """
    n_abstained = results.get("n_insufficient_evidence", 0)
    n_total = results.get("n_total_pairs_evaluated", 0)

    if n_total == 0:
        return GateResult("M4", "INSUFFICIENT_EVIDENCE used for uncertain pairs",
                          "NOT_EVALUATED", {"reason": "No pairs evaluated"})

    rate = n_abstained / n_total
    ev = {"n_abstained": n_abstained, "n_total": n_total, "rate": round(rate, 3),
          "min_required_rate": ABSTENTION_MIN_RATE}

    passes = n_abstained > 0 and rate >= ABSTENTION_MIN_RATE
    return GateResult(
        "M4", f"INSUFFICIENT_EVIDENCE used; abstention rate >= {ABSTENTION_MIN_RATE:.0%}",
        "PASS" if passes else "FAIL", ev
    )


# ── M5: LOCO Honesty ──────────────────────────────────────────────────────────

def check_m5_loco_honesty(results: dict) -> GateResult:
    """
    M5: LOCO results reported per held-out country.
    Folds with < LOW_EVIDENCE_LABEL_THRESHOLD labels are marked LOW_EVIDENCE
    and excluded from strong claims.
    """
    loco_by_country = results.get("loco_by_country", {})
    if not loco_by_country:
        return GateResult("M5", "LOCO results reported per fold; LOW_EVIDENCE folds marked",
                          "NOT_EVALUATED", {"reason": "No LOCO results"})

    issues = []
    ev = {}
    for country, fold_result in loco_by_country.items():
        n_labels = fold_result.get("n_labels", 0)
        sign_conc = fold_result.get("sign_concordance", float("nan"))
        low_evidence = n_labels < LOW_EVIDENCE_LABEL_THRESHOLD
        ev[country] = {
            "n_labels": n_labels,
            "sign_concordance": sign_conc,
            "low_evidence": low_evidence,
        }
        if low_evidence:
            fold_result["low_evidence"] = True  # mark in-place
        if math.isnan(sign_conc) and not low_evidence:
            issues.append(f"LOCO fold {country}: no sign concordance computed despite {n_labels} labels")

    # Check if all folds are low-evidence (would invalidate multi-country claim)
    all_low = all(v.get("low_evidence", False) for v in ev.values())
    if all_low and len(ev) > 0:
        issues.append("All LOCO folds are LOW_EVIDENCE — no strong multi-country claim possible")

    return GateResult(
        "M5", "Per-fold LOCO honesty; LOW_EVIDENCE folds excluded from strong claims",
        "PASS" if not issues else "FAIL", ev
    )


# ── M6: COVID Isolation ───────────────────────────────────────────────────────

def check_m6_covid_isolation(results: dict) -> GateResult:
    """M6: COVID_SENSITIVE pairs must not appear as REPLICATED or ROBUST."""
    covid_promoted = results.get("covid_sensitive_promoted_as_robust", [])
    covid_in_replicated = results.get("covid_in_replicated", [])
    issues = []
    if covid_promoted:
        issues.append(f"COVID_SENSITIVE promoted as ROBUST: {covid_promoted}")
    if covid_in_replicated:
        issues.append(f"COVID_SENSITIVE in REPLICATED: {covid_in_replicated}")
    return GateResult(
        "M6", "COVID_SENSITIVE not promoted to REPLICATED or ROBUST",
        "PASS" if not issues else "FAIL",
        {"covid_promoted": covid_promoted, "covid_in_replicated": covid_in_replicated}
    )


# ── M7: Replication ───────────────────────────────────────────────────────────

def check_m7_replication(results: dict) -> GateResult:
    """
    M7: At least one relation must survive all controls and be REPLICATED
    (>= 2 countries) with multi-window stability.
    Relations that replicate but fail M3 are not counted here.
    """
    n_stable_replicated = results.get("n_stable_replicated", 0)
    stable_replicated_pairs = results.get("stable_replicated_pairs", [])
    ev = {"n_stable_replicated": n_stable_replicated, "pairs": stable_replicated_pairs[:5]}

    return GateResult(
        "M7", ">=1 REPLICATED relation with multi-window stability survives controls",
        "PASS" if n_stable_replicated >= 1 else "FAIL", ev
    )


# ── M8: Country Specific ──────────────────────────────────────────────────────

def check_m8_country_specific(results: dict) -> GateResult:
    """
    M8: Country-specific relations are identified and reported separately.
    They must NOT be counted as European-level replication.
    This gate PASSES as long as the classification is honest.
    """
    n_country_specific = results.get("n_country_specific", 0)
    country_specific_in_replicated = results.get("country_specific_in_replicated", False)

    ev = {"n_country_specific": n_country_specific,
          "country_specific_in_replicated": country_specific_in_replicated}
    issues = []
    if country_specific_in_replicated:
        issues.append("Country-specific relations incorrectly counted as cross-country replication")
    return GateResult(
        "M8", "Country-specific relations identified and NOT counted as European replication",
        "PASS" if not issues else "FAIL", ev
    )


# ── M9: Determinism ───────────────────────────────────────────────────────────

def check_m9_determinism(results: dict) -> GateResult:
    """M9: Same seed produces same outputs."""
    hash_match = results.get("determinism_hash_match", None)
    if hash_match is None:
        return GateResult("M9", "Same seed produces same outputs",
                          "NOT_EVALUATED", {"reason": "Not checked"})
    return GateResult("M9", "Same seed produces identical outputs",
                      "PASS" if hash_match else "FAIL", {"hash_match": hash_match})


# ── M10: No Causal Claims ─────────────────────────────────────────────────────

def check_m10_no_causal_claims(results: dict) -> GateResult:
    """M10: No causal structural language in outputs or report."""
    found = results.get("causal_terms_found", [])
    return GateResult(
        "M10", "No causal language in outputs, report, or decision text",
        "PASS" if not found else "FAIL",
        {"terms_found": found, "checked_list": CAUSAL_TERMS_DEC059}
    )


# ── Aggregate ─────────────────────────────────────────────────────────────────

def evaluate_all_gates_dec059(results: dict) -> dict[str, GateResult]:
    return {
        "M1": check_m1_safety(results),
        "M2": check_m2_control_dominance(results),
        "M3": check_m3_multiwindow_stability(results),
        "M4": check_m4_abstention(results),
        "M5": check_m5_loco_honesty(results),
        "M6": check_m6_covid_isolation(results),
        "M7": check_m7_replication(results),
        "M8": check_m8_country_specific(results),
        "M9": check_m9_determinism(results),
        "M10": check_m10_no_causal_claims(results),
    }


def format_gate_report_dec059(gates: dict[str, GateResult]) -> str:
    lines = [
        "| Gate | Description | Verdict |",
        "|------|-------------|---------|",
    ]
    for gid in [f"M{i}" for i in range(1, 11)]:
        if gid not in gates:
            continue
        g = gates[gid]
        icon = {"PASS": "✓", "FAIL": "✗", "NOT_EVALUATED": "○",
                "LOW_EVIDENCE": "△"}.get(g.verdict, "?")
        lines.append(f"| {gid} | {g.description} | {icon} {g.verdict} |")
    return "\n".join(lines)


def derive_decision_dec059(gates: dict[str, GateResult]) -> str:
    """
    Decision hierarchy (strict):
    - If M1 FAIL: REAL_RELATION_LEARNING_NOT_SUPPORTED
    - If M2 FAIL: maximum = REAL_WEAK_LABEL_TUNING_PARTIAL
    - If M2 PASS and M3 PASS and M7 PASS: REAL_WEAK_LABEL_TUNING_SUPPORTED
    - If M2 PASS and (M7 FAIL or M3 FAIL): COUNTRY_SPECIFIC_ONLY or PARTIAL
    - If M6 FAIL: cannot promote any relation
    """
    m1 = gates["M1"].verdict
    m2 = gates["M2"].verdict
    m3 = gates["M3"].verdict
    m4 = gates["M4"].verdict
    m6 = gates["M6"].verdict
    m7 = gates["M7"].verdict

    if m1 == "FAIL":
        return "REAL_RELATION_LEARNING_NOT_SUPPORTED"

    if m6 == "FAIL":
        return "REAL_RELATION_LEARNING_NOT_SUPPORTED"

    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")

    if m2 == "FAIL":
        # Controls not clearly degraded; cannot claim full support
        if m7 == "PASS":
            return "REAL_WEAK_LABEL_TUNING_PARTIAL"
        else:
            return "WEAK_LABELS_TOO_NOISY"

    # M2 PASS
    if m3 == "PASS" and m7 == "PASS":
        return "REAL_WEAK_LABEL_TUNING_SUPPORTED"

    if m7 == "FAIL":
        # No stable replicated relations
        n_cs = gates["M8"].evidence.get("n_country_specific", 0)
        if n_cs > 0:
            return "COUNTRY_SPECIFIC_ONLY"
        return "WEAK_LABELS_TOO_NOISY"

    # m3 FAIL (unstable windows) but m7 PASS
    return "REAL_WEAK_LABEL_TUNING_PARTIAL"
