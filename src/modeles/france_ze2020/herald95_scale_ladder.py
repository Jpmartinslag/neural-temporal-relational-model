"""HERALD 95: measuring how much relational mechanism actually reaches the observations.

HERALD 94 found no composite informative and no relational recovery. Two readings survive
that result and they call for opposite responses:

    the relation is too small to be observed at all   -> the benchmark is the problem
    the relation is observable and the model missed it -> the model is the problem

This module separates them by varying one number, ``relational_scale``, and measuring what
that number does *to the observations* rather than what it was asked to do.

**Paired worlds.** Everything is measured against the same seed at ``scale = 0``. The random
stream has scenario-independent and scale-independent shapes drawn in a fixed order, so two
scales at one seed share the territory, the latent components, the macro path, the noise
draws, the volumes, the masks and the observation draws. The only difference is the
relational loading. Their difference in the observations is therefore the relational effect
itself, exactly, with nothing subtracted approximately.

**Why the observable side has to be measured and not assumed.** Three things stand between
the loading and the published number, and all three were found by inspection before this
stage ran:

1. ``relational_scale`` also multiplied ``gamma``, the loading on the *common* state, so
   varying it moved a non-relational component too. Fixed in the generator; at ``scale = 1``
   the two are indistinguishable, so nothing already reported changes.
2. The latent path is clipped to ``[-0.60, 0.60]``. At large scales the clip saturates -- 16 %
   of headcount cells at ``scale = 4`` -- and the world stops being "the same one with more
   mechanism". The clipped share is reported at every scale so that a scale can be read as
   what it is.
3. ``_observe`` normalises the integrated drift by its own standard deviation. A larger
   relational term therefore raises its *share* of the trajectory without raising the
   trajectory's amplitude. Measured at the observable level, a fourfold increase in the
   latent mechanism moved the standard deviation of observed log-growth by about ten per
   cent. This is the single most important quantity in the stage and it cannot be inferred
   from the loading.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.modeles.france_ze2020.herald94_temporal_features import (
    YEAR_LAG, to_transform_scale,
)

# Declared before execution. The scales the ladder walks, and the seeds it walks them on.
SCALES = (0.0, 0.5, 1.0, 2.0, 4.0)
LADDER_SCENARIOS = ("N0_NULL", "N2_NONLINEAR", "N3_REGIME", "N4_INTERACTION")
SMOKE_SEEDS = (9891, 9892)
FINAL_SEEDS = (9901, 9902, 9903)
assert not set(SMOKE_SEEDS) & set(FINAL_SEEDS)


def observed_growth(dataset: dict[str, Any], signal: str) -> np.ndarray:
    """Year-over-year log-growth as published, ``(T, N)``, NaN where unobserved."""
    block = dataset["signals"][signal]
    transformed = to_transform_scale(signal, np.asarray(block["values"], float),
                                     np.asarray(block["availability_mask"], bool),
                                     block["family"])
    out = np.full_like(transformed, np.nan)
    out[YEAR_LAG:] = transformed[YEAR_LAG:] - transformed[:-YEAR_LAG]
    return out


def paired_observable_effect(scaled: dict[str, Any], baseline: dict[str, Any],
                             signal: str) -> dict[str, float]:
    """The relational effect *in the observations*, from a matched pair.

    ``baseline`` is the same seed and scenario at ``relational_scale = 0``. Because the two
    worlds are identical in every other draw, ``growth_scaled - growth_baseline`` is the
    relational contribution exactly, and no model or approximation stands between the
    mechanism and this number.

    The residual is the baseline's own variation: measurement noise, the common state, the
    macro path and the calendar. Their ratio is what decides whether a method could see the
    relation at this scale even in principle.
    """
    left = observed_growth(scaled, signal)
    right = observed_growth(baseline, signal)
    both = np.isfinite(left) & np.isfinite(right)
    if not both.any():
        return {"relational_rms": float("nan"), "residual_rms": float("nan"),
                "snr": float("nan"), "n_cells": 0}
    difference = (left - right)[both]
    residual = right[both]
    relational = float(np.sqrt(np.mean(difference ** 2)))
    noise = float(np.sqrt(np.mean((residual - residual.mean()) ** 2)))
    return {
        "relational_rms": relational,
        "residual_rms": noise,
        "snr": float(relational / max(noise, 1e-12)),
        "n_cells": int(both.sum()),
    }


def ladder_diagnostics(datasets: dict[float, dict[str, Any]], signals: list[str],
                       baseline_scale: float = 0.0) -> dict[str, Any]:
    """Per-scale observable diagnostics for every signal, plus the saturation report."""
    baseline = datasets[baseline_scale]
    out: dict[str, Any] = {"baseline_scale": baseline_scale, "per_scale": {}}
    for scale, dataset in sorted(datasets.items()):
        entry = {
            "observable": {signal: paired_observable_effect(dataset, baseline, signal)
                           for signal in signals},
            "latent_relational_rms": dataset["calibration"]["relational_rms"],
            "latent_common_rms": dataset["calibration"]["common_state_rms"],
            "clipped_share": dataset["calibration"]["clipped_share"],
        }
        out["per_scale"][str(scale)] = entry
    return out


def worlds_are_paired(left: dict[str, Any], right: dict[str, Any]) -> dict[str, bool]:
    """Everything except the relational loading must be bit-identical between two scales."""
    return {
        "same_territory": bool(np.array_equal(left["truth"]["prior"],
                                              right["truth"]["prior"])),
        "same_graph": bool(np.array_equal(left["truth"]["propagation"],
                                          right["truth"]["propagation"])),
        "same_component_u": bool(np.array_equal(left["truth"]["components"]["u"],
                                                right["truth"]["components"]["u"])),
        "same_component_v": bool(np.array_equal(left["truth"]["components"]["v"],
                                                right["truth"]["components"]["v"])),
        "same_common_state": bool(np.allclose(
            left["truth"]["common"]["headcount"], right["truth"]["common"]["headcount"],
            rtol=0.0, atol=1e-15)),
        "same_masks": bool(all(
            np.array_equal(left["signals"][name]["availability_mask"],
                           right["signals"][name]["availability_mask"])
            for name in left["signals"])),
    }


def relational_regressor(dataset: dict[str, Any], signal: str) -> np.ndarray:
    """The true relational term of one signal, ``(T, N)``.

    Handed **only** to the oracle arm, which exists to measure the ceiling and is never a
    candidate model, never scored against the candidates as a peer, and never applied to
    France. Every candidate arm receives released observations and nothing else; a guard
    checks that the released view cannot reach this array.
    """
    return np.asarray(dataset["truth"]["relational"][signal], float)
