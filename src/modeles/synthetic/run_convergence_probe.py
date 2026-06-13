"""
run_convergence_probe.py

Targeted convergence probe for DEC-041: diagnose G3 block-masking failure
in linear/seed=123 from the DEC-040 pilot.

Runs linear/seed=123 at 200, 300, and 500 epochs using the same pilot config
(20T x 7S x 16Y, PILOT_SCENARIOS["linear"], mask_levels=[10, 30]).

Does NOT modify thresholds, architecture, learning rate, dropout, or data.
Does NOT run the full benchmark array.

Usage:
    python src/modeles/synthetic/run_convergence_probe.py
    python src/modeles/synthetic/run_convergence_probe.py \\
        --output-dir data/processed/synthetic_benchmark/convergence_probe

Outputs:
    <output-dir>/epochs_200/linear_seed00123.json
    <output-dir>/epochs_300/linear_seed00123.json
    <output-dir>/epochs_500/linear_seed00123.json
    <output-dir>/epochs_200_det2/linear_seed00123.json   (determinism re-run)
    <output-dir>/convergence_summary.json                (G3 table + verdict)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from pathlib import Path

# ── Project root on path ──────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO))

from src.data.synthetic.generate_herald_synthetic import (
    PILOT_SCENARIOS,
    BENCHMARK_MASK_TYPES,
)
from src.modeles.synthetic.run_full_benchmark import run_task

# ── Probe configuration (frozen — do not change after first run) ──────────────
PROBE_TASK = {
    "task_id": 1,
    "scenario": "linear",
    "seed": 123,
    "output_file": "linear_seed00123.json",
}
PROBE_MASK_LEVELS = [10, 30]  # same as pilot (not 50%)
PROBE_MASK_TYPES = BENCHMARK_MASK_TYPES  # mcar, mar, block
EPOCH_BUDGETS = [200, 300, 500]
SCENARIO_REGISTRY = PILOT_SCENARIOS  # 20T × 7S × 16Y


def _load_result(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _g3_margins(result: dict) -> dict[str, dict]:
    """Per-mask G3 margin: perm_mae - herald_mae (positive = PASS)."""
    margins = {}
    for mask_combo, bl in result["baselines"].items():
        if not isinstance(bl, dict):
            continue
        hg = bl.get("herald_graph", {})
        hp = bl.get("herald_permuted", {})
        hg_mae = hg.get("mae")
        hp_mae = hp.get("mae")
        if hg_mae is None or hp_mae is None:
            continue
        margin = hp_mae - hg_mae
        margins[mask_combo] = {
            "herald_mae": hg_mae,
            "perm_mae": hp_mae,
            "margin": margin,
            "g3_pass": bool(margin >= 0),
        }
    return margins


_NON_DETERMINISTIC_METRICS = {"train_s"}  # wall-clock time varies between runs


def _determinism_check(r1: dict, r2: dict, tol: float = 1e-6) -> tuple[bool, list[str]]:
    """Compare two runs of the same config; return (ok, list_of_failures).

    Excludes wall-clock metrics (train_s) which are inherently non-deterministic.
    """
    failures = []
    for mask_combo, bl1 in r1["baselines"].items():
        if not isinstance(bl1, dict):
            continue
        bl2 = r2["baselines"].get(mask_combo, {})
        for model, metrics1 in bl1.items():
            if not isinstance(metrics1, dict):
                continue
            metrics2 = bl2.get(model, {}) if isinstance(bl2, dict) else {}
            for metric, v1 in metrics1.items():
                if metric in _NON_DETERMINISTIC_METRICS:
                    continue
                if not isinstance(v1, (int, float)):
                    continue
                v2 = metrics2.get(metric)
                if v2 is None:
                    continue
                diff = abs(float(v1) - float(v2))
                if diff > tol:
                    failures.append(f"{mask_combo}/{model}/{metric}: diff={diff:.2e}")
    return len(failures) == 0, failures


def _all_g3_pass(margins: dict) -> bool:
    return all(v["g3_pass"] for v in margins.values())


def _mean_g3_margin(margins: dict) -> float:
    import numpy as np
    return float(np.mean([v["margin"] for v in margins.values()]))


def run_probe(output_dir: Path, verbose: bool = True) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    epoch_results: dict[int, dict] = {}

    # ── Run each epoch budget ─────────────────────────────────────────────────
    for n_epochs in EPOCH_BUDGETS:
        ep_dir = output_dir / f"epochs_{n_epochs}"
        ep_dir.mkdir(parents=True, exist_ok=True)
        out_path = ep_dir / PROBE_TASK["output_file"]

        if verbose:
            print(f"\n{'=' * 60}")
            print(f"  Convergence probe: linear/seed=123  epochs={n_epochs}")
            print(f"  Output: {out_path}")

        tracemalloc.start()
        t0 = time.time()

        run_task(
            PROBE_TASK,
            ep_dir,
            n_epochs,
            SCENARIO_REGISTRY,
            PROBE_MASK_TYPES,
            PROBE_MASK_LEVELS,
            verbose=verbose,
            resume=False,  # always re-run; never skip
        )

        elapsed = round(time.time() - t0, 1)
        _, peak_mb = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak_mb / 1024 / 1024

        result = _load_result(out_path)
        margins = _g3_margins(result)
        leakage_ok = result.get("leakage_check", {}).get("passed", False)

        epoch_results[n_epochs] = {
            "result": result,
            "margins": margins,
            "elapsed_s": elapsed,
            "peak_mb": round(peak_mb, 1),
            "leakage_pass": leakage_ok,
            "g3_all_pass": _all_g3_pass(margins),
            "g3_mean_margin": _mean_g3_margin(margins),
        }

        if verbose:
            print(f"\n  Elapsed: {elapsed:.1f}s  |  Peak RAM: {peak_mb:.0f} MB  "
                  f"|  Leakage: {'PASS' if leakage_ok else 'FAIL'}")
            print(f"  G3 margins:")
            for mk in sorted(margins):
                m = margins[mk]
                flag = "PASS" if m["g3_pass"] else "FAIL"
                print(f"    {mk:10s}  herald={m['herald_mae']:.4f}  "
                      f"perm={m['perm_mae']:.4f}  Δ={m['margin']:+.4f}  [{flag}]")

    # ── Determinism check (re-run 200 epochs) ────────────────────────────────
    if verbose:
        print(f"\n{'=' * 60}")
        print("  Determinism check: re-running 200 epochs ...")

    det_dir = output_dir / "epochs_200_det2"
    det_dir.mkdir(parents=True, exist_ok=True)
    run_task(
        PROBE_TASK, det_dir, 200,
        SCENARIO_REGISTRY, PROBE_MASK_TYPES, PROBE_MASK_LEVELS,
        verbose=False, resume=False,
    )
    r_det2 = _load_result(det_dir / PROBE_TASK["output_file"])
    r_det1 = epoch_results[200]["result"]
    det_ok, det_failures = _determinism_check(r_det1, r_det2)

    if verbose:
        if det_ok:
            print("  Determinism: PASS (all metrics identical to tol=1e-6)")
        else:
            print(f"  Determinism: FAIL ({len(det_failures)} differences)")
            for f in det_failures[:10]:
                print(f"    {f}")

    # ── G3 verdict ────────────────────────────────────────────────────────────
    # Rules (per user instruction):
    # - G3_CONVERGENCE_CONFIRMED: 300 or 500 passes reproducibly without retrospective selection
    # - G3_NOT_CONFIRMED: still fails, oscillates, or depends on retrospective selection
    # - "500 passes only because chosen after seeing 200/300" → sensitivity note, not validation

    passes_at_300 = epoch_results[300]["g3_all_pass"]
    passes_at_500 = epoch_results[500]["g3_all_pass"]

    # A budget is "reproducible" if it passes AND it was pre-specified before seeing results.
    # 200 is the original pilot budget (pre-specified). 300 and 500 were also pre-specified
    # in this probe BEFORE running — so both are valid evaluation points.
    # However, only passing at BOTH 300 AND 500 warrants CONFIRMED (not just one).

    if passes_at_300 and passes_at_500:
        g3_verdict = "G3_CONVERGENCE_CONFIRMED"
        g3_detail = (
            "G3 passes at both 300 and 500 epochs (both pre-specified, non-retrospective). "
            "Block masking failure at 200 epochs was a convergence artifact."
        )
    elif not passes_at_300 and passes_at_500:
        g3_verdict = "G3_NOT_CONFIRMED"
        g3_detail = (
            "G3 passes at 500 epochs but fails at 300. "
            "Epoch budget was not pre-specified independently; result is sensitive to budget selection. "
            "Records as convergence sensitivity, not independent validation."
        )
    elif passes_at_300 and not passes_at_500:
        g3_verdict = "G3_NOT_CONFIRMED"
        g3_detail = (
            "G3 passes at 300 but fails at 500. Result is not monotonically improving — "
            "oscillation detected. Not confirmed."
        )
    else:
        g3_verdict = "G3_NOT_CONFIRMED"
        g3_detail = (
            "G3 fails at both 300 and 500 epochs. Block masking failure is structural, "
            "not a convergence artifact."
        )

    # ── Calibration note (G4 — frozen FAIL) ──────────────────────────────────
    cal_vals = []
    for ne in EPOCH_BUDGETS:
        for mk, bl in epoch_results[ne]["result"]["baselines"].items():
            if isinstance(bl, dict) and "herald_graph" in bl:
                c = bl["herald_graph"].get("calibration_90")
                if c is not None:
                    cal_vals.append(c)
    import numpy as np
    mean_cal = float(np.nanmean(cal_vals)) if cal_vals else float("nan")
    g4_note = (
        f"G4 (cal90 ≥ 0.80): FAIL across all epoch budgets (mean={mean_cal:.3f}). "
        "MC Dropout is systematically overconfident. "
        "This task does NOT change MC Dropout. "
        "Conformal calibration is the designated remedy (see contract); not implemented here."
    )

    # ── Print final table ─────────────────────────────────────────────────────
    if verbose:
        print(f"\n{'=' * 60}")
        print("  G3 Summary Table (herald vs permuted MAE)")
        print(f"  {'mask':10s}  {'200ep':>22s}  {'300ep':>22s}  {'500ep':>22s}")
        print(f"  {'-'*10}  {'-'*22}  {'-'*22}  {'-'*22}")
        mask_combos = sorted(epoch_results[200]["margins"].keys())
        for mk in mask_combos:
            row = f"  {mk:10s}"
            for ne in EPOCH_BUDGETS:
                m = epoch_results[ne]["margins"].get(mk, {})
                mg = m.get("margin", float("nan"))
                flag = "PASS" if m.get("g3_pass") else "FAIL"
                row += f"  Δ={mg:+.4f} [{flag}]   "
            print(row)
        print()
        print(f"  G3 all-pass: 200ep={epoch_results[200]['g3_all_pass']}  "
              f"300ep={passes_at_300}  500ep={passes_at_500}")
        print(f"\n  VERDICT: {g3_verdict}")
        print(f"  {g3_detail}")
        print(f"\n  G4 NOTE: {g4_note}")
        print()

    # ── Write summary ─────────────────────────────────────────────────────────
    summary = {
        "probe_task": PROBE_TASK,
        "probe_config": {
            "scenario_registry": "PILOT_SCENARIOS (20T x 7S x 16Y)",
            "mask_types": PROBE_MASK_TYPES,
            "mask_levels": PROBE_MASK_LEVELS,
            "epoch_budgets": EPOCH_BUDGETS,
        },
        "determinism": {
            "pass": det_ok,
            "failures": det_failures[:20],
        },
        "epoch_results": {
            str(ne): {
                "elapsed_s": epoch_results[ne]["elapsed_s"],
                "peak_mb": epoch_results[ne]["peak_mb"],
                "leakage_pass": epoch_results[ne]["leakage_pass"],
                "g3_all_pass": epoch_results[ne]["g3_all_pass"],
                "g3_mean_margin": epoch_results[ne]["g3_mean_margin"],
                "g3_margins": epoch_results[ne]["margins"],
            }
            for ne in EPOCH_BUDGETS
        },
        "g3_verdict": g3_verdict,
        "g3_detail": g3_detail,
        "g4_note": g4_note,
        "g4_mean_cal90": round(mean_cal, 4),
    }

    summary_path = output_dir / "convergence_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print(f"  Summary written to {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Convergence probe for DEC-041 G3 diagnosis")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/synthetic_benchmark/convergence_probe"),
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    summary = run_probe(args.output_dir, verbose=not args.quiet)

    verdict = summary["g3_verdict"]
    print(f"\nFinal verdict: {verdict}")
    return 0 if verdict == "G3_CONVERGENCE_CONFIRMED" else 1


if __name__ == "__main__":
    sys.exit(main())
