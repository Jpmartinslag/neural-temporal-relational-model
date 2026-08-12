"""Mutation audit for the HERALD 92 guards: each mutant removes one named mechanism."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location("g92", REPO / "tests" / "test_herald92_guards.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
h92, gen = g.h92, g.gen


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
            print(f"PASS  {name:38s} killed by {type(error).__name__}: {str(error)[:66]}")
            return True
        print(f"FAIL  {name:38s} SURVIVED  <-- guard insufficient")
        return False
    finally:
        undo()
        g._cache.clear()


def m_latent_leaks_to_model():
    original = gen.model_inputs

    def bad(dataset, decision_period):
        released = original(dataset, decision_period)
        released["metadata"] = dict(released["metadata"])
        released["metadata"]["latent_state"] = dataset["truth"]["state"]
        return released
    return swap(gen, "model_inputs", bad)


def m_oracle_reads_latent():
    original = h92.signal_frames

    def bad(dataset, name):
        frame = original(dataset, name)
        latent = np.asarray(dataset["truth"]["latent"][name])
        frame["growth"] = latent[1:1 + len(frame["growth"])]
        return frame
    return swap(h92, "signal_frames", bad)


def m_future_period_enters_design():
    original = h92._design_block

    def bad(frame, index, graph, graph_by_period, driver):
        design, ok = original(frame, index, graph, graph_by_period, driver)
        ahead = min(index + 1, len(frame["growth"]) - 1)
        design[:, 1] = np.nan_to_num(frame["growth"][ahead])[ok]
        return design, ok
    return swap(h92, "_design_block", bad)


def m_release_dates_ignored():
    original = gen.model_inputs

    def bad(dataset, decision_period):
        released = original(dataset, len(dataset["metadata"]["years"]) - 1)
        return released
    return swap(gen, "model_inputs", bad)


def m_null_gets_propagation():
    original = gen.scenario_loadings

    def bad(scenario, scale):
        loadings = original(scenario, scale)
        if scenario == "S0_NULL":
            for name, entry in loadings.items():
                entry["loading"] = gen.SIGNAL_SPEC[name]["loading"] * scale
        return loadings
    return swap(gen, "scenario_loadings", bad)


def m_complementary_quietens_the_joint_arm():
    """S3 by cutting noise instead of by partial measurement."""
    original = gen.scenario_loadings

    def bad(scenario, scale):
        loadings = original(scenario, scale)
        if scenario == "S3_COMPLEMENTARY":
            for name, entry in loadings.items():
                entry["gamma"] = gen.SIGNAL_SPEC[name]["gamma"] * scale
                entry["loading"] = gen.SIGNAL_SPEC[name]["loading"] * scale
        return loadings
    return swap(gen, "scenario_loadings", bad)


def m_conflicting_flips_only_one_loading():
    original = gen.scenario_loadings

    def bad(scenario, scale):
        loadings = original(scenario, scale)
        if scenario == "S5_CONFLICTING":
            for name in ("establishments", "creations"):
                loadings[name]["loading"] = abs(loadings[name]["loading"])
        return loadings
    return swap(gen, "scenario_loadings", bad)


def m_redundant_keeps_independent_noise():
    original = gen.scenario_loadings

    def bad(scenario, scale):
        loadings = original(scenario, scale)
        if scenario == "S4_REDUNDANT":
            loadings["payroll"]["noise_group"] = "payroll"
        return loadings
    return swap(gen, "scenario_loadings", bad)


def m_absence_becomes_zero():
    original = h92.signal_frames

    def bad(dataset, name):
        frame = original(dataset, name)
        frame["usable"] = np.ones_like(frame["usable"])
        frame["growth"] = np.nan_to_num(frame["growth"])
        return frame
    return swap(h92, "signal_frames", bad)


def m_self_loops_restored():
    original = h92.build_graphs

    def bad(dataset, seed=92000):
        graphs = original(dataset, seed)
        for key in ("prior", "permuted", "degree_matched"):
            np.fill_diagonal(graphs[key], 0.2)
        return graphs
    return swap(h92, "build_graphs", bad)


def m_weights_fall_back_to_uniform():
    def bad(frames, train_rows):
        return {name: 1.0 for name in frames}
    return swap(h92, "pooling_weights", bad)


def m_weights_lose_their_sign():
    original = h92.pooling_weights

    def bad(frames, train_rows):
        return {name: abs(value) for name, value in original(frames, train_rows).items()}
    return swap(h92, "pooling_weights", bad)


def m_arms_collapse():
    original = h92.degree_matched_random
    return swap(h92, "degree_matched_random", lambda matrix, seed: matrix.copy())


def m_permutation_is_identity():
    return swap(h92, "derangement", lambda matrix, seed: matrix.copy())


def m_pooling_disabled():
    """Remove the mechanism itself: the pooled driver becomes the signal's own."""
    return swap(h92, "pooled_driver", lambda frames, period_row, weights=None: None)


