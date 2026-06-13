"""
adapter.py — Adapter architecture and freeze policies for DEC-047.

Architecture: HERALDGraphImputerLagged + optional bottleneck adapter injected
into the decoder MLP. The base model (herald_graph_imputer_lagged.py) is NOT
modified. The adapter wraps model.net in-place.

Original net structure (indices after model construction):
  0: Linear(10, 64)
  1: ReLU
  2: Dropout(0.1)
  3: Linear(64, 32)
  4: ReLU
  5: Linear(32, 2)

After inject_adapter (7 layers):
  0: Linear(10, 64)
  1: ReLU
  2: Dropout(0.1)
  3: Linear(64, 32)
  4: ReLU
  5: AdapterBottleneck(32, bottleneck=16)  -- new
  6: Linear(32, 2)

Bypass: set adapter.enabled=False to reproduce exact original behavior.

Strategies:
  Z0: freeze all (no adaptation)
  A1: freeze attention, unfreeze net (all of net)
  A2: freeze attention + net[0..4], unfreeze adapter + net[6]
  A3: freeze net[0], unfreeze attention + net[3..5]
  A4: unfreeze all
  C0: freeze attention (adj=0 used externally), unfreeze net — same as A1 freeze policy
  P0: freeze attention (permuted adj used externally), unfreeze net — same as A1 freeze policy
"""

from __future__ import annotations

import torch
import torch.nn as nn

from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged


# ── Adapter module ─────────────────────────────────────────────────────────────

