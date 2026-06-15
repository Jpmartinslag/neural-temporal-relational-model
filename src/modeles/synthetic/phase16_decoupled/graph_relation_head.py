"""
graph_relation_head.py — Component A: directed relation inference (DEC-053).

Learns presence/sign/lag/confidence for each directed sector pair [target, source].
Completely independent of the temporal backbone and its attention weights.
Ground truth available only in synthetic experiments.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GraphRelationHead(nn.Module):
    """
    Parameters (all [n_sectors, n_sectors], indexed [target, source]):
      presence_logit  — logit for P(relation source→target exists)
      sign_logit      — logit for P(relation is positive | exists)
      lag_logit       — logit for P(lag=1 | exists); lag=2 otherwise
      log_confidence  — log(reliability/magnitude) of each relation
    Diagonal entries are never evaluated (no self-loops).
    """

    def __init__(self, n_sectors: int):
        super().__init__()
        n = n_sectors
        self.n_S = n
        self.presence_logit = nn.Parameter(torch.zeros(n, n))
        self.sign_logit = nn.Parameter(torch.zeros(n, n))
        self.lag_logit = nn.Parameter(torch.zeros(n, n))
        self.log_confidence = nn.Parameter(torch.zeros(n, n))

    def presence_probs(self) -> torch.Tensor:
        """P(relation exists) per directed pair, shape (n_S, n_S)."""
        return torch.sigmoid(self.presence_logit)

    def directed_attention(self, lag: int) -> torch.Tensor:
        """
        Directed attention for routing messages at a given lag.
        Returns (n_S, n_S) where [target, source] = weight of source contributing to target.
        lag=1: weight = presence_prob * P(lag=1)
        lag=2: weight = presence_prob * P(lag=2) = presence_prob * (1 - P(lag=1))
        Normalised with softmax over sources per target.
        """
        p_present = torch.sigmoid(self.presence_logit)   # (n_S, n_S)
        p_lag1 = torch.sigmoid(self.lag_logit)            # (n_S, n_S)
        if lag == 1:
            w = p_present * p_lag1
        else:
            w = p_present * (1 - p_lag1)
        # Mask diagonal
        diag_mask = torch.eye(self.n_S, dtype=torch.bool, device=self.presence_logit.device)
        w = w.masked_fill(diag_mask, 0.0)
        # Row-normalise (per target)
        denom = w.sum(dim=-1, keepdim=True).clamp(min=1e-8)
        return w / denom

    # ── Losses ────────────────────────────────────────────────────────────────

    def presence_loss(self, true_relations: list, device: str) -> torch.Tensor:
        """BCE for directed edge presence. pos_weight = n_neg / n_pos."""
        n = self.n_S
        target = torch.zeros(n, n, device=device)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if 0 <= s < n and 0 <= t < n and s != t:
                target[t, s] = 1.0
        mask = ~torch.eye(n, dtype=torch.bool, device=device)
        logits = self.presence_logit[mask]
        tgt = target[mask]
        n_pos = tgt.sum().clamp(min=1)
        n_neg = (1 - tgt).sum().clamp(min=1)
        pw = torch.tensor([float(n_neg / n_pos)], device=device)
        return F.binary_cross_entropy_with_logits(logits, tgt, pos_weight=pw)

    def sign_loss(self, true_relations: list, device: str) -> torch.Tensor:
        """BCE for relation sign on known directed edges only."""
        n = self.n_S
        target = torch.full((n, n), -1.0, device=device)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if 0 <= s < n and 0 <= t < n and s != t:
                target[t, s] = 1.0 if r.weight > 0 else 0.0
        known = target >= 0
        if not known.any():
            return torch.tensor(0.0, device=device)
        return F.binary_cross_entropy_with_logits(self.sign_logit[known], target[known])

    def lag_loss(self, true_relations: list, device: str) -> torch.Tensor:
        """BCE for lag=1 vs lag=2 on known directed edges only."""
        n = self.n_S
        target = torch.full((n, n), -1.0, device=device)
        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if 0 <= s < n and 0 <= t < n and s != t:
                target[t, s] = 1.0 if r.lag == 1 else 0.0
        known = target >= 0
        if not known.any():
            return torch.tensor(0.0, device=device)
        return F.binary_cross_entropy_with_logits(self.lag_logit[known], target[known])

    def all_losses(self, true_relations: list, device: str) -> dict[str, torch.Tensor]:
        return {
            "presence": self.presence_loss(true_relations, device),
            "sign": self.sign_loss(true_relations, device),
            "lag": self.lag_loss(true_relations, device),
        }

    # ── Metrics ───────────────────────────────────────────────────────────────

    @torch.no_grad()
    def edge_metrics(self, true_relations: list, sector_adj: np.ndarray | None = None) -> dict:
        """
        Directed AUC, AUPRC, sign_acc, lag_acc, prevalence, and prior-bias audit.
        Does NOT use sector_adj as ground truth; uses it only for the bias audit.
        """
        from sklearn.metrics import roc_auc_score, average_precision_score

        n = self.n_S
        lag1_sc = self.presence_logit.cpu().numpy() + self.lag_logit.cpu().numpy()
        lag2_sc = self.presence_logit.cpu().numpy() - self.lag_logit.cpu().numpy()
        combined = self.presence_logit.cpu().numpy()

        presence = np.zeros((n, n), dtype=int)
        lag1_pres = np.zeros((n, n), dtype=int)
        lag2_pres = np.zeros((n, n), dtype=int)
        sign_gt = np.full((n, n), -1.0)
        lag_gt = np.full((n, n), -1.0)

        for r in true_relations:
            s, t = r.source_sector, r.target_sector
            if 0 <= s < n and 0 <= t < n and s != t:
                presence[t, s] = 1
                sign_gt[t, s] = 1.0 if r.weight > 0 else 0.0
                lag_gt[t, s] = 1.0 if r.lag == 1 else 0.0
                if r.lag == 1:
                    lag1_pres[t, s] = 1
                else:
                    lag2_pres[t, s] = 1

        off_diag = ~np.eye(n, dtype=bool)

        def _auc(y_t, y_s):
            y_t, y_s = np.asarray(y_t), np.asarray(y_s)
            if len(np.unique(y_t)) < 2:
                return float("nan")
            return float(roc_auc_score(y_t, y_s))

        def _auprc(y_t, y_s):
            y_t = np.asarray(y_t)
            if y_t.sum() == 0:
                return float("nan")
            return float(average_precision_score(y_t, np.asarray(y_s)))

        m: dict = {
            "edge_auc_directed": _auc(presence[off_diag], combined[off_diag]),
            "edge_auprc_directed": _auprc(presence[off_diag], combined[off_diag]),
            "prevalence": float(presence[off_diag].mean()),
            "edge_auc_lag1": _auc(lag1_pres[off_diag], lag1_sc[off_diag]),
            "edge_auc_lag2": _auc(lag2_pres[off_diag], lag2_sc[off_diag]),
            "n_true_directed": int(presence.sum()),
        }

        # Bias audit: how many symmetric adj entries are false reverses
        if sector_adj is not None:
            sadj = (sector_adj > 0).astype(int)
            n_adj_total = int(sadj[off_diag].sum())
            n_adj_false = int(((sadj > 0) & (presence == 0))[off_diag].sum())
            n_false_rev = int(sum(
                1 for t2 in range(n) for s2 in range(n)
                if t2 != s2 and presence[s2, t2] == 0 and presence[t2, s2] == 1
            ))
            m["n_adj_total_edges"] = n_adj_total
            m["n_adj_false_edges"] = n_adj_false
            m["n_false_reverses"] = n_false_rev

        # Sign accuracy
        known_s = sign_gt >= 0
        if known_s.any():
            sign_pred = (self.sign_logit.cpu().numpy() > 0).astype(float)
            m["sign_acc"] = float((sign_pred[known_s] == sign_gt[known_s]).mean())
        else:
            m["sign_acc"] = float("nan")

        # Lag accuracy
        known_l = lag_gt >= 0
        if known_l.any():
            lag_pred = (self.lag_logit.cpu().numpy() > 0).astype(float)
            m["lag_acc"] = float((lag_pred[known_l] == lag_gt[known_l]).mean())
        else:
            m["lag_acc"] = float("nan")

        return m
