"""Guards for HERALD 92: the multisignal generator and its observable oracle.

NumPy only. Each guard names one mechanism; ``run_herald92_mutations.py`` removes exactly
that mechanism and must break it.
"""
from __future__ import annotations

import inspect
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.data.synthetic import generate_france_multisignal_v92 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald92_multisignal_oracle as h92  # noqa: E402

SMALL = dict(n_zones=60)
_cache: dict = {}


def dataset(scenario: str = "S1_SHARED", seed: int = 9301) -> dict:
    key = (scenario, seed)
    if key not in _cache:
        _cache[key] = gen.generate_multisignal(
            gen.MultisignalConfig(seed=seed, scenario=scenario, **SMALL))
    return _cache[key]


def evaluated(scenario: str = "S1_SHARED") -> dict:
    key = f"eval::{scenario}"
    if key not in _cache:
        _cache[key] = h92.evaluate_scenario(dataset(scenario), n_score=8)
    return _cache[key]


# ── Leakage ──────────────────────────────────────────────────────────────────

def test_g1_latent_state_never_reaches_the_model():
    released = gen.model_inputs(dataset(), 60)
    blob = repr(sorted(released.keys())) + repr(sorted(released["metadata"].keys()))
    for forbidden in ("truth", "state", "latent", "relational", "calibration",
                      "propagation", "low_information"):
        assert forbidden not in blob, f"{forbidden!r} reachable from model inputs"
    assert set(released["signals"]) == set(gen.SIGNAL_SPEC)


def test_g2_oracle_reads_no_latent_variable():
    """Checked on the code, not the prose: docstrings may name what code must not touch."""
    import ast
    names: set[str] = set()
    for function in ("signal_frames", "standardised_driver", "pooled_driver",
                     "pooling_weights", "_fit_gain", "_design_block", "score_signal"):
        tree = ast.parse(inspect.getsource(getattr(h92, function)).lstrip())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.add(node.value)
    for forbidden in ("truth", "state", "latent", "relational", "common", "propagation"):
        offenders = {name for name in names if forbidden == name.lower()}
        assert not offenders, f"the oracle path touches {offenders}"


def test_g3_no_future_period_enters_a_design():
    frame = h92.signal_frames(dataset(), "headcount")
    design, ok = h92._design_block(frame, 20, None, None, None)
    perturbed = {key: (value.copy() if isinstance(value, np.ndarray) else value)
                 for key, value in frame.items()}
    perturbed["growth"][21:] *= 9.0
    later, _ = h92._design_block(perturbed, 20, None, None, None)
    assert np.allclose(design, later), "a future period changed a past design row"


def test_g4_release_dates_gate_the_inputs():
    released_early = gen.model_inputs(dataset(), 20)
    released_late = gen.model_inputs(dataset(), 100)
    early = int(released_early["signals"]["headcount"]["availability_mask"].sum())
    late = int(released_late["signals"]["headcount"]["availability_mask"].sum())
    assert 0 < early < late, (early, late)


# ── Generator mechanism ──────────────────────────────────────────────────────

def test_g5_null_scenario_has_no_propagation_but_keeps_the_state():
    calibration = dataset("S0_NULL")["calibration"]
    assert all(value == 0.0 for value in calibration["relational_share"].values()), (
        "S0 injected a relational term")
    assert any(value > 0.1 for value in calibration["common_share"].values()), (
        "S0 removed the common state as well; then it is not a relational null")


def test_g6_complementary_scenario_weakens_measurement_not_the_joint_arm():
    """S3 must reduce what each signal sees, not give the combination quieter data."""
    shared = dataset("S1_SHARED")["calibration"]
    complementary = dataset("S3_COMPLEMENTARY")["calibration"]
    for name in gen.SIGNAL_SPEC:
        assert complementary["common_share"][name] < shared["common_share"][name], name
        assert complementary["relational_share"][name] < shared["relational_share"][name], name
    # Noise groups must be untouched: complementarity comes from partial measurement.
    assert ({entry["noise_group"] for entry in shared["loadings"].values()}
            == {entry["noise_group"] for entry in complementary["loadings"].values()})


def test_g7_conflicting_scenario_keeps_its_magnitude():
    conflicting = dataset("S5_CONFLICTING")["calibration"]["loadings"]
    shared = dataset("S1_SHARED")["calibration"]["loadings"]
    flipped = [name for name in gen.SIGNAL_SPEC
               if np.sign(conflicting[name]["gamma"]) != np.sign(shared[name]["gamma"])]
    assert flipped, "S5 flipped nothing"
    for name in gen.SIGNAL_SPEC:
        assert abs(conflicting[name]["gamma"]) == abs(shared[name]["gamma"]), name
        assert abs(conflicting[name]["loading"]) == abs(shared[name]["loading"]), name
    for name in flipped:
        assert (np.sign(conflicting[name]["gamma"])
                == np.sign(conflicting[name]["loading"])), (
            f"{name} flipped only one loading; the mechanism is cancelled, not opposed")


def test_g8_redundant_scenario_shares_a_noise_group():
    groups = {name: entry["noise_group"]
              for name, entry in dataset("S4_REDUNDANT")["calibration"]["loadings"].items()}
    assert groups["payroll"] == groups["headcount"], "S4 did not share the noise"
    assert len(set(groups.values())) < len(gen.SIGNAL_SPEC)


def test_g9_absence_stays_absent_and_masks_are_honoured():
    block = dataset()["signals"]["establishments"]
    mask = block["availability_mask"].astype(bool)
    assert np.isnan(block["values"][~mask]).all(), "a masked cell carries a value"
    frame = h92.signal_frames(dataset(), "establishments")
    assert frame["usable"].sum() > 0 and not frame["usable"].all()


