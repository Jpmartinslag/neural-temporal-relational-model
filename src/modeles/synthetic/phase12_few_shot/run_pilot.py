"""
run_pilot.py — Phase 12 few-shot adaptation pilot runner (DEC-047).

Usage:
  python src/modeles/synthetic/phase12_few_shot/run_pilot.py \\
      --checkpoint-dir data/processed/synthetic_benchmark/phase11_pilot \\
      --strategy T2 \\
      --output-dir data/processed/synthetic_benchmark/phase12_pilot \\
      --device cpu \\
      --epochs 50 \\
      --patience 10 \\
      --dry-run

The script:
  1. Finds the T2 checkpoint from phase11_pilot or trains one if not found
  2. Runs pilot evaluation (novel_lag2, seeds [1000,2000,3000], k_fracs [0.0, 0.05, 0.10])
  3. Saves JSON records atomically
  4. Prints per-strategy MAE summary
  5. Runs gates A1-A10 (pass/fail table)
  6. Reports runtime
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))


def _find_or_train_checkpoint(
    checkpoint_dir: Path,
    strategy: str,
    device: str,
    pilot: bool = True,
) -> tuple[Path, str]:
    """
    Find existing T2 checkpoint or train one.
    Returns (checkpoint_path, checkpoint_hash).
    """
    from src.modeles.synthetic.phase11_generalization.trainer import (
        train_strategy, save_checkpoint, checkpoint_hash,
    )

    # Look for existing checkpoint
    candidate = checkpoint_dir / f"model_{strategy}_pilot.pt"
    if not candidate.exists():
        candidate = checkpoint_dir / f"model_{strategy}.pt"

    if candidate.exists():
        from src.modeles.synthetic.phase11_generalization.trainer import load_checkpoint
        print(f"Loading checkpoint from {candidate}")
        model = load_checkpoint(candidate, device=device)
        h = checkpoint_hash(model.state_dict())
        print(f"Checkpoint hash: {h}")
        return candidate, h

    print(f"No checkpoint found in {checkpoint_dir}. Training {strategy} model...")
    model, history = train_strategy(strategy, pilot=pilot, device=device)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    save_path = checkpoint_dir / f"model_{strategy}_pilot.pt"
    h = save_checkpoint(model, save_path)
    print(f"Checkpoint saved → {save_path} (hash: {h})")
    return save_path, h


def _print_mae_summary(records: list[dict]) -> None:
    """Print per-strategy MAE summary table."""
    from collections import defaultdict
    import numpy as np

    by_strat: dict[str, list[float]] = defaultdict(list)
    for r in records:
        if r.get("error") or r.get("mae") is None:
            continue
        mae = r["mae"]
        if mae == mae and abs(mae) != float("inf"):
            by_strat[r.get("strategy", "?")].append(mae)

    print("\n=== MAE Summary by Strategy ===")
    print(f"{'Strategy':<8} {'n':>4} {'mean MAE':>10} {'min MAE':>10} {'max MAE':>10}")
    print("-" * 45)
    for strat in sorted(by_strat.keys()):
        vals = by_strat[strat]
        if vals:
            print(f"{strat:<8} {len(vals):>4} {np.mean(vals):>10.4f} {np.min(vals):>10.4f} {np.max(vals):>10.4f}")


def _print_gate_table(gate_report: dict) -> None:
    """Print gate pass/fail table."""
    gates = gate_report.get("summary", {}).get("gates", {})
    n_pass = gate_report.get("summary", {}).get("n_pass", 0)
    n_total = gate_report.get("summary", {}).get("n_total", 0)
    decision = gate_report.get("summary", {}).get("decision", "?")

    print(f"\n=== Gate Report A1-A10 (DEC-047) ===")
    for k, v in sorted(gates.items()):
        status = "PASS" if v else "FAIL"
        print(f"  {k}: {status}")
    print(f"\n  {n_pass}/{n_total} gates PASS")
    print(f"  Decision: {decision}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 12 few-shot adaptation pilot (DEC-047)")
    ap.add_argument("--checkpoint-dir", type=Path,
                    default=Path("data/processed/synthetic_benchmark/phase11_pilot"))
    ap.add_argument("--strategy", default="T2", choices=["T1", "T2"],
                    help="Training strategy for the base checkpoint")
    ap.add_argument("--output-dir", type=Path,
                    default=Path("data/processed/synthetic_benchmark/phase12_pilot"))
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--epochs", type=int, default=ADAPTATION_EPOCHS_DEFAULT,
                    help="Max adaptation epochs per support set")
    ap.add_argument("--patience", type=int, default=ADAPTATION_PATIENCE_DEFAULT)
    ap.add_argument("--bottleneck", type=int, default=16)
    ap.add_argument("--decoder-variant", default="mlp_relu",
                    choices=["mlp_relu", "mlp_gelu", "linear"])
    ap.add_argument("--dry-run", action="store_true",
                    help="Print config and exit without running")
    ap.add_argument("--scenarios", nargs="+", default=["novel_lag2"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1000, 2000, 3000])
    ap.add_argument("--k-fracs", nargs="+", type=float, default=[0.0, 0.05, 0.10])
    ap.add_argument("--support-seeds", nargs="+", type=int, default=[42, 123, 456])
    ap.add_argument("--strategies-eval", nargs="+",
                    default=["Z0", "A1", "A2", "A4", "C0", "B0", "B1", "P0"])
    ap.add_argument("--mask-keys", nargs="+", default=["mcar_30", "block_30"])
    args = ap.parse_args()

    if args.dry_run:
        print("=== Phase 12 Pilot Configuration (dry-run) ===")
        print(f"  checkpoint_dir   : {args.checkpoint_dir}")
        print(f"  strategy         : {args.strategy}")
        print(f"  output_dir       : {args.output_dir}")
        print(f"  device           : {args.device}")
        print(f"  epochs           : {args.epochs}")
        print(f"  patience         : {args.patience}")
        print(f"  bottleneck       : {args.bottleneck}")
        print(f"  decoder_variant  : {args.decoder_variant}")
        print(f"  scenarios        : {args.scenarios}")
        print(f"  dataset_seeds    : {args.seeds}")
        print(f"  k_fracs          : {args.k_fracs}")
        print(f"  support_seeds    : {args.support_seeds}")
        print(f"  strategies       : {args.strategies_eval}")
        print(f"  mask_keys        : {args.mask_keys}")
        total = (len(args.scenarios) * len(args.seeds) * len(args.k_fracs) *
                 len(args.support_seeds) * len(args.strategies_eval) * len(args.mask_keys))
        print(f"  total combos     : {total}")
        return

    t_start = time.time()

    # Step 1: Find or train checkpoint
    checkpoint_path, ckpt_hash = _find_or_train_checkpoint(
        args.checkpoint_dir, args.strategy, args.device
    )

    output_path = args.output_dir / "phase12_pilot_records.json"
    gate_path = args.output_dir / "phase12_pilot_gates.json"

    # Step 2: Run pilot
    from src.modeles.synthetic.phase12_few_shot.evaluator import run_pilot

    records = run_pilot(
        checkpoint_path=checkpoint_path,
        checkpoint_hash_before=ckpt_hash,
        scenarios=args.scenarios,
        dataset_seeds=args.seeds,
        k_fracs=args.k_fracs,
        support_seeds=args.support_seeds,
        strategies=args.strategies_eval,
        mask_keys=args.mask_keys,
        device=args.device,
        output_path=output_path,
        decoder_variant=args.decoder_variant,
        n_adapt_epochs=args.epochs,
        adapt_patience=args.patience,
        bottleneck=args.bottleneck,
    )

    # Step 3: Print summary
    _print_mae_summary(records)

    # Step 4: Gate evaluation
    from src.modeles.synthetic.phase12_few_shot.gates_dec047 import evaluate_gates
    gate_report = evaluate_gates(records)
    _print_gate_table(gate_report)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(gate_report, indent=2))
    print(f"\nGate report → {gate_path}")
    print(f"Records → {output_path}")
    print(f"Total runtime: {time.time() - t_start:.1f}s")


# Import constants here (after sys.path setup)
try:
    from src.modeles.synthetic.phase12_few_shot.adaptation_trainer import (
        ADAPTATION_EPOCHS as ADAPTATION_EPOCHS_DEFAULT,
        ADAPTATION_PATIENCE as ADAPTATION_PATIENCE_DEFAULT,
    )
except ImportError:
    ADAPTATION_EPOCHS_DEFAULT = 100
    ADAPTATION_PATIENCE_DEFAULT = 15


if __name__ == "__main__":
    main()