def m_calibration_accepts_final_seeds():
    import importlib.util as util
    path = REPO / "hpc" / "herald92" / "run_oracle_array.py"
    backup = path.read_text()
    path.write_text(backup.replace(
        '    if seed in FINAL_SEEDS:\n'
        '        raise ValueError(f"seed {seed} is a final seed and must not calibrate anything")\n',
        ''))
    return lambda: path.write_text(backup)


def m_nondeterministic_weights():
    original = h92.pooling_weights

    def bad(frames, train_rows):
        weights = original(frames, train_rows)
        jitter = np.random.default_rng().normal(0, 0.05)
        return {name: value + jitter for name, value in weights.items()}
    return swap(h92, "pooling_weights", bad)


def m_redundant_also_strengthens_payroll():
    """The defect the v2 array actually carried: S4 becomes a stronger world, not a
    redundant one."""
    original = gen.scenario_loadings

    def bad(scenario, scale):
        loadings = original(scenario, scale)
        if scenario == "S4_REDUNDANT":
            loadings["payroll"]["gamma"] = loadings["headcount"]["gamma"]
            loadings["payroll"]["loading"] = loadings["headcount"]["loading"]
        return loadings
    return swap(gen, "scenario_loadings", bad)


CASES = [
    ("redundant_also_strengthens_payroll",
     g.test_g20_redundancy_changes_the_noise_and_nothing_else,
     m_redundant_also_strengthens_payroll),
    ("latent_leaks_to_model", g.test_g1_latent_state_never_reaches_the_model,
     m_latent_leaks_to_model),
    ("oracle_reads_latent", g.test_g19_oracle_frames_equal_the_published_observations,
     m_oracle_reads_latent),
    ("future_period_in_design", g.test_g3_no_future_period_enters_a_design,
     m_future_period_enters_design),
    ("release_dates_ignored", g.test_g4_release_dates_gate_the_inputs,
     m_release_dates_ignored),
    ("null_gets_propagation",
     g.test_g5_null_scenario_has_no_propagation_but_keeps_the_state, m_null_gets_propagation),
    ("complementary_quietens_joint_arm",
     g.test_g6_complementary_scenario_weakens_measurement_not_the_joint_arm,
     m_complementary_quietens_the_joint_arm),
    ("conflicting_flips_one_loading", g.test_g7_conflicting_scenario_keeps_its_magnitude,
     m_conflicting_flips_only_one_loading),
    ("redundant_keeps_independent_noise", g.test_g8_redundant_scenario_shares_a_noise_group,
     m_redundant_keeps_independent_noise),
    ("absence_becomes_zero", g.test_g9_absence_stays_absent_and_masks_are_honoured,
     m_absence_becomes_zero),
    ("self_loops_restored", g.test_g10_no_self_loop_in_any_graph, m_self_loops_restored),
    ("weights_uniform_fallback", g.test_g11_annual_signals_carry_real_weight_in_the_pool,
     m_weights_fall_back_to_uniform),
    ("weights_lose_sign", g.test_g12_pooling_weights_recover_opposite_signs,
     m_weights_lose_their_sign),
    ("degree_control_equals_prior", g.test_g14_permutation_and_degree_control_preserve_structure,
     m_arms_collapse),
    ("permutation_is_identity", g.test_g14_permutation_and_degree_control_preserve_structure,
     m_permutation_is_identity),
    ("pooling_disabled", g.test_g16_complementary_scenario_shows_the_mechanism,
     m_pooling_disabled),
    ("calibration_accepts_final_seeds", g.test_g17_final_seeds_never_calibrate,
     m_calibration_accepts_final_seeds),
    ("nondeterministic_weights", g.test_g18_determinism, m_nondeterministic_weights),
]


if __name__ == "__main__":
    survivors = len(CASES) - sum(killed(*case) for case in CASES)
    print(f"\n{len(CASES) - survivors}/{len(CASES)} mutants killed")
    raise SystemExit(1 if survivors else 0)
