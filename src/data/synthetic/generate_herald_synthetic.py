"""
generate_herald_synthetic.py

Controlled synthetic economic panel generator for HERALD benchmark (DEC-039).

Produces panels with known causal structure:
- Positive/negative sector-sector relations with lags 1-2
- Linear and non-linear relationships
- Territory-territory propagation
- Crisis, recovery, structural breaks
- Three masking mechanisms: MCAR, MAR, block-temporal
- Full ground truth for every hidden label and relation

Usage:
    from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
    ds = generate_dataset(SyntheticConfig(n_territories=10, n_sectors=5, n_years=12, seed=42))
"""

from __future__ import annotations

import dataclasses
from typing import NamedTuple

import numpy as np


# ── Economic state labels ──────────────────────────────────────────────────────
STATE_GROWTH = "growth"
STATE_ACCELERATION = "acceleration"
STATE_STAGNATION = "stagnation"
STATE_DECLINE = "decline"
STATE_RECOVERY = "recovery"
STATE_CRISIS = "crisis"


class TrueRelation(NamedTuple):
    source_sector: int
    target_sector: int
    lag: int              # 1 or 2
    weight: float         # positive = amplifying, negative = dampening
    nonlinear: bool       # True → tanh transform applied to source value


@dataclasses.dataclass
class SyntheticConfig:
    """All hyperparameters for synthetic data generation. Deterministic given seed."""
    n_territories: int = 10
    n_sectors: int = 5
    n_years: int = 12

    seed: int = 42

    # True relation parameters
    n_true_relations: int = 4        # directed sector→sector edges
    weight_range: tuple = (0.4, 0.8) # absolute weight magnitude
    frac_nonlinear: float = 0.3      # fraction of relations with tanh nonlinearity
    frac_negative: float = 0.4       # fraction of relations with negative weight

    # AR and propagation parameters
    ar_coef_range: tuple = (0.3, 0.6)   # AR(1) coefficient per sector
    territory_propagation: float = 0.15  # weight of neighboring territory same-sector signal
    territory_radius: float = 0.35       # adjacency threshold in [0,1] space

    # Noise
    noise_sigma_range: tuple = (0.10, 0.25)

    # Regimes
    crisis_duration: int = 3            # years of crisis effect
    n_crisis_territories: float = 0.35  # fraction affected by crisis
    n_crisis_sectors: float = 0.5       # fraction of sectors hit by crisis
    structural_break_year: int | None = None  # if None, set to 3/4 of n_years

    # Masking (include 50% for stress-testing)
    mcar_rates: tuple = (0.10, 0.20, 0.30, 0.50)
    mar_rates: tuple = (0.10, 0.20, 0.30, 0.50)
    block_rates: tuple = (0.10, 0.20, 0.30, 0.50)

    # Optional: force all true relations to a single lag (1 or 2). None = random mix.
    forced_lag: int | None = None


def _build_territory_adjacency(n_territories: int, radius: float, rng: np.random.Generator) -> np.ndarray:
    """
    Random geometric graph adjacency in [0,1]^2 space.
    Two territories are adjacent if their Euclidean distance < radius.
    Returns row-normalized adjacency (n_T, n_T), diagonal = 0.
    """
    coords = rng.uniform(0, 1, size=(n_territories, 2))
    dists = np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(axis=-1))
    adj = (dists < radius).astype(float)
    np.fill_diagonal(adj, 0)
    # Row-normalize (avoid division by zero for isolated nodes)
    row_sum = adj.sum(axis=1, keepdims=True)
    row_sum = np.where(row_sum == 0, 1.0, row_sum)
    return adj / row_sum


def _build_true_relations(n_sectors: int, config: SyntheticConfig, rng: np.random.Generator
                           ) -> list[TrueRelation]:
    """
    Generate ground-truth directed sector→sector relations.
    No self-loops, no duplicate (source, target, lag) triples.
    """
    relations: list[TrueRelation] = []
    all_pairs = [(s, t) for s in range(n_sectors) for t in range(n_sectors) if s != t]
    selected = rng.choice(len(all_pairs), size=min(config.n_true_relations, len(all_pairs)), replace=False)

    for idx in selected:
        src, tgt = all_pairs[int(idx)]
        lag = config.forced_lag if config.forced_lag is not None else int(rng.choice([1, 2]))
        w = float(rng.uniform(*config.weight_range))
        if rng.random() < config.frac_negative:
            w = -w
        nonlin = rng.random() < config.frac_nonlinear
        relations.append(TrueRelation(src, tgt, lag, w, nonlin))

    return relations


def _sector_adj_from_relations(n_sectors: int, relations: list[TrueRelation]) -> np.ndarray:
    """Undirected binary adjacency matrix from true relations."""
    adj = np.zeros((n_sectors, n_sectors))
    for r in relations:
        adj[r.source_sector, r.target_sector] = 1
        adj[r.target_sector, r.source_sector] = 1
    return adj


