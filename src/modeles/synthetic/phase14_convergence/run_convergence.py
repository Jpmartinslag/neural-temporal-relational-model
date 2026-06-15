"""
run_convergence.py — CLI script for DEC-049 convergence audit.

Usage:
    python src/modeles/synthetic/phase14_convergence/run_convergence.py \\
        --device cpu \\
        --pilot \\
        --output-dir data/processed/synthetic_benchmark/phase14_convergence

Pilot mode (--pilot): n_datasets=10, epoch_budgets=[30,75], 2 test seeds,
                       k_fracs=[0.05], mask_keys=["mcar_30"]
Full mode: n_datasets=50, epoch_budgets=[30,75,150] (+300 if triggered)

Script flow:
  1. Audit: verify D2 seeds are disjoint from test seeds
  2. Run pretraining for all 3 variants × epoch budgets
  3. Evaluate zero-shot and few-shot for all checkpoints
  4. Run gates E1-E10
  5. Check 300-epoch trigger rule
  6. Print summary table
  7. Save JSON records atomically (support resume)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))


def _atomic_write(path: Path, data: object) -> None:
    """Write JSON atomically via temp file to support resume on interruption."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


def _load_resume(path: Path) -> list[dict] | None:
    """Load existing records for resume support."""
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def print_summary_table(records: list[dict], gates: dict) -> None:
    """Print a summary table of results."""

    print("\n" + "=" * 70)
    print("DEC-049 CONVERGENCE AUDIT — SUMMARY TABLE")
    print("=" * 70)

    # Collect zero-shot records
    zs = [r for r in records if r.get("eval_type") == "zero_shot"]
    variants = sorted({r.get("variant", "") for r in zs})
    budgets = sorted({r.get("epoch_budget", 0) for r in zs})
    scenarios = sorted({r.get("scenario", "") for r in zs})

    print("\nZero-shot MAE by variant × budget (herald_lagged, all scenarios/seeds/masks):")
    print(f"{'Variant':<30} {'Budget':<8} {'Scenario':<20} {'MAE':>8} {'AUC':>8}")
    print("-" * 78)
    for variant in variants:
        for budget in budgets:
            for scenario in scenarios:
                maes = [r["mae"] for r in zs
                        if r.get("variant") == variant and r.get("epoch_budget") == budget
                        and r.get("scenario") == scenario and r.get("model_type") == "herald_lagged"
                        and not np.isnan(r.get("mae", float("nan")))]
                aucs = [r["edge_auc"] for r in zs
                        if r.get("variant") == variant and r.get("epoch_budget") == budget
                        and r.get("scenario") == scenario and r.get("model_type") == "herald_lagged"
                        and not np.isnan(r.get("edge_auc", float("nan")))]
                if maes:
                    m = float(np.mean(maes))
                    a = float(np.mean(aucs)) if aucs else float("nan")
                    print(f"{variant:<30} {budget:<8} {scenario:<20} {m:>8.4f} {a:>8.4f}")

    print("\nGates E1-E10:")
    for gate_id in ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"]:
        if gate_id in gates:
            result = gates[gate_id]["result"]
            note = gates[gate_id]["note"][:60]
            print(f"  {gate_id}: {result:<6} | {note}")

    summary = gates.get("summary", {})
    print(f"\nDecision: {summary.get('decision', 'UNKNOWN')}")
    print(f"Gates: {summary.get('n_pass', 0)}/{summary.get('total_gates', 10)} PASS")
    print(f"Recommendation: {summary.get('recommendation', '')}")
    print("=" * 70)


def run_audit_step(d2_seed_start: int, n_datasets: int) -> None:
    """Step 1: Verify D2 seeds are disjoint from test seeds."""
    from src.modeles.synthetic.phase14_convergence.pretrain_runner import verify_d2_seeds_disjoint
    seeds = list(range(d2_seed_start, d2_seed_start + n_datasets))
    verify_d2_seeds_disjoint(seeds)
    print(f"[AUDIT] D2 seeds {seeds[0]}..{seeds[-1]} are disjoint from test seeds. PASS.")


