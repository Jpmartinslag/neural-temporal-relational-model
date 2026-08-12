"""Integration guards for HERALD 91, on top of the six focused inference guards.

The focused guards in ``test_herald91_inference_guards.py`` check the corrected pieces in
isolation. These check that the pieces stay corrected once ``run_signal`` wires them
together: a unit test can pass while the caller quietly passes ``None`` and every arm
re-estimates its own noise scale.

NumPy only, small panel, seconds to run.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.modeles.france_ze2020 import herald91_corrected_tournament as h91  # noqa: E402

_cache: dict = {}
ANCHOR = "urssaf_employer_establishments"   # long series, NB family, cheap to score


def zones() -> list[str]:
    if "zones" not in _cache:
        _cache["zones"] = h91.canonical_zones()
    return _cache["zones"]


def commuting() -> np.ndarray:
    if "commuting" not in _cache:
        _cache["commuting"] = h91.commuting_matrix(zones(), 2019)
    return _cache["commuting"]


def signal(measure: str = ANCHOR) -> dict:
    key = f"signal::{measure}"
    if key not in _cache:
        _cache[key] = h91.load_signal(measure, zones())
    return _cache[key]


def designs(measure: str = ANCHOR) -> dict:
    key = f"designs::{measure}"
    if key not in _cache:
        meta = h91.SIGNALS[measure]
        loaded = signal(measure)
        _cache[key] = {
            "meta": meta,
            "B0": h91.build_design(loaded, meta, None, "B0_local"),
            "B1": h91.build_design(loaded, meta, commuting(), "B1_commuting"),
            "B4": h91.build_design(loaded, meta, None, "B4_national_only"),
            "B2": h91.build_design(loaded, meta, h91.derangement(commuting(), 5000),
                                   "B2_permuted"),
        }
    return _cache[key]


def _probe(measure: str = ANCHOR, draws: int = 2) -> dict:
    key = f"probe::{measure}::{draws}"
    if key not in _cache:
        _cache[key] = h91.run_signal(zones(), measure, commuting(), placebo_draws=draws)
    return _cache[key]


# 1 ── one dispersion per fold, shared by every arm ──────────────────────────

def test_i1_every_arm_in_a_fold_receives_the_same_dispersion():
    """B0, B1, B4 and a placebo must be scored under one frozen noise scale.

    Scored through ``fit_score`` directly, because that is the seam where a caller could
    pass a different value per arm without any unit test noticing.
    """
    built = designs()
    train, score = list(range(10)), 12
    phi = h91.estimate_nb_dispersion(built["B0"], train)
    assert np.isfinite(phi) and phi > 0
    seen = []
    for arm in ("B0", "B1", "B4", "B2"):
        result = h91.fit_score(built[arm], train, score, dispersion=phi)
        seen.append(result["dispersion"])
    assert all(value == phi for value in seen), (
        f"arms were scored under different dispersions: {seen}")


def test_i2_run_signal_freezes_one_dispersion_per_origin():
    exported = _probe()["nb_dispersion_by_origin"]
    assert exported, "run_signal did not export its per-origin dispersion"
    values = [value for value in exported.values() if value is not None]
    assert values and all(np.isfinite(value) and value > 0 for value in values), (
        f"non-finite or non-positive dispersion: {values[:5]}")


# 2 ── folds may legitimately differ ─────────────────────────────────────────

def test_i3_different_folds_may_carry_different_dispersion():
    """Freezing within a fold must not be confused with freezing across folds.

    A single global dispersion would leak late-period noise into early origins.
    """
    built = designs()
    early = h91.estimate_nb_dispersion(built["B0"], list(range(9)))
    late = h91.estimate_nb_dispersion(built["B0"], list(range(16)))
    assert np.isfinite(early) and np.isfinite(late)
    assert early != late, (
        "dispersion is identical across two different training windows; it is probably "
        "computed once and reused globally")


# 3 ── the scored year cannot touch the dispersion ───────────────────────────

def test_i4_no_period_outside_the_training_window_moves_the_dispersion():
    """Neither the scored period nor the one just past the window may leak in.

    Perturbing only the scored period is not enough: a widening bug typically takes
    ``max(train) + 1``, which sits between the window and the scored year and would go
    unnoticed. Every period outside the window is perturbed here.
    """
    built = designs()
    train = list(range(10))
    before = h91.estimate_nb_dispersion(built["B0"], train)
    outside = [t for t in range(len(built["B0"]["y"])) if t not in train]
    assert len(outside) >= 2, "the fixture leaves nothing outside the training window"
    for period in outside:
        mutated = {key: (value.copy() if isinstance(value, np.ndarray) else value)
                   for key, value in built["B0"].items()}
        mutated["y"][period] = mutated["y"][period] * 7.0 + 1000.0
        after = h91.estimate_nb_dispersion(mutated, train)
        assert before == after, (
            f"period {period}, outside the training window, changed the dispersion")


# 4 ── the graph cannot touch the dispersion ─────────────────────────────────

def test_i5_changing_a_graph_feature_does_not_move_the_dispersion():
    """The dispersion is graph-free by construction; this checks it stays so."""
    built = designs()
    train = list(range(10))
    from_b0 = h91.estimate_nb_dispersion(built["B0"], train)
    perturbed = {key: (value.copy() if isinstance(value, np.ndarray) else value)
                 for key, value in built["B1"].items()}
    perturbed["x"][..., -1] *= 50.0          # scale the neighbour column hard
    from_b1 = h91.estimate_nb_dispersion(built["B1"], train)
    from_perturbed = h91.estimate_nb_dispersion(perturbed, train)
    assert from_b1 == from_perturbed == from_b0, (
        "the neighbour column moved the dispersion; it is not graph-free")


# 5 ── NB weights are not Poisson weights when overdispersion is real ────────

def test_i6_nb_and_poisson_weights_diverge_under_overdispersion():
    mu = np.array([10.0, 100.0, 1000.0, 5000.0])
    phi = 20.0
    nb = h91._irls_weights(mu, "negative_binomial", phi)
    poisson = mu
    assert np.all(nb < poisson), "NB weights are not shrunk relative to Poisson"
    # The gap must widen with volume: that is the whole point of the correction.
    ratio = nb / poisson
    assert np.all(np.diff(ratio) < 0), "NB shrinkage does not increase with the mean"
    assert ratio[-1] < 0.01, (
        f"a cell of mean 5000 keeps {ratio[-1]:.3f} of its Poisson weight; the "
        f"dispersion is not binding")


# 6 ── no arm may silently re-estimate ───────────────────────────────────────

def test_i7_nb_scoring_refuses_to_run_without_a_frozen_dispersion():
    built = designs()
    try:
        h91.fit_score(built["B1"], list(range(10)), 12, dispersion=None)
    except ValueError:
        return
    raise AssertionError(
        "an NB arm was scored without a frozen dispersion; it re-estimated silently")


# 7 ── maxT shares the relabelling across signals ────────────────────────────

def test_i8_placebo_relabelling_is_identical_across_signals():
    """Draw ``b`` must be the same territorial relabelling for every signal.

    maxT is only valid if the per-draw statistics are comparable, which requires the same
    permutation to be applied everywhere rather than a fresh one per signal.
    """
    matrix = commuting()
    for draw in (0, 1, 7):
        first = h91.derangement(matrix, 5000 + draw)
        second = h91.derangement(matrix, 5000 + draw)
        assert np.array_equal(first, second), "the relabelling is not reproducible"
    assert not np.array_equal(h91.derangement(matrix, 5000),
                              h91.derangement(matrix, 5001)), (
        "consecutive draws produced the same relabelling")
    import inspect
    source = inspect.getsource(h91.run_signal)
    assert "5000 + draw" in source and "9000 + draw" in source, (
        "placebo seeds are not a fixed sequence shared across signals")


def test_i9_joint_maxt_needs_a_common_draw_count():
    left = {"observed_statistic": 2.0, "null_statistics": [0.1, 0.2, 0.3],
            "status": "scored"}
    right = {"observed_statistic": 0.5, "null_statistics": [0.1, 0.2, 0.3],
             "status": "scored"}
    adjusted = h91.joint_maxT({"a": left, "b": right})
    assert set(adjusted) == {"a", "b"}
    floor = 1.0 / (3 + 1)
    assert min(adjusted.values()) >= floor, (
        f"maxT returned a p-value below its Monte-Carlo floor {floor}")
    assert adjusted["b"] >= adjusted["a"], "maxT ordering is inverted"


# 8 ── an empty promotion is reachable ───────────────────────────────────────

def test_i10_promotion_can_be_empty():
    failing = {arm: {"dense_correlation": 0.05, "edge_f1": 0.10,
                     "complementarity_validated": False}
               for arm in ("C1", "C4", "C6", "I3")}
    decision = h91.promote_width_arms(failing)
    assert decision["promoted"] == [], (
        f"arms were promoted although none met a threshold: {decision['promoted']}")
    assert decision["promotion_authorised"] is False
    passing = dict(failing)
    passing["C4"] = {"dense_correlation": 0.42, "edge_f1": 0.10,
                     "complementarity_validated": False}
    promoted = h91.promote_width_arms(passing)
    assert promoted["promoted"] == ["C4"], promoted["promoted"]
    assert promoted["promotion_authorised"] is True


def _main() -> int:
    names = sorted((name for name in globals() if name.startswith("test_")),
                   key=lambda n: int(n.split("_")[1][1:]))
    failures = 0
    for name in names:
        try:
            globals()[name]()
            print(f"PASS  {name}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {name}\n      {type(error).__name__}: {str(error)[:260]}")
    print(f"\n{len(names) - failures}/{len(names)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
