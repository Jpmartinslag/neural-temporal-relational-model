"""
run_dec051.py — CLI runner for DEC-051 Stable Objective Audit.

Usage:
  python -m src.modeles.synthetic.phase15_stable_objective.run_dec051 \
      --output-dir data/processed/synthetic_benchmark/phase15_stable_objective \
      --device cpu \
      --n-datasets 50

Steps:
  1. Pretrain 5 variants × 3 budgets (cumulative: 30→75→150)
  2. Evaluate zero-shot on all EVAL_SCENARIOS × EVAL_MASKS × EVAL_SEEDS
  3. Negative audit (NT1-NT6) on TEMPORAL_MASKED_NLL_CLAMPED@75 checkpoint
  4. Select top-2 variants by val_loss (NOT by test)
  5. Run few-shot evaluation on top-2 variants
  6. Evaluate all gates V1-V10
  7. Write JSON summary + gate report
  8. STOP if any gate = FAIL (note in output; do not auto-proceed to 300 epochs)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from src.modeles.synthetic.phase15_stable_objective.pretrain_runner_v2 import (
    PRETRAIN_VARIANTS,
    EPOCH_BUDGETS,
    run_budget_grid,
)
from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import (
    evaluate_zero_shot,
    evaluate_few_shot,
    aggregate_zero_shot,
    aggregate_few_shot,
    select_top2_variants,
    EVAL_SEEDS,
    FEWSHOT_K_FRACS,
)
from src.modeles.synthetic.phase15_stable_objective.fewshot_audit import (
    run_all_negative_tests,
)
from src.modeles.synthetic.phase15_stable_objective.gates_dec051 import (
    evaluate_all_gates,
    format_gate_report,
    GateResult,
)


def _result_to_dict(r) -> dict:
    return r._asdict() if hasattr(r, "_asdict") else dict(r)


def _save_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically via temp file."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(path)


def _load_or_empty(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def main(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)

    device = args.device
    n_datasets = args.n_datasets
    t_start = time.time()

    print(f"[DEC-051] Output: {output_dir}")
    print(f"[DEC-051] Device: {device}, n_datasets: {n_datasets}")
    print(f"[DEC-051] Variants: {PRETRAIN_VARIANTS}")
    print(f"[DEC-051] Budgets: {EPOCH_BUDGETS}")
    print(f"[DEC-051] Eval seeds (FROZEN): {EVAL_SEEDS}")

    # ── Step 1: Pretraining ─────────────────────────────────────────────────
    print("\n[Step 1] Pretraining all variants × 3 budgets...")
    pretrain_results: dict[str, dict[int, dict]] = {}
    checkpoint_manifest: dict[str, dict] = {}

    for variant in PRETRAIN_VARIANTS:
        print(f"  Variant: {variant}")
        if variant == "NO_PRETRAINING":
            # Produce a checkpoint for each budget (same weights)
            from src.modeles.synthetic.phase15_stable_objective.pretrain_runner_v2 import (
                run_pretraining,
            )
            per_budget = {b: run_pretraining(variant, b, checkpoint_dir, device) for b in EPOCH_BUDGETS}
        else:
            per_budget = run_budget_grid(
                variant=variant,
                output_dir=checkpoint_dir,
                device=device,
                n_datasets=n_datasets,
                epoch_budgets=EPOCH_BUDGETS,
            )
        pretrain_results[variant] = per_budget

        for budget, res in per_budget.items():
            key = f"{variant}_ep{budget}"
            checkpoint_manifest[key] = {
                "checkpoint_path": res["checkpoint_path"],
                "checkpoint_hash": res["checkpoint_hash"],
                "best_epoch": res["best_epoch"],
                "best_val_loss": res["best_val_loss"],
                "runtime_s": res["runtime_s"],
                "heads_path": res.get("heads_path"),
            }
        print(f"    Done: budgets={list(per_budget.keys())}")

    _save_atomic(output_dir / "checkpoint_manifest.json", checkpoint_manifest)
    print(f"  Manifest saved: {output_dir / 'checkpoint_manifest.json'}")

    # ── Step 2: Zero-shot evaluation ────────────────────────────────────────
    print("\n[Step 2] Zero-shot evaluation...")
    all_zs_results = []
    for variant in PRETRAIN_VARIANTS:
        for budget in EPOCH_BUDGETS:
            key = f"{variant}_ep{budget}"
            ckpt = checkpoint_manifest[key]["checkpoint_path"]
            heads_path = checkpoint_manifest[key].get("heads_path")
            print(f"  {key} ...")
            results = evaluate_zero_shot(ckpt, heads_path, variant, budget, device)
            all_zs_results.extend(results)

    zs_summary = aggregate_zero_shot(all_zs_results)
    _save_atomic(
        output_dir / "zero_shot_results.json",
        {"results": [_result_to_dict(r) for r in all_zs_results],
         "summary": {str(k): v for k, v in zs_summary.items()}}
    )
    print(f"  Zero-shot saved: {len(all_zs_results)} results")

    # ── Step 3: Few-shot negative audit ─────────────────────────────────────
    print("\n[Step 3] Few-shot negative audit (NT1-NT6)...")
    # Use TEMPORAL_MASKED_NLL_CLAMPED@75 as the primary checkpoint
    nt_ckpt_key = "TEMPORAL_MASKED_NLL_CLAMPED_ep75"
    if nt_ckpt_key not in checkpoint_manifest:
        # Fall back to first available checkpoint
        nt_ckpt_key = list(checkpoint_manifest.keys())[0]
        print(f"  [WARN] {nt_ckpt_key!r} not found, using {nt_ckpt_key!r}")
    nt_ckpt = checkpoint_manifest[nt_ckpt_key]["checkpoint_path"]
    print(f"  Audit checkpoint: {nt_ckpt}")

    nt_result = run_all_negative_tests(nt_ckpt, device)
    nt_verdict = nt_result["verdict"]
    _save_atomic(
        output_dir / "negative_audit.json",
        {"checkpoint": nt_ckpt, **nt_result}
    )
    print(f"  NT verdict: {nt_verdict}")

    if "LEAKAGE" in nt_verdict:
        print("\n[STOP] Leakage detected in negative tests. Aborting per DEC-051 protocol.")
        _save_atomic(output_dir / "run_summary.json", {
            "status": "ABORTED_LEAKAGE",
            "nt_verdict": nt_verdict,
            "runtime_s": time.time() - t_start,
        })
        return

    # ── Step 4: Select top-2 variants by val_loss ───────────────────────────
    print("\n[Step 4] Selecting top-2 variants by val_loss...")
    val_losses = {
        k: v["best_val_loss"]
        for k, v in checkpoint_manifest.items()
        if not np.isnan(v.get("best_val_loss") or float("nan"))
    }
    top2_keys = select_top2_variants(val_losses)
    print(f"  Top-2 (by val_loss): {top2_keys}")

    # ── Step 5: Few-shot on top-2 variants ──────────────────────────────────
    print("\n[Step 5] Few-shot evaluation on top-2 variants...")
    all_fs_results = []
    for key in top2_keys:
        variant_name = "_".join(key.split("_")[:-1])  # strip _epN suffix
        budget = int(key.split("_")[-1].replace("ep", ""))
        ckpt = checkpoint_manifest[key]["checkpoint_path"]
        print(f"  {key} ...")
        fs_results = evaluate_few_shot(ckpt, variant_name, budget, device, FEWSHOT_K_FRACS)
        all_fs_results.extend(fs_results)

    fs_summary = aggregate_few_shot(all_fs_results)
    _save_atomic(
        output_dir / "fewshot_results.json",
        {"results": [_result_to_dict(r) for r in all_fs_results],
         "summary": {str(k): v for k, v in fs_summary.items()},
         "top2_variants_selected": top2_keys}
    )
    print(f"  Few-shot saved: {len(all_fs_results)} results")

    # ── Step 6: Gate evaluation ──────────────────────────────────────────────
    print("\n[Step 6] Evaluating gates V1-V10...")
    gates = evaluate_all_gates(
        zero_shot_results=all_zs_results,
        zero_shot_summary=zs_summary,
        fewshot_results=all_fs_results,
        fewshot_summary=fs_summary,
        nt_verdict=nt_verdict,
    )
    gate_report = format_gate_report(gates)
    print("\n" + gate_report)

    gate_dict = {
        gid: {
            "verdict": g.verdict,
            "description": g.description,
            "evidence": g.evidence,
            "notes": g.notes,
        }
        for gid, g in gates.items()
    }
    _save_atomic(output_dir / "gate_results.json", gate_dict)
    (output_dir / "gate_report.md").write_text(gate_report)

    # ── Step 7: Final summary ────────────────────────────────────────────────
    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")
    n_fail = sum(1 for g in gates.values() if g.verdict == "FAIL")
    runtime = time.time() - t_start

    summary = {
        "status": "COMPLETE",
        "runtime_s": runtime,
        "nt_verdict": nt_verdict,
        "top2_selected": top2_keys,
        "n_gates_pass": n_pass,
        "n_gates_fail": n_fail,
        "gates": gate_dict,
        "checkpoint_manifest": checkpoint_manifest,
    }
    _save_atomic(output_dir / "run_summary.json", summary)
    print(f"\n[DEC-051] Done in {runtime:.0f}s. Gates: {n_pass} PASS, {n_fail} FAIL.")

    if n_fail > 0:
        failing = [gid for gid, g in gates.items() if g.verdict == "FAIL"]
        print(f"[DEC-051] Failing gates: {failing}")
        print("[DEC-051] Do NOT proceed to 300 epochs without explicit user authorization.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEC-051 Stable Objective Audit")
    parser.add_argument(
        "--output-dir",
        default="data/processed/synthetic_benchmark/phase15_stable_objective",
        help="Output directory for checkpoints and results",
    )
    parser.add_argument("--device", default="cpu", help="torch device")
    parser.add_argument(
        "--n-datasets",
        type=int,
        default=50,
        help="Number of D2 datasets for pretraining (default 50)",
    )
    args = parser.parse_args()
    main(args)
