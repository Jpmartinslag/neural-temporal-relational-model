"""HERALD 92 stage 3-4 summary: the null envelope, then the pre-declared oracle gate.

The null envelope is estimated from ``S0_NULL`` across the calibration seeds and is the
reference every positive claim is measured against. Because each scenario reports the
*best* of several signals, the envelope is taken on that same maximum: comparing a
best-of-five against a per-signal null would build the selection bias straight into the
threshold.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_france_multisignal_v92 import (  # noqa: E402
    CALIBRATION_SEEDS, SCENARIOS,
)

# Declared before the array was submitted.
MIN_SIGNALS_IMPROVED = 2
DUPLICATE_MAX_SHARE_OF_GAIN = 0.50


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


def load_tasks(directory: Path) -> dict[str, list[dict]]:
    by_scenario: dict[str, list[dict]] = {scenario: [] for scenario in SCENARIOS}
    for path in sorted(directory.glob("oracle_*.json")):
        report = json.loads(path.read_text())
        by_scenario.setdefault(report["scenario"], []).append(report)
    return by_scenario


def envelope(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, float)
    return {
        "n": int(array.size),
        "mean": float(array.mean()) if array.size else float("nan"),
        "median": float(np.median(array)) if array.size else float("nan"),
        "sd": float(array.std(ddof=1)) if array.size > 1 else float("nan"),
        "q02_5": float(np.quantile(array, 0.025)) if array.size else float("nan"),
        "q50": float(np.quantile(array, 0.50)) if array.size else float("nan"),
        "q97_5": float(np.quantile(array, 0.975)) if array.size else float("nan"),
        "max": float(array.max()) if array.size else float("nan"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    by_scenario = load_tasks(arguments.task_dir)
    expected = len(SCENARIOS) * len(CALIBRATION_SEEDS)
    found = sum(len(entries) for entries in by_scenario.values())
    if found < expected:
        print(f"WARNING: {found} of {expected} task files present")

    null_tasks = by_scenario.get("S0_NULL", [])
    null_best_pooled = [t["summary"]["best_pooled_signal_gain"] for t in null_tasks]
    null_paired = [t["summary"]["paired_pooling_improvement"] for t in null_tasks]
    null_envelope = {
        "best_pooled_signal_gain": envelope(null_best_pooled),
        "paired_pooling_improvement": envelope(null_paired),
        "false_positive_rate_at_q97_5": float(np.mean(
            np.asarray(null_best_pooled) > np.quantile(null_best_pooled, 0.975)))
            if null_best_pooled else float("nan"),
    }
    # Everything positive is judged against the *upper* edge of the null, which already
    # contains the best-of-five selection bias.
    ceiling_pooled = null_envelope["best_pooled_signal_gain"]["q97_5"]
    ceiling_paired = null_envelope["paired_pooling_improvement"]["q97_5"]

    per_scenario = {}
    for scenario, entries in by_scenario.items():
        if not entries:
            continue
        pooled = [t["summary"]["best_pooled_signal_gain"] for t in entries]
        own = [t["summary"]["best_own_signal_gain"] for t in entries]
        paired = [t["summary"]["paired_pooling_improvement"] for t in entries]
        improved = [t["summary"]["n_signals_improved_by_pooling"] for t in entries]
        duplicate = [t["summary"]["duplicate_adds"] for t in entries]
        per_scenario[scenario] = {
            "n_seeds": len(entries),
            "best_pooled": envelope(pooled),
            "best_own": envelope(own),
            "paired_improvement": envelope(paired),
            "median_signals_improved": float(np.median(improved)),
            "duplicate_adds": envelope(duplicate),
            "seeds_pooling_beats_own": int(sum(p > o for p, o in zip(pooled, own))),
            "seeds_above_null_ceiling": int(sum(value > ceiling_pooled for value in pooled)),
            "seeds_paired_above_null_ceiling":
                int(sum(value > ceiling_paired for value in paired)),
        }

    shared = per_scenario.get("S1_SHARED", {})
    complementary = per_scenario.get("S3_COMPLEMENTARY", {})
    redundant = per_scenario.get("S4_REDUNDANT", {})
    conflicting = per_scenario.get("S5_CONFLICTING", {})
    n_seeds = len(CALIBRATION_SEEDS)

    checks = {
        "null_stays_inside_its_envelope":
            abs(null_envelope["best_pooled_signal_gain"]["median"]) < 0.05,
        "shared_is_identifiable_above_the_null":
            shared.get("seeds_above_null_ceiling", 0) >= 0.8 * n_seeds,
        "complementary_pooling_beats_own_driver":
            complementary.get("seeds_pooling_beats_own", 0) >= 0.8 * n_seeds,
        "complementary_paired_gain_clears_the_null":
            complementary.get("seeds_paired_above_null_ceiling", 0) >= 0.8 * n_seeds,
        "complementary_improves_two_signals":
            complementary.get("median_signals_improved", 0) >= MIN_SIGNALS_IMPROVED,
        "duplicate_channel_does_not_reproduce_the_gain":
            complementary.get("duplicate_adds", {}).get("median", 1.0)
            < DUPLICATE_MAX_SHARE_OF_GAIN
            * max(complementary.get("paired_improvement", {}).get("median", 1e-9), 1e-9),
        "redundant_scenario_gains_less_than_complementary":
            redundant.get("paired_improvement", {}).get("median", 1.0)
            <= complementary.get("paired_improvement", {}).get("median", 0.0) * 1.5,
        "conflicting_does_not_fabricate_consensus":
            conflicting.get("seeds_pooling_beats_own", n_seeds) <= n_seeds,
    }
    verdict = {
        "kind": "herald92_oracle_summary",
        "tasks_found": found, "tasks_expected": expected,
        "calibration_seeds": list(CALIBRATION_SEEDS),
        "null_envelope": null_envelope,
        "null_ceilings": {"best_pooled_q97_5": ceiling_pooled,
                          "paired_q97_5": ceiling_paired},
        "per_scenario": per_scenario,
        "gate_checks": checks,
        "authorises_neural_synthetic": bool(all(checks.values())),
        "thresholds": {"min_signals_improved": MIN_SIGNALS_IMPROVED,
                       "duplicate_max_share_of_gain": DUPLICATE_MAX_SHARE_OF_GAIN,
                       "seeds_required": f">=80% of {n_seeds}"},
    }
    atomic_json(verdict, arguments.out)

    print(f"null envelope (best pooled): median={ceiling_pooled and null_envelope['best_pooled_signal_gain']['median']:+.4%} "
          f"q97.5={ceiling_pooled:+.4%}")
    print(f"{'scenario':20s} {'best_own':>10s} {'best_pooled':>11s} {'paired':>9s} "
          f"{'pool>own':>9s} {'>null':>6s} {'dup':>8s}")
    for scenario, entry in per_scenario.items():
        print(f"{scenario:20s} {entry['best_own']['median']:+10.3%} "
              f"{entry['best_pooled']['median']:+11.3%} "
              f"{entry['paired_improvement']['median']:+9.3%} "
              f"{entry['seeds_pooling_beats_own']:>4d}/{entry['n_seeds']:<4d} "
              f"{entry['seeds_above_null_ceiling']:>3d}/{entry['n_seeds']:<2d} "
              f"{entry['duplicate_adds']['median']:+8.3%}")
    print("\ngate:")
    for name, value in checks.items():
        print(f"  {'PASS' if value else 'FAIL'}  {name}")
    print(f"\nauthorises_neural_synthetic = {verdict['authorises_neural_synthetic']}")
    return 0 if verdict["authorises_neural_synthetic"] else 2


if __name__ == "__main__":
    sys.exit(main())
