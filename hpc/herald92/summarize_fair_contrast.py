"""HERALD 92, part A: the definitive complementarity gate.

Eight criteria, all declared before the array was submitted, none of which may be widened
afterwards. The verdict is one of two strings and there is no third option:

``COMPLEMENTARITY_SUPPORTED``      S3F is included in the model evaluation.
``COMPLEMENTARITY_NOT_SUPPORTED``  the claim is dropped; the model is still evaluated on
                                   S0 and S1, which the oracle already found identifiable
                                   in twenty seeds of twenty.

The contrast is *paired*. S3F and S4F at the same seed read the same latent state, the same
macro path and the same territorial graph, so the seed-by-seed difference of their pooling
gains isolates the one quantity that separates them: whether the signals' measurement noises
are independent. This is what the previous gate could not do, because its two scenarios also
differed in relational amplitude by a factor of three.
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

from src.data.synthetic.generate_france_multisignal_v92 import FAIR_SEEDS  # noqa: E402

# ── Declared before submission. Do not edit after a result is seen. ──────────
MIN_SEEDS = 16                       # of twenty
NULL_QUANTILE = 0.975
S0_MEDIAN_CEILING = 0.0005           # 0.05 percentage points of deviance
LEAVE_ONE_SEED_OUT_MUST_HOLD = True


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


def load(directory: Path) -> dict[str, dict[int, dict]]:
    by_scenario: dict[str, dict[int, dict]] = {}
    for path in sorted(directory.glob("fair_*.json")):
        report = json.loads(path.read_text())
        by_scenario.setdefault(report["scenario"], {})[report["seed"]] = report
    return by_scenario


def envelope(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {"n": 0}
    return {"n": int(values.size), "mean": float(values.mean()),
            "median": float(np.median(values)),
            "sd": float(values.std(ddof=1)) if values.size > 1 else float("nan"),
            "q02_5": float(np.quantile(values, 0.025)),
            "q97_5": float(np.quantile(values, NULL_QUANTILE)),
            "max": float(values.max())}


def evaluate(by_scenario: dict, seeds: list[int], equality_matched: bool) -> dict:
    """Apply the eight criteria to a given seed set. Reused for leave-one-seed-out."""
    def column(scenario: str, key: str) -> np.ndarray:
        entries = by_scenario.get(scenario, {})
        return np.array([entries[seed]["summary"][key] for seed in seeds
                         if seed in entries], float)

    null_paired = column("S0_NULL", "paired_pooling_improvement")
    null_ceiling = float(np.quantile(null_paired, NULL_QUANTILE)) if null_paired.size else float("nan")

    s3_paired = column("S3F_COMPLEMENTARY", "paired_pooling_improvement")
    s4_paired = column("S4F_REDUNDANT", "paired_pooling_improvement")
    s3_own = column("S3F_COMPLEMENTARY", "best_own_signal_gain")
    s3_pooled = column("S3F_COMPLEMENTARY", "best_pooled_signal_gain")
    s3_duplicate = column("S3F_COMPLEMENTARY", "duplicate_adds")

    paired_seeds = [seed for seed in seeds
                    if seed in by_scenario.get("S3F_COMPLEMENTARY", {})
                    and seed in by_scenario.get("S4F_REDUNDANT", {})]
    difference = np.array(
        [by_scenario["S3F_COMPLEMENTARY"][seed]["summary"]["paired_pooling_improvement"]
         - by_scenario["S4F_REDUNDANT"][seed]["summary"]["paired_pooling_improvement"]
         for seed in paired_seeds], float)

    required = int(np.ceil(MIN_SEEDS * len(seeds) / len(FAIR_SEEDS)))
    checks = {
        "null_stays_inside_its_envelope":
            bool(null_paired.size and abs(np.median(null_paired)) < S0_MEDIAN_CEILING),
        "complementary_improves_the_best_individual_signal":
            int(np.sum(s3_pooled > s3_own)) >= required,
        "complementary_beats_redundant_seed_by_seed":
            int(np.sum(difference > 0)) >= required,
        "paired_difference_median_clears_the_null":
            bool(difference.size and np.median(difference) > 0
                 and np.median(difference) > null_ceiling),
        "complementary_beats_the_duplicate_channel":
            bool(s3_paired.size and s3_duplicate.size
                 and np.median(s3_paired) > np.median(s3_duplicate)),
        "redundant_shows_no_false_complementarity":
            bool(s4_paired.size and np.median(s4_paired) <= null_ceiling),
        "equality_audit_passed": bool(equality_matched),
    }
    return {
        "seeds": seeds, "required_seeds": required,
        "null_ceiling": null_ceiling,
        "null_envelope": envelope(null_paired),
        "s3f": {"paired": envelope(s3_paired), "own": envelope(s3_own),
                "pooled": envelope(s3_pooled), "duplicate_adds": envelope(s3_duplicate)},
        "s4f": {"paired": envelope(s4_paired)},
        "paired_difference": envelope(difference),
        "seeds_s3_beats_s4": int(np.sum(difference > 0)),
        "seeds_pooling_beats_own": int(np.sum(s3_pooled > s3_own)),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--equality-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    by_scenario = load(arguments.task_dir)
    audit = json.loads(arguments.equality_audit.read_text())
    equality_matched = bool(audit.get("matched"))

    seeds = sorted(set(FAIR_SEEDS) & set().union(
        *[set(entries) for entries in by_scenario.values()] or [set()]))
    found = sum(len(entries) for entries in by_scenario.values())
    if found < 3 * len(FAIR_SEEDS):
        print(f"WARNING: {found} of {3 * len(FAIR_SEEDS)} task files present")

    main_result = evaluate(by_scenario, seeds, equality_matched)

    # Criterion seven: no single seed may carry the verdict. Every leave-one-seed-out
    # subset must reach the same conclusion on the three seed-counting criteria.
    fragile: list[int] = []
    if LEAVE_ONE_SEED_OUT_MUST_HOLD and len(seeds) > 3:
        watched = ("complementary_improves_the_best_individual_signal",
                   "complementary_beats_redundant_seed_by_seed",
                   "paired_difference_median_clears_the_null")
        for dropped in seeds:
            subset = evaluate(by_scenario, [s for s in seeds if s != dropped],
                              equality_matched)
            if any(subset["checks"][name] != main_result["checks"][name]
                   for name in watched):
                fragile.append(dropped)
    main_result["checks"]["verdict_survives_dropping_any_single_seed"] = not fragile
    main_result["fragile_seeds"] = fragile

    supported = all(main_result["checks"].values())
    verdict = {
        "kind": "herald92_fair_contrast_verdict",
        "tasks_found": found, "tasks_expected": 3 * len(FAIR_SEEDS),
        "thresholds": {"min_seeds": MIN_SEEDS, "null_quantile": NULL_QUANTILE,
                       "s0_median_ceiling": S0_MEDIAN_CEILING},
        **main_result,
        "verdict": "COMPLEMENTARITY_SUPPORTED" if supported
                   else "COMPLEMENTARITY_NOT_SUPPORTED",
    }
    atomic_json(verdict, arguments.out)

    print(f"null paired envelope: median={main_result['null_envelope'].get('median', float('nan')):+.4%} "
          f"q97.5={main_result['null_ceiling']:+.4%}")
    print(f"S3F paired: median={main_result['s3f']['paired'].get('median', float('nan')):+.4%}  "
          f"S4F paired: median={main_result['s4f']['paired'].get('median', float('nan')):+.4%}")
    print(f"paired difference S3F-S4F: median="
          f"{main_result['paired_difference'].get('median', float('nan')):+.4%}  "
          f"positive in {main_result['seeds_s3_beats_s4']}/{len(seeds)} seeds")
    print(f"S3F pooling beats own driver in {main_result['seeds_pooling_beats_own']}/{len(seeds)} seeds "
          f"(need {main_result['required_seeds']})")
    print("\ngate:")
    for name, value in verdict["checks"].items():
        print(f"  {'PASS' if value else 'FAIL'}  {name}")
    if fragile:
        print(f"  fragile seeds: {fragile}")
    print(f"\nverdict = {verdict['verdict']}")
    return 0 if supported else 2


if __name__ == "__main__":
    sys.exit(main())
