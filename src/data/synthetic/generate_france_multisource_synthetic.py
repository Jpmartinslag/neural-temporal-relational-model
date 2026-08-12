"""France-shaped multi-source synthetic benchmark for HERALD 86.

The generator keeps source semantics and availability separate.  It exposes known
truth for evaluation, while :func:`model_inputs` returns only causally available
observations.  Synthetic relations are validation fixtures, not claims about France.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np


YEARS = tuple(range(1998, 2026))
A10 = ("BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU")
A17 = ("AZ", "DE", "C1", "C2", "C3", "C4", "C5", "FZ", "GZ",
       "HZ", "IZ", "JZ", "KZ", "LZ", "MN", "OQ", "RU")
SCENARIOS = ("null", "stable", "dynamic", "dynamic_sparse")


@dataclasses.dataclass(frozen=True)
class FranceSyntheticConfig:
    n_zones: int = 280
    years: tuple[int, ...] = YEARS
    sectors: tuple[str, ...] = A10
    seed: int = 8601
    scenario: str = "dynamic"
    commuting_k: int = 40
    propagation_k: int = 28
    count_dispersion: float = 18.0
    missing_block_rate: float = 0.025

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}")
        if len(self.years) < 8 or tuple(sorted(self.years)) != self.years:
            raise ValueError("years must be sorted and contain at least eight steps")
        if self.n_zones < 6 or len(self.sectors) < 3:
            raise ValueError("benchmark needs at least six zones and three sectors")


def _normalise_rows(a: np.ndarray) -> np.ndarray:
    out = np.maximum(np.asarray(a, dtype=float), 0.0).copy()
    np.fill_diagonal(out, 0.0)
    den = out.sum(1, keepdims=True)
    return np.divide(out, den, out=np.zeros_like(out), where=den > 0)


def _commuting_prior(n: int, k: int, rng: np.random.Generator) -> np.ndarray:
    coords = rng.uniform(size=(n, 2))
    dist = np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))
    np.fill_diagonal(dist, np.inf)
    k = min(max(1, k), n - 1)
    idx = np.argpartition(dist, k - 1, axis=1)[:, :k]
    a = np.zeros((n, n), dtype=float)
    row = np.arange(n)[:, None]
    directional = rng.lognormal(mean=0.0, sigma=0.22, size=idx.shape)
    a[row, idx] = np.exp(-4.0 * dist[row, idx]) * directional
    return _normalise_rows(a)


def _topk_rows(a: np.ndarray, k: int) -> np.ndarray:
    n = len(a); k = min(max(1, k), n - 1)
    out = np.zeros_like(a)
    idx = np.argpartition(-a, k - 1, axis=1)[:, :k]
    row = np.arange(n)[:, None]
    out[row, idx] = a[row, idx]
    return _normalise_rows(out)


def _dynamic_truth(prior: np.ndarray, years: tuple[int, ...], scenario: str,
                   propagation_k: int, zone_features: np.ndarray,
                   rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Generate a shared, observable-feature-conditioned flow modulation.

    The dense layer preserves every observed commuting edge.  Only the top-k
    propagation support enters the outcome equation; births/deaths refer to
    changes in that support.  No edge outside observed commuting can be created.
    """
    t_len, n = len(years), len(prior)
    dense = np.repeat(prior[None, :, :], t_len, axis=0)
    events: list[dict[str, Any]] = []
    if scenario not in ("dynamic", "dynamic_sparse"):
        propagation = np.stack([_topk_rows(prior, propagation_k) for _ in years])
        return propagation, dense, events

    src = zone_features[:, None, :]
    dst = zone_features[None, :, :]
    shared = (0.65 * src[..., 0] * dst[..., 1]
              - 0.55 * np.abs(src[..., 2] - dst[..., 2])
              + 0.35 * src[..., 3] * dst[..., 3])
    for t, year in enumerate(years):
        regime = (-0.30 if year < 2012 else
                  0.00 if year < 2017 else
                  0.40 if year < 2020 else
                  -0.80 if year == 2020 else
                  0.70 if year == 2021 else 0.20)
        interaction = np.outer(zone_features[:, 1], zone_features[:, 2])
        modulation = np.exp(0.25 * np.tanh(shared + regime * interaction))
        dense[t] = _normalise_rows(prior * modulation)
    propagation = np.stack([_topk_rows(a, propagation_k) for a in dense])
    support = propagation > 0
    for t in range(1, t_len):
        born = np.argwhere(support[t] & ~support[t - 1])
        died = np.argwhere(~support[t] & support[t - 1])
        events.extend({"event": "birth", "source": int(i), "target": int(j),
                       "year": int(years[t])} for i, j in born)
        events.extend({"event": "death", "source": int(i), "target": int(j),
                       "year": int(years[t])} for i, j in died)
    return propagation, dense, events


