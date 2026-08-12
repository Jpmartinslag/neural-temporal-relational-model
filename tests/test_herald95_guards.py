"""HERALD 95 guards: does ``relational_scale`` really move only the relational component?

The whole stage rests on one parameter meaning what its name says. If it also moves the
common state, or the noise, or the territory, then a ladder built on it measures a mixture
and every reading from it is uninterpretable. These guards check that at the latent level,
at the observable level, and across the paired worlds the design compares.

Run: ``python3 tests/test_herald95_guards.py``
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic import generate_france_multisignal_v94 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald95_scale_ladder as ladder  # noqa: E402

ZONES = 60
SEED = 9891
SCENARIO = "N4_INTERACTION"


def dataset(scale: float, scenario: str = SCENARIO, seed: int = SEED,
            n_zones: int = ZONES, common_scale: float = 1.0):
    return gen.generate_nonlinear(gen.NonlinearConfig(
        n_zones=n_zones, seed=seed, scenario=scenario,
        relational_scale=scale, common_scale=common_scale, paired_streams=True))


def k1_scale_multiplies_the_relational_term_only() -> None:
    """The relational RMS is proportional to the scale; the common state does not move.

    ``relational_scale`` multiplied ``gamma`` as well until this guard was written. ``gamma``
    is the loading on the common state, which is not relational, so the parameter moved two
    components at once and ``scale = 0`` destroyed the common state along with the relation.
    """
    reference = dataset(1.0)["calibration"]
    for scale in (0.0, 0.5, 2.0, 4.0):
        current = dataset(scale)["calibration"]
        for name in reference["relational_rms"]:
            expected = reference["relational_rms"][name] * scale
            actual = current["relational_rms"][name]
            assert abs(actual - expected) <= 1e-9 + 1e-6 * abs(expected), \
                f"{name} at scale {scale}: relational RMS {actual}, expected {expected}"
            assert abs(current["common_state_rms"][name]
                       - reference["common_state_rms"][name]) < 1e-12, \
                f"{name} at scale {scale}: the common state moved with the relational scale"


def k2_zero_scale_leaves_the_common_state_intact() -> None:
    """At scale zero the relation is gone and nothing else is."""
    off = dataset(0.0)["calibration"]
    on = dataset(1.0)["calibration"]
    assert max(abs(value) for value in off["relational_rms"].values()) < 1e-12
    assert all(abs(off["common_state_rms"][name] - on["common_state_rms"][name]) < 1e-12
               for name in off["common_state_rms"]), \
        "the common state vanished with the relation, so scale zero is not the control"
    assert max(off["common_state_rms"].values()) > 1e-6, \
        "there is no common state left to hold fixed"


def k3_worlds_at_different_scales_are_paired() -> None:
    """Territory, graph, latent components, common state and masks are bit-identical.

    Without this the difference between two scales is not the relational effect, it is the
    difference between two different worlds.
    """
    expected = {"same_territory", "same_graph", "same_component_u", "same_component_v",
                "same_common_state", "same_masks"}
    baseline = dataset(0.0)
    for scale in (0.5, 1.0, 2.0, 4.0):
        current = dataset(scale)
        checks = ladder.worlds_are_paired(current, baseline)
        # The reported set must be complete. Trusting `all(checks.values())` alone lets a
        # helper that quietly stops checking something pass for free -- a mutant dropping the
        # mask comparison survived until this line was added.
        assert set(checks) == expected, f"the pairing report is incomplete: {set(checks)}"
        assert all(checks.values()), f"scale {scale} broke the pairing: {checks}"
        # And verified here directly, not only through the helper.
        for name in current["signals"]:
            assert np.array_equal(
                np.asarray(current["signals"][name]["availability_mask"]),
                np.asarray(baseline["signals"][name]["availability_mask"])), \
                f"{name}: masks differ between scale {scale} and the baseline"


def k4_the_observable_effect_is_measured_not_assumed() -> None:
    """The paired difference is non-zero where a mechanism exists and exactly nil at zero."""
    baseline = dataset(0.0)
    identical = ladder.paired_observable_effect(baseline, baseline, "headcount")
    assert identical["relational_rms"] == 0.0, \
        "a world differs from itself, so the pairing is not exact"
    assert identical["n_cells"] > 1000
    effect = ladder.paired_observable_effect(dataset(1.0), baseline, "headcount")
    assert effect["relational_rms"] > 0.0 and np.isfinite(effect["snr"])


def k5_the_observable_effect_grows_with_the_scale() -> None:
    """Monotone in the scale, and *not* proportional to it.

    Proportionality is what one would assume and it is false here, by construction and by
    two mechanisms that are part of the model rather than defects in it: the latent path is
    clipped, and ``_observe`` normalises the integrated drift by its own standard deviation,
    so a larger relational term raises its share of the trajectory without raising the
    trajectory's amplitude. The guard therefore demands monotonicity and explicitly refuses
    to demand linearity, so that a later reader cannot mistake the scale for a multiplier on
    what the model sees.
    """
    baseline = dataset(0.0)
    measured = [ladder.paired_observable_effect(dataset(scale), baseline,
                                                "headcount")["relational_rms"]
                for scale in (0.5, 1.0, 2.0, 4.0)]
    assert all(later > earlier for earlier, later in zip(measured, measured[1:])), \
        f"the observable effect did not grow with the scale: {measured}"
    doubling = measured[1] / max(measured[0], 1e-12)
    assert doubling < 2.0, \
        (f"the observable effect doubled exactly ({doubling}); the clip and the drift "
         "normalisation should damp it, so this suggests one of them stopped acting")


def k6_saturation_is_reported() -> None:
    """The clipped share is published, and it does rise with the scale."""
    shares = [dataset(scale)["calibration"]["clipped_share"]["headcount"]
              for scale in (0.0, 1.0, 4.0)]
    assert all(0.0 <= value <= 1.0 for value in shares)
    assert shares[2] > shares[0], "the clip does not respond to the scale at all"
    assert shares[2] > 0.05, \
        ("the clip barely engages at scale four, which would make the saturation warning "
         "unnecessary; check that the report is measuring the latent path")


def k7_the_scenario_and_the_scale_are_independent() -> None:
    """Scaling does not change which component a signal measures or its noise group."""
    for scale in (0.0, 1.0, 4.0):
        loadings = gen.scenario_loadings(SCENARIO, scale)
        assert {entry["component"] for entry in loadings.values()} == {"u", "v"}
        assert len({entry["noise_group"] for entry in loadings.values()}) == 5
        reference = gen.scenario_loadings(SCENARIO, 1.0)
        for name, entry in loadings.items():
            assert entry["gamma"] == reference[name]["gamma"], \
                f"{name}: gamma moved with the relational scale at {scale}"


def k8_the_null_scenario_ignores_the_scale() -> None:
    """`N0_NULL` has no loading to scale, so the ladder must be flat there by construction."""
    reference = dataset(1.0, scenario="N0_NULL")
    for scale in (0.0, 0.5, 2.0, 4.0):
        current = dataset(scale, scenario="N0_NULL")
        assert np.array_equal(np.asarray(current["signals"]["headcount"]["values"]),
                              np.asarray(reference["signals"]["headcount"]["values"]),
                              equal_nan=True), \
            f"the null scenario changed at scale {scale}, so it is not a flat control"


def k9_the_oracle_regressor_never_reaches_a_candidate_arm() -> None:
    """The released view carries no relational truth, at any scale."""
    for scale in (0.0, 1.0, 4.0):
        data = dataset(scale)
        view = gen.model_inputs(data, 90)
        assert "truth" not in view and "calibration" not in view
        truth = ladder.relational_regressor(data, "headcount")
        for name, block in view["signals"].items():
            values = np.asarray(block["values"], float)
            seen = np.isfinite(values)
            if not seen.any():
                continue
            for period in (60, 80):
                left = values[period][np.isfinite(values[period])]
                if len(left) < 10:
                    continue
                right = truth[period][np.isfinite(values[period])]
                if np.std(right) < 1e-15 or np.std(left) < 1e-15:
                    continue
                correlation = abs(float(np.corrcoef(left, right)[0, 1]))
                assert correlation < 0.999, \
                    f"{name} reproduces the relational truth at period {period}"


def k10_scales_and_seeds_are_declared_and_disjoint() -> None:
    from src.data.synthetic.generate_france_multisignal_v94 import (
        FINAL_SEEDS as V94_FINAL, RETIRED_SEEDS, SMOKE_SEEDS as V94_SMOKE)
    earlier = set(V94_FINAL) | set(RETIRED_SEEDS) | set(V94_SMOKE)
    assert not (set(ladder.FINAL_SEEDS) & earlier), "a ladder seed was used by an earlier stage"
    assert not (set(ladder.SMOKE_SEEDS) & (earlier | set(ladder.FINAL_SEEDS)))
    assert 0.0 in ladder.SCALES and 1.0 in ladder.SCALES, \
        "the ladder needs its baseline and its reference scale"
    assert "N0_NULL" in ladder.LADDER_SCENARIOS, "the flat control is missing"


GUARDS = [value for key, value in sorted(globals().items()) if key.startswith("k")
          and callable(value) and key[1].isdigit()]


def main() -> int:
    failures = []
    for guard in sorted(GUARDS, key=lambda function: int(
            "".join(character for character in function.__name__.split("_")[0][1:]))):
        try:
            guard()
            print(f"PASS  {guard.__name__}")
        except AssertionError as error:
            failures.append((guard.__name__, str(error)))
            print(f"FAIL  {guard.__name__}: {error}")
        except Exception as error:                      # noqa: BLE001
            failures.append((guard.__name__, f"{type(error).__name__}: {error}"))
            print(f"ERROR {guard.__name__}: {type(error).__name__}: {error}")
    print(f"\n{len(GUARDS) - len(failures)}/{len(GUARDS)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
