"""
herald_graph_imputer.py

Neural graph-aware imputer for HERALD synthetic benchmark (DEC-039).

Architecture:
- Input features: temporal (causal) + sector-neighbor + territory-neighbor
- Learnable attention weights for sector and territory aggregation
- Small MLP decoder: features → (mean, log_sigma)
- Training: NLL loss on observed cells only
- Inference: MC Dropout for predictive uncertainty

Key design rules:
- Temporal features are strictly causal (only use t' < t)
- Missing cells are never implicitly zero-filled (mask handles all aggregation)
- Graph adjacency initialises attention but weights are learned
- Permuted variant: shuffle adjacency before computing features
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from src.modeles.synthetic.imputation_baselines import _build_temporal_features


def _apply_observed(imputed: np.ndarray, panel: np.ndarray, mask: np.ndarray) -> np.ndarray:
    result = imputed.copy()
    result[mask == 1] = panel[mask == 1]
    return result


class HERALDGraphImputer(nn.Module):
    """
    Neural graph-augmented imputer.

    For each cell (t, s, y) the model concatenates:
    - 7 temporal features (causal)
    - sector-neighbor mean (softmax attention weighted, from mask-weighted adjacency)
    - territory-neighbor mean (softmax attention weighted)

    Attention weights are learnable parameters, optionally biased
    by a known adjacency matrix.

    Two variants:
    - with_graph=True: sector and territory adjacency used
    - with_graph=False: adjacency fixed to identity (local only)
    """

    def __init__(
        self,
        n_sectors: int,
        n_territories: int,
        hidden_dim: int = 32,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.n_S = n_sectors
        self.n_T = n_territories

        # Learnable log-attention matrices (before softmax)
        self.log_sect_attn = nn.Parameter(torch.zeros(n_sectors, n_sectors))
        self.log_terr_attn = nn.Parameter(torch.zeros(n_territories, n_territories))

        # MLP: 9 features (7 temporal + 2 graph) → 2 outputs (mean, log_sigma)
        self.net = nn.Sequential(
            nn.Linear(9, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 2),
        )

    def _compute_graph_features_torch(
        self,
        safe: torch.Tensor,   # (n_T, n_S, n_Y) — zeros at missing
        mask: torch.Tensor,   # (n_T, n_S, n_Y) float
        sect_attn: torch.Tensor,   # (n_S, n_S) softmax
        terr_attn: torch.Tensor,   # (n_T, n_T) softmax
    ) -> torch.Tensor:
        """Returns (n_T, n_S, n_Y, 2): [sector_neighbor_mean, territory_neighbor_mean]."""
        # Sector neighbor: for each target sector i, mask-weighted mean over source j
        sector_wsum = torch.einsum("ij,tjy->tiy", sect_attn, safe * mask)      # (n_T, n_S, n_Y)
        sector_wcount = torch.einsum("ij,tjy->tiy", sect_attn, mask).clamp(min=1e-8)
        sector_nb = sector_wsum / sector_wcount

        # Territory neighbor: for each target territory i, mask-weighted mean over source j
        terr_wsum = torch.einsum("ij,jsy->isy", terr_attn, safe * mask)        # (n_T, n_S, n_Y)
        terr_wcount = torch.einsum("ij,jsy->isy", terr_attn, mask).clamp(min=1e-8)
        terr_nb = terr_wsum / terr_wcount

        return torch.stack([sector_nb, terr_nb], dim=-1)  # (n_T, n_S, n_Y, 2)

    def forward(
        self,
        panel_t: torch.Tensor,    # (n_T, n_S, n_Y)
        mask_t: torch.Tensor,     # (n_T, n_S, n_Y)
        adj_sector: torch.Tensor | None = None,   # (n_S, n_S)
        adj_territory: torch.Tensor | None = None, # (n_T, n_T)
        temp_feats_t: torch.Tensor | None = None,  # (n_T*n_S*n_Y, 7) precomputed
    ) -> torch.Tensor:
        """
        Returns (n_T, n_S, n_Y, 2) — [predicted_mean, log_sigma].
        """
        n_T, n_S, n_Y = panel_t.shape
        safe = panel_t * mask_t  # zero-fill for aggregation only (not imputation)

        # Attention matrices
        log_s = self.log_sect_attn + (adj_sector if adj_sector is not None else 0)
        log_t = self.log_terr_attn + (adj_territory if adj_territory is not None else 0)
        sect_attn = torch.softmax(log_s, dim=-1)   # (n_S, n_S)
        terr_attn = torch.softmax(log_t, dim=-1)   # (n_T, n_T)

        # Graph features
        graph_f = self._compute_graph_features_torch(safe, mask_t, sect_attn, terr_attn)
        # (n_T, n_S, n_Y, 2)
        graph_f_flat = graph_f.reshape(n_T * n_S * n_Y, 2)

        # Temporal features (precomputed if provided)
        if temp_feats_t is None:
            raise ValueError("temp_feats_t must be precomputed; call build_temp_features() first")
        feats = torch.cat([temp_feats_t, graph_f_flat], dim=-1)  # (n_T*n_S*n_Y, 9)

        out = self.net(feats)  # (n_T*n_S*n_Y, 2)
        return out.reshape(n_T, n_S, n_Y, 2)

    def get_sector_attention(self) -> np.ndarray:
        """Learned sector attention matrix (n_S, n_S) after softmax."""
        return torch.softmax(self.log_sect_attn, dim=-1).detach().cpu().numpy()


def _prep_tensors(
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None,
    adj_territory: np.ndarray | None,
    device: str,
) -> tuple:
    panel_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0)).float().to(device)
    mask_t = torch.from_numpy(mask.astype(np.float32)).to(device)
    adj_s_t = torch.from_numpy(adj_sector.astype(np.float32)).to(device) if adj_sector is not None else None
    adj_t_t = torch.from_numpy(adj_territory.astype(np.float32)).to(device) if adj_territory is not None else None
    return panel_t, mask_t, adj_s_t, adj_t_t


def train_herald_imputer(
    model: HERALDGraphImputer,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None = None,
    adj_territory: np.ndarray | None = None,
    n_epochs: int = 100,
    lr: float = 1e-3,
    device: str = "cpu",
) -> list[float]:
    """
    Train on observed cells using Gaussian NLL loss.
    Returns list of per-epoch losses.
    """
    model = model.to(device)
    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_sector, adj_territory, device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)

    # Precompute temporal features (numpy then convert once)
    temp_feats_np = _build_temporal_features(panel, mask)  # (N, 7)
    temp_feats_t = torch.from_numpy(temp_feats_np.astype(np.float32)).to(device)

    losses = []
    for _ in range(n_epochs):
        opt.zero_grad()
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)  # (n_T, n_S, n_Y, 2)
        pred_mean = out[..., 0]
        log_sigma = out[..., 1]
        sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
        # Gaussian NLL: 0.5 * (log(sigma^2) + (y-mu)^2/sigma^2)
        nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
        loss = (nll * mask_t).sum() / mask_t.sum().clamp(min=1)
        loss.backward()
        opt.step()
        losses.append(float(loss))

    return losses


def impute_deterministic(
    model: HERALDGraphImputer,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None = None,
    adj_territory: np.ndarray | None = None,
    device: str = "cpu",
) -> np.ndarray:
    """Single forward pass. Returns imputed panel (n_T, n_S, n_Y)."""
    model.eval()
    model = model.to(device)
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_sector, adj_territory, device)
    temp_feats_np = _build_temporal_features(panel, mask)
    temp_feats_t = torch.from_numpy(temp_feats_np.astype(np.float32)).to(device)

    with torch.no_grad():
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred = out[..., 0].cpu().numpy()
    return _apply_observed(pred, panel, mask)


def impute_with_uncertainty(
    model: HERALDGraphImputer,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_sector: np.ndarray | None = None,
    adj_territory: np.ndarray | None = None,
    n_mc: int = 50,
    device: str = "cpu",
) -> tuple[np.ndarray, np.ndarray]:
    """
    MC Dropout uncertainty. Returns (pred_mean, pred_std) as (n_T, n_S, n_Y) arrays.
    Observed cells always have std=0.
    """
    model.train()  # enable dropout
    model = model.to(device)
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_sector, adj_territory, device)
    temp_feats_np = _build_temporal_features(panel, mask)
    temp_feats_t = torch.from_numpy(temp_feats_np.astype(np.float32)).to(device)

    samples = []
    with torch.no_grad():
        for _ in range(n_mc):
            out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
            samples.append(out[..., 0].cpu().numpy())

    samples = np.stack(samples)  # (n_mc, n_T, n_S, n_Y)
    pred_mean = samples.mean(0)
    pred_std = samples.std(0)

    # Observed cells: use true value, std=0
    pred_mean[mask == 1] = panel[mask == 1]
    pred_std[mask == 1] = 0.0

    return pred_mean, pred_std


def build_permuted_adj(
    adj_sector: np.ndarray,
    adj_territory: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Permute rows AND columns of both adjacency matrices (node relabeling null).
    Panel, masks, and labels are NOT permuted → genuine structural mismatch.

    Proof of non-degeneracy: if panel were copermuted with the same permutation,
    the result would be identical to the original (pure relabeling, zero information change).
    Since only the graph is permuted, nodes receive messages from wrong neighbors.
    """
    n_S = adj_sector.shape[0]
    n_T = adj_territory.shape[0]
    perm_s = rng.permutation(n_S)
    perm_t = rng.permutation(n_T)
    adj_s_perm = adj_sector[perm_s][:, perm_s]
    adj_t_perm = adj_territory[perm_t][:, perm_t]
    return adj_s_perm, adj_t_perm, perm_s, perm_t  # return permutation for audit