def main() -> None:
    parser = argparse.ArgumentParser(description="DEC-049 Convergence Audit")
    parser.add_argument("--device", default="cpu", help="PyTorch device")
    parser.add_argument("--pilot", action="store_true", help="Run in pilot mode (faster)")
    parser.add_argument(
        "--output-dir",
        default="data/processed/synthetic_benchmark/phase14_convergence",
        help="Output directory",
    )
    parser.add_argument(
        "--epoch-budgets", nargs="+", type=int, default=None,
        help="Override epoch budgets (default: [30,75,150])",
    )
    parser.add_argument("--skip-fewshot", action="store_true", help="Skip few-shot evaluation")
    args = parser.parse_args()

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    # ── Configuration ──────────────────────────────────────────────────────
    from src.modeles.synthetic.phase14_convergence.pretrain_runner import (
        EPOCH_BUDGETS, N_PRETRAIN_DATASETS, D2_SEED_START, PRETRAIN_VARIANTS,
    )
    from src.modeles.synthetic.phase11_generalization.splits import TEST_SEEDS
    from src.modeles.synthetic.phase12_few_shot.splits import PILOT_FEWSHOT_SEEDS

    if args.pilot:
        n_datasets = 10
        epoch_budgets = args.epoch_budgets or [30, 75]
        test_seeds = [1000, 2000]
        k_fracs = [0.05]
        mask_keys = ["mcar_30"]
        fewshot_seeds = [42]
        print("[PILOT] Mode: n_datasets=10, epoch_budgets=[30,75], 2 test seeds")
    else:
        n_datasets = N_PRETRAIN_DATASETS
        epoch_budgets = args.epoch_budgets or EPOCH_BUDGETS
        test_seeds = TEST_SEEDS
        k_fracs = [0.05, 0.10]
        mask_keys = ["mcar_30", "block_30"]
        fewshot_seeds = PILOT_FEWSHOT_SEEDS
        print(f"[FULL] n_datasets={n_datasets}, epoch_budgets={epoch_budgets}")

    # ── Step 1: Audit ──────────────────────────────────────────────────────
    run_audit_step(D2_SEED_START, n_datasets)

    # ── Step 2: Pretraining ────────────────────────────────────────────────
    from src.modeles.synthetic.phase14_convergence.pretrain_runner import run_budget_grid

    pretrain_results: dict[str, dict[int, dict]] = {}
    pretrain_summary_path = output_dir / "pretrain_results.json"
    existing_pretrain = _load_resume(pretrain_summary_path)
    if existing_pretrain:
        print(f"[RESUME] Loaded pretrain results from {pretrain_summary_path}")

    for variant in PRETRAIN_VARIANTS:
        print(f"\n[PRETRAIN] Variant: {variant}")
        t_v = time.time()
        budget_results = run_budget_grid(
            variant=variant,
            output_dir=output_dir / "checkpoints",
            device=args.device,
            n_datasets=n_datasets,
            epoch_budgets=epoch_budgets,
            seed_start=D2_SEED_START,
        )
        pretrain_results[variant] = budget_results

        for budget, result in budget_results.items():
            best_epoch = result.get("best_epoch", 0)
            best_val = result.get("best_val_loss", float("nan"))
            runtime = result.get("runtime_s", 0)
            print(
                f"  budget={budget}: best_epoch={best_epoch}, "
                f"best_val={best_val:.4f}, runtime={runtime:.1f}s"
            )

        print(f"  Total variant time: {time.time() - t_v:.1f}s")

    # Save pretrain results (JSON-serializable summary)
    pretrain_summary: dict = {}
    for variant, budget_map in pretrain_results.items():
        pretrain_summary[variant] = {}
        for budget, res in budget_map.items():
            pretrain_summary[variant][str(budget)] = {
                k: v for k, v in res.items()
                if k not in ("history",)  # skip large arrays
            }
            pretrain_summary[variant][str(budget)]["checkpoint_path"] = str(
                res.get("checkpoint_path", "")
            )
    _atomic_write(pretrain_summary_path, pretrain_summary)
    print(f"\n[SAVE] Pretrain results saved to {pretrain_summary_path}")

    # ── Step 3: Evaluation ─────────────────────────────────────────────────
    from src.modeles.synthetic.phase14_convergence.evaluator import run_full_evaluation

    records_path = output_dir / "records.json"
    existing_records = _load_resume(records_path)

    print("\n[EVAL] Running zero-shot and few-shot evaluation...")
    t_eval = time.time()

    all_records = run_full_evaluation(
        pretrain_results=pretrain_results,
        output_dir=output_dir,
        device=args.device,
        test_seeds=test_seeds,
        mask_keys=mask_keys,
        k_fracs=k_fracs if not args.skip_fewshot else [],
        fewshot_support_seeds=fewshot_seeds if not args.skip_fewshot else [],
        scenario_names=["novel_lag2", "novel_highvar"],
    )

    print(f"  Evaluation time: {time.time() - t_eval:.1f}s, {len(all_records)} records")
    _atomic_write(records_path, all_records)
    print(f"[SAVE] Records saved to {records_path}")

    # ── Step 4: Gates E1-E10 ───────────────────────────────────────────────
    from src.modeles.synthetic.phase14_convergence.gates_dec049 import (
        evaluate_gates, check_300_epoch_trigger,
    )

    print("\n[GATES] Running E1-E10 gate evaluation...")
    gates = evaluate_gates(all_records, pretrain_results)

    gates_path = output_dir / "gates_dec049.json"
    _atomic_write(gates_path, gates)
    print(f"[SAVE] Gates saved to {gates_path}")

    # ── Step 5: Check 300-epoch trigger ───────────────────────────────────
    trigger_300 = check_300_epoch_trigger(gates, all_records, pretrain_results)
    print(f"\n[TRIGGER] 300-epoch auto-trigger: {trigger_300}")
    if trigger_300:
        print("[TRIGGER] E1+E2 PASS at 150. 300-epoch run authorized.")
        print("[TRIGGER] Run manually with --epoch-budgets 300 if desired.")
    else:
        print("[TRIGGER] 300-epoch run NOT triggered (E1+E2 not both PASS at 150).")

    # ── Step 6: Summary table ──────────────────────────────────────────────
    print_summary_table(all_records, gates)

    total_time = time.time() - t_start
    print(f"\n[DONE] Total runtime: {total_time:.1f}s")

    # Save complete run summary
    run_summary = {
        "pilot": args.pilot,
        "n_datasets": n_datasets,
        "epoch_budgets": epoch_budgets,
        "test_seeds": test_seeds,
        "mask_keys": mask_keys,
        "k_fracs": k_fracs,
        "n_records": len(all_records),
        "total_runtime_s": total_time,
        "trigger_300": trigger_300,
        "gate_summary": gates.get("summary", {}),
    }
    _atomic_write(output_dir / "run_summary.json", run_summary)

    # Fail fast if E1 fails
    if gates.get("E1", {}).get("result") == "FAIL":
        print("\n[STOP] E1 SAFETY gate failed. Halting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
