"""
graph_heads.py — Independent auxiliary heads for graph structure prediction (DEC-051).

Architecture:
  edge_presence_logit  = max(model.log_sect_attn_lag1, model.log_sect_attn_lag2)
                         (from main model — justified: attention weights encode connectivity)
  edge_sign_logit      = GraphAuxHeads.sign_logit[target, source]   ← INDEPENDENT
  edge_lag_logit       = GraphAuxHeads.lag_logit[target, source]    ← INDEPENDENT

Convention: edge_*[target, source] for directed source → target edge.
Diagonal excluded (no self-loops).

Bug C fix (DEC-050): sign and lag heads now have INDEPENDENT parameters.
No shared logit between presence, sign, and lag.

All objectives are SYNTHETIC_ONLY — true_relations ground truth is not available
for real country data (PT/IT/FR/NL/AT).

Frozen loss weights (DEC-051):
  ALPHA = 0.10  (edge_presence)
  BETA  = 0.05  (edge_sign)
  GAMMA = 0.05  (edge_lag)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged

# Frozen multitask weights
GRAPH_ALPHA: float = 0.10   # edge presence
GRAPH_BETA: float = 0.05    # edge sign
GRAPH_GAMMA: float = 0.05   # edge lag


class GraphAuxHeads(nn.Module):
    """
    Auxiliary prediction heads for edge sign and edge lag.

    Edge PRESENCE uses max(model.log_attn_lag1, model.log_attn_lag2) from the main
    model — this is appropriate because attention encodes connectivity strength.

    Edge SIGN and EDGE LAG each have independent parameters not shared with
    the attention weights. This corrects Bug C from DEC-050.

    Parameters:
        sign_logit: (n_S, n_S)  — positive value → positive weight edge
        lag_logit:  (n_S, n_S)  — positive value → lag-1, negative → lag-2 (BCE)
    """

    def __init__(self, n_sectors: int):
        super().__init__()
        self.n_S = n_sectors
        self.sign_logit = nn.Parameter(torch.zeros(n_sectors, n_sectors))
        self.lag_logit = nn.Parameter(torch.zeros(n_sectors, n_sectors))

    def edge_presence_bce(
        self,
        model: HERALDGraphImputerLagged,
        true_relations: list,
        device: str,
    ) -> torch.Tensor:
        """
        Binary BCE for edge PRESENCE. Both lag-1 and lag-2 true edges → positive.
        Logit = max(log_attn_lag1, log_attn_lag2) — from main model (justified).
        Diagonal excluded. pos_weight = n_neg / n_pos.
        """
        n_S = self.n_S
        edge_target = torch.zeros(n_S, n_S, device=device)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if s < n_S and t < n_S:
                edge_target[t, s] = 1.0  # lag-agnostic

        mask_diag = ~torch.eye(n_S, dtype=torch.bool, device=device)
        presence_logits = torch.max(model.log_sect_attn_lag1, model.log_sect_attn_lag2)
        logits = presence_logits[mask_diag]
        targets = edge_target[mask_diag]
        n_pos = targets.sum().clamp(min=1)
        n_neg = (1 - targets).sum().clamp(min=1)
        pos_weight = torch.tensor([float(n_neg / n_pos)], device=device)
        return F.binary_cross_entropy_with_logits(logits, targets, pos_weight=pos_weight)

    def edge_sign_bce(
        self,
        true_relations: list,
        device: str,
    ) -> torch.Tensor:
        """
        Binary BCE for edge SIGN on known true edges only.
        INDEPENDENT from presence logit (uses self.sign_logit).
        Positive weight → sign_logit > 0; negative weight → sign_logit < 0.
        Only evaluated on true_relations (not all off-diagonal pairs).
        """
        n_S = self.n_S
        sign_target = torch.full((n_S, n_S), -1.0, device=device)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if s < n_S and t < n_S:
                sign_target[t, s] = 1.0 if r.weight > 0 else 0.0

        known = sign_target >= 0
        if not known.any():
            return torch.tensor(0.0, device=device)
        return F.binary_cross_entropy_with_logits(
            self.sign_logit[known], sign_target[known]
        )

    def edge_lag_bce(
        self,
        true_relations: list,
        device: str,
    ) -> torch.Tensor:
        """
        Binary BCE for edge LAG on known true edges only.
        INDEPENDENT from sign logit (uses self.lag_logit).
        lag_logit[t,s] > 0 → lag-1; < 0 → lag-2.
        Only evaluated on true_relations (not all off-diagonal pairs).
        """
        n_S = self.n_S
        lag_target = torch.full((n_S, n_S), -1.0, device=device)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if s < n_S and t < n_S:
                lag_target[t, s] = 1.0 if r.lag == 1 else 0.0

        known = lag_target >= 0
        if not known.any():
            return torch.tensor(0.0, device=device)
        return F.binary_cross_entropy_with_logits(
            self.lag_logit[known], lag_target[known]
        )

    def all_losses(
        self,
        model: HERALDGraphImputerLagged,
        true_relations: list,
        device: str,
    ) -> dict[str, torch.Tensor]:
        """Return dict of all graph losses (presence, sign, lag)."""
        return {
            "presence": self.edge_presence_bce(model, true_relations, device),
            "sign": self.edge_sign_bce(true_relations, device),
            "lag": self.edge_lag_bce(true_relations, device),
        }

    def total_graph_loss(
        self,
        model: HERALDGraphImputerLagged,
        true_relations: list,
        device: str,
    ) -> torch.Tensor:
        """ALPHA*presence + BETA*sign + GAMMA*lag (FROZEN weights)."""
        losses = self.all_losses(model, true_relations, device)
        return (
            GRAPH_ALPHA * losses["presence"]
            + GRAPH_BETA * losses["sign"]
            + GRAPH_GAMMA * losses["lag"]
        )

    @torch.no_grad()
    def edge_metrics(
        self,
        model: HERALDGraphImputerLagged,
        true_relations: list,
        device: str,
        n_sectors: int | None = None,
    ) -> dict[str, float]:
        """Compute edge AUC, sign accuracy, lag accuracy for logging."""
        from sklearn.metrics import roc_auc_score, average_precision_score
        import numpy as np

        n_S = n_sectors or self.n_S
        edge_target = np.zeros((n_S, n_S), dtype=np.float32)
        sign_target = np.full((n_S, n_S), -1.0, dtype=np.float32)
        lag_target = np.full((n_S, n_S), -1.0, dtype=np.float32)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if s < n_S and t < n_S:
                edge_target[t, s] = 1.0
                sign_target[t, s] = 1.0 if r.weight > 0 else 0.0
                lag_target[t, s] = 1.0 if r.lag == 1 else 0.0

        mask_diag = ~np.eye(n_S, dtype=bool)
        presence_logits = torch.max(
            model.log_sect_attn_lag1, model.log_sect_attn_lag2
        ).cpu().numpy()
        scores = presence_logits[mask_diag]
        labels = edge_target[mask_diag]
        n_pos = int(labels.sum())
        n_neg = int((1 - labels).sum())

        metrics: dict[str, float] = {}
        if n_pos > 0 and n_neg > 0:
            metrics["edge_auc"] = float(roc_auc_score(labels, scores))
            metrics["edge_auprc"] = float(average_precision_score(labels, scores))
        else:
            metrics["edge_auc"] = float("nan")
            metrics["edge_auprc"] = float("nan")
        metrics["edge_prevalence"] = float(n_pos / (n_pos + n_neg)) if (n_pos + n_neg) > 0 else 0.0

        # Sign accuracy on known edges
        known_sign = sign_target >= 0
        if known_sign.any():
            sign_pred = (self.sign_logit.detach().cpu().numpy() > 0).astype(float)
            metrics["sign_acc"] = float(
                (sign_pred[known_sign] == sign_target[known_sign]).mean()
            )
        else:
            metrics["sign_acc"] = float("nan")

        # Lag accuracy on known edges
        known_lag = lag_target >= 0
        if known_lag.any():
            lag_pred = (self.lag_logit.detach().cpu().numpy() > 0).astype(float)
            metrics["lag_acc"] = float(
                (lag_pred[known_lag] == lag_target[known_lag]).mean()
            )
        else:
            metrics["lag_acc"] = float("nan")

        return metrics