def _negative_binomial(mean: np.ndarray, dispersion: float,
                       rng: np.random.Generator) -> np.ndarray:
    """NB2 draw: variance = mean + mean**2 / dispersion."""
    mu = np.maximum(np.asarray(mean, dtype=float), 1e-6)
    shape = max(float(dispersion), 1e-3)
    rate = rng.gamma(shape=shape, scale=mu / shape)
    return rng.poisson(rate).astype(float)


def _simulate_latent(config: FranceSyntheticConfig, graph: np.ndarray,
                     zone_features: np.ndarray, rng: np.random.Generator
                     ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t_len, n, s_len = len(config.years), config.n_zones, len(config.sectors)
    growth = np.zeros((t_len, n, s_len), dtype=float)
    macro = rng.normal(0.0, 0.045, size=(t_len, s_len))
    ar = rng.uniform(-0.38, 0.28, size=s_len)
    relation_strength = 0.0 if config.scenario == "null" else 0.22
    noise = 0.10 if config.scenario != "dynamic_sparse" else 0.18
    growth[0] = rng.normal(0.0, noise, size=(n, s_len))
    for t in range(t_len - 1):
        centred = growth[t] - growth[t].mean(0, keepdims=True)
        relational = graph[t] @ centred
        growth[t + 1] = (ar[None, :] * growth[t] + macro[t + 1][None, :]
                         + relation_strength * relational
                         + rng.normal(0.0, noise, size=(n, s_len)))
        if config.years[t + 1] == 2020:
            growth[t + 1, :, (1, 2, 8)] -= 0.32
        if config.years[t + 1] == 2021:
            growth[t + 1, :, (1, 2, 8)] += 0.20
        growth[t + 1] = np.clip(growth[t + 1], -0.70, 0.70)

    sector_loading = rng.normal(0.0, 0.22, size=(4, s_len))
    log_base = 4.45 + 0.48 * zone_features[:, [0]] + zone_features @ sector_loading
    base = np.exp(np.clip(log_base + rng.normal(0, 0.28, size=(n, s_len)), 0.0, 9.0))
    log_mean = np.empty_like(growth)
    log_mean[0] = np.log(base)
    for t in range(1, t_len):
        log_mean[t] = np.clip(log_mean[t - 1] + 0.32 * growth[t],
                              np.log(0.15), np.log(20000.0))
    means = np.exp(log_mean)
    counts = _negative_binomial(means, config.count_dispersion, rng)
    return growth, means, counts


def _source_block(values: np.ndarray, years: tuple[int, ...], start: int, end: int,
                  release_lag: int, rng: np.random.Generator, missing_rate: float,
                  semantics: str, unit: str, sector_scheme: str) -> dict[str, Any]:
    values = np.asarray(values, dtype=float).copy()
    t_len, n = values.shape[:2]
    structural = np.array([(start <= y <= end) for y in years], dtype=bool)
    mask = np.broadcast_to(structural.reshape((t_len,) + (1,) * (values.ndim - 1)),
                           values.shape).copy()
    # Missing blocks operate at ZE x year and are broadcast over channels.
    block = rng.uniform(size=(t_len, n)) < missing_rate
    block[~structural] = True
    mask &= np.broadcast_to((~block).reshape((t_len, n) + (1,) * (values.ndim - 2)),
                            values.shape)
    observed = values.copy()
    observed[~mask] = np.nan
    release = np.full(values.shape, -1, dtype=np.int16)
    for t, year in enumerate(years):
        if structural[t]:
            release[t] = year + release_lag
    return {"values": observed, "availability_mask": mask.astype(np.int8),
            "release_year": release, "semantics": semantics, "unit": unit,
            "sector_scheme": sector_scheme, "window": (start, end)}


def generate_france_multisource(config: FranceSyntheticConfig = FranceSyntheticConfig()) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    years, n, s_len = config.years, config.n_zones, len(config.sectors)
    prior = _commuting_prior(n, config.commuting_k, rng)
    zone_features = rng.normal(size=(n, 4))
    graph, dense_graph, events = _dynamic_truth(
        prior, years, config.scenario, config.propagation_k, zone_features, rng)
    growth, latent_mean, side_counts = _simulate_latent(config, graph, zone_features, rng)
    sparse = config.scenario == "dynamic_sparse"
    missing = config.missing_block_rate * (3.0 if sparse else 1.0)

    zone_scale = rng.lognormal(0.0, 0.35, size=(1, n, 1))
    employment_sector = _negative_binomial(latent_mean * zone_scale * 18.0,
                                            10.0 if sparse else 24.0, rng)
    private_jobs = employment_sector.sum(2, keepdims=True)
    employer_estab = _negative_binomial(np.maximum(private_jobs / 12.0, 1.0), 30.0, rng)
    wage_level = np.exp(np.log(36500.0) + 0.10 * zone_features[:, 3])[None, :, None]
    payroll = private_jobs * wage_level * rng.lognormal(0.0, 0.08, size=private_jobs.shape)
    # Explicit measurement breaks: metadata, not relational events.
    for year, multiplier in ((2021, 1.025), (2023, 1.018)):
        if year in years:
            employer_estab[years.index(year):] *= multiplier
            private_jobs[years.index(year):] *= multiplier
            payroll[years.index(year):] *= multiplier
    # Measurement breaks change the count-generating level, not the count unit.
    employer_estab = np.rint(employer_estab)
    private_jobs = np.rint(private_jobs)

    stock = _negative_binomial(np.maximum(latent_mean * 7.0, 1.0), 28.0, rng)
    unemployment = np.clip(8.2 - 3.0 * growth.mean(2, keepdims=True)
                           + rng.normal(0, 0.45, size=(len(years), n, 1)), 2.0, 20.0)
    flores_shares = rng.dirichlet(np.ones(len(A17)) * 1.8, size=(len(years), n))
    flores_total = np.maximum(employer_estab[..., 0] * 1.25, 1.0)
    flores_estab = _negative_binomial(flores_total[..., None] * flores_shares, 16.0, rng)
    # A low-volume A17 channel supplies genuine observed zeros.
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
    source_breaks = {"urssaf": (2021, 2023), "common_shock": (2020, 2021)}
    observed_zone_features = zone_features + rng.normal(0.0, 0.15, size=zone_features.shape)
    truth = {"prior": prior, "adjacency": graph, "dense_adjacency": dense_graph,
             "deviation": dense_graph - prior[None],
             "events": events, "latent_growth": growth, "latent_mean": latent_mean,
             "latent_zone_features": zone_features}
    metadata = {"years": years, "zones": tuple(f"Z{i:04d}" for i in range(n)),
                "a10": config.sectors, "a17": A17, "scenario": config.scenario,
                "source_breaks": source_breaks,
                "static_zone_features": observed_zone_features,
                "commuting_observation_years": tuple(y for y in (2012, 2017, 2022) if y in years)}
    return {"sources": sources, "truth": truth, "metadata": metadata,
            "config": dataclasses.asdict(config)}


def model_inputs(dataset: dict[str, Any], decision_year: int) -> dict[str, Any]:
    """Return only observations released by ``decision_year``; never return truth."""
    years = tuple(dataset["metadata"]["years"])
    keep_t = np.array([year <= decision_year for year in years], dtype=bool)
    result: dict[str, Any] = {"metadata": dict(dataset["metadata"]), "sources": {}}
    result["metadata"]["decision_year"] = int(decision_year)
    for name, block in dataset["sources"].items():
        mask = block["availability_mask"].astype(bool).copy()
        released = (block["release_year"] >= 0) & (block["release_year"] <= decision_year)
        temporal = np.broadcast_to(keep_t.reshape((len(years),) + (1,) * (mask.ndim - 1)), mask.shape)
        final_mask = mask & released & temporal
        values = block["values"].copy()
        values[~final_mask] = np.nan
        result["sources"][name] = {k: v for k, v in block.items()
                                    if k not in ("values", "availability_mask", "release_year")}
        result["sources"][name].update({"values": values,
                                         "availability_mask": final_mask.astype(np.int8)})
    return result
