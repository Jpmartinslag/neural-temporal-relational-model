"""
pretrain_runner_v2.py — Stable pretraining with clamped NLL or Huber loss (DEC-051).

Variants compared:
  TEMPORAL_MASKED_NLL_CLAMPED   — masked NLL with log_sigma clamped to [-3, 2]
  TEMPORAL_MASKED_HUBER         — masked Huber loss (no variance head)
  GRAPH_MULTITASK_NLL_CLAMPED   — TEMPORAL_MASKED_NLL_CLAMPED + independent graph heads
  GRAPH_MULTITASK_HUBER         — TEMPORAL_MASKED_HUBER + independent graph heads
  NO_PRETRAINING                — Phase 11 T2 checkpoint (reference, no new training)

D2 dataset generation unchanged from DEC-049/050 (seeds 200-249, frac_nonlinear~U[0,0.9]).
Val loss validation unchanged (nonlinear_heavy, seeds 100/200/300, mcar_30).

All constants FROZEN before execution:
  LOG_SIGMA_MIN = -3.0, LOG_SIGMA_MAX = 2.0
  SIGMA_ENTROPY_LAMBDA = 0.001
  HUBER_DELTA = 1.0
  GRAPH_ALPHA = 0.10, GRAPH_BETA = 0.05, GRAPH_GAMMA = 0.05
  N_PRETRAIN_DATASETS = 50, EPOCH_BUDGETS = [30, 75, 150]
  EXTRA_MASK_RATE = 0.40  (fraction of observed cells hidden per step)
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from src.data.synthetic.generate_herald_synthetic import (
    SyntheticConfig,
    BENCHMARK_SCENARIOS,
    generate_dataset,
)
from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.phase11_generalization.trainer import (
    _compute_nll_loss,
    checkpoint_hash as _checkpoint_hash_from_state,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase11_generalization.splits import TEST_SEEDS
from src.modeles.synthetic.phase15_stable_objective.loss_functions import (
    masked_nll_clamped,
    masked_huber,
    masked_mse,
    LOG_SIGMA_MIN,
    LOG_SIGMA_MAX,
    log_sigma_stats,
)
from src.modeles.synthetic.phase15_stable_objective.graph_heads import (
    GraphAuxHeads,
    GRAPH_ALPHA,
    GRAPH_BETA,
    GRAPH_GAMMA,
)

def checkpoint_hash(path: Path) -> str:
    """MD5 hash of a saved checkpoint file (given as Path)."""
    state = torch.load(path, map_location="cpu")
    return _checkpoint_hash_from_state(state)


# ── Frozen constants ───────────────────────────────────────────────────────────
EPOCH_BUDGETS: list[int] = [30, 75, 150]
N_PRETRAIN_DATASETS: int = 50
D2_SEED_START: int = 200
D2_NL_MIN: float = 0.0
D2_NL_MAX: float = 0.9
EXTRA_MASK_RATE: float = 0.40

VAL_SCENARIO: str = "nonlinear_heavy"
VAL_SEEDS: list[int] = [100, 200, 300]
VAL_MASK_KEY: str = "mcar_30"

PHASE11_T2_CHECKPOINT: Path = Path(
    "data/processed/synthetic_benchmark/phase11_pilot/model_T2_pilot.pt"
)

PRETRAIN_VARIANTS: list[str] = [
    "NO_PRETRAINING",
    "TEMPORAL_MASKED_NLL_CLAMPED",
    "TEMPORAL_MASKED_HUBER",
    "GRAPH_MULTITASK_NLL_CLAMPED",
    "GRAPH_MULTITASK_HUBER",
]


def verify_d2_seeds_disjoint(seeds: list[int]) -> None:
    test_seeds_set = set(TEST_SEEDS) | set(range(1000, 5001))
    overlap = set(seeds) & test_seeds_set
    if overlap:
        raise ValueError(f"D2 seeds overlap with TEST_SEEDS: {overlap}")
    novel_seeds = {1000, 2000, 3000, 4000, 5000}
    overlap2 = set(seeds) & novel_seeds
    if overlap2:
        raise ValueError(f"D2 seeds overlap with novel test seeds: {overlap2}")


def generate_d2_datasets(
    n_datasets: int,
    seed_start: int = D2_SEED_START,
    mask_keys: tuple[str, ...] = ("mcar_30", "block_30"),
) -> list[dict]:
    seeds = list(range(seed_start, seed_start + n_datasets))
    verify_d2_seeds_disjoint(seeds)
    rng = np.random.default_rng(888 + seed_start)
    entries = []
    for seed in seeds:
        frac_nl = float(rng.uniform(D2_NL_MIN, D2_NL_MAX))
        t_radius = float(rng.uniform(0.28, 0.38))
        terr_prop = float(rng.uniform(0.10, 0.22))
        cfg = SyntheticConfig(
            n_territories=30, n_sectors=9, n_years=20,
            seed=seed, n_true_relations=8,
            frac_nonlinear=frac_nl,
            frac_negative=float(rng.uniform(0.30, 0.50)),
            noise_sigma_range=(0.08, 0.25),
            ar_coef_range=(0.25, 0.60),
            territory_propagation=terr_prop,
            territory_radius=t_radius,
            forced_lag=None, structural_break_year=None,
        )
        ds = generate_dataset(cfg)
        for mk in mask_keys:
            if mk in ds["masks"]:
                entries.append({
                    "panel": ds["panel"],
                    "mask": ds["masks"][mk],
                    "adj_s": ds["sector_adj"],
                    "adj_t": ds["territory_adj"],
                    "true_relations": ds["true_relations"],
                    "scenario": f"d2_nl_{frac_nl:.2f}",
                    "seed": seed,
                    "mask_key": mk,
                    "frac_nonlinear": frac_nl,
                })
    return entries


def _build_val_entries() -> list[dict]:
    base = BENCHMARK_SCENARIOS[VAL_SCENARIO]
    entries = []
    for seed in VAL_SEEDS:
        cfg = dataclasses.replace(base, seed=seed)
        ds = generate_dataset(cfg)
        if VAL_MASK_KEY in ds["masks"]:
            entries.append({
                "panel": ds["panel"],
                "mask": ds["masks"][VAL_MASK_KEY],
                "adj_s": ds["sector_adj"],
                "adj_t": ds["territory_adj"],
                "true_relations": ds["true_relations"],
            })
    return entries


def _fresh_model(device: str) -> HERALDGraphImputerLagged:
    return HERALDGraphImputerLagged(
        N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=DROPOUT
    ).to(device)


def _compute_masked_reconstruction_loss(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    input_mask: np.ndarray,
    loss_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
    loss_type: str = "NLL_CLAMPED",
) -> tuple[torch.Tensor, dict]:
    """
    Compute reconstruction loss on loss_mask cells.
    input_mask: what model sees (structural minus artificially hidden).
    loss_mask: artificially hidden cells to predict.
    Both must be disjoint — assertion enforced.
    """
    from src.modeles.synthetic.phase15_stable_objective.loss_functions import _check_disjoint
    _check_disjoint(input_mask, loss_mask)

    panel_t, input_mask_t, adj_s_t, adj_t_t = _prep_tensors(
        panel, input_mask, adj_s, adj_t, device
    )
    loss_mask_t = torch.from_numpy(loss_mask.astype(np.float32)).to(device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, input_mask).astype(np.float32)
    ).to(device)

    out = model(panel_t, input_mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    pred_log_sigma = out[..., 1]

    stats = log_sigma_stats(pred_log_sigma, loss_mask_t)

    if loss_type == "NLL_CLAMPED":
        loss = masked_nll_clamped(pred_mean, pred_log_sigma, true_t, loss_mask_t)
    elif loss_type == "HUBER":
        loss = masked_huber(pred_mean, true_t, loss_mask_t)
    elif loss_type == "MSE":
        loss = masked_mse(pred_mean, true_t, loss_mask_t)
    else:
        raise ValueError(f"Unknown loss_type: {loss_type!r}")

    return loss, stats


def _compute_variant_loss(
    model: HERALDGraphImputerLagged,
    heads: GraphAuxHeads | None,
    entry: dict,
    device: str,
    variant: str,
    rng: np.random.Generator,
) -> torch.Tensor:
    """Compute full training loss for one variant + one D2 dataset entry."""
    panel = entry["panel"]
    mask = entry["mask"]
    adj_s = entry["adj_s"]
    adj_t = entry["adj_t"]
    true_relations = entry["true_relations"]
    n_S = panel.shape[1]

    # Determine reconstruction loss type
    if "NLL_CLAMPED" in variant:
        rec_loss_type = "NLL_CLAMPED"
    elif "HUBER" in variant:
        rec_loss_type = "HUBER"
    else:
        raise ValueError(f"Unknown variant: {variant!r}")

    # Apply MCAR extra masking
    structural_mask = mask
    observed_positions = np.where(structural_mask == 1)
    n_obs = len(observed_positions[0])
    n_to_hide = int(EXTRA_MASK_RATE * n_obs)

    if n_to_hide == 0:
        input_mask = structural_mask.copy()
        loss_mask = np.zeros_like(structural_mask, dtype=np.float32)
        # Nothing to predict → zero loss
        return torch.tensor(0.0, requires_grad=False)

    hide_idx = rng.choice(n_obs, n_to_hide, replace=False)
    indices_to_hide = tuple(arr[hide_idx] for arr in observed_positions)

    input_mask = structural_mask.copy()
    input_mask[indices_to_hide] = 0
    loss_mask = np.zeros_like(structural_mask, dtype=np.float32)
    loss_mask[indices_to_hide] = 1.0

    rec_loss, _ = _compute_masked_reconstruction_loss(
        model, panel, input_mask, loss_mask, adj_s, adj_t, device, rec_loss_type
    )

    if "GRAPH_MULTITASK" in variant and heads is not None:
        graph_loss = heads.total_graph_loss(model, true_relations, device)
        return rec_loss + graph_loss

    return rec_loss


def _compute_val_loss(
    model: HERALDGraphImputerLagged,
    val_entries: list[dict],
    device: str,
) -> float:
    """Standard NLL val loss on nonlinear_heavy (same as DEC-049/050 for comparability)."""
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for e in val_entries:
            loss = _compute_nll_loss(
                model, e["panel"], e["mask"], e["adj_s"], e["adj_t"], device
            )
            total += loss.item()
            count += 1
    model.train()
    return total / max(count, 1)


def _measure_grad_norms(
    model: HERALDGraphImputerLagged,
    heads: GraphAuxHeads | None,
    entries: list[dict],
    device: str,
    variant: str,
    rng: np.random.Generator,
) -> dict:
    """Measure gradient norms for attention vs decoder parameters."""
    model.train()
    if heads is not None:
        heads.train()

    all_params = list(model.parameters())
    for p in all_params:
        if p.grad is not None:
            p.grad.zero_()

    entry = entries[0]
    loss = _compute_variant_loss(model, heads, entry, device, variant, rng)
    loss.backward()

    attn_params = [model.log_sect_attn_lag1, model.log_sect_attn_lag2, model.log_terr_attn]
    dec_params = list(model.net.parameters())

    def _gnorm(params):
        g = [p.grad for p in params if p.grad is not None]
        if not g:
            return float("nan")
        return float(torch.stack([x.norm() for x in g]).mean())

    attn_norm = _gnorm(attn_params)
    dec_norm = _gnorm(dec_params)
    ratio = dec_norm / attn_norm if (attn_norm > 0 and not np.isnan(attn_norm)) else float("nan")
    aux_reaches_attn = (
        attn_norm > 1e-10 and not np.isnan(attn_norm)
        and "GRAPH_MULTITASK" in variant
    )

    for p in all_params:
        if p.grad is not None:
            p.grad.zero_()

    return {
        "grad_norm_attention": attn_norm,
        "grad_norm_decoder": dec_norm,
        "ratio_dec_attn": ratio,
        "aux_reaches_attn": aux_reaches_attn,
    }


def run_pretraining(
    variant: str,
    epoch_budget: int,
    output_dir: Path,
    device: str = "cpu",
    n_datasets: int = N_PRETRAIN_DATASETS,
    seed_start: int = D2_SEED_START,
    patience: int = 20,
    rng_seed: int = 0,
) -> dict:
    """
    Train a new model from scratch (or return Phase 11 T2 for NO_PRETRAINING).
    Returns dict with checkpoint_path, checkpoint_hash, grad_norms, val_loss, etc.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_name = f"model_{variant}_ep{epoch_budget}.pt"
    ckpt_path = output_dir / ckpt_name

    if variant == "NO_PRETRAINING":
        t2 = PHASE11_T2_CHECKPOINT
        if not t2.exists():
            # Fall back to fresh model (smoke test mode)
            model = _fresh_model(device)
            torch.save(model.state_dict(), ckpt_path)
            return {
                "checkpoint_path": str(ckpt_path),
                "checkpoint_hash": checkpoint_hash(ckpt_path),
                "best_epoch": 0,
                "best_val_loss": float("nan"),
                "grad_norms": {},
                "runtime_s": 0.0,
                "variant": variant,
                "epoch_budget": epoch_budget,
            }
        import shutil
        shutil.copy(t2, ckpt_path)
        return {
            "checkpoint_path": str(ckpt_path),
            "checkpoint_hash": checkpoint_hash(ckpt_path),
            "best_epoch": 0,
            "best_val_loss": float("nan"),
            "grad_norms": {},
            "runtime_s": 0.0,
            "variant": variant,
            "epoch_budget": epoch_budget,
        }

    t0 = time.time()
    rng = np.random.default_rng(rng_seed)
    entries = generate_d2_datasets(n_datasets, seed_start)
    val_entries = _build_val_entries()

    model = _fresh_model(device)
    heads = GraphAuxHeads(N_SECTORS).to(device) if "GRAPH_MULTITASK" in variant else None

    params = list(model.parameters())
    if heads is not None:
        params = params + list(heads.parameters())
    optimizer = optim.Adam(params, lr=1e-3)

    best_val = float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    best_heads_state = copy.deepcopy(heads.state_dict()) if heads is not None else None
    no_improve = 0

    # Gradient norms measured on first epoch
    grad_norms = _measure_grad_norms(model, heads, entries[:3], device, variant, np.random.default_rng(rng_seed + 1))

    for epoch in range(epoch_budget):
        model.train()
        if heads is not None:
            heads.train()

        ep_rng = np.random.default_rng(rng_seed + epoch + 1)
        order = ep_rng.permutation(len(entries))

        for idx in order:
            entry = entries[idx]
            optimizer.zero_grad()
            loss = _compute_variant_loss(model, heads, entry, device, variant, ep_rng)
            if torch.isnan(loss) or torch.isinf(loss):
                continue
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
            optimizer.step()

        val_loss = _compute_val_loss(model, val_entries, device)

        if val_loss < best_val - 1e-6:
            best_val = val_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            if heads is not None:
                best_heads_state = copy.deepcopy(heads.state_dict())
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    model.load_state_dict(best_state)
    torch.save(model.state_dict(), ckpt_path)

    if heads is not None and best_heads_state is not None:
        heads.load_state_dict(best_heads_state)
        heads_path = output_dir / f"heads_{variant}_ep{epoch_budget}.pt"
        torch.save(heads.state_dict(), heads_path)

    runtime = time.time() - t0
    return {
        "checkpoint_path": str(ckpt_path),
        "checkpoint_hash": checkpoint_hash(ckpt_path),
        "best_epoch": best_epoch,
        "best_val_loss": best_val,
        "grad_norms": grad_norms,
        "runtime_s": runtime,
        "variant": variant,
        "epoch_budget": epoch_budget,
        "heads_path": str(output_dir / f"heads_{variant}_ep{epoch_budget}.pt") if heads else None,
    }


