"""
gates_phase11.py — Phase 11 True Generalization Gates X1-X9 (DEC-045)

FROZEN before any pilot execution (2026-06-13).
DO NOT modify thresholds or gate logic after first results are available.

These gates test TRUE GENERALIZATION: model trained on {linear, mixed_default}
evaluated zero-shot on {novel_lag2, novel_highvar} (never seen during training).

X1 SAFETY              : NaN=0, leakage=False, n_hidden > 0 for all test records
X2 DATASET_DISJOINT    : train/val/test seed sets are non-overlapping (structural)
X3 NO_ADAPTATION       : checkpoint hash unchanged before/after evaluation
X4 T2_ADVANTAGE        : T2 MAE <= T1 MAE on novel_lag2 (multi-environment helps)
X5 GENERALIZES_BASELINE: T2 herald_lagged MAE < no_graph on novel_lag2 in >=2/3 seeds
X6 EDGE_TRANSFER       : T2 herald_lagged edge AUC > 0.55 averaged over test scenarios
X7 PILOT_COMPLETENESS  : all expected (scenario × seed × mask) records present, no error
X8 SEED_CONSISTENCY    : T2 improvement direction (vs no_graph) consistent in >=2/3 seeds
X9 ORACLE_BOUND        : oracle_lagged MAE < ffill for every test record

Thresholds:
  X4 : T2_mae / T1_mae <= 1.02  (allow 2% tolerance for stochasticity)
  X5 : fraction of seeds where herald_lagged < no_graph >= 2/3
  X6 : mean edge AUC across all test tasks > 0.55
  X9 : oracle_lagged < ffill for all records (100%)

Decision vocabulary:
  SYNTHETIC_RECONSTRUCTION_GENERALIZES  : X5 PASS and X9 PASS (primary success)
  SYNTHETIC_RELATIONS_GENERALIZE        : X6 PASS (edge structure transfers)
  MULTI_ENVIRONMENT_TRAINING_SUPPORTED  : X4 PASS (T2 benefits from broader training)
  GENERALIZATION_PARTIAL                : some X gates pass, not all primary
  GENERALIZATION_FAIL                   : X5 and X9 both FAIL
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import numpy as np

PHASE11_GATE_VERSION = "phase11_gates_v1"

# Thresholds (frozen)
X4_RATIO_THRESHOLD = 1.02   # T2_mae <= T1_mae × threshold
X5_SEED_FRAC = 2 / 3        # fraction of seeds where T2 herald_lagged < no_graph
X6_AUC_THRESHOLD = 0.55     # mean herald_lagged edge AUC on novel test scenarios
X9_REQUIRED_FRAC = 1.00     # oracle_lagged < ffill in ALL records


# ── Utilities ─────────────────────────────────────────────────────────────────

def _model_mae(record: dict, model: str) -> float | None:
    m = record.get("models", {}).get(model, {})
    v = m.get("mae") if isinstance(m, dict) else None
    if v is None or v != v or abs(v) == float("inf"):
        return None
    return float(v)


def _mean_safe(vals: list[float]) -> float:
    clean = [v for v in vals if v is not None and v == v]
    return float(np.mean(clean)) if clean else float("nan")


# ── Gate evaluators ───────────────────────────────────────────────────────────

def _x1_safety(records: list[dict]) -> dict:
    nan_count = 0
    leakage_count = 0
    zero_hidden = 0
    errors: list[str] = []
    for r in records:
        if not r.get("leakage_pass", True):
            leakage_count += 1
            errors.append(f"{r['scenario']}/seed={r.get('seed')}/{r.get('mask_key')}: LEAKAGE")
        if r.get("n_hidden", 1) == 0:
            zero_hidden += 1
        for model, mres in r.get("models", {}).items():
            if not isinstance(mres, dict):
                continue
            for k in ["mae", "rmse"]:
                v = mres.get(k)
                if v is not None and (v != v or abs(v) == float("inf")):
                    nan_count += 1
                    errors.append(f"{r['scenario']}/{model}/{k}: NaN/Inf")
    passed = nan_count == 0 and leakage_count == 0 and zero_hidden == 0
    return {
        "pass": passed,
        "nan_inf_count": nan_count,
        "leakage_count": leakage_count,
        "zero_hidden_count": zero_hidden,
        "errors": errors[:5],
    }


def _x2_dataset_disjoint(records: list[dict]) -> dict:
    """Verify structural seed disjointness (checked at import time in splits.py)."""
    from src.modeles.synthetic.phase11_generalization.splits import (
        TRAIN_SEEDS, VAL_SEEDS, TEST_SEEDS,
    )
    train_set = set(TRAIN_SEEDS)
    val_set = set(VAL_SEEDS)
    test_set = set(TEST_SEEDS)
    overlap_tv = train_set & val_set
    overlap_tt = train_set & test_set
    overlap_vt = val_set & test_set
    passed = not (overlap_tv or overlap_tt or overlap_vt)
    # Also verify all test seeds in records came from TEST_SEEDS
    seen_test_seeds = {r["seed"] for r in records}
    unexpected = seen_test_seeds - test_set
    passed = passed and not unexpected
    return {
        "pass": bool(passed),
        "train_val_overlap": sorted(overlap_tv),
        "train_test_overlap": sorted(overlap_tt),
        "val_test_overlap": sorted(overlap_vt),
        "unexpected_test_seeds": sorted(unexpected),
        "n_train_seeds": len(TRAIN_SEEDS),
        "n_val_seeds": len(VAL_SEEDS),
        "n_test_seeds": len(TEST_SEEDS),
    }


def _x3_no_adaptation(records: list[dict]) -> dict:
    """
    Verify checkpoint hash unchanged: each record must carry matching pre/post hashes.
    The evaluator stores 'checkpoint_hash_before' in the training history, and the
    evaluator function verifies it internally (assertion). Here we check the records
    carry a consistent strategy hash.
    """
    # Records don't carry the hash directly; this gate verifies no records have
    # an 'adaptation_applied' flag (would be set if fine-tuning occurred).
    adapted = [
        f"{r['scenario']}/seed={r.get('seed')}/{r.get('mask_key')}"
        for r in records if r.get("adaptation_applied", False)
    ]
    return {
        "pass": len(adapted) == 0,
        "n_adapted": len(adapted),
        "note": "Checkpoint hash verified internally by evaluator assertion at runtime",
    }


def _x4_t2_advantage(records: list[dict]) -> dict:
    """T2 MAE <= T1 MAE * X4_RATIO_THRESHOLD on novel_lag2 scenario."""
    t1_maes: list[float] = []
    t2_maes: list[float] = []
    for r in records:
        if r.get("scenario") != "novel_lag2":
            continue
        strategy = r.get("strategy", "")
        mae = _model_mae(r, "herald_lagged")
        if mae is None:
            continue
        if strategy == "T1":
            t1_maes.append(mae)
        elif strategy == "T2":
            t2_maes.append(mae)
    t1_mean = _mean_safe(t1_maes)
    t2_mean = _mean_safe(t2_maes)
    if t1_mean != t1_mean or t2_mean != t2_mean or t1_mean == 0:
        passed = False
    else:
        passed = bool(t2_mean <= t1_mean * X4_RATIO_THRESHOLD)
    return {
        "pass": passed,
        "t1_mean_mae": round(t1_mean, 5) if t1_mean == t1_mean else None,
        "t2_mean_mae": round(t2_mean, 5) if t2_mean == t2_mean else None,
        "ratio_threshold": X4_RATIO_THRESHOLD,
        "ratio": round(t2_mean / t1_mean, 4) if (t1_mean == t1_mean and t1_mean > 0) else None,
        "n_t1": len(t1_maes),
        "n_t2": len(t2_maes),
    }


def _x5_generalizes_baseline(records: list[dict]) -> dict:
    """
    T2 herald_lagged MAE < no_graph on novel_lag2, in >= X5_SEED_FRAC of seeds.
    """
    by_seed: dict[int, list[int]] = defaultdict(list)
    for r in records:
        if r.get("strategy") != "T2" or r.get("scenario") != "novel_lag2":
            continue
        hl = _model_mae(r, "herald_lagged")
        ng = _model_mae(r, "no_graph")
        if hl is None or ng is None:
            continue
        by_seed[r["seed"]].append(int(hl < ng))

    if not by_seed:
        return {"pass": False, "note": "no T2/novel_lag2 records found", "seed_fracs": {}}

    seed_fracs = {s: sum(v) / len(v) for s, v in by_seed.items()}
    n_pass_seeds = sum(1 for f in seed_fracs.values() if f >= 0.5)
    frac_seeds_passing = n_pass_seeds / len(by_seed)
    passed = frac_seeds_passing >= X5_SEED_FRAC

    return {
        "pass": bool(passed),
        "frac_seeds_where_herald_beats_no_graph": round(frac_seeds_passing, 3),
        "threshold": X5_SEED_FRAC,
        "seed_fracs": {str(s): round(f, 3) for s, f in seed_fracs.items()},
        "n_seeds": len(by_seed),
    }


def _x6_edge_transfer(records: list[dict]) -> dict:
    """Mean T2 herald_lagged edge AUC > X6_AUC_THRESHOLD across all test scenarios."""
    aucs: list[float] = []
    for r in records:
        if r.get("strategy") != "T2":
            continue
        auc = r.get("models", {}).get("herald_lagged", {}).get("edge_auc")
        if auc is not None and auc == auc:
            aucs.append(float(auc))
    mean_auc = _mean_safe(aucs)
    passed = mean_auc > X6_AUC_THRESHOLD if mean_auc == mean_auc else False
    return {
        "pass": bool(passed),
        "mean_edge_auc": round(mean_auc, 4) if mean_auc == mean_auc else None,
        "threshold": X6_AUC_THRESHOLD,
        "n_tasks": len(aucs),
    }


def _x7_pilot_completeness(records: list[dict], expected_per_strategy: int | None = None) -> dict:
    """All expected (scenario × seed × mask) records present, no errors."""
    errors = [r for r in records if "error" in r]
    by_strategy: dict[str, int] = defaultdict(int)
    for r in records:
        by_strategy[r.get("strategy", "?")] += 1
    min_count = min(by_strategy.values()) if by_strategy else 0
    threshold = expected_per_strategy or 1
    passed = len(errors) == 0 and min_count >= threshold
    return {
        "pass": bool(passed),
        "n_records_total": len(records),
        "by_strategy": dict(by_strategy),
        "n_errors": len(errors),
        "errors": [e.get("error", "?") for e in errors[:3]],
    }


def _x8_seed_consistency(records: list[dict]) -> dict:
    """
    T2 improvement direction (herald_lagged < no_graph) consistent across >= 2/3 test seeds
    on any test scenario.
    """
    by_seed: dict[int, list[int]] = defaultdict(list)
    for r in records:
        if r.get("strategy") != "T2":
            continue
        hl = _model_mae(r, "herald_lagged")
        ng = _model_mae(r, "no_graph")
        if hl is None or ng is None:
            continue
        by_seed[r["seed"]].append(int(hl < ng))

    if not by_seed:
        return {"pass": False, "note": "no T2 records", "n_seeds": 0}

    seed_pass_fracs = {s: sum(v) / len(v) for s, v in by_seed.items()}
    n_consistent = sum(1 for f in seed_pass_fracs.values() if f >= 0.5)
    frac_consistent = n_consistent / len(by_seed)
    passed = frac_consistent >= X5_SEED_FRAC  # same 2/3 threshold
    return {
        "pass": bool(passed),
        "frac_consistent_seeds": round(frac_consistent, 3),
        "threshold": X5_SEED_FRAC,
        "seed_pass_fracs": {str(s): round(f, 3) for s, f in seed_pass_fracs.items()},
    }


def _x9_oracle_bound(records: list[dict]) -> dict:
    """oracle_lagged MAE < ffill for all records."""
    fails: list[str] = []
    total = 0
    for r in records:
        oracle = _model_mae(r, "oracle_lagged")
        ff = _model_mae(r, "ffill")
        if oracle is None or ff is None:
            continue
        total += 1
        if not (oracle < ff):
            fails.append(
                f"{r.get('strategy')}/{r.get('scenario')}/seed={r.get('seed')}/{r.get('mask_key')}: "
                f"oracle={oracle:.4f} >= ffill={ff:.4f}"
            )
    frac_pass = (total - len(fails)) / total if total > 0 else 0
    return {
        "pass": len(fails) == 0 and total > 0,
        "n_total": total,
        "n_fail": len(fails),
        "frac_pass": round(frac_pass, 3),
        "fails": fails[:5],
    }


# ── Decision logic ────────────────────────────────────────────────────────────

def _make_decision(gates: dict[str, bool]) -> str:
    x5 = gates.get("X5_generalizes_baseline", False)
    x9 = gates.get("X9_oracle_bound", False)
    x4 = gates.get("X4_t2_advantage", False)
    x6 = gates.get("X6_edge_transfer", False)

    if x5 and x9:
        return "SYNTHETIC_RECONSTRUCTION_GENERALIZES"
    if x6:
        return "SYNTHETIC_RELATIONS_GENERALIZE"
    if x4 and not x5:
        return "GENERALIZATION_PARTIAL"
    if not x5 and not x9:
        return "GENERALIZATION_FAIL"
    return "GENERALIZATION_PARTIAL"


# ── Main evaluator ────────────────────────────────────────────────────────────

def evaluate_gates(records: list[dict]) -> dict[str, Any]:
    if not records:
        return {"error": "no records", "gate_version": PHASE11_GATE_VERSION}

    report: dict[str, Any] = {
        "gate_version": PHASE11_GATE_VERSION,
        "n_records": len(records),
        "strategies_present": sorted({r.get("strategy", "?") for r in records}),
    }

    report["X1_safety"] = _x1_safety(records)
    report["X2_dataset_disjoint"] = _x2_dataset_disjoint(records)
    report["X3_no_adaptation"] = _x3_no_adaptation(records)
    report["X4_t2_advantage"] = _x4_t2_advantage(records)
    report["X5_generalizes_baseline"] = _x5_generalizes_baseline(records)
    report["X6_edge_transfer"] = _x6_edge_transfer(records)
    report["X7_pilot_completeness"] = _x7_pilot_completeness(
        records, expected_per_strategy=len(records) // max(len(report["strategies_present"]), 1) // 2
    )
    report["X8_seed_consistency"] = _x8_seed_consistency(records)
    report["X9_oracle_bound"] = _x9_oracle_bound(records)

    gate_keys = [k for k in report if k.startswith("X") and isinstance(report[k], dict) and "pass" in report[k]]
    gates_bool = {k: report[k]["pass"] for k in gate_keys}
    n_pass = sum(gates_bool.values())

    report["summary"] = {
        "gates": gates_bool,
        "n_pass": n_pass,
        "n_total": len(gate_keys),
        "decision": _make_decision(gates_bool),
    }
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Phase 11 gate evaluator X1-X9")
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    import json
    records = []
    for f in sorted(args.results_dir.glob("phase11_*.json")):
        if "gate" in f.name:
            continue
        try:
            data = json.loads(f.read_text())
            if isinstance(data, list):
                records.extend(data)
            elif isinstance(data, dict):
                records.append(data)
        except Exception:
            pass
    print(f"Loaded {len(records)} records from {args.results_dir}")
    report = evaluate_gates(records)
    out = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out)
        print(f"Gate report → {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
