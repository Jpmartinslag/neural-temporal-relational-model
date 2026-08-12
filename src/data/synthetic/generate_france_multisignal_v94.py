"""HERALD 94: the same synthetic France, with links that are not linear in the latent state.

`generate_france_multisignal_v92` propagates ``lambda_s * (A_t @ centred(z_t))``. That is
linear in ``z``, so a non-linear territorial relation does not exist anywhere in that
benchmark: no method could have found one, and a negative result there would have been a
property of the generator rather than of the method. This module reuses v92's territory,
marginals, autocorrelations, masks, breaks, COVID calendar, low-information stratum and
observation models **unchanged**, and replaces exactly one thing -- the link.

    N0_NULL          no relational effect anywhere; the false-positive floor.
    N1_LINEAR        A_t @ centred(z_t). v92's mechanism, for continuity.
    N2_NONLINEAR     A_t @ centred(relu(centred(z_t))). Only expansions propagate.
    N3_REGIME        rho(own regime) * (A_t @ centred(z_t)). The receiving zone's own state
                     gates how much of its neighbours' movement reaches it.
    N4_INTERACTION   A_t @ centred(u_t * v_t), where u and v are two independent latent
                     components measured by *disjoint* subsets of signals.
    N5_REDUNDANT     N1's link with one measurement noise shared by every signal: the
                     duplicated channel, against which a claimed pooling gain is checked.

``N2`` is the cleanest refutation target for a linear model. ``relu`` re-centred is not a
linear function of ``z`` and no linear model in ``z`` can represent it, however it is
regularised.

``N4`` is the strongest form of the composite hypothesis and the only scenario in which a
non-linear combination of *distinct signals* is the unique route to the mechanism. Headcount
and payroll measure ``u``; employer establishments and creations measure ``v``; unemployment
measures neither. The propagated quantity is the product, so neither subset alone identifies
it, and a model that can only average its signals cannot recover it no matter how many it
averages.

Every random array is drawn with a scenario-independent shape and in a fixed order. Two
scenarios at the same seed therefore inhabit the same world -- same territory, same latent
path, same macro path, same masks -- and differ only in the declared mechanism, which is what
makes a paired seed-by-seed comparison a comparison rather than two separate experiments.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from src.data.synthetic.generate_france_multisignal_v92 import (
    BREAKS, COVID_YEARS, LEVEL_DRIFT_SD, LEVEL_VOLUME_SD, SIGNAL_SPEC, STATE_PERSISTENCE,
    VOLUME_LOG_SD, _commuting_prior, _dynamic_truth, _observe, _private_graph,
    _row_normalise, _topk,
)

SCENARIOS = ("N0_NULL", "N1_LINEAR", "N2_NONLINEAR", "N3_REGIME", "N4_INTERACTION",
             "N5_REDUNDANT")

LINK_OF = {"N0_NULL": "linear", "N1_LINEAR": "linear", "N2_NONLINEAR": "rectified",
           "N3_REGIME": "regime_gated", "N4_INTERACTION": "product",
           "N5_REDUNDANT": "linear"}

# Disjoint by design. `N4`'s product cannot be identified from either subset alone, and the
# signal that measures neither component is the control that must not appear to help.
COMPONENT_OF = {"headcount": "u", "payroll": "u",
                "establishments": "v", "creations": "v",
                "unemployment": "u"}

# Seeds for this stage, disjoint from every seed the earlier stages used.
SMOKE_SEEDS = (9601, 9602)
FINAL_SEEDS = (9701, 9702, 9703, 9704, 9705)
assert not set(SMOKE_SEEDS) & set(FINAL_SEEDS)

# The regime gate of `N3`. A zone whose own latent state is rising absorbs its neighbours'
# movement; a zone that is contracting largely does not. Declared here, not tuned: the two
# values average to 1.0 weighted by the (symmetric) sign distribution of a centred state, so
# the scenario's mean relational amplitude matches `N1`'s and the contrast is about *where*
# the transfer happens rather than how much of it there is.
REGIME_GATE_RISING = 1.7
REGIME_GATE_FALLING = 0.3


@dataclasses.dataclass(frozen=True)
class NonlinearConfig:
    n_zones: int = 280
    first_year: int = 1998
    last_year: int = 2025
    seed: int = 9701
    scenario: str = "N1_LINEAR"
    commuting_k: int = 40
    propagation_k: int = 28
    relational_scale: float = 1.0
    low_information_share: float = 0.25
    missing_block_rate: float = 0.02

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}, got {self.scenario!r}")
        if self.n_zones < 20:
            raise ValueError("at least twenty zones are needed for a usable placebo")


def scenario_loadings(scenario: str, scale: float) -> dict[str, dict[str, Any]]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; known: {sorted(SCENARIOS)}")
    base = {name: {"loading": spec["loading"] * scale, "gamma": spec["gamma"] * scale,
                   "noise_group": name, "component": COMPONENT_OF[name]}
            for name, spec in SIGNAL_SPEC.items()}
    # Outside `N4` every signal measures the same component, so the disjoint split is a
    # property of that scenario alone and not a hidden difference between the others. This
    # runs *before* the per-scenario branches and outside the chain: as an `elif` it never
    # fired for `N0_NULL` or `N5_REDUNDANT`, and those two silently kept the split. Each
    # would then have differed from `N1` in two ways at once -- its own declared mechanism
    # and the component assignment -- which is precisely the confound a matched design
    # exists to exclude.
    if scenario != "N4_INTERACTION":
        for entry in base.values():
            entry["component"] = "u"
    if scenario == "N0_NULL":
        # The propagation matrix still exists and the common state still moves; only the
        # relational loading goes. Nothing observable then distinguishes one candidate edge
        # from another, which is the point of the control.
        for entry in base.values():
            entry["loading"] = 0.0
    elif scenario == "N5_REDUNDANT":
        for entry in base.values():
            entry["noise_group"] = "common"
    return base


def _centre(array: np.ndarray) -> np.ndarray:
    return array - array.mean()


def _propagate(link: str, matrix: np.ndarray, state_u: np.ndarray,
               state_v: np.ndarray) -> np.ndarray:
    """The one quantity that separates the scenarios."""
    if link == "linear":
        return matrix @ _centre(state_u)
    if link == "rectified":
        # Re-centred so the scenario changes the *shape* of the transfer and not its mean:
        # an uncentred relu would also add a positive constant to every zone, and a method
        # could then appear to detect the mechanism by detecting a level shift.
        return matrix @ _centre(np.maximum(_centre(state_u), 0.0))
    if link == "regime_gated":
        return matrix @ _centre(state_u)          # the gate is applied per receiving zone
    if link == "product":
        return matrix @ _centre(_centre(state_u) * _centre(state_v))
    raise ValueError(f"unknown link {link!r}")


def _simulate(config: NonlinearConfig, propagation: np.ndarray,
              loadings: dict[str, dict[str, Any]], years: np.ndarray,
              rng: np.random.Generator) -> dict[str, Any]:
    """Two latent components, one graph, and a link chosen by the scenario.

        u[t+1]      = rho u[t] + shock_u[t+1]
        v[t+1]      = rho v[t] + shock_v[t+1]
        p[t+1]      = link(A[t], u[t], v[t])
        eta_s[t+1]  = ar_s eta_s[t] + macro_s[t+1]
                      + gamma_s * component_s[t]
                      + lambda_s * gate_s[t] * p[t+1] / scale
                      + noise_s[t+1]

    ``gamma_s`` gives each signal a contemporaneous view of the component it measures, which
    is what makes pooling able to help at all: without it the relational term would be driven
    by something no signal observes and the joint arm would estimate nothing.
    """
    n_periods, n = len(years), config.n_zones
    names = list(SIGNAL_SPEC)
    link = LINK_OF[config.scenario]

    macro = {name: rng.normal(0.0, 0.010, size=n_periods) for name in names}
    shock_u = rng.normal(0.0, 1.0, size=(n_periods, n))
    shock_v = rng.normal(0.0, 1.0, size=(n_periods, n))
    per_signal_noise = rng.normal(0.0, 1.0, size=(len(names), n_periods, n))
    first_of_group: dict[str, int] = {}
    for index, name in enumerate(names):
        first_of_group.setdefault(loadings[name]["noise_group"], index)
    noise = {group: per_signal_noise[index] for group, index in first_of_group.items()}

    components: dict[str, np.ndarray] = {}
    for key, shock in (("u", shock_u), ("v", shock_v)):
        path = np.zeros((n_periods, n))
        path[0] = shock[0]
        for t in range(n_periods - 1):
            path[t + 1] = STATE_PERSISTENCE * path[t] + shock[t + 1]
        components[key] = path / max(float(np.std(path)), 1e-12)

    propagated = np.zeros((n_periods, n))
    for t in range(n_periods - 1):
        propagated[t + 1] = _propagate(link, propagation[t], components["u"][t],
                                       components["v"][t])
    scale = max(float(np.sqrt(np.mean(propagated[1:] ** 2))), 1e-12)

    # `N3`'s gate: the receiving zone's own state decides how much reaches it. Derived from
    # `u`, which every signal in that scenario measures, so the mechanism is discoverable in
    # principle from observables and is not a hidden variable.
    if link == "regime_gated":
        rising = components["u"][:-1] >= 0.0
        gate = np.where(rising, REGIME_GATE_RISING, REGIME_GATE_FALLING)
        gate = np.concatenate([np.ones((1, n)), gate])
        # Normalised to unit root-mean-square, so `N3` carries exactly `N1`'s relational
        # amplitude and differs from it only in *where* the transfer lands. Without this the
        # gate's own RMS, sqrt((1.7^2 + 0.3^2)/2) = 1.22, would raise the relational share
        # from 1.00 to 1.20 and the scenario would be a stronger world as well as a
        # differently shaped one -- the exact defect that made v92's S3/S4 gate unreadable.
        gate = gate / max(float(np.sqrt(np.mean(gate[1:] ** 2))), 1e-12)
    else:
        gate = np.ones((n_periods, n))

    latent = {name: np.zeros((n_periods, n)) for name in names}
    relational = {name: np.zeros((n_periods, n)) for name in names}
    common = {name: np.zeros((n_periods, n)) for name in names}
    for name in names:
        latent[name][0] = noise[loadings[name]["noise_group"]][0] * SIGNAL_SPEC[name]["noise"]

    for t in range(n_periods - 1):
        for name in names:
            spec = SIGNAL_SPEC[name]
            entry = loadings[name]
            measured = components[entry["component"]][t]
            shared_term = entry["gamma"] * spec["noise"] * measured
            neighbour_term = (entry["loading"] * spec["noise"] * gate[t + 1]
                              * propagated[t + 1] / scale)
            common[name][t + 1] = shared_term
            relational[name][t + 1] = neighbour_term
            latent[name][t + 1] = np.clip(
                spec["ar_log"] * latent[name][t] + macro[name][t + 1]
                + shared_term + neighbour_term
                + spec["noise"] * noise[entry["noise_group"]][t + 1], -0.60, 0.60)
    return {"latent": latent, "relational": relational, "common": common,
            "components": components, "gate": gate, "propagated": propagated,
            "link": link}


def generate_nonlinear(config: NonlinearConfig = NonlinearConfig()) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    quarters_per_year = 4
    years_axis = np.repeat(np.arange(config.first_year, config.last_year + 1),
                           quarters_per_year)
    quarters_axis = np.tile(np.arange(1, quarters_per_year + 1),
                            config.last_year - config.first_year + 1)
    n_periods, n = len(years_axis), config.n_zones

    prior = _commuting_prior(n, config.commuting_k, rng)
    features = rng.normal(size=(n, 4))
    truth = _dynamic_truth(prior, n_periods, years_axis, features, config.propagation_k, rng)
    # Drawn even where it is unused, so that the random stream advances identically in every
    # scenario at a given seed.
    private = _private_graph(prior, n_periods, config.propagation_k, rng)
    loadings = scenario_loadings(config.scenario, config.relational_scale)
    simulated = _simulate(config, truth["propagation"], loadings, years_axis, rng)

    volume = rng.lognormal(0.0, VOLUME_LOG_SD, size=n)
    volume = volume / np.median(volume)
    low_cut = np.quantile(volume, config.low_information_share)
    low_information = volume <= low_cut

    signals: dict[str, Any] = {}
    for name, spec in SIGNAL_SPEC.items():
        values = _observe(name, simulated["latent"][name], volume, years_axis,
                          quarters_axis, config, rng)
        start, end = spec["window"]
        in_window = (years_axis >= start) & (years_axis <= end)
        if spec["freq"] == "A":
            in_window = in_window & (quarters_axis == 4)
        mask = np.broadcast_to(in_window[:, None], values.shape).copy()
        mask &= ~(rng.uniform(size=values.shape) < config.missing_block_rate)
        signals[name] = {
            "values": np.where(mask, values, np.nan),
            "availability_mask": mask.astype(np.int8),
            "release_year": np.where(in_window, years_axis + spec["release_lag_periods"], -1),
            "family": spec["family"], "freq": spec["freq"], "label": spec["label"],
            "window": spec["window"],
        }

    diagnostics = {
        "scenario": config.scenario, "link": simulated["link"],
        "loadings": {name: dict(entry) for name, entry in loadings.items()},
        "relational_rms": {name: float(np.sqrt(np.mean(simulated["relational"][name][1:] ** 2)))
                           for name in SIGNAL_SPEC},
        "common_state_rms": {name: float(np.sqrt(np.mean(simulated["common"][name][1:] ** 2)))
                             for name in SIGNAL_SPEC},
        "noise_rms": {name: float(SIGNAL_SPEC[name]["noise"]) for name in SIGNAL_SPEC},
        "low_information_zones": int(low_information.sum()),
    }
    diagnostics["relational_share"] = {
        name: diagnostics["relational_rms"][name] / max(diagnostics["noise_rms"][name], 1e-12)
        for name in SIGNAL_SPEC}
    diagnostics["common_share"] = {
        name: diagnostics["common_state_rms"][name] / max(diagnostics["noise_rms"][name], 1e-12)
        for name in SIGNAL_SPEC}

    return {
        "signals": signals,
        "metadata": {"years": years_axis, "quarters": quarters_axis,
                     "zones": tuple(f"Z{i:04d}" for i in range(n)),
                     "scenario": config.scenario, "low_information": low_information,
                     "breaks": BREAKS, "covid_years": COVID_YEARS},
        "truth": {"prior": prior, "propagation": truth["propagation"], "dense": truth["dense"],
                  "private_propagation": private, "latent": simulated["latent"],
                  "relational": simulated["relational"], "common": simulated["common"],
                  "components": simulated["components"], "gate": simulated["gate"],
                  "features": features, "diagnostics": diagnostics},
        "config": dataclasses.asdict(config),
        "calibration": diagnostics,
    }


def model_inputs(dataset: dict[str, Any], decision_period: int) -> dict[str, Any]:
    """Released observations only. Truth and calibration never travel to the model."""
    years = np.asarray(dataset["metadata"]["years"])
    result: dict[str, Any] = {"signals": {}, "metadata": {
        key: value for key, value in dataset["metadata"].items()
        if key not in ("low_information",)}}
    for name, block in dataset["signals"].items():
        released = (block["release_year"] >= 0) & (
            block["release_year"] <= years[decision_period])
        temporal = np.arange(len(years))[:, None] <= decision_period
        final = block["availability_mask"].astype(bool) & released[:, None] & temporal
        result["signals"][name] = {
            "values": np.where(final, block["values"], np.nan),
            "availability_mask": final.astype(np.int8),
            "family": block["family"], "freq": block["freq"]}
    return result


__all__ = ["SCENARIOS", "LINK_OF", "COMPONENT_OF", "SMOKE_SEEDS", "FINAL_SEEDS",
           "NonlinearConfig", "generate_nonlinear", "model_inputs", "scenario_loadings"]