def _simulate_panel(config: SyntheticConfig,
                    territory_adj: np.ndarray,
                    relations: list[TrueRelation],
                    rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """
    Simulate economic panel y (n_T, n_S, n_Y) with:
    - AR(1) per sector
    - Cross-sector effects with true relations
    - Territory propagation (same sector)
    - Crisis shock + recovery
    - Structural break

    Returns: (panel, regime_at_each_cell) where regime is an int index.
    """
    n_T = config.n_territories
    n_S = config.n_sectors
    n_Y = config.n_years

    ar_coef = rng.uniform(*config.ar_coef_range, size=n_S)
    noise_sigma = rng.uniform(*config.noise_sigma_range, size=n_S)

    # Crisis setup
    crisis_year = int(n_Y * 0.45)
    crisis_T = rng.choice(n_T, size=max(1, int(n_T * config.n_crisis_territories)), replace=False)
    crisis_S = rng.choice(n_S, size=max(1, int(n_S * config.n_crisis_sectors)), replace=False)

    # Structural break: AR coefficient changes after break year
    sb_year = config.structural_break_year or int(n_Y * 0.75)
    ar_coef_post = ar_coef * rng.uniform(0.5, 1.5, size=n_S)

    y = np.zeros((n_T, n_S, n_Y))
    # Initial values
    y[:, :, 0] = rng.normal(0.0, 0.3, size=(n_T, n_S))

    for t_idx in range(1, n_Y):
        use_ar = ar_coef if t_idx < sb_year else ar_coef_post

        for s in range(n_S):
            # AR component
            ar_term = use_ar[s] * y[:, s, t_idx - 1]

            # Cross-sector effects from true relations
            cross_term = np.zeros(n_T)
            for rel in relations:
                if rel.target_sector == s and t_idx >= rel.lag:
                    src_val = y[:, rel.source_sector, t_idx - rel.lag]
                    if rel.nonlinear:
                        cross_term += rel.weight * np.tanh(src_val)
                    else:
                        cross_term += rel.weight * src_val

            # Territory propagation (same sector, lag 1)
            territory_term = config.territory_propagation * (territory_adj @ y[:, s, t_idx - 1])

            # Crisis shock
            crisis_term = np.zeros(n_T)
            if t_idx == crisis_year and s in crisis_S:
                crisis_term[crisis_T] = -rng.uniform(0.4, 0.8, size=len(crisis_T))
            elif 0 < t_idx - crisis_year < config.crisis_duration and s in crisis_S:
                decay = 0.45 ** (t_idx - crisis_year)
                crisis_term[crisis_T] = decay * 0.4  # recovery signal

            # Noise
            noise_term = rng.normal(0, noise_sigma[s], size=n_T)

            y[:, s, t_idx] = ar_term + cross_term + territory_term + crisis_term + noise_term

    # Compute per-cell regime integer: 0=stagnation, 1=growth, 2=decline, 3=crisis, 4=recovery
    regimes = np.zeros((n_T, n_S, n_Y), dtype=np.int8)
    for t_idx in range(1, n_Y):
        growth_rate = y[:, :, t_idx] - y[:, :, t_idx - 1]  # absolute change
        global_std = y[:, :, 1:].std() + 1e-6
        g = growth_rate / global_std  # normalized
        regimes[:, :, t_idx] = np.where(g > 0.5, 1,  # growth
                                np.where(g < -0.5, 2,  # decline
                                0))  # stagnation
    # Mark crisis year
    if crisis_year < n_Y:
        regimes[np.ix_(crisis_T, crisis_S, [crisis_year])] = 3
        for k in range(1, config.crisis_duration):
            if crisis_year + k < n_Y:
                regimes[np.ix_(crisis_T, crisis_S, [crisis_year + k])] = 4

    return y, regimes


def _apply_mcar(y: np.ndarray, rate: float, rng: np.random.Generator) -> np.ndarray:
    """MCAR mask: uniform random. Returns (n_T, n_S, n_Y) int8, 1=observed."""
    return (rng.uniform(size=y.shape) >= rate).astype(np.int8)


def _apply_mar(y: np.ndarray, rate: float, rng: np.random.Generator) -> np.ndarray:
    """
    MAR mask: cells with extreme (high |y|) are more likely to be missing.
    Simulates that unusual economic activity is under-reported.
    """
    abs_y = np.abs(y)
    q75 = np.percentile(abs_y, 75)
    # Base probability of being observed
    p_obs = np.where(abs_y > q75, 1 - rate * 1.5, 1 - rate * 0.75)
    p_obs = np.clip(p_obs, 0.05, 0.99)
    return (rng.uniform(size=y.shape) < p_obs).astype(np.int8)


def _apply_block(y: np.ndarray, rate: float, rng: np.random.Generator) -> np.ndarray:
    """
    Block-temporal mask: entire (territory, year) cross-sections missing.
    Simulates that a territory has no reporting for certain years.
    """
    n_T, n_S, n_Y = y.shape
    mask = np.ones((n_T, n_S, n_Y), dtype=np.int8)
    # Number of (territory, year) blocks to mask
    n_blocks = max(1, int(n_T * n_Y * rate * 0.8))
    for _ in range(n_blocks):
        t = int(rng.integers(0, n_T))
        yr = int(rng.integers(1, n_Y))  # never mask year 0 (needed for AR initialization context)
        mask[t, :, yr] = 0
    return mask


def generate_dataset(config: SyntheticConfig) -> dict:
    """
    Generate a fully-labelled synthetic economic panel.

    Returns dict with:
        panel: (n_T, n_S, n_Y) float64 — true values
        regimes: (n_T, n_S, n_Y) int8 — 0=stagnation,1=growth,2=decline,3=crisis,4=recovery
        territory_adj: (n_T, n_T) float64 — row-normalized adjacency
        sector_adj: (n_S, n_S) float64 — binary adjacency from relations
        true_relations: list[TrueRelation] — ground truth sector-sector structure
        masks: dict str → (n_T, n_S, n_Y) int8 (1=observed, 0=hidden)
            keys: mcar_10, mcar_20, mcar_30, mar_20, block_20
        config: SyntheticConfig
    """
    rng = np.random.default_rng(config.seed)

    territory_adj = _build_territory_adjacency(config.n_territories, config.territory_radius, rng)
    relations = _build_true_relations(config.n_sectors, config, rng)
    sector_adj = _sector_adj_from_relations(config.n_sectors, relations)
    panel, regimes = _simulate_panel(config, territory_adj, relations, rng)

    # Build masks — separate rng states so masks don't correlate
    masks = {}
    for rate in config.mcar_rates:
        masks[f"mcar_{int(rate*100):02d}"] = _apply_mcar(panel, rate, np.random.default_rng(config.seed + 100 + int(rate * 100)))
    for rate in config.mar_rates:
        masks[f"mar_{int(rate*100):02d}"] = _apply_mar(panel, rate, np.random.default_rng(config.seed + 200 + int(rate * 100)))
    for rate in config.block_rates:
        masks[f"block_{int(rate*100):02d}"] = _apply_block(panel, rate, np.random.default_rng(config.seed + 300 + int(rate * 100)))

    return {
        "panel": panel,
        "regimes": regimes,
        "territory_adj": territory_adj,
        "sector_adj": sector_adj,
        "true_relations": relations,
        "masks": masks,
        "config": config,
    }


def mask_panel(panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return panel with NaN at unobserved cells (mask=0)."""
    out = panel.copy()
    out[mask == 0] = np.nan
    return out


# ── Benchmark scenario registry ───────────────────────────────────────────────
# Full-scale configs for HPC (30T × 9S × 20Y).
# Seed is overridden per-task; only structural parameters are fixed here.

BENCHMARK_SCENARIOS: dict[str, SyntheticConfig] = {
    "linear": SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0,  # overridden per task
        n_true_relations=8,
        frac_nonlinear=0.0,       # ALL relations are linear
        frac_negative=0.4,
        noise_sigma_range=(0.08, 0.18),
        ar_coef_range=(0.3, 0.6),
        territory_propagation=0.15,
        territory_radius=0.35,
    ),
    "nonlinear_heavy": SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0,
        n_true_relations=8,
        frac_nonlinear=0.8,       # 80% nonlinear relations
        frac_negative=0.4,
        noise_sigma_range=(0.08, 0.18),
        ar_coef_range=(0.3, 0.6),
        territory_propagation=0.15,
        territory_radius=0.35,
    ),
    "mixed_default": SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0,
        n_true_relations=8,
        frac_nonlinear=0.3,       # 30% nonlinear (default mix)
        frac_negative=0.4,
        noise_sigma_range=(0.10, 0.25),
        ar_coef_range=(0.3, 0.6),
        territory_propagation=0.15,
        territory_radius=0.35,
    ),
    "generalization": SyntheticConfig(
        # Qualitatively different dynamics to test structural generalization.
        # Higher nonlinearity + higher noise + higher territory propagation
        # + denser true relations + different AR range.
        n_territories=30, n_sectors=9, n_years=20,
        seed=0,
        n_true_relations=12,
        frac_nonlinear=0.6,
        frac_negative=0.5,
        noise_sigma_range=(0.15, 0.35),   # higher noise than other scenarios
        ar_coef_range=(0.2, 0.7),          # wider AR range
        territory_propagation=0.25,        # stronger cross-territory signal
        territory_radius=0.28,             # sparser territory graph
    ),
}

# Pilot-scale configs (20T × 7S × 16Y, ≈2× faster than full).
PILOT_SCENARIOS: dict[str, SyntheticConfig] = {
    k: dataclasses.replace(v, n_territories=20, n_sectors=7, n_years=16)
    for k, v in BENCHMARK_SCENARIOS.items()
}

# Full benchmark grid
BENCHMARK_SEEDS = [42, 123, 456, 789, 1337]
PILOT_SEEDS = [42, 123, 456]
BENCHMARK_MASK_TYPES = ["mcar", "mar", "block"]
BENCHMARK_MASK_LEVELS = [10, 30, 50]  # percent
