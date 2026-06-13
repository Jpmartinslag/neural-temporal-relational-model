"""
splits.py — Phase 11 dataset split definitions (DEC-045)

Frozen split protocol:
  TRAIN  : "linear" + "mixed_default" scenarios, seeds TRAIN_SEEDS
  VAL    : "nonlinear_heavy" scenario, seeds VAL_SEEDS (early stopping only)
  TEST   : "novel_lag2" + "novel_highvar" scenarios, seeds TEST_SEEDS (frozen, never seen)

Disjoint guarantee:
  TRAIN_SEEDS ∩ VAL_SEEDS ∩ TEST_SEEDS = ∅
  TEST scenarios are NOT in BENCHMARK_SCENARIOS and NOT used in Phase 10

Novel test scenario properties (vs train):
  novel_lag2  : frac_nonlinear=0.85 (vs 0.0-0.3), forced_lag=2, sparser territory
  novel_highvar: frac_nonlinear=0.90, high noise, strong territory propagation, structural break

Seeds chosen to be disjoint from:
  - Phase 9/10 BENCHMARK_SEEDS [42, 123, 456, 789, 1337]
  - OFAT seeds [42, 123, 456]

DO NOT modify seeds or scenario configs after first pilot execution.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

import numpy as np

from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset

# ── Frozen split seeds ────────────────────────────────────────────────────────

TRAIN_SEEDS: list[int] = [10, 20, 30, 40, 50]
VAL_SEEDS: list[int] = [100, 200, 300]
TEST_SEEDS: list[int] = [1000, 2000, 3000, 4000, 5000]

# Pilot subsets (3/1/3 seeds)
PILOT_TRAIN_SEEDS: list[int] = [10, 20, 30]
PILOT_VAL_SEEDS: list[int] = [100]
PILOT_TEST_SEEDS: list[int] = [1000, 2000, 3000]

# ── Training scenario names (used from BENCHMARK_SCENARIOS) ──────────────────

TRAIN_SCENARIO_NAMES: list[str] = ["linear", "mixed_default"]
VAL_SCENARIO_NAME: str = "nonlinear_heavy"

# ── Novel test scenario configs ───────────────────────────────────────────────
# These are NOT added to BENCHMARK_SCENARIOS. They are frozen here.
# Key differences from training:
#   - frac_nonlinear >> max_train (0.0-0.3) → 0.85-0.90
#   - forced_lag=2 (novel_lag2) vs mixed during training
#   - territory_radius differs from train (0.35) → 0.25 or 0.42
#   - ar_coef_range, noise_sigma_range, territory_propagation all shifted

NOVEL_TEST_SCENARIOS: dict[str, SyntheticConfig] = {
    "novel_lag2": SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0,  # overridden per task
        n_true_relations=10,           # more than train (8)
        frac_nonlinear=0.85,           # predominantly nonlinear (train max: 0.30)
        frac_negative=0.55,            # different positive/negative balance
        noise_sigma_range=(0.12, 0.28),  # different noise range vs train (0.08-0.25)
        ar_coef_range=(0.20, 0.50),    # different AR range vs train (0.30-0.60)
        territory_propagation=0.20,    # different from train (0.15)
        territory_radius=0.25,         # sparser territory (train: 0.35)
        forced_lag=2,                  # lag-2 dominant (train: mixed)
    ),
    "novel_highvar": SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0,
        n_true_relations=12,           # denser cross-sector structure
        frac_nonlinear=0.90,           # almost all nonlinear
        frac_negative=0.30,            # fewer dampening relations
        noise_sigma_range=(0.18, 0.38),  # higher noise
        ar_coef_range=(0.35, 0.70),    # extended AR range
        territory_propagation=0.28,    # stronger territory signal
        territory_radius=0.42,         # denser territory topology (train: 0.35)
        structural_break_year=8,       # earlier structural break (train: ~15)
        forced_lag=None,               # mixed lag — but all else novel
    ),
}

TEST_SCENARIO_NAMES: list[str] = list(NOVEL_TEST_SCENARIOS.keys())

# ── Training mask keys ────────────────────────────────────────────────────────

TRAIN_MASK_KEYS: list[str] = ["mcar_30", "block_30"]
VAL_MASK_KEY: str = "mcar_30"
PILOT_TEST_MASK_KEYS: list[str] = ["mcar_30", "block_30"]
FULL_TEST_MASK_KEYS: list[str] = ["mcar_10", "mcar_30", "mcar_50", "mar_30",
                                   "block_10", "block_30", "block_50"]


# ── Disjoint verification ─────────────────────────────────────────────────────

def verify_disjoint() -> None:
    """Assert that TRAIN, VAL, TEST seed sets are fully disjoint."""
    train_set = set(TRAIN_SEEDS)
    val_set = set(VAL_SEEDS)
    test_set = set(TEST_SEEDS)
    benchmark_seeds = {42, 123, 456, 789, 1337}  # Phase 9/10
    ofat_seeds = {42, 123, 456}                   # OFAT

    assert train_set & val_set == set(), f"Train/Val overlap: {train_set & val_set}"
    assert train_set & test_set == set(), f"Train/Test overlap: {train_set & test_set}"
    assert val_set & test_set == set(), f"Val/Test overlap: {val_set & test_set}"
    assert train_set & benchmark_seeds == set(), f"Train overlaps Phase 9/10 seeds"
    assert val_set & benchmark_seeds == set(), f"Val overlaps Phase 9/10 seeds"
    assert test_set & benchmark_seeds == set(), f"Test overlaps Phase 9/10 seeds"
    assert test_set & ofat_seeds == set(), f"Test overlaps OFAT seeds"

    pilot_train = set(PILOT_TRAIN_SEEDS)
    pilot_val = set(PILOT_VAL_SEEDS)
    pilot_test = set(PILOT_TEST_SEEDS)
    assert pilot_train <= train_set, "Pilot train seeds not subset of TRAIN_SEEDS"
    assert pilot_val <= val_set, "Pilot val seeds not subset of VAL_SEEDS"
    assert pilot_test <= test_set, "Pilot test seeds not subset of TEST_SEEDS"


# ── Scenario novelty verification ─────────────────────────────────────────────

def verify_novel_test_dynamics() -> None:
    """Assert test scenarios are genuinely more nonlinear than training scenarios."""
    from src.data.synthetic.generate_herald_synthetic import BENCHMARK_SCENARIOS

    max_train_nonlinear = max(
        BENCHMARK_SCENARIOS[s].frac_nonlinear for s in TRAIN_SCENARIO_NAMES
    )
    for name, cfg in NOVEL_TEST_SCENARIOS.items():
        assert cfg.frac_nonlinear > max_train_nonlinear, (
            f"{name}: frac_nonlinear={cfg.frac_nonlinear} must exceed "
            f"train max={max_train_nonlinear}"
        )

    # novel_lag2 must have forced_lag=2
    assert NOVEL_TEST_SCENARIOS["novel_lag2"].forced_lag == 2, \
        "novel_lag2 must have forced_lag=2"

    # territory_radius must differ from all training scenarios
    train_radii = {BENCHMARK_SCENARIOS[s].territory_radius for s in TRAIN_SCENARIO_NAMES}
    for name, cfg in NOVEL_TEST_SCENARIOS.items():
        assert cfg.territory_radius not in train_radii, (
            f"{name}: territory_radius={cfg.territory_radius} conflicts with training"
        )


# ── Dataset checksum ──────────────────────────────────────────────────────────

def dataset_checksum(ds: dict) -> str:
    """MD5 of panel + true_relations; deterministic given (config, seed)."""
    h = hashlib.md5()
    h.update(ds["panel"].astype(np.float64).tobytes())
    for rel in ds["true_relations"]:
        h.update(f"{rel.source_sector},{rel.target_sector},{rel.lag},{rel.weight},{rel.nonlinear}".encode())
    return h.hexdigest()


def build_split_manifest(
    train_seeds: list[int] | None = None,
    val_seeds: list[int] | None = None,
    test_seeds: list[int] | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    """
    Generate all split datasets and compute checksums.
    Returns manifest dict with checksums for disjoint verification.
    Does NOT return the raw datasets (caller generates them on demand).
    """
    from src.data.synthetic.generate_herald_synthetic import BENCHMARK_SCENARIOS

    if verify:
        verify_disjoint()
        verify_novel_test_dynamics()

    train_seeds = train_seeds or TRAIN_SEEDS
    val_seeds = val_seeds or VAL_SEEDS
    test_seeds = test_seeds or TEST_SEEDS

    manifest: dict[str, Any] = {
        "protocol_version": "phase11_v1",
        "train_scenarios": TRAIN_SCENARIO_NAMES,
        "val_scenario": VAL_SCENARIO_NAME,
        "test_scenarios": TEST_SCENARIO_NAMES,
        "train_seeds": train_seeds,
        "val_seeds": val_seeds,
        "test_seeds": test_seeds,
        "checksums": {},
    }

    # Train checksums
    for scenario_name in TRAIN_SCENARIO_NAMES:
        base = BENCHMARK_SCENARIOS[scenario_name]
        for seed in train_seeds:
            cfg = dataclasses.replace(base, seed=seed)
            ds = generate_dataset(cfg)
            key = f"train/{scenario_name}/seed={seed}"
            manifest["checksums"][key] = dataset_checksum(ds)

    # Val checksums
    base_val = BENCHMARK_SCENARIOS[VAL_SCENARIO_NAME]
    for seed in val_seeds:
        cfg = dataclasses.replace(base_val, seed=seed)
        ds = generate_dataset(cfg)
        key = f"val/{VAL_SCENARIO_NAME}/seed={seed}"
        manifest["checksums"][key] = dataset_checksum(ds)

    # Test checksums
    for scenario_name, base_cfg in NOVEL_TEST_SCENARIOS.items():
        for seed in test_seeds:
            cfg = dataclasses.replace(base_cfg, seed=seed)
            ds = generate_dataset(cfg)
            key = f"test/{scenario_name}/seed={seed}"
            manifest["checksums"][key] = dataset_checksum(ds)

    return manifest


def load_split_datasets(
    split: str,
    scenario_names: list[str],
    base_configs: dict[str, SyntheticConfig],
    seeds: list[str],
    mask_keys: list[str],
) -> list[dict]:
    """
    Generate a list of mini-datasets for training/validation/evaluation.
    Each entry: {panel, mask, adj_s, adj_t, true_relations, scenario, seed, mask_key, split}
    """
    from src.data.synthetic.generate_herald_synthetic import BENCHMARK_SCENARIOS
    entries = []
    for scenario_name in scenario_names:
        base = base_configs[scenario_name]
        for seed in seeds:
            cfg = dataclasses.replace(base, seed=seed)
            ds = generate_dataset(cfg)
            for mk in mask_keys:
                if mk not in ds["masks"]:
                    continue
                entries.append({
                    "panel": ds["panel"],
                    "mask": ds["masks"][mk],
                    "adj_s": ds["sector_adj"],
                    "adj_t": ds["territory_adj"],
                    "true_relations": ds["true_relations"],
                    "scenario": scenario_name,
                    "seed": seed,
                    "mask_key": mk,
                    "split": split,
                    "checksum": dataset_checksum(ds),
                })
    return entries


# Run disjoint check at import time (catches programming errors)
verify_disjoint()
verify_novel_test_dynamics()
