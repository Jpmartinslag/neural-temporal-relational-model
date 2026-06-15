"""
gates_dec055.py — Gate definitions S1-S10 for DEC-055.

FROZEN before results. All thresholds set before any experiment.

Evaluates whether SharedRelationEncoder generalizes across:
  - Unseen pairs (same environments, withheld labels)
  - Unseen environments (never seen during training)
  - Direction, sign, lag discrimination OOS
  - Local context adapter value
  - Temporal dynamics detection
  - Negative controls (permuted relations/labels)
  - Replication across seeds
  - Parameter compactness

Thresholds (frozen, DEC-055):
  S3: AUC_unseen_pairs >= 0.65 AND AUPRC > prevalence
  S4: SharedEncoder OOS-env AUC > old_head OOS-env AUC AND > permuted baseline
  S5: direction_acc > 0.50, sign_acc > 0.55, lag_acc > 0.55 OOS
  S6: adapter improves AUC in >= 1 OOS-env without degrading pair transfer >0.02
  S7: temporal peak in correct window in >= 2/3 regime-change envs
  S8: permuted controls degrade AUC by >= 0.05 vs real encoder
  S9: positive effect on AUC in >= 4/5 seeds (unseen pairs)
  S10: total params <= 5000
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


# ── S1: No leakage, NaN, Inf ──────────────────────────────────────────────────

def check_s1_safety(results: dict) -> GateResult:
    """S1: Zero leakage, overlap, NaN, or Inf in any metric."""
    issues = []
    evidence: dict = {}

    leakage_ok = results.get("leakage_check", True)
    evidence["leakage_check"] = leakage_ok
    if not leakage_ok:
        issues.append("Leakage detected (future info in encoder inputs)")

    nan_count = results.get("nan_count", 0)
    inf_count = results.get("inf_count", 0)
    evidence["nan_count"] = nan_count
    evidence["inf_count"] = inf_count
    if nan_count > 0:
        issues.append(f"{nan_count} NaN values in outputs")
    if inf_count > 0:
        issues.append(f"{inf_count} Inf values in outputs")

    test_overlap = results.get("test_target_in_train", False)
    evidence["test_overlap"] = test_overlap
    if test_overlap:
        issues.append("Test targets appeared in training data")

    return GateResult(
        "S1", "Zero leakage / NaN / Inf in all metrics",
        "PASS" if not issues else "FAIL",
        {**evidence, "issues": issues},
    )


# ── S2: No pair memorization ──────────────────────────────────────────────────

def check_s2_no_pair_memorization(results: dict) -> GateResult:
    """S2: No trainable parameter indexed by (src, tgt) pair."""
    issues = []
    evidence: dict = {}

    pair_params_found = results.get("pair_params_found", [])
    evidence["pair_params_found"] = pair_params_found
    if pair_params_found:
        issues.append(f"Pair-specific parameters: {pair_params_found}")

    n_params = results.get("n_encoder_params", 0)
    evidence["n_encoder_params"] = n_params

    # Additional check: AUC for unseen-instance pairs should NOT be 1.000
    # (1.000 would indicate memorization, not generalization)
    is_auc = results.get("in_sample_auc_mean", float("nan"))
    oos_auc = results.get("unseen_pair_auc_mean", float("nan"))
    evidence["in_sample_auc_mean"] = is_auc
    evidence["unseen_pair_auc_mean"] = oos_auc

    if not math.isnan(is_auc) and is_auc > 0.999:
        issues.append(f"IS AUC={is_auc:.3f} = 1.000 — likely memorization, check architecture")

    return GateResult(
        "S2", "No trainable parameter indexed by sector pair; no S×S lookup table",
        "PASS" if not issues else "FAIL",
        {**evidence, "issues": issues},
    )


# ── S3: Unseen-pair transfer ───────────────────────────────────────────────────

def check_s3_unseen_pair_transfer(results: dict) -> GateResult:
    """S3: AUC >= 0.65 AND AUPRC > prevalence on unseen pairs."""
    auc = results.get("unseen_pair_auc_mean", float("nan"))
    auprc = results.get("unseen_pair_auprc_mean", float("nan"))
    prev = results.get("unseen_pair_prevalence_mean", float("nan"))

    if math.isnan(auc):
        return GateResult("S3", "Unseen-pair AUC >= 0.65 AND AUPRC > prevalence",
                          "NOT_EVALUATED", {"reason": "No unseen_pair_auc"})

    issues = []
    if auc < 0.65:
        issues.append(f"AUC={auc:.3f} < 0.65")
    if not math.isnan(auprc) and not math.isnan(prev) and auprc <= prev:
        issues.append(f"AUPRC={auprc:.3f} not > prevalence={prev:.3f}")

    return GateResult(
        "S3", "Unseen-pair transfer: AUC >= 0.65 AND AUPRC > prevalence",
        "PASS" if not issues else "FAIL",
        {
            "auc": auc, "auprc": auprc, "prevalence": prev,
            "all_aucs": results.get("unseen_pair_aucs", []),
            "issues": issues,
        },
    )


# ── S4: Unseen-environment transfer ───────────────────────────────────────────

def check_s4_unseen_env_transfer(results: dict) -> GateResult:
    """S4: SharedEncoder OOS-env AUC > old_head OOS-env AUC AND > permuted baseline."""
    shared_auc = results.get("oos_env_shared_auc_mean", float("nan"))
    old_auc = results.get("oos_env_old_head_auc_mean", float("nan"))
    perm_auc = results.get("oos_env_permuted_auc_mean", float("nan"))

    if math.isnan(shared_auc):
        return GateResult("S4", "SharedEncoder OOS-env AUC > old head AND > permuted",
                          "NOT_EVALUATED", {"reason": "No oos_env_shared_auc"})

    issues = []
    if not math.isnan(old_auc) and shared_auc <= old_auc:
        issues.append(f"SharedEncoder AUC={shared_auc:.3f} not > old_head AUC={old_auc:.3f}")
    if not math.isnan(perm_auc) and shared_auc <= perm_auc:
        issues.append(f"SharedEncoder AUC={shared_auc:.3f} not > permuted AUC={perm_auc:.3f}")

    return GateResult(
        "S4", "Unseen-env transfer: SharedEncoder > old head AND > permuted baseline",
        "PASS" if not issues else "FAIL",
        {
            "shared_auc": shared_auc,
            "old_head_auc": old_auc,
            "permuted_auc": perm_auc,
            "issues": issues,
        },
    )


# ── S5: Direction / sign / lag discrimination OOS ─────────────────────────────

def check_s5_direction_sign_lag(results: dict) -> GateResult:
    """S5: direction_acc > 0.50, sign_acc > 0.55, lag_acc > 0.55 OOS."""
    dir_acc = results.get("oos_direction_acc_mean", float("nan"))
    sign_acc = results.get("oos_sign_acc_mean", float("nan"))
    lag_acc = results.get("oos_lag_acc_mean", float("nan"))

    issues = []
    evidence = {
        "direction_acc": dir_acc,
        "sign_acc": sign_acc,
        "lag_acc": lag_acc,
    }

    if math.isnan(dir_acc):
        return GateResult("S5", "Direction/sign/lag each beat chance OOS",
                          "NOT_EVALUATED", {**evidence, "reason": "No OOS direction_acc"})

    if dir_acc <= 0.50:
        issues.append(f"direction_acc={dir_acc:.3f} <= 0.50")
    if not math.isnan(sign_acc) and sign_acc <= 0.55:
        issues.append(f"sign_acc={sign_acc:.3f} <= 0.55")
    if not math.isnan(lag_acc) and lag_acc <= 0.55:
        issues.append(f"lag_acc={lag_acc:.3f} <= 0.55")

    return GateResult(
        "S5", "Direction > 0.50 / sign > 0.55 / lag > 0.55 OOS",
        "PASS" if not issues else "FAIL",
        {**evidence, "issues": issues},
    )


# ── S6: Local-context adapter value ───────────────────────────────────────────

def check_s6_adapter_value(results: dict) -> GateResult:
    """
    S6: Adapter improves AUC in >= 1 OOS env without degrading pair transfer > 0.02.
    Control without adapter must also be evaluated.
    """
    adapter_oos_aucs = results.get("adapter_oos_env_aucs", [])
    no_adapter_oos_aucs = results.get("no_adapter_oos_env_aucs", [])
    pair_auc_with = results.get("adapter_unseen_pair_auc", float("nan"))
    pair_auc_without = results.get("no_adapter_unseen_pair_auc", float("nan"))

    if not adapter_oos_aucs or not no_adapter_oos_aucs:
        return GateResult("S6", "Adapter improves OOS env AUC without degrading pair transfer",
                          "NOT_EVALUATED", {"reason": "Missing adapter/no-adapter OOS results"})

    issues = []
    n_improved = sum(1 for a, b in zip(adapter_oos_aucs, no_adapter_oos_aucs) if a > b)
    evidence = {
        "adapter_oos_aucs": adapter_oos_aucs,
        "no_adapter_oos_aucs": no_adapter_oos_aucs,
        "n_improved": n_improved,
        "pair_auc_with_adapter": pair_auc_with,
        "pair_auc_without_adapter": pair_auc_without,
    }

    if n_improved < 1:
        issues.append(f"Adapter improved 0/{len(adapter_oos_aucs)} OOS envs")

    # Check that adapter doesn't degrade pair transfer
    if not math.isnan(pair_auc_with) and not math.isnan(pair_auc_without):
        degradation = pair_auc_without - pair_auc_with
        evidence["pair_transfer_degradation"] = degradation
        if degradation > 0.02:
            issues.append(f"Adapter degraded pair transfer by {degradation:.3f} > 0.02")

    return GateResult(
        "S6", "Adapter improves OOS env AUC in >= 1 env; pair transfer degradation <= 0.02",
        "PASS" if not issues else "FAIL",
        {**evidence, "issues": issues},
    )


# ── S7: Temporal dynamics detection ───────────────────────────────────────────

def check_s7_temporal_dynamics(results: dict) -> GateResult:
    """
    S7: Temporal graph changes detected in correct window in >= 2/3 regime-change envs.
    The presence probability A_t should peak during the active relation window.
    """
    temporal_results = results.get("temporal_dynamics", [])

    if not temporal_results:
        return GateResult("S7", "Temporal dynamics detected in correct window (>= 2/3)",
                          "NOT_EVALUATED", {"reason": "No temporal_dynamics results"})

    n_correct = 0
    n_total = 0
    details = []

    for tr in temporal_results:
        if not tr.get("has_regime_change", False):
            continue
        n_total += 1
        peak_in_window = tr.get("peak_in_active_window", False)
        if peak_in_window:
            n_correct += 1
        details.append({
            "env_id": tr.get("env_id"),
            "peak_year": tr.get("peak_year"),
            "active_window": tr.get("active_window"),
            "peak_in_window": peak_in_window,
        })

    if n_total == 0:
        return GateResult("S7", "Temporal dynamics detected in correct window (>= 2/3)",
                          "NOT_EVALUATED", {"reason": "No regime-change environments found"})

    frac = n_correct / n_total
    passes = frac >= 2.0 / 3.0

    return GateResult(
        "S7", "Temporal peak in correct window in >= 2/3 regime-change environments",
        "PASS" if passes else "FAIL",
        {
            "n_correct": n_correct,
            "n_total": n_total,
            "frac_correct": frac,
            "details": details,
        },
    )


# ── S8: Negative controls ─────────────────────────────────────────────────────

def check_s8_negative_controls(results: dict) -> GateResult:
    """
    S8: Permuted relations AND permuted pair labels degrade AUC by >= 0.05 vs real encoder.
    """
    real_auc = results.get("unseen_pair_auc_mean", float("nan"))
    perm_rel_auc = results.get("permuted_relations_auc_mean", float("nan"))
    perm_lab_auc = results.get("permuted_pair_labels_auc_mean", float("nan"))

    if math.isnan(real_auc):
        return GateResult("S8", "Permuted controls degrade AUC by >= 0.05",
                          "NOT_EVALUATED", {"reason": "No real AUC"})

    issues = []
    evidence = {
        "real_auc": real_auc,
        "permuted_relations_auc": perm_rel_auc,
        "permuted_pair_labels_auc": perm_lab_auc,
    }

    if not math.isnan(perm_rel_auc):
        delta_rel = real_auc - perm_rel_auc
        evidence["delta_permuted_relations"] = delta_rel
        if delta_rel < 0.05:
            issues.append(f"Permuted-relations delta={delta_rel:.3f} < 0.05")

    if not math.isnan(perm_lab_auc):
        delta_lab = real_auc - perm_lab_auc
        evidence["delta_permuted_labels"] = delta_lab
        if delta_lab < 0.05:
            issues.append(f"Permuted-labels delta={delta_lab:.3f} < 0.05")

    return GateResult(
        "S8", "Permuted controls degrade AUC by >= 0.05 (both relations and labels)",
        "PASS" if not issues else "FAIL",
        {**evidence, "issues": issues},
    )


# ── S9: Replication across seeds ──────────────────────────────────────────────

def check_s9_replication(per_seed_results: list) -> GateResult:
    """
    S9: Positive effect (SharedEncoder AUC > 0.60 on unseen pairs) in >= 4/5 seeds.
    """
    if not per_seed_results:
        return GateResult("S9", "Positive effect on AUC in >= 4/5 seeds",
                          "NOT_EVALUATED", {"reason": "No per-seed results"})

    n_pass = 0
    aucs = []
    for sr in per_seed_results:
        auc = sr.get("unseen_pair_auc_mean", float("nan"))
        aucs.append(auc)
        if not math.isnan(auc) and auc > 0.60:
            n_pass += 1

    n_total = len(per_seed_results)
    frac = n_pass / max(1, n_total)
    passes = n_pass >= 4 and n_total >= 4

    return GateResult(
        "S9", "SharedEncoder AUC > 0.60 on unseen pairs in >= 4/5 seeds",
        "PASS" if passes else "FAIL",
        {
            "n_pass": n_pass,
            "n_total": n_total,
            "frac_pass": frac,
            "per_seed_aucs": aucs,
        },
    )


# ── S10: Compactness ──────────────────────────────────────────────────────────

def check_s10_compactness(results: dict) -> GateResult:
    """S10: Total parameters (encoder + adapter) <= 5000."""
    n_encoder = results.get("n_encoder_params", 0)
    n_adapter = results.get("n_adapter_params", 0)
    n_total = n_encoder + n_adapter

    passes = n_total <= 5000

    return GateResult(
        "S10", "Total params (encoder + adapter) <= 5000",
        "PASS" if passes else "FAIL",
        {
            "n_encoder_params": n_encoder,
            "n_adapter_params": n_adapter,
            "n_total_params": n_total,
            "threshold": 5000,
        },
        notes=f"Encoder: {n_encoder}, Adapter: {n_adapter}, Total: {n_total}",
    )


# ── Aggregate ─────────────────────────────────────────────────────────────────

def evaluate_all_gates_dec055(
    results: dict,
    per_seed_results: list,
) -> dict[str, GateResult]:
    """Evaluate all S1-S10 gates."""
    gates = {
        "S1": check_s1_safety(results),
        "S2": check_s2_no_pair_memorization(results),
        "S3": check_s3_unseen_pair_transfer(results),
        "S4": check_s4_unseen_env_transfer(results),
        "S5": check_s5_direction_sign_lag(results),
        "S6": check_s6_adapter_value(results),
        "S7": check_s7_temporal_dynamics(results),
        "S8": check_s8_negative_controls(results),
        "S9": check_s9_replication(per_seed_results),
        "S10": check_s10_compactness(results),
    }
    return gates


def format_gate_report_dec055(gates: dict[str, GateResult]) -> str:
    lines = [
        "| Gate | Description | Verdict |",
        "|------|-------------|---------|",
    ]
    for gid in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]:
        if gid not in gates:
            continue
        g = gates[gid]
        icon = "✓" if g.verdict == "PASS" else ("✗" if g.verdict == "FAIL" else "○")
        notes = f" *{g.notes}*" if g.notes else ""
        lines.append(f"| {gid} | {g.description}{notes} | {icon} {g.verdict} |")
    return "\n".join(lines)
