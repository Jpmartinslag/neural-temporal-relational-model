"""HERALD 94, Layer 1: the declared gate on the composite signal.

Thresholds are fixed here, before submission, and are not edited after a result is seen. The
gate is applied to each candidate composite arm separately:

``ridge_composite``  the two *named* product composites, `C4` and `C6`, added to the linear
                     span. Passing means the pre-declared economic interactions carry it.
``mlp_nonlinear``    curvature found by the network itself, with no composite handed to it.
                     Passing means non-linear information is present whether or not the
                     declared products are the right ones.

The two can disagree, and the disagreement is informative rather than awkward: the network
passing alone says the interaction exists but was not the one hypothesised.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

# ── Declared before submission. ──────────────────────────────────────────────
# A gain smaller than this is not distinguishable from the arm's own fitting variance and is
# not counted as one. One per cent of the reference's squared error.
MIN_GAIN = 0.01
MIN_SEEDS = 4
MIN_ORIGINS = 8
# `duplicated` repeats a column already present, so it adds no information and any movement
# it shows is the regularisation responding to a changed design. A candidate arm must beat
# the reference by more than the duplicated arm does, not merely beat the reference.
DUPLICATED_CEILING = MIN_GAIN
# `C1`, `C2`, `C3` and `C5` are linear functions of columns already in the table, so a linear
# model spanning it contains them exactly. Their measured effect is not identically zero
# because adding collinear columns changes what the ridge penalty shrinks; the tolerance is
# the size of that artefact, not of an effect.
LINEAR_COMPOSITE_TOLERANCE = 0.05
# Under the interaction-destroyed control the gain must fall to at most this share of what it
# was. A gain that survives the permutation was never an interaction.
SURVIVING_GAIN_CEILING = 0.30
NULL_SCENARIO = "N0_NULL"
CANDIDATES = ("ridge_composite", "mlp_nonlinear")


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


def median(values) -> float:
    finite = [float(value) for value in values
              if value is not None and np.isfinite(value)]
    return float(np.median(finite)) if finite else float("nan")


def origins_won(report: dict, candidate: str, reference: str) -> tuple[int, int]:
    """Origins at which the candidate's squared error is below the reference's."""
    left = report["arms"][candidate]["per_origin_mse"]
    right = report["arms"][reference]["per_origin_mse"]
    shared = sorted(set(left) & set(right))
    won = sum(1 for origin in shared if left[origin] < right[origin])
    return won, len(shared)


def assess(candidate: str, runs: list[dict], null_runs: list[dict]) -> dict:
    over_single = [run["arms"][candidate]["gain_over_best_single"] for run in runs]
    over_linear = [run["arms"][candidate]["gain_over_ridge_linear"] for run in runs]
    duplicated = [run["arms"]["duplicated"]["gain_over_best_single"] for run in runs]
    linear_composites = [run["arms"]["ridge_linear_composites_only"]["gain_over_ridge_linear"]
                         for run in runs]
    in_sample_only = [
        run["arms"][candidate]["in_sample"]["mse"] < run["arms"]["ridge_linear"]["in_sample"]["mse"]
        and run["arms"][candidate]["gain_over_ridge_linear"] <= 0.0
        for run in runs]

    seeds_beating_single = sum(1 for value in over_single if value > MIN_GAIN)
    seeds_beating_linear = sum(1 for value in over_linear if value > MIN_GAIN)
    per_origin = [origins_won(run, candidate, "ridge_linear") for run in runs]
    origins_median = median([won for won, _ in per_origin])
    origins_total = int(np.median([total for _, total in per_origin])) if per_origin else 0

    destroyed = [run["controls"]["interaction_destroyed"][candidate]["gain_over_ridge_linear"]
                 for run in runs]
    null_gain = ([run["arms"][candidate]["gain_over_ridge_linear"] for run in null_runs]
                 if null_runs else [])

    observed = median(over_linear)
    surviving = median(destroyed)
    ratio = (float(surviving / observed) if np.isfinite(observed) and observed > MIN_GAIN
             else float("nan"))

    checks = {
        "beats_best_single": median(over_single) > MIN_GAIN,
        "beats_ridge_linear": median(over_linear) > MIN_GAIN,
        "gain_is_out_of_sample": not all(in_sample_only),
        "holds_in_enough_seeds": (seeds_beating_single >= MIN_SEEDS
                                  and seeds_beating_linear >= MIN_SEEDS),
        "holds_in_enough_origins": origins_median >= MIN_ORIGINS,
        "gain_lost_when_interaction_destroyed":
            (not np.isfinite(observed) or observed <= MIN_GAIN
             or (np.isfinite(ratio) and ratio <= SURVIVING_GAIN_CEILING)),
        "no_gain_in_null_scenario": (not null_gain) or median(null_gain) <= MIN_GAIN,
        "duplicated_channel_shows_no_gain": median(duplicated) <= DUPLICATED_CEILING,
    }
    return {
        "checks": checks,
        "informative": all(checks.values()),
        "gain_over_best_single_median": median(over_single),
        "gain_over_ridge_linear_median": median(over_linear),
        "gain_over_ridge_linear_per_seed": [float(value) for value in over_linear],
        "seeds_beating_best_single": seeds_beating_single,
        "seeds_beating_ridge_linear": seeds_beating_linear,
        "origins_won_median": origins_median, "origins_total": origins_total,
        "gain_after_interaction_destroyed_median": surviving,
        "surviving_share_of_gain": ratio,
        "gain_in_null_scenario_median": median(null_gain),
        "duplicated_gain_median": median(duplicated),
        "linear_composites_effect_median": median(linear_composites),
        "n_seeds": len(runs),
    }


def temporal_feature_verdict(runs: list[dict]) -> dict:
    """Question 1: do the temporal derivations add anything over the best single one?

    The linear arm spans every derivation; the floor is one of them. Their difference is the
    whole contribution of the temporal representation, before any question of non-linearity.
    """
    gains = [run["arms"]["ridge_linear"]["gain_over_best_single"] for run in runs]
    return {
        "gain_of_full_table_over_best_single_median": median(gains),
        "per_seed": [float(value) for value in gains],
        "temporal_features_add_information": median(gains) > MIN_GAIN,
        "best_single_columns": sorted({run["best_single_column"] for run in runs}),
    }


def load(directory: Path) -> dict[str, list[dict]]:
    runs = defaultdict(list)
    for path in sorted(directory.glob("layer1_*.json")):
        report = json.loads(path.read_text())
        runs[report["scenario"]].append(report)
    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    runs = load(arguments.task_dir)
    null_runs = runs.get(NULL_SCENARIO, [])

    table: dict[str, dict] = {}
    for scenario, scenario_runs in sorted(runs.items()):
        entry = {"n_seeds": len(scenario_runs),
                 "temporal_features": temporal_feature_verdict(scenario_runs)}
        for candidate in CANDIDATES:
            entry[candidate] = assess(candidate, scenario_runs,
                                      [] if scenario == NULL_SCENARIO else null_runs)
        entry["ablation_median"] = {
            signal: median([run["ablation_gain_when_signal_removed"].get(signal)
                            for run in scenario_runs])
            for signal in scenario_runs[0]["ablation_gain_when_signal_removed"]}
        entry["top_interactions"] = scenario_runs[0]["explanation"]["top_interactions"][:5]
        table[scenario] = entry

    # Layer 2 is authorised only where a composite carries non-linear information in a
    # scenario that actually contains a mechanism. Passing in `N0_NULL` would be a failure,
    # not a licence.
    mechanism_scenarios = [name for name in table if name != NULL_SCENARIO]
    passing = [name for name in mechanism_scenarios
               if any(table[name][candidate]["informative"] for candidate in CANDIDATES)]
    null_clean = all(not table[NULL_SCENARIO][candidate]["informative"]
                     for candidate in CANDIDATES) if NULL_SCENARIO in table else False

    verdict = {
        "kind": "herald94_layer1_summary",
        "thresholds": {"min_gain": MIN_GAIN, "min_seeds": MIN_SEEDS,
                       "min_origins": MIN_ORIGINS,
                       "surviving_gain_ceiling": SURVIVING_GAIN_CEILING,
                       "duplicated_ceiling": DUPLICATED_CEILING,
                       "linear_composite_tolerance": LINEAR_COMPOSITE_TOLERANCE},
        "table": table,
        "scenarios_with_an_informative_composite": passing,
        "null_scenario_stayed_clean": null_clean,
        "layer2_authorised": bool(passing) and null_clean,
        "layer2_reason": (
            "a composite carries non-linear information and the null scenario stayed clean"
            if passing and null_clean else
            "the null scenario did not stay clean; no gain elsewhere can be trusted"
            if not null_clean else
            "no composite cleared the gate in any scenario containing a mechanism"),
    }
    atomic_json(verdict, arguments.out)

    print(f"{'scenario':16s} {'temporal':>9s} "
          f"{'ridgeC vs lin':>14s} {'mlp vs lin':>11s} {'mlp vs single':>14s} "
          f"{'destroyed':>10s} {'dup':>7s}  verdict")
    for scenario, entry in table.items():
        ridge_c, mlp = entry["ridge_composite"], entry["mlp_nonlinear"]
        label = ("MLP" if mlp["informative"] else "") + \
                ("+NAMED" if ridge_c["informative"] else "")
        print(f"{scenario:16s} "
              f"{entry['temporal_features']['gain_of_full_table_over_best_single_median']:+9.4f} "
              f"{ridge_c['gain_over_ridge_linear_median']:+14.4f} "
              f"{mlp['gain_over_ridge_linear_median']:+11.4f} "
              f"{mlp['gain_over_best_single_median']:+14.4f} "
              f"{mlp['gain_after_interaction_destroyed_median']:+10.4f} "
              f"{mlp['duplicated_gain_median']:+7.4f}  {label or 'none'}")
    print("\ngate detail, per scenario and candidate:")
    for scenario, entry in table.items():
        for candidate in CANDIDATES:
            print(f"  {scenario} / {candidate}")
            for name, value in entry[candidate]["checks"].items():
                print(f"    {'PASS' if value else 'FAIL'}  {name}")
    print(f"\nlayer 2 authorised = {verdict['layer2_authorised']} "
          f"({verdict['layer2_reason']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