def build_random_adj(
    adj_sector: np.ndarray,
    adj_territory: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Erdős-Rényi random adjacency preserving exact edge density of the original.
    Sector adj → symmetric random with same density.
    Territory adj → row-normalized random with same mean density.
    This is a weaker null than node-permutation: no structural relationship to true graph.
    """
    n_S = adj_sector.shape[0]
    # Sector adj: symmetric, density = fraction of off-diagonal entries that are 1
    n_off = n_S * (n_S - 1)
    density_s = float(adj_sector.sum()) / max(n_off, 1)
    upper = rng.uniform(size=(n_S, n_S)) < density_s
    upper = np.triu(upper, k=1)
    adj_s_rand = (upper | upper.T).astype(float)
    np.fill_diagonal(adj_s_rand, 0)

    # Territory adj: row-normalized random with same density
    n_T = adj_territory.shape[0]
    density_t = float((adj_territory > 0).sum()) / max(n_T * (n_T - 1), 1)
    adj_t_bin = (rng.uniform(size=(n_T, n_T)) < density_t).astype(float)
    np.fill_diagonal(adj_t_bin, 0)
    row_sum = adj_t_bin.sum(axis=1, keepdims=True)
    row_sum = np.where(row_sum == 0, 1.0, row_sum)
    adj_t_rand = adj_t_bin / row_sum

    return adj_s_rand, adj_t_rand
