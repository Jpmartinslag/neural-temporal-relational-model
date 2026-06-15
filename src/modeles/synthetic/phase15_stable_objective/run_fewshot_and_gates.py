"""
run_fewshot_and_gates.py — Resume DEC-051 after NT audit passes.

Loads existing checkpoints from checkpoint_manifest.json, validates hashes,
runs few-shot evaluation on top-2 val-selected variants, evaluates gates V1-V10.
Does NOT retrain. Does NOT overwrite checkpoint_manifest.json or zero_shot_results.json.

Usage:
  python -m src.modeles.synthetic.phase15_stable_objective.run_fewshot_and_gates \
      --output-dir data/processed/synthetic_benchmark/phase15_stable_objective \
      --device cpu
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.modeles.synthetic.phase11_generalization.trainer import load_checkpoint, checkpoint_hash
from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import (
    ZeroShotResult,
    evaluate_few_shot,
    aggregate_zero_shot,
    aggregate_few_shot,
    select_top2_variants,
    FEWSHOT_K_FRACS,
)
from src.modeles.synthetic.phase15_stable_objective.gates_dec051 import (
    evaluate_all_gates,
    format_gate_report,
)


def _result_to_dict(r) -> dict:
    return r._asdict() if hasattr(r, "_asdict") else dict(r)


def _save_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(path)


def _verify_manifest_hashes(manifest: dict, output_dir: Path) -> dict:
    """Verify all checkpoint hashes match manifest. Returns {key: ok}."""
    results = {}
    for key, entry in manifest.items():
        ckpt_path = Path(entry["checkpoint_path"])
        if not ckpt_path.exists():
            results[key] = {"hash_ok": False, "error": "file not found"}
            continue
        expected = entry["checkpoint_hash"]
        try:
            model = load_checkpoint(ckpt_path, "cpu")
            actual = checkpoint_hash(model.state_dict())
            results[key] = {"hash_ok": expected == actual, "actual": actual, "expected": expected}
        except Exception as e:
            results[key] = {"hash_ok": False, "error": str(e)}
    return results


def main(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    device = args.device

    # Load existing artifacts
    manifest_path = output_dir / "checkpoint_manifest.json"
    zs_results_path = output_dir / "zero_shot_results.json"
    nt_path = output_dir / "negative_audit_deterministic.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"checkpoint_manifest.json not found — run pretraining first")
    if not nt_path.exists():
        raise FileNotFoundError(f"negative_audit_deterministic.json not found — run NT audit first")

    manifest = json.loads(manifest_path.read_text())
    nt_result = json.loads(nt_path.read_text())
    nt_verdict = nt_result["verdict"]

    print(f"[RESUME] NT verdict: {nt_verdict}")
    if "LEAKAGE" in nt_verdict:
        print("[RESUME] STOP: NT audit did not pass. Cannot proceed to few-shot.")
        return

    # Verify checkpoint hashes before any use
    print("[RESUME] Verifying checkpoint hashes...")
    hash_checks = _verify_manifest_hashes(manifest, output_dir)
    all_ok = all(v.get("hash_ok", False) for v in hash_checks.values())
    for key, v in hash_checks.items():
        status = "OK" if v.get("hash_ok") else f"FAIL ({v.get('error', 'hash mismatch')})"
        print(f"  {key}: {status}")
    if not all_ok:
        print("[RESUME] WARNING: Hash mismatches found — checkpoints may have been modified.")

    # Load zero-shot results
    zs_raw = json.loads(zs_results_path.read_text()) if zs_results_path.exists() else {}
    if "results" in zs_raw:
        all_zs_results = []
        for r in zs_raw["results"]:
            try:
                all_zs_results.append(ZeroShotResult(**r))
            except Exception:
                pass  # skip malformed records
        zs_summary_raw = zs_raw.get("summary", {})
        # Reconstruct tuple-keyed summary
        zs_summary = {}
        for k_str, v in zs_summary_raw.items():
            try:
                # key format: "('variant', budget, 'scenario', 'mask_key')"
                import ast
                k = ast.literal_eval(k_str)
                zs_summary[k] = v
            except Exception:
                pass
        print(f"[RESUME] Loaded {len(all_zs_results)} zero-shot results from file.")
    else:
        all_zs_results = []
        zs_summary = {}
        print("[RESUME] No zero-shot results found — gates may be limited.")

    # Select top-2 variants by val_loss
    print("[RESUME] Selecting top-2 variants by val_loss...")
    val_losses = {
        k: v["best_val_loss"]
        for k, v in manifest.items()
        if v.get("best_val_loss") is not None and not np.isnan(float(v.get("best_val_loss", float("nan"))))
    }
    if val_losses:
        top2_keys = select_top2_variants(val_losses)
    else:
        # Fall back to first two non-NO_PRETRAINING
        top2_keys = [k for k in manifest if "NO_PRETRAINING" not in k][:2]
    print(f"  Top-2: {top2_keys}")

    # Few-shot evaluation on top-2
    print("[RESUME] Running few-shot evaluation on top-2 variants...")
    all_fs_results = []
    for key in top2_keys:
        parts = key.rsplit("_ep", 1)
        variant_name = parts[0]
        budget = int(parts[1]) if len(parts) == 2 else 75
        ckpt_path = Path(manifest[key]["checkpoint_path"])
        if not ckpt_path.exists():
            print(f"  SKIP {key}: checkpoint not found at {ckpt_path}")
            continue
        print(f"  {key} ...")
        fs_results = evaluate_few_shot(str(ckpt_path), variant_name, budget, device, FEWSHOT_K_FRACS)
        all_fs_results.extend(fs_results)

    fs_summary = aggregate_few_shot(all_fs_results)
    _save_atomic(
        output_dir / "fewshot_results.json",
        {
            "results": [_result_to_dict(r) for r in all_fs_results],
            "summary": {str(k): v for k, v in fs_summary.items()},
            "top2_variants_selected": top2_keys,
        }
    )
    print(f"[RESUME] Few-shot saved: {len(all_fs_results)} results")

    # Evaluate gates
    print("[RESUME] Evaluating gates V1-V10...")
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

    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")
    n_fail = sum(1 for g in gates.values() if g.verdict == "FAIL")
    print(f"\n[RESUME] Gates: {n_pass} PASS, {n_fail} FAIL.")

    # Verify checkpoints unchanged after resumption
    print("[RESUME] Final hash verification...")
    hash_checks_after = _verify_manifest_hashes(manifest, output_dir)
    for key in manifest:
        before = hash_checks.get(key, {}).get("actual") or ""
        after = hash_checks_after.get(key, {}).get("actual") or ""
        if before and after and before != after:
            print(f"  CHANGED (unexpected): {key}")
        else:
            print(f"  unchanged: {key}")

    # Final summary
    _save_atomic(
        output_dir / "run_summary_resumed.json",
        {
            "status": "RESUMED_COMPLETE",
            "nt_verdict": nt_verdict,
            "top2_selected": top2_keys,
            "n_gates_pass": n_pass,
            "n_gates_fail": n_fail,
            "gates": gate_dict,
        }
    )
    print("\n[RESUME] Done. See gate_report.md for gate verdicts.")
    if n_fail > 0:
        failing = [gid for gid, g in gates.items() if g.verdict == "FAIL"]
        print(f"  Failing gates: {failing}")
        print("  Do NOT proceed to 300 epochs without explicit user authorization.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume DEC-051: few-shot + gates")
    parser.add_argument(
        "--output-dir",
        default="data/processed/synthetic_benchmark/phase15_stable_objective",
    )
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    main(args)
