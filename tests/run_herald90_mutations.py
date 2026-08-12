"""Mutation audit for the HERALD 90 stage-1 guards: thirteen guards, thirteen mutants."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location("g90", REPO / "tests" / "test_herald90_guards.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
h90 = g.h90


def swap(target, name, replacement):
    original = getattr(target, name)
    setattr(target, name, replacement)
    return lambda: setattr(target, name, original)


def killed(name, guard, install) -> bool:
    undo = install()
    g._cache.clear()
    try:
        try:
            guard()
        except Exception as error:  # noqa: BLE001
            print(f"PASS  {name:36s} killed by {type(error).__name__}: {str(error)[:76]}")
            return True
        print(f"FAIL  {name:36s} SURVIVED  <-- guard insufficient")
        return False
    finally:
        undo()
        g._cache.clear()


def m1():  # masked cells become values
    original = h90.load_signal

    def bad(measure, zones, sector="TOTAL"):
        loaded = original(measure, zones, sector)
        loaded["values"] = np.nan_to_num(loaded["values"], nan=0.0)
        loaded["mask"] = np.ones_like(loaded["mask"])
        return loaded
    return swap(h90, "load_signal", bad)


def m2():  # the future level is used as a feature
    original = h90._design

    def bad(signal, neighbour, breaks=True):
        design = original(signal, neighbour, breaks)
        design["x"][..., 1] = design["y"]
        return design
    return swap(h90, "_design", bad)


def m3():  # absence is zero-filled inside the design
    original = h90._design

    def bad(signal, neighbour, breaks=True):
        design = original(signal, neighbour, breaks)
        design["usable"] = np.ones_like(design["usable"])
        return design
    return swap(h90, "_design", bad)


def m4():  # break indicators dropped
    original = h90._design

    def bad(signal, neighbour, breaks=True):
        return original(signal, neighbour, breaks=False)
    return swap(h90, "_design", bad)


def m5():  # the national mean is removed from the baseline
    original = h90._design

    def bad(signal, neighbour, breaks=True):
        design = original(signal, neighbour, breaks)
        design["x"][..., 3] = 0.0
        return design
    return swap(h90, "_design", bad)


def m6():  # the permutation keeps identities
    return swap(h90, "derangement", lambda matrix, seed: matrix.copy())


def m7():  # the random control ignores degree
    def bad(commuting, seed):
        rng = np.random.default_rng(seed)
        out = rng.random(commuting.shape) * (rng.random(commuting.shape) < 0.5)
        np.fill_diagonal(out, 0.0)
        total = out.sum(1, keepdims=True)
        return np.divide(out, total, out=np.zeros_like(out), where=total > 0)
    return swap(h90, "degree_matched_random", bad)


def m8():  # self-loops restored
    original = h90.commuting_matrix

    def bad(zones, decision_year=2019):
        matrix = original(zones, decision_year)
        np.fill_diagonal(matrix, 0.3)
        return matrix
    return swap(h90, "commuting_matrix", bad)


def m9():  # the scored period joins the training window
    original = h90._fit_score

    def bad(design, train, score):
        return original(design, list(train) + [score], score)
    return swap(h90, "_fit_score", bad)


def m10():  # the direction gate always passes
    def bad(result, min_fold_share=0.80):
        return {"verdict": "RELATION_INFORMATIVE", "checks": {}, "passes": True}
    return swap(h90, "relation_informative", bad)


def m11():  # zone codes lose their padding
    original = h90.canonical_zones
    return swap(h90, "canonical_zones", lambda: [c.lstrip("0") for c in original()])


def m12():  # a duplicated regressor is treated as new information
    original = h90._fit_score

    def bad(design, train, score):
        result = original(design, train, score)
        result["sse"] = result["sse"] / max(design["x"].shape[-1], 1)
        return result
    return swap(h90, "_fit_score", bad)


def m13():  # a single informative signal is allowed to authorise fusion
    return swap(h90, "MIN_INFORMATIVE_SIGNALS_FOR_FUSION", 1)


CASES = [
    ("masked_cell_becomes_value", g.test_g1_only_released_rows_are_loaded, m1),
    ("future_level_as_feature", g.test_g2_features_are_strictly_lagged, m2),
    ("absence_zero_filled", g.test_g3_absence_stays_absent, m3),
    ("breaks_dropped", g.test_g4_breaks_are_modelled_not_read_as_dynamics, m4),
    ("national_mean_removed_from_base", g.test_g5_national_mean_lives_in_the_baseline, m5),
    ("permutation_is_identity", g.test_g6_permutation_moves_every_zone, m6),
    ("random_control_ignores_degree", g.test_g7_random_control_matches_degree_and_weights, m7),
    ("self_loop_restored", g.test_g8_no_self_loop, m8),
    ("scored_period_in_training", g.test_g9_no_coefficient_is_fitted_on_the_scored_period, m9),
    ("direction_gate_bypassed", g.test_g10_direction_gate_actually_decides, m10),
    ("zone_codes_unpadded", g.test_g11_zone_codes_are_four_character_strings, m11),
    ("duplicate_counts_as_evidence",
     g.test_g12_duplicating_a_signal_adds_no_independent_information, m12),
    ("one_signal_authorises_fusion",
     g.test_g13_multisignal_stage_needs_two_informative_signals, m13),
]


if __name__ == "__main__":
    total = len(CASES)
    survivors = total - sum(killed(name, guard, install)
                            for name, guard, install in CASES)
    print(f"\n{total - survivors}/{total} mutants killed")
    raise SystemExit(1 if survivors else 0)
