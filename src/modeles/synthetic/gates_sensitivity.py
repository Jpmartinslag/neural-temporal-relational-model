"""
gates_sensitivity.py — PHASE10_SIGNAL_SENSITIVITY gates (DEC-044)

Gates S1-S7 frozen before execution. DO NOT modify after results are available.

S1: Oracle upper bound — oracle_lagged MAE < ffill AND oracle_lagged MAE < no_graph
    (if this fails, the graph oracle provides no imputation benefit)
S2: Learned graph utility — herald_lagged MAE < no_graph AND herald_lagged MAE < herald_lagged_permuted
    (net graph benefit; controls for model capacity)
S3: Edge recovery — mean herald_lagged AUC >= 0.60
    (lagged architecture must recover edge structure above chance)
S4: Structural accuracy — herald_lagged edge_precision > prevalence
    (precision at k=n_true_edges must beat random baseline)
S5: Seed consistency — improvement (herald_lagged < no_graph) holds in >= 2/3 seeds
    per (scenario, config) tuple
S6: Safety — zero NaN or Inf in any imputation MAE; leakage_check passed for all tasks
S7: Monotonicity — mean (no_graph_mae - oracle_lagged_mae) increases from cs_force=low
    to cs_force=high (stronger signal → larger oracle advantage)
    Fail = oracle advantage decreases or reverses as cs_force increases
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
import numpy as np


GATE_VERSION = "sensitivity_gates_v1"
# These thresholds are frozen. Do not modify after 2026-06-13.
S3_AUC_THRESHOLD = 0.60
S4_PREVALENCE_N_SECTORS = 9   # off-diagonal pairs = 72
S5_MIN_SEED_FRACTION = 2 / 3


def load_results(output_dir: Path) -> list[dict]:
    results = []
    for f in sorted(output_dir.glob("sensitivity_*.json")):
        if f.name.startswith("gate_"):
            continue
        try:
            d = json.loads(f.read_text())
            if d.get("manifest_version") == "sensitivity_v1" and "mask_results" in d:
                results.append(d)
        except Exception:
            pass
    return results


def _mae(task: dict, model: str) -> list[float]:
    vals = []
    for mk, mr in task.get("mask_results", {}).items():
        if isinstance(mr, dict) and model in mr and isinstance(mr[model], dict):
            v = mr[model].get("mae")
            if v is not None and not (v != v):
                vals.append(float(v))
    return vals


def _auc(task: dict, model: str) -> list[float]:
    vals = []
    for mk, mr in task.get("mask_results", {}).items():
        if isinstance(mr, dict) and model in mr and isinstance(mr[model], dict):
            v = mr[model].get("edge_auc")
            if v is not None and not (v != v):
                vals.append(float(v))
    return vals


def _prec(task: dict, model: str) -> list[float]:
    vals = []
    for mk, mr in task.get("mask_results", {}).items():
        if isinstance(mr, dict) and model in mr and isinstance(mr[model], dict):
            v = mr[model].get("edge_precision")
            if v is not None and not (v != v):
                vals.append(float(v))
    return vals


def evaluate_gates(results: list[dict]) -> dict:
    if not results:
        return {"error": "no results", "gate_version": GATE_VERSION}

    report = {"gate_version": GATE_VERSION, "n_tasks": len(results)}

    # ── S1: Oracle upper bound ────────────────────────────────────────────────
    s1_fails = []
    for t in results:
        ff = np.mean(_mae(t, "ffill")) if _mae(t, "ffill") else None
        ng = np.mean(_mae(t, "no_graph")) if _mae(t, "no_graph") else None
        ol = np.mean(_mae(t, "oracle_lagged")) if _mae(t, "oracle_lagged") else None
        if ff is None or ng is None or ol is None:
            continue
        if not (ol < ff and ol < ng):
            s1_fails.append({"task_id": t["task_id"], "scenario": t["scenario"], "seed": t["seed"],
                              "cs": t["cs"], "oracle_mae": ol, "ffill_mae": ff, "no_graph_mae": ng})
    s1_pass = len(s1_fails) == 0
    report["S1_oracle_bound"] = {"pass": s1_pass, "n_fail": len(s1_fails), "fails": s1_fails[:5]}

    # ── S2: Learned graph utility ─────────────────────────────────────────────
    s2_fails = []
    for t in results:
        ng = np.mean(_mae(t, "no_graph")) if _mae(t, "no_graph") else None
        hl = np.mean(_mae(t, "herald_lagged")) if _mae(t, "herald_lagged") else None
        hp = np.mean(_mae(t, "herald_lagged_permuted")) if _mae(t, "herald_lagged_permuted") else None
        if ng is None or hl is None or hp is None:
            continue
        if not (hl < ng and hl < hp):
            s2_fails.append({"task_id": t["task_id"], "herald_lagged_mae": hl, "no_graph_mae": ng, "permuted_mae": hp})
    s2_pass = len(s2_fails) == 0
    report["S2_learned_graph_utility"] = {"pass": s2_pass, "n_fail": len(s2_fails), "fails": s2_fails[:5]}

    # ── S3: Edge recovery AUC ≥ 0.60 ─────────────────────────────────────────
    all_aucs = []
    for t in results:
        all_aucs.extend(_auc(t, "herald_lagged"))
    mean_auc = float(np.mean(all_aucs)) if all_aucs else float("nan")
    s3_pass = mean_auc >= S3_AUC_THRESHOLD
    report["S3_edge_recovery"] = {"pass": s3_pass, "mean_auc": round(mean_auc, 4),
                                   "threshold": S3_AUC_THRESHOLD, "n_auc": len(all_aucs)}

    # ── S4: Structural precision > prevalence ─────────────────────────────────
    all_prec = []
    n_true_vals = []
    for t in results:
        all_prec.extend(_prec(t, "herald_lagged"))
        n_true_vals.append(t.get("n_true_relations", 8))
    n_true = float(np.mean(n_true_vals)) if n_true_vals else 8.0
    off_diag = S4_PREVALENCE_N_SECTORS * (S4_PREVALENCE_N_SECTORS - 1)
    prevalence = n_true / off_diag
    mean_prec = float(np.mean(all_prec)) if all_prec else float("nan")
    s4_pass = mean_prec > prevalence
    report["S4_structural_precision"] = {"pass": s4_pass, "mean_precision": round(mean_prec, 4),
                                          "prevalence": round(prevalence, 4)}

    # ── S5: Seed consistency ≥ 2/3 seeds ─────────────────────────────────────
    by_config_scenario: dict[tuple, dict] = defaultdict(lambda: {"seeds": [], "passes": []})
    for t in results:
        ng = np.mean(_mae(t, "no_graph")) if _mae(t, "no_graph") else None
        hl = np.mean(_mae(t, "herald_lagged")) if _mae(t, "herald_lagged") else None
        key = (t["scenario"], t["cs"], t["ar"], t["noise"], t["lag"])
        if ng is not None and hl is not None:
            by_config_scenario[key]["seeds"].append(t["seed"])
            by_config_scenario[key]["passes"].append(int(hl < ng))
    s5_fails = []
    for key, val in by_config_scenario.items():
        n_seeds = len(val["seeds"])
        frac = sum(val["passes"]) / n_seeds if n_seeds > 0 else 0
        if frac < S5_MIN_SEED_FRACTION:
            s5_fails.append({"config": key, "pass_frac": round(frac, 3), "n_seeds": n_seeds})
    s5_pass = len(s5_fails) == 0
    report["S5_seed_consistency"] = {"pass": s5_pass, "n_configs": len(by_config_scenario),
                                      "n_fail_configs": len(s5_fails), "fails": s5_fails[:5]}

    # ── S6: Safety — NaN/Inf/leakage ─────────────────────────────────────────
    s6_nan = 0
    s6_leakage = 0
    for t in results:
        if not t.get("leakage_check", {}).get("passed", True):
            s6_leakage += 1
        for mk, mr in t.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            for model_name, model_res in mr.items():
                if not isinstance(model_res, dict):
                    continue
                for k in ["mae", "rmse"]:
                    v = model_res.get(k)
                    if v is not None:
                        if v != v or abs(v) == float("inf"):
                            s6_nan += 1
    s6_pass = s6_nan == 0 and s6_leakage == 0
    report["S6_safety"] = {"pass": s6_pass, "nan_inf_count": s6_nan, "leakage_count": s6_leakage}

    # ── S7: Monotonicity — oracle advantage grows with cs_force ───────────────
    cs_order = ["low", "original", "high"]
    cs_oracle_gaps = defaultdict(list)
    for t in results:
        cs = t.get("cs")
        if cs not in cs_order:
            continue
        ng = np.mean(_mae(t, "no_graph")) if _mae(t, "no_graph") else None
        ol = np.mean(_mae(t, "oracle_lagged")) if _mae(t, "oracle_lagged") else None
        if ng is not None and ol is not None:
            cs_oracle_gaps[cs].append(ng - ol)  # positive = oracle better than no_graph

    cs_means = {cs: float(np.mean(v)) for cs, v in cs_oracle_gaps.items() if v}
    s7_monotone = True
    s7_detail = {}
    for cs in cs_order:
        s7_detail[cs] = round(cs_means.get(cs, float("nan")), 4)
    if all(cs in cs_means for cs in ["low", "high"]):
        s7_monotone = cs_means["high"] >= cs_means["low"]
    report["S7_monotonicity"] = {"pass": s7_monotone, "oracle_gap_by_cs": s7_detail,
                                  "interpretation": "gap = (no_graph_mae - oracle_lagged_mae)"}

    # ── Summary ───────────────────────────────────────────────────────────────
    gates = {k: report[k]["pass"] for k in report if k.startswith("S") and isinstance(report[k], dict) and "pass" in report[k]}
    n_pass = sum(gates.values())
    report["summary"] = {
        "gates": gates,
        "n_pass": n_pass,
        "n_total": len(gates),
        "decision": "SENSITIVITY_PASS" if n_pass == len(gates) else "SENSITIVITY_PARTIAL",
    }
    return report


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    results = load_results(args.results_dir)
    print(f"Loaded {len(results)} results from {args.results_dir}")
    report = evaluate_gates(results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2))
        print(f"Report written to {args.output}")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
