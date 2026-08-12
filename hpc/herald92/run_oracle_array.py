"""HERALD 92 stage 3-4: the null envelope and the observable multisignal oracle.

One Slurm array task per (scenario, seed). Each writes an independent JSON; the summariser
builds the null envelope from S0 and evaluates the pre-declared gate against it.

Calibration seeds only. The final seeds 9401-9405 are never touched here, and a guard
enforces it.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_france_multisignal_v92 import (  # noqa: E402
    CALIBRATION_SEEDS, FINAL_SEEDS, SCENARIOS, MultisignalConfig,
    generate_multisignal,
)
from src.modeles.france_ze2020 import herald92_multisignal_oracle as h92  # noqa: E402

# Combinations carried over from HERALD 91, plus the redundancy controls.
COMBINATIONS = {
    "C1": ["headcount", "payroll"],
    "C2": ["headcount", "unemployment"],
    "C3": ["headcount", "establishments"],
    "C4": ["headcount", "payroll", "establishments"],
    "C5": ["headcount", "payroll", "unemployment"],
    "C6": ["headcount", "payroll", "establishments", "unemployment"],
    "C7": ["headcount", "payroll", "establishments", "unemployment", "creations"],
}


def atomic_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w") as stream:
            json.dump(payload, stream, indent=2, default=lambda value: value.tolist())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def task_grid() -> list[tuple[str, int]]:
    return [(scenario, seed) for scenario in SCENARIOS for seed in CALIBRATION_SEEDS]


def run_task(scenario: str, seed: int, n_zones: int, n_score: int) -> dict:
    if seed in FINAL_SEEDS:
        raise ValueError(f"seed {seed} is a final seed and must not calibrate anything")
    started = time.time()
    dataset = generate_multisignal(MultisignalConfig(
        seed=seed, n_zones=n_zones, scenario=scenario))
    full = h92.evaluate_scenario(dataset, n_score=n_score)

    graphs = h92.build_graphs(dataset, seed=92000)
    combinations = {}
    for label, names in COMBINATIONS.items():
        joint = h92.score_joint(dataset, names, graphs, n_score)
        combinations[label] = {
            "signals": names,
            "best_own": joint["best_own_signal_gain"],
            "best_pooled": joint["best_pooled_signal_gain"],
            "paired_improvement": joint["mean_pairwise_improvement"],
            "n_improved": joint["n_signals_improved_by_pooling"],
            "pooling_weights": joint["pooling_weights"],
        }

    # Redundancy controls, on the same folds and the same graphs.
    r1 = h92.duplicate_signal(dataset, "headcount", "headcount_copy")
    r2 = h92.duplicate_signal(dataset, "headcount", "headcount_jitter",
                              jitter=0.01, seed=seed + 5)
    controls = {}
    for label, alias, source in (("R1", "headcount_copy", r1),
                                 ("R2", "headcount_jitter", r2)):
        joint = h92.score_joint(source, list(dataset["signals"]) + [alias],
                                h92.build_graphs(source, seed=92000), n_score)
        controls[label] = {
            "best_pooled": joint["best_pooled_signal_gain"],
            "paired_improvement": joint["mean_pairwise_improvement"],
        }

    return {
        "kind": "herald92_oracle_task",
        "scenario": scenario, "seed": seed, "n_zones": n_zones, "n_score": n_score,
        "elapsed_seconds": round(time.time() - started, 1),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "calibration_seed": True,
        "summary": {
            "best_own_signal_gain": full["best_own_signal_gain"],
            "best_pooled_signal_gain": full["best_pooled_signal_gain"],
            "paired_pooling_improvement": full["paired_pooling_improvement"],
            "n_signals_improved_by_pooling": full["n_signals_improved_by_pooling"],
            "joint_beats_best_individual": full["joint_beats_best_individual"],
            "duplicate_adds": full["duplicate_control"]["duplicate_adds"],
            "best_individual_gain": full["best_individual_gain"],
        },
        "individual": {name: {"gain_true_vs_permuted": entry["gain_true_vs_permuted"],
                              "gain_true_vs_degree": entry["gain_true_vs_degree"],
                              "gain_true_vs_null": entry["gain_true_vs_null"],
                              "n_origins": entry["n_origins"]}
                       for name, entry in full["individual"].items()},
        "combinations": combinations,
        "redundancy_controls": controls,
        "leave_one_out": full["leave_one_out"],
        "generator_diagnostics": dataset["calibration"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--n-zones", type=int, default=280)
    parser.add_argument("--n-score", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    grid = task_grid()
    if arguments.dry_run:
        print(json.dumps({
            "kind": "herald92_oracle_plan", "n_tasks": len(grid),
            "scenarios": list(SCENARIOS), "seeds": list(CALIBRATION_SEEDS),
            "final_seeds_excluded": list(FINAL_SEEDS),
            "combinations": {k: v for k, v in COMBINATIONS.items()},
            "n_zones": arguments.n_zones, "n_score": arguments.n_score,
            "first_tasks": grid[:3], "last_task": grid[-1]}, indent=2))
        return 0
    if arguments.task_id is None or arguments.out_dir is None:
        parser.error("--task-id and --out-dir are required unless --dry-run")
    if not 0 <= arguments.task_id < len(grid):
        parser.error(f"task-id must lie in [0, {len(grid) - 1}]")

    scenario, seed = grid[arguments.task_id]
    report = run_task(scenario, seed, arguments.n_zones, arguments.n_score)
    atomic_json(report, arguments.out_dir / f"oracle_{scenario}_{seed}.json")
    print(f"{scenario} seed={seed} "
          f"own={report['summary']['best_own_signal_gain']:+.4%} "
          f"pooled={report['summary']['best_pooled_signal_gain']:+.4%} "
          f"paired={report['summary']['paired_pooling_improvement']:+.4%} "
          f"[{report['elapsed_seconds']}s]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
