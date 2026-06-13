"""
herald_graph_imputer_lagged.py — DEC-043 / Phase 10

HERALDGraphImputerLagged: lag-1 and lag-2 sector message passing.

Architecture specification (frozen in DEC-043 before benchmark):

  Two learnable attention matrices:
    log_sect_attn_lag1: (n_S, n_S) — weights for source[t-1] → target[t]
    log_sect_attn_lag2: (n_S, n_S) — weights for source[t-2] → target[t]

  Attention semantics:
    sect_attn_lagK[i, j] = softmax(log_sect_attn_lagK + adj_sector)[i, j]
    = weight of source j contributing to target i at lag K
    = attention for the directed message j → i with delay K

  Graph features (3 values per (territory, sector, year) cell):
    sector_nb_lag1: mask-weighted mean of source-sector values at t-1
    sector_nb_lag2: mask-weighted mean of source-sector values at t-2
    territory_nb:   mask-weighted mean of territory neighbors (contemporaneous)

  MLP: 10 inputs (7 temporal + 3 graph) → hidden=64 → hidden/2 → 2 (mean, log_sigma)

  Fallback rules:
    Year 0 at lag-1: no history → lag-1 feature = 0
    Years 0-1 at lag-2: no history → lag-2 feature = 0
    All lag-k neighbors missing: feature = 0 (mask-weighted avg denominator = 0 → 0/ε = 0)

  No future information:
    lag-1 uses only values at t-1 (strictly before target t)
    lag-2 uses only values at t-2 (strictly before target t)
    Territory feature is contemporaneous with masking (does not leak target)

  Oracle (directed):
    log_sect_attn_lag1[target, source] = 0  for lag-1 true edge source→target
    log_sect_attn_lag2[target, source] = 0  for lag-2 true edge source→target
    All other entries = log(1e-6) ≈ -13.8
    Both matrices frozen (requires_grad=False); MLP remains trainable.

  get_sector_attention() returns max(lag1, lag2) elementwise for backward compatibility
  with compute_edge_recovery_metrics (which expects a single (n_S, n_S) array).
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.herald_graph_imputer import (
    _apply_observed,
    _prep_tensors,
)


# ── Architecture ──────────────────────────────────────────────────────────────

class HERALDGraphImputerLagged(nn.Module):
    """
    HERALD imputer with lag-1 and lag-2 directed sector message passing.

    Source values from years t-1 and t-2 are separately aggregated via
    dedicated attention matrices to predict target values at year t.
    """

    def __init__(
        self,
        n_sectors: int,
        n_territories: int,
        hidden_dim: int = 64,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.n_S = n_sectors
        self.n_T = n_territories

        # Separate attention for each lag
        self.log_sect_attn_lag1 = nn.Parameter(torch.zeros(n_sectors, n_sectors))
        self.log_sect_attn_lag2 = nn.Parameter(torch.zeros(n_sectors, n_sectors))
        self.log_terr_attn = nn.Parameter(torch.zeros(n_territories, n_territories))

        # MLP: 7 temporal + 3 graph (lag1, lag2, territory) = 10 inputs
        self.net = nn.Sequential(
            nn.Linear(10, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 2),
        )

    # ── Graph feature computation ─────────────────────────────────────────────

    def _compute_graph_features_torch(
        self,
        safe: torch.Tensor,          # (n_T, n_S, n_Y) — zero at missing positions
        mask: torch.Tensor,          # (n_T, n_S, n_Y) float, 1=observed, 0=missing
        sect_attn_lag1: torch.Tensor, # (n_S, n_S) softmax
        sect_attn_lag2: torch.Tensor, # (n_S, n_S) softmax
        terr_attn: torch.Tensor,      # (n_T, n_T) softmax
    ) -> torch.Tensor:
        """Returns (n_T, n_S, n_Y, 3): [sector_nb_lag1, sector_nb_lag2, territory_nb]."""

        # ── Lag-1: aggregate source sectors at year t-1 ───────────────────────
        # Roll forward by 1: safe_lag1[:, :, y] = safe[:, :, y-1]
        safe_lag1 = torch.roll(safe, shifts=1, dims=2)
        safe_lag1[:, :, 0].zero_()      # year 0 has no lag-1 history → explicit 0
        mask_lag1 = torch.roll(mask, shifts=1, dims=2)
        mask_lag1[:, :, 0].zero_()      # no observed lag-1 at year 0

        # sect_attn_lag1[i,j] = weight for target i from source j at t-1
        wsum1 = torch.einsum("ij,tjy->tiy", sect_attn_lag1, safe_lag1 * mask_lag1)
        wcnt1 = torch.einsum("ij,tjy->tiy", sect_attn_lag1, mask_lag1).clamp(min=1e-8)
        sector_nb_lag1 = wsum1 / wcnt1   # 0/ε = 0 when all lag-1 neighbors missing

        # ── Lag-2: aggregate source sectors at year t-2 ───────────────────────
        safe_lag2 = torch.roll(safe, shifts=2, dims=2)
        safe_lag2[:, :, :2].zero_()     # years 0-1 have no lag-2 history
        mask_lag2 = torch.roll(mask, shifts=2, dims=2)
        mask_lag2[:, :, :2].zero_()

        wsum2 = torch.einsum("ij,tjy->tiy", sect_attn_lag2, safe_lag2 * mask_lag2)
        wcnt2 = torch.einsum("ij,tjy->tiy", sect_attn_lag2, mask_lag2).clamp(min=1e-8)
        sector_nb_lag2 = wsum2 / wcnt2

        # ── Territory: contemporaneous neighbors ──────────────────────────────
        terr_wsum = torch.einsum("ij,jsy->isy", terr_attn, safe * mask)
        terr_wcnt = torch.einsum("ij,jsy->isy", terr_attn, mask).clamp(min=1e-8)
        territory_nb = terr_wsum / terr_wcnt

        return torch.stack([sector_nb_lag1, sector_nb_lag2, territory_nb], dim=-1)

    # ── Forward pass ──────────────────────────────────────────────────────────

    def forward(
        self,
        panel_t: torch.Tensor,                    # (n_T, n_S, n_Y)
        mask_t: torch.Tensor,                     # (n_T, n_S, n_Y)
        adj_sector: torch.Tensor | None = None,   # (n_S, n_S) additive log-prior
        adj_territory: torch.Tensor | None = None, # (n_T, n_T) additive log-prior
        temp_feats_t: torch.Tensor | None = None,  # (n_T*n_S*n_Y, 7) precomputed
    ) -> torch.Tensor:
        """Returns (n_T, n_S, n_Y, 2) — [predicted_mean, log_sigma]."""
        if temp_feats_t is None:
            raise ValueError("temp_feats_t must be precomputed via _build_temporal_features")

        n_T, n_S, n_Y = panel_t.shape
        safe = panel_t * mask_t

        # Attention: add adj as log-prior bias (shared for both lags, as in Phase 9)
        adj_s = adj_sector if adj_sector is not None else 0
        adj_t = adj_territory if adj_territory is not None else 0

        log_s1 = self.log_sect_attn_lag1 + adj_s
        log_s2 = self.log_sect_attn_lag2 + adj_s
        log_t = self.log_terr_attn + adj_t

        sect_attn_lag1 = torch.softmax(log_s1, dim=-1)
        sect_attn_lag2 = torch.softmax(log_s2, dim=-1)
        terr_attn = torch.softmax(log_t, dim=-1)

        # Graph features (n_T, n_S, n_Y, 3)
        graph_f = self._compute_graph_features_torch(
            safe, mask_t, sect_attn_lag1, sect_attn_lag2, terr_attn
        )
        graph_f_flat = graph_f.reshape(n_T * n_S * n_Y, 3)

        # Combine temporal (7) + graph (3) = 10 features
        feats = torch.cat([temp_feats_t, graph_f_flat], dim=-1)
        out = self.net(feats)                          # (n_T*n_S*n_Y, 2)
        return out.reshape(n_T, n_S, n_Y, 2)

    # ── Attention access ──────────────────────────────────────────────────────

    def get_sector_attention_lag1(self) -> np.ndarray:
        """Lag-1 sector attention (n_S, n_S) after softmax."""
        return torch.softmax(self.log_sect_attn_lag1, dim=-1).detach().cpu().numpy()

    def get_sector_attention_lag2(self) -> np.ndarray:
        """Lag-2 sector attention (n_S, n_S) after softmax."""
        return torch.softmax(self.log_sect_attn_lag2, dim=-1).detach().cpu().numpy()

    def get_sector_attention(self) -> np.ndarray:
        """
        Combined attention: elementwise max(lag1, lag2).
        Backward-compatible with compute_edge_recovery_metrics (expects single matrix).
        The max selects the dominant lag for each (target, source) pair.
        """
        a1 = self.get_sector_attention_lag1()
        a2 = self.get_sector_attention_lag2()
        return np.maximum(a1, a2)


# ── Oracle setup ──────────────────────────────────────────────────────────────

def build_directed_oracle_lagged(
    model: HERALDGraphImputerLagged,
    true_relations: list,
    n_sectors: int,
) -> None:
    """
    Freeze log_sect_attn_lag1 and log_sect_attn_lag2 to directed oracle values.

    Encoding: log_sect_attn_lagK[target, source] = 0 (high) for true lag-K edge source→target.
    All other entries = log(1e-6) (strongly suppressed).

    This fixes both B2 (uses directed adj) and B3 (uses lagged aggregation).
    MLP weights remain trainable.
    """
    log_lag1 = np.full((n_sectors, n_sectors), np.log(1e-6), dtype=np.float32)
    log_lag2 = np.full((n_sectors, n_sectors), np.log(1e-6), dtype=np.float32)

    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        if s < n_sectors and t < n_sectors:
            if r.lag == 1:
                log_lag1[t, s] = 0.0   # target row t, source col s → high attention for s→t at lag-1
            elif r.lag == 2:
                log_lag2[t, s] = 0.0

    with torch.no_grad():
        model.log_sect_attn_lag1.data = torch.from_numpy(log_lag1)
        model.log_sect_attn_lag2.data = torch.from_numpy(log_lag2)
    model.log_sect_attn_lag1.requires_grad_(False)
    model.log_sect_attn_lag2.requires_grad_(False)


def build_symmetric_oracle_lagged(
    model: HERALDGraphImputerLagged,
    adj_s: np.ndarray,
) -> None:
    """
    Freeze both lag matrices to log(adj_s) (undirected, no lag distinction).
    Equivalent to Phase 9 oracle but applied to the lagged architecture.
    """
    oracle_log = np.log(adj_s.astype(np.float32).clip(min=1e-6))
    with torch.no_grad():
        model.log_sect_attn_lag1.data = torch.from_numpy(oracle_log)
        model.log_sect_attn_lag2.data = torch.from_numpy(oracle_log)
    model.log_sect_attn_lag1.requires_grad_(False)
    model.log_sect_attn_lag2.requires_grad_(False)


# ── Training and inference (reuse Phase 9 functions) ──────────────────────────

def train_herald_lagged(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None = None,
    adj_territory: np.ndarray | None = None,
    n_epochs: int = 100,
    lr: float = 1e-3,
    device: str = "cpu",
) -> list[float]:
    """
    Train lagged model with Gaussian NLL loss on observed cells.
    Identical to train_herald_imputer but calls the lagged model's forward.
    Returns list of per-epoch losses.
    """
    model = model.to(device)
    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(
        panel, mask, adj_sector, adj_territory, device
    )
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    ).to(device)

    losses = []
    for _ in range(n_epochs):
        opt.zero_grad()
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
        pred_mean = out[..., 0]
        log_sigma = out[..., 1]
        sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
        nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
        loss = (nll * mask_t).sum() / mask_t.sum().clamp(min=1)
        loss.backward()
        opt.step()
        losses.append(float(loss))
    return losses


def impute_deterministic_lagged(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None = None,
    adj_territory: np.ndarray | None = None,
    device: str = "cpu",
) -> np.ndarray:
    """Single forward pass. Returns imputed panel (n_T, n_S, n_Y)."""
    model.eval()
    model = model.to(device)
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(
        panel, mask, adj_sector, adj_territory, device
    )
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    ).to(device)

    with torch.no_grad():
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred = out[..., 0].cpu().numpy()
    return _apply_observed(pred, panel, mask)


def impute_with_uncertainty_lagged(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None = None,
    adj_territory: np.ndarray | None = None,
    n_mc: int = 50,
    device: str = "cpu",
) -> tuple[np.ndarray, np.ndarray]:
    """MC Dropout uncertainty. Returns (pred_mean, pred_std) as (n_T, n_S, n_Y)."""
    model.train()
    model = model.to(device)
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(
        panel, mask, adj_sector, adj_territory, device
    )
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    ).to(device)

    samples = []
    with torch.no_grad():
        for _ in range(n_mc):
            out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
            samples.append(out[..., 0].cpu().numpy())

    samples = np.stack(samples)
    pred_mean = samples.mean(0)
    pred_std = samples.std(0)
    pred_mean[mask == 1] = panel[mask == 1]
    pred_std[mask == 1] = 0.0
    return pred_mean, pred_std