def run_budget_grid(
    variant: str,
    output_dir: Path,
    device: str = "cpu",
    n_datasets: int = N_PRETRAIN_DATASETS,
    epoch_budgets: list[int] | None = None,
    seed_start: int = D2_SEED_START,
    patience: int = 20,
) -> dict[int, dict]:
    """Run pretraining for all budgets in sequence (cumulative: 75 continues from 30)."""
    if epoch_budgets is None:
        epoch_budgets = EPOCH_BUDGETS

    if variant == "NO_PRETRAINING":
        return {b: run_pretraining(variant, b, output_dir, device) for b in epoch_budgets}

    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[int, dict] = {}
    rng_seed = 0
    rng = np.random.default_rng(rng_seed)
    entries = generate_d2_datasets(n_datasets, seed_start)
    val_entries = _build_val_entries()

    model = _fresh_model(device)
    heads = GraphAuxHeads(N_SECTORS).to(device) if "GRAPH_MULTITASK" in variant else None

    params = list(model.parameters())
    if heads is not None:
        params = params + list(heads.parameters())
    optimizer = optim.Adam(params, lr=1e-3)

    grad_norms = _measure_grad_norms(model, heads, entries[:3], device, variant, np.random.default_rng(1))

    budgets_sorted = sorted(epoch_budgets)
    global_epoch = 0
    best_val = float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    best_heads_state = copy.deepcopy(heads.state_dict()) if heads else None
    no_improve = 0
    t0 = time.time()

    for budget in budgets_sorted:
        epochs_for_this_budget = budget - global_epoch
        for _ in range(epochs_for_this_budget):
            model.train()
            if heads:
                heads.train()
            ep_rng = np.random.default_rng(rng_seed + global_epoch + 1)
            order = ep_rng.permutation(len(entries))
            for idx in order:
                entry = entries[idx]
                optimizer.zero_grad()
                loss = _compute_variant_loss(model, heads, entry, device, variant, ep_rng)
                if torch.isnan(loss) or torch.isinf(loss):
                    continue
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
                optimizer.step()

            val_loss = _compute_val_loss(model, val_entries, device)
            if val_loss < best_val - 1e-6:
                best_val = val_loss
                best_epoch = global_epoch
                best_state = copy.deepcopy(model.state_dict())
                if heads:
                    best_heads_state = copy.deepcopy(heads.state_dict())
                no_improve = 0
            else:
                no_improve += 1

            global_epoch += 1

        # Save checkpoint at this budget milestone
        model.load_state_dict(best_state)
        ckpt_name = f"model_{variant}_ep{budget}.pt"
        ckpt_path = output_dir / ckpt_name
        torch.save(model.state_dict(), ckpt_path)

        if heads is not None and best_heads_state is not None:
            heads.load_state_dict(best_heads_state)
            heads_path = output_dir / f"heads_{variant}_ep{budget}.pt"
            torch.save(heads.state_dict(), heads_path)

        # Re-load best (to continue training from best)
        model.load_state_dict(best_state)

        runtime = time.time() - t0
        results[budget] = {
            "checkpoint_path": str(ckpt_path),
            "checkpoint_hash": checkpoint_hash(ckpt_path),
            "best_epoch": best_epoch,
            "best_val_loss": best_val,
            "grad_norms": grad_norms if budget == budgets_sorted[0] else {},
            "runtime_s": runtime,
            "variant": variant,
            "epoch_budget": budget,
            "heads_path": str(output_dir / f"heads_{variant}_ep{budget}.pt") if heads else None,
        }

    return results
