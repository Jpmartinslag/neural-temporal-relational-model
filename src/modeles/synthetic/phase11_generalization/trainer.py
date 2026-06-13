"""
trainer.py — Multi-dataset trainer for Phase 11 generalization (DEC-045)

Two training strategies:
  T1 (single-family) : train on "linear" scenario only
  T2 (multi-environment): train on "linear" + "mixed_default"

Architecture: HERALDGraphImputerLagged(n_sectors=9, n_territories=30) — shared weights
Early stopping: val loss (mean NLL over nonlinear_heavy datasets, patience=20)

Key invariants:
  - Normalization: none (not computed on test data; model is not normalized)
  - No optimizer state is created at evaluation time
  - Checkpoint saved before any test evaluation
  - train() returns (model, history) where history carries the best val epoch

Usage:
    from src.modeles.synthetic.phase11_generalization.trainer import train_strategy
    model, history = train_strategy("T2", pilot=True, device="cuda")
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[4]

import sys
sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_herald_synthetic import (
    BENCHMARK_SCENARIOS,
    generate_dataset,
    mask_panel,
)
from src.modeles.synthetic.herald_graph_imputer import _prep_tensors, _apply_observed
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    train_herald_lagged,
)
from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.phase11_generalization.splits import (
    TRAIN_SCENARIO_NAMES,
    VAL_SCENARIO_NAME,
    NOVEL_TEST_SCENARIOS,
    TRAIN_SEEDS,
    VAL_SEEDS,
    PILOT_TRAIN_SEEDS,
    PILOT_VAL_SEEDS,
    TRAIN_MASK_KEYS,
    VAL_MASK_KEY,
)

# ── Constants ─────────────────────────────────────────────────────────────────

N_SECTORS = 9
N_TERRITORIES = 30
HIDDEN_DIM = 64
DROPOUT = 0.1
DEFAULT_LR = 1e-3
DEFAULT_EPOCHS = 150
DEFAULT_PATIENCE = 20

STRATEGY_SCENARIOS: dict[str, list[str]] = {
    "T1": ["linear"],
    "T2": ["linear", "mixed_default"],
}


# ── Single-dataset NLL loss ───────────────────────────────────────────────────

def _compute_nll_loss(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> torch.Tensor:
    """NLL on observed cells only (same loss as train_herald_lagged)."""
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    ).to(device)

    out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    log_sigma = out[..., 1]
    sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
    nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
    return (nll * mask_t).sum() / mask_t.sum().clamp(min=1)


def checkpoint_hash(state_dict: dict) -> str:
    """MD5 of serialized model state; verifies checkpoint integrity."""
    h = hashlib.md5()
    for k in sorted(state_dict.keys()):
        h.update(k.encode())
        h.update(state_dict[k].cpu().numpy().astype(np.float32).tobytes())
    return h.hexdigest()


# ── Multi-dataset trainer ─────────────────────────────────────────────────────

def train_multi_dataset(
    train_entries: list[dict],
    val_entries: list[dict],
    n_epochs: int = DEFAULT_EPOCHS,
    lr: float = DEFAULT_LR,
    patience: int = DEFAULT_PATIENCE,
    device: str = "cpu",
    seed: int = 0,
) -> tuple[HERALDGraphImputerLagged, dict]:
    """
    Train one HERALDGraphImputerLagged on multiple datasets (shared weights).

    Each epoch: shuffle train_entries, compute NLL + backward for each mini-dataset.
    Early stopping on mean val NLL (patience epochs without improvement).

    Returns (best_model, history) where history contains per-epoch losses and
    a checkpoint_hash for integrity verification before evaluation.

    INVARIANT: no optimizer step is called during val evaluation.
    """
    rng = np.random.default_rng(seed)
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    best_val = float("inf")
    best_state: dict | None = None
    no_improve = 0
    train_losses: list[float] = []
    val_losses: list[float] = []
    best_epoch = 0

    for epoch in range(n_epochs):
        # Train
        model.train()
        order = rng.permutation(len(train_entries))
        ep_loss = 0.0
        for idx in order:
            e = train_entries[int(idx)]
            opt.zero_grad()
            loss = _compute_nll_loss(model, e["panel"], e["mask"], e["adj_s"], e["adj_t"], device)
            loss.backward()
            opt.step()
            ep_loss += float(loss)
        train_losses.append(ep_loss / max(len(train_entries), 1))

        # Validation — no grad, no optimizer
        model.eval()
        with torch.no_grad():
            vl = [
                float(_compute_nll_loss(model, e["panel"], e["mask"], e["adj_s"], e["adj_t"], device))
                for e in val_entries
            ]
        val_loss = float(np.mean(vl))
        val_losses.append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = copy.deepcopy(model.state_dict())
            no_improve = 0
            best_epoch = epoch
        else:
            no_improve += 1
        if no_improve >= patience:
            break

    assert best_state is not None, "No improvement in any epoch"
    model.load_state_dict(best_state)
    model.eval()

    c_hash = checkpoint_hash(model.state_dict())

    return model, {
        "n_epochs_run": len(train_losses),
        "best_epoch": best_epoch,
        "best_val_loss": float(best_val),
        "train_losses": train_losses,
        "val_losses": val_losses,
        "checkpoint_hash": c_hash,
        "n_train_entries": len(train_entries),
        "n_val_entries": len(val_entries),
    }


def save_checkpoint(model: HERALDGraphImputerLagged, path: Path) -> str:
    """Save model state_dict and return its MD5 hash."""
    state = model.state_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, path)
    return checkpoint_hash(state)


def load_checkpoint(path: Path, device: str = "cpu") -> HERALDGraphImputerLagged:
    """Load model from checkpoint path. Model is set to eval mode."""
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    state = torch.load(path, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model


# ── Strategy factory ──────────────────────────────────────────────────────────

def make_train_entries(
    strategy: str,
    seeds: list[int],
    mask_keys: list[str] = TRAIN_MASK_KEYS,
) -> list[dict]:
    """
    Build list of mini-dataset dicts for multi-dataset training.
    strategy: "T1" (linear only) or "T2" (linear + mixed_default).
    """
    scenario_names = STRATEGY_SCENARIOS[strategy]
    entries = []
    for scenario_name in scenario_names:
        base = BENCHMARK_SCENARIOS[scenario_name]
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
                })
    return entries


def make_val_entries(
    seeds: list[int],
    mask_key: str = VAL_MASK_KEY,
) -> list[dict]:
    """Build list of mini-dataset dicts for validation (nonlinear_heavy)."""
    base = BENCHMARK_SCENARIOS[VAL_SCENARIO_NAME]
    entries = []
    for seed in seeds:
        cfg = dataclasses.replace(base, seed=seed)
        ds = generate_dataset(cfg)
        if mask_key not in ds["masks"]:
            return entries
        entries.append({
            "panel": ds["panel"],
            "mask": ds["masks"][mask_key],
            "adj_s": ds["sector_adj"],
            "adj_t": ds["territory_adj"],
            "true_relations": ds["true_relations"],
            "scenario": VAL_SCENARIO_NAME,
            "seed": seed,
            "mask_key": mask_key,
        })
    return entries


def train_strategy(
    strategy: str,
    pilot: bool = False,
    n_epochs: int = DEFAULT_EPOCHS,
    lr: float = DEFAULT_LR,
    patience: int = DEFAULT_PATIENCE,
    device: str = "cpu",
    rng_seed: int = 7,
) -> tuple[HERALDGraphImputerLagged, dict]:
    """
    Top-level training entry point.

    strategy : "T1" or "T2"
    pilot    : if True, use PILOT_TRAIN_SEEDS / PILOT_VAL_SEEDS (3+1 seeds)
    """
    assert strategy in STRATEGY_SCENARIOS, f"Unknown strategy: {strategy}"
    train_seeds = PILOT_TRAIN_SEEDS if pilot else TRAIN_SEEDS
    val_seeds = PILOT_VAL_SEEDS if pilot else VAL_SEEDS
    train_entries = make_train_entries(strategy, train_seeds)
    val_entries = make_val_entries(val_seeds)
    assert len(train_entries) > 0, "No train entries"
    assert len(val_entries) > 0, "No val entries"
    model, history = train_multi_dataset(
        train_entries, val_entries,
        n_epochs=n_epochs, lr=lr, patience=patience,
        device=device, seed=rng_seed,
    )
    history["strategy"] = strategy
    history["pilot"] = pilot
    history["train_seeds"] = train_seeds
    history["val_seeds"] = val_seeds
    return model, history
