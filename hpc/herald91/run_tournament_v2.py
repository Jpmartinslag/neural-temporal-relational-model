"""HERALD 91 tournament v2: the rerun demanded by DEC-130, with numerical health checks.

The DEC-129 artefact stays where it is as history. This writes a separate file and, before
any coefficient is read as a result, records whether the fit is trustworthy at all: IRLS
convergence, the dispersion distribution, whether every arm in a fold really shared one
dispersion, whether any deviance is non-finite, and whether B4 is still a different model
from B0.

Forty draws are a probe. The floor is ``1/41 = 0.02439``, nothing is confirmatory, and the
only decisions it may inform are "is this numerically sound" and "is there a candidate
worth 199 draws".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.modeles.france_ze2020 import herald91_corrected_tournament as h91  # noqa: E402


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


def health_checks(zones, measure, commuting, result) -> dict:
    """Numerical soundness, checked before any p-value is interpreted."""
    meta = h91.SIGNALS[measure]
    signal = h91.load_signal(measure, zones)
    b0 = h91.build_design(signal, meta, None, "B0_local")
    b1 = h91.build_design(signal, meta, commuting, "B1_commuting")
    b4 = h91.build_design(signal, meta, None, "B4_national_only")
    origins = sorted(int(key) for key in result["nb_dispersion_by_origin"])
    dispersions = [result["nb_dispersion_by_origin"][str(t)] for t in origins]
    finite = [value for value in dispersions if value is not None]

    shared, deviances = True, []
    for t in origins[: min(3, len(origins))]:
        phi = result["nb_dispersion_by_origin"][str(t)]
        seen = set()
        for design in (b0, b1, b4):
            scored = h91.fit_score(design, list(range(t)), t, dispersion=phi)
            seen.add(scored["dispersion"])
            deviances.append(scored["deviance"])
        if len(seen) != 1:
            shared = False

    return {
        "family": meta["family"],
        "n_origins": len(origins),
        "dispersion_all_finite_positive": bool(
            all(np.isfinite(value) and value > 0 for value in finite)) if finite else None,
        "dispersion_min": float(np.min(finite)) if finite else None,
        "dispersion_median": float(np.median(finite)) if finite else None,
        "dispersion_max": float(np.max(finite)) if finite else None,
        "dispersion_at_ceiling": int(sum(value >= 1e5 for value in finite)) if finite else 0,
        "same_dispersion_across_arms_in_fold": shared,
        "all_deviances_finite": bool(np.all(np.isfinite(deviances))),
        "b4_differs_from_b0": not result["b0_equals_b4"],
        "b4_relative_to_null": result["relative_to_null"]["B4_national_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--placebo-draws", type=int, default=40)
    parser.add_argument("--confirmatory", action="store_true",
                        help="label the run confirmatory; requires at least 199 draws")
    arguments = parser.parse_args()
    if arguments.confirmatory and arguments.placebo_draws < 199:
        parser.error("a confirmatory run needs at least 199 placebo draws")

    zones = h91.canonical_zones()
    commuting = h91.commuting_matrix(zones, 2019)
    results, health, timings = {}, {}, {}
    for measure in h91.SIGNALS:
        started = time.time()
        result = h91.run_signal(zones, measure, commuting,
                                placebo_draws=arguments.placebo_draws)
        timings[measure] = round(time.time() - started, 2)
        results[measure] = result
        if result.get("status") == "scored":
            health[measure] = health_checks(zones, measure, commuting, result)

    adjusted = h91.joint_maxT(results)
    verdicts = {name: h91.verdict(entry, adjusted_p=adjusted.get(name))
                for name, entry in results.items() if entry.get("status") == "scored"}

    sound = all(entry["dispersion_all_finite_positive"] is not False
                and entry["same_dispersion_across_arms_in_fold"]
                and entry["all_deviances_finite"] and entry["b4_differs_from_b0"]
                for entry in health.values())
    candidates = [name for name, verdict in verdicts.items()
                  if verdict["verdict"] in ("RELATION_INFORMATIVE", "WEAK_CANDIDATE")]

    report = {
        "kind": "herald91_tournament_v2",
        "run_type": "confirmatory" if arguments.confirmatory else "exploratory_probe",
        "placebo_draws": arguments.placebo_draws,
        "p_value_floor": 1.0 / (arguments.placebo_draws + 1),
        "vintage_policy": h91.VINTAGE_POLICY,
        "supersedes": "DEC-129 classifications (artefact kept as corrected_tournament.json)",
        "results": results, "adjusted_maxT": adjusted, "verdicts": verdicts,
        "health": health, "seconds_per_signal": timings,
        "numerically_sound": bool(sound),
        "mechanical_candidates": candidates,
        "authorises_confirmatory_rerun": bool(sound and candidates
                                              and not arguments.confirmatory),
    }
    atomic_json(report, arguments.out)

    print(f"run_type={report['run_type']}  draws={arguments.placebo_draws}  "
          f"floor={report['p_value_floor']:.5f}\n")
    print(f"{'signal':32s} {'orig':>4s} {'phi med':>9s} {'B1/nul':>7s} {'p_perm':>7s} "
          f"{'p_maxT':>7s} {'consist':>8s} {'cov%':>5s}  verdict")
    for measure, result in results.items():
        if result.get("status") != "scored":
            print(f"{measure:32s}  {result.get('status')}")
            continue
        entry, verdict = health[measure], verdicts[measure]
        median = entry["dispersion_median"]
        print(f"{measure:32s} {result['n_origins']:4d} "
              f"{('n/a' if median is None else f'{median:9.1f}'):>9s} "
              f"{result['relative_to_null']['B1_commuting']:7.3f} "
              f"{result['p_value_vs_permuted']:7.4f} "
              f"{adjusted.get(measure, float('nan')):7.4f} "
              f"{result['origins_where_commuting_wins_over_median_placebo']:3d}"
              f"/{result['n_origins']:<4d} "
              f"{result['covid_window_gain_share']:5.0%}  {verdict['verdict']}")
    print(f"\nnumerically_sound={report['numerically_sound']}  "
          f"candidates={candidates}")
    print(f"authorises_confirmatory_rerun={report['authorises_confirmatory_rerun']}")
    print(f"cost: {sum(timings.values()):.0f}s total at {arguments.placebo_draws} draws")
    return 0


if __name__ == "__main__":
    sys.exit(main())
