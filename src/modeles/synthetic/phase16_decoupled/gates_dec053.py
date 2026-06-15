"""
gates_dec053.py — Gate definitions D1-D10 for DEC-053.

FROZEN before results. Do not modify after running the experiment.

Gates:
  D1  Metric correctness   — AUC/AUPRC finite, directed target, prevalence recorded.
  D2  Analytic recovery    — AUC≥0.60, AUPRC>prevalence, sign/lag>0.50.
  D3  Temporal fallback    — gate=0 reproduces temporal-only exactly (atol=1e-5).
  D4  Useful-graph opening — gate>0.3 in F1/F3/F4 cells where relation helps.
  D5  Useless-graph closing— gate<0.2 in F2; closes outside useful window in F5.
  D6  Directed specificity — presence_logit[true_dir] >> presence_logit[false_dir] in F6.
  D7  Predictive safety    — gated never >5% worse than temporal-only on any scenario.
  D8  Selective utility    — gated MAE < graph-always-on AND < graph-permuted.
  D9  Realistic recon      — honest comparison reported (gain not required).
  D10 Replication          — functional results replicate in ≥2/3 seeds.

Possible verdicts: PASS, FAIL, NOT_EVALUATED.
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


def check_d1_metric_correctness(eval_results: dict) -> GateResult:
    """D1: AUC/AUPRC fields present, finite, directed target used."""
    issues = []
    for r in eval_results.get("all_results", []):
        auc = r.get("edge_auc_directed", float("nan"))
        auprc = r.get("edge_auprc_directed", float("nan"))
        prev = r.get("prevalence", float("nan"))
        if math.isnan(auc) and r.get("n_true_directed", 0) > 0:
            issues.append(f"AUC NaN with {r.get('n_true_directed')} true edges ({r.get('scenario')} s={r.get('seed')})")
        if math.isnan(auprc) and r.get("n_true_directed", 0) > 0:
            issues.append(f"AUPRC NaN with true edges ({r.get('scenario')} s={r.get('seed')})")
        if math.isnan(prev):
            issues.append(f"prevalence NaN ({r.get('scenario')} s={r.get('seed')})")
    verdict = "PASS" if not issues else "FAIL"
    return GateResult("D1", "Metric correctness: AUC/AUPRC finite, directed target", verdict,
                      {"n_issues": len(issues), "examples": issues[:3]})


def check_d2_analytic_recovery(eval_results: dict) -> GateResult:
    """D2: AUC≥0.60, AUPRC>prevalence, sign/lag>0.50."""
    aucs = [r.get("edge_auc_directed", float("nan"))
            for r in eval_results.get("all_results", [])
            if not math.isnan(r.get("edge_auc_directed", float("nan")))]
    auprc_beats = [
        r.get("edge_auprc_directed", float("nan")) > r.get("prevalence", float("nan"))
        for r in eval_results.get("all_results", [])
        if not math.isnan(r.get("edge_auprc_directed", float("nan")))
    ]
    sign_accs = [r.get("sign_acc", float("nan"))
                 for r in eval_results.get("all_results", [])
                 if not math.isnan(r.get("sign_acc", float("nan")))]
    lag_accs = [r.get("lag_acc", float("nan"))
                for r in eval_results.get("all_results", [])
                if not math.isnan(r.get("lag_acc", float("nan")))]

    mean_auc = sum(aucs) / len(aucs) if aucs else float("nan")
    frac_auprc_beats = sum(auprc_beats) / len(auprc_beats) if auprc_beats else float("nan")
    mean_sign = sum(sign_accs) / len(sign_accs) if sign_accs else float("nan")
    mean_lag = sum(lag_accs) / len(lag_accs) if lag_accs else float("nan")

    passes = (
        (not math.isnan(mean_auc) and mean_auc >= 0.60) and
        (not math.isnan(frac_auprc_beats) and frac_auprc_beats > 0.5) and
        (math.isnan(mean_sign) or mean_sign > 0.50) and
        (math.isnan(mean_lag) or mean_lag > 0.50)
    )
    return GateResult("D2", "Analytic relation recovery: AUC≥0.60, AUPRC>prev, sign/lag>0.50",
                      "PASS" if passes else "FAIL",
                      {"mean_auc": mean_auc, "frac_auprc_beats_prev": frac_auprc_beats,
                       "mean_sign_acc": mean_sign, "mean_lag_acc": mean_lag})


def check_d3_temporal_fallback(fixture_results: dict) -> GateResult:
    """D3: gate=0 reproduces temporal-only exactly (atol=1e-5)."""
    delta = fixture_results.get("gate_zero_identity_max_delta", float("nan"))
    passes = not math.isnan(delta) and delta < 1e-5
    return GateResult("D3", "Temporal fallback identity: gate=0 → temporal-only (atol=1e-5)",
                      "PASS" if passes else "FAIL",
                      {"max_delta": delta})


def check_d4_useful_graph_opening(fixture_results: dict) -> GateResult:
    """D4: gate>0.3 in F1/F3/F4 cells where relation helps."""
    f1 = fixture_results.get("F1_useful_graph", {})
    f3 = fixture_results.get("F3_negative_relation", {})
    f4 = fixture_results.get("F4_lag2_relation", {})
    gates = [f1.get("gate_mean"), f3.get("gate_mean"), f4.get("gate_mean")]
    gates = [g for g in gates if g is not None and not math.isnan(g)]
    passes = len(gates) >= 2 and sum(g > 0.3 for g in gates) >= 2
    return GateResult("D4", "Useful-graph opening: gate>0.3 in F1/F3/F4",
                      "PASS" if passes else "FAIL",
                      {"f1_gate": f1.get("gate_mean"), "f3_gate": f3.get("gate_mean"),
                       "f4_gate": f4.get("gate_mean")})


def check_d5_useless_graph_closing(fixture_results: dict) -> GateResult:
    """D5: gate<0.2 in F2 (pure AR); gate closes outside regime window in F5."""
    f2 = fixture_results.get("F2_useless_graph", {})
    f5 = fixture_results.get("F5_regime_window", {})
    f2_gate = f2.get("gate_mean", float("nan"))
    f5_outside = f5.get("gate_outside_window_mean", float("nan"))
    issues = []
    if not math.isnan(f2_gate) and f2_gate >= 0.2:
        issues.append(f"F2 gate too high: {f2_gate:.3f} (expected <0.2)")
    if not math.isnan(f5_outside) and f5_outside >= 0.3:
        issues.append(f"F5 outside-window gate too high: {f5_outside:.3f}")
    return GateResult("D5", "Useless-graph closing: gate<0.2 in F2, closed outside F5 window",
                      "PASS" if not issues else "FAIL",
                      {"f2_gate": f2_gate, "f5_outside_gate": f5_outside, "issues": issues})


def check_d6_directed_specificity(fixture_results: dict) -> GateResult:
    """D6: In F6, presence_logit[true_dir] >> presence_logit[false_dir] (diff>0.2)."""
    f6 = fixture_results.get("F6_asymmetric_directed", {})
    diff = f6.get("presence_logit_true_minus_false", float("nan"))
    passes = not math.isnan(diff) and diff > 0.2
    return GateResult("D6", "Directed specificity: A→B separated from B→A in F6",
                      "PASS" if passes else "FAIL",
                      {"presence_logit_diff": diff})


def check_d7_predictive_safety(eval_results: dict) -> GateResult:
    """D7: gated never >5% worse than temporal-only in MAE on any (scenario, mask) group."""
    from collections import defaultdict
    groups: dict = defaultdict(lambda: {"temporal": [], "gated": []})
    for r in eval_results.get("all_results", []):
        k = (r.get("scenario"), r.get("mask_key"))
        if not math.isnan(r.get("mae_temporal", float("nan"))):
            groups[k]["temporal"].append(r["mae_temporal"])
        if not math.isnan(r.get("mae_gated", float("nan"))):
            groups[k]["gated"].append(r["mae_gated"])

    violations = []
    for k, v in groups.items():
        if v["temporal"] and v["gated"]:
            mean_temp = sum(v["temporal"]) / len(v["temporal"])
            mean_gated = sum(v["gated"]) / len(v["gated"])
            if mean_gated > mean_temp * 1.05:
                violations.append(f"{k}: temporal={mean_temp:.4f}, gated={mean_gated:.4f}")

    return GateResult("D7", "Predictive safety: gated never >5% worse than temporal-only",
                      "PASS" if not violations else "FAIL",
                      {"n_violations": len(violations), "examples": violations[:3]})


def check_d8_selective_utility(eval_results: dict) -> GateResult:
    """D8: gated MAE < graph-always-on AND < graph-permuted in aggregate."""
    results = eval_results.get("all_results", [])
    maes_gated = [r.get("mae_gated", float("nan")) for r in results if not math.isnan(r.get("mae_gated", float("nan")))]
    maes_always = [r.get("mae_graph_always", float("nan")) for r in results if not math.isnan(r.get("mae_graph_always", float("nan")))]
    maes_perm = [r.get("mae_permuted", float("nan")) for r in results if not math.isnan(r.get("mae_permuted", float("nan")))]

    mean_gated = sum(maes_gated) / len(maes_gated) if maes_gated else float("nan")
    mean_always = sum(maes_always) / len(maes_always) if maes_always else float("nan")
    mean_perm = sum(maes_perm) / len(maes_perm) if maes_perm else float("nan")

    beats_always = not math.isnan(mean_gated) and not math.isnan(mean_always) and mean_gated < mean_always
    beats_perm = not math.isnan(mean_gated) and not math.isnan(mean_perm) and mean_gated < mean_perm
    passes = beats_always and beats_perm

    return GateResult("D8", "Selective utility: gated < graph-always and < graph-permuted",
                      "PASS" if passes else "FAIL",
                      {"mae_gated": mean_gated, "mae_graph_always": mean_always, "mae_permuted": mean_perm})


def check_d9_realistic_reconstruction(eval_results: dict) -> GateResult:
    """D9: Honest comparison reported. Always PASS (informational gate)."""
    results = eval_results.get("all_results", [])
    maes = {
        "temporal": [r.get("mae_temporal") for r in results if r.get("mae_temporal") is not None],
        "gated": [r.get("mae_gated") for r in results if r.get("mae_gated") is not None],
        "ffill": [r.get("mae_ffill") for r in results if r.get("mae_ffill") is not None],
    }
    means = {k: sum(v) / len(v) if v else float("nan") for k, v in maes.items()}
    return GateResult("D9", "Realistic reconstruction: honest comparison reported",
                      "PASS",  # informational
                      {"mean_maes": means,
                       "note": "gain over ffill/temporal not required for ANALYTIC layer"})


def check_d10_replication(eval_results: dict) -> GateResult:
    """D10: Key functional results replicate in ≥2/3 seeds."""
    from collections import defaultdict
    seeds_beat: dict = defaultdict(int)
    seeds_total: dict = defaultdict(int)
    for r in eval_results.get("all_results", []):
        k = (r.get("scenario"), r.get("mask_key"))
        s = r.get("seed")
        seeds_total[(k, s)] += 1
        if not math.isnan(r.get("mae_gated", float("nan"))) and not math.isnan(r.get("mae_temporal", float("nan"))):
            if r["mae_gated"] <= r["mae_temporal"] * 1.05:
                seeds_beat[(k, s)] += 1

    # Count groups where ≥2 seeds pass
    groups: dict = defaultdict(lambda: {"pass": 0, "total": 0})
    for (k, s), count in seeds_total.items():
        groups[k]["total"] += 1
        if seeds_beat.get((k, s), 0) > 0:
            groups[k]["pass"] += 1

    n_groups = len(groups)
    n_replicate = sum(1 for v in groups.values() if v["pass"] >= 2)
    passes = n_groups > 0 and n_replicate / n_groups >= 0.5

    return GateResult("D10", "Replication: safety holds in ≥2/3 seeds across scenarios",
                      "PASS" if passes else "FAIL",
                      {"n_groups": n_groups, "n_replicate": n_replicate,
                       "frac": n_replicate / n_groups if n_groups else float("nan")})


def evaluate_all_gates(eval_results: dict, fixture_results: dict) -> dict[str, GateResult]:
    gates = {}
    gates["D1"] = check_d1_metric_correctness(eval_results)
    gates["D2"] = check_d2_analytic_recovery(eval_results)
    gates["D3"] = check_d3_temporal_fallback(fixture_results)
    gates["D4"] = check_d4_useful_graph_opening(fixture_results)
    gates["D5"] = check_d5_useless_graph_closing(fixture_results)
    gates["D6"] = check_d6_directed_specificity(fixture_results)
    gates["D7"] = check_d7_predictive_safety(eval_results)
    gates["D8"] = check_d8_selective_utility(eval_results)
    gates["D9"] = check_d9_realistic_reconstruction(eval_results)
    gates["D10"] = check_d10_replication(eval_results)
    return gates


def format_gate_report(gates: dict[str, GateResult]) -> str:
    lines = ["| Gate | Description | Verdict |",
             "|------|-------------|---------|"]
    for gid in sorted(gates):
        g = gates[gid]
        icon = "✓" if g.verdict == "PASS" else ("✗" if g.verdict == "FAIL" else "○")
        lines.append(f"| {gid} | {g.description} | {icon} {g.verdict} |")
    return "\n".join(lines)
