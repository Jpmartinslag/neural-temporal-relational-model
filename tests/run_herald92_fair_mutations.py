"""Mutation audit for the matched-contrast guards.

Every mutant reinstates a concrete defect that the fair pair was built to exclude. None of
them stubs a function with a constant or deletes it wholesale: each reproduces a mistake
that could plausibly be made, and the paired guard must catch it.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location(
    "f92", REPO / "tests" / "test_herald92_fair_guards.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
gen, h92 = g.gen, g.h92


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
            print(f"PASS  {name:42s} killed by {type(error).__name__}: {str(error)[:62]}")
            return True
        print(f"FAIL  {name:42s} SURVIVED  <-- guard insufficient")
        return False
    finally:
        undo()
        g._cache.clear()


def m_amplitude_differs_between_the_pair():
    """The exact defect of the previous pair: S3F scaled down, S4F not."""
    original = gen.scenario_loadings

    def bad(scenario, scale):
        entries = original(scenario, scale)
        if scenario == "S3F_COMPLEMENTARY":
            for entry in entries.values():
                entry["gamma"] *= 0.35
                entry["loading"] *= 0.35
        return entries
    return swap(gen, "scenario_loadings", bad)


def m_noise_budget_differs():
    """Redundancy bought by making the redundant scenario quieter, not by sharing error.

    The scaling happens inside the simulator and only for the one-group scenario, so the
    declared ``noise_rms`` in the calibration block is untouched: the guard can only catch
    this by measuring the realised residual.
    """
    original = gen._simulate

    def bad(config, graphs, loadings, years, rng):
        result = original(config, graphs, loadings, years, rng)
        if len({entry["noise_group"] for entry in loadings.values()}) == 1:
            for name in gen.SIGNAL_SPEC:
                spec = gen.SIGNAL_SPEC[name]
                latent = result["latent"][name]
                common = result["common"][name]
                relational = result["relational"][name]
                quieter = np.array(latent)
                for t in range(len(years) - 1):
                    residual = (latent[t + 1] - spec["ar_log"] * latent[t]
                                - common[t + 1] - relational[t + 1])
                    quieter[t + 1] = (spec["ar_log"] * quieter[t] + common[t + 1]
                                      + relational[t + 1] + 0.5 * residual)
                result["latent"][name] = quieter
        return result
    return swap(gen, "_simulate", bad)


def m_noise_allocated_per_group_again():
    """Draw the noise per group, so the two scenarios consume the stream differently and
    silently end up with different latent states at the same seed."""
    original = gen._simulate

    def bad(config, graphs, loadings, years, rng):
        groups = sorted({entry["noise_group"] for entry in loadings.values()})
        rng.normal(0.0, 1.0, size=(len(groups), len(years), config.n_zones))
        return original(config, graphs, loadings, years, rng)
    return swap(gen, "_simulate", bad)


def m_complementary_shares_two_signals():
    """S3F is no longer five independent views: two of them collapse into one."""
    original = gen.scenario_loadings

    def bad(scenario, scale):
        entries = original(scenario, scale)
        if scenario == "S3F_COMPLEMENTARY":
            entries["payroll"]["noise_group"] = "headcount"
        return entries
    return swap(gen, "scenario_loadings", bad)


def m_redundant_keeps_independent_noise():
    """S4F stops being redundant: the contrast becomes S1 against S1."""
    original = gen.scenario_loadings

    def bad(scenario, scale):
        entries = original(scenario, scale)
        if scenario == "S4F_REDUNDANT":
            for name, entry in entries.items():
                entry["noise_group"] = name
        return entries
    return swap(gen, "scenario_loadings", bad)


def m_duplicate_is_not_a_duplicate():
    """The duplication control quietly becomes an independent second signal."""
    original = h92.duplicate_signal

    def bad(dataset, source, alias, jitter=0.0, seed=0):
        result = original(dataset, source, alias, jitter=jitter, seed=seed)
        rng = np.random.default_rng(1234)
        values = np.asarray(result["signals"][alias]["values"], float)
        result["signals"][alias] = dict(result["signals"][alias])
        result["signals"][alias]["values"] = values * rng.normal(1.0, 0.5, values.shape)
        return result
    return swap(h92, "duplicate_signal", bad)


def m_null_gets_propagation():
    original = gen.scenario_loadings

    def bad(scenario, scale):
        entries = original(scenario, scale)
        if scenario == "S0_NULL":
            for name, entry in entries.items():
                entry["loading"] = gen.SIGNAL_SPEC[name]["loading"] * scale
        return entries
    return swap(gen, "scenario_loadings", bad)


def m_oracle_reads_the_latent_path():
    original = h92.signal_frames

    def bad(dataset, name):
        frame = original(dataset, name)
        latent = np.asarray(dataset["truth"]["latent"][name])
        frame["growth"] = latent[1:1 + len(frame["growth"])]
        return frame
    return swap(h92, "signal_frames", bad)


def m_driver_accepts_reserved_seeds():
    path = REPO / "hpc" / "herald92" / "run_fair_contrast_array.py"
    backup = path.read_text()
    mutated = backup.replace(
        '    if seed in FINAL_SEEDS:\n'
        '        raise ValueError(f"seed {seed} is a final seed and must not calibrate anything")\n'
        '    if seed in CALIBRATION_SEEDS:\n'
        '        raise ValueError(f"seed {seed} belongs to the development arrays; the fair "\n'
        '                         "contrast runs on fresh seeds only")\n', '')
    assert mutated != backup, "the mutation did not apply; the driver text changed"
    path.write_text(mutated)
    return lambda: path.write_text(backup)


def m_gate_compares_medians_not_pairs():
    """The defect the paired design exists to prevent: two separate medians."""
    path = REPO / "hpc" / "herald92" / "summarize_fair_contrast.py"
    backup = path.read_text()
    mutated = backup.replace(
        "    difference = np.array(\n"
        "        [by_scenario[\"S3F_COMPLEMENTARY\"][seed][\"summary\"][\"paired_pooling_improvement\"]\n"
        "         - by_scenario[\"S4F_REDUNDANT\"][seed][\"summary\"][\"paired_pooling_improvement\"]\n"
        "         for seed in paired_seeds], float)",
        "    difference = np.array(\n"
        "        [by_scenario[\"S3F_COMPLEMENTARY\"][seed][\"summary\"][\"paired_pooling_improvement\"]\n"
        "         - float(np.median(s4_paired))\n"
        "         for seed in paired_seeds], float)")
    assert mutated != backup, "the mutation did not apply; the gate text changed"
    path.write_text(mutated)
    return lambda: path.write_text(backup)


def m_audit_skips_the_mechanism_assertion():
    """The equality audit stops checking that the pair differs at all, so an accidental
    S3F-against-S3F contrast would be reported as perfectly matched."""
    original = g.audit.compare

    def bad(left, right):
        return [row for row in original(left, right)
                if row["requirement"] != "noise_groups_differ_this_is_the_mechanism"]
    return swap(g.audit, "compare", bad)


CASES = [
    ("amplitude_differs_between_pair", g.test_f1_same_relational_strength,
     m_amplitude_differs_between_the_pair),
    ("noise_budget_differs", g.test_f2_same_noise_budget, m_noise_budget_differs),
    ("noise_allocated_per_group_again",
     g.test_f3_equivalent_marginals_and_the_same_latent_draw,
     m_noise_allocated_per_group_again),
    ("complementary_shares_two_signals",
     g.test_f4_complementary_noise_is_genuinely_independent,
     m_complementary_shares_two_signals),
    ("redundant_keeps_independent_noise", g.test_f5_redundant_noise_is_genuinely_shared,
     m_redundant_keeps_independent_noise),
    ("duplicate_is_not_a_duplicate", g.test_f6_duplication_does_not_create_information,
     m_duplicate_is_not_a_duplicate),
    ("null_gets_propagation", g.test_f7_null_scenario_has_no_propagation,
     m_null_gets_propagation),
    ("oracle_reads_latent_path",
     g.test_f8_latent_state_never_reaches_the_observable_oracle,
     m_oracle_reads_the_latent_path),
    ("driver_accepts_reserved_seeds",
     g.test_f9_fair_seeds_are_fresh_and_the_driver_refuses_the_others,
     m_driver_accepts_reserved_seeds),
    ("gate_compares_medians_not_pairs", g.test_f10_gate_uses_paired_differences,
     m_gate_compares_medians_not_pairs),
    ("audit_skips_mechanism_assertion",
     g.test_f11_the_pair_differs_only_in_the_declared_mechanism,
     m_audit_skips_the_mechanism_assertion),
]


if __name__ == "__main__":
    survivors = len(CASES) - sum(killed(*case) for case in CASES)
    print(f"\n{len(CASES) - survivors}/{len(CASES)} mutants killed")
    raise SystemExit(1 if survivors else 0)
