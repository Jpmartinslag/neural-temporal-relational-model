"""HERALD 96: a synthetic France whose relations are not all commuting relations.

Every earlier stage restricted candidate edges to the forty nearest commuting neighbours, so
a relation between two distant zones could not be found, or even considered. This generator
builds three families of relation at once and deliberately places one of them **outside**
commuting, so that a support restricted to commuting provably cannot contain it and the
comparison between supports means something.

    A. commuting        propagation along the observed commuting support.
    B. similarity       pairs that resemble each other in a latent economic profile,
                        independently of distance. Drawn to be far apart and to carry no
                        commuting flow.
    C. complementarity  the source anticipates the target only under a regime, so the
                        contribution is gated by the target's own state and a linear
                        detector averaging over all periods sees close to nothing.

**Nothing here is reconstructible from a feature the model receives.** The similarity truth
is drawn from a latent profile that is never exported. What the candidate generator may use
is a *noisy causal estimate* of similarity computed from released observations, good enough
to propose pairs and far too weak to identify which of them are true. A guard measures that
gap rather than asserting it.

**Positive and negative pairs are matched inside each family.** For every true edge the
generator records a decoy: a pair drawn from the same family's candidate pool, at comparable
distance and comparable observable similarity, that carries no mechanism. Without matched
decoys a method could separate true from false by distance or by similarity alone and would
be scored as having discovered something.

The marginals, autocorrelations, dispersion, masks, release lags, breaks and observation
models are v94's, unchanged, including the cell-by-cell paired draws HERALD 95 added.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from src.data.synthetic.generate_france_multisignal_v94 import (
    BREAKS, COVID_YEARS, LEVEL_DRIFT_SD, LEVEL_VOLUME_SD, SIGNAL_SPEC, STATE_PERSISTENCE,
    VOLUME_LOG_SD, _commuting_prior, _draw_observation, _row_normalise, _topk,
)

FAMILIES = ("commuting", "similarity", "complementarity")
SCENARIOS = ("M0_NULL", "M1_MULTIRELATIONAL")
SCALES = (0.0, 1.0, 2.0)
SMOKE_SEEDS = (9951,)
FINAL_SEEDS = (9961, 9962, 9963, 9964, 9965)

# Edges per family. Small and equal, so no family dominates the metrics by count alone.
EDGES_PER_FAMILY = 40
# The regime gate of family C, normalised to unit root-mean-square so that the family carries
# the same amplitude as the others and differs only in *when* it acts.
GATE_ON, GATE_OFF = 1.8, 0.2
# How far apart a similarity edge must be, as a quantile of the distance distribution. High
# enough that the pair cannot plausibly share a commuting flow.
SIMILARITY_MIN_DISTANCE_QUANTILE = 0.60
# How much of a zone's state comes from the profile-loaded common factors rather than from
# its own idiosyncratic path. It has to be large enough that an observer can recover a usable
# similarity from the trajectories, and small enough that similar zones are not simply copies
# of one another.
PROFILE_WEIGHT = 0.55


@dataclasses.dataclass(frozen=True)
class MultirelationalConfig:
    n_zones: int = 280
    first_year: int = 1998
    last_year: int = 2025
    seed: int = 9961
    scenario: str = "M1_MULTIRELATIONAL"
    relational_scale: float = 1.0
    commuting_k: int = 40
    edges_per_family: int = EDGES_PER_FAMILY
    low_information_share: float = 0.25
    missing_block_rate: float = 0.02

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}, got {self.scenario!r}")
        if self.n_zones < 40:
            raise ValueError("at least forty zones are needed for matched decoys")


# ── territory, profiles and the three families ───────────────────────────────

def _coordinates_and_distance(n: int, rng: np.random.Generator):
    coords = rng.uniform(size=(n, 2))
    distance = np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))
    np.fill_diagonal(distance, np.inf)
    return coords, distance


def _latent_profile(n: int, rng: np.random.Generator) -> np.ndarray:
    """The economic profile similarity is drawn from. Never exported to the model."""
    return rng.normal(size=(n, 3))


def _profile_similarity(profile: np.ndarray) -> np.ndarray:
    centred = profile - profile.mean(0)
    norm = np.linalg.norm(centred, axis=1, keepdims=True)
    similarity = (centred / np.maximum(norm, 1e-12)) @ (centred / np.maximum(norm, 1e-12)).T
    np.fill_diagonal(similarity, -np.inf)
    return similarity


def _pick_matched(candidates: np.ndarray, chosen: set, count: int,
                  rng: np.random.Generator) -> list[tuple[int, int]]:
    """Draw ``count`` pairs from ``candidates`` avoiding those already taken."""
    out: list[tuple[int, int]] = []
    order = rng.permutation(len(candidates))
    for index in order:
        source, target = int(candidates[index, 0]), int(candidates[index, 1])
        if source == target or (source, target) in chosen:
            continue
        chosen.add((source, target))
        out.append((source, target))
        if len(out) == count:
            break
    return out


def build_relations(n: int, commuting: np.ndarray, distance: np.ndarray,
                    similarity: np.ndarray, edges_per_family: int,
                    rng: np.random.Generator) -> dict[str, Any]:
    """True edges and matched decoys for each family.

    A decoy is drawn from the same pool as its true edge and matched on the two quantities
    that could otherwise separate the classes for free: distance, and observable-side
    similarity. Without that matching a detector could score perfectly by ranking on
    distance and would be credited with a discovery it never made.
    """
    taken: set = set()
    relations: dict[str, list[tuple[int, int]]] = {}
    decoys: dict[str, list[tuple[int, int]]] = {}

    # A. commuting: pairs carrying real flow.
    flow_pairs = np.array(np.nonzero(commuting > 0)).T
    relations["commuting"] = _pick_matched(flow_pairs, taken, edges_per_family, rng)
    decoys["commuting"] = _pick_matched(flow_pairs, taken, edges_per_family, rng)

    # B and C: far apart, no commuting flow, high profile similarity.
    #
    # The four sets -- similarity true, similarity decoy, complementarity true,
    # complementarity decoy -- are dealt round-robin from one ranked pool, so all four carry
    # the *same* profile similarity and the same distance regime by construction. Drawing the
    # decoys from further down the ranking was the first design and it left the true pairs at
    # a profile similarity of 0.725 against the decoys' 0.039: any detector ranking on
    # similarity would have scored perfectly without discovering anything. Matching them is
    # what makes the family a test of mechanism rather than of proximity in profile space.
    far = distance > np.quantile(distance[np.isfinite(distance)],
                                 SIMILARITY_MIN_DISTANCE_QUANTILE)
    eligible = far & (commuting <= 0)
    ranked = np.argsort(-np.where(eligible, similarity, -np.inf), axis=None)
    pool = [(int(index // n), int(index % n)) for index in ranked[:12 * edges_per_family]]
    buckets: dict[str, list] = {"similarity_true": [], "similarity_decoy": [],
                                "complementarity_true": [], "complementarity_decoy": []}
    order = list(buckets)
    for position, pair in enumerate(pool):
        buckets[order[position % 4]].append(pair)
    relations["similarity"] = _pick_matched(
        np.array(buckets["similarity_true"]), taken, edges_per_family, rng)
    decoys["similarity"] = _pick_matched(
        np.array(buckets["similarity_decoy"]), taken, edges_per_family, rng)
    relations["complementarity"] = _pick_matched(
        np.array(buckets["complementarity_true"]), taken, edges_per_family, rng)
    decoys["complementarity"] = _pick_matched(
        np.array(buckets["complementarity_decoy"]), taken, edges_per_family, rng)

    return {"edges": relations, "decoys": decoys}


def relation_matrices(relations: dict[str, Any], n: int) -> dict[str, np.ndarray]:
    out = {}
    for family, edges in relations["edges"].items():
        matrix = np.zeros((n, n))
        for source, target in edges:
            matrix[source, target] = 1.0
        out[family] = matrix
    return out


# ── the process ──────────────────────────────────────────────────────────────

def _simulate(config: MultirelationalConfig, matrices: dict[str, np.ndarray],
              profile: np.ndarray, years: np.ndarray,
              rng: np.random.Generator) -> dict[str, Any]:
    """One latent state per zone, propagated along three differently-shaped families.

        z[t+1]   = rho z[t] + shock[t+1]
        A_t      = sum over families of  w_f * gate_f[t] * (M_f^T @ centred(z[t]))
        eta_s    = ar_s eta_s[t] + macro + gamma_s z[t] + lambda_s * scale * A_t + noise

    The commuting and similarity families propagate the state directly. The complementarity
    family is gated by the *target's* own state, so its contribution is present in some
    periods and absent in others; averaged over the whole panel a linear detector sees a
    fraction of what is there, which is the point of the family.
    """
    n_periods, n = len(years), config.n_zones
    names = list(SIGNAL_SPEC)

    macro = {name: rng.normal(0.0, 0.010, size=n_periods) for name in names}
    shock = rng.normal(0.0, 1.0, size=(n_periods, n))
    factor_shock = rng.normal(0.0, 1.0, size=(n_periods, profile.shape[1]))
    per_signal_noise = rng.normal(0.0, 1.0, size=(len(names), n_periods, n))

    idiosyncratic = np.zeros((n_periods, n))
    idiosyncratic[0] = shock[0]
    for t in range(n_periods - 1):
        idiosyncratic[t + 1] = STATE_PERSISTENCE * idiosyncratic[t] + shock[t + 1]

    # Common factors, loaded by each zone's latent profile. Without this the profile only
    # chose which pairs to connect and never reached the observations, so two "similar" zones
    # were not observably similar at all: an observable similarity would have been pure noise
    # and the similarity-only support could not have contained a single true edge. With it,
    # zones of similar profile move together, an observer can *propose* them as candidates,
    # and -- because the decoys share that similarity -- cannot tell which of them carry a
    # mechanism. That is exactly the division of labour the design needs.
    factors = np.zeros((n_periods, profile.shape[1]))
    for t in range(n_periods - 1):
        factors[t + 1] = STATE_PERSISTENCE * factors[t] + factor_shock[t + 1]
    common = factors @ profile.T

    state = PROFILE_WEIGHT * common + (1.0 - PROFILE_WEIGHT) * idiosyncratic
    state = state / max(float(np.std(state)), 1e-12)

    gate = np.where(state >= 0.0, GATE_ON, GATE_OFF)
    gate = gate / max(float(np.sqrt(np.mean(gate ** 2))), 1e-12)

    per_family = {family: np.zeros((n_periods, n)) for family in FAMILIES}
    for t in range(n_periods - 1):
        centred = state[t] - state[t].mean()
        for family in FAMILIES:
            arriving = matrices[family].T @ centred
            per_family[family][t + 1] = (arriving * gate[t]
                                         if family == "complementarity" else arriving)
    total = sum(per_family.values())
    normaliser = max(float(np.sqrt(np.mean(total[1:] ** 2))), 1e-12)

    latent = {name: np.zeros((n_periods, n)) for name in names}
    relational = {name: np.zeros((n_periods, n)) for name in names}
    for index, name in enumerate(names):
        latent[name][0] = per_signal_noise[index][0] * SIGNAL_SPEC[name]["noise"]

    for t in range(n_periods - 1):
        for index, name in enumerate(names):
            spec = SIGNAL_SPEC[name]
            neighbour = (spec["loading"] * spec["noise"] * config.relational_scale
                         * total[t + 1] / normaliser)
            relational[name][t + 1] = neighbour
            latent[name][t + 1] = np.clip(
                spec["ar_log"] * latent[name][t] + macro[name][t + 1]
                + spec["gamma"] * spec["noise"] * state[t] + neighbour
                + spec["noise"] * per_signal_noise[index][t + 1], -0.60, 0.60)
    return {"latent": latent, "relational": relational, "state": state,
            "per_family": per_family, "gate": gate, "total": total}


def _observe_paired(name: str, path: np.ndarray, volume: np.ndarray, years: np.ndarray,
                    quarters: np.ndarray, seed: int, key: int) -> np.ndarray:
    spec = SIGNAL_SPEC[name]
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
    if spec["family"] in ("negative_binomial", "gamma"):
        ceiling = 20.0 if spec["family"] == "negative_binomial" else 30.0
        mean = np.exp(np.clip(level, 0.0, ceiling))
        return _draw_observation(spec["family"], mean, spec["dispersion"], key, seed)
    centre = np.log(spec["median"] / (100.0 - spec["median"]))
    zone_offset = 0.030 * np.log(np.maximum(volume, 1e-6))[None, :]
    logit = centre - zone_offset + 0.9 * path
    jitter = np.random.default_rng([seed, 6_000 + key]).normal(0.0, 0.20, size=logit.shape)
    return np.clip(100.0 / (1.0 + np.exp(-logit)) + jitter, 1.0, 30.0)


def generate_multirelational(
        config: MultirelationalConfig = MultirelationalConfig()) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
    years_axis = np.repeat(np.arange(config.first_year, config.last_year + 1), 4)
    quarters_axis = np.tile(np.arange(1, 5), config.last_year - config.first_year + 1)
    n_periods, n = len(years_axis), config.n_zones

    coords, distance = _coordinates_and_distance(n, rng)
    commuting = _commuting_prior(n, config.commuting_k, rng)
    profile = _latent_profile(n, rng)
    similarity = _profile_similarity(profile)
    relations = build_relations(n, commuting, distance, similarity,
                                config.edges_per_family, rng)
    matrices = relation_matrices(relations, n)
    if config.scenario == "M0_NULL":
        # No propagation whatever. The families and their pairs are still *drawn*, so the
        # random stream and the candidate pools are identical to the mechanism scenario and
        # the two differ only in whether anything travels along the edges.
        matrices = {family: np.zeros_like(matrix) for family, matrix in matrices.items()}

    simulated = _simulate(config, matrices, profile, years_axis, rng)

    volume = np.random.default_rng([config.seed, 2_000]).lognormal(
        0.0, VOLUME_LOG_SD, size=n)
    volume = volume / np.median(volume)
    low_information = volume <= np.quantile(volume, config.low_information_share)

    signals: dict[str, Any] = {}
    for index, (name, spec) in enumerate(SIGNAL_SPEC.items()):
        values = _observe_paired(name, simulated["latent"][name], volume, years_axis,
                                 quarters_axis, config.seed, index)
        start, end = spec["window"]
        in_window = (years_axis >= start) & (years_axis <= end)
        if spec["freq"] == "A":
            in_window = in_window & (quarters_axis == 4)
        mask = np.broadcast_to(in_window[:, None], values.shape).copy()
        mask &= ~(np.random.default_rng([config.seed, 1_000 + index]).uniform(
            size=values.shape) < config.missing_block_rate)
        signals[name] = {
            "values": np.where(mask, values, np.nan),
            "availability_mask": mask.astype(np.int8),
            "release_year": np.where(in_window, years_axis + spec["release_lag_periods"], -1),
            "family": spec["family"], "freq": spec["freq"], "label": spec["label"],
            "window": spec["window"]}

    outside = {family: int(sum(1 for s, t in relations["edges"][family]
                               if commuting[s, t] <= 0))
               for family in FAMILIES}
    diagnostics = {
        "scenario": config.scenario, "relational_scale": config.relational_scale,
        "edges_per_family": {f: len(relations["edges"][f]) for f in FAMILIES},
        "decoys_per_family": {f: len(relations["decoys"][f]) for f in FAMILIES},
        "true_edges_outside_commuting": outside,
        "relational_rms": {name: float(np.sqrt(np.mean(simulated["relational"][name][1:] ** 2)))
                           for name in SIGNAL_SPEC},
        "noise_rms": {name: float(SIGNAL_SPEC[name]["noise"]) for name in SIGNAL_SPEC},
        "clipped_share": {
            name: float(np.mean(np.abs(np.abs(simulated["latent"][name]) - 0.60) < 1e-9))
            for name in SIGNAL_SPEC},
        "low_information_zones": int(low_information.sum()),
    }
    diagnostics["relational_share"] = {
        name: diagnostics["relational_rms"][name] / max(diagnostics["noise_rms"][name], 1e-12)
        for name in SIGNAL_SPEC}

    return {
        "signals": signals,
        "metadata": {"years": years_axis, "quarters": quarters_axis,
                     "zones": tuple(f"Z{i:04d}" for i in range(n)),
                     "scenario": config.scenario, "low_information": low_information,
                     "breaks": BREAKS, "covid_years": COVID_YEARS},
        "truth": {"commuting": commuting, "distance": distance, "coordinates": coords,
                  "profile": profile, "profile_similarity": similarity,
                  "relations": relations, "matrices": matrices,
                  "latent": simulated["latent"], "relational": simulated["relational"],
                  "state": simulated["state"], "per_family": simulated["per_family"],
                  "total_arriving": simulated["total"],
                  "gate": simulated["gate"], "diagnostics": diagnostics},
        "config": dataclasses.asdict(config),
        "calibration": diagnostics,
    }


def model_inputs(dataset: dict[str, Any], decision_period: int) -> dict[str, Any]:
    """Released observations only. Truth, profiles and relations never travel to the model."""
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


__all__ = ["FAMILIES", "SCENARIOS", "SCALES", "SMOKE_SEEDS", "FINAL_SEEDS",
           "MultirelationalConfig", "generate_multirelational", "model_inputs",
           "build_relations", "relation_matrices"]
