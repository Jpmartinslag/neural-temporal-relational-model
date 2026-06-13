"""
decoder_ablation.py — Diagnostic ablation of MLP decoder functional form (DEC-047 §10).

Three decoder variants (same input dimension 10, same output dimension 2):
  - linear   : single Linear(10, 2) — test if linear decoder is the bottleneck
  - mlp_relu : current architecture (Linear→ReLU→Dropout→Linear→ReLU→Linear)
  - mlp_gelu : same as current but with GELU instead of ReLU

NOT used for model selection. Diagnostic only.
Hypothesis: if linear decoder performs similarly to MLP, the bottleneck is the
functional form of nonlinear aggregation, not the decoder architecture.
(Hypothesis to verify by ablation — DEC-047 §10)

Note on dimensions:
  hidden_in=10 matches the 10-feature input (7 temporal + 3 graph) of
  HERALDGraphImputerLagged. hidden_dim=64 matches the base model.
"""

from __future__ import annotations

import torch.nn as nn

from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged


def build_decoder_linear(hidden_in: int = 10) -> nn.Sequential:
    """Single linear layer decoder. Minimal param count."""
    return nn.Sequential(nn.Linear(hidden_in, 2))


def build_decoder_mlp_relu(
    hidden_in: int = 10,
    hidden_dim: int = 64,
    dropout: float = 0.1,
) -> nn.Sequential:
    """Current architecture — same as HERALDGraphImputerLagged.net."""
    return nn.Sequential(
        nn.Linear(hidden_in, hidden_dim),
        nn.ReLU(),
        nn.Dropout(dropout),
        nn.Linear(hidden_dim, hidden_dim // 2),
        nn.ReLU(),
        nn.Linear(hidden_dim // 2, 2),
    )


def build_decoder_mlp_gelu(
    hidden_in: int = 10,
    hidden_dim: int = 64,
    dropout: float = 0.1,
) -> nn.Sequential:
    """GELU variant — potentially better for nonlinear relations (tanh-type)."""
    return nn.Sequential(
        nn.Linear(hidden_in, hidden_dim),
        nn.GELU(),
        nn.Dropout(dropout),
        nn.Linear(hidden_dim, hidden_dim // 2),
        nn.GELU(),
        nn.Linear(hidden_dim // 2, 2),
    )


def count_decoder_params(net: nn.Sequential) -> int:
    """Total parameter count for a decoder Sequential."""
    return sum(p.numel() for p in net.parameters())


def replace_decoder(model: HERALDGraphImputerLagged, new_net: nn.Sequential) -> None:
    """
    Replace model.net in-place. Attention params (log_sect_attn_lag1/lag2,
    log_terr_attn) are preserved. Only the MLP decoder is replaced.

    Caller is responsible for ensuring new_net accepts 10-dim input and
    produces 2-dim output (mean, log_sigma).
    """
    model.net = new_net


DECODER_VARIANTS: dict[str, callable] = {
    "linear": build_decoder_linear,
    "mlp_relu": build_decoder_mlp_relu,
    "mlp_gelu": build_decoder_mlp_gelu,
}


def build_decoder(variant: str, **kwargs) -> nn.Sequential:
    """
    Build decoder by variant name.
    variant: one of 'linear', 'mlp_relu', 'mlp_gelu'.
    """
    if variant not in DECODER_VARIANTS:
        raise ValueError(f"Unknown decoder variant: {variant!r}. Valid: {list(DECODER_VARIANTS)}")
    return DECODER_VARIANTS[variant](**kwargs)