def test_g10_no_self_loop_in_any_graph():
    graphs = h92.build_graphs(dataset())
    assert np.allclose(np.diagonal(graphs["true"], axis1=1, axis2=2), 0.0)
    for name in ("prior", "permuted", "degree_matched"):
        assert np.allclose(np.diag(graphs[name]), 0.0), name


# ── Oracle mechanism ─────────────────────────────────────────────────────────

def test_g11_annual_signals_carry_real_weight_in_the_pool():
    """Behavioural, not textual: annual and quarterly signals rarely share a row.

    An implementation that zero-fills the missing quarters, or that falls back to uniform
    weights when the fully-observed intersection is thin, gives the annual signals no
    influence and quietly reduces the pool to the quarterly pair. The check is on the
    weights themselves, so any implementation that achieves the mechanism passes.
    """
    frames = {name: h92.signal_frames(dataset(), name) for name in gen.SIGNAL_SPEC}
    rows = sorted({int(r) for f in frames.values() for r in f["period_rows"]})
    weights = h92.pooling_weights(frames, rows[:40])
    assert set(weights) == set(gen.SIGNAL_SPEC)
    annual = [abs(weights[name]) for name in ("establishments", "creations")]
    assert max(annual) > 0.05, (
        f"annual signals carry no weight in the pool: {annual}")
    assert len({round(value, 6) for value in weights.values()}) > 1, (
        f"every signal received the same weight; this is a uniform fallback: {weights}")


def test_g12_pooling_weights_recover_opposite_signs():
    frames = {name: h92.signal_frames(dataset("S5_CONFLICTING"), name)
              for name in gen.SIGNAL_SPEC}
    rows = sorted({int(r) for f in frames.values() for r in f["period_rows"]})
    weights = h92.pooling_weights(frames, rows[:40])
    signs = {np.sign(value) for value in weights.values() if abs(value) > 0.1}
    assert len(signs) > 1, (
        f"the estimator produced one sign under conflicting loadings: {weights}")


def test_g13_arms_are_genuinely_different():
    graphs = h92.build_graphs(dataset())
    scored = h92.score_signal(dataset(), "headcount", graphs, n_score=8)
    values = [scored[arm] for arm in h92.ARMS]
    assert len(set(round(v, 6) for v in values)) == len(values), (
        f"two arms produced the same deviance: {dict(zip(h92.ARMS, values))}")


def test_g14_permutation_and_degree_control_preserve_structure():
    """Preserving the weights is necessary but not sufficient: identity preserves them too."""
    graphs = h92.build_graphs(dataset())
    prior = graphs["prior"]
    assert np.allclose(np.sort(prior, axis=None), np.sort(graphs["permuted"], axis=None))
    assert not np.array_equal(prior, graphs["permuted"]), (
        "the permutation left the matrix unchanged; it is an identity, not a placebo")
    assert np.array_equal((prior > 0).sum(1), (graphs["degree_matched"] > 0).sum(1))
    assert not np.array_equal(prior > 0, graphs["degree_matched"] > 0)


def test_g19_oracle_frames_equal_the_published_observations():
    """Behavioural counterpart to g2: a runtime substitution is invisible to an AST check.

    The growth the oracle fits must be recomputable from the signal block the model is
    allowed to see, so swapping in the latent path breaks this even though the source text
    never changes.
    """
    for name in ("headcount", "establishments"):
        frame = h92.signal_frames(dataset(), name)
        block = dataset()["signals"][name]
        values = np.asarray(block["values"], float)
        mask = np.asarray(block["availability_mask"], bool)
        rows = np.flatnonzero(mask.any(1))
        scale = np.where(mask[rows], np.log(np.maximum(values[rows], 1e-9)), np.nan)
        expected = scale[1:] - scale[:-1]
        assert np.allclose(np.nan_to_num(frame["growth"]), np.nan_to_num(expected)), (
            f"{name}: the oracle is not fitting the published observations")


def test_g15_null_scenario_shows_no_pooling_benefit():
    result = evaluated("S0_NULL")
    assert abs(result["paired_pooling_improvement"]) < 0.02, (
        f"pooling helped in the null: {result['paired_pooling_improvement']:+.4%}")


def test_g16_complementary_scenario_shows_the_mechanism():
    result = evaluated("S3_COMPLEMENTARY")
    assert result["best_pooled_signal_gain"] > result["best_own_signal_gain"], (
        "pooling did not improve the decisive scenario")
    assert result["n_signals_improved_by_pooling"] >= 2


def test_g17_final_seeds_never_calibrate():
    assert not set(gen.CALIBRATION_SEEDS) & set(gen.FINAL_SEEDS)
    import importlib.util
    path = pathlib.Path(__file__).resolve().parents[1] / "hpc" / "herald92" / "run_oracle_array.py"
    spec = importlib.util.spec_from_file_location("oracle_array", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    grid = module.task_grid()
    assert grid, "the array grid is empty"
    assert all(seed in gen.CALIBRATION_SEEDS for _, seed in grid), (
        "a final seed entered the calibration array")
    try:
        module.run_task("S1_SHARED", gen.FINAL_SEEDS[0], 20, 4)
    except ValueError:
        return
    raise AssertionError("a final seed was accepted by the calibration task")


def test_g18_determinism():
    first = h92.evaluate_scenario(dataset("S1_SHARED"), n_score=8)
    second = h92.evaluate_scenario(dataset("S1_SHARED"), n_score=8)
    assert first["best_pooled_signal_gain"] == second["best_pooled_signal_gain"]
    assert first["joint"]["pooling_weights"] == second["joint"]["pooling_weights"]


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
