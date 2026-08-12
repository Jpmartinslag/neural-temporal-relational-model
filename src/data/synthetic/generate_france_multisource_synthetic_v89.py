"""HERALD 89: the HERALD 88 truth, observed through three levels of exposure.

Nothing about the truth moves. Same commuting prior, same regimes, same shared relational
formula, same calibrated latent ratio of 0.25. What changes is how much of the process the
observer gets to see.

Exposure is multiplied the way a statistician gets more exposure in practice: by observing
more units of the same cell. A count that was ``NB(mu, phi)`` becomes ``NB(M*mu, M*phi)``,
whose variance is ``M*(mu + mu^2/phi)`` and whose coefficient of variation therefore falls
exactly as ``1/sqrt(M)``. Per-unit overdispersion is preserved; only the number of units
rises. That is a property of the instrument, not a softening of the truth: no noise term is
removed, no dynamic is smoothed, no scenario is re-tuned after seeing a score.

Three panels are built from the same generator call:

``IDENTIFIABLE``       exposure multiplied by a factor frozen during calibration;
``FRANCE_REALISTIC``   the empirical spread of French zone volumes, multiplier one;
``LOW_INFORMATION``    the lower quartile of that spread, multiplier one.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from src.data.synthetic.generate_france_multisource_synthetic import (
    A10, A17, SCENARIOS, YEARS, _commuting_prior, _dynamic_truth, _source_block,
)
from src.data.synthetic.generate_france_multisource_synthetic_v88 import (
    LATENT_RATIO_TOLERANCE, REQUESTED_EFFECTIVE_RATIO, _draw_dynamics, _latent_path,
    _rms, calibrate_coefficient,
)

EXPOSURE_GRID = (1, 2, 4, 8, 16)
CALIBRATION_SEEDS = tuple(range(8801, 8821))
FINAL_SEEDS = (8901, 8902, 8903, 8904, 8905)
INFORMATION_LEVELS = ("identifiable", "france_realistic", "low_information")

# HERALD 88 used generator seed 8601 and model seeds 42-46. The HERALD 89 seeds are
# disjoint from both, and calibration is disjoint from evaluation.
assert not set(CALIBRATION_SEEDS) & set(FINAL_SEEDS)


@dataclasses.dataclass(frozen=True)
class FranceSyntheticConfigV89:
    n_zones: int = 280
    years: tuple[int, ...] = YEARS
    sectors: tuple[str, ...] = A10
    seed: int = 8901
    scenario: str = "dynamic"
    commuting_k: int = 40
    propagation_k: int = 28
    count_dispersion: float = 18.0
    missing_block_rate: float = 0.025
    requested_effective_ratio: float = REQUESTED_EFFECTIVE_RATIO
    information_level: str = "identifiable"
    exposure_multiplier: int = 1

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}")
        if self.information_level not in INFORMATION_LEVELS:
            raise ValueError(f"information_level must be one of {INFORMATION_LEVELS}")
        if self.exposure_multiplier not in EXPOSURE_GRID:
            raise ValueError(f"exposure_multiplier must lie in {EXPOSURE_GRID}")
        if len(self.years) < 8 or tuple(sorted(self.years)) != self.years:
            raise ValueError("years must be sorted and contain at least eight steps")


def _scaled_negative_binomial(mean: np.ndarray, dispersion: float, multiplier: int,
                              rng: np.random.Generator) -> np.ndarray:
    """Draw ``NB(M*mu, M*phi)``: more units observed, same overdispersion per unit."""
    mu = np.maximum(np.asarray(mean, dtype=float), 1e-6) * float(multiplier)
    shape = max(float(dispersion) * float(multiplier), 1e-3)
    rate = rng.gamma(shape=shape, scale=mu / shape)
    return rng.poisson(rate).astype(float)


def _volume_profile(level: str, n_zones: int, rng: np.random.Generator) -> np.ndarray:
    """Per-zone multiplicative volume, from the French spread of zone sizes.

    ``france_realistic`` reproduces the heavy right tail of ZE2020 establishment counts
    with a lognormal whose spread is taken from the HERALD 86 panel and is *not* tuned
    afterwards. ``low_information`` keeps the lower quartile of the same draw, so the two
    levels differ by selection rather than by a new distribution. ``identifiable`` is flat,
    because it is a diagnostic level whose purpose is to isolate exposure.
    """
    if level == "identifiable":
        return np.ones(n_zones)
    draw = rng.lognormal(mean=0.0, sigma=0.85, size=n_zones)
    draw = draw / np.median(draw)
    if level == "france_realistic":
        return draw
    threshold = np.quantile(draw, 0.25)
    return np.minimum(draw, threshold)


def generate_france_multisource_v89(
        config: FranceSyntheticConfigV89 = FranceSyntheticConfigV89()) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    years, n, s_len = config.years, config.n_zones, len(config.sectors)
    prior = _commuting_prior(n, config.commuting_k, rng)
    zone_features = rng.normal(size=(n, 4))
    graph, dense_graph, events = _dynamic_truth(
        prior, years, config.scenario, config.propagation_k, zone_features, rng)

    draws = _draw_dynamics(config, rng)
    calibration = calibrate_coefficient(config, graph, draws)
    growth, rel_inc, nonrel_inc, _ = _latent_path(
        config, graph, draws, calibration["applied_coefficient"])
    latent_ratio = (_rms(rel_inc[1:]) / _rms(nonrel_inc[1:])
                    if _rms(nonrel_inc[1:]) > 0 else 0.0)

    sector_loading = draws["sector_loading"]
    log_base = 4.45 + 0.48 * zone_features[:, [0]] + zone_features @ sector_loading
    base_level = np.exp(np.clip(log_base + draws["base_noise"], 0.0, 9.0))
    volume = _volume_profile(config.information_level, n, rng)[:, None]
    base_level = base_level * volume

    log_mean = np.empty_like(growth)
    log_mean[0] = np.log(base_level)
    for t in range(1, len(years)):
        log_mean[t] = np.clip(log_mean[t - 1] + 0.32 * growth[t],
                              np.log(0.15), np.log(20000.0))
    latent_mean = np.exp(log_mean)
    side_counts = _scaled_negative_binomial(
        latent_mean, config.count_dispersion, config.exposure_multiplier, rng)

    sparse = config.scenario == "dynamic_sparse"
    missing = config.missing_block_rate * (3.0 if sparse else 1.0)
    zone_scale = rng.lognormal(0.0, 0.35, size=(1, n, 1))
    employment_sector = _scaled_negative_binomial(
        latent_mean * zone_scale * 18.0, 10.0 if sparse else 24.0,
        config.exposure_multiplier, rng)
    private_jobs = employment_sector.sum(2, keepdims=True)
    employer_estab = _scaled_negative_binomial(
        np.maximum(private_jobs / 12.0, 1.0), 30.0, 1, rng)
    wage_level = np.exp(np.log(36500.0) + 0.10 * zone_features[:, 3])[None, :, None]
    payroll = private_jobs * wage_level * rng.lognormal(0.0, 0.08, size=private_jobs.shape)
    for year, multiplier in ((2021, 1.025), (2023, 1.018)):
        if year in years:
            employer_estab[years.index(year):] *= multiplier
            private_jobs[years.index(year):] *= multiplier
            payroll[years.index(year):] *= multiplier
    employer_estab = np.rint(employer_estab)
    private_jobs = np.rint(private_jobs)

    stock = _scaled_negative_binomial(np.maximum(latent_mean * 7.0, 1.0), 28.0,
                                      config.exposure_multiplier, rng)
    unemployment = np.clip(8.2 - 3.0 * growth.mean(2, keepdims=True)
                           + rng.normal(0, 0.45, size=(len(years), n, 1)), 2.0, 20.0)
    flores_shares = rng.dirichlet(np.ones(len(A17)) * 1.8, size=(len(years), n))
    flores_total = np.maximum(employer_estab[..., 0] * 1.25, 1.0)
    flores_estab = _scaled_negative_binomial(flores_total[..., None] * flores_shares,
                                             16.0, 1, rng)
    low = rng.uniform(size=flores_estab[:, :, 3].shape) < 0.76
    flores_estab[:, :, 3][low] = 0.0
    flores_jobs = _scaled_negative_binomial(np.maximum(private_jobs * 1.22, 1.0), 22.0,
                                            1, rng)

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

    observed = np.asarray(sources["side_creations"]["values"], dtype=float)
    mask = np.asarray(sources["side_creations"]["availability_mask"], dtype=bool)
    volumes = observed[mask]
    diagnostics = {
        "requested_effective_ratio": float(config.requested_effective_ratio
                                           if config.scenario != "null" else 0.0),
        "realised_latent_effective_ratio": float(latent_ratio),
        "applied_coefficient": float(calibration["applied_coefficient"]),
        "calibration_steps": int(calibration.get("calibration_steps", 0)),
        "relational_rms": _rms(rel_inc[1:]),
        "nonrelational_rms": _rms(nonrel_inc[1:]),
        "information_level": config.information_level,
        "exposure_multiplier": int(config.exposure_multiplier),
        "median_observed_count": float(np.median(volumes)) if volumes.size else 0.0,
        "q25_observed_count": float(np.quantile(volumes, 0.25)) if volumes.size else 0.0,
        "q75_observed_count": float(np.quantile(volumes, 0.75)) if volumes.size else 0.0,
    }
    truth = {"prior": prior, "adjacency": graph, "dense_adjacency": dense_graph,
             "deviation": dense_graph - prior[None], "events": events,
             "latent_growth": growth, "latent_mean": latent_mean,
             "latent_zone_features": zone_features,
             "relational_increment": rel_inc, "nonrelational_increment": nonrel_inc,
             "calibration": diagnostics}
    metadata = {"years": years, "zones": tuple(f"Z{i:04d}" for i in range(n)),
                "a10": config.sectors, "a17": A17, "scenario": config.scenario,
                "information_level": config.information_level,
                "exposure_multiplier": int(config.exposure_multiplier),
                "source_breaks": {"urssaf": (2021, 2023), "common_shock": (2020, 2021)},
                "static_zone_features": observed_zone_features,
                "commuting_observation_years": tuple(y for y in (2012, 2017, 2022) if y in years)}
    return {"sources": sources, "truth": truth, "metadata": metadata,
            "config": dataclasses.asdict(config), "calibration": diagnostics}


def model_inputs(dataset: dict[str, Any], decision_year: int) -> dict[str, Any]:
    """Released observations only. Truth and calibration diagnostics never travel."""
    from src.data.synthetic.generate_france_multisource_synthetic import (
        model_inputs as _released,
    )
    result = _released(dataset, decision_year)
    for forbidden in ("truth", "calibration", "config"):
        result.pop(forbidden, None)
    result["metadata"] = {key: value for key, value in result["metadata"].items()
                          if key not in ("latent_zone_features",)}
    return result
