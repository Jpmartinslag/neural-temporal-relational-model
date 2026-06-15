"""
dec055_environments.py — Multi-environment synthetic data for DEC-055.

Creates varied environments with different:
  - Crisis timing (year 3, 5, 7, 10 of a 20-year panel)
  - Crisis intensity (low=0.3, medium=0.6, high=0.9)
  - Lag patterns (lag1-only, lag2-only, mixed)
  - Nonlinearity (0%, 50%, 100%)
  - Missing data (MCAR 10%, 30%, 50%; block)

Split:
  Train (5 envs): varied but "canonical" configurations
  OOS envs (3 envs): different crisis years, unseen parameter regimes
  Unseen pairs: for each env, hold out a fraction of true edges from the
                training loss (labels withheld, but panel includes their signal)

No fine-tuning on test data. No target in encoder inputs.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

import numpy as np

from src.data.synthetic.generate_herald_synthetic import (
    SyntheticConfig,
    TrueRelation,
    generate_dataset,
)


@dataclasses.dataclass
class EnvConfig:
    """Configuration for one synthetic environment."""
    env_id: str
    seed: int
    n_territories: int = 10
    n_sectors: int = 6
    n_years: int = 20
    n_true_relations: int = 5
    crisis_year_offset: int = 5          # year of crisis start
    crisis_intensity: float = 0.6        # multiplier on crisis effect
    forced_lag: Optional[int] = None     # None=mixed, 1=lag1-only, 2=lag2-only
    frac_nonlinear: float = 0.3
    frac_negative: float = 0.4
    mcar_rate: float = 0.25
    block_missing: bool = False          # add block-temporal masking


# ── Frozen environment configurations ─────────────────────────────────────────

TRAIN_ENV_CONFIGS: list[EnvConfig] = [
    # Env 0: Medium crisis (year 5), mixed lags, low nonlinearity
    EnvConfig("T0", seed=1001, crisis_year_offset=5, crisis_intensity=0.6,
              forced_lag=None, frac_nonlinear=0.2, mcar_rate=0.20),
    # Env 1: Early crisis (year 3), lag1-only, moderate nonlinearity
    EnvConfig("T1", seed=1002, crisis_year_offset=3, crisis_intensity=0.5,
              forced_lag=1, frac_nonlinear=0.4, mcar_rate=0.25),
    # Env 2: Late crisis (year 10), lag2-only, low nonlinearity
    EnvConfig("T2", seed=1003, crisis_year_offset=10, crisis_intensity=0.7,
              forced_lag=2, frac_nonlinear=0.1, mcar_rate=0.30),
    # Env 3: Strong crisis (year 7), mixed lags, high nonlinearity
    EnvConfig("T3", seed=1004, crisis_year_offset=7, crisis_intensity=0.9,
              forced_lag=None, frac_nonlinear=0.6, mcar_rate=0.25),
    # Env 4: Weak crisis (year 5), lag1-only, moderate missing
    EnvConfig("T4", seed=1005, crisis_year_offset=5, crisis_intensity=0.3,
              forced_lag=1, frac_nonlinear=0.3, mcar_rate=0.40),
]

OOS_ENV_CONFIGS: list[EnvConfig] = [
    # OOS 0: Very early crisis (year 2) — unseen timing
    EnvConfig("O0", seed=9001, crisis_year_offset=2, crisis_intensity=0.5,
              forced_lag=None, frac_nonlinear=0.5, mcar_rate=0.20),
    # OOS 1: Very late crisis (year 14) — unseen timing
    EnvConfig("O1", seed=9002, crisis_year_offset=14, crisis_intensity=0.8,
              forced_lag=2, frac_nonlinear=0.3, mcar_rate=0.30),
    # OOS 2: Dual crisis (approximate: different intensity) — unseen regime
    EnvConfig("O2", seed=9003, crisis_year_offset=8, crisis_intensity=1.0,
              forced_lag=None, frac_nonlinear=0.8, mcar_rate=0.35),
]


def _crisis_adj_structural_break(config: SyntheticConfig, env: EnvConfig) -> SyntheticConfig:
    """Adjust SyntheticConfig to encode crisis timing via structural_break_year."""
    return dataclasses.replace(
        config,
        structural_break_year=env.crisis_year_offset,
        n_crisis_territories=0.4 + 0.1 * env.crisis_intensity,
        n_crisis_sectors=0.5,
    )


def build_environment(env: EnvConfig) -> dict:
    """
    Generate one synthetic environment.
    Returns dict with: panel, obs_mask, true_relations, sector_adj, env_id, env_config.
    """
    cfg = SyntheticConfig(
        seed=env.seed,
        n_territories=env.n_territories,
        n_sectors=env.n_sectors,
        n_years=env.n_years,
        n_true_relations=env.n_true_relations,
        frac_nonlinear=env.frac_nonlinear,
        frac_negative=env.frac_negative,
        forced_lag=env.forced_lag,
        structural_break_year=env.crisis_year_offset,
        n_crisis_territories=0.35 + 0.15 * env.crisis_intensity,
        n_crisis_sectors=0.5,
        mcar_rates=(env.mcar_rate,),
        mar_rates=(env.mcar_rate * 0.5,),
        block_rates=(0.10,) if env.block_missing else (0.0,),
    )
    data = generate_dataset(cfg)
    rng = np.random.default_rng(env.seed + 999)
    obs_mask = (rng.random(data["panel"].shape) > env.mcar_rate).astype(np.float32)

    return {
        "panel": data["panel"],
        "obs_mask": obs_mask,
        "true_relations": data["true_relations"],
        "sector_adj": data.get("sector_adj"),
        "env_id": env.env_id,
        "env_config": env,
        "n_sectors": env.n_sectors,
        "n_territories": env.n_territories,
        "n_years": env.n_years,
    }


def split_pairs_train_oos(
    true_relations: list,
    n_sectors: int,
    holdout_frac: float = 0.30,
    rng: Optional[np.random.Generator] = None,
) -> tuple[list, list]:
    """
    Split true_relations into train_relations (used in loss) and oos_relations (held out).
    OOS relations: labels withheld from training but their influence is in the panel.

    Returns: (train_relations, oos_relations)
    """
    if rng is None:
        rng = np.random.default_rng(42)
    n = len(true_relations)
    if n == 0:
        return [], []
    idx = rng.permutation(n)
    n_oos = max(1, int(n * holdout_frac))
    oos_idx = set(idx[:n_oos].tolist())
    train_rels = [r for i, r in enumerate(true_relations) if i not in oos_idx]
    oos_rels = [r for i, r in enumerate(true_relations) if i in oos_idx]
    return train_rels, oos_rels


def build_all_environments(seed_offset: int = 0, holdout_frac: float = 0.30) -> dict:
    """
    Build all training and OOS environments.
    For each training env: split true_relations into train/oos for pair generalization test.
    Returns:
      train_envs: list of dicts with train_relations and oos_relations
      oos_envs: list of dicts (all relations are OOS)
    """
    rng = np.random.default_rng(42 + seed_offset)

    train_envs = []
    for env_cfg in TRAIN_ENV_CONFIGS:
        env_data = build_environment(env_cfg)
        train_rels, oos_rels = split_pairs_train_oos(
            env_data["true_relations"],
            env_data["n_sectors"],
            holdout_frac=holdout_frac,
            rng=rng,
        )
        env_data["train_relations"] = train_rels
        env_data["oos_relations"] = oos_rels
        train_envs.append(env_data)

    oos_envs = []
    for env_cfg in OOS_ENV_CONFIGS:
        env_data = build_environment(env_cfg)
        env_data["train_relations"] = []       # not used in training
        env_data["oos_relations"] = env_data["true_relations"]
        oos_envs.append(env_data)

    return {"train_envs": train_envs, "oos_envs": oos_envs}


def permute_relations(true_relations: list, n_sectors: int, rng: np.random.Generator) -> list:
    """
    Permute sector indices in true_relations (both source and target).
    Used for the permuted-relations control (S8).
    """
    perm = rng.permutation(n_sectors)
    permuted = []
    for r in true_relations:
        permuted.append(TrueRelation(
            source_sector=int(perm[r.source_sector]),
            target_sector=int(perm[r.target_sector]),
            lag=r.lag,
            weight=r.weight,
            nonlinear=r.nonlinear,
        ))
    return permuted


def permute_pair_labels(true_relations: list, n_sectors: int, rng: np.random.Generator) -> list:
    """
    Keep relation properties (lag, weight) but assign random sector pairs.
    Used for the permuted-pair-labels control (S8).
    """
    all_pairs = [(s, t) for s in range(n_sectors) for t in range(n_sectors) if s != t]
    n = len(true_relations)
    chosen_pairs = [all_pairs[i] for i in rng.choice(len(all_pairs), size=n, replace=False)]
    permuted = []
    for r, (s, t) in zip(true_relations, chosen_pairs):
        permuted.append(TrueRelation(
            source_sector=s,
            target_sector=t,
            lag=r.lag,
            weight=r.weight,
            nonlinear=r.nonlinear,
        ))
    return permuted
