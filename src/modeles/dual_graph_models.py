"""HERALD — Frugal dual-graph model for sector-territory dynamics.

Implements the model frozen in
``reports/HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md`` (FROZEN_V2).

Scope
-----
France NUTS3, 101 regions, 9 A10 sectors, evaluation 2021-2025.
This is NOT a residual correction of the total-birth Ridge. The model learns
node states ``(B,R,S,H)`` and predicts sector-level dynamics:

  - ``pred_log_growth``  : continuous log-growth regression
  - ``regime_logits``    : 3-class direction (decline / stagnation / growth)
  - ``recovery_logits``  : binary recovery transition
  - ``emergence_logits`` : binary emergence

Graphs
------
Territory graph: observed, per-sector NUTS3 co-growth adjacency supplied in the
tensors as ``territory_adj_seq (B,T,S,R,R)`` with availability mask
``territory_adj_mask (B,T,S)``. Message passing is degree-normalised 1-hop over
regions, *within each sector*. When ``territory_adj_mask=0`` the territory
message is disabled (set to zero) and only the temporal self-state path remains;
no synthetic edge is inserted.

Sector graph: a small LEARNED symmetric ``(S,S)`` adjacency with zero diagonal,
non-negative weights and L1 sparsity + temporal-stability regularization. The
old observable L1 layer is never loaded or reused. An optional causal time
modulation from past sector states is available and stays within budget.

Rules (contract §6)
-------------------
  - one temporal recurrent layer;
  - hidden width in {4, 8};
  - at most 10,000 trainable parameters;
  - dropout >= 0.3;
  - parameters shared across territories (no per-region parameter);
  - no bounded residual around any total-birth Ridge;
  - graph use is toggled by zeroing messages, keeping capacity equal across the
    no-graph / territory-only / sector-only / dual controls.

Shape conventions (local variables)
-----------------------------------
  B  = batch (samples)        R  = regions (101)
  T  = sequence steps (5)     S  = sectors (9)
  NF = features (6)           H  = hidden width
  E  = sector embedding dim
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Masked pooling helpers
# ---------------------------------------------------------------------------

def _masked_mean(state: torch.Tensor, mask: torch.Tensor, dim: int) -> torch.Tensor:
    """Masked mean of ``state`` along ``dim`` using boolean ``mask``.

    ``mask`` must broadcast to ``state`` without the trailing feature axis.
    Returns zeros (not NaN) where a slice has no valid element, so downstream
    embeddings stay finite for isolated territories or sectors.
    """
    m = mask.unsqueeze(-1).to(state.dtype)
    num = (state * m).sum(dim=dim)
    den = m.sum(dim=dim).clamp(min=1.0)
    return num / den


def _clean_features(
    features: torch.Tensor,       # (B, R, S, NF)
    feature_mask: torch.Tensor,   # (B, R, S, NF)
    struct_mask: torch.Tensor,    # (B, R, S)
) -> tuple[torch.Tensor, torch.Tensor]:
    """Zero-fill invalid feature values and return a per-node validity mask.

    A node is valid at this step if it is structurally present and at least one
    feature is observed. Absent values never enter as observed zeros.
    """
    feature_valid = feature_mask.bool() & struct_mask.bool().unsqueeze(-1)
    clean = torch.where(
        feature_valid,
        torch.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0),
        torch.zeros_like(features),
    )
    return clean, feature_valid.any(dim=-1)


# ---------------------------------------------------------------------------
# Message passing (parameter-free aggregation)
# ---------------------------------------------------------------------------

def territory_message(
    h: torch.Tensor,           # (B, R, S, H)
    adj: torch.Tensor,         # (B, S, R, R)
    node_valid: torch.Tensor,  # (B, R, S)
    adj_mask: torch.Tensor,    # (B, S)
) -> torch.Tensor:
    """Degree-normalised 1-hop region aggregation, within each sector.

    Neighbours that are invalid at this step are dropped. Isolated nodes
    (degree 0) and sectors whose graph is unavailable (``adj_mask==0``) receive
    a zero message — the self-state path lives in the GRU recurrence, so no
    self-edge is added here and no synthetic edge is inserted.
    """
    B, R, S, H = h.shape
    h_bsrh = h.permute(0, 2, 1, 3).reshape(B * S, R, H)        # (BS, R, H)
    adj_bsrr = adj.reshape(B * S, R, R)
    valid_bsr = node_valid.permute(0, 2, 1).reshape(B * S, R)
    adj_bsrr = adj_bsrr * valid_bsr.unsqueeze(1).to(adj_bsrr.dtype)

    w_sum = torch.bmm(adj_bsrr, h_bsrh)                         # (BS, R, H)
    deg = adj_bsrr.sum(dim=-1, keepdim=True)                    # (BS, R, 1)
    msg = w_sum / deg.clamp(min=1.0)
    msg = torch.where(deg > 0, msg, torch.zeros_like(msg))
    msg = msg.reshape(B, S, R, H).permute(0, 2, 1, 3)          # (B, R, S, H)

    gate = adj_mask.to(h.dtype).view(B, 1, S, 1)               # disable masked sectors
    return msg * gate


def sector_message(
    h: torch.Tensor,           # (B, R, S, H)
    adj: torch.Tensor,         # (B, S, S)
    node_valid: torch.Tensor,  # (B, R, S)
) -> torch.Tensor:
    """Degree-normalised aggregation across sectors, within each region.

    ``adj[b,i,j]`` is the learned weight between sectors i and j. The message
    for sector i is the degree-normalised sum of valid neighbour sector states.
    """
    valid = node_valid.unsqueeze(-1).to(h.dtype)               # (B, R, S, 1)
    hv = h * valid
    w_sum = torch.einsum("bij,brjh->brih", adj, hv)            # (B, R, S, H)
    deg = torch.einsum("bij,brj->bri", adj, node_valid.to(adj.dtype))  # (B,R,S)
    msg = w_sum / deg.unsqueeze(-1).clamp(min=1.0)
    msg = torch.where(deg.unsqueeze(-1) > 0, msg, torch.zeros_like(msg))
    return msg


# ---------------------------------------------------------------------------
# Dual-graph model
# ---------------------------------------------------------------------------

class DualGraphModel(nn.Module):
    """Frugal recurrent dual-graph model for sector-territory dynamics.

    One GRUCell evolves node states ``(B,R,S,H)`` over ``T`` steps. At each
    step the GRU input concatenates the cleaned features, the sector identity
    embedding, the territory message and the sector message. Graph channels are
    toggled by zeroing their message, so the four scientific controls
    (no-graph / territory-only / sector-only / dual) share identical capacity.
    """

    def __init__(
        self,
        n_sectors: int = 9,
        n_features: int = 6,
        hidden_dim: int = 8,
        sector_embed_dim: int = 4,
        dropout: float = 0.3,
        use_territory_graph: bool = True,
        use_sector_graph: bool = True,
        temporal_sector_graph: bool = False,
    ) -> None:
        super().__init__()
        if hidden_dim not in (4, 8):
            raise ValueError(f"hidden_dim must be 4 or 8 (contract §6); got {hidden_dim}")
        self.n_sectors = n_sectors
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.use_territory_graph = use_territory_graph
        self.use_sector_graph = use_sector_graph
        self.temporal_sector_graph = temporal_sector_graph

        self.sector_embed = nn.Embedding(n_sectors, sector_embed_dim)

        # Learned sector graph base (symmetric, zero-diagonal after transform).
        self.sector_base = nn.Parameter(torch.full((n_sectors, n_sectors), -2.0))
        self.register_buffer(
            "_offdiag", 1.0 - torch.eye(n_sectors), persistent=False
        )
        if temporal_sector_graph:
            # Optional causal time modulation from the previous-step context.
            self.sector_modulation = nn.Linear(hidden_dim, n_sectors * n_sectors)

        # Single temporal layer. Input keeps both message slots at all times so
        # capacity is identical across graph controls.
        gru_in = n_features + sector_embed_dim + 2 * hidden_dim
        self.gru = nn.GRUCell(gru_in, hidden_dim)
        self.drop = nn.Dropout(p=dropout)

        # Task heads (shared across all nodes).
        self.head_log_growth = nn.Linear(hidden_dim, 1)
        self.head_regime = nn.Linear(hidden_dim, 3)
        self.head_recovery = nn.Linear(hidden_dim, 1)
        self.head_emergence = nn.Linear(hidden_dim, 1)

    # -- learned sector adjacency ------------------------------------------

    def _sector_adjacency(self, context: Optional[torch.Tensor], batch: int,
                          device, dtype) -> torch.Tensor:
        """Return one symmetric, non-negative, zero-diagonal ``(B,S,S)`` matrix.

        ``context`` (B,H) optionally modulates the base graph from the previous
        step's sector states (causal). The static base is used otherwise.
        """
        base = F.softplus(self.sector_base)                    # (S, S) >= 0
        adj = base.unsqueeze(0).expand(batch, -1, -1)          # (B, S, S)
        if self.temporal_sector_graph and context is not None:
            mod = self.sector_modulation(context)              # (B, S*S)
            mod = mod.view(batch, self.n_sectors, self.n_sectors)
            adj = F.softplus(self.sector_base.unsqueeze(0) + mod)
        adj = 0.5 * (adj + adj.transpose(-1, -2))              # symmetric
        adj = adj * self._offdiag.to(adj.dtype)               # zero diagonal
        return adj

    # -- forward ------------------------------------------------------------

    def forward(
        self,
        features_seq: torch.Tensor,          # (B, T, R, S, NF)
        feature_mask_seq: torch.Tensor,      # (B, T, R, S, NF)
        territory_adj_seq: torch.Tensor,     # (B, T, S, R, R)
        territory_adj_mask: torch.Tensor,    # (B, T, S)
        struct_mask: Optional[torch.Tensor] = None,  # (B, R, S)
    ) -> dict[str, torch.Tensor]:
        B, T, R, S, NF = features_seq.shape
        device = features_seq.device
        dtype = features_seq.dtype

        if struct_mask is None:
            struct_mask = feature_mask_seq.bool().any(dim=1).any(dim=-1)  # (B,R,S)
        struct_mask = struct_mask.bool()

        s_idx = torch.arange(S, device=device)
        emb = self.sector_embed(s_idx)                         # (S, E)
        emb_full = emb.view(1, 1, S, -1).expand(B, R, S, -1)   # (B, R, S, E)

        h = torch.zeros(B, R, S, self.hidden_dim, device=device, dtype=dtype)
        prev_context = None
        sector_adj_steps: list[torch.Tensor] = []

        for t in range(T):
            sector_adj = self._sector_adjacency(prev_context, B, device, dtype)
            sector_adj_steps.append(sector_adj)

            x_t, node_valid = _clean_features(
                features_seq[:, t], feature_mask_seq[:, t], struct_mask
            )

            if self.use_territory_graph:
                terr_msg = territory_message(
                    h, territory_adj_seq[:, t], node_valid, territory_adj_mask[:, t]
                )
            else:
                terr_msg = torch.zeros_like(h)

            if self.use_sector_graph:
                sect_msg = sector_message(h, sector_adj, node_valid)
            else:
                sect_msg = torch.zeros_like(h)

            inp = torch.cat([x_t, emb_full, terr_msg, sect_msg], dim=-1)
            candidate = self.gru(
                inp.reshape(B * R * S, -1),
                h.reshape(B * R * S, self.hidden_dim),
            ).reshape(B, R, S, self.hidden_dim)
            h = torch.where(node_valid.unsqueeze(-1), candidate, h)

            # Causal context for the next step's sector-graph modulation.
            prev_context = _masked_mean(
                _masked_mean(h, node_valid, dim=2), struct_mask.any(dim=2), dim=1
            )

        node_emb = self.drop(h)                                # (B, R, S, H)
        pred_log_growth = self.head_log_growth(node_emb).squeeze(-1)
        regime_logits = self.head_regime(node_emb)             # (B, R, S, 3)
        recovery_logits = self.head_recovery(node_emb).squeeze(-1)
        emergence_logits = self.head_emergence(node_emb).squeeze(-1)

        territory_emb = _masked_mean(h, struct_mask, dim=2)    # (B, R, H)
        sector_emb = _masked_mean(h.transpose(1, 2), struct_mask.transpose(1, 2), dim=2)

        sector_adj_learned = torch.stack(sector_adj_steps, dim=1)  # (B, T, S, S)

        return {
            "pred_log_growth": pred_log_growth,
            "regime_logits": regime_logits,
            "recovery_logits": recovery_logits,
            "emergence_logits": emergence_logits,
            "node_embeddings": node_emb,
            "territory_embeddings": territory_emb,
            "sector_embeddings": sector_emb,
            "sector_adj_learned": sector_adj_learned,
        }


# ---------------------------------------------------------------------------
# Losses (contract §7)
# ---------------------------------------------------------------------------

def masked_huber_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    delta: float = 1.0,
) -> torch.Tensor:
    """Masked Huber loss for log-growth. WMAPE is forbidden for growth rates."""
    m = mask.bool() & torch.isfinite(target) & torch.isfinite(pred)
    if not m.any():
        return pred.sum() * 0.0
    return F.huber_loss(pred[m], target[m], delta=delta, reduction="mean")


def weighted_ce_loss(
    logits: torch.Tensor,         # (B, R, S, C)
    target: torch.Tensor,         # (B, R, S) int, -1 = missing
    mask: torch.Tensor,           # (B, R, S)
    class_weights: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    """Weighted cross-entropy for the 3-class regime head."""
    valid = mask.bool() & (target >= 0)
    if not valid.any():
        return logits.sum() * 0.0
    return F.cross_entropy(logits[valid], target[valid], weight=class_weights)


def weighted_bce_loss(
    logits: torch.Tensor,         # (B, R, S)
    target: torch.Tensor,         # (B, R, S) int, -1 = missing
    mask: torch.Tensor,           # (B, R, S)
    pos_weight: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    """Weighted BCE-with-logits for binary recovery / emergence heads."""
    valid = mask.bool() & (target >= 0)
    if not valid.any():
        return logits.sum() * 0.0
    return F.binary_cross_entropy_with_logits(
        logits[valid], target[valid].to(logits.dtype), pos_weight=pos_weight
    )


def sector_graph_sparsity(sector_adj_learned: torch.Tensor) -> torch.Tensor:
    """L1 sparsity penalty on the learned sector adjacency (off-diagonal)."""
    return sector_adj_learned.abs().mean()


def sector_graph_stability(sector_adj_learned: torch.Tensor) -> torch.Tensor:
    """Temporal-variation penalty across consecutive sequence steps."""
    if sector_adj_learned.shape[1] < 2:
        return sector_adj_learned.sum() * 0.0
    diff = sector_adj_learned[:, 1:] - sector_adj_learned[:, :-1]
    return diff.abs().mean()


def compute_class_weights(
    labels: torch.Tensor,
    n_classes: int,
) -> torch.Tensor:
    """Inverse-frequency class weights from training labels only (ignores -1)."""
    flat = labels.reshape(-1)
    flat = flat[flat >= 0]
    counts = torch.zeros(n_classes, dtype=torch.float64)
    for c in range(n_classes):
        counts[c] = float((flat == c).sum())
    counts = counts.clamp(min=1.0)
    weights = counts.sum() / (n_classes * counts)
    return weights.to(torch.float32)


def compute_pos_weight(labels: torch.Tensor) -> torch.Tensor:
    """Positive-class weight (#neg / #pos) for a binary head; training only."""
    flat = labels.reshape(-1)
    flat = flat[flat >= 0]
    pos = float((flat == 1).sum())
    neg = float((flat == 0).sum())
    return torch.tensor(neg / max(pos, 1.0), dtype=torch.float32)


# Fixed loss coefficients (frozen before any full run; contract §7).
LOSS_COEFFICIENTS = {
    "regime": 0.20,
    "recovery": 0.10,
    "emergence": 0.05,
    "lambda_sparse": 1e-3,
    "lambda_stable": 1e-3,
}


def dual_graph_loss(
    outputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    target_mask: torch.Tensor,
    class_weights: Optional[torch.Tensor] = None,
    recovery_pos_weight: Optional[torch.Tensor] = None,
    emergence_pos_weight: Optional[torch.Tensor] = None,
    coef: Optional[dict[str, float]] = None,
) -> dict[str, torch.Tensor]:
    """Assemble the four-task loss plus graph regularization (contract §7)."""
    c = coef if coef is not None else LOSS_COEFFICIENTS

    l_growth = masked_huber_loss(
        outputs["pred_log_growth"], targets["target_log_growth"], target_mask
    )
    l_regime = weighted_ce_loss(
        outputs["regime_logits"], targets["target_regime"], target_mask, class_weights
    )
    l_recovery = weighted_bce_loss(
        outputs["recovery_logits"], targets["target_recovery"], target_mask,
        recovery_pos_weight,
    )
    l_emergence = weighted_bce_loss(
        outputs["emergence_logits"], targets["target_emergence"], target_mask,
        emergence_pos_weight,
    )
    l_sparse = sector_graph_sparsity(outputs["sector_adj_learned"])
    l_stable = sector_graph_stability(outputs["sector_adj_learned"])

    total = (
        l_growth
        + c["regime"] * l_regime
        + c["recovery"] * l_recovery
        + c["emergence"] * l_emergence
        + c["lambda_sparse"] * l_sparse
        + c["lambda_stable"] * l_stable
    )
    return {
        "total": total,
        "growth": l_growth,
        "regime": l_regime,
        "recovery": l_recovery,
        "emergence": l_emergence,
        "sparse": l_sparse,
        "stable": l_stable,
    }


# ---------------------------------------------------------------------------
# Factory / utilities
# ---------------------------------------------------------------------------

def build_dual_graph_model(
    hidden_dim: int = 8,
    use_territory_graph: bool = True,
    use_sector_graph: bool = True,
    temporal_sector_graph: bool = False,
    n_features: int = 6,
    n_sectors: int = 9,
    sector_embed_dim: int = 4,
    dropout: float = 0.3,
) -> DualGraphModel:
    """Instantiate a dual-graph model with contract-compliant defaults."""
    return DualGraphModel(
        n_sectors=n_sectors,
        n_features=n_features,
        hidden_dim=hidden_dim,
        sector_embed_dim=sector_embed_dim,
        dropout=dropout,
        use_territory_graph=use_territory_graph,
        use_sector_graph=use_sector_graph,
        temporal_sector_graph=temporal_sector_graph,
    )


def count_parameters(model: nn.Module) -> int:
    """Count trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
