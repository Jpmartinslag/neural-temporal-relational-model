"""
loss_functions.py — Decoupled training loss for DEC-053.

L_total = L_recon + λ_p*L_presence + λ_s*L_sign + λ_l*L_lag + λ_u*L_utility + λ_g*mean(gate)

L_utility is supervised only during TRAINING (compute_utility=True).
NEVER pass compute_utility=True during test/evaluation.

All weights frozen before experiment.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

# Frozen loss weights (DEC-053)
LAMBDA_PRESENCE: float = 0.05
LAMBDA_SIGN: float = 0.02
LAMBDA_LAG: float = 0.02
LAMBDA_UTILITY: float = 0.05
LAMBDA_GATE: float = 0.01   # L1 regularisation toward closed gate


def masked_mse(pred: torch.Tensor, true: torch.Tensor, loss_mask: torch.Tensor) -> torch.Tensor:
    """MSE on loss_mask==1 cells."""
    n = loss_mask.sum().clamp(min=1)
    return ((pred - true) ** 2 * loss_mask).sum() / n


def _utility_target(
    y_temporal: torch.Tensor,
    y_oracle: torch.Tensor,
    true: torch.Tensor,
    loss_mask: torch.Tensor,
) -> torch.Tensor:
    """
    Binary utility target: 1 where oracle-gated reduces error vs temporal-only.
    y_oracle = y_temporal + (true correction from true_relations)
    """
    err_temporal = (y_temporal - true).abs()
    err_oracle = (y_oracle - true).abs()
    return (err_oracle < err_temporal).float()


def decoupled_total_loss(
    y_pred: torch.Tensor,
    y_temporal: torch.Tensor,
    gate: torch.Tensor,
    true: torch.Tensor,
    loss_mask: torch.Tensor,
    model,                              # GatedGraphModel
    true_relations: list,
    device: str,
    compute_utility: bool = True,       # False during eval/test
    y_oracle: torch.Tensor | None = None,
) -> tuple[torch.Tensor, dict]:
    """
    Full decoupled loss. Returns (total_loss, component_dict).
    compute_utility=False when no target access is permitted.
    """
    true_t = torch.from_numpy(np.nan_to_num(true, nan=0.0).astype(np.float32)).to(device)

    # L_reconstruction: MSE of gated prediction on loss_mask cells
    l_recon = masked_mse(y_pred, true_t, loss_mask)

    # Graph head losses
    head = model.graph_relation_head
    graph_losses = head.all_losses(true_relations, device)
    l_presence = graph_losses["presence"]
    l_sign = graph_losses["sign"]
    l_lag = graph_losses["lag"]

    # Utility loss (training only)
    if compute_utility and y_oracle is not None:
        util_tgt = _utility_target(y_temporal, y_oracle, true_t, loss_mask)
        util_logit = gate  # gate ∈ (0,1); treat as probability matching utility
        l_utility = F.binary_cross_entropy(gate * loss_mask, util_tgt * loss_mask,
                                           reduction="sum") / loss_mask.sum().clamp(min=1)
    else:
        l_utility = torch.tensor(0.0, device=device)

    # Gate regularisation (L1 toward closed)
    l_gate = gate.mean()

    total = (
        l_recon
        + LAMBDA_PRESENCE * l_presence
        + LAMBDA_SIGN * l_sign
        + LAMBDA_LAG * l_lag
        + LAMBDA_UTILITY * l_utility
        + LAMBDA_GATE * l_gate
    )

    components = {
        "l_recon": float(l_recon),
        "l_presence": float(l_presence),
        "l_sign": float(l_sign),
        "l_lag": float(l_lag),
        "l_utility": float(l_utility),
        "l_gate": float(l_gate),
        "total": float(total),
    }
    return total, components
