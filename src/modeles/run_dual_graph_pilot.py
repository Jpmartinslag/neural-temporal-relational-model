"""HERALD — Local technical pilot for the dual-graph trainer.

Purpose
-------
Technical liveness only on the FR/2021 fold: runtime, peak memory, finite
losses, early stopping, complete finite outputs and per-seed determinism.

Scope (deliberately limited):
  - fold FR/2021 only;
  - seeds 42 and 43;
  - max 30 epochs, patience 5;
  - controls C0–C5, C6 and C8 (C7, C9, C10 are NOT run yet).

This pilot does NOT apply or report the scientific fail-closed gate. No metric
printed here is a result; it is a pipeline health signal.

Run (mlearning env):
  /home/jpdark/miniconda3/envs/mlearning/bin/python -m src.modeles.run_dual_graph_pilot
"""
from __future__ import annotations

import resource
import time

import numpy as np

from src.modeles.train_dual_graph_experiment import (
    CONTROLS,
    HYPERPARAMS,
    evaluate_run,
    load_fold,
    temporal_split,
    train_neural,
    _to_tensor_fold,
)

EVAL_YEAR = 2021
SEEDS = [42, 43]
PILOT_CONTROLS = [
    "C0_persistence", "C1_ridge", "C2_no_graph", "C3_territory_only",
    "C4_sector_only", "C5_dual", "C6_territory_temporal_perm",
    "C8_sector_identity_perm",
]


def _peak_rss_gb() -> float:
    # ru_maxrss is in kilobytes on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 ** 2)


def main() -> None:
    hp = dict(HYPERPARAMS)
    hp["max_epochs"] = 30
    hp["patience"] = 5

    print(f"Dual-graph PILOT — fold FR/{EVAL_YEAR}, seeds {SEEDS}, "
          f"<= {hp['max_epochs']} epochs, patience {hp['patience']}")
    print("Technical liveness only — no scientific gate is applied.\n")

    fold = load_fold(EVAL_YEAR)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    assert split["leakage_ok"], "leakage in pilot fold"
    print(f"leakage check: train_years={split['train_years']} "
          f"val_year={split['val_year']} outer_year={split['outer_year']}  OK")
    print(f"samples: {len(fold['sample_years'])} "
          f"(train {len(split['train_idx'])}, val 1, outer 1)\n")

    t0 = time.time()
    rows = []
    all_ok = True
    for control in PILOT_CONTROLS:
        for seed in SEEDS:
            res = evaluate_run(fold_t, fold, control, seed, EVAL_YEAR, split, hp)
            reg = res["metrics"].get("regression", {})
            stopped = res.get("stopped_epoch")
            best = res.get("best_epoch")
            ok = (res["status"] == "ok"
                  and reg.get("mae") is not None and np.isfinite(reg["mae"]))
            all_ok = all_ok and ok
            rows.append({
                "control": control, "seed": seed, "status": res["status"],
                "n_params": res.get("n_params"), "mae": reg.get("mae"),
                "stopped_epoch": stopped, "best_epoch": best,
            })

    # Determinism: rerun C5/seed42 and compare predictions.
    spec = CONTROLS["C5_dual"]
    a = train_neural(fold_t, spec, split, 42, hp)
    b = train_neural(fold_t, spec, split, 42, hp)
    deterministic = bool(np.allclose(
        a["outputs"]["pred_log_growth"], b["outputs"]["pred_log_growth"]))

    runtime = time.time() - t0
    peak_gb = _peak_rss_gb()

    print(f"{'control':<28}{'seed':>5}{'status':>8}{'params':>8}"
          f"{'mae':>10}{'stop@':>7}{'best@':>7}")
    for r in rows:
        mae = f"{r['mae']:.5f}" if r["mae"] is not None else "—"
        stop = r["stopped_epoch"] if r["stopped_epoch"] is not None else "—"
        bst = r["best_epoch"] if r["best_epoch"] is not None else "—"
        params = r["n_params"] if r["n_params"] is not None else "—"
        print(f"{r['control']:<28}{r['seed']:>5}{r['status']:>8}{str(params):>8}"
              f"{mae:>10}{str(stop):>7}{str(bst):>7}")

    print(f"\nruntime={runtime:.1f}s  peak_rss={peak_gb:.3f} GB  "
          f"deterministic={deterministic}")
    outputs_ok = all_ok and deterministic
    print(f"PILOT {'PASS' if outputs_ok else 'FAIL'} — technical liveness only, "
          f"no scientific claim.")
    if not outputs_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
