"""
gates_dec047.py — A1-A10 gates for DEC-047 (frozen before execution).

These gates are frozen before any pilot execution. Do NOT modify thresholds
or gate logic after first results are available.

Gates:
  A1 SAFETY              : zero leakage, NaN, Inf; support/val/test disjoint
  A2 ADAPTATION_BENEFIT  : adapted strategy beats Z0 (zero-shot) on frozen test
  A3 GRAPH_CONTRIBUTION  : graph strategy beats C0 (no-graph) and P0 (permuted)
  A4 BASELINE_RELEVANCE  : records whether strategy beats B0 (ffill) and B1 (Ridge)
  A5 FEWSHOT_EFFICIENCY  : gain appears at k_frac <= 0.10 (not only at 0.20)
  A6 GRAPH_PRESERVATION  : edge AUC doesn't drop > 0.05 after adaptation
  A7 BLOCK_ROBUSTNESS    : result holds in block_30 mask (not only mcar_30)
  A8 REPLICATION         : effect in same direction in >= 4/5 seeds
  A9 ADAPTER_VALUE       : A2 (adapter+decoder) beats A1 (decoder-only)
  A10 FINETUNING_TRADEOFF: A4 is only preferred if MAE improves AND graph not degraded

Decision vocabulary:
  DECODER_ONLY_SUPPORTED           : A2+A3+A8 PASS
  ADAPTER_FEWSHOT_SUPPORTED        : A2+A3+A8+A9 PASS
  FULL_FINETUNING_SUPPORTED        : A2+A3+A8+A10 PASS (graph preserved)
  GRAPH_PRESERVATION_FAILED        : A6 FAIL for any strategy
  FEWSHOT_ADAPTATION_PARTIAL       : A2 PASS but A5 FAIL (only works at k_frac=0.20)
  FEWSHOT_ADAPTATION_FAILED        : A2 FAIL

Thresholds (frozen):
  AUC_DEGRADATION_THRESHOLD = 0.05  (A6: AUC must not drop more than this)
  FEWSHOT_MAX_K = 0.10              (A5: gain must appear at <= 10%)
  SEED_PASS_FRAC = 4/5              (A8: at least 4 of 5 seeds must agree)
  BASELINE_MAE_THRESHOLD = 1.0      (A4: ratio adapted/baseline; < 1 means beat baseline)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

DEC047_GATE_VERSION = "dec047_gates_v1"

# ── Frozen thresholds ─────────────────────────────────────────────────────────

AUC_DEGRADATION_THRESHOLD: float = 0.05
FEWSHOT_MAX_K: float = 0.10
SEED_PASS_FRAC: float = 4 / 5
BASELINE_MAE_THRESHOLD: float = 1.0


# ── Utilities ─────────────────────────────────────────────────────────────────

def _get_mae(record: dict) -> float | None:
    v = record.get("mae")
    if v is None or (isinstance(v, float) and (v != v or abs(v) == float("inf"))):
        return None
    return float(v)


def _mean_safe(vals: list) -> float:
    clean = [v for v in vals if v is not None and v == v]
    return float(np.mean(clean)) if clean else float("nan")


def _is_finite(v) -> bool:
    if v is None:
        return False
    try:
        return float(v) == float(v) and abs(float(v)) != float("inf")
    except (TypeError, ValueError):
        return False


# ── Gate evaluators ───────────────────────────────────────────────────────────

def _a1_safety(records: list[dict]) -> dict:
    """
    A1 SAFETY: zero leakage, NaN, Inf; support/val/test disjoint.
    Every record must have leakage_pass=True, no NaN/Inf in mae/rmse.
    """
    nan_count = 0
    leakage_count = 0
    zero_hidden = 0
    errors: list[str] = []

    for r in records:
        if r.get("error"):
            errors.append(f"error_record: {r.get('error', '')[:60]}")
            continue
        if not r.get("leakage_pass", True):
            leakage_count += 1
            errors.append(f"{r.get('scenario')}/seed={r.get('dataset_seed')}/{r.get('strategy')}: LEAKAGE")
        if r.get("n_hidden_test", 1) == 0:
            zero_hidden += 1
        for k in ["mae", "rmse"]:
            v = r.get(k)
            if v is not None and (v != v or abs(float(v)) == float("inf")):
                nan_count += 1
                errors.append(f"{r.get('strategy')}/{k}: NaN/Inf={v}")

    passed = nan_count == 0 and leakage_count == 0 and zero_hidden == 0
    return {
        "pass": bool(passed),
        "nan_inf_count": nan_count,
        "leakage_count": leakage_count,
        "zero_hidden_count": zero_hidden,
        "errors": errors[:5],
    }


def _a2_adaptation_benefit(records: list[dict]) -> dict:
    """
    A2 ADAPTATION_BENEFIT: at least one adapted strategy (A1/A2/A3/A4) beats
    Z0 (zero-shot) on the same (scenario, dataset_seed, k_frac, support_seed, mask_key).
    k_frac > 0 required.

    Pass condition: fraction of comparisons where adapted < z0 >= 0.5.
    """
    adapted_strategies = {"A1", "A2", "A3", "A4"}
    # Build Z0 index
    z0_index: dict = {}
    for r in records:
        if r.get("strategy") == "Z0" and not r.get("error"):
            key = (r.get("scenario"), r.get("dataset_seed"), r.get("support_seed"), r.get("mask_key"))
            z0_index[key] = _get_mae(r)

    wins = 0
    total = 0
    for r in records:
        if r.get("strategy") not in adapted_strategies or r.get("error"):
            continue
        if (r.get("k_frac") or 0) <= 0:
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("support_seed"), r.get("mask_key"))
        z0_mae = z0_index.get(key)
        adapted_mae = _get_mae(r)
        if z0_mae is None or adapted_mae is None:
            continue
        total += 1
        if adapted_mae < z0_mae:
            wins += 1

    if total == 0:
        return {"pass": False, "note": "no valid comparisons", "wins": 0, "total": 0}

    frac = wins / total
    return {
        "pass": bool(frac >= 0.5),
        "frac_adapted_beats_z0": round(frac, 3),
        "wins": wins,
        "total": total,
    }


def _a3_graph_contribution(records: list[dict]) -> dict:
    """
    A3 GRAPH_CONTRIBUTION: graph strategy (A1/A2) beats C0 (no-graph) and P0 (permuted)
    on same (scenario, dataset_seed, k_frac, support_seed, mask_key).
    """
    graph_strategies = {"A1", "A2"}
    c0_index: dict = {}
    p0_index: dict = {}
    for r in records:
        if r.get("error"):
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"), r.get("mask_key"))
        if r.get("strategy") == "C0":
            c0_index[key] = _get_mae(r)
        elif r.get("strategy") == "P0":
            p0_index[key] = _get_mae(r)

    beats_c0 = 0
    beats_p0 = 0
    total_c0 = 0
    total_p0 = 0
    for r in records:
        if r.get("strategy") not in graph_strategies or r.get("error"):
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"), r.get("mask_key"))
        gmae = _get_mae(r)
        if gmae is None:
            continue
        c0 = c0_index.get(key)
        if c0 is not None:
            total_c0 += 1
            if gmae < c0:
                beats_c0 += 1
        p0 = p0_index.get(key)
        if p0 is not None:
            total_p0 += 1
            if gmae < p0:
                beats_p0 += 1

    frac_c0 = beats_c0 / total_c0 if total_c0 > 0 else float("nan")
    frac_p0 = beats_p0 / total_p0 if total_p0 > 0 else float("nan")
    passed = total_c0 > 0 and frac_c0 >= 0.5 and (total_p0 == 0 or frac_p0 >= 0.5)
    return {
        "pass": bool(passed),
        "frac_graph_beats_c0": round(frac_c0, 3) if _is_finite(frac_c0) else None,
        "frac_graph_beats_p0": round(frac_p0, 3) if _is_finite(frac_p0) else None,
        "total_c0_comparisons": total_c0,
        "total_p0_comparisons": total_p0,
    }


def _a4_baseline_relevance(records: list[dict]) -> dict:
    """
    A4 BASELINE_RELEVANCE: records whether best neural strategy beats B0 (ffill) and B1 (Ridge).
    Pass condition: at least one graph/adapted strategy beats both baselines in >= 50% of comparisons.
    """
    neural_strategies = {"A1", "A2", "A3", "A4"}
    b0_index: dict = {}
    b1_index: dict = {}
    for r in records:
        if r.get("error"):
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"), r.get("mask_key"))
        if r.get("strategy") == "B0":
            b0_index[key] = _get_mae(r)
        elif r.get("strategy") == "B1":
            b1_index[key] = _get_mae(r)

    beats_b0 = 0
    beats_b1 = 0
    beats_both = 0
    total = 0
    for r in records:
        if r.get("strategy") not in neural_strategies or r.get("error"):
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"), r.get("mask_key"))
        nmae = _get_mae(r)
        b0 = b0_index.get(key)
        b1 = b1_index.get(key)
        if nmae is None:
            continue
        total += 1
        if b0 is not None and nmae < b0:
            beats_b0 += 1
        if b1 is not None and nmae < b1:
            beats_b1 += 1
        if b0 is not None and b1 is not None and nmae < b0 and nmae < b1:
            beats_both += 1

    if total == 0:
        return {"pass": False, "note": "no neural records", "beats_both": 0, "total": 0}

    frac_both = beats_both / total
    return {
        "pass": bool(frac_both >= 0.5),
        "frac_beats_b0": round(beats_b0 / total, 3),
        "frac_beats_b1": round(beats_b1 / total, 3),
        "frac_beats_both": round(frac_both, 3),
        "total": total,
        "note": "Informational: records whether neural strategies beat simple baselines",
    }


def _a5_fewshot_efficiency(records: list[dict]) -> dict:
    """
    A5 FEWSHOT_EFFICIENCY: adaptation benefit appears at k_frac <= FEWSHOT_MAX_K.
    i.e., adapted_mae < z0_mae for some k_frac in [0.01, FEWSHOT_MAX_K].
    """
    adapted_strategies = {"A1", "A2", "A3", "A4"}
    z0_index: dict = {}
    for r in records:
        if r.get("strategy") == "Z0" and not r.get("error"):
            key = (r.get("scenario"), r.get("dataset_seed"), r.get("support_seed"), r.get("mask_key"))
            z0_index[key] = _get_mae(r)

    wins_low_k = 0
    total_low_k = 0
    for r in records:
        if r.get("strategy") not in adapted_strategies or r.get("error"):
            continue
        kf = r.get("k_frac") or 0
        if kf <= 0 or kf > FEWSHOT_MAX_K:
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("support_seed"), r.get("mask_key"))
        z0_mae = z0_index.get(key)
        adapted_mae = _get_mae(r)
        if z0_mae is None or adapted_mae is None:
            continue
        total_low_k += 1
        if adapted_mae < z0_mae:
            wins_low_k += 1

    if total_low_k == 0:
        return {"pass": False, "note": f"no records with k_frac <= {FEWSHOT_MAX_K}", "wins": 0, "total": 0}

    frac = wins_low_k / total_low_k
    return {
        "pass": bool(frac >= 0.5),
        "frac_wins_at_low_k": round(frac, 3),
        "k_threshold": FEWSHOT_MAX_K,
        "wins": wins_low_k,
        "total": total_low_k,
    }


def _a6_graph_preservation(records: list[dict]) -> dict:
    """
    A6 GRAPH_PRESERVATION: edge AUC doesn't drop > AUC_DEGRADATION_THRESHOLD after adaptation.
    Checked for all adapted strategies (not Z0/B0/B1).
    """
    excluded = {"Z0", "B0", "B1"}
    fails: list[str] = []
    total = 0
    for r in records:
        if r.get("strategy") in excluded or r.get("error"):
            continue
        auc_change = r.get("auc_change")
        if auc_change is None:
            continue
        total += 1
        if float(auc_change) < -AUC_DEGRADATION_THRESHOLD:
            fails.append(
                f"{r.get('strategy')}/{r.get('scenario')}/k={r.get('k_frac')}: "
                f"auc_change={auc_change:.4f}"
            )

    if total == 0:
        return {"pass": False, "note": "no graph metric records", "n_fail": 0, "total": 0}

    return {
        "pass": len(fails) == 0,
        "n_total": total,
        "n_fail": len(fails),
        "threshold": AUC_DEGRADATION_THRESHOLD,
        "fails": fails[:5],
    }


def _a7_block_robustness(records: list[dict]) -> dict:
    """
    A7 BLOCK_ROBUSTNESS: adaptation benefit (adapted < Z0) holds in block_30 mask,
    not only in mcar_30.
    """
    adapted_strategies = {"A1", "A2", "A3", "A4"}
    z0_block: dict = {}
    for r in records:
        if r.get("strategy") == "Z0" and r.get("mask_key") == "block_30" and not r.get("error"):
            key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"))
            z0_block[key] = _get_mae(r)

    wins = 0
    total = 0
    for r in records:
        if r.get("strategy") not in adapted_strategies or r.get("error"):
            continue
        if r.get("mask_key") != "block_30":
            continue
        if (r.get("k_frac") or 0) <= 0:
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"))
        z0 = z0_block.get(key)
        adapted = _get_mae(r)
        if z0 is None or adapted is None:
            continue
        total += 1
        if adapted < z0:
            wins += 1

    if total == 0:
        return {"pass": False, "note": "no block_30 records", "wins": 0, "total": 0}

    frac = wins / total
    return {
        "pass": bool(frac >= 0.5),
        "frac_wins_block30": round(frac, 3),
        "wins": wins,
        "total": total,
    }


def _a8_replication(records: list[dict]) -> dict:
    """
    A8 REPLICATION: effect (adapted < Z0) in same direction in >= SEED_PASS_FRAC of seeds.
    """
    adapted_strategies = {"A1", "A2", "A3", "A4"}
    z0_index: dict = {}
    for r in records:
        if r.get("strategy") == "Z0" and not r.get("error"):
            key = (r.get("scenario"), r.get("dataset_seed"), r.get("support_seed"), r.get("mask_key"))
            z0_index[key] = _get_mae(r)

    by_seed: dict[int, list[int]] = defaultdict(list)
    for r in records:
        if r.get("strategy") not in adapted_strategies or r.get("error"):
            continue
        if (r.get("k_frac") or 0) <= 0:
            continue
        sseed = r.get("support_seed")
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("support_seed"), r.get("mask_key"))
        z0 = z0_index.get(key)
        adapted = _get_mae(r)
        if z0 is None or adapted is None:
            continue
        by_seed[sseed].append(int(adapted < z0))

    if not by_seed:
        return {"pass": False, "note": "no valid seed comparisons", "n_seeds": 0}

    seed_fracs = {s: sum(v) / len(v) for s, v in by_seed.items()}
    n_pass = sum(1 for f in seed_fracs.values() if f >= 0.5)
    frac_pass = n_pass / len(by_seed)

    return {
        "pass": bool(frac_pass >= SEED_PASS_FRAC),
        "frac_seeds_pass": round(frac_pass, 3),
        "threshold": SEED_PASS_FRAC,
        "n_seeds": len(by_seed),
        "seed_fracs": {str(s): round(f, 3) for s, f in seed_fracs.items()},
    }


def _a9_adapter_value(records: list[dict]) -> dict:
    """
    A9 ADAPTER_VALUE: A2 (adapter+decoder) beats A1 (decoder-only) on same combo.
    """
    a1_index: dict = {}
    a2_index: dict = {}
    for r in records:
        if r.get("error"):
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"), r.get("mask_key"))
        if r.get("strategy") == "A1":
            a1_index[key] = _get_mae(r)
        elif r.get("strategy") == "A2":
            a2_index[key] = _get_mae(r)

    wins = 0
    total = 0
    common = set(a1_index.keys()) & set(a2_index.keys())
    for key in common:
        a1 = a1_index[key]
        a2 = a2_index[key]
        if a1 is None or a2 is None:
            continue
        total += 1
        if a2 < a1:
            wins += 1

    if total == 0:
        return {"pass": False, "note": "no A1/A2 comparisons", "wins": 0, "total": 0}

    frac = wins / total
    return {
        "pass": bool(frac >= 0.5),
        "frac_a2_beats_a1": round(frac, 3),
        "wins": wins,
        "total": total,
    }


def _a10_finetuning_tradeoff(records: list[dict]) -> dict:
    """
    A10 FINETUNING_TRADEOFF: A4 is only preferred if MAE improves AND graph not degraded.
    Checks: A4 MAE < A1 MAE AND A4 graph_preserved=True.
    """
    a1_index: dict = {}
    a4_index: dict = {}
    for r in records:
        if r.get("error"):
            continue
        key = (r.get("scenario"), r.get("dataset_seed"), r.get("k_frac"), r.get("support_seed"), r.get("mask_key"))
        if r.get("strategy") == "A1":
            a1_index[key] = r
        elif r.get("strategy") == "A4":
            a4_index[key] = r

    wins_mae = 0
    wins_both = 0
    total = 0
    common = set(a1_index.keys()) & set(a4_index.keys())
    for key in common:
        r1 = a1_index[key]
        r4 = a4_index[key]
        mae1 = _get_mae(r1)
        mae4 = _get_mae(r4)
        graph_ok = r4.get("graph_preserved", False)
        if mae1 is None or mae4 is None:
            continue
        total += 1
        if mae4 < mae1:
            wins_mae += 1
        if mae4 < mae1 and graph_ok:
            wins_both += 1

    if total == 0:
        return {"pass": False, "note": "no A1/A4 comparisons", "total": 0}

    frac_mae = wins_mae / total
    frac_both = wins_both / total
    return {
        "pass": bool(frac_both >= 0.5),
        "frac_a4_mae_improvement": round(frac_mae, 3),
        "frac_a4_mae_improvement_graph_safe": round(frac_both, 3),
        "total": total,
        "note": "A4 preferred only if BOTH MAE improves and graph not degraded",
    }


# ── Decision logic ─────────────────────────────────────────────────────────────

def _make_decision(gates: dict[str, bool]) -> str:
    a2 = gates.get("A2_adaptation_benefit", False)
    a3 = gates.get("A3_graph_contribution", False)
    a5 = gates.get("A5_fewshot_efficiency", False)
    a6 = gates.get("A6_graph_preservation", False)
    a8 = gates.get("A8_replication", False)
    a9 = gates.get("A9_adapter_value", False)
    a10 = gates.get("A10_finetuning_tradeoff", False)

    if not a6:
        return "GRAPH_PRESERVATION_FAILED"
    if not a2:
        return "FEWSHOT_ADAPTATION_FAILED"
    if a2 and not a5:
        return "FEWSHOT_ADAPTATION_PARTIAL"
    if a2 and a3 and a8 and a9:
        return "ADAPTER_FEWSHOT_SUPPORTED"
    if a2 and a3 and a8 and a10:
        return "FULL_FINETUNING_SUPPORTED"
    if a2 and a3 and a8:
        return "DECODER_ONLY_SUPPORTED"
    return "FEWSHOT_ADAPTATION_PARTIAL"


# ── Main evaluator ─────────────────────────────────────────────────────────────

def evaluate_gates(records: list[dict]) -> dict[str, Any]:
    if not records:
        return {"error": "no records", "gate_version": DEC047_GATE_VERSION}

    report: dict[str, Any] = {
        "gate_version": DEC047_GATE_VERSION,
        "n_records": len(records),
        "strategies_present": sorted({r.get("strategy", "?") for r in records if not r.get("error")}),
    }

    report["A1_safety"] = _a1_safety(records)
    report["A2_adaptation_benefit"] = _a2_adaptation_benefit(records)
    report["A3_graph_contribution"] = _a3_graph_contribution(records)
    report["A4_baseline_relevance"] = _a4_baseline_relevance(records)
    report["A5_fewshot_efficiency"] = _a5_fewshot_efficiency(records)
    report["A6_graph_preservation"] = _a6_graph_preservation(records)
    report["A7_block_robustness"] = _a7_block_robustness(records)
    report["A8_replication"] = _a8_replication(records)
    report["A9_adapter_value"] = _a9_adapter_value(records)
    report["A10_finetuning_tradeoff"] = _a10_finetuning_tradeoff(records)

    gate_keys = [k for k in report if k.startswith("A") and isinstance(report[k], dict) and "pass" in report[k]]
    gates_bool = {k: report[k]["pass"] for k in gate_keys}
    n_pass = sum(gates_bool.values())

    report["summary"] = {
        "gates": gates_bool,
        "n_pass": n_pass,
        "n_total": len(gate_keys),
        "decision": _make_decision(gates_bool),
    }
    return report
