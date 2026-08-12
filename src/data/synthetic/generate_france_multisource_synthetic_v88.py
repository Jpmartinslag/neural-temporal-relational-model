"""HERALD 88: the HERALD 86 benchmark with a calibrated relational component.

HERALD 86 fixed ``relation_strength = 0.22`` by hand. Because ``A`` is row-normalised,
that coefficient multiplies an *average* over 28 neighbours rather than a growth rate,
and the injected term ended up at 0.12% of the latent growth variance. A benchmark whose
signal is that small cannot separate a model that fails from a model that has nothing to
find.

Here the coefficient is derived instead. A deterministic probe pass simulates the
trajectory with no relational effect at all, measures the two root-mean-squares that
define the ratio, and solves for the coefficient that puts

    RMS(relational increment) / RMS(non-relational increment) = requested_ratio

The probe reads only generator internals, before any Negative-Binomial draw. It never
reads a model output, an F1, an evaluation MSE or a recovered edge.

Everything else is inherited unchanged from HERALD 86: the same row normalisation, the
same noise, the same source semantics and windows, and a null scenario whose relational
contribution is exactly zero.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from src.data.synthetic.generate_france_multisource_synthetic import (
    A10,
    A17,
    SCENARIOS,
    YEARS,
    _commuting_prior,
    _dynamic_truth,
    _negative_binomial,
    _source_block,
    model_inputs as _model_inputs_v86,
)

REQUESTED_EFFECTIVE_RATIO = 0.25
LATENT_RATIO_TOLERANCE = 0.02


@dataclasses.dataclass(frozen=True)
class FranceSyntheticConfigV88:
    n_zones: int = 280
    years: tuple[int, ...] = YEARS
    sectors: tuple[str, ...] = A10
    seed: int = 8601
    scenario: str = "dynamic"
    commuting_k: int = 40
    propagation_k: int = 28
    count_dispersion: float = 18.0
    missing_block_rate: float = 0.025
    requested_effective_ratio: float = REQUESTED_EFFECTIVE_RATIO

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}")
        if len(self.years) < 8 or tuple(sorted(self.years)) != self.years:
            raise ValueError("years must be sorted and contain at least eight steps")
        if self.n_zones < 6 or len(self.sectors) < 3:
            raise ValueError("benchmark needs at least six zones and three sectors")
        if not 0.0 <= self.requested_effective_ratio <= 2.0:
            raise ValueError("requested_effective_ratio must lie in [0, 2]")


def _rms(a: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    return float(np.sqrt(np.mean(a * a))) if a.size else 0.0


def _draw_dynamics(config: FranceSyntheticConfigV88, rng: np.random.Generator):
    """Draw every stochastic term of the latent path once, so the probe is exact.

    The probe pass and the calibrated pass must differ only in the coefficient. If they
    drew their own noise the measured ratio would carry sampling error and the guard
    band would be meaningless.
    """
    t_len, n, s_len = len(config.years), config.n_zones, len(config.sectors)
    noise_sd = 0.10 if config.scenario != "dynamic_sparse" else 0.18
    return {
        "macro": rng.normal(0.0, 0.045, size=(t_len, s_len)),
        "ar": rng.uniform(-0.38, 0.28, size=s_len),
        "innovation": rng.normal(0.0, noise_sd, size=(t_len, n, s_len)),
        "initial": rng.normal(0.0, noise_sd, size=(n, s_len)),
        "sector_loading": rng.normal(0.0, 0.22, size=(4, s_len)),
        "base_noise": rng.normal(0.0, 0.28, size=(n, s_len)),
    }


def _latent_path(config: FranceSyntheticConfigV88, graph: np.ndarray,
                 draws: dict[str, np.ndarray], coefficient: float):
    """Integrate the latent growth path for one relational coefficient.

    Returns the path plus the two increment streams the calibration is defined on:
    ``rel_inc`` is what the graph injected, ``nonrel_inc`` is everything else.
    """
    t_len, n, s_len = len(config.years), config.n_zones, len(config.sectors)
    growth = np.zeros((t_len, n, s_len), dtype=float)
    rel_inc = np.zeros_like(growth)
    nonrel_inc = np.zeros_like(growth)
    raw_rel = np.zeros_like(growth)
    growth[0] = draws["initial"]
    for t in range(t_len - 1):
        centred = growth[t] - growth[t].mean(0, keepdims=True)
        raw_rel[t + 1] = graph[t] @ centred
        base = (draws["ar"][None, :] * growth[t] + draws["macro"][t + 1][None, :]
                + draws["innovation"][t + 1])
        if config.years[t + 1] == 2020:
            base[:, (1, 2, 8)] -= 0.32
        if config.years[t + 1] == 2021:
            base[:, (1, 2, 8)] += 0.20
        nonrel_inc[t + 1] = base
        rel_inc[t + 1] = coefficient * raw_rel[t + 1]
        growth[t + 1] = np.clip(base + rel_inc[t + 1], -0.70, 0.70)
    return growth, rel_inc, nonrel_inc, raw_rel


def _realised_ratio(config, graph, draws, coefficient: float) -> float:
    _, rel_inc, nonrel_inc, _ = _latent_path(config, graph, draws, coefficient)
    denominator = _rms(nonrel_inc[1:])
    return _rms(rel_inc[1:]) / denominator if denominator > 0 else 0.0


CALIBRATION_MAX_STEPS = 60
CALIBRATION_TOLERANCE = 1e-4


def calibrate_coefficient(config: FranceSyntheticConfigV88, graph: np.ndarray,
                          draws: dict[str, np.ndarray]) -> dict[str, float]:
    """Solve for the coefficient that hits the requested *realised* latent ratio.

    A single closed-form probe is not enough. The relational increment feeds back through
    the autoregression, so the ratio realised on the calibrated path is far larger than
    the one the open-loop probe predicts: at the naive closed-form coefficient the
    realised ratio overshoots 0.25 by a factor of seventeen. The ratio is monotone in the
    coefficient and zero at zero, so a bracketed bisection on the *realised* quantity is
    both exact and deterministic.

    Every evaluation reuses the same frozen noise draws and reads only generator
    internals. No model output, F1, evaluation MSE or recovered edge enters the loop.
    """
    if config.scenario == "null" or config.requested_effective_ratio == 0.0:
        return {"applied_coefficient": 0.0, "probe_relational_rms": 0.0,
                "probe_nonrelational_rms": 0.0, "calibration_steps": 0}

    target = config.requested_effective_ratio
    _, _, probe_nonrel, probe_raw = _latent_path(config, graph, draws, 0.0)
    relational_rms = _rms(probe_raw[1:])
    nonrelational_rms = _rms(probe_nonrel[1:])
    if relational_rms <= 1e-12:
        raise ValueError("probe found no relational variation to scale")

    low, high = 0.0, target * nonrelational_rms / relational_rms
    steps = 0
    while _realised_ratio(config, graph, draws, high) < target and steps < 20:
        high *= 2.0
        steps += 1
    if _realised_ratio(config, graph, draws, high) < target:
        raise ValueError("could not bracket the requested effective ratio")
    for _ in range(CALIBRATION_MAX_STEPS):
        steps += 1
        middle = 0.5 * (low + high)
        if _realised_ratio(config, graph, draws, middle) < target:
            low = middle
        else:
            high = middle
        if high - low <= CALIBRATION_TOLERANCE * max(high, 1e-9):
            break
    coefficient = 0.5 * (low + high)
    return {"applied_coefficient": float(coefficient),
            "probe_relational_rms": float(relational_rms),
            "probe_nonrelational_rms": float(nonrelational_rms),
            "calibration_steps": int(steps)}


def generate_france_multisource_v88(
        config: FranceSyntheticConfigV88 = FranceSyntheticConfigV88()) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    years, n, s_len = config.years, config.n_zones, len(config.sectors)
    prior = _commuting_prior(n, config.commuting_k, rng)
    zone_features = rng.normal(size=(n, 4))
    graph, dense_graph, events = _dynamic_truth(
        prior, years, config.scenario, config.propagation_k, zone_features, rng)

    draws = _draw_dynamics(config, rng)
    calibration = calibrate_coefficient(config, graph, draws)
    growth, rel_inc, nonrel_inc, raw_rel = _latent_path(
        config, graph, draws, calibration["applied_coefficient"])

    latent_ratio = (_rms(rel_inc[1:]) / _rms(nonrel_inc[1:])
                    if _rms(nonrel_inc[1:]) > 0 else 0.0)

    log_base = 4.45 + 0.48 * zone_features[:, [0]] + zone_features @ draws["sector_loading"]
    base_level = np.exp(np.clip(log_base + draws["base_noise"], 0.0, 9.0))
    log_mean = np.empty_like(growth)
    log_mean[0] = np.log(base_level)
    for t in range(1, len(years)):
        log_mean[t] = np.clip(log_mean[t - 1] + 0.32 * growth[t],
                              np.log(0.15), np.log(20000.0))
    latent_mean = np.exp(log_mean)
    side_counts = _negative_binomial(latent_mean, config.count_dispersion, rng)

    # Observable ratio: the same two increment streams carried to the scale on which the
    # model actually sees growth, namely the log-count difference. The 0.32 factor is the
    # generator's own transmission coefficient; the denominator is the realised spread of
    # the observed differences, so the ratio says what fraction of what the loss sees is
    # relational.
    observed_diff = np.full_like(side_counts, np.nan)
    observed_diff[1:] = np.log1p(side_counts[1:]) - np.log1p(side_counts[:-1])
    observable_rel_rms = _rms(0.32 * rel_inc[1:])
    observable_total_rms = float(np.sqrt(np.nanmean(observed_diff[1:] ** 2)))
    observable_ratio = (observable_rel_rms / observable_total_rms
                        if observable_total_rms > 0 else 0.0)

    sparse = config.scenario == "dynamic_sparse"
    missing = config.missing_block_rate * (3.0 if sparse else 1.0)
    zone_scale = rng.lognormal(0.0, 0.35, size=(1, n, 1))
    employment_sector = _negative_binomial(latent_mean * zone_scale * 18.0,
                                           10.0 if sparse else 24.0, rng)
    private_jobs = employment_sector.sum(2, keepdims=True)
    employer_estab = _negative_binomial(np.maximum(private_jobs / 12.0, 1.0), 30.0, rng)
    wage_level = np.exp(np.log(36500.0) + 0.10 * zone_features[:, 3])[None, :, None]
    payroll = private_jobs * wage_level * rng.lognormal(0.0, 0.08, size=private_jobs.shape)
    for year, multiplier in ((2021, 1.025), (2023, 1.018)):
        if year in years:
            employer_estab[years.index(year):] *= multiplier
            private_jobs[years.index(year):] *= multiplier
            payroll[years.index(year):] *= multiplier
    employer_estab = np.rint(employer_estab)
    private_jobs = np.rint(private_jobs)

    stock = _negative_binomial(np.maximum(latent_mean * 7.0, 1.0), 28.0, rng)
    unemployment = np.clip(8.2 - 3.0 * growth.mean(2, keepdims=True)
                           + rng.normal(0, 0.45, size=(len(years), n, 1)), 2.0, 20.0)
    flores_shares = rng.dirichlet(np.ones(len(A17)) * 1.8, size=(len(years), n))
    flores_total = np.maximum(employer_estab[..., 0] * 1.25, 1.0)
    flores_estab = _negative_binomial(flores_total[..., None] * flores_shares, 16.0, rng)
    low = rng.uniform(size=flores_estab[:, :, 3].shape) < 0.76
    flores_estab[:, :, 3][low] = 0.0
    flores_jobs = _negative_binomial(np.maximum(private_jobs * 1.22, 1.0), 22.0, rng)

    srng = lambda offset: np.random.default_rng(config.seed + offset)
    sources = {
        "side_creations": _source_block(side_counts, years, 2012, 2025, 1, srng(1), missing,
            "registered establishment creations", "count", "A10_SIDE"),
        "side_active_stock": _source_block(stock, years, 2014, 2024, 2, srng(2), missing,
            "economically active establishment stock", "count", "A10_SIDE"),
        "urssaf_employer_establishments": _source_block(employer_estab, years, 1998, 2024, 1, srng(3), missing,
            "private-sector employer establishments", "count", "TOTAL"),
        "urssaf_private_headcount": _source_block(private_jobs, years, 1998, 2024, 1, srng(4), missing,
            "private-sector salaried headcount", "jobs", "TOTAL"),
        "urssaf_private_payroll": _source_block(payroll, years, 1998, 2024, 1, srng(5), missing,
            "private-sector gross payroll", "eur", "TOTAL"),
        "local_unemployment_rate": _source_block(unemployment, years, 2003, 2025, 1, srng(6), missing,
            "localized unemployment rate", "pct", "TOTAL"),
        "flores_establishments": _source_block(flores_estab, years, 2017, 2024, 2, srng(7), missing,
            "FLORES establishment level; no inter-vintage growth", "count", "A17_FLORES"),
        "flores_salaried_jobs": _source_block(flores_jobs, years, 2017, 2024, 2, srng(8), missing,
            "total salaried jobs including public and private", "jobs", "TOTAL"),
    }
    observed_zone_features = zone_features + rng.normal(0.0, 0.15, size=zone_features.shape)

    diagnostics = {
        "requested_effective_ratio": float(config.requested_effective_ratio
                                           if config.scenario != "null" else 0.0),
        "realised_latent_effective_ratio": float(latent_ratio),
        "realised_observable_effective_ratio": float(observable_ratio),
        "relational_rms": _rms(rel_inc[1:]),
        "nonrelational_rms": _rms(nonrel_inc[1:]),
        "applied_coefficient": float(calibration["applied_coefficient"]),
        "probe_relational_rms": float(calibration["probe_relational_rms"]),
        "probe_nonrelational_rms": float(calibration["probe_nonrelational_rms"]),
        "calibration_steps": int(calibration.get("calibration_steps", 0)),
        "observable_total_rms": observable_total_rms,
    }
    truth = {"prior": prior, "adjacency": graph, "dense_adjacency": dense_graph,
             "deviation": dense_graph - prior[None], "events": events,
             "latent_growth": growth, "latent_mean": latent_mean,
             "latent_zone_features": zone_features,
             "relational_increment": rel_inc, "nonrelational_increment": nonrel_inc,
             "calibration": diagnostics}
    metadata = {"years": years, "zones": tuple(f"Z{i:04d}" for i in range(n)),
                "a10": config.sectors, "a17": A17, "scenario": config.scenario,
                "source_breaks": {"urssaf": (2021, 2023), "common_shock": (2020, 2021)},
                "static_zone_features": observed_zone_features,
                "commuting_observation_years": tuple(y for y in (2012, 2017, 2022) if y in years)}
    return {"sources": sources, "truth": truth, "metadata": metadata,
            "config": dataclasses.asdict(config), "calibration": diagnostics}


def model_inputs(dataset: dict[str, Any], decision_year: int) -> dict[str, Any]:
    """Released observations only. Truth and calibration diagnostics never travel."""
    result = _model_inputs_v86(dataset, decision_year)
    for forbidden in ("truth", "calibration", "config"):
        result.pop(forbidden, None)
    return result
