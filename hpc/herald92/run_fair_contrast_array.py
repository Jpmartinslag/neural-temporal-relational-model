"""HERALD 92, part A: the matched complementarity contrast.

Three scenarios, twenty fresh seeds, sixty tasks. ``S0_NULL`` supplies the false-positive
floor; ``S3F_COMPLEMENTARY`` and ``S4F_REDUNDANT`` are identical in every audited quantity
except whether the signals' measurement noises are independent or shared.

The seeds 9501-9520 have never been used. The calibration seeds 9301-9320 belong to the
development arrays 7864671 and 7864792 and are not reused here; the final seeds 9401-9405
are reserved for the model evaluation and a guard kills any attempt to use them.
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
    CALIBRATION_SEEDS, FAIR_SCENARIOS, FAIR_SEEDS, FINAL_SEEDS, MultisignalConfig,
    generate_multisignal,
)
from src.modeles.france_ze2020 import herald92_multisignal_oracle as h92  # noqa: E402


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
    return [(scenario, seed) for scenario in FAIR_SCENARIOS for seed in FAIR_SEEDS]


def run_task(scenario: str, seed: int, n_zones: int, n_score: int) -> dict:
    if seed in FINAL_SEEDS:
        raise ValueError(f"seed {seed} is a final seed and must not calibrate anything")
    if seed in CALIBRATION_SEEDS:
        raise ValueError(f"seed {seed} belongs to the development arrays; the fair "
                         "contrast runs on fresh seeds only")
    started = time.time()
    dataset = generate_multisignal(MultisignalConfig(
        seed=seed, n_zones=n_zones, scenario=scenario))
    full = h92.evaluate_scenario(dataset, n_score=n_score)
    calibration = dataset["calibration"]
    return {
        "kind": "herald92_fair_contrast_task",
        "scenario": scenario, "seed": seed, "n_zones": n_zones, "n_score": n_score,
        "elapsed_seconds": round(time.time() - started, 1),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "summary": {
            "best_own_signal_gain": full["best_own_signal_gain"],
            "best_pooled_signal_gain": full["best_pooled_signal_gain"],
            "paired_pooling_improvement": full["paired_pooling_improvement"],
            "n_signals_improved_by_pooling": full["n_signals_improved_by_pooling"],
            "best_individual_gain": full["best_individual_gain"],
            "duplicate_adds": full["duplicate_control"]["duplicate_adds"],
        },
        "individual": {name: {"gain_true_vs_permuted": entry["gain_true_vs_permuted"],
                              "gain_true_vs_degree": entry["gain_true_vs_degree"],
                              "gain_true_vs_null": entry["gain_true_vs_null"]}
                       for name, entry in full["individual"].items()},
        "leave_one_out": full["leave_one_out"],
        "equality_fingerprint": {
            "relational_share": calibration["relational_share"],
            "common_share": calibration["common_share"],
            "noise_groups": sorted({entry["noise_group"]
                                    for entry in calibration["loadings"].values()}),
            "state_checksum": float(np.asarray(dataset["truth"]["state"]).sum()),
        },
        "generator_diagnostics": calibration,
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
        print(json.dumps({"kind": "herald92_fair_contrast_plan", "n_tasks": len(grid),
                          "scenarios": list(FAIR_SCENARIOS), "seeds": list(FAIR_SEEDS),
                          "n_zones": arguments.n_zones}, indent=2))
        return 0
    if arguments.task_id is None or arguments.out_dir is None:
        parser.error("--task-id and --out-dir are required unless --dry-run")
    if not 0 <= arguments.task_id < len(grid):
        parser.error(f"task-id must lie in [0, {len(grid) - 1}]")

    scenario, seed = grid[arguments.task_id]
    report = run_task(scenario, seed, arguments.n_zones, arguments.n_score)
    atomic_json(report, arguments.out_dir / f"fair_{scenario}_{seed}.json")
    print(f"{scenario} seed={seed} "
          f"own={report['summary']['best_own_signal_gain']:+.4%} "
          f"pooled={report['summary']['best_pooled_signal_gain']:+.4%} "
          f"paired={report['summary']['paired_pooling_improvement']:+.4%} "
          f"[{report['elapsed_seconds']}s]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
