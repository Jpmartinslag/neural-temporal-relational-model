"""Mutation audit for the HERALD 91 integration guards.

Each mutant restores a wiring defect that a unit test would not see: a per-arm dispersion,
a global dispersion shared across folds, a graph-dependent noise scale, a Poisson weight, a
per-signal relabelling, or a promotion rule that always finds a winner.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location(
    "i91", REPO / "tests" / "test_herald91_integration_guards.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
h91 = g.h91


def swap(name, replacement):
    original = getattr(h91, name)
    setattr(h91, name, replacement)
    return lambda: setattr(h91, name, original)


def killed(name, guard, install) -> bool:
    undo = install()
    g._cache.clear()
    try:
        try:
            guard()
        except Exception as error:  # noqa: BLE001
            print(f"PASS  {name:38s} killed by {type(error).__name__}: {str(error)[:70]}")
            return True
        print(f"FAIL  {name:38s} SURVIVED  <-- guard insufficient")
        return False
    finally:
        undo()
        g._cache.clear()


# i1 ── each arm quietly gets its own dispersion
def m_per_arm_dispersion():
    original = h91.fit_score

    def bad(design, train, score, dispersion=None, allow_local_dispersion=False):
        result = original(design, train, score, dispersion=dispersion,
                          allow_local_dispersion=True)
        if design["family"] == "negative_binomial":
            result = dict(result)
            result["dispersion"] = h91.estimate_nb_dispersion(design, train)
        return result
    return swap("fit_score", bad)


# i2 ── run_signal stops exporting what it froze
def m_dispersion_not_exported():
    original = h91.run_signal

    def bad(*args, **kwargs):
        result = original(*args, **kwargs)
        if isinstance(result, dict):
            result = dict(result)
            result["nb_dispersion_by_origin"] = {}
        return result
    return swap("run_signal", bad)


# i3 ── one global dispersion reused for every fold
def m_global_dispersion():
    original = h91.estimate_nb_dispersion
    cache: dict = {}

    def bad(design, train):
        if "value" not in cache:
            cache["value"] = original(design, train)
        return cache["value"]
    return swap("estimate_nb_dispersion", bad)


# i4 ── the scored period feeds the dispersion
def m_dispersion_sees_scored_year():
    original = h91.estimate_nb_dispersion

    def bad(design, train):
        widened = list(train) + [min(max(train) + 1, len(design["y"]) - 1)]
        return original(design, widened)
    return swap("estimate_nb_dispersion", bad)


# i5 ── the dispersion becomes graph-dependent
def m_graph_dependent_dispersion():
    original = h91.estimate_nb_dispersion

    def bad(design, train):
        value = original(design, train)
        if design.get("has_neighbour"):
            column = np.concatenate(
                [design["x"][t][design["usable"][t], -1] for t in train])
            value *= float(1.0 + abs(np.mean(column)))
        return value
    return swap("estimate_nb_dispersion", bad)


# i6 ── NB weights revert to Poisson
def m_poisson_weights():
    return swap("_irls_weights",
                lambda mu, family, dispersion=None: np.asarray(mu, float))


# i7 ── NB scoring silently re-estimates again
def m_silent_reestimation():
    original = h91.fit_score

    def bad(design, train, score, dispersion=None, allow_local_dispersion=False):
        return original(design, train, score, dispersion=dispersion,
                        allow_local_dispersion=True)
    return swap("fit_score", bad)


# i8 ── each signal draws its own relabelling
def m_per_signal_relabelling():
    counter = {"n": 0}

    def bad(matrix, seed):
        counter["n"] += 1
        rng = np.random.default_rng(seed * 7919 + counter["n"])
        n = len(matrix)
        for _ in range(2000):
            permutation = rng.permutation(n)
            if not np.any(permutation == np.arange(n)):
                return matrix[permutation][:, permutation]
        raise RuntimeError("no derangement")
    return swap("derangement", bad)


# i9 ── maxT drops its Monte-Carlo floor
def m_maxt_without_floor():
    def bad(results):
        joint = np.max([entry["null_statistics"] for entry in results.values()], axis=0)
        return {name: float(np.mean(joint >= entry["observed_statistic"]))
                for name, entry in results.items()}
    return swap("joint_maxT", bad)


# i10 ── promotion always finds someone
def m_promotion_always_finds_a_winner():
    def bad(metrics, dense_threshold=0.30, edge_threshold=0.50):
        ranked = sorted(metrics, key=lambda arm: metrics[arm].get("edge_f1", -1),
                        reverse=True)[:3]
        return {"promoted": ranked, "controls_to_accompany_promoted": [],
                "promotion_authorised": True, "reasons": {}, "rule": "top3"}
    return swap("promote_width_arms", bad)


CASES = [
    ("per_arm_dispersion", g.test_i1_every_arm_in_a_fold_receives_the_same_dispersion,
     m_per_arm_dispersion),
    ("dispersion_not_exported", g.test_i2_run_signal_freezes_one_dispersion_per_origin,
     m_dispersion_not_exported),
    ("global_dispersion_across_folds",
     g.test_i3_different_folds_may_carry_different_dispersion, m_global_dispersion),
    ("dispersion_sees_period_outside_window",
     g.test_i4_no_period_outside_the_training_window_moves_the_dispersion,
     m_dispersion_sees_scored_year),
    ("graph_dependent_dispersion",
     g.test_i5_changing_a_graph_feature_does_not_move_the_dispersion,
     m_graph_dependent_dispersion),
    ("poisson_weights", g.test_i6_nb_and_poisson_weights_diverge_under_overdispersion,
     m_poisson_weights),
    ("silent_reestimation",
     g.test_i7_nb_scoring_refuses_to_run_without_a_frozen_dispersion,
     m_silent_reestimation),
    ("per_signal_relabelling",
     g.test_i8_placebo_relabelling_is_identical_across_signals, m_per_signal_relabelling),
    ("maxt_without_floor", g.test_i9_joint_maxt_needs_a_common_draw_count,
     m_maxt_without_floor),
    ("promotion_always_wins", g.test_i10_promotion_can_be_empty,
     m_promotion_always_finds_a_winner),
]


if __name__ == "__main__":
    survivors = len(CASES) - sum(killed(*case) for case in CASES)
    print(f"\n{len(CASES) - survivors}/{len(CASES)} mutants killed")
    raise SystemExit(1 if survivors else 0)
