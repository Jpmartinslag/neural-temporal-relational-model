"""HERALD 95 mutation audit: the scale parameter must be killable where it is claimed.

Every guard asserts something about what ``relational_scale`` does and does not touch. Each
mutant here breaks exactly one of those claims, in memory, and at least one guard must
notice. A guard no mutant can kill is decoration.

Run: ``python3 tests/run_herald95_mutations.py``
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
from src.modeles.france_ze2020 import herald95_scale_ladder as ladder  # noqa: E402
from tests import test_herald95_guards as guards  # noqa: E402


@contextlib.contextmanager
def swap(module, name: str, replacement):
    original = getattr(module, name)
    setattr(module, name, replacement)
    try:
        yield
    finally:
        setattr(module, name, original)


def n01_scale_also_multiplies_the_common_state():
    """The defect this stage was built to find, reinstated."""
    original = gen.scenario_loadings

    def coupled(scenario, scale, common_scale=1.0):
        return original(scenario, scale, common_scale * scale)
    return swap(gen, "scenario_loadings", coupled)


def n02_scale_does_not_reach_the_relational_term():
    original = gen.scenario_loadings

    def ignored(scenario, scale, common_scale=1.0):
        return original(scenario, 1.0, common_scale)
    return swap(gen, "scenario_loadings", ignored)


def n03_zero_scale_keeps_a_residual_relation():
    original = gen.scenario_loadings

    def leaky(scenario, scale, common_scale=1.0):
        return original(scenario, max(scale, 0.05), common_scale)
    return swap(gen, "scenario_loadings", leaky)


def n04_the_streams_are_not_decoupled():
    """Volumes, observations and masks share one generator again, so the pairing breaks."""
    original = gen.generate_nonlinear

    def coupled(config=gen.NonlinearConfig()):
        import dataclasses
        return original(dataclasses.replace(config, paired_streams=False))
    return swap(gen, "generate_nonlinear", coupled)


def n05_the_clip_is_not_reported():
    original = gen.generate_nonlinear

    def silent(config=gen.NonlinearConfig()):
        data = original(config)
        for block in (data["calibration"], data["truth"]["diagnostics"]):
            block["clipped_share"] = {name: 0.0 for name in block["clipped_share"]}
        return data
    return swap(gen, "generate_nonlinear", silent)


def n06_the_paired_effect_is_not_paired():
    """The effect is measured against a *different* seed, so it carries world noise."""
    def sloppy(scaled, baseline, signal):
        other = gen.generate_nonlinear(gen.NonlinearConfig(
            n_zones=guards.ZONES, seed=guards.SEED + 7, scenario=guards.SCENARIO,
            relational_scale=0.0, paired_streams=True))
        left = ladder.observed_growth(scaled, signal)
        right = ladder.observed_growth(other, signal)
        both = np.isfinite(left) & np.isfinite(right)
        difference = (left - right)[both]
        residual = right[both]
        relational = float(np.sqrt(np.mean(difference ** 2)))
        noise = float(np.sqrt(np.mean((residual - residual.mean()) ** 2)))
        return {"relational_rms": relational, "residual_rms": noise,
                "snr": float(relational / max(noise, 1e-12)), "n_cells": int(both.sum())}
    return swap(ladder, "paired_observable_effect", sloppy)


def n07_the_null_scenario_responds_to_the_scale():
    original = gen.scenario_loadings

    def active(scenario, scale, common_scale=1.0):
        base = original("N1_LINEAR" if scenario == "N0_NULL" else scenario,
                        scale, common_scale)
        return base
    return swap(gen, "scenario_loadings", active)


def n08_the_pairing_check_never_looks_at_the_masks():
    original = ladder.worlds_are_paired

    def partial(left, right):
        checks = original(left, right)
        checks.pop("same_masks", None)
        return checks
    return swap(ladder, "worlds_are_paired", partial)


def n09_the_ladder_seeds_collide_with_an_earlier_stage():
    return swap(ladder, "FINAL_SEEDS", (9801, 9802, 9803))


def n10_the_baseline_scale_is_dropped():
    return swap(ladder, "SCALES", (0.5, 1.0, 2.0, 4.0))


def n11_the_oracle_regressor_is_the_observation():
    """The oracle column becomes the published series, so the leak check must fire."""
    def leaky(dataset, signal):
        return np.nan_to_num(np.asarray(dataset["signals"][signal]["values"], float))
    return swap(ladder, "relational_regressor", leaky)


def n12_the_scale_changes_the_noise_groups():
    original = gen.scenario_loadings

    def entangled(scenario, scale, common_scale=1.0):
        base = original(scenario, scale, common_scale)
        if scale >= 2.0:
            for entry in base.values():
                entry["noise_group"] = "common"
        return base
    return swap(gen, "scenario_loadings", entangled)


MUTANTS = [value for key, value in sorted(globals().items())
           if key.startswith("n") and key[1:3].isdigit() and callable(value)]


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
            print(f"killed   {mutant.__name__:46s} by {', '.join(killed_by[:3])}"
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
