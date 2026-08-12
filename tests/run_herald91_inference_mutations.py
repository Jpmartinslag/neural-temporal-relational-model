"""Mutation audit for the six focused HERALD 91 inference guards."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location("g91", REPO / "tests" / "test_herald91_inference_guards.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
h91 = g.h91


def swap(name, replacement):
    original = getattr(h91, name)
    setattr(h91, name, replacement)
    return lambda: setattr(h91, name, original)


def killed(name, guard, install):
    undo = install()
    try:
        try:
            guard()
        except Exception as error:  # noqa: BLE001
            print(f"PASS  {name:34s} killed by {type(error).__name__}: {str(error)[:70]}")
            return True
        print(f"FAIL  {name:34s} SURVIVED")
        return False
    finally:
        undo()


def m1():
    return swap("_irls_weights", lambda mu, family, dispersion=None: np.asarray(mu, float))


def m2():
    original = h91.estimate_nb_dispersion
    def bad(design, train):
        return original(design, list(train) + [min(max(train) + 1, len(design["y"]) - 1)])
    return swap("estimate_nb_dispersion", bad)


def m3():
    original = h91.fit_score
    def bad(design, train, score, dispersion=None):
        return original(design, train, score, dispersion=None)
    return swap("fit_score", bad)


def m4():
    def bad(null_totals, observed_total):
        totals = np.asarray(null_totals, float)
        null = []
        for index, value in enumerate(totals):
            others = np.delete(totals, index)
            null.append((np.median(others) - value) / max(np.median(others), 1e-12))
        return float((np.median(totals) - observed_total) / np.median(totals)), np.asarray(null)
    return swap("permutation_statistics", bad)


def m5():
    def bad(results):
        joint = np.max([entry["null_statistics"] for entry in results.values()], axis=0)
        return {name: float(np.mean(joint >= entry["observed_statistic"]))
                for name, entry in results.items()}
    return swap("joint_maxT", bad)


def m6():
    def bad(metrics, dense_threshold=0.30, edge_threshold=0.50):
        ranked = sorted(metrics, key=lambda arm: metrics[arm].get("edge_f1", -1), reverse=True)[:3]
        return {"promoted": ranked, "controls_to_accompany_promoted": [],
                "promotion_authorised": bool(ranked), "reasons": {}, "rule": "top3"}
    return swap("promote_width_arms", bad)


CASES = [
    ("nb_reverts_to_poisson", g.test_g1_nb_weights_are_not_poisson_weights, m1),
    ("dispersion_reads_scored_period", g.test_g2_dispersion_uses_training_only, m2),
    ("arm_reestimates_dispersion", g.test_g3_fit_score_honours_frozen_dispersion, m3),
    ("maxt_uses_bespoke_references", g.test_g4_permutation_statistic_uses_one_common_scale, m4),
    ("maxt_omits_plus_one", g.test_g5_joint_maxt_has_monte_carlo_floor, m5),
    ("width_forces_top_three", g.test_g6_width_promotion_never_forces_a_winner, m6),
]


if __name__ == "__main__":
    killed_count = sum(killed(*case) for case in CASES)
    print(f"\n{killed_count}/{len(CASES)} mutants killed")
    raise SystemExit(0 if killed_count == len(CASES) else 1)
