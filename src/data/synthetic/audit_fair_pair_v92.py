"""Equality audit for the matched complementarity pair, run before the contrast executes.

``S3F_COMPLEMENTARY`` and ``S4F_REDUNDANT`` are only a valid contrast if they differ in one
declared mechanism and in nothing else. The previous pair failed its gate because it was
not matched: ``S3_COMPLEMENTARY`` carried 0.35 of the relational amplitude of
``S4_REDUNDANT``, so the check compared strength, not redundancy. Dividing the gain by the
amplitude afterwards was rejected as a repair because the response to amplitude need not be
linear; the construction is matched instead, and this module is what demonstrates it.

Every tolerance below is declared here and is read by the gate. None may be widened after
a result is seen.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_france_multisignal_v92 import (  # noqa: E402
    FAIR_SEEDS, SIGNAL_SPEC, MultisignalConfig, generate_multisignal, scenario_loadings,
)

# Declared before any fair-pair dataset was generated.
#
# Two classes of quantity. The *exact* ones are fixed by construction at a shared seed:
# both scenarios read the same latent state, the same macro path and the same loadings, so
# any difference at all is a bug. The *distributional* ones depend on which noise rows the
# signals read, which is precisely the knob under test, so they are matched in distribution
# and given a tolerance sized to the seed-to-seed spread of the quantity itself.
EXACT_KEYS = ("gamma", "loading", "graph")
EXACT_TOLERANCE = 0.0
RELATIVE_TOLERANCE = {
    "relational_share": 0.0,        # identical loadings and identical state: must be exact
    "common_share": 0.0,
    "relational_rms": 0.0,
    "noise_rms": 0.0,
    "observed_cells": 0.02,
    "masked_cells": 0.02,
    "low_information_zones": 0.0,
    "graph_density": 0.0,
    "graph_support": 0.0,
}

# Median, coefficient of variation and autocorrelation are realised statistics of a path
# that *must* differ between the two scenarios, because which noise row each signal reads
# is the mechanism under test. Demanding they agree seed by seed would be demanding the
# mechanism not exist. What can honestly be required is that they agree *in distribution*:
# across the twenty seeds the paired difference must show no systematic shift, measured
# against the scenario's own seed-to-seed spread. A first version of this audit used a flat
# 8% per-seed tolerance, which failed on payroll and creations at sixty zones for no reason
# other than sampling. The criterion below is declared before the contrast is run and is
# not read by the complementarity gate, which never touches marginals.
DISTRIBUTIONAL_KEYS = ("median", "cv", "ar1")
MAX_SYSTEMATIC_SHIFT_IN_SD = 0.25


def signal_marginals(dataset: dict) -> dict[str, dict[str, float]]:
    out = {}
    for name, block in dataset["signals"].items():
        values = np.asarray(block["values"], float)
        mask = np.asarray(block["availability_mask"], bool)
        seen = values[mask]
        seen = seen[np.isfinite(seen)]
        logs = np.log(np.maximum(values, 1e-9))
        logs[~mask] = np.nan
        # AR(1) of the log level, pooled over zones. The lag must follow the publication
        # frequency: an annual signal is observed only in the fourth quarter, so lag one
        # never has both ends observed and the correlation came back NaN for every annual
        # signal. The lag is four periods for annual series and one for quarterly.
        lag = 4 if SIGNAL_SPEC[name]["freq"] == "A" else 1
        first, second = logs[:-lag].ravel(), logs[lag:].ravel()
        pair = np.isfinite(first) & np.isfinite(second)
        if pair.sum() > 8:
            a, b = first[pair], second[pair]
            ar1 = float(np.corrcoef(a, b)[0, 1])
        else:
            ar1 = float("nan")
        out[name] = {
            "median": float(np.median(seen)) if seen.size else float("nan"),
            "cv": float(seen.std() / max(abs(seen.mean()), 1e-12)) if seen.size else float("nan"),
            "ar1": ar1,
            "observed_cells": int(mask.sum()),
            "masked_cells": int((~mask).sum()),
        }
    return out


def graph_shape(dataset: dict) -> dict[str, float]:
    propagation = np.asarray(dataset["truth"]["propagation"], float)
    support = np.asarray(dataset["truth"]["prior"], float) > 0
    return {
        "graph_density": float((propagation != 0).mean()),
        "graph_support": float(support.sum()),
    }


def describe(scenario: str, seed: int, n_zones: int) -> dict:
    dataset = generate_multisignal(MultisignalConfig(
        seed=seed, n_zones=n_zones, scenario=scenario))
    calibration = dataset["calibration"]
    return {
        "loadings": calibration["loadings"],
        "relational_share": calibration["relational_share"],
        "common_share": calibration["common_share"],
        "relational_rms": calibration["relational_rms"],
        "noise_rms": calibration["noise_rms"],
        "low_information_zones": calibration["low_information_zones"],
        "marginals": signal_marginals(dataset),
        "graph": graph_shape(dataset),
        "state_checksum": float(np.asarray(dataset["truth"]["state"]).sum()),
    }


def _relative(left: float, right: float) -> float:
    scale = max(abs(left), abs(right), 1e-12)
    return abs(left - right) / scale


def compare(left: dict, right: dict) -> list[dict]:
    """One row per audited requirement, in the order the report prints them."""
    rows: list[dict] = []

    for name in SIGNAL_SPEC:
        for key in EXACT_KEYS:
            a, b = left["loadings"][name][key], right["loadings"][name][key]
            rows.append({"requirement": f"{key}[{name}]", "s3f": a, "s4f": b,
                         "must_match": True, "tolerance": EXACT_TOLERANCE,
                         "difference": 0.0 if a == b else 1.0, "ok": a == b})

    for block, keys in (("", ("relational_share", "common_share", "relational_rms",
                              "noise_rms")),):
        for key in keys:
            for name in SIGNAL_SPEC:
                a, b = left[key][name], right[key][name]
                difference = _relative(a, b)
                tolerance = RELATIVE_TOLERANCE[key]
                rows.append({"requirement": f"{key}[{name}]", "s3f": a, "s4f": b,
                             "must_match": True, "tolerance": tolerance,
                             "difference": difference, "ok": difference <= tolerance})

    for key in ("observed_cells", "masked_cells"):
        for name in SIGNAL_SPEC:
            a = left["marginals"][name][key]
            b = right["marginals"][name][key]
            difference = _relative(a, b)
            tolerance = RELATIVE_TOLERANCE[key]
            rows.append({"requirement": f"{key}[{name}]", "s3f": a, "s4f": b,
                         "must_match": True, "tolerance": tolerance,
                         "difference": difference, "ok": difference <= tolerance})

    for key in ("graph_density", "graph_support"):
        a, b = left["graph"][key], right["graph"][key]
        difference = _relative(a, b)
        rows.append({"requirement": key, "s3f": a, "s4f": b, "must_match": True,
                     "tolerance": RELATIVE_TOLERANCE[key], "difference": difference,
                     "ok": difference <= RELATIVE_TOLERANCE[key]})

    a, b = left["low_information_zones"], right["low_information_zones"]
    rows.append({"requirement": "low_information_zones", "s3f": a, "s4f": b,
                 "must_match": True, "tolerance": 0.0,
                 "difference": 0.0 if a == b else 1.0, "ok": a == b})

    # The latent state must be *identical*, not merely similar: both scenarios read the same
    # draw. This is the single row that proves the pairing is real rather than statistical.
    a, b = left["state_checksum"], right["state_checksum"]
    rows.append({"requirement": "latent_state_is_the_same_draw", "s3f": a, "s4f": b,
                 "must_match": True, "tolerance": 1e-9,
                 "difference": _relative(a, b), "ok": _relative(a, b) <= 1e-9})

    # The one permitted difference, asserted in the opposite direction: if the noise groups
    # matched, there would be no contrast to run.
    groups_left = {entry["noise_group"] for entry in left["loadings"].values()}
    groups_right = {entry["noise_group"] for entry in right["loadings"].values()}
    rows.append({"requirement": "noise_groups_differ_this_is_the_mechanism",
                 "s3f": len(groups_left), "s4f": len(groups_right),
                 "must_match": False, "tolerance": None,
                 "difference": None,
                 "ok": len(groups_left) == len(SIGNAL_SPEC) and len(groups_right) == 1})
    return rows


def distributional_rows(left_all: list[dict], right_all: list[dict]) -> list[dict]:
    """Paired-across-seeds check for the statistics that are allowed to differ per seed."""
    rows = []
    if len(left_all) < 3:
        return rows
    for key in DISTRIBUTIONAL_KEYS:
        for name in SIGNAL_SPEC:
            a = np.array([entry["marginals"][name][key] for entry in left_all], float)
            b = np.array([entry["marginals"][name][key] for entry in right_all], float)
            finite = np.isfinite(a) & np.isfinite(b)
            if finite.sum() < 3:
                rows.append({"requirement": f"{key}[{name}] (paired)", "s3f": float("nan"),
                             "s4f": float("nan"), "must_match": True, "tolerance": None,
                             "difference": None, "ok": False})
                continue
            a, b = a[finite], b[finite]
            spread = float(a.std(ddof=1))
            shift = float(np.mean(a - b))
            allowed = MAX_SYSTEMATIC_SHIFT_IN_SD * max(spread, 1e-12)
            rows.append({
                "requirement": f"{key}[{name}] (paired)",
                "s3f": float(a.mean()), "s4f": float(b.mean()),
                "must_match": True, "tolerance": allowed,
                "difference": abs(shift), "ok": abs(shift) <= allowed,
                "within_scenario_sd": spread, "n_seeds": int(finite.sum())})
    return rows


def audit(seeds, n_zones: int) -> dict:
    per_seed = {}
    failures: list[str] = []
    left_all, right_all = [], []
    for seed in seeds:
        left = describe("S3F_COMPLEMENTARY", seed, n_zones)
        right = describe("S4F_REDUNDANT", seed, n_zones)
        left_all.append(left)
        right_all.append(right)
        rows = compare(left, right)
        per_seed[str(seed)] = rows
        failures.extend(f"seed {seed}: {row['requirement']}"
                        for row in rows if not row["ok"])

    paired = distributional_rows(left_all, right_all)
    failures.extend(f"paired: {row['requirement']}" for row in paired if not row["ok"])
    return {
        "kind": "herald92_fair_pair_equality_audit",
        "seeds": list(seeds), "n_zones": n_zones,
        "tolerances": {"exact_keys": list(EXACT_KEYS),
                       "relative": RELATIVE_TOLERANCE,
                       "distributional_keys": list(DISTRIBUTIONAL_KEYS),
                       "max_systematic_shift_in_sd": MAX_SYSTEMATIC_SHIFT_IN_SD},
        "per_seed": per_seed,
        "paired": paired,
        "n_failures": len(failures),
        "failures": failures[:40],
        "matched": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(FAIR_SEEDS[:3]))
    parser.add_argument("--n-zones", type=int, default=280)
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()

    report = audit(arguments.seeds, arguments.n_zones)
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(json.dumps(report, indent=2, default=float))

    first = report["per_seed"][str(arguments.seeds[0])] + report["paired"]
    print(f"{'requirement':44s} {'S3F':>14s} {'S4F':>14s} {'rel.diff':>10s} "
          f"{'tol':>8s}  ok")
    for row in first:
        difference = "-" if row["difference"] is None else f"{row['difference']:.3e}"
        tolerance = "-" if row["tolerance"] is None else f"{row['tolerance']:.3g}"
        left = row["s3f"] if isinstance(row["s3f"], str) else f"{float(row['s3f']):.5g}"
        right = row["s4f"] if isinstance(row["s4f"], str) else f"{float(row['s4f']):.5g}"
        print(f"{row['requirement']:44s} {left:>14s} {right:>14s} {difference:>10s} "
              f"{tolerance:>8s}  {'ok' if row['ok'] else 'FAIL'}")
    print(f"\nseeds audited: {len(report['seeds'])}   failures: {report['n_failures']}")
    if report["failures"]:
        for entry in report["failures"]:
            print(f"  FAIL {entry}")
    print(f"matched = {report['matched']}")
    return 0 if report["matched"] else 2


if __name__ == "__main__":
    sys.exit(main())
