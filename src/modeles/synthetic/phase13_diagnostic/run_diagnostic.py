"""
run_diagnostic.py — CLI runner for DEC-048 failure cause diagnostic.

Executes:
  1. Functional scenario test (C2 check — STOP if fails)
  2. Axis M (architecture) with local training on novel_lag2
  3. Axis D (data quantity/diversity) with fresh training
  4. Axis L (training objective)
  5. Axis S (shift intensity)
  6. Gradient diagnostics
  7. Masked pretraining (3 variants, pilot: 25 datasets)
  8. Gates C1-C10
  9. Summary

Usage:
    python src/modeles/synthetic/phase13_diagnostic/run_diagnostic.py \\
        --device cpu --pilot \\
        --output-dir data/processed/synthetic_benchmark/phase13_pilot

--pilot mode: 3 seeds, n_epochs=30, patience=5, n_datasets=[10,25], skip 100.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from src.modeles.synthetic.phase13_diagnostic.functional_scenario import (
    test_oracle_vs_ffill_functional,
    FUNCTIONAL_CONFIG,
)
from src.modeles.synthetic.phase13_diagnostic.ofat_runner import (
    run_axis_d,
    run_axis_m,
    run_axis_l,
    run_axis_s,
    run_gradient_diagnostics,
    _build_d2_entries,
    _build_val_entries,
    PILOT_TEST_SEEDS,
)
from src.modeles.synthetic.phase13_diagnostic.masked_pretraining import (
    run_pretraining_comparison,
    generate_d2_pretrain_datasets,
)
from src.modeles.synthetic.phase13_diagnostic.gates_dec048 import evaluate_gates
from src.modeles.synthetic.phase11_generalization.trainer import (
    train_multi_dataset, make_train_entries, make_val_entries,
    PILOT_TRAIN_SEEDS, PILOT_VAL_SEEDS,
)
from src.data.synthetic.generate_herald_synthetic import generate_dataset
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DEC-048 failure cause diagnostic")
    p.add_argument("--device", default="cpu", help="torch device")
    p.add_argument("--pilot", action="store_true",
                   help="Pilot mode: 3 seeds, n_epochs=30, n_datasets=[10,25]")
    p.add_argument("--output-dir", default="data/processed/synthetic_benchmark/phase13_pilot",
                   help="Output directory for results JSON")
    p.add_argument("--skip-pretraining", action="store_true",
                   help="Skip masked pretraining step (faster)")
    p.add_argument("--seed", type=int, default=7, help="RNG seed for training")
    return p.parse_args()


def _save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = args.device
    pilot = args.pilot
    t_global = time.time()

    if pilot:
        n_epochs = 30
        patience = 5
        n_datasets_list = [10, 25]
        test_seeds = [1000, 2000, 3000]
        pretrain_epochs = 50
        pretrain_patience = 10
        n_pretrain_datasets = 25
        functional_seeds = [9999, 9998]
        print("[DEC-048] PILOT MODE: n_epochs=30, seeds=[1000,2000,3000], n_datasets=[10,25]")
    else:
        n_epochs = 150
        patience = 20
        n_datasets_list = [10, 25, 50]
        test_seeds = [1000, 2000, 3000, 4000, 5000]
        pretrain_epochs = 200
        pretrain_patience = 20
        n_pretrain_datasets = 50
        functional_seeds = [9999, 9998, 9997]
        print("[DEC-048] FULL MODE: n_epochs=150, seeds=[1000..5000]")

    results = {
        "mode": "pilot" if pilot else "full",
        "device": device,
        "n_epochs": n_epochs,
        "test_seeds": test_seeds,
    }

    # ── Step 1: Functional scenario (C2 gate) ────────────────────────────────
    print("\n[Step 1/8] Functional scenario test (C2)...")
    t0 = time.time()
    functional_result = test_oracle_vs_ffill_functional(
        device=device,
        n_local_epochs=n_epochs * 2,  # oracle gets more epochs
        seeds=functional_seeds,
    )
    functional_result["elapsed_s"] = time.time() - t0
    results["functional_result"] = functional_result
    _save_json({"functional_result": functional_result}, output_dir / "step1_functional.json")

    print(f"  oracle_mae={functional_result['oracle_mae']:.4f} "
          f"ffill_mae={functional_result['ffill_mae']:.4f} "
          f"ratio={functional_result['oracle_ratio']:.3f} "
          f"C2={'PASS' if functional_result['gate_c2_pass'] else 'FAIL'}")

    if not functional_result["gate_c2_pass"]:
        print("\n[STOP] C2 FAIL: Oracle does not beat ffill in functional scenario.")
        print("Classification: ARCHITECTURE_INADEQUATE or IMPLEMENTATION_BUG")
        print("Stopping OFAT — further axes would not be informative.")
        results["decision"] = "ARCHITECTURE_INADEQUATE"
        results["stopped_at"] = "C2_FAIL"
        _save_json(results, output_dir / "dec048_results.json")
        return

    # ── Step 2: Axis M (architecture) ────────────────────────────────────────
    print("\n[Step 2/8] Axis M — Architecture contribution...")
    t0 = time.time()
    axis_m_records = run_axis_m(device=device, seeds=test_seeds, n_epochs=n_epochs)
    elapsed_m = time.time() - t0
    results["axis_m_records"] = axis_m_records
    _save_json({"axis_m": axis_m_records}, output_dir / "step2_axis_m.json")
    print(f"  {len(axis_m_records)} records in {elapsed_m:.1f}s")
    for model_type in ["M0_ffill", "M1_temporal_only", "M2_contemp_graph", "M3_lagged_graph", "M4_oracle_lagged"]:
        mae_vals = [r["mae"] for r in axis_m_records if r.get("model_type") == model_type]
        if mae_vals:
            print(f"  {model_type}: mean_mae={np.mean(mae_vals):.4f}")

    # ── Step 3: Axis D (data quantity/diversity) ──────────────────────────────
    print("\n[Step 3/8] Axis D — Data quantity and diversity...")
    t0 = time.time()
    axis_d_records = run_axis_d(
        device=device, seeds=test_seeds, n_epochs=n_epochs, patience=patience,
        n_datasets_list=n_datasets_list,
    )
    elapsed_d = time.time() - t0
    results["axis_d_records"] = axis_d_records
    _save_json({"axis_d": axis_d_records}, output_dir / "step3_axis_d.json")
    print(f"  {len(axis_d_records)} records in {elapsed_d:.1f}s")

    # Find best data config (lowest mean MAE)
    if axis_d_records:
        by_config = {}
        for r in axis_d_records:
            key = (r["n_datasets"], r["diversity"])
            by_config.setdefault(key, []).append(r["mae"])
        best_config_key = min(by_config.keys(), key=lambda k: np.mean(by_config[k]))
        best_data_config = {"n_datasets": best_config_key[0], "diversity": best_config_key[1]}
        results["best_data_config"] = best_data_config
        print(f"  Best data config: n_datasets={best_config_key[0]}, diversity={best_config_key[1]}, "
              f"mean_mae={np.mean(by_config[best_config_key]):.4f}")
    else:
        best_data_config = {"n_datasets": 25, "diversity": "D2"}
        results["best_data_config"] = best_data_config

    # ── Step 4: Axis L (training objective) ──────────────────────────────────
    print("\n[Step 4/8] Axis L — Training objective...")
    t0 = time.time()
    axis_l_records = run_axis_l(
        best_data_config=best_data_config,
        device=device, seeds=test_seeds,
        n_epochs=n_epochs, patience=patience,
    )
    elapsed_l = time.time() - t0
    results["axis_l_records"] = axis_l_records
    _save_json({"axis_l": axis_l_records}, output_dir / "step4_axis_l.json")
    print(f"  {len(axis_l_records)} records in {elapsed_l:.1f}s")
    for obj in ["L0", "L1", "L2", "L3"]:
        mae_vals = [r["mae"] for r in axis_l_records if r.get("objective") == obj]
        if mae_vals:
            print(f"  {obj}: mean_mae={np.mean(mae_vals):.4f}")

    # ── Step 5: Axis S (shift intensity) ─────────────────────────────────────
    print("\n[Step 5/8] Axis S — Shift intensity...")
    t0 = time.time()
    axis_s_records = run_axis_s(
        base_model=None,  # trains its own model
        device=device, test_seeds=test_seeds,
    )
    elapsed_s = time.time() - t0
    results["axis_s_records"] = axis_s_records
    _save_json({"axis_s": axis_s_records}, output_dir / "step5_axis_s.json")
    print(f"  {len(axis_s_records)} records in {elapsed_s:.1f}s")
    for sl in ["S0_indist", "S1_moderate", "S2_novel_lag2", "S3_novel_highvar"]:
        mae_vals = [r["mae"] for r in axis_s_records if r.get("shift_level") == sl]
        if mae_vals:
            ratio_vals = [r["mae_ratio"] for r in axis_s_records if r.get("shift_level") == sl]
            print(f"  {sl}: mean_mae={np.mean(mae_vals):.4f}, ratio={np.mean(ratio_vals):.3f}")

    # ── Step 6: Gradient diagnostics ─────────────────────────────────────────
    print("\n[Step 6/8] Gradient diagnostics...")
    import dataclasses
    from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
    from src.modeles.synthetic.phase13_diagnostic.ofat_runner import (
        _build_d2_entries, _build_val_entries, N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT
    )

    # Train a small model for gradient diagnostics
    train_entries_grad = _build_d2_entries(10)
    val_entries_grad = _build_val_entries()
    grad_model, _ = train_multi_dataset(
        train_entries_grad, val_entries_grad, n_epochs=10, patience=3, device=device, seed=7,
    )
    # Use first novel_lag2 dataset for gradient computation
    base_cfg = NOVEL_TEST_SCENARIOS["novel_lag2"]
    cfg_diag = dataclasses.replace(base_cfg, seed=test_seeds[0])
    ds_diag = generate_dataset(cfg_diag)
    panel_diag = ds_diag["panel"]
    mask_diag = ds_diag["masks"]["mcar_30"]
    adj_s_diag = ds_diag["sector_adj"]
    adj_t_diag = ds_diag["territory_adj"]
    true_rels_diag = ds_diag["true_relations"]

    grad_diag = run_gradient_diagnostics(
        grad_model, panel_diag, mask_diag, adj_s_diag, adj_t_diag, device,
        true_relations=true_rels_diag,
    )
    results["gradient_diagnostics"] = grad_diag
    _save_json({"gradient_diagnostics": grad_diag}, output_dir / "step6_gradient_diag.json")
    print(f"  grad_norm_attn={grad_diag['grad_norm_attn_total']:.6f} "
          f"grad_norm_mlp={grad_diag['grad_norm_mlp']:.6f} "
          f"graph_contribution_mae={grad_diag['graph_contribution_mae']:.4f}")
    if grad_diag.get("attn_grad_near_zero"):
        print("  WARNING: Attention gradient near zero — graph signal not reaching encoder")

    # ── Step 7: Masked pretraining ────────────────────────────────────────────
    if not args.skip_pretraining:
        print("\n[Step 7/8] Masked pretraining (3 variants)...")
        # Look for Phase 11 T2 checkpoint
        checkpoint_path = Path("data/processed/synthetic_benchmark/phase11_pilot/model_T2_pilot.pt")
        if not checkpoint_path.exists():
            checkpoint_path = None

        t0 = time.time()
        pretrain_records = run_pretraining_comparison(
            n_datasets=n_pretrain_datasets,
            n_pretrain_epochs=pretrain_epochs,
            patience=pretrain_patience,
            test_seeds=test_seeds,
            test_mask_keys=["mcar_30", "block_30"],
            device=device,
            base_checkpoint_path=checkpoint_path,
        )
        elapsed_pt = time.time() - t0
        results["pretraining_records"] = pretrain_records
        _save_json({"pretraining": pretrain_records}, output_dir / "step7_pretraining.json")
        print(f"  {len(pretrain_records)} records in {elapsed_pt:.1f}s")
        for variant in ["NO_PRETRAINING", "TEMPORAL_MASKED", "GRAPH_MASKED_MULTITASK"]:
            mae_vals = [r["mae"] for r in pretrain_records if r.get("variant") == variant]
            if mae_vals:
                print(f"  {variant}: mean_mae={np.mean(mae_vals):.4f}")
    else:
        print("\n[Step 7/8] Masked pretraining SKIPPED (--skip-pretraining)")
        pretrain_records = []
        results["pretraining_records"] = pretrain_records

    # ── Step 8: Gates C1-C10 ─────────────────────────────────────────────────
    print("\n[Step 8/8] Evaluating gates C1-C10...")
    gate_report = evaluate_gates(
        functional_result=functional_result,
        axis_d_records=axis_d_records,
        axis_m_records=axis_m_records,
        axis_l_records=axis_l_records,
        axis_s_records=axis_s_records,
        pretraining_records=pretrain_records,
    )
    results["gate_report"] = gate_report
    _save_json({"gates": gate_report}, output_dir / "step8_gates.json")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_elapsed = time.time() - t_global
    results["total_elapsed_s"] = total_elapsed
    results["gate_summary"] = gate_report.get("summary", {})

    print(f"\n{'='*60}")
    print("DEC-048 SUMMARY")
    print(f"{'='*60}")
    print(f"Total runtime: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    summary = gate_report.get("summary", {})
    print(f"Gates: {summary.get('n_pass', '?')}/10 PASS")
    print(f"Principal cause: {gate_report.get('principal_cause', 'UNKNOWN')}")
    print(f"Decision: {gate_report.get('decision', 'UNKNOWN')}")
    print(f"Next step: {gate_report.get('next_step', 'See gate report')}")
    print(f"\nGate table:")
    for gate_id in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]:
        g = gate_report.get(gate_id, {})
        print(f"  {gate_id}: {g.get('result', 'NA'):<6} — {g.get('note', '')[:80]}")

    # Save full results
    _save_json(results, output_dir / "dec048_results.json")
    print(f"\nResults saved to {output_dir}/dec048_results.json")

    if total_elapsed > 30 * 60:
        print(f"\nWARNING: Runtime exceeded 30 minutes ({total_elapsed/60:.1f} min). "
              f"Use --pilot for faster execution.")


if __name__ == "__main__":
    main()
