"""Guards for the matched complementarity contrast (HERALD 92, part A).

The previous contrast failed because its two scenarios differed in relational amplitude as
well as in mechanism. Every guard here exists to make that class of defect impossible to
reintroduce silently: the pair must be identical in what it claims to hold fixed, and
genuinely different in the one thing it claims to vary.

NumPy only. ``run_herald92_fair_mutations.py`` removes exactly one named mechanism per
guard and must break it.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.synthetic import generate_france_multisignal_v92 as gen  # noqa: E402
from src.data.synthetic import audit_fair_pair_v92 as audit  # noqa: E402
from src.modeles.france_ze2020 import herald92_multisignal_oracle as h92  # noqa: E402

SMALL = dict(n_zones=60)
FAIR_A, FAIR_B = "S3F_COMPLEMENTARY", "S4F_REDUNDANT"
_cache: dict = {}


def dataset(scenario: str, seed: int = 9501) -> dict:
    key = (scenario, seed)
    if key not in _cache:
        _cache[key] = gen.generate_multisignal(
            gen.MultisignalConfig(seed=seed, scenario=scenario, **SMALL))
    return _cache[key]


def loadings(scenario: str) -> dict:
    return gen.scenario_loadings(scenario, 1.0)


def measurement_error(scenario: str, seed: int = 9501):
    """Recover each signal's realised measurement error from the simulated latent path.

    Inverting the recursion is what lets the guards check the noise budget *as realised*
    rather than as declared. Reading ``SIGNAL_SPEC[name]["noise"]`` back out of the
    calibration block proves only that a constant was copied: a scenario that quietly
    scaled its own noise would pass. Two corrections are applied. The macro term is one
    scalar per period shared by every zone, removed exactly by centring across zones. And
    the simulator clips the latent path at +/-0.60, so clipped cells no longer satisfy the
    recursion and are excluded.
    """
    truth = dataset(scenario, seed)["truth"]
    series, live = {}, {}
    for name, spec in gen.SIGNAL_SPEC.items():
        latent = np.asarray(truth["latent"][name])
        step = (latent[1:] - spec["ar_log"] * latent[:-1]
                - np.asarray(truth["common"][name])[1:]
                - np.asarray(truth["relational"][name])[1:])
        step = step - step.mean(axis=1, keepdims=True)
        series[name] = step
        live[name] = (np.abs(latent[1:]) < 0.5999) & (np.abs(latent[:-1]) < 0.5999)
    return series, live


# ── f1-f3: the pair holds fixed what it claims to hold fixed ─────────────────

def test_f1_same_relational_strength():
    """Gamma, loading and graph must be identical, signal by signal.

    This is the guard the previous pair did not have. `S3_COMPLEMENTARY` scaled both by
    0.35 and `S4_REDUNDANT` did not, so the gate compared amplitude and called it
    redundancy.
    """
    left, right = loadings(FAIR_A), loadings(FAIR_B)
    for name in gen.SIGNAL_SPEC:
        for key in ("gamma", "loading", "graph"):
            assert left[name][key] == right[name][key], (
                f"{name}.{key}: {left[name][key]} vs {right[name][key]}")


def test_f2_same_noise_budget():
    """Per-signal measurement-noise variance identical; only its sharing may differ.

    Checked both as declared and as realised. The declared half alone was insufficient:
    ``noise_rms`` in the calibration block is a copy of the spec constant, so a scenario
    that scaled its own noise inside the simulator would have passed while buying its
    redundancy with quieter data instead of with shared error.
    """
    left = dataset(FAIR_A)["calibration"]
    right = dataset(FAIR_B)["calibration"]
    for name in gen.SIGNAL_SPEC:
        assert left["noise_rms"][name] == right["noise_rms"][name], name
        assert left["relational_rms"][name] == right["relational_rms"][name], name
        assert left["relational_share"][name] == right["relational_share"][name], name
        assert left["common_share"][name] == right["common_share"][name], name

    a_series, a_live = measurement_error(FAIR_A)
    b_series, b_live = measurement_error(FAIR_B)
    for name, spec in gen.SIGNAL_SPEC.items():
        a = float(a_series[name][a_live[name]].std())
        b = float(b_series[name][b_live[name]].std())
        for measured, label in ((a, FAIR_A), (b, FAIR_B)):
            assert abs(measured - spec["noise"]) / spec["noise"] < 0.10, (
                f"{label}/{name}: realised noise {measured:.5f} against declared "
                f"{spec['noise']:.5f}")
        assert abs(a - b) / max(a, b) < 0.10, (
            f"{name}: realised noise differs between the pair, {a:.5f} vs {b:.5f}")


def test_f3_equivalent_marginals_and_the_same_latent_draw():
    """The two scenarios must be the same world, differing only downstream of the noise.

    The latent state is checked for *identity*, not similarity: both read the same draw
    because every random array in the simulator has a scenario-independent shape and is
    drawn in a fixed order. If the noise were allocated per group instead, the five-group
    and one-group scenarios would consume different amounts of the stream and the paired
    comparison would quietly be comparing two different worlds.
    """
    left, right = dataset(FAIR_A), dataset(FAIR_B)
    assert np.array_equal(np.asarray(left["truth"]["state"]),
                          np.asarray(right["truth"]["state"])), "different latent state"
    assert np.array_equal(np.asarray(left["truth"]["propagation"]),
                          np.asarray(right["truth"]["propagation"])), "different graph"
    assert np.array_equal(np.asarray(left["truth"]["prior"]),
                          np.asarray(right["truth"]["prior"])), "different support"
    assert (left["calibration"]["low_information_zones"]
            == right["calibration"]["low_information_zones"])


# ── f4-f5: the pair varies what it claims to vary ────────────────────────────

def test_f4_complementary_noise_is_genuinely_independent():
    """Five distinct measurement errors, so averaging can cancel them."""
    groups = {name: entry["noise_group"] for name, entry in loadings(FAIR_A).items()}
    assert len(set(groups.values())) == len(gen.SIGNAL_SPEC), (
        f"S3F must give every signal its own noise: {groups}")


def test_f5_redundant_noise_is_genuinely_shared():
    """One measurement error for all, so averaging cancels nothing.

    Checked behaviourally as well as declaratively: with the state and the loadings held
    fixed, the residual left after removing the common and relational terms must be the
    same series (up to each signal's own scale) for every signal in S4F, and must not be
    in S3F.
    """
    groups = {entry["noise_group"] for entry in loadings(FAIR_B).values()}
    assert len(groups) == 1, f"S4F must share one noise group, found {groups}"

    def residual_correlation(scenario: str) -> float:
        data = dataset(scenario)
        truth = data["truth"]
        names = list(gen.SIGNAL_SPEC)
        series, live = [], []
        for name in names:
            latent = np.asarray(truth["latent"][name])
            spec = gen.SIGNAL_SPEC[name]
            # The simulator clips the latent path at +/-0.60. A clipped cell no longer
            # satisfies the recursion, so its residual is not the measurement error and
            # correlating it understates the sharing: creations reaches the clip in 13% of
            # cells and dragged the median pairwise correlation from 0.98 to 0.93. Clipped
            # cells are excluded rather than tolerated by a looser threshold.
            live.append((np.abs(latent[1:]) < 0.5999) & (np.abs(latent[:-1]) < 0.5999))
            step = (latent[1:] - spec["ar_log"] * latent[:-1]
                    - np.asarray(truth["common"][name])[1:]
                    - np.asarray(truth["relational"][name])[1:])
            # The remaining macro term is one scalar per period, shared by every zone and
            # drawn independently per signal. It is identical in both scenarios, so it
            # cannot bias the contrast, but it does dilute this correlation: with a macro
            # standard deviation of 0.010 against headcount's noise of 0.030 the shared
            # residuals correlate at 0.86 rather than 1.0. Centring across zones removes it
            # exactly and leaves the measurement error this guard is about.
            step = step - step.mean(axis=1, keepdims=True)
            series.append(step / spec["noise"])
        pairs = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                keep = (live[i] & live[j]).ravel()
                a, b = series[i].ravel()[keep], series[j].ravel()[keep]
                pairs.append(abs(np.corrcoef(a, b)[0, 1]))
        return float(np.median(pairs))

    shared = residual_correlation(FAIR_B)
    independent = residual_correlation(FAIR_A)
    assert shared > 0.98, f"S4F residuals are not shared (median |r| = {shared:.3f})"
    assert independent < 0.30, (
        f"S3F residuals are not independent (median |r| = {independent:.3f})")


def test_f6_duplication_does_not_create_information():
    """A copied channel must not buy what a genuinely different signal buys."""
    data = dataset(FAIR_A)
    duplicated = h92.duplicate_signal(data, "headcount", "headcount_copy")
    assert "headcount_copy" in duplicated["signals"]
    original = np.asarray(data["signals"]["headcount"]["values"], float)
    copy = np.asarray(duplicated["signals"]["headcount_copy"]["values"], float)
    assert np.allclose(np.nan_to_num(original), np.nan_to_num(copy)), (
        "the duplicate control is not a duplicate")


def test_f7_null_scenario_has_no_propagation():
    entries = loadings("S0_NULL")
    assert all(entry["loading"] == 0.0 for entry in entries.values()), (
        "S0 still propagates")
    assert any(entry["gamma"] != 0.0 for entry in entries.values()), (
        "S0 must keep the common state; removing it changes two things at once")
    relational = dataset("S0_NULL")["calibration"]["relational_rms"]
    assert all(value == 0.0 for value in relational.values()), relational


def test_f8_latent_state_never_reaches_the_observable_oracle():
    """What the oracle fits must be recomputable from the published observations alone."""
    for scenario in (FAIR_A, FAIR_B):
        data = dataset(scenario)
        for name in ("headcount", "establishments"):
            frame = h92.signal_frames(data, name)
            block = data["signals"][name]
            values = np.asarray(block["values"], float)
            mask = np.asarray(block["availability_mask"], bool)
            rows = np.flatnonzero(mask.any(1))
            scale = np.where(mask[rows], np.log(np.maximum(values, 1e-9))[rows], np.nan)
            expected = scale[1:] - scale[:-1]
            assert np.allclose(np.nan_to_num(frame["growth"]),
                               np.nan_to_num(expected)), f"{scenario}/{name}"


def test_f9_fair_seeds_are_fresh_and_the_driver_refuses_the_others():
    assert not set(gen.FAIR_SEEDS) & set(gen.CALIBRATION_SEEDS)
    assert not set(gen.FAIR_SEEDS) & set(gen.FINAL_SEEDS)
    assert len(gen.FAIR_SEEDS) == 20

    spec = importlib.util.spec_from_file_location(
        "fair_driver", REPO / "hpc" / "herald92" / "run_fair_contrast_array.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    for forbidden in (gen.FINAL_SEEDS[0], gen.CALIBRATION_SEEDS[0]):
        try:
            driver.run_task(FAIR_A, forbidden, 40, 4)
        except ValueError:
            continue
        raise AssertionError(f"the driver accepted seed {forbidden}")


def test_f10_gate_uses_paired_differences():
    """The verdict must come from a seed-by-seed difference, not two separate medians.

    Constructed so that the two scenarios have the *same* median gain while S3F wins in
    every seed. A gate comparing medians would find nothing; the paired gate must find it.
    """
    spec = importlib.util.spec_from_file_location(
        "fair_gate", REPO / "hpc" / "herald92" / "summarize_fair_contrast.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)

    seeds = list(gen.FAIR_SEEDS)
    swing = np.linspace(-0.04, 0.04, len(seeds))

    def block(scenario, values, own=0.0, pooled=0.0, duplicate=0.0):
        return {seed: {"scenario": scenario, "seed": seed, "summary": {
            "paired_pooling_improvement": float(value),
            "best_own_signal_gain": own, "best_pooled_signal_gain": pooled,
            "duplicate_adds": duplicate}}
            for seed, value in zip(seeds, values)}

    by_scenario = {
        "S0_NULL": block("S0_NULL", np.zeros(len(seeds))),
        # Same median (0.010) in both, but S3F is above S4F at every single seed.
        "S3F_COMPLEMENTARY": block(FAIR_A, 0.010 + swing + 0.002,
                                   own=0.0, pooled=1.0, duplicate=0.0),
        "S4F_REDUNDANT": block(FAIR_B, 0.010 + swing - 0.002),
    }
    medians_agree = abs(
        np.median([e["summary"]["paired_pooling_improvement"]
                   for e in by_scenario[FAIR_A].values()])
        - np.median([e["summary"]["paired_pooling_improvement"]
                     for e in by_scenario[FAIR_B].values()])) < 0.005
    assert medians_agree, "the fixture no longer isolates pairing"
    result = gate.evaluate(by_scenario, seeds, True)
    assert result["seeds_s3_beats_s4"] == len(seeds), (
        "the gate is not comparing seeds pairwise")
    assert result["checks"]["complementary_beats_redundant_seed_by_seed"]


def test_f11_the_pair_differs_only_in_the_declared_mechanism():
    """End to end: the audit that runs before the array must report a match."""
    report = audit.audit(list(gen.FAIR_SEEDS[:4]), 40)
    exact = [row for seed_rows in report["per_seed"].values() for row in seed_rows]
    assert all(row["ok"] for row in exact), [
        row["requirement"] for row in exact if not row["ok"]]
    mechanism = [row for row in exact
                 if row["requirement"] == "noise_groups_differ_this_is_the_mechanism"]
    assert mechanism and all(row["ok"] for row in mechanism), (
        "the audit no longer asserts that the mechanism is present")


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
            print(f"FAIL  {name}\n      {type(error).__name__}: {str(error)[:240]}")
    print(f"\n{len(names) - failures}/{len(names)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
