"""
gates_ofat.py — OFAT sensitivity gates O1-O8 (DEC-044 addendum)

Frozen before any execution. DO NOT modify after first results are available.
These gates are DIAGNOSTIC — they do not alter L1-L8 from Phase 10.

O1 SAFETY         : zero leakage, NaN, Inf across all tasks
O2 GRAPH_SPECIF.  : herald_lagged MAE < no_graph AND < herald_lagged_permuted
O3 EDGE_RECOVERY  : herald_lagged edge AUC >= 0.60 AND AUPRC > prevalence
O4 SEED_REPLICATION: improvement direction consistent in >= 2/3 seeds per (axis, scenario)
O5 MASK_ROBUSTNESS : improvement appears in both MCAR-30 and block-30
O6 MONOTONIC_SIGNAL: increasing cs_force alone does not reduce oracle-vs-no_graph advantage
O7 AR_DIAGNOSIS    : reducing AR alone increases relative graph contribution
O8 ORACLE_CEILING  : oracle_lagged MAE < no_graph for every (config, scenario, seed, mask)

Thresholds frozen 2026-06-13, before any OFAT execution.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

OFAT_GATE_VERSION = "ofat_gates_v1"
O3_AUC_THRESHOLD = 0.60

# ── Loader ────────────────────────────────────────────────────────────────────

def load_results(output_dir: Path) -> list[dict]:
    results = []
    for f in sorted(output_dir.glob("ofat_*.json")):
        if f.name.startswith("gate_"):
            continue
        try:
            d = json.loads(f.read_text())
            if d.get("manifest_version") == "ofat_v1" and "mask_results" in d:
                results.append(d)
        except Exception:
            pass
    return results


# ── Metric extractors ─────────────────────────────────────────────────────────

def _get(task: dict, model: str, metric: str, mask_key: str | None = None) -> list[float]:
    vals = []
    for mk, mr in task.get("mask_results", {}).items():
        if mask_key is not None and mk != mask_key:
            continue
        if not isinstance(mr, dict):
            continue
        m = mr.get(model)
        if not isinstance(m, dict):
            continue
        v = m.get(metric)
        if v is not None and v == v and abs(v) != float("inf"):
            vals.append(float(v))
    return vals


def _mean(vals: list[float]) -> float:
    return float(np.mean(vals)) if vals else float("nan")


# ── Gate evaluators ───────────────────────────────────────────────────────────

def _o1_safety(results: list[dict]) -> dict:
    nan_count = 0
    leakage_count = 0
    errors = []
    for t in results:
        if not t.get("leakage_check", {}).get("passed", True):
            leakage_count += 1
            errors.append(f"{t['ofat_label']}/{t['scenario']}/seed={t['seed']}: LEAKAGE")
        for mk, mr in t.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            if "error" in mr:
                errors.append(f"{t['ofat_label']}/{t['scenario']}/seed={t['seed']}/{mk}: error")
                continue
            for model, model_res in mr.items():
                if not isinstance(model_res, dict):
                    continue
                for k in ["mae", "rmse"]:
                    v = model_res.get(k)
                    if v is not None and (v != v or abs(v) == float("inf")):
                        nan_count += 1
    passed = nan_count == 0 and leakage_count == 0 and not errors
    return {"pass": passed, "nan_inf": nan_count, "leakage": leakage_count, "errors": errors[:5]}


def _o2_graph_specificity(results: list[dict]) -> dict:
    fails = []
    for t in results:
        hl = _mean(_get(t, "herald_lagged", "mae"))
        ng = _mean(_get(t, "no_graph", "mae"))
        hp = _mean(_get(t, "herald_lagged_permuted", "mae"))
        if any(v != v for v in [hl, ng, hp]):
            continue
        if not (hl < ng and hl < hp):
            fails.append({
                "label": t["ofat_label"], "scenario": t["scenario"], "seed": t["seed"],
                "herald_lagged": round(hl, 4), "no_graph": round(ng, 4), "permuted": round(hp, 4),
            })
    return {"pass": len(fails) == 0, "n_fail": len(fails), "fails": fails[:5]}


def _o3_edge_recovery(results: list[dict]) -> dict:
    auc_all, auprc_all, prev_all = [], [], []
    below_auc = []
    below_auprc = []
    for t in results:
        for mk, mr in t.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            hl = mr.get("herald_lagged", {})
            if not isinstance(hl, dict):
                continue
            auc = hl.get("edge_auc")
            auprc = hl.get("edge_auprc")
            prev = hl.get("edge_prevalence")
            if auc is not None and auc == auc:
                auc_all.append(auc)
                if auc < O3_AUC_THRESHOLD:
                    below_auc.append((t["ofat_label"], t["scenario"], t["seed"], mk, round(auc, 3)))
            if auprc is not None and auprc == auprc and prev is not None:
                auprc_all.append(auprc)
                prev_all.append(prev)
                if auprc <= prev:
                    below_auprc.append((t["ofat_label"], t["scenario"], t["seed"], mk,
                                        round(auprc, 3), round(prev, 3)))
    mean_auc = _mean(auc_all)
    mean_auprc = _mean(auprc_all)
    mean_prev = _mean(prev_all)
    auc_pass = mean_auc >= O3_AUC_THRESHOLD
    auprc_pass = mean_auprc > mean_prev if mean_auprc == mean_auprc else False
    return {
        "pass": auc_pass and auprc_pass,
        "mean_auc": round(mean_auc, 4), "auc_threshold": O3_AUC_THRESHOLD,
        "auc_pass": auc_pass, "n_below_auc": len(below_auc), "below_auc_examples": below_auc[:3],
        "mean_auprc": round(mean_auprc, 4), "mean_prevalence": round(mean_prev, 4),
        "auprc_pass": auprc_pass,
    }


def _o4_seed_replication(results: list[dict]) -> dict:
    by_axis_scenario: dict[tuple, dict] = defaultdict(lambda: {"seeds": [], "passes": []})
    for t in results:
        hl = _mean(_get(t, "herald_lagged", "mae"))
        ng = _mean(_get(t, "no_graph", "mae"))
        key = (t["axis"], t["scenario"])
        if hl == hl and ng == ng:
            by_axis_scenario[key]["seeds"].append(t["seed"])
            by_axis_scenario[key]["passes"].append(int(hl < ng))
    fails = []
    for key, val in by_axis_scenario.items():
        n = len(val["seeds"])
        frac = sum(val["passes"]) / n if n > 0 else 0
        if frac < 2 / 3:
            fails.append({"axis_scenario": key, "pass_frac": round(frac, 2), "n_seeds": n})
    return {
        "pass": len(fails) == 0,
        "n_axis_scenario": len(by_axis_scenario),
        "n_fail": len(fails),
        "fails": fails[:5],
    }


def _o5_mask_robustness(results: list[dict]) -> dict:
    by_config: dict[tuple, dict] = defaultdict(lambda: {"mcar": [], "block": []})
    for t in results:
        key = (t["ofat_label"], t["scenario"], t["seed"])
        for mk, mr in t.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            hl = mr.get("herald_lagged", {})
            ng = mr.get("no_graph", {})
            if not isinstance(hl, dict) or not isinstance(ng, dict):
                continue
            hl_mae = hl.get("mae")
            ng_mae = ng.get("mae")
            if hl_mae is None or ng_mae is None:
                continue
            mtype = mr.get("mask_type", mk.split("_")[0])
            if mtype == "mcar":
                by_config[key]["mcar"].append(int(hl_mae < ng_mae))
            elif mtype == "block":
                by_config[key]["block"].append(int(hl_mae < ng_mae))
    fails = []
    for key, val in by_config.items():
        mcar_ok = any(v for v in val["mcar"]) if val["mcar"] else None
        block_ok = any(v for v in val["block"]) if val["block"] else None
        if mcar_ok is False or block_ok is False:
            fails.append({"config": key, "mcar_any_pass": mcar_ok, "block_any_pass": block_ok})
    return {"pass": len(fails) == 0, "n_fail": len(fails), "fails": fails[:5]}


def _o6_monotonic_signal(results: list[dict]) -> dict:
    cs_gaps: dict[str, list[float]] = defaultdict(list)
    for t in results:
        cs = t.get("cs")
        if cs not in ("low", "original", "high"):
            continue
        if t.get("axis") not in ("none", "A_cs"):
            continue  # only reference and A-axis tasks
        ol = _mean(_get(t, "oracle_lagged", "mae"))
        ng = _mean(_get(t, "no_graph", "mae"))
        if ol == ol and ng == ng:
            cs_gaps[cs].append(ng - ol)
    means = {k: _mean(v) for k, v in cs_gaps.items()}
    # Monotone: gap(high) >= gap(original) >= gap(low)
    ordered = [means.get("low"), means.get("original"), means.get("high")]
    valid = [v for v in ordered if v is not None and v == v]
    monotone = all(valid[i] <= valid[i + 1] for i in range(len(valid) - 1)) if len(valid) >= 2 else True
    return {
        "pass": monotone,
        "oracle_gap_by_cs": {k: round(v, 4) for k, v in means.items()},
        "interpretation": "gap = no_graph_mae - oracle_lagged_mae (higher = more oracle benefit)",
        "note": "only A_cs axis and reference tasks included",
    }


def _o7_ar_diagnosis(results: list[dict]) -> dict:
    ar_gaps: dict[str, list[float]] = defaultdict(list)
    for t in results:
        ar = t.get("ar")
        if ar not in ("low", "original", "high"):
            continue
        if t.get("axis") not in ("none", "B_ar"):
            continue  # only reference and B-axis tasks
        hl = _mean(_get(t, "herald_lagged", "mae"))
        ng = _mean(_get(t, "no_graph", "mae"))
        ff = _mean(_get(t, "ffill", "mae"))
        if hl == hl and ng == ng and ff == ff:
            # Relative graph contribution: (no_graph - herald_lagged) / no_graph
            rel = (ng - hl) / ng if ng != 0 else float("nan")
            ar_gaps[ar].append(rel)
    means = {k: _mean(v) for k, v in ar_gaps.items()}
    # Expectation: reducing AR (low) increases relative graph contribution
    low_val = means.get("low")
    orig_val = means.get("original")
    if low_val is not None and orig_val is not None and low_val == low_val and orig_val == orig_val:
        confirmed = bool(low_val > orig_val)
    else:
        confirmed = None
    return {
        "pass": confirmed is not False,
        "relative_graph_contrib_by_ar": {k: round(v, 4) for k, v in means.items()},
        "ar_low_increases_contribution": confirmed,
        "interpretation": "relative contribution = (no_graph - herald_lagged) / no_graph",
    }


def _o8_oracle_ceiling(results: list[dict]) -> dict:
    fails = []
    for t in results:
        for mk, mr in t.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            ol = mr.get("oracle_lagged", {})
            ng = mr.get("no_graph", {})
            if not isinstance(ol, dict) or not isinstance(ng, dict):
                continue
            ol_mae = ol.get("mae")
            ng_mae = ng.get("mae")
            if ol_mae is None or ng_mae is None:
                continue
            if not (ol_mae < ng_mae):
                fails.append({
                    "label": t["ofat_label"], "scenario": t["scenario"],
                    "seed": t["seed"], "mask": mk,
                    "oracle_mae": round(ol_mae, 4), "no_graph_mae": round(ng_mae, 4),
                })
    return {"pass": len(fails) == 0, "n_fail": len(fails), "fails": fails[:5]}


# ── Main evaluator ────────────────────────────────────────────────────────────

def evaluate_gates(results: list[dict]) -> dict:
    if not results:
        return {"error": "no results", "gate_version": OFAT_GATE_VERSION}
    report: dict[str, Any] = {
        "gate_version": OFAT_GATE_VERSION,
        "n_tasks": len(results),
    }
    report["O1_safety"] = _o1_safety(results)
    report["O2_graph_specificity"] = _o2_graph_specificity(results)
    report["O3_edge_recovery"] = _o3_edge_recovery(results)
    report["O4_seed_replication"] = _o4_seed_replication(results)
    report["O5_mask_robustness"] = _o5_mask_robustness(results)
    report["O6_monotonic_signal"] = _o6_monotonic_signal(results)
    report["O7_ar_diagnosis"] = _o7_ar_diagnosis(results)
    report["O8_oracle_ceiling"] = _o8_oracle_ceiling(results)
    gates = {k: report[k]["pass"] for k in report if k.startswith("O") and isinstance(report[k], dict) and "pass" in report[k]}
    n_pass = sum(gates.values())
    report["summary"] = {
        "gates": gates,
        "n_pass": n_pass,
        "n_total": len(gates),
        "decision": "OFAT_PASS" if n_pass == len(gates) else "OFAT_PARTIAL",
    }
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser(description="OFAT gate evaluator O1-O8")
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    results = load_results(args.results_dir)
    print(f"Loaded {len(results)} OFAT results from {args.results_dir}")
    report = evaluate_gates(results)
    out_text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out_text)
        print(f"Gate report → {args.output}")
    else:
        print(out_text)


if __name__ == "__main__":
    main()
