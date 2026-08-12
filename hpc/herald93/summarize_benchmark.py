"""HERALD 93: the model gate and the four-method comparison table.

Two questions are kept apart on purpose, because conflating them is how a forecasting result
becomes a discovery claim. Forecasting is judged against persistence and against the other
methods. Relational recovery is judged against the synthetic truth, and *only* on the
synthetic benchmark. A method may pass one and fail the other, and the label says which.

    good forecast + good recovery  ->  RELATIONAL_MODEL_SUPPORTED
    good forecast + poor recovery  ->  PREDICTIVE_ONLY_NO_RELATIONAL_DISCOVERY_CLAIM
    poor forecast + good recovery  ->  STRUCTURE_RECOVERED_WITHOUT_PREDICTIVE_VALUE
    neither                        ->  NOT_SUPPORTED_IN_THIS_SCENARIO

Thresholds are declared here and were fixed before the grid was submitted.
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

# ── Declared before submission. Not to be edited after a result is seen. ─────
EDGE_F1_MIN = 0.50
DENSE_CORRELATION_MIN = 0.30
STABILITY_MIN = 0.90
S0_ADDED_EDGE_MAX = 0.10
EVENT_F1_MIN = 0.30
FORECAST_SKILL_MIN = 0.0          # must at least match persistence


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


def median(values: list[float]) -> float:
    finite = [value for value in values if value is not None and np.isfinite(value)]
    return float(np.median(finite)) if finite else float("nan")


def classify(s1_runs: list[dict], s0_runs: list[dict]) -> dict:
    """Apply the recovery gate to one method at one width.

    ``s1_runs`` carry the recovery evidence; ``s0_runs`` carry the false-positive control.
    Both are needed: a method that finds the graph in S1 but also finds one in S0 has found
    nothing, and reporting only the first number would hide it.
    """
    edge_f1 = [run["relational"].get("edge_f1") for run in s1_runs]
    dense = [run["relational"].get("dense_correlation") for run in s1_runs]
    auprc = [run["relational"].get("auprc") for run in s1_runs]
    prevalence = [run["relational"].get("prevalence") for run in s1_runs]
    events = [run.get("events", {}).get("event_f1") for run in s1_runs]
    added_s0 = [run["relational"].get("predicted_added_edge_rate") for run in s0_runs]
    skill = [run["forecast"].get("skill_vs_persistence") for run in s1_runs]
    gradient = [max((value for key, value in run.get("gradients", {}).items()
                     if key in ("scorer", "pair_net", "embed_source")), default=0.0)
                for run in s1_runs]

    finite_f1 = [value for value in edge_f1 if value is not None and np.isfinite(value)]
    stability = (float(1.0 - np.std(finite_f1) / max(abs(np.mean(finite_f1)), 1e-9))
                 if len(finite_f1) > 1 else float("nan"))
    event_median = median(events)

    checks = {
        "edge_f1_at_least_0_50": median(edge_f1) >= EDGE_F1_MIN,
        "dense_correlation_at_least_0_30": median(dense) >= DENSE_CORRELATION_MIN,
        "stability_across_seeds_at_least_0_90":
            bool(np.isfinite(stability)) and stability >= STABILITY_MIN,
        "false_edge_rate_in_s0_at_most_0_10": median(added_s0) <= S0_ADDED_EDGE_MAX,
        "auprc_above_prevalence": median(auprc) > median(prevalence),
        # A scenario whose truth never moves has no events to find. Reporting a failed F1
        # there would punish the method for the benchmark's calendar, so the criterion is
        # skipped, explicitly, rather than silently scored zero.
        "typed_event_f1_at_least_0_30":
            True if not np.isfinite(event_median) else event_median >= EVENT_F1_MIN,
        "relational_gradient_is_non_zero": median(gradient) > 0.0,
    }
    forecast_ok = median(skill) >= FORECAST_SKILL_MIN
    recovery_ok = all(checks.values())
    label = ("RELATIONAL_MODEL_SUPPORTED" if forecast_ok and recovery_ok else
             "PREDICTIVE_ONLY_NO_RELATIONAL_DISCOVERY_CLAIM" if forecast_ok else
             "STRUCTURE_RECOVERED_WITHOUT_PREDICTIVE_VALUE" if recovery_ok else
             "NOT_SUPPORTED_IN_THIS_SCENARIO")
    return {
        "checks": checks,
        "relational_recovery_supported": recovery_ok,
        "forecast_at_least_persistence": forecast_ok,
        "label": label,
        "edge_f1_median": median(edge_f1), "dense_correlation_median": median(dense),
        "auprc_median": median(auprc), "prevalence_median": median(prevalence),
        "event_f1_median": event_median, "stability": stability,
        "s0_added_edge_rate_median": median(added_s0),
        "forecast_skill_median": median(skill),
        "n_seeds": len(s1_runs),
    }


def load(directory: Path) -> dict:
    runs = defaultdict(list)
    for path in sorted(directory.glob("bench_*.json")):
        report = json.loads(path.read_text())
        runs[(report["method"], report["width"], report["scenario"])].append(report)
    return runs


def choose_width(per_width: dict[int, dict]) -> tuple[int | None, str]:
    """Configuration chosen on the synthetic results alone, in the declared order.

    False-positive control first, then structural recovery, then stability, then frugality,
    then forecast. Choosing on forecast error alone is what would turn this study into a
    forecasting competition; choosing on France would make the synthetic benchmark
    decorative.
    """
    eligible = [width for width, entry in per_width.items()
                if entry["checks"]["false_edge_rate_in_s0_at_most_0_10"]]
    if not eligible:
        return None, "no width controlled false positives in S0"
    passing = [width for width in eligible
               if per_width[width]["relational_recovery_supported"]]
    if not passing:
        return None, "no width passed the recovery gate; no width is promoted"
    best = sorted(passing, key=lambda width: (
        -per_width[width]["edge_f1_median"],
        -per_width[width]["stability"],
        width))[0]
    return best, "recovery, then stability, then the smaller width"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    runs = load(arguments.task_dir)
    methods = sorted({key[0] for key in runs})
    widths = sorted({key[1] for key in runs})

    table = {}
    for method in methods:
        for width in widths:
            s1 = runs.get((method, width, "S1_SHARED"), [])
            s0 = runs.get((method, width, "S0_NULL"), [])
            if not s1:
                continue
            entry = classify(s1, s0)
            entry["cost"] = {
                "parameters": int(median([run["cost"]["parameters"] for run in s1])),
                "epochs": int(median([run["cost"]["epochs"] for run in s1])),
                "seconds": median([run["cost"]["total_seconds"] for run in s1]),
                "peak_memory_mb": median([run["cost"]["peak_memory_mb"] for run in s1]),
            }
            entry["capabilities"] = s1[0]["capabilities"]
            entry["abstention_rate"] = median(
                [run.get("abstention_rate") for run in s1
                 if run.get("abstention_rate") is not None])
            table[f"{method}@{width}"] = entry

    herald_widths = {width: table[f"herald@{width}"] for width in widths
                     if f"herald@{width}" in table}
    chosen, reason = choose_width(herald_widths) if herald_widths else (None, "no herald run")

    verdict = {
        "kind": "herald93_benchmark_summary",
        "thresholds": {"edge_f1": EDGE_F1_MIN, "dense_correlation": DENSE_CORRELATION_MIN,
                       "stability": STABILITY_MIN, "s0_added_edge": S0_ADDED_EDGE_MAX,
                       "event_f1": EVENT_F1_MIN},
        "table": table,
        "chosen_herald_width": chosen,
        "width_choice_reason": reason,
        "france_decision": (
            "CASE_A_APPLY_WITH_RELATIONAL_CLAIM" if chosen is not None else
            "CASE_B_PREDICTIVE_ONLY" if any(
                entry["forecast_at_least_persistence"]
                for key, entry in table.items() if key.startswith("herald@"))
            else "CASE_C_DO_NOT_APPLY_RELATIONS"),
    }
    atomic_json(verdict, arguments.out)

    print(f"{'method@width':18s} {'skill':>8s} {'edgeF1':>8s} {'dense':>8s} {'AUPRC':>8s} "
          f"{'prev':>7s} {'eventF1':>8s} {'S0 add':>8s} {'params':>9s} {'sec':>7s}  label")
    for key in sorted(table):
        e = table[key]
        print(f"{key:18s} {e['forecast_skill_median']:+8.4f} {e['edge_f1_median']:8.3f} "
              f"{e['dense_correlation_median']:8.3f} {e['auprc_median']:8.3f} "
              f"{e['prevalence_median']:7.3f} {e['event_f1_median']:8.3f} "
              f"{e['s0_added_edge_rate_median']:8.3f} {e['cost']['parameters']:9d} "
              f"{e['cost']['seconds']:7.1f}  {e['label']}")
    print("\nherald gate detail:")
    for key in sorted(k for k in table if k.startswith("herald@")):
        print(f"  {key}")
        for name, value in table[key]["checks"].items():
            print(f"    {'PASS' if value else 'FAIL'}  {name}")
    print(f"\nchosen herald width = {chosen}  ({reason})")
    print(f"france decision = {verdict['france_decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
