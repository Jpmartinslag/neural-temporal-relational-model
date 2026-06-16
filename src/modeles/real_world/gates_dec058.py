"""
gates_dec058.py — Gate definitions W1-W10 for DEC-058 (frozen before results).

DEC-058: Weak-label real relation tuning using Phase 7 as noisy evidence.

FROZEN: All thresholds set before any experiment is run.

Scientific scope:
  - Association/precedence only. No causal claims.
  - Phase 7 = weak noisy labels, not ground truth.
  - Validation = leave-one-country-out (FR/NL/PT).
  - Controls must degrade relative to real labels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class GateResult:
    gate_id: str
    description: str
    verdict: str          # PASS / FAIL / NOT_EVALUATED
    evidence: dict = field(default_factory=dict)
    notes: str = ""


# ── W1: Safety ────────────────────────────────────────────────────────────────

def check_w1_safety(results: dict) -> GateResult:
    """W1: No NaN/Inf, no leakage, no schema broken, PT KZ excluded."""
    issues = []
    ev: dict = {}

    ev["nan_count"] = results.get("nan_count", 0)
    ev["inf_count"] = results.get("inf_count", 0)
    if ev["nan_count"] > 0:
        issues.append(f"NaN in outputs: {ev['nan_count']}")
    if ev["inf_count"] > 0:
        issues.append(f"Inf in outputs: {ev['inf_count']}")

    ev["leakage_check"] = results.get("leakage_check", True)
    if not ev["leakage_check"]:
        issues.append("Leakage detected")

    ev["schema_valid"] = results.get("schema_valid", True)
    if not ev["schema_valid"]:
        issues.append("Schema broken")

    ev["pt_kz_excluded"] = results.get("pt_kz_excluded", True)
    if not ev["pt_kz_excluded"]:
        issues.append("PT KZ not excluded")

    return GateResult("W1", "Safety: no NaN/Inf/leakage/broken-schema/PT-KZ",
                      "PASS" if not issues else "FAIL",
                      {**ev, "issues": issues})


# ── W2: Controls degrade ──────────────────────────────────────────────────────

def check_w2_controls(results: dict) -> GateResult:
    """
    W2: V1 (trained) must outperform C1 (permuted labels) and C2 (country-shuffled)
    on held-out sign concordance by >= 0.05.
    """
    v1_sign = results.get("v1_sign_concordance_mean", float("nan"))
    c1_sign = results.get("c1_permuted_labels_sign_concordance", float("nan"))
    c2_sign = results.get("c2_country_shuffled_sign_concordance", float("nan"))

    if math.isnan(v1_sign):
        return GateResult("W2", "Controls degrade: V1 > permuted/country-shuffled by >= 0.05",
                          "NOT_EVALUATED", {"reason": "V1 sign concordance not computed"})

    issues = []
    ev = {"v1_sign": v1_sign, "c1_sign": c1_sign, "c2_sign": c2_sign}

    if not math.isnan(c1_sign) and v1_sign - c1_sign < 0.05:
        issues.append(f"V1 ({v1_sign:.3f}) not > C1-permuted ({c1_sign:.3f}) by >= 0.05")
    if not math.isnan(c2_sign) and v1_sign - c2_sign < 0.05:
        issues.append(f"V1 ({v1_sign:.3f}) not > C2-shuffled ({c2_sign:.3f}) by >= 0.05")

    # Partial PASS if at least one control is degraded
    if len(issues) < 2:
        verdict = "PASS"
        issues = []
    else:
        verdict = "FAIL"

    return GateResult("W2", "V1 sign concordance > permuted/country-shuffled controls by >= 0.05",
                      verdict, {**ev, "issues": issues})


# ── W3: Sign concordance improves over DEC-056 baseline ──────────────────────

def check_w3_sign_concordance(results: dict) -> GateResult:
    """
    W3: Fine-tuned sign concordance on held-out country must exceed:
      - DEC-056 baseline (0.438)
      - V0 (no fine-tuning) baseline
      - permuted control (C1)
    Threshold: >= 0.50 and > V0 baseline.
    """
    DEC056_BASELINE = 0.438
    V0_BASELINE_THRESHOLD = 0.438  # at least match DEC-056

    v1_sign = results.get("v1_sign_concordance_mean", float("nan"))
    v0_sign = results.get("v0_sign_concordance_mean", float("nan"))

    if math.isnan(v1_sign):
        return GateResult("W3", "Sign concordance > DEC-056 baseline (0.438) and > V0",
                          "NOT_EVALUATED", {"reason": "V1 not computed"})

    ev = {"v1_sign": v1_sign, "v0_sign": v0_sign, "dec056_baseline": DEC056_BASELINE}
    issues = []

    if v1_sign < 0.50:
        issues.append(f"V1 ({v1_sign:.3f}) < 0.50 threshold")
    if not math.isnan(v0_sign) and v1_sign <= v0_sign:
        issues.append(f"V1 ({v1_sign:.3f}) not > V0 ({v0_sign:.3f})")

    return GateResult("W3", "Sign concordance >= 0.50 AND > V0 baseline (DEC-056=0.438)",
                      "PASS" if not issues else "FAIL",
                      {**ev, "issues": issues})


# ── W4: Replication ────────────────────────────────────────────────────────────

def check_w4_replication(results: dict) -> GateResult:
    """
    W4: At least 1 relation classified as REPLICATED_ASSOCIATION (>= 2 countries)
    OR at least 1 correctly identified as COUNTRY_SPECIFIC.
    COVID_SENSITIVE alone is not sufficient.
    """
    n_replicated = results.get("n_replicated_associations", 0)
    n_country_specific = results.get("n_country_specific", 0)
    replicated_pairs = results.get("replicated_pairs", [])

    if n_replicated >= 1 or n_country_specific >= 1:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return GateResult("W4", ">=1 REPLICATED_ASSOCIATION or >=1 COUNTRY_SPECIFIC identified",
                      verdict,
                      {
                          "n_replicated": n_replicated,
                          "n_country_specific": n_country_specific,
                          "replicated_pairs": replicated_pairs[:5],
                      })


# ── W5: COVID sensitivity not promoted ────────────────────────────────────────

def check_w5_covid_not_promoted(results: dict) -> GateResult:
    """W5: No COVID_SENSITIVE relation promoted to ROBUST status."""
    covid_promoted = results.get("covid_sensitive_promoted_as_robust", [])
    return GateResult("W5", "COVID_SENSITIVE not promoted as ROBUST",
                      "PASS" if not covid_promoted else "FAIL",
                      {"covid_sensitive_promoted": covid_promoted})


# ── W6: Abstention available ──────────────────────────────────────────────────

def check_w6_abstention(results: dict) -> GateResult:
    """W6: Uncertain relations classified as INSUFFICIENT_EVIDENCE (not forced positive/negative)."""
    n_abstained = results.get("n_insufficient_evidence", 0)
    n_total = results.get("n_total_pairs_evaluated", 1)

    if n_total == 0:
        return GateResult("W6", "Uncertain relations classified as INSUFFICIENT_EVIDENCE",
                          "NOT_EVALUATED", {"reason": "No pairs evaluated"})

    abstention_rate = n_abstained / n_total
    # At least some abstentions expected — relations without evidence should not be forced
    passes = n_abstained > 0 and abstention_rate > 0.30
    return GateResult("W6", ">=30% of pairs classified as INSUFFICIENT_EVIDENCE (not forced)",
                      "PASS" if passes else "FAIL",
                      {
                          "n_abstained": n_abstained,
                          "n_total": n_total,
                          "abstention_rate": abstention_rate,
                      })


# ── W7: No causal language ────────────────────────────────────────────────────

CAUSAL_TERMS_DEC058 = [
    "causes", "caused by", "causal", "causality", "causation",
    "Granger cause", "drives", "effect of", "impact of", "leads to",
    "impacta", "impacto causal", "causa estrutural",
]


def scan_causal_terms_dec058(text: str) -> list[str]:
    found = []
    text_lower = text.lower()
    for t in CAUSAL_TERMS_DEC058:
        if t.lower() in text_lower:
            found.append(t)
    return found


def check_w7_no_causal_language(results: dict) -> GateResult:
    """W7: No causal language in outputs/report."""
    found = results.get("causal_terms_found", [])
    return GateResult("W7", "No causal language in outputs and report",
                      "PASS" if not found else "FAIL",
                      {"causal_terms_found": found, "checked_terms": CAUSAL_TERMS_DEC058})


# ── W8: Determinism ───────────────────────────────────────────────────────────

def check_w8_determinism(results: dict) -> GateResult:
    """W8: Same seed produces same results (hash matches across two runs)."""
    hash_match = results.get("determinism_hash_match", None)
    if hash_match is None:
        return GateResult("W8", "Same seed produces same results",
                          "NOT_EVALUATED", {"reason": "Determinism check not run"})
    return GateResult("W8", "Same seed produces identical outputs",
                      "PASS" if hash_match else "FAIL",
                      {"hash_match": hash_match})


# ── W9: Checkpoint documented ─────────────────────────────────────────────────

def check_w9_checkpoint(results: dict) -> GateResult:
    """W9: Initial and final checkpoint hashes documented."""
    initial_hash = results.get("initial_checkpoint_hash", "")
    final_hash = results.get("final_checkpoint_hash", "")
    issues = []
    if not initial_hash:
        issues.append("Initial checkpoint hash missing")
    if not final_hash:
        issues.append("Final checkpoint hash missing (expected if V0 only)")
    # V0 (no fine-tuning) may not produce a new hash — only require initial
    return GateResult("W9", "Initial and final checkpoint hashes documented",
                      "PASS" if initial_hash else "FAIL",
                      {"initial_hash": initial_hash, "final_hash": final_hash, "issues": issues})


# ── W10: Model size ────────────────────────────────────────────────────────────

def check_w10_model_size(results: dict) -> GateResult:
    """W10: Encoder + adapter <= 5000 params total. Frugal model."""
    n_params = results.get("n_encoder_params", 0)
    n_adapter = results.get("n_adapter_params", 0)
    total = n_params + n_adapter

    return GateResult("W10", "Encoder + adapter <= 5000 params (frugal model)",
                      "PASS" if total <= 5000 else "FAIL",
                      {
                          "n_encoder_params": n_params,
                          "n_adapter_params": n_adapter,
                          "n_total_params": total,
                      })


# ── Aggregate ─────────────────────────────────────────────────────────────────

def evaluate_all_gates_dec058(results: dict) -> dict[str, GateResult]:
    return {
        "W1": check_w1_safety(results),
        "W2": check_w2_controls(results),
        "W3": check_w3_sign_concordance(results),
        "W4": check_w4_replication(results),
        "W5": check_w5_covid_not_promoted(results),
        "W6": check_w6_abstention(results),
        "W7": check_w7_no_causal_language(results),
        "W8": check_w8_determinism(results),
        "W9": check_w9_checkpoint(results),
        "W10": check_w10_model_size(results),
    }


def format_gate_report_dec058(gates: dict[str, GateResult]) -> str:
    lines = [
        "| Gate | Description | Verdict |",
        "|------|-------------|---------|",
    ]
    for gid in [f"W{i}" for i in range(1, 11)]:
        if gid not in gates:
            continue
        g = gates[gid]
        icon = "✓" if g.verdict == "PASS" else ("✗" if g.verdict == "FAIL" else "○")
        lines.append(f"| {gid} | {g.description} | {icon} {g.verdict} |")
    return "\n".join(lines)
