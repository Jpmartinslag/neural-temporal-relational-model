"""
run_negative_audit.py — Re-run NT1-NT6 from existing checkpoints.

Loads checkpoint_manifest.json, validates hashes, runs audit, writes
negative_audit_deterministic.json. Does NOT retrain or overwrite existing files.

Usage:
  python -m src.modeles.synthetic.phase15_stable_objective.run_negative_audit \
      --output-dir data/processed/synthetic_benchmark/phase15_stable_objective \
      --device cpu
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from src.modeles.synthetic.phase15_stable_objective.fewshot_audit import (
    run_all_negative_tests,
    ADAPT_SEED,
)
from src.modeles.synthetic.phase11_generalization.trainer import load_checkpoint, checkpoint_hash


def _load_manifest(output_dir: Path) -> dict:
    manifest_path = output_dir / "checkpoint_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"checkpoint_manifest.json not found in {output_dir}")
    return json.loads(manifest_path.read_text())


def _verify_hash(manifest: dict, key: str) -> dict:
    """Load checkpoint and verify its hash against the manifest."""
    entry = manifest[key]
    ckpt_path = Path(entry["checkpoint_path"])
    if not ckpt_path.is_absolute():
        ckpt_path = ckpt_path
    expected_hash = entry["checkpoint_hash"]
    model = load_checkpoint(ckpt_path, "cpu")
    actual_hash = checkpoint_hash(model.state_dict())
    return {
        "key": key,
        "path": str(ckpt_path),
        "expected_hash": expected_hash,
        "actual_hash": actual_hash,
        "hash_ok": expected_hash == actual_hash,
    }


def _save_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(path)


def main(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    device = args.device

    # Load manifest
    print(f"[NT-RERUN] Output dir: {output_dir}")
    manifest = _load_manifest(output_dir)

    # Determine NT checkpoint (TEMPORAL_MASKED_NLL_CLAMPED@75)
    nt_ckpt_key = "TEMPORAL_MASKED_NLL_CLAMPED_ep75"
    if nt_ckpt_key not in manifest:
        nt_ckpt_key = list(manifest.keys())[0]
        print(f"  [WARN] TEMPORAL_MASKED_NLL_CLAMPED_ep75 not found, using {nt_ckpt_key!r}")
    nt_ckpt_path = Path(manifest[nt_ckpt_key]["checkpoint_path"])

    # Record pre-run hashes for all checkpoints
    print("[NT-RERUN] Verifying checkpoint hashes...")
    hash_records = {}
    for key in manifest:
        try:
            rec = _verify_hash(manifest, key)
            hash_records[key] = rec
            status = "OK" if rec["hash_ok"] else "MISMATCH"
            print(f"  {key}: {status} ({rec['actual_hash'][:12]})")
        except Exception as e:
            hash_records[key] = {"key": key, "error": str(e), "hash_ok": False}
            print(f"  {key}: ERROR — {e}")

    all_hashes_ok = all(v.get("hash_ok", False) for v in hash_records.values())
    if not all_hashes_ok:
        print("[NT-RERUN] WARNING: Some checkpoints have hash mismatches.")

    # Save pre-run hash record
    _save_atomic(output_dir / "checkpoint_hashes_before_audit.json", hash_records)
    print(f"  Hashes saved to checkpoint_hashes_before_audit.json")

    # Run NT1-NT6
    print(f"\n[NT-RERUN] Running NT1-NT6 on {nt_ckpt_key} (adapt_seed={ADAPT_SEED})...")
    nt_result = run_all_negative_tests(nt_ckpt_path, device)
    verdict = nt_result["verdict"]
    print(f"\n[NT-RERUN] Verdict: {verdict}")
    for name, test in nt_result["tests"].items():
        status = "PASS" if test["all_pass"] else "FAIL"
        print(f"  {name}: {status}")
        for r in test.get("results", []):
            seed = r.get("seed")
            passed = r.get("pass", False)
            details = []
            if "params_identical" in r:
                details.append(f"params_identical={r['params_identical']}")
            if "max_abs_param_diff" in r:
                details.append(f"max_diff={r['max_abs_param_diff']:.2e}")
            if "same_best_epoch" in r:
                details.append(f"same_epoch={r['same_best_epoch']}")
            print(f"    seed={seed} pass={passed} {' '.join(details)}")

    # Verify checkpoints unchanged after audit
    print("\n[NT-RERUN] Verifying checkpoints unchanged after audit...")
    hash_records_after = {}
    for key in manifest:
        try:
            rec = _verify_hash(manifest, key)
            hash_records_after[key] = rec
            unchanged = rec["actual_hash"] == hash_records.get(key, {}).get("actual_hash")
            if not unchanged:
                print(f"  CHANGED: {key}")
            else:
                print(f"  unchanged: {key}")
        except Exception as e:
            hash_records_after[key] = {"key": key, "error": str(e), "hash_ok": False}

    _save_atomic(output_dir / "checkpoint_hashes_after_audit.json", hash_records_after)

    # Write deterministic audit result
    full_result = {
        "verdict": verdict,
        "all_pass": nt_result["all_pass"],
        "failing_tests": nt_result.get("failing_tests", []),
        "checkpoint_key": nt_ckpt_key,
        "checkpoint_path": str(nt_ckpt_path),
        "adapt_seed": ADAPT_SEED,
        "checkpoint_hash_before": hash_records.get(nt_ckpt_key, {}).get("actual_hash"),
        "checkpoint_hash_after": hash_records_after.get(nt_ckpt_key, {}).get("actual_hash"),
        "tests": nt_result["tests"],
    }
    _save_atomic(output_dir / "negative_audit_deterministic.json", full_result)
    print(f"\n[NT-RERUN] Saved: negative_audit_deterministic.json")

    if "LEAKAGE" in verdict:
        print("[NT-RERUN] STOP: Leakage found. Do not proceed to few-shot.")
    else:
        print("[NT-RERUN] Audit PASSED. Ready for few-shot evaluation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-run NT1-NT6 from existing checkpoints")
    parser.add_argument(
        "--output-dir",
        default="data/processed/synthetic_benchmark/phase15_stable_objective",
    )
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    main(args)
