"""
Execute a single task from the Phase 7 sector precedence manifest.

Outputs one JSON file per task with raw p-values (no q_fdr).
BH/FDR is applied by merge_sector_precedence_results.py after collecting
the full family, which is required for correct multiple-testing correction.

Usage:
    python run_sector_precedence_task.py \
        --manifest <path> --task-id <N> \
        --panel <path> --output-dir <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Import scientific functions from the builder — single source of truth.
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))
from src.data.european_panel.build_sector_precedence_graph import (
    evaluate_edge,
    pair_samples,
)

SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_and_validate_manifest(manifest_path: Path, task_id: int) -> dict:
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, list) or not manifest:
        sys.exit("Manifest must be a non-empty list.")
    if task_id < 0 or task_id >= len(manifest):
        sys.exit(f"task_id {task_id} out of range [0, {len(manifest)-1}].")
    task = manifest[task_id]
    if task["task_id"] != task_id:
        sys.exit(
            f"Manifest task_id mismatch: expected {task_id}, got {task['task_id']}."
        )
    return task


def _validate_panel(panel_path: Path, expected_checksum: str, expected_commit: str) -> None:
    actual_checksum = sha256_file(panel_path)
    if actual_checksum != expected_checksum:
        sys.exit(
            f"Panel checksum mismatch.\n"
            f"  Expected: {expected_checksum}\n"
            f"  Actual:   {actual_checksum}"
        )
    # Check git commit (warn but don't fail — remote worktree may have same content)
    try:
        import subprocess
        actual_commit = subprocess.check_output(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual_commit != expected_commit:
            print(
                f"WARNING: commit mismatch (expected {expected_commit[:12]}, "
                f"got {actual_commit[:12]}). Proceeding with checksum-verified panel.",
                file=sys.stderr,
            )
    except Exception:
        print("WARNING: could not verify git commit.", file=sys.stderr)


def run_task(task: dict, panel: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    """Execute one task: all target edges for this (country, scenario, window, source)."""
    source_sector = task["source_sector"]
    targets = task["targets"]
    window_start = task["window_start"]
    window_end = task["window_end"]
    scenario = task["scenario"]
    n_permutations = task["n_permutations"]
    n_bootstraps = task["n_bootstraps"]

    exclude_years = frozenset({2020}) if "without_2020" in scenario else frozenset()

    country_panel = panel[panel["country"].eq(task["country"])]

    edges = []
    for target_sector in targets:
        if target_sector == source_sector:
            continue
        samples = pair_samples(
            country_panel, source_sector, target_sector,
            window_start, window_end, exclude_years,
        )
        result = evaluate_edge(samples, rng, n_permutations, n_bootstraps)

        # Validate no silent NaN/Inf in numeric fields
        for key in ("beta", "delta_r2", "p_perm", "bootstrap_sign_stability"):
            val = result.get(key)
            if val is not None and np.isfinite(val):
                pass  # ok
            elif val is not None and not np.isfinite(val):
                result[key] = None  # convert Inf → None for JSON

        edges.append(
            {
                "target_sector": target_sector,
                "n_samples": int(result["n_samples"]),
                "beta": float(result["beta"]) if result["beta"] is not None and np.isfinite(result["beta"]) else None,
                "delta_r2": float(result["delta_r2"]) if result["delta_r2"] is not None and np.isfinite(result["delta_r2"]) else None,
                "p_perm": float(result["p_perm"]) if result.get("p_perm") is not None and np.isfinite(result["p_perm"]) else None,
                "bootstrap_sign_stability": (
                    float(result["bootstrap_sign_stability"])
                    if result.get("bootstrap_sign_stability") is not None
                    and np.isfinite(result["bootstrap_sign_stability"])
                    else None
                ),
            }
        )
    return edges


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute one Phase 7 task from the manifest."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--task-id", required=True, type=int)
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    task = _load_and_validate_manifest(args.manifest, args.task_id)
    _validate_panel(args.panel, task["panel_checksum"], task["commit_sha"])

    # Derive deterministic seed from base seed and task_id
    derived_seed = (task["seed"] * 131071 + task["task_id"]) % (2**31)
    rng = np.random.default_rng(derived_seed)

    print(
        f"Task {args.task_id}: {task['country']} / {task['scenario']} / "
        f"{task['window_start']}-{task['window_end']} / src={task['source_sector']} "
        f"/ {len(task['targets'])} targets",
        flush=True,
    )

    panel = pd.read_csv(args.panel, dtype={"territory_id": str}, low_memory=False)

    t0 = time.monotonic()
    edges = run_task(task, panel, rng)
    runtime = time.monotonic() - t0

    output = {
        "schema_version": SCHEMA_VERSION,
        "task_id": args.task_id,
        "country": task["country"],
        "scenario": task["scenario"],
        "window_start": task["window_start"],
        "window_end": task["window_end"],
        "source_sector": task["source_sector"],
        "targets": task["targets"],
        "n_permutations": task["n_permutations"],
        "n_bootstraps": task["n_bootstraps"],
        "panel_checksum": task["panel_checksum"],
        "commit_sha": task["commit_sha"],
        "derived_seed": derived_seed,
        "edges": edges,
        "runtime_seconds": round(runtime, 3),
        "hostname": platform.node(),
        "status": "complete",
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / task["expected_output"]

    # Idempotent: if result exists and is valid, skip
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if (
                existing.get("status") == "complete"
                and existing.get("task_id") == args.task_id
                and existing.get("panel_checksum") == task["panel_checksum"]
                and existing.get("commit_sha") == task["commit_sha"]
                and existing.get("schema_version") == SCHEMA_VERSION
            ):
                print(f"Task {args.task_id} already complete, skipping.", flush=True)
                return
        except Exception:
            pass
        # Incompatible existing result → fail rather than silently overwrite
        sys.exit(
            f"ERROR: {out_path} exists but is not a valid completed result for this task. "
            "Delete it manually to rerun."
        )

    # Atomic write
    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(output, indent=2) + "\n")
    tmp_path.replace(out_path)
    print(f"Task {args.task_id} complete: {out_path} ({runtime:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
