"""P6_DDEG_S1 HPC result auditor.

Scans hpc_results/dual_graph_s1/raw/ for the 275 expected JSON outputs,
verifies completeness, health, and leakage, then runs the frozen gate.

Usage:
    python hpc/phase6_dynamic_dual_graph/scripts/audit_dual_graph_hpc_results.py \\
        --results-dir hpc_results/dual_graph_s1
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.modeles.train_dual_graph_experiment import (
    CONTROL_ORDER,
    GATE,
    aggregate,
    apply_gate,
    atomic_write_json,
)
from hpc.phase6_dynamic_dual_graph.scripts.run_dual_graph_task import (
    FOLDS,
    SEEDS,
    decode_task,
)

EXPECTED_TOTAL = 275  # 5 × 11 × 5


def _has_nonfinite(obj) -> bool:
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, (list, tuple)):
        return any(_has_nonfinite(v) for v in obj)
    if isinstance(obj, dict):
        return any(_has_nonfinite(v) for v in obj.values())
    return False


def load_results(raw_dir: Path) -> tuple[list[dict], list[str]]:
    """Load all JSON results; return (results, errors)."""
    results, errors = [], []
    for p in raw_dir.glob("*.json"):
        try:
            r = json.loads(p.read_text())
            results.append(r)
        except Exception as e:
            errors.append(f"PARSE_ERROR {p.name}: {e}")
    return results, errors


def build_expected_keys() -> set[str]:
    return {
        f"{ctrl}__fr{fold}__seed{seed}.json"
        for fold in FOLDS
        for ctrl in CONTROL_ORDER
        for seed in SEEDS
    }


def audit(results_dir: Path, write_summary: bool = True) -> dict:
    raw_dir = results_dir / "raw"
    if not raw_dir.exists():
        print(f"ERROR: raw directory not found: {raw_dir}")
        sys.exit(1)

    results, parse_errors = load_results(raw_dir)
    expected_keys = build_expected_keys()
    present_keys = {p.name for p in raw_dir.glob("*.json")}

    missing = sorted(expected_keys - present_keys)
    extra = sorted(present_keys - expected_keys)

    print(f"\n==== P6_DDEG_S1 HPC Result Audit ====")
    print(f"Results dir: {results_dir}")
    print(f"Expected:    {EXPECTED_TOTAL} outputs")
    print(f"Present:     {len(present_keys)}")
    print(f"Parsed OK:   {len(results)}")
    print(f"Missing:     {len(missing)}")
    print(f"Extra:       {len(extra)}")
    print(f"Parse errors: {len(parse_errors)}")

    if parse_errors:
        print("\nParse errors:")
        for e in parse_errors:
            print(f"  {e}")

    # ── per-result health checks ──────────────────────────────────────────
    health_errors = []
    leakage_errors = []
    for r in results:
        fname = f"{r.get('control')}__fr{r.get('fold')}__seed{r.get('seed')}.json"

        if r.get("status") != "ok":
            health_errors.append(f"status={r.get('status')} {fname}")

        if _has_nonfinite(r.get("metrics", {})):
            health_errors.append(f"NaN/Inf in metrics {fname}")

        la = r.get("leakage_audit", {})
        if not la.get("leakage_ok"):
            leakage_errors.append(
                f"leakage_ok=False {fname}: {la}")
        else:
            # Prove temporal ordering.
            train = la.get("train_years", [])
            val = la.get("val_year")
            outer = la.get("outer_year")
            if train and val and outer:
                if max(train) >= val:
                    leakage_errors.append(
                        f"max_train={max(train)} >= val={val} in {fname}")
                if val >= outer:
                    leakage_errors.append(
                        f"val={val} >= outer={outer} in {fname}")

    # ── commit + hyperparameter consistency ──────────────────────────────
    commits = {r.get("git_commit") for r in results if r.get("git_commit")}
    if len(commits) > 1:
        print(f"\nWARN: multiple git commits found: {commits}")

    # ── print health summary ──────────────────────────────────────────────
    print(f"\nHealth errors:   {len(health_errors)}")
    for e in health_errors[:20]:
        print(f"  {e}")

    print(f"Leakage errors:  {len(leakage_errors)}")
    for e in leakage_errors[:20]:
        print(f"  {e}")

    completeness_ok = (len(missing) == 0 and len(extra) == 0
                       and len(parse_errors) == 0)
    health_ok = len(health_errors) == 0
    leakage_ok = len(leakage_errors) == 0
    all_ok = completeness_ok and health_ok and leakage_ok

    if missing:
        print(f"\nMissing outputs (first 20):")
        for m in missing[:20]:
            print(f"  {m}")
        # Compute missing task IDs for re-launch.
        task_ids = []
        for fname in missing:
            parts = fname.replace(".json", "").split("__")
            if len(parts) == 3:
                ctrl = parts[0]
                fold = int(parts[1].replace("fr", ""))
                seed = int(parts[2].replace("seed", ""))
                try:
                    from hpc.phase6_dynamic_dual_graph.scripts.run_dual_graph_task import encode_task
                    task_ids.append(encode_task(fold, ctrl, seed))
                except Exception:
                    pass
        if task_ids:
            print(f"\nMissing task IDs (for --array re-launch):")
            print(f"  {','.join(map(str, sorted(task_ids)))}")
            if len(task_ids) <= 50:
                ranges = _to_slurm_range(sorted(task_ids))
                print(f"  Slurm range: {ranges}")

    if not all_ok:
        print("\nAUDIT INCOMPLETE — gate not applied. Fix errors first.")
        return {"audit_ok": False, "missing": missing, "health_errors": health_errors,
                "leakage_errors": leakage_errors}

    # ── aggregate + gate ──────────────────────────────────────────────────
    print("\n==== Aggregating results ====")
    agg = aggregate(results, CONTROL_ORDER, FOLDS)

    print("\n==== Applying fail-closed gate ====")
    gate_result = apply_gate(agg, FOLDS, GATE)

    print(f"\nGate decision: {gate_result['decision']}")
    print("Criteria:")
    for k, v in gate_result["criteria"].items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"Jaccard: {gate_result.get('jaccard_value')}")

    # ── per-fold/control MAE summary ─────────────────────────────────────
    print("\n==== MAE by fold (mean over seeds) ====")
    header = f"{'control':<32}" + "".join(f"{y:>8}" for y in FOLDS)
    print(header)
    for ctrl in CONTROL_ORDER:
        row = f"{ctrl:<32}"
        for fold in FOLDS:
            v = agg.get(ctrl, {}).get("by_fold", {}).get(str(fold), {}).get("mae")
            row += f"{v:>8.4f}" if v is not None else f"{'—':>8}"
        print(row)

    # ── Jaccard by control ────────────────────────────────────────────────
    print("\n==== Seed Jaccard by fold (dual C5) ====")
    for fold in FOLDS:
        v = agg.get("C5_dual", {}).get("by_fold", {}).get(str(fold), {}).get("seed_jaccard")
        print(f"  fold {fold}: {v:.4f}" if v is not None else f"  fold {fold}: —")

    # ── without 2021 ─────────────────────────────────────────────────────
    folds_no2021 = [f for f in FOLDS if f != 2021]
    gate_no2021 = apply_gate(agg, folds_no2021, GATE)
    print(f"\nGate without 2021: {gate_no2021['decision']}")

    summary = {
        "audit_ok": True,
        "total_results": len(results),
        "gate": gate_result,
        "gate_no2021": gate_no2021,
        "aggregated": agg,
        "git_commits": sorted(commits),
        "missing": [],
        "health_errors": [],
        "leakage_errors": [],
    }

    if write_summary:
        out = results_dir / "audit_summary.json"
        atomic_write_json(out, summary)
        print(f"\nSummary written to {out}")

    return summary


def _to_slurm_range(ids: list[int]) -> str:
    """Convert sorted list of ints to compact Slurm array range string."""
    if not ids:
        return ""
    ranges = []
    start = end = ids[0]
    for i in ids[1:]:
        if i == end + 1:
            end = i
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
            start = end = i
    ranges.append(str(start) if start == end else f"{start}-{end}")
    return ",".join(ranges)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P6_DDEG_S1 HPC result auditor")
    parser.add_argument("--results-dir", type=Path,
                        default=BASE / "hpc_results/dual_graph_s1",
                        help="Root directory containing raw/ subdirectory")
    parser.add_argument("--no-write", action="store_true",
                        help="Do not write audit_summary.json")
    args = parser.parse_args()

    summary = audit(args.results_dir, write_summary=not args.no_write)
    sys.exit(0 if summary.get("audit_ok") else 1)
