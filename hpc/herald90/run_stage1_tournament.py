"""HERALD 90 stage 1: audit the real French signals and run the cheap tournament.

NumPy only, seconds to run, and its verdict decides whether stage 2 is written at all.
Emits ``authorises_multisignal_oracle`` explicitly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from src.modeles.france_ze2020 import herald90_signal_audit as h90  # noqa: E402

TOURNAMENT_SEEDS = (9001, 9002, 9003, 9004, 9005)
SCORE_PERIODS = {"Q": 8, "A": 5}


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


def per_seed_direction(zones, measure, commuting, seeds, n_score) -> dict:
    """Median per-fold gain against the derangement, aggregated seed by seed.

    The task states the direction gate as "advantage in at least 4 of 5 seeds", so the
    seed is the unit. The per-fold share is reported alongside it, because the two
    aggregations can disagree and picking the flattering one after the fact would be
    exactly the failure this project keeps auditing.
    """
    signal = h90.load_signal(measure, zones)
    with_graph = h90._design(signal, commuting)
    n_steps = len(with_graph["y"])
    positions = [p for p in range(n_steps - n_score, n_steps) if p >= 8]
    per_seed, fold_wins = [], []
    for seed in seeds:
        permuted = h90._design(signal, h90.derangement(commuting, seed))
        gains = []
        for position in positions:
            train = list(range(position))
            true_mse = h90._fit_score(with_graph, train, position)["mse"]
            permuted_mse = h90._fit_score(permuted, train, position)["mse"]
            gains.append((permuted_mse - true_mse) / max(permuted_mse, 1e-12))
            fold_wins.append(true_mse < permuted_mse)
        per_seed.append(float(np.median(gains)))
    return {"per_seed_median_gain": per_seed,
            "seeds_favourable": int(sum(value > 0 for value in per_seed)),
            "n_seeds": len(seeds),
            "fold_share_favourable": float(np.mean(fold_wins)) if fold_wins else 0.0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    plan = {"kind": "herald90_stage1_plan", "seeds": list(TOURNAMENT_SEEDS),
            "arms": list(h90.ARMS), "signals": list(h90.SIGNALS),
            "direction_gate": "advantage in >= 4 of 5 seeds",
            "authorisation": "multisignal oracle needs >= 2 informative signals"}
    if arguments.dry_run:
        print(json.dumps(plan, indent=2)); return 0
    if arguments.out is None:
        parser.error("--out is required unless --dry-run is used")

    zones = h90.canonical_zones()
    commuting = h90.commuting_matrix(zones, 2019)
    audit = h90.audit_signals(zones)

    results, verdicts = {}, {}
    for measure, meta in h90.SIGNALS.items():
        n_score = SCORE_PERIODS[meta["freq"]]
        tournament = h90.tournament(zones, measure, commuting, TOURNAMENT_SEEDS, n_score)
        direction = per_seed_direction(zones, measure, commuting, TOURNAMENT_SEEDS, n_score)
        # The seed-level aggregation is the declared gate; the fold share is reported.
        seed_gate = direction["seeds_favourable"] >= 4
        passes = bool(seed_gate
                      and tournament.get("commuting_vs_permuted", -1) > 0
                      and tournament.get("commuting_vs_random", -1) > 0)
        results[measure] = {"tournament": tournament, "direction": direction,
                            "seed_gate_passes": seed_gate}
        verdicts[measure] = {"passes": passes}

    authorisation = h90.authorise_multisignal_oracle(verdicts)
    report = {"kind": "herald90_stage1", "plan": plan, "audit": audit,
              "results": results, "verdicts": verdicts, **authorisation}
    atomic_json(report, arguments.out)

    print(f"{'signal':34s} {'seeds fav':>9s} {'fold share':>10s} {'vs perm':>9s} "
          f"{'vs random':>9s}  verdict")
    for measure, entry in results.items():
        tour, direction = entry["tournament"], entry["direction"]
        print(f"{measure:34s} {direction['seeds_favourable']:>7d}/5 "
              f"{direction['fold_share_favourable']:>9.0%} "
              f"{tour.get('commuting_vs_permuted', float('nan')):>+8.3%} "
              f"{tour.get('commuting_vs_random', float('nan')):>+9.3%}  "
              f"{'RELATION_INFORMATIVE' if verdicts[measure]['passes'] else 'not informative'}")
    print(f"\ninformative signals: {authorisation['informative_signals']}")
    print(f"authorises_multisignal_oracle = {authorisation['authorises_multisignal_oracle']}")
    print(f"authorises_single_signal_followup = "
          f"{authorisation['authorises_single_signal_followup']}")
    return 0 if authorisation["authorises_multisignal_oracle"] else 2


if __name__ == "__main__":
    sys.exit(main())
