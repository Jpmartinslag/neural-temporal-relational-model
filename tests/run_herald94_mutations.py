"""HERALD 94 mutation audit: every guard must be killable by removing its own mechanism.

Each mutant removes **exactly one** mechanism and nothing else. None of them is a stub that
returns a constant: a constant kills every guard that touches it and therefore proves that
the guards run, not that they test anything. The previous stage produced three guards that
passed for the wrong reason and were only found this way.

Patches are applied in memory, never to the source files. Rewriting a module on disk and
re-importing leaves the already-imported object in place, which is how two mutants survived
in HERALD 93 while appearing to have been applied.

Run: ``python3 tests/run_herald94_mutations.py``
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic import generate_france_multisignal_v94 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald94_composite as arms  # noqa: E402
from src.modeles.france_ze2020 import herald94_temporal_features as feat  # noqa: E402
from tests import test_herald94_guards as guards  # noqa: E402


@contextlib.contextmanager
def swap(module, name: str, replacement):
    original = getattr(module, name)
    setattr(module, name, replacement)
    try:
        yield
    finally:
        setattr(module, name, original)


# ── mutants ──────────────────────────────────────────────────────────────────

def m01_features_see_the_future():
    """The rolling slope reads the whole series instead of the trailing window."""
    def leaky(series, window):
        out = np.full(series.shape, np.nan)
        for t in range(len(series)):
            block = series                      # the whole panel, past and future alike
            seen = np.isfinite(block)
            if seen.sum() < 3:
                continue
            clock = np.arange(len(block), dtype=float)[:, None]
            mean_x = (seen * clock).sum(0) / np.maximum(seen.sum(0), 1)
            mean_y = np.where(seen, block, 0.0).sum(0) / np.maximum(seen.sum(0), 1)
            cx = (clock - mean_x) * seen
            cy = np.where(seen, block - mean_y, 0.0)
            variance = (cx ** 2).sum(0)
            out[t] = np.divide((cx * cy).sum(0), variance,
                               out=np.zeros(series.shape[1]), where=variance > 1e-12)
        return out
    return swap(feat, "_rolling_slope", leaky)


def m02_absence_becomes_zero():
    def zero_fill(block):
        fresh = np.isfinite(block).astype(float)
        return np.nan_to_num(block, nan=0.0), fresh
    return swap(feat, "resolve_missing", zero_fill)


def m03_carry_forward_reads_backwards():
    def bidirectional(block):
        out = block.copy()
        for _ in range(2):
            out = np.where(np.isfinite(out), out, np.roll(out, -1, axis=0))
        forward = feat._carry_forward.__wrapped__(block) if hasattr(
            feat._carry_forward, "__wrapped__") else None
        assert forward is None or True
        return out
    return swap(feat, "_carry_forward", bidirectional)


def m04_product_composite_becomes_a_sum():
    """`C4` stops being a product, so it falls inside the linear span."""
    mutated = {key: dict(value) for key, value in feat.COMPOSITE_SPEC.items()}
    mutated["C4_tight_labour"]["kind"] = "difference"
    return swap(feat, "COMPOSITE_SPEC", mutated)


def m05_linear_composite_becomes_a_product():
    mutated = {key: dict(value) for key, value in feat.COMPOSITE_SPEC.items()}
    mutated["C1_wage_per_head"]["kind"] = "product"
    return swap(feat, "COMPOSITE_SPEC", mutated)


def m06_gradient_drops_the_activation_derivative():
    def wrong(params, x):
        _, activation = arms.mlp_forward(params, x)
        return np.repeat((activation * params["w2"]).sum(1, keepdims=True),
                         params["w1"].shape[0], axis=1) * 0.0 + \
            (params["w1"] @ params["w2"])[None, :]
    return swap(arms, "marginal_effects", wrong)


def m07_mixed_partial_uses_the_wrong_curvature():
    def wrong(params, x, first, second):
        _, activation = arms.mlp_forward(params, x)
        curvature = (1.0 - activation ** 2) * params["w2"]     # first derivative, not second
        return (curvature * params["w1"][first] * params["w1"][second]).sum(1)
    return swap(arms, "mixed_partial", wrong)


def m08_activation_is_not_smooth_at_the_origin():
    """A rectifier: the small-weight limit is no longer the linear map the nesting needs."""
    def rectified(params, x):
        activation = np.maximum(x @ params["w1"] + params["b1"], 0.0)
        return activation @ params["w2"] + params["b2"], activation
    return swap(arms, "mlp_forward", rectified)


def m09_fitting_is_not_deterministic():
    original = arms.initialise_mlp

    def jittered(n_features, hidden, seed):
        params = original(n_features, hidden, seed)
        params["w1"] = params["w1"] + np.random.default_rng().normal(
            0.0, 1e-3, size=params["w1"].shape)
        return params
    return swap(arms, "initialise_mlp", jittered)


def m10_permutation_acts_across_periods():
    """The control shuffles time instead of zones, so it no longer preserves the period effect."""
    def across(raw, plan, seed):
        rng = np.random.default_rng(seed)
        for signal, features in plan.items():
            for feature in features:
                block = raw[signal][feature]
                block[:] = block[rng.permutation(len(block))]
    return swap(feat, "permute_raw_blocks", across)


def m11_null_scenario_carries_a_mechanism():
    original = gen.scenario_loadings

    def leaky(scenario, scale):
        base = original("N1_LINEAR" if scenario == "N0_NULL" else scenario, scale)
        return base
    return swap(gen, "scenario_loadings", leaky)


def m12_random_stream_depends_on_the_scenario():
    """Noise drawn per group, so scenarios with different group counts diverge."""
    original = gen._simulate

    def divergent(config, propagation, loadings, years, rng):
        groups = {entry["noise_group"] for entry in loadings.values()}
        rng.normal(0.0, 1.0, size=(len(groups), len(years), config.n_zones))
        return original(config, propagation, loadings, years, rng)
    return swap(gen, "_simulate", divergent)


def m13_regime_gate_is_not_normalised():
    """The gate keeps its own root-mean-square, so `N3` carries more mechanism than `N1`.

    Raising `REGIME_GATE_RISING` was the first attempt and it changed nothing at all: the
    normalisation divides the constant straight back out, so the mutant removed no mechanism
    and the guard was right to stay quiet. The mechanism is the normalisation itself.
    """
    def unnormalised(state):
        rising = state[:-1] >= 0.0
        gate = np.where(rising, gen.REGIME_GATE_RISING, gen.REGIME_GATE_FALLING)
        return np.concatenate([np.ones((1, state.shape[1])), gate])
    return swap(gen, "_regime_gate", unnormalised)


def m14_nonlinear_link_becomes_linear():
    mutated = dict(gen.LINK_OF)
    mutated["N2_NONLINEAR"] = "linear"
    return swap(gen, "LINK_OF", mutated)


def m15_interaction_link_propagates_one_component():
    original = gen._propagate

    def one_component(link, matrix, state_u, state_v):
        if link == "product":
            return matrix @ (state_u - state_u.mean())
        return original(link, matrix, state_u, state_v)
    return swap(gen, "_propagate", one_component)


def m16_components_are_not_split():
    mutated = {name: "u" for name in gen.COMPONENT_OF}
    return swap(gen, "COMPONENT_OF", mutated)


def m17_redundant_scenario_keeps_independent_noise():
    original = gen.scenario_loadings

    def independent(scenario, scale):
        base = original("N1_LINEAR" if scenario == "N5_REDUNDANT" else scenario, scale)
        return base
    return swap(gen, "scenario_loadings", independent)


def m18_unknown_scenarios_are_accepted():
    original = gen.scenario_loadings

    def permissive(scenario, scale):
        try:
            return original(scenario, scale)
        except ValueError:
            return original("N1_LINEAR", scale)
    return swap(gen, "scenario_loadings", permissive)


def m19_release_lag_is_ignored():
    def leaky(dataset, decision_period):
        years = np.asarray(dataset["metadata"]["years"])
        result = {"signals": {}, "metadata": {
            key: value for key, value in dataset["metadata"].items()
            if key not in ("low_information",)}}
        for name, block in dataset["signals"].items():
            temporal = np.arange(len(years))[:, None] <= decision_period
            final = block["availability_mask"].astype(bool) & temporal
            result["signals"][name] = {
                "values": np.where(final, block["values"], np.nan),
                "availability_mask": final.astype(np.int8),
                "family": block["family"], "freq": block["freq"]}
        return result
    return swap(gen, "model_inputs", leaky)


def m20_rows_read_the_target_period():
    original = arms.assemble_rows

    def shifted(table, target, periods, columns=None):
        return original(table, target, [period + 1 for period in periods], columns)
    return swap(arms, "assemble_rows", shifted)


def m21_temporal_placebo_does_nothing():
    return swap(arms, "permute_across_periods", lambda x, keys, seed: x.copy())


def m22_penalty_selection_is_not_reproducible():
    """The penalty changes between two identical calls.

    Drawing it at random was the first attempt and it survived once in six: with a grid of
    six alphas, two random draws coincide often enough that a probabilistic mutant is not a
    test. This one alternates on a call counter, so the second call always disagrees with
    the first.
    """
    counter = {"calls": 0}

    def alternating(x, y, periods=None):
        counter["calls"] += 1
        return float(arms.RIDGE_ALPHAS[counter["calls"] % len(arms.RIDGE_ALPHAS)])
    return swap(arms, "choose_alpha", alternating)


def m23_final_seeds_collide_with_an_earlier_stage():
    return swap(gen, "FINAL_SEEDS", (9401, 9402, 9403, 9404, 9405))


def m24_a_forbidden_ratio_is_formed():
    mutated = {key: dict(value) for key, value in feat.COMPOSITE_SPEC.items()}
    mutated["C7_creation_rate_per_stock"] = {
        "kind": "ratio", "terms": (("creations", "growth"), ("establishments", "level")),
        "linear_in_features": False}
    return swap(feat, "COMPOSITE_SPEC", mutated)


MUTANTS = [value for key, value in sorted(globals().items())
           if key.startswith("m") and key[1:3].isdigit() and callable(value)]


def main() -> int:
    survivors = []
    for mutant in MUTANTS:
        context = mutant()
        killed_by = []
        if context is None:
            survivors.append((mutant.__name__, "the mutant did not apply"))
            print(f"SURVIVED {mutant.__name__}: the mutant did not apply")
            continue
        with context:
            for guard in guards.GUARDS:
                try:
                    guard()
                except Exception:                             # noqa: BLE001
                    killed_by.append(guard.__name__)
        if killed_by:
            print(f"killed   {mutant.__name__:48s} by {', '.join(killed_by[:3])}"
                  + (f" (+{len(killed_by) - 3})" if len(killed_by) > 3 else ""))
        else:
            survivors.append((mutant.__name__, "no guard noticed"))
            print(f"SURVIVED {mutant.__name__}: no guard noticed")
    print(f"\n{len(MUTANTS) - len(survivors)}/{len(MUTANTS)} mutants killed")
    for name, reason in survivors:
        print(f"  survivor: {name} -- {reason}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
