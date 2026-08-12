"""Focused guards for the HERALD 91 inference corrections (NumPy only)."""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.modeles.france_ze2020 import herald91_corrected_tournament as h91  # noqa: E402


def _nb_design(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    periods, zones = 7, 6
    values = rng.negative_binomial(8, 8 / (8 + 40), size=(periods, zones)).astype(float) + 1
    signal = {
        "values": values,
        "mask": np.ones_like(values, dtype=bool),
        "periods": [(2010 + t, 0) for t in range(periods)],
    }
    meta = {"family": "negative_binomial", "seasonal": False, "breaks": ()}
    return h91.build_design(signal, meta, None, "B0_local")


def test_g1_nb_weights_are_not_poisson_weights():
    mu = np.array([2.0, 20.0, 200.0])
    phi = 5.0
    got = h91._irls_weights(mu, "negative_binomial", phi)
    expected = mu / (1.0 + mu / phi)
    assert np.allclose(got, expected)
    assert not np.allclose(got, mu), "NB silently reverted to Poisson weights"


def test_g2_dispersion_uses_training_only():
    design = _nb_design()
    train, score = [0, 1, 2, 3], 4
    before = h91.estimate_nb_dispersion(design, train)
    changed = {key: (value.copy() if isinstance(value, np.ndarray) else value)
               for key, value in design.items()}
    changed["y"][score] *= 100.0
    after = h91.estimate_nb_dispersion(changed, train)
    assert before == after, "the scored period changed the training dispersion"


def test_g3_fit_score_honours_frozen_dispersion():
    design = _nb_design()
    supplied = 3.25
    result = h91.fit_score(design, [0, 1, 2, 3], 4, dispersion=supplied)
    assert result["dispersion"] == supplied, "the arm replaced the shared dispersion"


def test_g4_permutation_statistic_uses_one_common_scale():
    totals = np.array([8.0, 10.0, 12.0, 14.0])
    observed, null = h91.permutation_statistics(totals, 7.0)
    centre, scale = totals.mean(), totals.std(ddof=1)
    assert np.isclose(observed, (centre - 7.0) / scale)
    assert np.allclose(null, (centre - totals) / scale)
    assert np.isclose(null.mean(), 0.0)
    assert np.isclose(null.std(ddof=1), 1.0)


def test_g5_joint_maxt_has_monte_carlo_floor():
    results = {
        "a": {"status": "scored", "observed_statistic": 99.0,
              "null_statistics": [-1.0, 0.0, 1.0, 2.0]},
        "b": {"status": "scored", "observed_statistic": 99.0,
              "null_statistics": [0.0, 1.0, -1.0, 2.0]},
    }
    adjusted = h91.joint_maxT(results)
    assert adjusted == {"a": 0.2, "b": 0.2}, "maxT omitted the +1 correction"


def test_g6_width_promotion_never_forces_a_winner():
    failed = {
        "A": {"dense_correlation": 0.29, "edge_f1": 0.49},
        "B": {"dense_correlation": -0.2, "edge_f1": 0.1},
        "R1": {"dense_correlation": 0.0, "edge_f1": 0.0},
    }
    decision = h91.promote_width_arms(failed)
    assert decision["promoted"] == []
    assert decision["promotion_authorised"] is False
    passed = dict(failed)
    passed["C3"] = {"dense_correlation": 0.31, "edge_f1": 0.2}
    decision = h91.promote_width_arms(passed)
    assert "C3" in decision["promoted"] and "R1" in decision["controls_to_accompany_promoted"]


def _main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_g")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {test.__name__}: {type(error).__name__}: {error}")
    print(f"\n{len(tests) - failures}/{len(tests)} guards passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(_main())
