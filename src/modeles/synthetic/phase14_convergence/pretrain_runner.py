"""
pretrain_runner.py — Controlled pretraining with epoch-budget grid (DEC-049).

Trains HERALDGraphImputerLagged from scratch on 50 D2 datasets.
Saves checkpoints at each budget milestone (30, 75, 150 epochs).
Validates on nonlinear_heavy scenario with Phase 11 val seeds.

CRITICAL CONSTRAINT: true_relations ground truth used in GRAPH_MASKED_MULTITASK
objective ONLY exists in synthetic data. This supervision is NOT available for
real country data (PT/IT/FR/NL/AT) and must not be claimed to apply to them.

Multitask loss weights (FROZEN before execution — do NOT change after seeing results):
  MULTITASK_ALPHA = 0.1    # edge_presence BCE weight
  MULTITASK_BETA  = 0.05   # sign prediction BCE weight
  MULTITASK_GAMMA = 0.05   # lag prediction BCE weight
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
import torch.nn as nn
import torch.nn.functional as F

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
    checkpoint_hash,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase11_generalization.splits import TEST_SEEDS

# ── Frozen constants ───────────────────────────────────────────────────────────

# Epoch budgets for the grid (300 only if E2 auto-trigger fires)
EPOCH_BUDGETS: list[int] = [30, 75, 150]

# Pretraining datasets
N_PRETRAIN_DATASETS: int = 50
D2_SEED_START: int = 200        # seeds 200-249 for D2 pretrain datasets (50 seeds)
D2_NL_MIN: float = 0.0
D2_NL_MAX: float = 0.9          # frac_nonlinear uniformly in [0, 0.9]

# Validation config (Phase 11 val seeds)
VAL_SCENARIO: str = "nonlinear_heavy"
VAL_SEEDS: list[int] = [100, 200, 300]
VAL_MASK_KEY: str = "mcar_30"

# Multitask loss weights — FROZEN before execution, do NOT change
MULTITASK_ALPHA: float = 0.1    # edge_presence BCE weight
MULTITASK_BETA: float = 0.05    # sign prediction BCE weight
MULTITASK_GAMMA: float = 0.05   # lag prediction BCE weight

# Phase 11 T2 checkpoint path (for NO_PRETRAINING variant)
PHASE11_T2_CHECKPOINT: Path = Path(
    "data/processed/synthetic_benchmark/phase11_pilot/model_T2_pilot.pt"
)

PRETRAIN_VARIANTS: list[str] = [
    "NO_PRETRAINING",
    "TEMPORAL_MASKED",
    "GRAPH_MASKED_MULTITASK",
]


# ── Seed disjointness verification ────────────────────────────────────────────

def verify_d2_seeds_disjoint(seeds: list[int]) -> None:
    """Assert D2 seeds are disjoint from TEST_SEEDS [1000-5000]."""
    test_seeds_set = set(TEST_SEEDS) | set(range(1000, 5001))
    overlap = set(seeds) & test_seeds_set
    if overlap:
        raise ValueError(
            f"D2 pretrain seeds overlap with TEST_SEEDS: {overlap}. "
            "This would contaminate the evaluation."
        )
    # Also check against novel test scenario seeds
    novel_seeds = {1000, 2000, 3000, 4000, 5000}
    overlap2 = set(seeds) & novel_seeds
    if overlap2:
        raise ValueError(f"D2 seeds overlap with novel test seeds: {overlap2}")


# ── D2 dataset generation ──────────────────────────────────────────────────────

def generate_d2_datasets(
    n_datasets: int,
    seed_start: int = D2_SEED_START,
    mask_keys: tuple[str, ...] = ("mcar_30", "block_30"),
) -> list[dict]:
    """
    Generate D2 mini-datasets. frac_nonlinear uniformly in [0, 0.9].
    Seeds in [seed_start, seed_start + n_datasets) — disjoint from TEST_SEEDS.

    Returns list of ds dicts with panel, masks, adj, true_relations.

    NOTE: true_relations is SYNTHETIC-ONLY ground truth. Not available for real data.
    """
    seeds = list(range(seed_start, seed_start + n_datasets))
    verify_d2_seeds_disjoint(seeds)

    rng = np.random.default_rng(888 + seed_start)  # matches phase13 convention
    entries = []

    for seed in seeds:
        frac_nl = float(rng.uniform(D2_NL_MIN, D2_NL_MAX))
        # Vary territory_radius within [0.28, 0.38]
        # Avoids 0.25 (novel_lag2) and 0.42 (novel_highvar)
        t_radius = float(rng.uniform(0.28, 0.38))
        terr_prop = float(rng.uniform(0.10, 0.22))  # avoids 0.28 (novel_highvar)

        cfg = SyntheticConfig(
            n_territories=30, n_sectors=9, n_years=20,
            seed=seed,
            n_true_relations=8,
            frac_nonlinear=frac_nl,
            frac_negative=float(rng.uniform(0.30, 0.50)),
            noise_sigma_range=(0.08, 0.25),
            ar_coef_range=(0.25, 0.60),
            territory_propagation=terr_prop,
            territory_radius=t_radius,
            forced_lag=None,           # NOT forced_lag=2 (that is novel_lag2)
            structural_break_year=None,  # NOT 8 (that is novel_highvar)
        )
        ds = generate_dataset(cfg)

        for mk in mask_keys:
            if mk in ds["masks"]:
                entries.append({
                    "panel": ds["panel"],
                    "mask": ds["masks"][mk],
                    "adj_s": ds["sector_adj"],
                    "adj_t": ds["territory_adj"],
                    "true_relations": ds["true_relations"],  # SYNTHETIC-ONLY
                    "scenario": f"d2_frac_nl_{frac_nl:.2f}",
                    "seed": seed,
                    "mask_key": mk,
                    "frac_nonlinear": frac_nl,
                })

    return entries


def _build_val_entries() -> list[dict]:
    """Build validation entries (Phase 11 val config, nonlinear_heavy, seeds 100/200/300)."""
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
                "scenario": VAL_SCENARIO,
                "seed": seed,
                "mask_key": VAL_MASK_KEY,
            })
    return entries


# ── Multitask loss functions (v2 — DEC-050 bug fixes) ────────────────────────
#
# Bugs fixed vs DEC-049 pilot implementation:
#   A. TEMPORAL_MASKED now computes loss on artificially hidden cells (loss_mask),
#      NOT on the cells the model can see (input_mask). Separated:
#        structural_mask: cells that are ever observed in this dataset (1=known)
#        input_mask:      cells shown to model (structural_mask minus extra hidden)
#        loss_mask:       cells artificially hidden (truth known, model cannot see)
#   B. Edge presence BCE now marks BOTH lag-1 and lag-2 true edges as positive.
#      Previous version only marked lag-1 → lag-2 edges were treated as negatives.
#      Logit = max(log_attn_lag1, log_attn_lag2) per (target, source) pair.
#      Imbalance corrected via pos_weight = n_neg / n_pos.
#   C. Sign BCE REMOVED — HERALD softmax attention is always positive after softmax;
#      it cannot encode the sign (direction) of an effect without a dedicated head.
#      MULTITASK_BETA is kept in the constant but effectively unused (set to 0).
#      Lag BCE keeps the lag1-lag2 logit (reasonable proxy for lag discrimination)
#      but is now correctly separated from presence logit.

def _compute_masked_nll_loss(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    input_mask: np.ndarray,   # (n_T, n_S, n_Y) — cells the model sees (1=visible)
    loss_mask: np.ndarray,    # (n_T, n_S, n_Y) — cells where loss is computed (1=target)
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> torch.Tensor:
    """
    NLL on loss_mask cells, using input_mask as model input context.

    input_mask and loss_mask must be disjoint — the model cannot see the cells
    whose values it is being asked to predict.

    Used for TEMPORAL_MASKED variant where 40% of observed cells are artificially
    hidden: the model predicts those cells from the remaining 60%.
    """
    assert not np.any((input_mask == 1) & (loss_mask == 1)), (
        "input_mask and loss_mask overlap — model would see the cells it predicts"
    )
    panel_t, input_mask_t, adj_s_t, adj_t_t = _prep_tensors(
        panel, input_mask, adj_s, adj_t, device
    )
    loss_mask_t = torch.from_numpy(loss_mask.astype(np.float32)).to(device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    # Temporal features computed with input_mask (model sees only input_mask cells)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, input_mask).astype(np.float32)
    ).to(device)
    out = model(panel_t, input_mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    log_sigma = out[..., 1]
    sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
    nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
    n_loss = loss_mask_t.sum().clamp(min=1)
    return (nll * loss_mask_t).sum() / n_loss


def _edge_presence_bce(
    model: HERALDGraphImputerLagged,
    true_relations: list,
    n_sectors: int,
    device: str,
) -> torch.Tensor:
    """
    Edge PRESENCE BCE — both lag-1 and lag-2 true edges are positive targets.

    Presence logit: max(log_sect_attn_lag1, log_sect_attn_lag2) per (target, source).
    Diagonal excluded (self-loops not modelled).
    Positive class weighted by n_neg/n_pos to handle class imbalance.
    Convention: edge_target[target, source] = 1 if source→target edge exists.

    BUG FIX (DEC-050): previous version only marked lag-1 as positive.
    lag-2 true edges are now correctly marked as positive for presence.

    NOTE: true_relations ground truth is SYNTHETIC-ONLY.
    """
    edge_target = torch.zeros(n_sectors, n_sectors, device=device)
    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        if s < n_sectors and t < n_sectors:
            edge_target[t, s] = 1.0  # lag-agnostic: any lag → positive
    mask_diag = ~torch.eye(n_sectors, dtype=torch.bool, device=device)
    # Presence logit: max of both lag attention logits per (target, source) pair
    presence_logits = torch.max(model.log_sect_attn_lag1, model.log_sect_attn_lag2)
    logits = presence_logits[mask_diag]
    targets = edge_target[mask_diag]
    n_pos = targets.sum().clamp(min=1)
    n_neg = (1 - targets).sum().clamp(min=1)
    pos_weight = torch.tensor([float(n_neg / n_pos)], device=device)
    return F.binary_cross_entropy_with_logits(logits, targets, pos_weight=pos_weight)


def _lag_bce(
    model: HERALDGraphImputerLagged,
    true_relations: list,
    n_sectors: int,
    device: str,
) -> torch.Tensor:
    """
    Lag prediction BCE (lag-1 = 1.0, lag-2 = 0.0) for known edges only.
    Logit = log_sect_attn_lag1[t,s] - log_sect_attn_lag2[t,s].

    Rationale: if lag-1 attention > lag-2 attention, the edge is more likely lag-1.
    Applied only to cells where a true edge exists (not all off-diagonal pairs).

    BUG FIX (DEC-050): now uses a DIFFERENT logit than edge_presence (which uses max).
    Previous version used the same lag1-lag2 logit for BOTH sign and lag prediction.

    NOTE: true_relations ground truth is SYNTHETIC-ONLY.
    """
    lag_target = torch.full((n_sectors, n_sectors), -1.0, device=device)
    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        if s < n_sectors and t < n_sectors:
            lag_target[t, s] = 1.0 if r.lag == 1 else 0.0
    known = lag_target >= 0
    if not known.any():
        return torch.tensor(0.0, device=device)
    lag_logit = model.log_sect_attn_lag1 - model.log_sect_attn_lag2
    return F.binary_cross_entropy_with_logits(lag_logit[known], lag_target[known])


# SIGN BCE — REMOVED (DEC-050 architectural finding):
# HERALD softmax attention always produces values in [0,1] after softmax.
# The sign (positive/negative) of an edge weight cannot be encoded via attention
# without a dedicated signed output head not present in HERALDGraphImputerLagged.
# Using lag1-lag2 as a sign proxy conflated two different properties (lag vs sign).
# MULTITASK_BETA is kept in constants but sign loss is not included in training.


def compute_multitask_nll(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    true_relations: list,
    n_sectors: int,
    device: str,
    variant: str = "GRAPH_MASKED_MULTITASK",
    rng: np.random.Generator | None = None,
    extra_mask_rate: float = 0.40,
) -> torch.Tensor:
    """
    Compute total pretraining loss.

    TEMPORAL_MASKED:
        Apply MCAR extra masking to extra_mask_rate of observed cells.
        input_mask = observed cells minus artificially hidden.
        loss_mask  = artificially hidden cells (truth known, model cannot see).
        Loss = NLL on loss_mask only.

        BUG FIX (DEC-050): previous version computed loss on input_mask (cells the
        model CAN see), not on loss_mask (cells artificially hidden). Now correct.

    GRAPH_MASKED_MULTITASK:
        Loss = NLL(all observed) + ALPHA * edge_presence_BCE + GAMMA * lag_BCE.
        Sign BCE removed (see note above). BETA unused.
        Requires true_relations (SYNTHETIC-ONLY — not for real country data).

    Loss weights FROZEN: ALPHA=0.1, GAMMA=0.05.
    """
    if variant == "TEMPORAL_MASKED":
        if rng is None:
            rng = np.random.default_rng(42)
        structural_mask = mask  # 1 = structurally observed in this dataset
        observed_positions = np.where(structural_mask == 1)
        n_obs = len(observed_positions[0])
        n_to_hide = int(extra_mask_rate * n_obs)

        if n_to_hide == 0:
            # Degenerate case: fall back to standard NLL
            return _compute_nll_loss(model, panel, structural_mask, adj_s, adj_t, device)

        hide_idx = rng.choice(n_obs, n_to_hide, replace=False)
        indices_to_hide = tuple(arr[hide_idx] for arr in observed_positions)

        # input_mask: what the model sees (structural minus artificially hidden)
        input_mask = structural_mask.copy()
        input_mask[indices_to_hide] = 0

        # loss_mask: artificially hidden cells — truth is known, model cannot see them
        loss_mask = np.zeros_like(structural_mask, dtype=np.float32)
        loss_mask[indices_to_hide] = 1.0

        return _compute_masked_nll_loss(model, panel, input_mask, loss_mask, adj_s, adj_t, device)

    elif variant == "GRAPH_MASKED_MULTITASK":
        # Reconstruction NLL on all observed cells
        nll_loss = _compute_nll_loss(model, panel, mask, adj_s, adj_t, device)
        # Auxiliary losses (SYNTHETIC-ONLY — not for real country data)
        edge_loss = _edge_presence_bce(model, true_relations, n_sectors, device)
        lag_loss = _lag_bce(model, true_relations, n_sectors, device)
        # Sign BCE omitted — architecturally unimplementable (see note above)
        return nll_loss + MULTITASK_ALPHA * edge_loss + MULTITASK_GAMMA * lag_loss

    else:
        raise ValueError(f"Unknown variant: {variant!r}")


def _compute_nll_loss(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> torch.Tensor:
    """NLL on observed cells (gradient-enabled)."""
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


# ── Gradient measurement ──────────────────────────────────────────────────────

def _measure_grad_norms(
    model: HERALDGraphImputerLagged,
    train_entries: list[dict],
    device: str,
    variant: str,
    rng: np.random.Generator,
) -> dict:
    """
    Measure gradient norms during one forward-backward pass on the final training entry.

    Returns:
      grad_norm_attention: sqrt(||grad(lag1)||^2 + ||grad(lag2)||^2)
      grad_norm_decoder: sqrt(sum ||grad(net.weight/bias)||^2)
      grad_norm_multitask: gradient norm from auxiliary losses only (L2/L3)
      attn_grad_from_aux_reaches: bool — auxiliary grad reaches log_sect_attn_lag1
    """
    if not train_entries:
        return {
            "grad_norm_attention": float("nan"),
            "grad_norm_decoder": float("nan"),
            "grad_norm_multitask": float("nan"),
            "attn_grad_from_aux_reaches": False,
        }

    model = model.to(device)

    # Use a representative entry for gradient measurement
    e = train_entries[min(len(train_entries) - 1, 0)]
    n_sectors = e["panel"].shape[1]

    # Zero grads
    for p in model.parameters():
        if p.grad is not None:
            p.grad.zero_()

    model.train()
    loss = compute_multitask_nll(
        model, e["panel"], e["mask"], e["adj_s"], e["adj_t"],
        e["true_relations"], n_sectors, device, variant=variant, rng=rng,
    )
    loss.backward()

    def _norm(p: nn.Parameter) -> float:
        return float(p.grad.norm().item()) if p.grad is not None else 0.0

    grad_lag1 = _norm(model.log_sect_attn_lag1)
    grad_lag2 = _norm(model.log_sect_attn_lag2)
    grad_attn = float(np.sqrt(grad_lag1**2 + grad_lag2**2))

    grad_dec = 0.0
    for p in model.net.parameters():
        if p.grad is not None:
            grad_dec += float(p.grad.norm().item()) ** 2
    grad_dec = float(np.sqrt(grad_dec))

    # Measure auxiliary loss contribution separately
    grad_multitask = float("nan")
    attn_from_aux = False
    if variant == "GRAPH_MASKED_MULTITASK":
        for p in model.parameters():
            if p.grad is not None:
                p.grad.zero_()
        # Only aux losses (sign BCE removed — see compute_multitask_nll docstring)
        edge_loss = _edge_presence_bce(model, e["true_relations"], n_sectors, device)
        lag_loss = _lag_bce(model, e["true_relations"], n_sectors, device)
        aux_loss = MULTITASK_ALPHA * edge_loss + MULTITASK_GAMMA * lag_loss
        aux_loss.backward()
        attn_from_aux = (
            model.log_sect_attn_lag1.grad is not None
            and float(model.log_sect_attn_lag1.grad.norm()) > 1e-10
        )
        aux_norm = 0.0
        for p in [model.log_sect_attn_lag1, model.log_sect_attn_lag2]:
            if p.grad is not None:
                aux_norm += float(p.grad.norm().item()) ** 2
        grad_multitask = float(np.sqrt(aux_norm))

    return {
        "grad_norm_attention": grad_attn,
        "grad_norm_decoder": grad_dec,
        "grad_norm_multitask": grad_multitask,
        "attn_grad_from_aux_reaches": attn_from_aux,
    }


# ── Core pretraining function ─────────────────────────────────────────────────

def run_pretraining(
    variant: str,
    epoch_budget: int,
    output_dir: Path,
    n_datasets: int = N_PRETRAIN_DATASETS,
    device: str = "cpu",
    lr: float = 1e-3,
    patience: int = 20,
    seed_start: int = D2_SEED_START,
) -> dict:
    """
    Pretrain HERALDGraphImputerLagged for a given epoch budget.

    variant:
      "NO_PRETRAINING"          — skip training, return Phase 11 T2 checkpoint
      "TEMPORAL_MASKED"         — masked NLL reconstruction, 50 D2 datasets
      "GRAPH_MASKED_MULTITASK"  — NLL + edge_BCE + sign_BCE + lag_BCE, 50 D2 datasets

    Checkpoint is selected by minimum val loss (NOT last epoch).
    Checkpoint saved to output_dir / f"model_{variant}_ep{epoch_budget}.pt"

    Returns:
      {
        checkpoint_path: Path,
        checkpoint_hash: str,
        best_epoch: int,
        history: {train_loss: [], val_loss: []},
        grad_norms: {attention, decoder, multitask},
        runtime_s: float,
      }
    """
    assert variant in PRETRAIN_VARIANTS, f"Unknown variant: {variant!r}"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_name = f"model_{variant}_ep{epoch_budget}.pt"
    checkpoint_path = output_dir / checkpoint_name

    t0 = time.time()

    # ── NO_PRETRAINING: use Phase 11 T2 checkpoint ────────────────────────────
    if variant == "NO_PRETRAINING":
        t2_path = PHASE11_T2_CHECKPOINT
        # Try repo-root relative path
        repo_root = Path(__file__).resolve().parents[5]
        abs_t2 = repo_root / t2_path
        if not abs_t2.exists():
            # Train a pilot T2 model and save
            from src.modeles.synthetic.phase11_generalization.trainer import (
                train_strategy, save_checkpoint,
            )
            model, _ = train_strategy("T2", pilot=True, n_epochs=epoch_budget,
                                      device=device, patience=patience)
            chkpt_hash = save_checkpoint(model, abs_t2)
        else:
            state = torch.load(abs_t2, map_location=device, weights_only=True)
            model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
            model.load_state_dict(state)
            model.to(device)
            model.eval()
            chkpt_hash = checkpoint_hash(model.state_dict())

        # Save a copy in output_dir for provenance
        torch.save(model.state_dict(), checkpoint_path)
        runtime_s = time.time() - t0
        return {
            "checkpoint_path": checkpoint_path,
            "checkpoint_hash": chkpt_hash,
            "best_epoch": 0,
            "history": {"train_loss": [], "val_loss": []},
            "grad_norms": {
                "grad_norm_attention": float("nan"),
                "grad_norm_decoder": float("nan"),
                "grad_norm_multitask": float("nan"),
                "attn_grad_from_aux_reaches": False,
            },
            "runtime_s": runtime_s,
            "variant": variant,
            "epoch_budget": epoch_budget,
        }

    # ── TEMPORAL_MASKED / GRAPH_MASKED_MULTITASK ─────────────────────────────
    pretrain_entries = generate_d2_datasets(n_datasets, seed_start=seed_start)
    val_entries = _build_val_entries()

    assert len(pretrain_entries) > 0, "No pretrain entries generated"
    assert len(val_entries) > 0, "No val entries generated"

    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    rng = np.random.default_rng(99 + seed_start)
    best_val = float("inf")
    best_state: dict | None = None
    no_improve = 0
    train_losses: list[float] = []
    val_losses: list[float] = []
    best_epoch = 0

    n_sectors = N_SECTORS
    grad_norms: dict = {}

    for epoch in range(epoch_budget):
        model.train()
        order = rng.permutation(len(pretrain_entries))
        ep_loss = 0.0

        for idx in order:
            e = pretrain_entries[int(idx)]
            opt.zero_grad()
            loss = compute_multitask_nll(
                model, e["panel"], e["mask"], e["adj_s"], e["adj_t"],
                e["true_relations"], n_sectors, device,
                variant=variant, rng=rng,
            )
            loss.backward()
            opt.step()
            ep_loss += float(loss)

        train_losses.append(ep_loss / max(len(pretrain_entries), 1))

        # Validation
        model.eval()
        with torch.no_grad():
            vl = []
            for v in val_entries:
                vl.append(float(_compute_nll_loss(
                    model, v["panel"], v["mask"], v["adj_s"], v["adj_t"], device
                )))
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

    # Use best state (val-selected checkpoint, NOT last epoch)
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    # Measure gradient norms on final epoch state (re-enable grad)
    model.train()
    grad_norms = _measure_grad_norms(model, pretrain_entries[:5], device, variant, rng)
    model.eval()

    chkpt_hash = checkpoint_hash(model.state_dict())
    torch.save(model.state_dict(), checkpoint_path)

    runtime_s = time.time() - t0

    return {
        "checkpoint_path": checkpoint_path,
        "checkpoint_hash": chkpt_hash,
        "best_epoch": best_epoch,
        "history": {"train_loss": train_losses, "val_loss": val_losses},
        "grad_norms": grad_norms,
        "runtime_s": runtime_s,
        "variant": variant,
        "epoch_budget": epoch_budget,
        "n_pretrain_datasets": n_datasets,
        "best_val_loss": float(best_val),
    }


# ── Budget grid ───────────────────────────────────────────────────────────────

def run_budget_grid(
    variant: str,
    output_dir: Path,
    device: str = "cpu",
    n_datasets: int = N_PRETRAIN_DATASETS,
    epoch_budgets: list[int] | None = None,
    seed_start: int = D2_SEED_START,
    lr: float = 1e-3,
    patience: int = 20,
) -> dict[int, dict]:
    """
    Run pretraining for all epoch budgets in EPOCH_BUDGETS.
    Returns {budget: result_dict}.

    For NO_PRETRAINING variant: same checkpoint for all budgets.
    For other variants: separate training run per budget.
    """
    if epoch_budgets is None:
        epoch_budgets = EPOCH_BUDGETS

    results: dict[int, dict] = {}
    for budget in epoch_budgets:
        result = run_pretraining(
            variant=variant,
            epoch_budget=budget,
            output_dir=Path(output_dir),
            n_datasets=n_datasets,
            device=device,
            lr=lr,
            patience=patience,
            seed_start=seed_start,
        )
        results[budget] = result
    return results
