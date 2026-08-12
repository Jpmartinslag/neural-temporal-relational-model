"""HERALD 92: a multisignal synthetic France with a known relational truth.

HERALD 91 established that no single French signal carries direction-stable relational
information along observed commuting. That closes the individual question and leaves the
one this generator exists to test:

    can signals that are individually too weak to detect a relation carry it jointly?

The mechanism is stated before any scenario is written, because a generator that cannot
say *why* combining would help is not testing complementarity, it is assuming it. Here the
reason is concrete and falsifiable: every signal is a noisy measurement of the **same**
relational term, and their measurement noises are **independent**. Averaging S such signals
divides the noise by ``sqrt(S)`` while the relational part adds coherently, so the joint
signal-to-noise ratio is ``sqrt(S)`` times the individual one. Four signals buy a factor of
two. Nothing else in the construction helps a combination, which is what makes the
redundant and conflicting scenarios able to fail.

Six scenarios, each isolating one way a multisignal claim can be right or wrong:

``S0_NULL``            no relational effect anywhere; the false-positive floor.
``S1_SHARED``          one graph, every signal loads on it strongly enough to be found alone.
``S2_PARTIAL_SHARED``  some signals load on the shared graph, others on a private one.
``S3_COMPLEMENTARY``   the decisive case: each signal alone sits below detectability, the
                       combination sits above it.
``S4_REDUNDANT``       two signals share their noise as well as their signal, so the second
                       adds nothing; a method that claims a gain here is counting the same
                       evidence twice.
``S5_CONFLICTING``     signals load with opposite signs, so naive pooling cancels; a method
                       that reports consensus here is fabricating it.

Marginals, autocorrelation and dispersion are taken from the measured French panel, not
invented: quarterly headcount around 28,000 per zone with NB dispersion near 7,600; payroll
around 166 M EUR on a Gamma; annual employer establishments around 3,200 with dispersion
near 12,000; the unemployment rate around 8% on a logit scale; annual creations around 1,300
with dispersion near 315. Log-level autocorrelation sits between 0.91 and 0.99 in the real
panel and is reproduced per signal.

The relational truth is drawn before any observation exists, and no exported feature
reconstructs it: the observer sees counts and rates, never the latent growth, never the
relational term, never the adjacency.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

SCENARIOS = ("S0_NULL", "S1_SHARED", "S2_PARTIAL_SHARED", "S3_COMPLEMENTARY",
             "S4_REDUNDANT", "S5_CONFLICTING")

CALIBRATION_SEEDS = tuple(range(9301, 9321))
FINAL_SEEDS = (9401, 9402, 9403, 9404, 9405)
assert not set(CALIBRATION_SEEDS) & set(FINAL_SEEDS)

# Measured on the French panel by `herald91_corrected_tournament`. `loading` is the
# scenario-independent share of the shared relational term this signal carries; the
# scenarios rescale it but never invent a different shape.
SIGNAL_SPEC: dict[str, dict[str, Any]] = {
    "headcount": {
        "family": "negative_binomial", "freq": "Q", "median": 28075.0,
        "dispersion": 7591.0, "ar_log": 0.916, "noise": 0.030, "loading": 1.00, "gamma": 1.20,
        "release_lag_periods": 1, "window": (1998, 2026),
        "label": "private salaried headcount"},
    "payroll": {
        "family": "gamma", "freq": "Q", "median": 1.656e8,
        "dispersion": 40.0, "ar_log": 0.906, "noise": 0.035, "loading": 0.90, "gamma": 1.05,
        "release_lag_periods": 1, "window": (1998, 2026),
        "label": "gross payroll"},
    # For the two annual signals `ar_log` is the *quarterly* rate whose fourth power is
    # the annual autocorrelation measured in France (0.937 and 0.933): the simulation runs
    # on a quarterly grid and annual series are sampled at Q4.
    "establishments": {
        "family": "negative_binomial", "freq": "A", "median": 3221.0,
        "dispersion": 12257.0, "ar_log": 0.9840, "noise": 0.022, "loading": 0.85, "gamma": 0.95,
        "release_lag_periods": 1, "window": (1998, 2024),
        "label": "employer establishments"},
    "unemployment": {
        "family": "logit_gaussian", "freq": "Q", "median": 8.0,
        "dispersion": None, "ar_log": 0.952, "noise": 0.040, "loading": -0.70, "gamma": -0.85,
        "release_lag_periods": 1, "window": (2003, 2026),
        "label": "localised unemployment rate"},
    "creations": {
        "family": "negative_binomial", "freq": "A", "median": 1322.0,
        "dispersion": 315.0, "ar_log": 0.9829, "noise": 0.055, "loading": 0.60, "gamma": 0.75,
        "release_lag_periods": 1, "window": (2012, 2025),
        "label": "establishment creations"},
}

# Nuisance only. A method that reads these as territorial events is wrong by construction.
BREAKS = {"headcount": (2021, 2023), "payroll": (2021, 2023),
          "establishments": (2021, 2023), "unemployment": (2018,), "creations": ()}
COVID_YEARS = (2020, 2021)

# Log-level spread, split between permanent zone size and accumulated drift. Chosen so the
# generated coefficient of variation lands near the 3.1 measured on French headcount:
# for a lognormal, CV = sqrt(exp(sigma^2) - 1), so sigma ~ 1.54 in total.
# Solved rather than tuned: for a lognormal, CV = sqrt(exp(sigma^2) - 1), so a French
# headcount CV of 3.10 needs sigma ~ 1.54 in total. The drift contributes 0.55, leaving
# sigma ~ 1.43 for permanent zone size.
STATE_PERSISTENCE = 0.80
LEVEL_VOLUME_SD = 1.00
LEVEL_DRIFT_SD = 0.55
VOLUME_LOG_SD = 1.43


@dataclasses.dataclass(frozen=True)
class MultisignalConfig:
    n_zones: int = 280
    first_year: int = 1998
    last_year: int = 2025
    seed: int = 9401
    scenario: str = "S1_SHARED"
    commuting_k: int = 40
    propagation_k: int = 28
    relational_scale: float = 1.0
    low_information_share: float = 0.25
    missing_block_rate: float = 0.02

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}")
        if self.n_zones < 20:
            raise ValueError("at least twenty zones are needed for a usable placebo")


# ── Territory and truth ──────────────────────────────────────────────────────

def _row_normalise(matrix: np.ndarray) -> np.ndarray:
    out = np.maximum(np.asarray(matrix, float), 0.0).copy()
    np.fill_diagonal(out, 0.0)
    total = out.sum(1, keepdims=True)
    return np.divide(out, total, out=np.zeros_like(out), where=total > 0)


def _commuting_prior(n: int, k: int, rng: np.random.Generator) -> np.ndarray:
    """A distance-decayed, asymmetric flow matrix in the shape of real commuting."""
    coords = rng.uniform(size=(n, 2))
    distance = np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))
    np.fill_diagonal(distance, np.inf)
    k = min(max(1, k), n - 1)
    index = np.argpartition(distance, k - 1, axis=1)[:, :k]
    matrix = np.zeros((n, n))
    rows = np.arange(n)[:, None]
    matrix[rows, index] = (np.exp(-4.0 * distance[rows, index])
                           * rng.lognormal(0.0, 0.22, size=index.shape))
    return _row_normalise(matrix)


def _topk(matrix: np.ndarray, k: int) -> np.ndarray:
    n = len(matrix)
    k = min(max(1, k), n - 1)
    out = np.zeros_like(matrix)
    index = np.argpartition(-matrix, k - 1, axis=1)[:, :k]
    rows = np.arange(n)[:, None]
    out[rows, index] = matrix[rows, index]
    return _row_normalise(out)


def _dynamic_truth(prior: np.ndarray, n_periods: int, years: np.ndarray,
                   features: np.ndarray, propagation_k: int,
                   rng: np.random.Generator) -> dict[str, np.ndarray]:
    """A shared, feature-conditioned reweighting of the observed commuting support.

    No edge is created outside commuting; the truth only moves weight inside it, and the
    top-k support is what births and deaths refer to. The regime shifts at the documented
    French breakpoints so that a method cannot separate them by calendar alone.
    """
    source = features[:, None, :]
    target = features[None, :, :]
    shared = (0.65 * source[..., 0] * target[..., 1]
              - 0.55 * np.abs(source[..., 2] - target[..., 2])
              + 0.35 * source[..., 3] * target[..., 3])
    interaction = np.outer(features[:, 1], features[:, 2])
    dense = np.empty((n_periods, len(prior), len(prior)))
    for t in range(n_periods):
        year = int(years[t])
        regime = (-0.30 if year < 2012 else 0.00 if year < 2017 else
                  0.40 if year < 2020 else -0.80 if year == 2020 else
                  0.70 if year == 2021 else 0.20)
        dense[t] = _row_normalise(
            prior * np.exp(0.25 * np.tanh(shared + regime * interaction)))
    propagation = np.stack([_topk(matrix, propagation_k) for matrix in dense])
    return {"dense": dense, "propagation": propagation}


def _private_graph(prior: np.ndarray, n_periods: int, propagation_k: int,
                   rng: np.random.Generator) -> np.ndarray:
    """A second graph on the same support, for the partially-shared scenario."""
    weights = rng.lognormal(0.0, 0.5, size=prior.shape)
    dense = _row_normalise(prior * weights)
    return np.stack([_topk(dense, propagation_k) for _ in range(n_periods)])


# ── Scenario wiring ──────────────────────────────────────────────────────────

def scenario_loadings(scenario: str, scale: float) -> dict[str, dict[str, Any]]:
    """Per-signal loadings on the common state (``gamma``) and on its propagation (``lambda``).

    ``noise_group`` decides whether pooling can help: signals sharing a group share their
    measurement noise, so averaging them cannot reduce it. That is the only mechanism by
    which the redundant scenario denies complementarity, and it is deliberately the same
    knob the complementary scenario uses in the opposite direction.
    """
    base = {name: {"loading": spec["loading"] * scale,
                   "gamma": spec["gamma"] * scale,
                   "graph": "shared", "noise_group": name}
            for name, spec in SIGNAL_SPEC.items()}
    if scenario == "S0_NULL":
        for entry in base.values():
            entry["loading"] = 0.0          # the common state stays; only propagation goes
    elif scenario == "S1_SHARED":
        pass
    elif scenario == "S2_PARTIAL_SHARED":
        for name in ("unemployment", "creations"):
            base[name]["graph"] = "private"
    elif scenario == "S3_COMPLEMENTARY":
        # Partial measurement, not a quieter joint arm: each signal sees a weak share of
        # the same state, so one signal estimates it badly and five estimate it well.
        for entry in base.values():
            entry["gamma"] *= 0.35
            entry["loading"] *= 0.35
    elif scenario == "S4_REDUNDANT":
        # Payroll becomes a second view of headcount, noise included: pooling the two
        # cannot average anything away, so the second channel adds nothing.
        base["payroll"]["gamma"] = base["headcount"]["gamma"]
        base["payroll"]["loading"] = base["headcount"]["loading"]
        base["payroll"]["noise_group"] = "headcount"
    elif scenario == "S5_CONFLICTING":
        # Signs flip on both loadings together, so each signal still carries the full
        # mechanism and only naive unsigned pooling cancels. Flipping one loading alone
        # would have destroyed the mechanism instead of opposing it.
        for name in ("establishments", "creations"):
            base[name]["gamma"] *= -1.0
            base[name]["loading"] *= -1.0
    return base


# ── Latent process ───────────────────────────────────────────────────────────

def _simulate(config: MultisignalConfig, graphs: dict[str, np.ndarray],
              loadings: dict[str, dict[str, Any]], years: np.ndarray,
              rng: np.random.Generator) -> dict[str, Any]:
    """The declared formulation: one latent economic state, measured by every signal.

        z[t+1]        = rho * z[t] + shock[t+1]
        eta_s[t+1]    = ar_s * eta_s[t] + macro_s[t+1]
                        + gamma_s * z[t]
                        + lambda_s * (A[t] @ centred(z[t]))
                        + noise_s[t+1]
        x_s[t+1]      = observation_model_s(eta_s[t+1])

    ``gamma_s`` is what makes complementarity possible at all. An earlier version drove the
    relational term from an exogenous state that no signal measured, so pooling signals
    estimated nothing and the combination could never beat its parts: the task was
    impossible by construction rather than hard. With a contemporaneous loading, pooling S
    signals estimates ``z`` with noise divided by ``sqrt(S)``, and the neighbour term built
    on that estimate is correspondingly sharper.

    Complementarity therefore comes from **partial measurement**, not from giving the joint
    arm quieter data: every arm sees exactly the same observations.
    """
    n_periods, n = len(years), config.n_zones
    names = list(SIGNAL_SPEC)
    groups = sorted({entry["noise_group"] for entry in loadings.values()})
    noise = {group: rng.normal(0.0, 1.0, size=(n_periods, n)) for group in groups}
    macro = {name: rng.normal(0.0, 0.010, size=n_periods) for name in names}

    # Latent territorial state. Never exported to the model, never a regressor.
    state = np.zeros((n_periods, n))
    shock = rng.normal(0.0, 1.0, size=(n_periods, n))
    state[0] = shock[0]
    for t in range(n_periods - 1):
        state[t + 1] = STATE_PERSISTENCE * state[t] + shock[t + 1]
    state = state / max(float(np.std(state)), 1e-12)

    # Relational propagation of the state, one column per graph.
    propagated = np.zeros((n_periods, n, 2))
    for t in range(n_periods - 1):
        centred = state[t] - state[t].mean()
        propagated[t + 1, :, 0] = graphs["shared"][t] @ centred
        propagated[t + 1, :, 1] = graphs["private"][t] @ centred
    scale = max(float(np.sqrt(np.mean(propagated[1:, :, 0] ** 2))), 1e-12)

    latent = {name: np.zeros((n_periods, n)) for name in names}
    relational = {name: np.zeros((n_periods, n)) for name in names}
    common = {name: np.zeros((n_periods, n)) for name in names}
    for name in names:
        latent[name][0] = noise[loadings[name]["noise_group"]][0] * SIGNAL_SPEC[name]["noise"]

    for t in range(n_periods - 1):
        for name in names:
            spec = SIGNAL_SPEC[name]
            entry = loadings[name]
            column = 0 if entry["graph"] == "shared" else 1
            shared_term = entry["gamma"] * spec["noise"] * state[t]
            neighbour_term = (entry["loading"] * spec["noise"]
                              * propagated[t + 1, :, column] / scale)
            common[name][t + 1] = shared_term
            relational[name][t + 1] = neighbour_term
            latent[name][t + 1] = np.clip(
                spec["ar_log"] * latent[name][t] + macro[name][t + 1]
                + shared_term + neighbour_term
                + spec["noise"] * noise[entry["noise_group"]][t + 1], -0.60, 0.60)
    return {"latent": latent, "relational": relational, "common": common, "state": state}


# ── Observation models ───────────────────────────────────────────────────────

def _observe(name: str, path: np.ndarray, volume: np.ndarray, years: np.ndarray,
             quarters: np.ndarray, config: MultisignalConfig,
             rng: np.random.Generator) -> np.ndarray:
    """Turn a latent path into the measurement a French statistician would publish."""
    spec = SIGNAL_SPEC[name]
    # The latent path is integrated to make a level, but the raw cumulative sum of an
    # AR(0.92) process over 112 quarters behaves like a random walk and spread the
    # simulated zones far wider than France: a coefficient of variation of 9.0 against a
    # measured 3.1. The drift is therefore normalised to unit scale and multiplied by a
    # declared log-level spread, so the *shape* of the trajectory is kept while its
    # amplitude matches the panel it is meant to imitate.
    drift = np.cumsum(path, axis=0)
    drift = drift / max(float(np.std(drift)), 1e-12)
    level = (np.log(spec["median"])
             + LEVEL_VOLUME_SD * np.log(np.maximum(volume, 1e-6))[None, :]
             + LEVEL_DRIFT_SD * drift)
    if spec["freq"] == "Q":
        level = level + 0.03 * np.sin(2 * np.pi * (quarters[:, None] - 1) / 4.0)
    for year in BREAKS[name]:
        level = level + 0.02 * (years[:, None] >= year)
    for year in COVID_YEARS:
        level = level + (-0.05 if year == 2020 else 0.04) * (years[:, None] == year)

    if spec["family"] == "negative_binomial":
        mean = np.exp(np.clip(level, 0.0, 20.0))
        shape = float(spec["dispersion"])
        return rng.poisson(rng.gamma(shape=shape, scale=mean / shape)).astype(float)
    if spec["family"] == "gamma":
        mean = np.exp(np.clip(level, 0.0, 30.0))
        shape = float(spec["dispersion"])
        return rng.gamma(shape=shape, scale=mean / shape)
    # A rate is bounded and mean-reverting, not a random walk. Accumulating the latent
    # path here sent the median to 25% against a French 8%; the level responds to the
    # current state instead.
    centre = np.log(spec["median"] / (100.0 - spec["median"]))
    # French localised unemployment is tight across zones: a coefficient of variation of
    # 0.27, not 0.7. Both the size effect and the latent gain are damped accordingly.
    zone_offset = 0.030 * np.log(np.maximum(volume, 1e-6))[None, :]
    logit = centre - zone_offset + 0.9 * path
    return np.clip(100.0 / (1.0 + np.exp(-logit))
                   + rng.normal(0.0, 0.20, size=logit.shape), 1.0, 30.0)


def generate_multisignal(config: MultisignalConfig = MultisignalConfig()) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    quarters_per_year = 4
    years_axis = np.repeat(np.arange(config.first_year, config.last_year + 1),
                           quarters_per_year)
    quarters_axis = np.tile(np.arange(1, quarters_per_year + 1),
                            config.last_year - config.first_year + 1)
    n_periods, n = len(years_axis), config.n_zones

    prior = _commuting_prior(n, config.commuting_k, rng)
    features = rng.normal(size=(n, 4))
    truth = _dynamic_truth(prior, n_periods, years_axis, features,
                           config.propagation_k, rng)
    graphs = {"shared": truth["propagation"],
              "private": _private_graph(prior, n_periods, config.propagation_k, rng)}
    loadings = scenario_loadings(config.scenario, config.relational_scale)
    simulated = _simulate(config, graphs, loadings, years_axis, rng)

    # Volume heterogeneity in the French shape, with a declared low-information stratum.
    # The French panel spreads zone volumes widely: a coefficient of variation near 3 on
    # counts. A narrower draw would make every zone look alike and quietly remove the
    # low-information stratum the design exists to test.
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
        block = rng.uniform(size=values.shape) < config.missing_block_rate
        mask &= ~block
        observed = np.where(mask, values, np.nan)
        release = np.where(in_window, years_axis + spec["release_lag_periods"], -1)
        signals[name] = {
            "values": observed, "availability_mask": mask.astype(np.int8),
            "release_year": release, "family": spec["family"], "freq": spec["freq"],
            "label": spec["label"], "window": spec["window"],
        }

    diagnostics = {
        "scenario": config.scenario,
        "relational_scale": config.relational_scale,
        "loadings": {name: {"loading": entry["loading"], "gamma": entry["gamma"],
                            "graph": entry["graph"], "noise_group": entry["noise_group"]}
                     for name, entry in loadings.items()},
        "relational_rms": {name: float(np.sqrt(np.mean(simulated["relational"][name][1:] ** 2)))
                           for name in SIGNAL_SPEC},
        "common_state_rms": {name: float(np.sqrt(np.mean(simulated["common"][name][1:] ** 2)))
                             for name in SIGNAL_SPEC},
        "noise_rms": {name: float(SIGNAL_SPEC[name]["noise"]) for name in SIGNAL_SPEC},
        "latent_rms": {name: float(np.sqrt(np.mean(np.diff(simulated["latent"][name], axis=0) ** 2)))
                       for name in SIGNAL_SPEC},
        "low_information_zones": int(low_information.sum()),
    }
    # Share against the *measurement noise* of the same signal: the quantity that decides
    # whether one signal alone can see the relation.
    diagnostics["relational_share"] = {
        name: diagnostics["relational_rms"][name] / max(diagnostics["noise_rms"][name], 1e-12)
        for name in SIGNAL_SPEC}
    diagnostics["common_share"] = {
        name: diagnostics["common_state_rms"][name] / max(diagnostics["noise_rms"][name], 1e-12)
        for name in SIGNAL_SPEC}

    return {
        "signals": signals,
        "metadata": {
            "years": years_axis, "quarters": quarters_axis,
            "zones": tuple(f"Z{i:04d}" for i in range(n)),
            "scenario": config.scenario,
            "low_information": low_information,
            "breaks": BREAKS, "covid_years": COVID_YEARS,
        },
        "truth": {
            "prior": prior, "propagation": truth["propagation"],
            "dense": truth["dense"], "private_propagation": graphs["private"],
            "latent": simulated["latent"], "relational": simulated["relational"],
            "state": simulated["state"], "common": simulated["common"],
            "features": features, "diagnostics": diagnostics,
        },
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
        values = np.where(final, block["values"], np.nan)
        result["signals"][name] = {"values": values,
                                   "availability_mask": final.astype(np.int8),
                                   "family": block["family"], "freq": block["freq"]}
    return result
