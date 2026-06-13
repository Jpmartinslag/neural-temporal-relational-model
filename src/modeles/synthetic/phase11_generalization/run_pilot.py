"""
run_pilot.py — Phase 11 True Generalization Pilot (DEC-045)

Local pilot: 3 train seeds × 1 val seed × 3 test seeds × 2 strategies (T1, T2)
Epochs: 150, patience: 20
Train masks: mcar_30, block_30
Val mask: mcar_30
Test masks: mcar_30, block_30 (pilot scope)

Expected: ~2 × (6 train entries) × 150 epochs ≈ 3-8 minutes on CPU/GPU

Output directory: data/processed/synthetic_benchmark/phase11_pilot/
  phase11_T1_results.json   — T1 evaluation records
  phase11_T2_results.json   — T2 evaluation records
  phase11_T1_history.json   — T1 training history + checkpoint hash
  phase11_T2_history.json   — T2 training history + checkpoint hash
  phase11_T1.ckpt           — T1 model checkpoint (torch save)
  phase11_T2.ckpt           — T2 model checkpoint (torch save)
  phase11_gate_report.json  — Gate report X1-X9

Usage:
    # Full pilot (T1 + T2, default 150 epochs)
    python -m src.modeles.synthetic.phase11_generalization.run_pilot

    # Single strategy
    python -m src.modeles.synthetic.phase11_generalization.run_pilot --strategy T2

    # Dry run (no training, just verify manifest)
    python -m src.modeles.synthetic.phase11_generalization.run_pilot --dry-run

    # Custom epochs
    python -m src.modeles.synthetic.phase11_generalization.run_pilot --epochs 100 --patience 15
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import torch

from src.modeles.synthetic.phase11_generalization.splits import (
    PILOT_TRAIN_SEEDS,
    PILOT_VAL_SEEDS,
    PILOT_TEST_SEEDS,
    PILOT_TEST_MASK_KEYS,
    NOVEL_TEST_SCENARIOS,
    build_split_manifest,
    verify_disjoint,
    verify_novel_test_dynamics,
)
from src.modeles.synthetic.phase11_generalization.trainer import (
    make_train_entries,
    make_val_entries,
    train_multi_dataset,
    save_checkpoint,
    load_checkpoint,
    checkpoint_hash,
    DEFAULT_LR,
    STRATEGY_SCENARIOS,
)
from src.modeles.synthetic.phase11_generalization.evaluator import run_evaluation
from src.modeles.synthetic.phase11_generalization.gates_phase11 import evaluate_gates

DEFAULT_EPOCHS = 150
DEFAULT_PATIENCE = 20
DEFAULT_OUTPUT = Path("data/processed/synthetic_benchmark/phase11_pilot")


def run_pilot(
    strategies: list[str],
    output_dir: Path,
    n_epochs: int = DEFAULT_EPOCHS,
    patience: int = DEFAULT_PATIENCE,
    device: str = "cpu",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build and save split manifest (verifies disjointness + novelty)
    print("Building split manifest …")
    manifest = build_split_manifest(
        train_seeds=PILOT_TRAIN_SEEDS,
        val_seeds=PILOT_VAL_SEEDS,
        test_seeds=PILOT_TEST_SEEDS,
    )
    (output_dir / "phase11_split_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"  Train seeds: {PILOT_TRAIN_SEEDS}, Val seeds: {PILOT_VAL_SEEDS}, "
          f"Test seeds: {PILOT_TEST_SEEDS}")
    print(f"  Train scenarios: {manifest['train_scenarios']}, Val: {manifest['val_scenario']}, "
          f"Test: {manifest['test_scenarios']}")

    all_records: list[dict] = []

    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"Strategy {strategy}: training …")
        t_train_start = time.time()

        train_entries = make_train_entries(strategy, PILOT_TRAIN_SEEDS)
        val_entries = make_val_entries(PILOT_VAL_SEEDS)
        print(f"  {len(train_entries)} train mini-datasets, {len(val_entries)} val mini-datasets")

        model, history = train_multi_dataset(
            train_entries, val_entries,
            n_epochs=n_epochs,
            lr=DEFAULT_LR,
            patience=patience,
            device=device,
            seed=7,
        )
        history["strategy"] = strategy
        t_train = time.time() - t_train_start
        print(f"  Training done in {t_train:.1f}s ({history['n_epochs_run']} epochs, "
              f"best val loss={history['best_val_loss']:.4f} at epoch {history['best_epoch']})")

        # Save checkpoint before any evaluation
        ckpt_path = output_dir / f"phase11_{strategy}.ckpt"
        c_hash = save_checkpoint(model, ckpt_path)
        history["checkpoint_path"] = str(ckpt_path)
        history["checkpoint_hash"] = c_hash
        (output_dir / f"phase11_{strategy}_history.json").write_text(json.dumps(history, indent=2))
        print(f"  Checkpoint saved → {ckpt_path} (hash={c_hash[:12]}…)")

        # Zero-shot evaluation
        print(f"  Evaluating {strategy} on test scenarios …")
        t_eval_start = time.time()
        records = run_evaluation(
            strategy=strategy,
            herald_checkpoint_path=ckpt_path,
            checkpoint_hash_before=c_hash,
            test_seeds=PILOT_TEST_SEEDS,
            test_mask_keys=PILOT_TEST_MASK_KEYS,
            device=device,
        )
        t_eval = time.time() - t_eval_start
        print(f"  Evaluation done in {t_eval:.1f}s ({len(records)} records)")

        # Save evaluation records
        result_path = output_dir / f"phase11_{strategy}_results.json"
        result_path.write_text(json.dumps(records, indent=2))
        print(f"  Results → {result_path}")

        # Quick summary
        for scenario in sorted({r["scenario"] for r in records}):
            sc_recs = [r for r in records if r["scenario"] == scenario]
            hl_maes = [r["models"].get("herald_lagged", {}).get("mae") for r in sc_recs
                       if isinstance(r.get("models"), dict)]
            ff_maes = [r["models"].get("ffill", {}).get("mae") for r in sc_recs
                       if isinstance(r.get("models"), dict)]
            ng_maes = [r["models"].get("no_graph", {}).get("mae") for r in sc_recs
                       if isinstance(r.get("models"), dict)]
            hl_clean = [v for v in hl_maes if v is not None and v == v]
            ff_clean = [v for v in ff_maes if v is not None and v == v]
            ng_clean = [v for v in ng_maes if v is not None and v == v]

            import numpy as np
            print(f"    {scenario}: herald_lagged={np.mean(hl_clean):.4f}, "
                  f"ffill={np.mean(ff_clean):.4f}, "
                  f"no_graph={np.mean(ng_clean):.4f}")

        all_records.extend(records)

    # Evaluate gates on combined records
    print(f"\n{'='*60}")
    print("Evaluating gates X1-X9 …")
    gate_report = evaluate_gates(all_records)
    gate_path = output_dir / "phase11_gate_report.json"
    gate_path.write_text(json.dumps(gate_report, indent=2))
    print(f"Gate report → {gate_path}")
    summary = gate_report.get("summary", {})
    print(f"\nDecision: {summary.get('decision', '?')}")
    print(f"Gates passed: {summary.get('n_pass', '?')}/{summary.get('n_total', '?')}")
    for gate, passed in summary.get("gates", {}).items():
        status = "PASS" if passed else "FAIL"
        print(f"  {gate}: {status}")

    return gate_report


def dry_run() -> None:
    print("DRY RUN — verifying split structure …")
    verify_disjoint()
    verify_novel_test_dynamics()
    print("  Seed disjointness: OK")
    print("  Novel test dynamics: OK")

    manifest = build_split_manifest(
        train_seeds=PILOT_TRAIN_SEEDS,
        val_seeds=PILOT_VAL_SEEDS,
        test_seeds=PILOT_TEST_SEEDS,
    )
    n_train = sum(1 for k in manifest["checksums"] if k.startswith("train/"))
    n_val = sum(1 for k in manifest["checksums"] if k.startswith("val/"))
    n_test = sum(1 for k in manifest["checksums"] if k.startswith("test/"))
    print(f"  Manifest: {n_train} train, {n_val} val, {n_test} test checksums")

    for strategy in ["T1", "T2"]:
        entries = make_train_entries(strategy, PILOT_TRAIN_SEEDS)
        val_entries = make_val_entries(PILOT_VAL_SEEDS)
        expected_test = len(NOVEL_TEST_SCENARIOS) * len(PILOT_TEST_SEEDS) * len(PILOT_TEST_MASK_KEYS)
        print(f"  {strategy}: {len(entries)} train entries, {len(val_entries)} val entries, "
              f"~{expected_test} test evaluations")
    print("DRY RUN OK — all checks passed")


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 11 generalization pilot (DEC-045)")
    ap.add_argument("--strategy", choices=["T1", "T2", "both"], default="both")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    ap.add_argument("--patience", type=int, default=DEFAULT_PATIENCE)
    ap.add_argument("--device", type=str, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        dry_run()
        return

    if args.device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    print(f"Device: {device}")

    strategies = ["T1", "T2"] if args.strategy == "both" else [args.strategy]
    run_pilot(
        strategies=strategies,
        output_dir=args.output_dir,
        n_epochs=args.epochs,
        patience=args.patience,
        device=device,
    )


if __name__ == "__main__":
    main()
