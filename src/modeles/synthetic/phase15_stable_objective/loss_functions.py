"""
loss_functions.py — Stable reconstruction losses for DEC-051.

Three variants compared:
  R1 — Gaussian NLL with clamped log_sigma (prevents variance collapse)
  R2 — Huber loss (no variance head; robust to outliers)
  R3 — MSE (diagnostic baseline only)

All losses compute on loss_mask cells only. Visible cells (input_mask) must
NOT enter the loss — enforced via assertion in _compute_masked_loss.

Constants frozen before execution:
  LOG_SIGMA_MIN = -3.0  (σ_min ≈ 0.05 — prevents σ → 0)
  LOG_SIGMA_MAX =  2.0  (σ_max ≈ 7.4 — prevents σ → ∞)
  SIGMA_ENTROPY_LAMBDA = 0.001  (small penalty to avoid log_sigma → boundary)
  HUBER_DELTA = 1.0
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

# ── Frozen constants ───────────────────────────────────────────────────────────
LOG_SIGMA_MIN: float = -3.0     # σ_min ≈ 0.05
LOG_SIGMA_MAX: float = 2.0      # σ_max ≈ 7.4
SIGMA_ENTROPY_LAMBDA: float = 0.001  # small regulariser on log_sigma extremes
HUBER_DELTA: float = 1.0


def _check_disjoint(input_mask: np.ndarray, loss_mask: np.ndarray) -> None:
    """Verify that input_mask and loss_mask have no overlap."""
    if np.any((input_mask == 1) & (loss_mask == 1)):
        overlap = int(((input_mask == 1) & (loss_mask == 1)).sum())
        raise AssertionError(
            f"input_mask and loss_mask overlap ({overlap} cells). "
            "Visible cells must not enter masked reconstruction loss."
        )


def masked_nll_clamped(
    pred_mean: torch.Tensor,
    pred_log_sigma: torch.Tensor,
    true: torch.Tensor,
    loss_mask: torch.Tensor,
) -> torch.Tensor:
    """
    Gaussian NLL on loss_mask cells, with log_sigma clamped to [LOG_SIGMA_MIN, LOG_SIGMA_MAX].

    Prevents variance collapse (σ → 0 → NLL → -∞) by clamping.
    Small entropy penalty discourages log_sigma sitting at the clamp boundaries.

    Args:
        pred_mean:      (n_T, n_S, n_Y) model predictions
        pred_log_sigma: (n_T, n_S, n_Y) raw log sigma (before clamping)
        true:           (n_T, n_S, n_Y) ground truth (nan → 0 already applied)
        loss_mask:      (n_T, n_S, n_Y) float, 1 = compute loss here

    Returns scalar loss.
    """
    log_sigma = pred_log_sigma.clamp(LOG_SIGMA_MIN, LOG_SIGMA_MAX)
    sigma_sq = (2 * log_sigma).exp()
    nll = 0.5 * (2 * log_sigma + (true - pred_mean) ** 2 / sigma_sq)
    n_loss = loss_mask.sum().clamp(min=1)
    base_loss = (nll * loss_mask).sum() / n_loss
    # Entropy penalty: penalize sitting at clamp boundaries
    entropy_penalty = SIGMA_ENTROPY_LAMBDA * (log_sigma * loss_mask).pow(2).sum() / n_loss
    return base_loss + entropy_penalty


def masked_huber(
    pred_mean: torch.Tensor,
    true: torch.Tensor,
    loss_mask: torch.Tensor,
    delta: float = HUBER_DELTA,
) -> torch.Tensor:
    """
    Huber loss on loss_mask cells (no variance head used in optimization).

    Robust to outliers; does not suffer from variance collapse.

    Args:
        pred_mean:  (n_T, n_S, n_Y) model predictions (only mean output used)
        true:       (n_T, n_S, n_Y) ground truth
        loss_mask:  float mask
        delta:      Huber threshold (FROZEN: 1.0)
    """
    abs_err = (pred_mean - true).abs()
    huber = torch.where(
        abs_err <= delta,
        0.5 * abs_err ** 2,
        delta * (abs_err - 0.5 * delta),
    )
    n_loss = loss_mask.sum().clamp(min=1)
    return (huber * loss_mask).sum() / n_loss


def masked_mse(
    pred_mean: torch.Tensor,
    true: torch.Tensor,
    loss_mask: torch.Tensor,
) -> torch.Tensor:
    """MSE on loss_mask cells. Diagnostic baseline only (R3)."""
    sq = (pred_mean - true) ** 2
    n_loss = loss_mask.sum().clamp(min=1)
    return (sq * loss_mask).sum() / n_loss


def log_sigma_stats(
    pred_log_sigma: torch.Tensor,
    loss_mask: torch.Tensor,
) -> dict[str, float]:
    """Return min/mean/max of log_sigma on loss cells (diagnostic)."""
    masked = pred_log_sigma.detach()[loss_mask.bool()]
    if masked.numel() == 0:
        return {"log_sigma_min": float("nan"), "log_sigma_mean": float("nan"), "log_sigma_max": float("nan")}
    return {
        "log_sigma_min": masked.min().item(),
        "log_sigma_mean": masked.mean().item(),
        "log_sigma_max": masked.max().item(),
    }