class AdapterBottleneck(nn.Module):
    """
    Bottleneck adapter with residual connection.
    x → Linear(dim, bottleneck) → GELU → Linear(bottleneck, dim) → + x

    Param count: 2 * dim * bottleneck + dim + bottleneck
      = dim*bottleneck (W1) + bottleneck (b1) + bottleneck*dim (W2) + dim (b2)

    When enabled=False, acts as identity (bypass).
    """

    def __init__(self, dim: int, bottleneck: int = 16, enabled: bool = True) -> None:
        super().__init__()
        self.dim = dim
        self.bottleneck = bottleneck
        self.enabled = enabled
        self.down = nn.Linear(dim, bottleneck)
        self.act = nn.GELU()
        self.up = nn.Linear(bottleneck, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not self.enabled:
            return x
        return x + self.up(self.act(self.down(x)))

    @property
    def n_params(self) -> int:
        return 2 * self.dim * self.bottleneck + self.dim + self.bottleneck


# ── Adapter injection ──────────────────────────────────────────────────────────

def inject_adapter(
    model: HERALDGraphImputerLagged,
    bottleneck: int = 16,
) -> AdapterBottleneck:
    """
    Replace model.net with version containing AdapterBottleneck after index 4.
    In-place modification. Returns the adapter module.

    Before: [L0, ReLU, Drop, L3, ReLU, L5]
    After:  [L0, ReLU, Drop, L3, ReLU, Adapter, L5]
    """
    old_net = model.net
    layers = list(old_net.children())
    assert len(layers) == 6, (
        f"Expected 6 layers in model.net, got {len(layers)}. "
        "Do not call inject_adapter twice."
    )
    adapter = AdapterBottleneck(32, bottleneck, enabled=True)
    new_net = nn.Sequential(
        layers[0], layers[1], layers[2], layers[3], layers[4],
        adapter,
        layers[5],
    )
    model.net = new_net
    return adapter


def has_adapter(model: HERALDGraphImputerLagged) -> bool:
    """Return True if adapter has already been injected."""
    layers = list(model.net.children())
    return any(isinstance(l, AdapterBottleneck) for l in layers)


# ── Freeze helpers ─────────────────────────────────────────────────────────────

def freeze_attention(model: HERALDGraphImputerLagged) -> None:
    """Freeze log_sect_attn_lag1, log_sect_attn_lag2, log_terr_attn."""
    for param in [model.log_sect_attn_lag1, model.log_sect_attn_lag2, model.log_terr_attn]:
        param.requires_grad_(False)


def unfreeze_attention(model: HERALDGraphImputerLagged) -> None:
    """Unfreeze attention params."""
    for param in [model.log_sect_attn_lag1, model.log_sect_attn_lag2, model.log_terr_attn]:
        param.requires_grad_(True)


def freeze_all(model: nn.Module) -> None:
    """Freeze all parameters."""
    for p in model.parameters():
        p.requires_grad_(False)


def unfreeze_all(model: nn.Module) -> None:
    """Unfreeze all parameters."""
    for p in model.parameters():
        p.requires_grad_(True)


def freeze_encoder_first_layer(model: HERALDGraphImputerLagged) -> None:
    """Freeze net[0] (Linear 10→64)."""
    layers = list(model.net.children())
    for p in layers[0].parameters():
        p.requires_grad_(False)


def unfreeze_encoder_first_layer(model: HERALDGraphImputerLagged) -> None:
    """Unfreeze net[0] (Linear 10→64)."""
    layers = list(model.net.children())
    for p in layers[0].parameters():
        p.requires_grad_(True)


def freeze_net_except_adapter_and_output(model: HERALDGraphImputerLagged) -> None:
    """
    For A2: freeze net[0..4], unfreeze net[5] (adapter) and net[6] (output).
    Assumes inject_adapter has been called (7 layers total).
    """
    layers = list(model.net.children())
    assert len(layers) == 7, f"Expected 7 layers (adapter injected), got {len(layers)}"
    # Freeze indices 0..4
    for i in range(5):
        for p in layers[i].parameters():
            p.requires_grad_(False)
    # Unfreeze adapter (index 5) and output (index 6)
    for i in [5, 6]:
        for p in layers[i].parameters():
            p.requires_grad_(True)


# ── Param audit ───────────────────────────────────────────────────────────────

def audit_trainable_params(model: nn.Module) -> dict:
    """
    Returns dict with per-named-parameter trainability and totals.
    {
      "params": {name: {"n_params": int, "trainable": bool}},
      "total_trainable": int,
      "total_frozen": int,
      "total": int,
    }
    """
    result: dict = {"params": {}, "total_trainable": 0, "total_frozen": 0, "total": 0}
    for name, p in model.named_parameters():
        n = p.numel()
        trainable = p.requires_grad
        result["params"][name] = {"n_params": n, "trainable": trainable}
        result["total"] += n
        if trainable:
            result["total_trainable"] += n
        else:
            result["total_frozen"] += n
    return result


# ── Strategy factory ──────────────────────────────────────────────────────────

def apply_strategy_freeze(
    model: HERALDGraphImputerLagged,
    strategy: str,
    bottleneck: int = 16,
) -> dict:
    """
    Apply freeze/unfreeze policy for given strategy.
    Inserts adapter if strategy is A2.
    Returns audit dict from audit_trainable_params.

    Z0: freeze all (no adaptation)
    A1: freeze attention, unfreeze net (all of net)
    A2: freeze attention, inject adapter, freeze net[0..4], unfreeze adapter+net[6]
    A3: freeze net[0] (encoder first layer), unfreeze attention + net (rest unfrozen)
    A4: unfreeze all
    C0: same freeze policy as A1 (adj=0 applied externally by caller)
    P0: same freeze policy as A1 (permuted adj applied externally by caller)
    B0: not a model strategy — ForwardFill baseline (no freeze needed)
    B1: not a model strategy — Ridge baseline (no freeze needed)
    """
    valid = {"Z0", "A1", "A2", "A3", "A4", "C0", "P0"}
    if strategy not in valid:
        raise ValueError(f"Unknown strategy: {strategy!r}. Valid: {valid}")

    if strategy == "Z0":
        freeze_all(model)

    elif strategy in {"A1", "C0", "P0"}:
        unfreeze_all(model)
        freeze_attention(model)

    elif strategy == "A2":
        # Inject adapter if not already present
        if not has_adapter(model):
            inject_adapter(model, bottleneck=bottleneck)
        unfreeze_all(model)
        freeze_attention(model)
        freeze_net_except_adapter_and_output(model)

    elif strategy == "A3":
        unfreeze_all(model)
        freeze_encoder_first_layer(model)
        # Attention unfrozen — can adjust
        # net[3..5] (or [3..6] if adapter) unfrozen — decoder can adjust
        # net[0] frozen — 10→64 projection frozen

    elif strategy == "A4":
        unfreeze_all(model)

    return audit_trainable_params(model)
