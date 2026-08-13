"""HERALD 95: read the ladder and apply the interpretation declared before it ran.

The rules are fixed here and are the ones stated in the instruction that commissioned the
stage, not rules chosen after seeing the numbers:

    oracle fails                          -> the signal is not observable at that scale
    oracle passes and network fails       -> a limitation of the model, not of the benchmark
    network passes only at larger scale   -> estimate the sensitivity threshold
    both rise while N0 stays flat         -> genuine relational recovery
    network gains in N0, or does not
      respond monotonically to the scale  -> the gain is not relational

Scale four is a stress test and is excluded from every threshold and every verdict: its clip
saturates about a fifth of the cells, so the world there is not the same one with more
mechanism.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.modeles.france_ze2020 import herald95_scale_ladder as ladder  # noqa: E402

# A gain smaller than this is not distinguishable from fitting variance. Same figure as
# HERALD 94's gate, deliberately: the two stages must not use different rulers.
MIN_GAIN = 0.01
NULL_SCENARIO = "N0_NULL"
PRIMARY = "headcount"


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
    finite = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(statistics.median(finite)) if finite else float("nan")


def load(directory: Path) -> dict:
    runs = defaultdict(list)
    for path in sorted(directory.glob("ladder_*.json")):
        report = json.loads(path.read_text())
        runs[(report["scenario"], float(report["relational_scale"]))].append(report)
    return runs


def collect(reports: list[dict]) -> dict:
    def observable(report, field):
        scale = str(report["relational_scale"])
        return report["observable_diagnostics"]["per_scale"][scale]["observable"][PRIMARY][field]

    return {
        "n_seeds": len(reports),
        "worlds_are_paired": all(all(r["worlds_are_paired"].values()) for r in reports),
        "observable_relational_rms": median(observable(r, "relational_rms") for r in reports),
        "observable_residual_rms": median(observable(r, "residual_rms") for r in reports),
        "observable_snr": median(observable(r, "snr") for r in reports),
        "clipped_share": median(r["calibration"]["clipped_share"][PRIMARY] for r in reports),
        "oracle_gain": median(
            r["arms"]["oracle_relational"]["gain_over_ridge_linear"] for r in reports),
        "oracle_gain_per_seed": [
            float(r["arms"]["oracle_relational"]["gain_over_ridge_linear"]) for r in reports],
        "network_gain": median(
            r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"] for r in reports),
        "network_gain_per_seed": [
            float(r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"]) for r in reports],
        "network_gain_after_interaction_destroyed": median(
            r["controls"]["interaction_destroyed"]["mlp_nonlinear"]["gain_over_ridge_linear"]
            for r in reports),
        "edge_auprc": median(r["edge_recovery"]["auprc"] for r in reports),
        "edge_prevalence": median(r["edge_recovery"]["prevalence"] for r in reports),
        "edge_f1": median(r["edge_recovery"]["edge_f1"] for r in reports),
        "edge_dense_correlation": median(
            r["edge_recovery"]["dense_correlation"] for r in reports),
        "score_correlation_with_prior": median(
            r["edge_recovery"]["score_diagnostics"]["correlation_with_prior"]
            for r in reports),
        "score_correlation_with_truth": median(
            r["edge_recovery"]["score_diagnostics"]["correlation_with_true_propagation"]
            for r in reports),
    }


def monotone(values: list[float], tolerance: float = 0.0) -> bool:
    return all(later >= earlier - tolerance
               for earlier, later in zip(values, values[1:]))


def first_scale_above(scales: list[float], values: list[float], floor: float) -> float | None:
    for scale, value in zip(scales, values):
        if scale > 0.0 and np.isfinite(value) and value > floor:
            return scale
    return None


def interpret(table: dict, scenario: str) -> dict:
    """The declared decision rules, applied to the interpretive range only."""
    scales = [s for s in ladder.INTERPRETIVE_SCALES if (scenario, s) in table]
    oracle = [table[(scenario, s)]["oracle_gain"] for s in scales]
    network = [table[(scenario, s)]["network_gain"] for s in scales]
    snr = [table[(scenario, s)]["observable_snr"] for s in scales]

    null_network = [table[(NULL_SCENARIO, s)]["network_gain"]
                    for s in scales if (NULL_SCENARIO, s) in table]
    network_gains_in_null = median(null_network) > MIN_GAIN

    oracle_start = first_scale_above(scales, oracle, MIN_GAIN)
    network_start = first_scale_above(scales, network, MIN_GAIN)
    oracle_monotone = monotone(oracle)
    network_monotone = monotone(network, tolerance=MIN_GAIN)

    if network_gains_in_null or not network_monotone:
        verdict = "NETWORK_GAIN_IS_NOT_RELATIONAL"
    elif oracle_start is None:
        verdict = "SIGNAL_NOT_OBSERVABLE_AT_THESE_SCALES"
    elif network_start is None:
        verdict = "MODEL_LIMITATION_NOT_SCALE_LIMITATION"
    elif network_start > oracle_start:
        verdict = "NETWORK_RECOVERS_ONLY_ABOVE_THRESHOLD"
    else:
        verdict = "GENUINE_RELATIONAL_RECOVERY"

    return {
        "scales": scales,
        "observable_snr": snr,
        "oracle_gain": oracle, "network_gain": network,
        "oracle_is_monotone_in_scale": oracle_monotone,
        "network_is_monotone_in_scale": network_monotone,
        "network_gains_in_null_scenario": network_gains_in_null,
        "scale_at_which_oracle_starts_recovering": oracle_start,
        "scale_at_which_network_starts_recovering": network_start,
        "unit_scale_is_observable": bool(
            (scenario, 1.0) in table
            and table[(scenario, 1.0)]["oracle_gain"] > MIN_GAIN),
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    runs = load(arguments.task_dir)
    table = {key: collect(reports) for key, reports in runs.items()}
    scenarios = sorted({key[0] for key in table})

    interpretation = {scenario: interpret(table, scenario)
                      for scenario in scenarios if scenario != NULL_SCENARIO}
    null_flat = all(
        abs(table[(NULL_SCENARIO, s)]["observable_snr"]) < 1e-12
        for s in ladder.SCALES if (NULL_SCENARIO, s) in table)

    verdict = {
        "kind": "herald95_ladder_summary",
        "interpretive_scales": list(ladder.INTERPRETIVE_SCALES),
        "stress_scales": list(ladder.STRESS_SCALES),
        "min_gain": MIN_GAIN,
        "table": {f"{key[0]}@{key[1]}": value for key, value in sorted(table.items())},
        "null_scenario_is_flat_across_scales": null_flat,
        "all_worlds_paired": all(entry["worlds_are_paired"] for entry in table.values()),
        "interpretation": interpretation,
    }
    atomic_json(verdict, arguments.out)

    print(f"{'scenario':16s}{'scale':>6s}{'snr':>8s}{'clip':>7s}{'oracle':>9s}"
          f"{'network':>9s}{'destroyed':>11s}{'auprc':>9s}{'dense':>10s}")
    for key in sorted(table):
        entry = table[key]
        stress = " *" if key[1] in ladder.STRESS_SCALES else "  "
        print(f"{key[0]:16s}{key[1]:6g}{entry['observable_snr']:8.4f}"
              f"{entry['clipped_share']:7.3f}{entry['oracle_gain']:+9.4f}"
              f"{entry['network_gain']:+9.4f}"
              f"{entry['network_gain_after_interaction_destroyed']:+11.4f}"
              f"{entry['edge_auprc']:9.5f}{entry['edge_dense_correlation']:10.6f}{stress}")
    print("\n* stress scale, excluded from every threshold and verdict\n")
    for scenario, entry in interpretation.items():
        print(f"{scenario}: {entry['verdict']}")
        print(f"    oracle starts at   {entry['scale_at_which_oracle_starts_recovering']}"
              f"   monotone={entry['oracle_is_monotone_in_scale']}")
        print(f"    network starts at  {entry['scale_at_which_network_starts_recovering']}"
              f"   monotone={entry['network_is_monotone_in_scale']}"
              f"   gains_in_null={entry['network_gains_in_null_scenario']}")
        print(f"    unit scale observable = {entry['unit_scale_is_observable']}")
    print(f"\nnull flat across scales = {null_flat}")
    print(f"all worlds paired = {verdict['all_worlds_paired']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
