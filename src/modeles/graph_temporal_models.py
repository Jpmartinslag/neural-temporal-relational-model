"""HERALD DEC-028 — Graph-temporal model architectures.

Implements exactly three models as specified in
HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md:

  A0Neural   — GRU per (region, sector), no message passing.
  GConvGRU   — A1a: 1-hop degree-normalised aggregation + GRU gating.
  EvolveGCNH — A1b: GRU evolves GCN weight matrix (H variant).

All share:
  - same input/output interface (§1–2 of contract)
  - masked mean pooling of sector states → territory state (§3.1)
  - bounded residual head: delta_bounded = clamp(delta_raw, ±frac*max(ridge,0)) (§3.2)
  - sector identity embedding, shared weights across sectors (§3.7)
  - dropout ≥ 0.3 before residual head (§3.10)
  - ≤ 5000 trainable parameters (§3.6)

Shape conventions (local variables):
  B  = batch size
  T  = time steps (T_SEQ = 5)
  R  = regions
  S  = sectors
  NF = number of features (named NF to avoid shadowing torch.nn.functional as F)
  H  = hidden_dim
  E  = sector_embed_dim
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def masked_mean_pool(
    sector_state: torch.Tensor,
    pool_mask: torch.Tensor,
) -> torch.Tensor:
    """Masked mean over sector axis (dim=2).

    sector_state : (B, R, S, H)
    pool_mask    : (B, R, S)   bool
    returns      : (B, R, H)   NaN where all sectors absent for a region
    """
    m = pool_mask.float().unsqueeze(-1)        # (B, R, S, 1)
    num = (sector_state * m).sum(dim=2)         # (B, R, H)
    denom = m.sum(dim=2)                        # (B, R, 1)
    safe = denom.clone()
    safe[safe == 0] = float("nan")
    return num / safe                           # NaN where no valid sector


def build_pool_mask(
    struct_mask: torch.Tensor,       # (B, R, S)
    feature_mask_seq: torch.Tensor,  # (B, T, R, S, NF)
    t: int,
) -> torch.Tensor:
    """Boolean pool mask at time step t: structural & any-feature-valid."""
    feat_any = feature_mask_seq[:, t, :, :, :].any(dim=-1)  # (B, R, S)
    return struct_mask.bool() & feat_any


def mask_features(
    features: torch.Tensor,
    feature_mask: torch.Tensor,
    struct_mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Remove invalid feature values without treating absent sectors as observed.

    Returns zero-filled inputs for numerical computation and a sector-level
    validity mask used to block recurrent updates and graph messages.
    """
    feature_valid = feature_mask.bool() & struct_mask.bool().unsqueeze(-1)
    clean = torch.where(
        feature_valid,
        torch.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0),
        torch.zeros_like(features),
    )
    return clean, feature_valid.any(dim=-1)


