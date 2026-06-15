"""
context_adapter.py — LocalContextAdapter for DEC-055.

Small MLP that maps observable environment features to an ADDITIVE residual
for the shared encoder embedding.

Invariants (DEC-055):
  - No parameter indexed by sector pair
  - No S×S lookup table
  - No pair identity in inputs
  - Input is ONLY observable data statistics (no ground truth)
  - Adapter cannot replace encoder — only adds a small residual
  - For unseen environments: zeros residual (transparent fallback)
  - Tested: adapter + adapter absent (control comparison)

Input features (6, computed from observable data via compute_env_context_features):
  [obs_fraction, activity_mean, activity_std, crisis_severity, vol_change, block_frac]

Output: (ENCODER_HIDDEN2,) additive residual clamped to [-MAX_RESIDUAL, +MAX_RESIDUAL]
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from src.modeles.synthetic.phase16_decoupled.shared_relation_encoder import (
    ENCODER_HIDDEN2,
    compute_env_context_features,
)

ENV_FEATURE_DIM: int = 6
ADAPTER_HIDDEN: int = 16
MAX_ADAPTER_RESIDUAL: float = 0.5   # clamp ensures adapter can't replace encoder


class LocalContextAdapter(nn.Module):
    """
    Maps observable environment features to a small additive residual.

    The residual is added to the encoder embedding BEFORE the output heads.
    The residual is clamped so the adapter cannot overpower the encoder.

    No pair-specific parameters. Generalizes to unseen environments IF
    the env features are informative — no memorization possible.
    """

    def __init__(
        self,
        env_feature_dim: int = ENV_FEATURE_DIM,
        hidden: int = ADAPTER_HIDDEN,
        output_dim: int = ENCODER_HIDDEN2,
        max_residual: float = MAX_ADAPTER_RESIDUAL,
    ):
        super().__init__()
        self.max_residual = max_residual
        self.net = nn.Sequential(
            nn.Linear(env_feature_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, output_dim),
            nn.Tanh(),   # output in (-1, +1)
        )
        # Zero-init last layer → starts as identity pass-through (no residual)
        nn.init.zeros_(self.net[-2].weight)
        nn.init.zeros_(self.net[-2].bias)

    def forward(self, env_features: torch.Tensor) -> torch.Tensor:
        """
        env_features: (ENV_FEATURE_DIM,) or (batch, ENV_FEATURE_DIM)
        Returns: (ENCODER_HIDDEN2,) or (batch, ENCODER_HIDDEN2) — clamped residual
        """
        residual = self.net(env_features)
        return residual.clamp(-self.max_residual, self.max_residual)

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def assert_no_pair_params(self, max_sector_size: int = 20) -> None:
        """S2 check: no parameter shaped (n, n) for 1 < n <= max_sector_size."""
        for name, p in self.named_parameters():
            shape = tuple(p.shape)
            if (len(shape) == 2 and shape[0] == shape[1]
                    and 1 < shape[0] <= max_sector_size):
                raise AssertionError(
                    f"Pair-specific parameter in adapter: {name} shape {shape}"
                )


def make_adapter_fn(
    adapter: LocalContextAdapter,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    device: str = "cpu",
    enabled: bool = True,
):
    """
    Returns a closure: env_features → adapter_residual.
    If enabled=False, returns None (no adapter, for ablation control).
    For UNSEEN environments (OOS), caller passes enabled=False or provides
    the same closure (adapter generalizes from observable features).
    """
    if not enabled:
        return None

    env_feats = compute_env_context_features(panel, obs_mask)
    env_t = torch.from_numpy(env_feats).to(device)

    def _fn(_: torch.Tensor) -> torch.Tensor:
        return adapter(env_t)

    return _fn


def compute_adapter_residual(
    adapter: LocalContextAdapter,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    device: str = "cpu",
) -> torch.Tensor:
    """Compute adapter residual from observable environment features."""
    env_feats = compute_env_context_features(panel, obs_mask)
    env_t = torch.from_numpy(env_feats).to(device)
    with torch.no_grad():
        return adapter(env_t)
