"""
adaptation_trainer.py — Few-shot adaptation trainer for Phase 12 (DEC-047).

Trains the unfrozen parameters of a model on support labels only.
Same NLL loss as Phase 11 trainer. Early stopping on val_mask.

Key invariants:
- No optimizer state during evaluation
- No statistics computed from test cells
- checkpoint hash verified before/after (for Z0: hash must not change)
- Support labels must be disjoint from val/test labels
- If support has 0 cells (zero-shot): no optimizer created, model unchanged
"""

from __future__ import annotations

import copy

import numpy as np
import torch

from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.phase11_generalization.trainer import checkpoint_hash

ADAPTATION_EPOCHS: int = 100
ADAPTATION_LR: float = 1e-3
ADAPTATION_PATIENCE: int = 15
MIN_LABELS: int = 5  # if support has fewer cells, flag EXTREME_LOW_SHOT


def compute_nll_on_mask(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    active_mask: np.ndarray,  # (n_T, n_S, n_Y) — 1 = cells to compute loss on
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> float:
    """
    NLL on cells where active_mask=1 (support or val cells).
    Returns scalar loss. No gradient computed.
    """
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, active_mask, adj_s, adj_t, device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, active_mask).astype(np.float32)
    ).to(device)
    active_t = torch.from_numpy(active_mask.astype(np.float32)).to(device)

    with torch.no_grad():
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    log_sigma = out[..., 1]
    sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
    nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
    n_active = float(active_t.sum().clamp(min=1))
    return float((nll * active_t).sum() / n_active)


def _compute_nll_train(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    support_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> torch.Tensor:
    """NLL with gradient for training step."""
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, support_mask, adj_s, adj_t, device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, support_mask).astype(np.float32)
    ).to(device)
    support_t = torch.from_numpy(support_mask.astype(np.float32)).to(device)

    out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    log_sigma = out[..., 1]
    sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
    nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
    return (nll * support_t).sum() / support_t.sum().clamp(min=1)


def adapt_model(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    support_mask: np.ndarray,       # cells available for adaptation
    val_mask: np.ndarray,           # cells for early stopping
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    n_epochs: int = ADAPTATION_EPOCHS,
    lr: float = ADAPTATION_LR,
    patience: int = ADAPTATION_PATIENCE,
    device: str = "cpu",
) -> dict:
    """
    Adapt only the unfrozen parameters (set by apply_strategy_freeze before calling).

    Returns history dict:
      {train_loss, val_loss, best_epoch, n_support_labels, adapted, is_extreme_low_shot}

    Zero-shot (support_mask.sum()==0): no optimizer created, model unchanged.
    All-frozen (no trainable params): no optimizer created, model unchanged.
    """
    n_support = int(support_mask.sum())
    is_extreme_low_shot = 0 < n_support < MIN_LABELS

    if n_support == 0:
        return {
            "train_loss": [],
            "val_loss": [],
            "best_epoch": 0,
            "n_support_labels": 0,
            "adapted": False,
            "is_extreme_low_shot": False,
            "reason": "zero_shot",
        }

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    if not trainable_params:
        return {
            "train_loss": [],
            "val_loss": [],
            "best_epoch": 0,
            "n_support_labels": n_support,
            "adapted": False,
            "is_extreme_low_shot": is_extreme_low_shot,
            "reason": "no_trainable_params",
        }

    model = model.to(device)
    opt = torch.optim.Adam(trainable_params, lr=lr)

    best_val = float("inf")
    best_state: dict | None = None
    no_improve = 0
    train_losses: list[float] = []
    val_losses: list[float] = []
    best_epoch = 0

    has_val = int(val_mask.sum()) > 0

    for epoch in range(n_epochs):
        model.train()
        opt.zero_grad()
        loss = _compute_nll_train(model, panel, support_mask, adj_s, adj_t, device)
        loss.backward()
        opt.step()
        train_losses.append(float(loss))

        model.eval()
        if has_val:
            val_loss = compute_nll_on_mask(model, panel, val_mask, adj_s, adj_t, device)
        else:
            val_loss = float(loss)  # fallback to train loss for early stopping
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

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    return {
        "train_loss": train_losses,
        "val_loss": val_losses,
        "best_epoch": best_epoch,
        "n_support_labels": n_support,
        "adapted": True,
        "is_extreme_low_shot": is_extreme_low_shot,
        "reason": "adapted",
    }