def bounded_residual_head(
    delta_raw: torch.Tensor,
    y_ridge: torch.Tensor,
    clamp_frac: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Bounded correction: delta_bounded = clamp(delta_raw, ±frac*max(ridge,0))."""
    ridge_ref = y_ridge.clamp(min=0.0)
    bound = clamp_frac * ridge_ref
    delta_bounded = torch.clamp(delta_raw, -bound, bound)
    return delta_bounded, y_ridge + delta_bounded


def masked_wmape(
    y_hat: torch.Tensor,
    y_true: torch.Tensor,
    target_mask: torch.Tensor,
) -> torch.Tensor:
    """WMAPE = sum|y_hat-y_true| / sum|y_true|, evaluated where target_mask==1."""
    m = target_mask.bool() & torch.isfinite(y_hat) & torch.isfinite(y_true)
    num = (y_hat - y_true).abs()[m].sum()
    denom = y_true.abs()[m].sum().clamp(min=1e-8)
    return num / denom


# ---------------------------------------------------------------------------
# A0-neural — no-graph temporal control (§4)
# ---------------------------------------------------------------------------

class A0Neural(nn.Module):
    """GRU per (region, sector), no message passing.

    h_t[r,s] = GRUCell(concat(x[t,r,s], embed[s]), h_{t-1}[r,s])
    territory[r] = masked_mean_s(h_T[r,s])
    delta_raw[r]  = Linear(dropout(territory[r]))
    """

    def __init__(
        self,
        n_sectors: int = 9,
        n_features: int = 3,
        hidden_dim: int = 8,
        sector_embed_dim: int = 4,
        dropout: float = 0.3,
        clamp_frac: float = 0.15,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.clamp_frac = clamp_frac

        self.sector_embed = nn.Embedding(n_sectors, sector_embed_dim)
        self.gru = nn.GRUCell(n_features + sector_embed_dim, hidden_dim)
        self.drop = nn.Dropout(p=dropout)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        features_seq: torch.Tensor,       # (B, T, R, S, NF)
        feature_mask_seq: torch.Tensor,   # (B, T, R, S, NF)
        struct_mask: torch.Tensor,        # (B, R, S)
        y_ridge_canonical: torch.Tensor,  # (B, R)
        adjacency_seq: Optional[torch.Tensor] = None,  # ignored
    ) -> dict[str, torch.Tensor]:
        B, T, R, S, NF = features_seq.shape
        device = features_seq.device
        dtype = features_seq.dtype

        s_idx = torch.arange(S, device=device)
        emb = self.sector_embed(s_idx)              # (S, E)

        h = torch.zeros(B * R * S, self.hidden_dim, device=device, dtype=dtype)

        for t in range(T):
            x_t, sector_valid = mask_features(
                features_seq[:, t], feature_mask_seq[:, t], struct_mask
            )
            emb_t = emb.view(1, 1, S, -1).expand(B, R, S, -1)    # (B,R,S,E)
            inp = torch.cat([x_t, emb_t], dim=-1)                 # (B,R,S,NF+E)
            candidate = self.gru(inp.reshape(B * R * S, -1), h)
            valid_flat = sector_valid.reshape(B * R * S, 1)
            h = torch.where(valid_flat, candidate, h)

        h_out = h.reshape(B, R, S, self.hidden_dim)               # (B,R,S,H)
        pool_mask = build_pool_mask(struct_mask, feature_mask_seq, T - 1)
        territory = masked_mean_pool(h_out, pool_mask)             # (B,R,H)
        territory = self.drop(territory)
        delta_raw = self.head(territory).squeeze(-1)               # (B,R)

        delta_bounded, y_hat = bounded_residual_head(
            delta_raw, y_ridge_canonical, self.clamp_frac
        )
        return {
            "delta_raw": delta_raw,
            "delta_bounded": delta_bounded,
            "y_hat": y_hat,
            "territory_embeddings": territory,
        }


# ---------------------------------------------------------------------------
# A1a — GConvGRU (§5)
# ---------------------------------------------------------------------------

class GConvGRU(nn.Module):
    """1-hop degree-normalised aggregation of hidden states + GRU gating.

    Per time step t, per sector s:
      deg[r]    = adj[b,t,s,r,:].sum()
      agg[r]    = (sum_j A[r,j]*h[j]) / (deg[r]+1)
                  + h[r] * (deg[r]==0)   ← self-value fallback (DEC-023)
      h_t[r,s]  = GRUCell(concat(x[t,r,s], embed[s], agg[r]), h_{t-1}[r,s])
    """

    def __init__(
        self,
        n_sectors: int = 9,
        n_features: int = 3,
        hidden_dim: int = 8,
        sector_embed_dim: int = 4,
        dropout: float = 0.3,
        clamp_frac: float = 0.15,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.clamp_frac = clamp_frac

        self.sector_embed = nn.Embedding(n_sectors, sector_embed_dim)
        # input = features + embed + aggregated hidden
        self.gru = nn.GRUCell(n_features + sector_embed_dim + hidden_dim, hidden_dim)
        self.drop = nn.Dropout(p=dropout)
        self.head = nn.Linear(hidden_dim, 1)

    @staticmethod
    def _agg_hidden(
        h: torch.Tensor,    # (B, R, S, H)
        adj: torch.Tensor,  # (B, S, R, R)
        node_valid: torch.Tensor,  # (B, R, S)
    ) -> torch.Tensor:
        """Degree-normalised 1-hop aggregation of hidden states → (B,R,S,H)."""
        B, R, S, H = h.shape
        h_bsrh = h.permute(0, 2, 1, 3).reshape(B * S, R, H)   # (BS,R,H)
        adj_bsrr = adj.reshape(B * S, R, R)                    # (BS,R,R)
        valid_bsr = node_valid.permute(0, 2, 1).reshape(B * S, R)
        adj_bsrr = adj_bsrr * valid_bsr.unsqueeze(1).to(adj_bsrr.dtype)

        w_sum = torch.bmm(adj_bsrr, h_bsrh)                   # (BS,R,H)
        deg = adj_bsrr.sum(dim=-1, keepdim=True)               # (BS,R,1)
        agg = w_sum / (deg + 1.0)

        # self-value fallback for isolated nodes (deg==0 → agg=h/1, but
        # w_sum=0 there, so add h directly when deg==0)
        isolated = (deg.squeeze(-1) == 0).float().unsqueeze(-1)  # (BS,R,1)
        agg = agg + h_bsrh * isolated

        return agg.reshape(B, S, R, H).permute(0, 2, 1, 3)    # (B,R,S,H)

    def forward(
        self,
        features_seq: torch.Tensor,       # (B, T, R, S, NF)
        feature_mask_seq: torch.Tensor,   # (B, T, R, S, NF)
        struct_mask: torch.Tensor,        # (B, R, S)
        y_ridge_canonical: torch.Tensor,  # (B, R)
        adjacency_seq: torch.Tensor,      # (B, T, S, R, R)
    ) -> dict[str, torch.Tensor]:
        B, T, R, S, NF = features_seq.shape
        device = features_seq.device
        dtype = features_seq.dtype

        s_idx = torch.arange(S, device=device)
        emb = self.sector_embed(s_idx)                          # (S, E)

        h = torch.zeros(B, R, S, self.hidden_dim, device=device, dtype=dtype)
        h_valid = torch.zeros(B, R, S, device=device, dtype=torch.bool)

        for t in range(T):
            adj_t = adjacency_seq[:, t]                         # (B,S,R,R)
            agg = self._agg_hidden(h, adj_t, h_valid)           # (B,R,S,H)

            x_t, sector_valid = mask_features(
                features_seq[:, t], feature_mask_seq[:, t], struct_mask
            )
            emb_t = emb.view(1, 1, S, -1).expand(B, R, S, -1)
            inp = torch.cat([x_t, emb_t, agg], dim=-1)         # (B,R,S,NF+E+H)

            candidate = self.gru(
                inp.reshape(B * R * S, -1),
                h.reshape(B * R * S, self.hidden_dim),
            ).reshape(B, R, S, self.hidden_dim)
            h = torch.where(sector_valid.unsqueeze(-1), candidate, h)
            h_valid = h_valid | sector_valid

        pool_mask = build_pool_mask(struct_mask, feature_mask_seq, T - 1)
        territory = masked_mean_pool(h, pool_mask)              # (B,R,H)
        territory = self.drop(territory)
        delta_raw = self.head(territory).squeeze(-1)
        zero_graph = adjacency_seq.abs().sum(dim=(1, 2, 3, 4)) == 0
        zero_correction = zero_graph.unsqueeze(-1) & torch.isfinite(delta_raw)
        delta_raw = torch.where(zero_correction, torch.zeros_like(delta_raw), delta_raw)

        delta_bounded, y_hat = bounded_residual_head(
            delta_raw, y_ridge_canonical, self.clamp_frac
        )
        return {
            "delta_raw": delta_raw,
            "delta_bounded": delta_bounded,
            "y_hat": y_hat,
            "territory_embeddings": territory,
        }


# ---------------------------------------------------------------------------
# A1b — EvolveGCN-H (§6)
# ---------------------------------------------------------------------------

class EvolveGCNH(nn.Module):
    """EvolveGCN-H: GRU evolves the GCN weight matrix (Pareja et al., 2020).

    The GCN weight matrix W (shape NF × H) is the GRU hidden state.
    Budget constraint (≤5000 params) requires gcn_in = NF = 3 so that
    w_size = NF*H ∈ {12, 24} keeps the GRU affordable.

    Per time step t, per sector s:
      agg_x[r,s] = deg-normalised mean of neighbour features  (NF)
      graph_in   = project(concat(x_t, agg_x, sector_embed))   (NF)
      context_t  = masked_mean(graph_in)                       (NF)
      W_t        = GRUCell(context_t, W_{t-1}_flat).reshape(NF, H)
      h_t[r,s]   = relu(graph_in[r,s] @ W_t + bias)            (H)

    A small shared projection preserves the contract's explicit concatenation
    while keeping the evolved matrix below the 5,000-parameter budget.
    Neighbour aggregation is degree-normalised 1-hop on raw features,
    with self-value fallback for isolated nodes (DEC-023).
    """

    def __init__(
        self,
        n_sectors: int = 9,
        n_features: int = 3,
        hidden_dim: int = 8,
        sector_embed_dim: int = 4,
        dropout: float = 0.3,
        clamp_frac: float = 0.15,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.clamp_frac = clamp_frac

        self.sector_embed = nn.Embedding(n_sectors, sector_embed_dim)
        self.input_proj = nn.Linear(
            2 * n_features + sector_embed_dim, n_features
        )

        # W maps NF → H; w_size = NF * H (12 or 24 for H=4/8)
        self.gcn_in = n_features                               # NF = 3
        self.w_size = n_features * hidden_dim
        self.gru_evolve = nn.GRUCell(
            input_size=n_features,   # context = mean of (x + agg_x)
            hidden_size=self.w_size,
        )
        self.gcn_bias = nn.Parameter(torch.zeros(hidden_dim))
        self.drop = nn.Dropout(p=dropout)
        self.head = nn.Linear(hidden_dim, 1)

    @staticmethod
    def _agg_features(
        x: torch.Tensor,    # (B, R, S, NF)
        adj: torch.Tensor,  # (B, S, R, R)
        node_valid: torch.Tensor,  # (B, R, S)
    ) -> torch.Tensor:
        """Degree-normalised 1-hop mean of raw features → (B,R,S,NF).
        Self-value fallback for isolated nodes."""
        B, R, S, NF = x.shape
        x_bsrnf = x.permute(0, 2, 1, 3).reshape(B * S, R, NF)
        adj_bsrr = adj.reshape(B * S, R, R)
        valid_bsr = node_valid.permute(0, 2, 1).reshape(B * S, R)
        adj_bsrr = adj_bsrr * valid_bsr.unsqueeze(1).to(adj_bsrr.dtype)

        w_sum = torch.bmm(adj_bsrr, x_bsrnf)
        deg = adj_bsrr.sum(dim=-1, keepdim=True)
        agg = w_sum / (deg + 1.0)
        isolated = (deg.squeeze(-1) == 0).float().unsqueeze(-1)
        agg = agg + x_bsrnf * isolated

        return agg.reshape(B, S, R, NF).permute(0, 2, 1, 3)   # (B,R,S,NF)

    def forward(
        self,
        features_seq: torch.Tensor,       # (B, T, R, S, NF)
        feature_mask_seq: torch.Tensor,   # (B, T, R, S, NF)
        struct_mask: torch.Tensor,        # (B, R, S)
        y_ridge_canonical: torch.Tensor,  # (B, R)
        adjacency_seq: torch.Tensor,      # (B, T, S, R, R)
    ) -> dict[str, torch.Tensor]:
        B, T, R, S, NF = features_seq.shape
        device = features_seq.device
        dtype = features_seq.dtype

        s_idx = torch.arange(S, device=device)
        emb = self.sector_embed(s_idx)                          # (S, E)

        W_flat = torch.zeros(B, self.w_size, device=device, dtype=dtype)
        h_final = torch.zeros(B, R, S, self.hidden_dim, device=device, dtype=dtype)

        for t in range(T):
            x_t, sector_valid = mask_features(
                features_seq[:, t], feature_mask_seq[:, t], struct_mask
            )
            adj_t = adjacency_seq[:, t]                           # (B,S,R,R)

            agg_x = self._agg_features(x_t, adj_t, sector_valid)  # (B,R,S,NF)
            emb_t = emb.view(1, 1, S, -1).expand(B, R, S, -1)
            graph_in = self.input_proj(torch.cat([x_t, agg_x, emb_t], dim=-1))

            valid = sector_valid.unsqueeze(-1)
            context_num = torch.where(
                valid, graph_in, torch.zeros_like(graph_in)
            ).sum(dim=(1, 2))
            context_den = valid.sum(dim=(1, 2)).clamp(min=1)
            context = context_num / context_den

            # Evolve W
            W_flat = self.gru_evolve(context, W_flat)            # (B, w_size)
            W = W_flat.reshape(B, NF, self.hidden_dim)           # (B, NF, H)

            # GCN: (B,R,S,NF) @ (B,NF,H) → (B,R,S,H)
            h_t = torch.einsum("brsd,bdh->brsh", graph_in, W) + self.gcn_bias
            candidate = F.relu(h_t)
            h_final = torch.where(valid, candidate, h_final)

        pool_mask = build_pool_mask(struct_mask, feature_mask_seq, T - 1)
        territory = masked_mean_pool(h_final, pool_mask)         # (B,R,H)
        territory = self.drop(territory)
        delta_raw = self.head(territory).squeeze(-1)             # (B,R)
        zero_graph = adjacency_seq.abs().sum(dim=(1, 2, 3, 4)) == 0
        zero_correction = zero_graph.unsqueeze(-1) & torch.isfinite(delta_raw)
        delta_raw = torch.where(zero_correction, torch.zeros_like(delta_raw), delta_raw)

        delta_bounded, y_hat = bounded_residual_head(
            delta_raw, y_ridge_canonical, self.clamp_frac
        )
        return {
            "delta_raw": delta_raw,
            "delta_bounded": delta_bounded,
            "y_hat": y_hat,
            "territory_embeddings": territory,
        }


# ---------------------------------------------------------------------------
# Factory and parameter counting
# ---------------------------------------------------------------------------

_MODEL_REGISTRY: dict[str, type] = {
    "A0Neural": A0Neural,
    "GConvGRU": GConvGRU,
    "EvolveGCNH": EvolveGCNH,
}


def build_model(
    name: str,
    n_sectors: int = 9,
    n_features: int = 3,
    hidden_dim: int = 8,
    sector_embed_dim: int = 4,
    dropout: float = 0.3,
    clamp_frac: float = 0.15,
) -> nn.Module:
    """Instantiate a model by name with contract-compliant defaults."""
    if name not in _MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {name}. Choose from {list(_MODEL_REGISTRY)}")
    return _MODEL_REGISTRY[name](
        n_sectors=n_sectors,
        n_features=n_features,
        hidden_dim=hidden_dim,
        sector_embed_dim=sector_embed_dim,
        dropout=dropout,
        clamp_frac=clamp_frac,
    )


def count_parameters(model: nn.Module) -> int:
    """Count trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
