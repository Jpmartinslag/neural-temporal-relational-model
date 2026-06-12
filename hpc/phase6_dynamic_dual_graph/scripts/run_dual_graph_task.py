"""P6_DDEG_S1 HPC task runner — one (fold, control, seed) per job.

Called by run_dual_graph_array.sbatch via SLURM_ARRAY_TASK_ID.
Decodes task ID to (fold, control, seed), runs evaluate_run from the
frozen trainer, and writes one atomic JSON result.

Task-ID mapping (275 jobs total, 5 folds × 11 controls × 5 seeds):
  fold_idx    = task_id // (N_CONTROLS * N_SEEDS)   # 0-4
  control_idx = (task_id % (N_CONTROLS * N_SEEDS)) // N_SEEDS   # 0-10
  seed_idx    = task_id % N_SEEDS                   # 0-4

Output: OUT_ROOT/raw/{control}__fr{fold}__seed{seed}.json
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import socket
import sys
import time
import tempfile
from pathlib import Path

# ── repo root (hpc/phase6_dynamic_dual_graph/scripts/ → up 3 levels) ──────
BASE = Path(__file__).resolve().parents[3]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import numpy as np

from src.modeles.train_dual_graph_experiment import (
    CONTROLS,
    CONTROL_ORDER,
    HYPERPARAMS,
    TENSOR_DIR,
    MANIFEST,
    _to_tensor_fold,
    evaluate_run,
    load_fold,
    temporal_split,
    atomic_write_json,
    _git_commit,
)

# ── thread limits ─────────────────────────────────────────────────────────
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

FOLDS = [2021, 2022, 2023, 2024, 2025]
SEEDS = [42, 43, 44, 45, 46]
N_FOLDS, N_CONTROLS, N_SEEDS = len(FOLDS), len(CONTROL_ORDER), len(SEEDS)
_STRIDE = N_CONTROLS * N_SEEDS  # 55


def decode_task(task_id: int) -> tuple[int, str, int]:
    """Return (eval_year, control_name, seed)."""
    if not (0 <= task_id < N_FOLDS * _STRIDE):
        raise ValueError(f"task_id {task_id} out of range [0, {N_FOLDS * _STRIDE})")
    fold_idx = task_id // _STRIDE
    ctrl_idx = (task_id % _STRIDE) // N_SEEDS
    seed_idx = task_id % N_SEEDS
    return FOLDS[fold_idx], CONTROL_ORDER[ctrl_idx], SEEDS[seed_idx]


def encode_task(fold: int, control: str, seed: int) -> int:
    fi = FOLDS.index(fold)
    ci = CONTROL_ORDER.index(control)
    si = SEEDS.index(seed)
    return fi * _STRIDE + ci * N_SEEDS + si


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_tensor_checksum(eval_year: int) -> bool:
    """Return True if tensor checksum matches manifest; True if manifest missing."""
    if not MANIFEST.exists():
        return True
    manifest = json.loads(MANIFEST.read_text())
    for f in manifest.get("folds", []):
        if f.get("eval_year") == eval_year:
            expected = f.get("sha256")
            if expected is None:
                return True
            actual = _sha256(TENSOR_DIR / f"fr_{eval_year}.npz")
            return actual == expected
    return True  # fold not in manifest → don't block


def _has_nonfinite(obj, path="") -> bool:
    """Recursively scan a JSON-like object for NaN / Inf floats."""
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, (list, tuple)):
        return any(_has_nonfinite(v, f"{path}[{i}]") for i, v in enumerate(obj))
    if isinstance(obj, dict):
        return any(_has_nonfinite(v, f"{path}.{k}") for k, v in obj.items())
    return False


def _strip_outputs(result: dict) -> dict:
    """Remove large raw prediction arrays before writing to disk."""
    clean = {k: v for k, v in result.items() if k != "outputs"}
    if "learned_graph" in clean and isinstance(clean["learned_graph"], dict):
        lg = clean["learned_graph"]
        clean["learned_graph"] = {k: v for k, v in lg.items()
                                   if k not in ("edges_by_time",)}
    return clean


def _json_default(o):
    if isinstance(o, (int, float, str, bool, type(None))):
        return o
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    return str(o)


def run_task(task_id: int, out_root: Path, force: bool = False) -> None:
    eval_year, control, seed = decode_task(task_id)

    out_dir = out_root / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{control}__fr{eval_year}__seed{seed}.json"

    # Skip if valid output already exists (idempotent).
    if not force and out_file.exists():
        try:
            prev = json.loads(out_file.read_text())
            if prev.get("status") == "ok":
                print(f"SKIP (already done): task={task_id} {control} fr{eval_year} seed{seed}")
                return
        except Exception:
            pass  # corrupted → overwrite

    print(f"START task={task_id} fold={eval_year} control={control} seed={seed} "
          f"pid={os.getpid()} host={socket.gethostname()}")

    # ── tensor checksum ───────────────────────────────────────────────────
    if not _verify_tensor_checksum(eval_year):
        raise RuntimeError(f"Tensor checksum mismatch for fold {eval_year}")

    t0 = time.time()

    # ── load fold + split ─────────────────────────────────────────────────
    fold = load_fold(eval_year)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)

    if not split["leakage_ok"]:
        raise RuntimeError(
            f"Leakage detected in fold {eval_year}: "
            f"train={split['train_years']} val={split['val_year']} outer={split['outer_year']}")

    # ── run ───────────────────────────────────────────────────────────────
    hp = dict(HYPERPARAMS)  # frozen; never modify based on results
    result = evaluate_run(fold_t, fold, control, seed, eval_year, split, hp)

    runtime = time.time() - t0

    # ── health checks ─────────────────────────────────────────────────────
    if result.get("status") != "ok":
        raise RuntimeError(
            f"evaluate_run status={result.get('status')} "
            f"for task={task_id} ({control}, fr{eval_year}, seed{seed})")

    stripped = _strip_outputs(result)
    if _has_nonfinite(stripped):
        raise RuntimeError(
            f"NaN/Inf in result for task={task_id} ({control}, fr{eval_year}, seed{seed})")

    # ── annotate with HPC provenance ──────────────────────────────────────
    output = {
        "task_id": task_id,
        "fold": eval_year,
        "control": control,
        "seed": seed,
        "git_commit": _git_commit(),
        "hostname": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_array_task_id": task_id,
        "runtime_seconds": runtime,
        "hyperparameters": {k: v for k, v in hp.items()},
        "leakage_audit": {
            "leakage_ok": split["leakage_ok"],
            "train_years": split["train_years"],
            "val_year": split["val_year"],
            "outer_year": split["outer_year"],
        },
        "tensor_dir": str(TENSOR_DIR),
        "platform": platform.platform(),
        **stripped,
    }

    atomic_write_json(out_file, output)
    print(f"DONE  task={task_id} fold={eval_year} control={control} seed={seed} "
          f"mae={result.get('metrics', {}).get('regression', {}).get('mae', 'n/a'):.5f} "
          f"runtime={runtime:.1f}s → {out_file.name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="P6_DDEG_S1 HPC single-job runner")
    parser.add_argument("--task-id", type=int, default=None,
                        help="Override SLURM_ARRAY_TASK_ID (for smoke testing)")
    parser.add_argument("--out-root", type=Path,
                        default=BASE / "hpc_results/dual_graph_s1",
                        help="Output root directory")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing valid output")
    args = parser.parse_args()

    task_id = args.task_id
    if task_id is None:
        raw = os.environ.get("SLURM_ARRAY_TASK_ID")
        if raw is None:
            raise SystemExit("SLURM_ARRAY_TASK_ID not set and --task-id not given")
        task_id = int(raw)

    run_task(task_id, args.out_root, force=args.force)
