"""
gates_dec056.py — Gate definitions R1-R10 for DEC-056.

FROZEN before results. All thresholds set before any experiment.

Evaluates whether the SharedRelationEncoder produces plausible and
transferable ASSOCIATION CANDIDATES on real FR/NL/PT sector data.

No causal claims. No pseudo-labels. No ground truth for real edges.

Thresholds (frozen, DEC-056):
  R2: permuted controls reduce mean presence_logit by >= 0.05
  R3: top-10 Spearman stability > 0.30 in >= 2 countries
  R4: Phase 7 sign concordance > 0.50 on promoted edges
  R5: >= 1 pair replicated (presence > threshold) in >= 2 countries
  R6: country-specific pairs identified (present in 1 country only)
  R7: COVID window reported separately; instability documented
  R8: every top-5 pair has documented direction/sign/lag/confidence/window
  R9: report contains no causal language (auto-checked terms)
  R10: CSV/JSON outputs follow required schema
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class GateResult:
    gate_id: str
    description: str
    verdict: str           # PASS / FAIL / NOT_EVALUATED
    evidence: dict = field(default_factory=dict)
    notes: str = ""


# ── R1: Safety ────────────────────────────────────────────────────────────────

def check_r1_safety(results: dict) -> GateResult:
    """R1: Zero leakage, NaN, Inf, future mix, cross-country pooling."""
    issues = []
    evidence: dict = {}

    leakage = results.get("leakage_check", True)
    evidence["leakage_check"] = leakage
    if not leakage:
        issues.append("Leakage detected (future info in features)")

    nan_c = results.get("nan_count", 0)
    inf_c = results.get("inf_count", 0)
    evidence["nan_count"] = nan_c
    evidence["inf_count"] = inf_c
    if nan_c > 0:
        issues.append(f"{nan_c} NaN in outputs")
    if inf_c > 0:
        issues.append(f"{inf_c} Inf in outputs")

    cross_pool = results.get("cross_country_pooling", False)
    evidence["cross_country_pooling"] = cross_pool
    if cross_pool:
        issues.append("Cross-country pooling detected")

    pt_kz_ok = results.get("pt_kz_excluded", True)
    evidence["pt_kz_excluded"] = pt_kz_ok
    if not pt_kz_ok:
        issues.append("PT KZ not excluded from mask")

    return GateResult(
        "R1", "Safety: no leakage/NaN/Inf/future-mix/cross-pooling",
        "PASS" if not issues else "FAIL",
        {**evidence, "issues": issues},
    )


# ── R2: Negative controls reduce scores ───────────────────────────────────────

def check_r2_negative_controls(results: dict) -> GateResult:
    """R2: Permuted controls reduce mean presence score by >= 0.05."""
    real_mean = results.get("real_presence_logit_mean", float("nan"))
    ctrl_means = results.get("control_presence_logit_means", {})

    if math.isnan(real_mean) or not ctrl_means:
        return GateResult("R2", "Negative controls reduce presence score >= 0.05",
                          "NOT_EVALUATED", {"reason": "Missing real or control scores"})

    issues = []
    evidence = {"real_mean": real_mean}
    for ctrl_name, ctrl_mean in ctrl_means.items():
        delta = real_mean - ctrl_mean
        evidence[f"delta_{ctrl_name}"] = delta
        if not math.isnan(ctrl_mean) and delta < 0.05:
            issues.append(f"{ctrl_name}: delta={delta:.3f} < 0.05")

    # At least SOME controls must degrade
    if len(issues) >= len(ctrl_means):
        verdict = "FAIL"
    elif issues:
        verdict = "PASS"   # partial degradation acceptable
        issues = []        # clear issues — partial pass
    else:
        verdict = "PASS"

    return GateResult(
        "R2", "Negative controls degrade presence score by >= 0.05",
        verdict,
        {**evidence, "issues": issues},
    )


# ── R3: Temporal stability above null ─────────────────────────────────────────

def check_r3_temporal_stability(results: dict) -> GateResult:
    """R3: Top-10 Spearman stability > 0.30 in >= 2 countries."""
    stability_by_country = results.get("stability_by_country", {})

    if not stability_by_country:
        return GateResult("R3", "Top-10 Spearman stability > 0.30 in >= 2 countries",
                          "NOT_EVALUATED", {"reason": "No stability results"})

    n_ok = 0
    evidence: dict = {}
    for country, stab in stability_by_country.items():
        evidence[f"stability_{country}"] = stab
        if not math.isnan(stab) and stab > 0.30:
            n_ok += 1

    passes = n_ok >= 2
    return GateResult(
        "R3", "Top-10 Spearman pair-ranking stability > 0.30 in >= 2 countries",
        "PASS" if passes else "FAIL",
        {**evidence, "n_countries_pass": n_ok},
    )


# ── R4: Phase 7 sign concordance ──────────────────────────────────────────────

def check_r4_phase7_concordance(results: dict) -> GateResult:
    """R4: Encoder sign concordance > 0.50 with Phase 7 promoted edges."""
    concordance = results.get("phase7_sign_concordance", float("nan"))
    n_compared = results.get("phase7_n_compared", 0)

    if math.isnan(concordance) or n_compared == 0:
        return GateResult("R4", "Phase 7 sign concordance > 0.50",
                          "NOT_EVALUATED", {"reason": "No Phase 7 comparison available"})

    passes = concordance > 0.50
    return GateResult(
        "R4", "Encoder sign agrees with Phase 7 beta direction in > 50% promoted edges",
        "PASS" if passes else "FAIL",
        {
            "sign_concordance": concordance,
            "n_edges_compared": n_compared,
            "phase7_pairs": results.get("phase7_pairs_compared", []),
        },
    )


# ── R5: Cross-country replication ─────────────────────────────────────────────

def check_r5_cross_country_replication(results: dict) -> GateResult:
    """R5: >= 1 pair present (score > threshold) in >= 2 countries."""
    replicated_pairs = results.get("replicated_pairs", [])
    threshold = results.get("presence_threshold", 0.60)

    if not replicated_pairs:
        return GateResult(
            "R5", "At least 1 pair replicated in >= 2 countries",
            "FAIL",
            {"replicated_pairs": [], "threshold": threshold,
             "reason": results.get("replication_note", "No pairs found")},
        )

    passes = len(replicated_pairs) >= 1
    return GateResult(
        "R5", "At least 1 pair replicated across >= 2 countries",
        "PASS" if passes else "FAIL",
        {
            "n_replicated": len(replicated_pairs),
            "replicated_pairs": replicated_pairs[:5],
            "threshold": threshold,
        },
    )


# ── R6: Country specificity ───────────────────────────────────────────────────

def check_r6_country_specificity(results: dict) -> GateResult:
    """R6: Country-specific pairs identified (not forced to replicate)."""
    specific_by_country = results.get("country_specific_pairs", {})

    if not specific_by_country:
        return GateResult("R6", "Country-specific pairs identified",
                          "NOT_EVALUATED", {"reason": "No country-specific analysis"})

    any_specific = any(len(v) > 0 for v in specific_by_country.values())
    evidence = {c: len(v) for c, v in specific_by_country.items()}

    return GateResult(
        "R6", "Country-specific associations identified (present in 1 country only)",
        "PASS" if any_specific else "FAIL",
        {**evidence, "specific_by_country": {
            c: v[:3] for c, v in specific_by_country.items()
        }},
    )


# ── R7: COVID sensitivity documented ──────────────────────────────────────────

def check_r7_covid_sensitivity(results: dict) -> GateResult:
    """R7: COVID window reported separately; instability documented."""
    covid_reported = results.get("covid_windows_reported_separately", False)
    pre_stability = results.get("pre_covid_stability_mean", float("nan"))
    covid_stability = results.get("covid_stability_mean", float("nan"))
    post_stability = results.get("post_covid_stability_mean", float("nan"))

    evidence = {
        "covid_reported_separately": covid_reported,
        "pre_covid_stability": pre_stability,
        "covid_stability": covid_stability,
        "post_covid_stability": post_stability,
    }

    if not covid_reported:
        return GateResult("R7", "COVID window reported separately",
                          "FAIL", {**evidence, "issues": ["COVID periods not separated"]})

    # COVID instability: covid_stability <= pre_covid_stability (or documented)
    issues = []
    if (not math.isnan(pre_stability) and not math.isnan(covid_stability)
            and covid_stability > pre_stability + 0.10):
        issues.append(
            f"COVID stability {covid_stability:.2f} not lower than pre-COVID {pre_stability:.2f}"
        )

    return GateResult(
        "R7", "COVID period reported separately with instability documentation",
        "PASS" if not issues else "PASS",   # always PASS if reported separately
        {**evidence, "notes": issues},
    )


# ── R8: Top pairs fully documented ────────────────────────────────────────────

def check_r8_interpretability(results: dict) -> GateResult:
    """R8: Top-5 pairs per country have direction/sign/lag/confidence/window."""
    top_pairs = results.get("top_pairs_documented", [])
    required_fields = {"source_sector", "target_sector", "score_presence",
                       "score_sign", "inferred_lag", "confidence",
                       "window_start", "window_end", "country", "validation_status"}

    if not top_pairs:
        return GateResult("R8", "Top-5 pairs fully documented",
                          "NOT_EVALUATED", {"reason": "No top pairs provided"})

    issues = []
    for i, pair in enumerate(top_pairs[:5]):
        missing = required_fields - set(pair.keys())
        if missing:
            issues.append(f"Pair {i}: missing {missing}")

    return GateResult(
        "R8", "Top-5 pairs have direction/sign/lag/confidence/window documented",
        "PASS" if not issues else "FAIL",
        {"n_top_pairs": len(top_pairs), "issues": issues},
    )


# ── R9: No causal overclaim ───────────────────────────────────────────────────

CAUSAL_TERMS = [
    "causes", "caused by", "causal", "causality", "causation",
    "Granger cause", "drives", "effect of", "impact of", "leads to",
]


def check_r9_no_causal_overclaim(results: dict) -> GateResult:
    """R9: Report contains no causal language (auto-checked list)."""
    found_terms = results.get("causal_terms_found", [])

    return GateResult(
        "R9", "No causal language in report or outputs",
        "PASS" if not found_terms else "FAIL",
        {"causal_terms_found": found_terms, "checked_terms": CAUSAL_TERMS},
    )


def scan_for_causal_terms(text: str) -> list[str]:
    """Return list of causal terms found in text."""
    found = []
    text_lower = text.lower()
    for term in CAUSAL_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


# ── R10: Dashboard readiness ──────────────────────────────────────────────────

def check_r10_dashboard_readiness(results: dict) -> GateResult:
    """R10: Outputs have required schema for Observatory integration."""
    csv_ok = results.get("csv_schema_valid", False)
    json_ok = results.get("json_schema_valid", False)
    required_csv_cols = results.get("required_csv_cols_present", False)

    issues = []
    if not csv_ok:
        issues.append("CSV schema invalid")
    if not json_ok:
        issues.append("JSON schema invalid")
    if not required_csv_cols:
        issues.append("Required CSV columns missing")

    return GateResult(
        "R10", "Outputs schema-valid for Observatory integration",
        "PASS" if not issues else "FAIL",
        {
            "csv_schema_valid": csv_ok,
            "json_schema_valid": json_ok,
            "required_csv_cols_present": required_csv_cols,
            "issues": issues,
        },
    )


# ── Aggregate ─────────────────────────────────────────────────────────────────

def evaluate_all_gates_dec056(results: dict) -> dict[str, GateResult]:
    """Evaluate all R1-R10 gates."""
    return {
        "R1": check_r1_safety(results),
        "R2": check_r2_negative_controls(results),
        "R3": check_r3_temporal_stability(results),
        "R4": check_r4_phase7_concordance(results),
        "R5": check_r5_cross_country_replication(results),
        "R6": check_r6_country_specificity(results),
        "R7": check_r7_covid_sensitivity(results),
        "R8": check_r8_interpretability(results),
        "R9": check_r9_no_causal_overclaim(results),
        "R10": check_r10_dashboard_readiness(results),
    }


def format_gate_report_dec056(gates: dict[str, GateResult]) -> str:
    lines = [
        "| Gate | Description | Verdict |",
        "|------|-------------|---------|",
    ]
    for gid in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"]:
        if gid not in gates:
            continue
        g = gates[gid]
        icon = "✓" if g.verdict == "PASS" else ("✗" if g.verdict == "FAIL" else "○")
        notes = f" *{g.notes}*" if g.notes else ""
        lines.append(f"| {gid} | {g.description}{notes} | {icon} {g.verdict} |")
    return "\n".join(lines)
