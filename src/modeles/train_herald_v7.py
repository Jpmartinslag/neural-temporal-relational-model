"""
HERALD V7 — adaptive Ridge/graph mixture + stronger A10 sector head.

V7 is intentionally incremental over V6:
  - keeps the same geo2025 data contract and walk-forward protocol;
  - adds alpha_t,z, a learned local-vs-graph mixture gate;
  - lets the model fall back to Ridge AR when graph correction is noisy;
  - strengthens A10 prediction by blending a neural sector head with lag-1
    sector proportions;
  - exposes variants used by the V7 research battery.

Outputs use the herald_v7_ prefix and do not overwrite V6/Semi artifacts.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ModuleNotFoundError as exc:
    raise SystemExit("PyTorch required. Run inside torch environment.") from exc

import train_herald_v6 as base


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data/processed"
REPORTS = ROOT / "reports"

OUT_JSON = REPORTS / "herald_v7_metrics_v1.json"
OUT_MD = REPORTS / "HERALD_V7_MODEL_V1.md"


def sector_lag1_tensor(sec_props_tensor):
    """Forecast-safe sector prior: A10 proportions from t-1, forward-filled."""
    out = np.empty_like(sec_props_tensor)
    fill = np.full(sec_props_tensor.shape[1:], 1.0 / len(base.A10_SECTORS), dtype=np.float32)
    for t in range(sec_props_tensor.shape[0]):
        if t > 0:
            prev = sec_props_tensor[t - 1]
            valid = np.isfinite(prev).all(axis=-1, keepdims=True)
            fill = np.where(valid, np.nan_to_num(prev, nan=1.0 / len(base.A10_SECTORS)), fill)
        out[t] = fill
    return out.astype(np.float32)


def make_sequences_v7(panel, cols, q_tensor, sec_props_tensor, sec_lag1_tensor,
                      zones_sorted, years_sorted, train_max, target_year):
    seq = base.make_sequences(
        panel, cols, q_tensor, sec_props_tensor,
        zones_sorted, years_sorted, train_max, target_year,
    )
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}
    t_train_idx = [year_to_idx[y] for y in years_sorted if y <= train_max]
    t_full_idx = [year_to_idx[y] for y in years_sorted if y <= target_year]
    seq["sec_prior_train"] = sec_lag1_tensor[t_train_idx].astype(np.float32)
    seq["sec_prior_full"] = sec_lag1_tensor[t_full_idx].astype(np.float32)
    return seq


class HERALDv7Residual(nn.Module):
    """V7 model with local/Ridge fallback and graph correction."""

    def __init__(self, num_nodes, annual_dim, hidden_dim, attn_dim=16, q_hidden=32,
                 n_sectors_a10=9, top_k=10, prior_strength_init=1.0,
                 gate_bias_init=2.0, alpha_bias_init=1.5,
                 latent_regime_dim=None, auto_mask=False,
                 latent_dim_mask_type="sigmoid",
                 latent_dim_beta_start=None, latent_dim_beta_end=None,
                 auditor_mode="none", auditor_bias_init=2.0):
        super().__init__()
        self.num_nodes = num_nodes
        self.hidden_dim = hidden_dim
        self.attn_dim = attn_dim
        self.top_k = top_k
        self.n_sectors_a10 = n_sectors_a10
        # latent_regime_dim controls the learned latent vector size (Phase 2K hyperparameter).
        # Defaults to base.REGIME_DIM (3) for backward compat with all existing configs.
        self._latent_regime_dim = latent_regime_dim if latent_regime_dim is not None else base.REGIME_DIM
        self._auto_mask = auto_mask
        self._latent_dim_mask_type = latent_dim_mask_type
        self._hard_concrete_beta = 2.0 / 3.0
        self._hard_concrete_beta_start = latent_dim_beta_start
        self._hard_concrete_beta_end = latent_dim_beta_end
        self._hard_concrete_gamma = -0.1
        self._hard_concrete_zeta = 1.1
        self._auditor_mode = auditor_mode

        self.quarterly_enc = base.QuarterlyEncoder(in_dim=2, hidden_dim=q_hidden)
        self.q_proj = nn.Linear(q_hidden, hidden_dim)
        self.annual_proj = nn.Linear(annual_dim, hidden_dim)
        self.proj_e = nn.Linear(hidden_dim * 3, hidden_dim)

        # regime_proj_{q,k}: used when explicit regime (manual_flags, zeros) drives the graph.
        self.regime_proj_q = nn.Linear(base.REGIME_DIM, attn_dim)
        self.regime_proj_k = nn.Linear(base.REGIME_DIM, attn_dim)
        # latent_proj_{q,k}: used when the learned latent vector drives the graph (learned_regime_both*).
        self.latent_proj_q = nn.Linear(self._latent_regime_dim, attn_dim)
        self.latent_proj_k = nn.Linear(self._latent_regime_dim, attn_dim)
        self.latent_regime = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self._latent_regime_dim),
            nn.Tanh(),
        )
        self.auditor_gate = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        nn.init.constant_(self.auditor_gate[-1].bias, float(auditor_bias_init))
        # Phase 2K auto-mask: learned per-dimension gate; allows model to deactivate unused dims.
        if auto_mask:
            self.mask_logits = nn.Parameter(torch.zeros(self._latent_regime_dim))
        self.proj_Q = nn.Linear(hidden_dim, attn_dim)
        self.proj_K = nn.Linear(hidden_dim, attn_dim)

        self.gamma_geo = nn.Parameter(torch.tensor(float(prior_strength_init)))
        self.gamma_mob = nn.Parameter(torch.tensor(float(prior_strength_init)))
        self.static_emb_1 = nn.Parameter(torch.empty(num_nodes, attn_dim))
        self.static_emb_2 = nn.Parameter(torch.empty(attn_dim, num_nodes))
        nn.init.orthogonal_(self.static_emb_1)
        nn.init.orthogonal_(self.static_emb_2)

        self.msg_proj = nn.Linear(hidden_dim, hidden_dim)
        self.gate_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        nn.init.constant_(self.gate_mlp[-1].bias, float(gate_bias_init))

        self.gru_local_cell = nn.GRUCell(hidden_dim, hidden_dim)
        self.gru_cell = nn.GRUCell(hidden_dim, hidden_dim)
        self.out_local_residual = nn.Linear(hidden_dim, 1)
        self.out_graph_residual = nn.Linear(hidden_dim, 1)

        # alpha close to 1 means local neural correction; low alpha activates graph correction.
        self.alpha_gate = nn.Sequential(
            nn.Linear(hidden_dim * 2 + self._latent_regime_dim + 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        nn.init.constant_(self.alpha_gate[-1].bias, float(alpha_bias_init))

        # Stronger A10 head: neural props blended with lag-1 sector prior.
        self.out_sector_a10 = nn.Sequential(
            nn.Linear(hidden_dim + 1 + n_sectors_a10, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_sectors_a10),
        )
        self.sector_prior_gate = nn.Sequential(
            nn.Linear(hidden_dim + 1 + n_sectors_a10, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        nn.init.constant_(self.sector_prior_gate[-1].bias, 1.0)

    def _static_adj(self):
        return torch.softmax(torch.relu(self.static_emb_1 @ self.static_emb_2), dim=1)

    def _dynamic_adj(self, e_t, prior_logits, regime_t, use_latent=False):
        if use_latent:
            rq = self.latent_proj_q(regime_t)
            rk = self.latent_proj_k(regime_t)
        else:
            rq = self.regime_proj_q(regime_t)
            rk = self.regime_proj_k(regime_t)
        Q = self.proj_Q(e_t) + rq.unsqueeze(0)
        K = self.proj_K(e_t) + rk.unsqueeze(0)
        raw = (Q @ K.T) / (self.attn_dim ** 0.5)
        return base.topk_sparse_softmax(raw + prior_logits, self.top_k)

    def set_latent_dim_mask_progress(self, epoch, total_epochs):
        """Anneal hard-concrete temperature for Phase 2M auto-regulation tests."""
        if self._hard_concrete_beta_start is None or self._hard_concrete_beta_end is None:
            return
        if total_epochs <= 1:
            ratio = 1.0
        else:
            ratio = min(max(float(epoch) / float(total_epochs - 1), 0.0), 1.0)
        self._hard_concrete_beta = (
            float(self._hard_concrete_beta_start) * (1.0 - ratio)
            + float(self._hard_concrete_beta_end) * ratio
        )

    def _latent_dim_mask(self, stochastic=True):
        if not self._auto_mask:
            return None
        if self._latent_dim_mask_type == "sigmoid":
            return torch.sigmoid(self.mask_logits)
        if self._latent_dim_mask_type == "hard_concrete":
            beta = self._hard_concrete_beta
            gamma = self._hard_concrete_gamma
            zeta = self._hard_concrete_zeta
            if stochastic and self.training:
                eps = torch.finfo(self.mask_logits.dtype).eps
                u = torch.rand_like(self.mask_logits).clamp(eps, 1.0 - eps)
                s = torch.sigmoid((torch.log(u) - torch.log1p(-u) + self.mask_logits) / beta)
            else:
                s = torch.sigmoid(self.mask_logits)
            return torch.clamp(s * (zeta - gamma) + gamma, 0.0, 1.0)
        if self._latent_dim_mask_type == "concrete_dropout":
            p_drop = torch.sigmoid(self.mask_logits)
            if stochastic and self.training:
                eps = torch.finfo(self.mask_logits.dtype).eps
                u = torch.rand_like(self.mask_logits).clamp(eps, 1.0 - eps)
                temp = max(float(self._hard_concrete_beta), 1e-3)
                drop = torch.sigmoid((torch.log(u) - torch.log1p(-u) + self.mask_logits) / temp)
                return 1.0 - drop
            return 1.0 - p_drop
        raise ValueError(f"Unknown latent_dim_mask_type={self._latent_dim_mask_type!r}")

    def _latent_dim_mask_penalty(self):
        if not self._auto_mask:
            return None
        if self._latent_dim_mask_type == "sigmoid":
            return torch.sigmoid(self.mask_logits)
        if self._latent_dim_mask_type == "hard_concrete":
            beta = self._hard_concrete_beta
            gamma = self._hard_concrete_gamma
            zeta = self._hard_concrete_zeta
            offset = beta * math.log(-gamma / zeta)
            return torch.sigmoid(self.mask_logits - offset)
        if self._latent_dim_mask_type == "concrete_dropout":
            # Penalize expected active dimensions, not raw dropout probability.
            return 1.0 - torch.sigmoid(self.mask_logits)
        raise ValueError(f"Unknown latent_dim_mask_type={self._latent_dim_mask_type!r}")

    def _latent_group_lasso_term(self):
        # Output layer rows generate individual latent dimensions.
        out = self.latent_regime[2]
        row_norms = torch.linalg.vector_norm(out.weight, ord=2, dim=1)
        return row_norms.mean(), row_norms.detach().cpu().tolist()

    def _auditor_confidence(self, latent_context):
        if self._auditor_mode == "none":
            return torch.ones((), device=latent_context.device, dtype=latent_context.dtype)
        if self._auditor_mode not in {"latent_scale", "alpha_neutral", "both"}:
            raise ValueError(f"Unknown auditor_mode={self._auditor_mode!r}")
        return torch.sigmoid(self.auditor_gate(latent_context).squeeze())

    def forward(self, x_annual_seq, x_quarterly_seq, regime_seq, sec_prior_seq,
                adj_geo, adj_mob, adj_log_geo, adj_log_mob,
                variant="full", return_internals=False,
                smooth_regime_source="explicit",
                latent_mode="normal"):
        N = self.num_nodes
        device = next(self.parameters()).device
        learned_graph_variants = {"learned_regime_graph", "learned_regime_both", "learned_regime_both_sector_enhanced"}
        learned_gate_variants = {"learned_regime_gate", "learned_regime_both", "learned_regime_gate_sector_enhanced", "learned_regime_both_sector_enhanced"}
        sector_enhanced_variants = {"sector_enhanced", "learned_regime_gate_sector_enhanced", "learned_regime_both_sector_enhanced"}
        h_local = torch.zeros(N, self.hidden_dim, device=device)
        h = torch.zeros(N, self.hidden_dim, device=device)

        prior_logits = self.gamma_geo * adj_log_geo + self.gamma_mob * adj_log_mob
        static_adj_m = self._static_adj()
        fixed_blend = 0.5 * adj_geo + 0.5 * adj_mob

        pred_list, sector_list, alpha_list = [], [], []
        latent_regime_list = []
        auditor_confidence_list = []
        auditor_confidence_list_grad = []
        latent_regime_list_grad = []   # differentiable — for H1 latent regularisation loss
        alpha_balance_list = []        # differentiable — for H4 alpha balance loss
        adj_list, gate_list = [], []
        smooth_term = torch.tensor(0.0, device=device)
        gate_entropy = torch.tensor(0.0, device=device)
        alpha_smooth = torch.tensor(0.0, device=device)
        n_graph = 0
        n_gate = 0
        A_prev = None
        alpha_prev = None
        regime_prev = None
        latent_prev = None
        latent_anchor = None
        adj_delta_list = []
        regime_delta_list = []

        for x_ann, x_q, regime_t, sec_prior_t in zip(
            x_annual_seq, x_quarterly_seq, regime_seq, sec_prior_seq
        ):
            ann = F.relu(self.annual_proj(x_ann))
            q_enc = F.relu(self.q_proj(self.quarterly_enc(x_q)))
            e_t = F.relu(self.proj_e(torch.cat([ann, q_enc, h_local], dim=-1)))
            latent_context = torch.cat([
                e_t.mean(dim=0),
                e_t.std(dim=0, unbiased=False),
            ], dim=-1)
            auditor_confidence = self._auditor_confidence(latent_context)
            latent_regime_t_raw = self.latent_regime(latent_context)
            if latent_mode == "normal":
                latent_regime_t = latent_regime_t_raw
            elif latent_mode == "zero":
                latent_regime_t = torch.zeros_like(latent_regime_t_raw)
            elif latent_mode == "frozen_first":
                if latent_anchor is None:
                    latent_anchor = latent_regime_t_raw.detach()
                latent_regime_t = latent_anchor
            else:
                raise ValueError(f"Unknown latent_mode={latent_mode!r}")
            # Phase 2K auto-mask: z_eff = z * sigmoid(mask_logits).
            if self._auto_mask:
                latent_regime_t = latent_regime_t * self._latent_dim_mask(stochastic=True)
            if self._auditor_mode in {"latent_scale", "both"}:
                latent_regime_t = auditor_confidence * latent_regime_t
            latent_regime_list_grad.append(latent_regime_t)        # keep grad for H1 loss
            latent_regime_list.append(latent_regime_t.detach())    # detached for internals
            auditor_confidence_list_grad.append(auditor_confidence)
            auditor_confidence_list.append(auditor_confidence.detach())
            h_local = self.gru_local_cell(e_t, h_local)

            if variant == "ridge_only":
                A_t = None
                m_t = e_t
            elif variant == "fixed_graph":
                A_t = fixed_blend
                m_t = self.msg_proj(A_t @ e_t)
            elif variant == "static_adaptive":
                A_t = static_adj_m
                m_t = self.msg_proj(A_t @ e_t)
            else:
                if variant in learned_graph_variants:
                    A_t = self._dynamic_adj(e_t, prior_logits, latent_regime_t, use_latent=True)
                elif variant == "no_regime_graph":
                    A_t = self._dynamic_adj(e_t, prior_logits, torch.zeros_like(regime_t), use_latent=False)
                else:
                    A_t = self._dynamic_adj(e_t, prior_logits, regime_t, use_latent=False)
                m_t = self.msg_proj(A_t @ e_t)

            if A_t is not None and A_prev is not None:
                delta_sq = torch.sum((A_t - A_prev) ** 2)
                if smooth_regime_source == "explicit":
                    reg_delta = torch.sum(torch.abs(regime_t - regime_prev))
                    regime_weight = torch.tanh(reg_delta)
                elif smooth_regime_source == "latent":
                    if latent_prev is None:
                        reg_delta = torch.tensor(0.0, device=device)
                    else:
                        reg_delta = torch.sum(torch.abs(latent_regime_t - latent_prev))
                    regime_weight = torch.tanh(reg_delta)
                elif smooth_regime_source == "none":
                    reg_delta = torch.tensor(0.0, device=device)
                    regime_weight = torch.tensor(0.0, device=device)
                else:
                    raise ValueError(f"Unknown smooth_regime_source={smooth_regime_source!r}")
                smooth_term = smooth_term + delta_sq * (1.0 - regime_weight)
                n_graph += 1
                if return_internals:
                    adj_delta_list.append(torch.sqrt(delta_sq.detach()))
                    regime_delta_list.append(reg_delta.detach())

            if variant == "ridge_only":
                z_t = e_t
                g_t = torch.ones(N, 1, device=device)
            else:
                g_t = torch.sigmoid(self.gate_mlp(torch.cat([e_t, m_t], dim=-1)))
                z_t = g_t * e_t + (1.0 - g_t) * m_t
                eps = 1e-8
                gate_entropy = gate_entropy + (
                    -g_t * torch.log(g_t + eps) - (1.0 - g_t) * torch.log(1.0 - g_t + eps)
                ).mean()
                n_gate += 1

            h = self.gru_cell(z_t, h)
            local_residual = self.out_local_residual(h_local).squeeze(-1)
            graph_residual = self.out_graph_residual(h).squeeze(-1)

            graph_disp = torch.mean(torch.abs(m_t - e_t), dim=-1, keepdim=True)
            h_norm = torch.norm(h, dim=-1, keepdim=True) / max(self.hidden_dim ** 0.5, 1.0)
            h_local_norm = torch.norm(h_local, dim=-1, keepdim=True) / max(self.hidden_dim ** 0.5, 1.0)
            if variant == "ridge_only":
                alpha = torch.ones(N, device=device)
            else:
                if variant in learned_gate_variants:
                    r_alpha = latent_regime_t
                elif variant == "no_regime_gate":
                    r_alpha = torch.zeros_like(regime_t)
                else:
                    r_alpha = regime_t
                alpha_input = torch.cat([
                    h_local,
                    h,
                    r_alpha.unsqueeze(0).expand(N, -1),
                    graph_disp,
                    torch.abs(h_norm - h_local_norm),
                ], dim=-1)
                alpha = torch.sigmoid(self.alpha_gate(alpha_input)).squeeze(-1)

            if variant == "graph_only":
                alpha = torch.zeros_like(alpha)
            elif variant == "fixed_alpha_0.5":
                alpha = torch.full_like(alpha, 0.5)
            elif self._auditor_mode in {"alpha_neutral", "both"} and variant in learned_gate_variants:
                alpha = auditor_confidence * alpha + (1.0 - auditor_confidence) * 0.5

            if variant == "ridge_only":
                pred = torch.zeros_like(local_residual)
            else:
                pred = alpha * local_residual + (1.0 - alpha) * graph_residual

            if alpha_prev is not None:
                alpha_smooth = alpha_smooth + torch.mean((alpha - alpha_prev) ** 2)
            alpha_prev = alpha
            alpha_balance_list.append(torch.mean((alpha - 0.5) ** 2))  # grad kept for H4

            sec_prior_t = torch.nan_to_num(sec_prior_t, nan=1.0 / self.n_sectors_a10)
            sector_input = torch.cat([h, pred.detach().unsqueeze(-1), sec_prior_t], dim=-1)
            neural_sector = torch.softmax(self.out_sector_a10(sector_input), dim=-1)
            prior_weight = torch.sigmoid(self.sector_prior_gate(sector_input))
            if variant == "sector_lag1_only":
                sector = sec_prior_t
            elif variant in sector_enhanced_variants:
                sector = prior_weight * sec_prior_t + (1.0 - prior_weight) * neural_sector
            else:
                sector = 0.5 * sec_prior_t + 0.5 * neural_sector
            sector = sector / torch.clamp(sector.sum(dim=-1, keepdim=True), min=1e-8)

            pred_list.append(pred)
            sector_list.append(sector)
            alpha_list.append(alpha.detach())
            if return_internals:
                A_store = A_t if A_t is not None else torch.eye(N, device=device)
                adj_list.append(A_store.detach())
                gate_list.append(g_t.detach())

            A_prev = A_t
            regime_prev = regime_t
            latent_prev = latent_regime_t.detach()

        if n_graph > 0:
            smooth_term = smooth_term / n_graph
        if n_gate > 0:
            gate_entropy = gate_entropy / n_gate
        if len(pred_list) > 1:
            alpha_smooth = alpha_smooth / (len(pred_list) - 1)

        preds = torch.stack(pred_list, dim=0)
        sectors = torch.stack(sector_list, dim=0)
        alpha_tensor = torch.stack(alpha_list, dim=0)
        latent_regime_tensor = torch.stack(latent_regime_list, dim=0)
        auditor_confidence_tensor = torch.stack(auditor_confidence_list, dim=0).view(-1)

        # H1 latent regularisation terms (differentiable — C1/C2 fix)
        if latent_regime_list_grad:
            lat_stack = torch.stack(latent_regime_list_grad, dim=0)  # (T, REGIME_DIM)
            lat_var = lat_stack.var(dim=0).mean()
            latent_collapse_term = F.relu(0.05 - lat_var)
            if lat_stack.shape[0] > 1:
                latent_smooth_term = ((lat_stack[1:] - lat_stack[:-1]) ** 2).mean()
                latent_step_norm = (lat_stack[1:] - lat_stack[:-1]).norm(dim=-1)
                step_threshold = float(getattr(self, "_latent_step_threshold", 0.6))
                latent_max_step_term = F.relu(latent_step_norm - step_threshold).pow(2).mean()
            else:
                latent_smooth_term = torch.tensor(0.0, device=device)
                latent_max_step_term = torch.tensor(0.0, device=device)
        else:
            latent_collapse_term = torch.tensor(0.0, device=device)
            latent_smooth_term = torch.tensor(0.0, device=device)
            latent_max_step_term = torch.tensor(0.0, device=device)

        # H4 alpha balance term (differentiable — C2 fix)
        alpha_balance_term = (
            torch.stack(alpha_balance_list).mean()
            if alpha_balance_list
            else torch.tensor(0.0, device=device)
        )

        if auditor_confidence_list_grad:
            auditor_stack = torch.stack(auditor_confidence_list_grad, dim=0).view(-1)
            auditor_budget_term = auditor_stack.mean()
            if auditor_stack.shape[0] > 1:
                auditor_smooth_term = ((auditor_stack[1:] - auditor_stack[:-1]) ** 2).mean()
                auditor_var = auditor_stack.var(unbiased=False)
            else:
                auditor_smooth_term = torch.tensor(0.0, device=device)
                auditor_var = torch.tensor(0.0, device=device)
        else:
            auditor_budget_term = torch.tensor(0.0, device=device)
            auditor_smooth_term = torch.tensor(0.0, device=device)
            auditor_var = torch.tensor(0.0, device=device)

        # Phase 2K auto-mask L1 term: mean(sigmoid(mask_logits)) penalizes active dimensions.
        latent_group_lasso_term, latent_group_norm_values = self._latent_group_lasso_term()
        latent_group_effective_dim = int(
            sum(float(v) > 1e-3 for v in latent_group_norm_values)
        )
        if self._auto_mask:
            mask_penalty = self._latent_dim_mask_penalty()
            mask_values = self._latent_dim_mask(stochastic=False)
            latent_dim_mask_l1_term = mask_penalty.mean()
            latent_dim_mask_values = mask_values.detach().cpu().tolist()
            latent_dim_effective_dim = int((mask_values.detach() > 0.2).sum().item())
        else:
            latent_dim_mask_l1_term = torch.tensor(0.0, device=device)
            latent_dim_mask_values = None
            latent_dim_effective_dim = self._latent_regime_dim

        graph_losses = {
            "smooth_term": smooth_term,
            "contrast_term": torch.tensor(0.0, device=device),
            "gate_entropy": gate_entropy,
            "alpha_smooth": alpha_smooth,
            "latent_collapse_term": latent_collapse_term,
            "latent_smooth_term": latent_smooth_term,
            "latent_max_step_term": latent_max_step_term,
            "alpha_balance_term": alpha_balance_term,
            "latent_dim_mask_l1_term": latent_dim_mask_l1_term,
            "latent_dim_mask_values": latent_dim_mask_values,
            "latent_dim_effective_dim": latent_dim_effective_dim,
            "latent_dim_mask_type": self._latent_dim_mask_type,
            "latent_group_lasso_term": latent_group_lasso_term,
            "latent_group_norm_values": latent_group_norm_values,
            "latent_group_effective_dim": latent_group_effective_dim,
            "latent_dim_mask_beta": float(self._hard_concrete_beta),
            "auditor_mode": self._auditor_mode,
            "auditor_budget_term": auditor_budget_term,
            "auditor_smooth_term": auditor_smooth_term,
            "auditor_variance": auditor_var,
            "auditor_confidence_values": auditor_confidence_tensor.detach().cpu().tolist(),
        }

        if return_internals:
            adj_tensor = torch.stack(adj_list, dim=0)
            gate_tensor = torch.stack(gate_list, dim=0)
            if adj_delta_list:
                adj_delta = torch.stack(adj_delta_list)
                regime_delta = torch.stack(regime_delta_list)
            else:
                adj_delta = torch.zeros(0, device=device)
                regime_delta = torch.zeros(0, device=device)
            return (
                preds,
                sectors,
                graph_losses,
                adj_tensor,
                gate_tensor,
                alpha_tensor,
                latent_regime_tensor,
                auditor_confidence_tensor,
                regime_delta,
                adj_delta,
            )

        return preds, sectors, graph_losses


def train_herald_v7(seq, adj_geo, adj_mob, args, device):
    N = len(seq["zones"])
    annual_dim = seq["x_ann_train"].shape[-1]
    model = HERALDv7Residual(
        num_nodes=N,
        annual_dim=annual_dim,
        hidden_dim=args.hidden_dim,
        attn_dim=args.attn_dim,
        q_hidden=args.q_hidden,
        n_sectors_a10=len(base.A10_SECTORS),
        top_k=args.top_k,
        prior_strength_init=args.prior_strength_init,
        gate_bias_init=args.gate_bias_init,
        alpha_bias_init=args.alpha_bias_init,
    ).to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    huber = nn.HuberLoss(delta=args.huber_delta, reduction="none")

    x_ann = torch.tensor(seq["x_ann_train"], device=device)
    x_q = torch.tensor(seq["q_train"], device=device)
    regime = torch.tensor(seq["regime_train"], device=device)
    sec_prior = torch.tensor(seq["sec_prior_train"], device=device)
    target = torch.tensor(seq["train_resid"], device=device)
    mask = torch.tensor(seq["mask"], device=device)
    zone_w = torch.tensor(seq["zone_weight"], device=device)
    sec_t = torch.tensor(seq["sec_train"], device=device)
    sec_m = torch.tensor(seq["sec_mask"], device=device)

    adj_g = torch.tensor(adj_geo, device=device)
    adj_m_t = torch.tensor(adj_mob, device=device)
    adj_log_g = torch.log(adj_g + 1e-6)
    adj_log_m = torch.log(adj_m_t + 1e-6)

    T = x_ann.shape[0]
    model.train()
    for _ in range(args.epochs):
        opt.zero_grad()
        ann_list = [x_ann[t] for t in range(T)]
        q_list = [x_q[t].permute(1, 0, 2) for t in range(T)]
        reg_list = [regime[t] for t in range(T)]
        sec_prior_list = [sec_prior[t] for t in range(T)]

        pred_main, pred_sector, graph_losses = model(
            ann_list, q_list, reg_list, sec_prior_list,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            variant=args.variant,
            return_internals=False,
            smooth_regime_source=args.smooth_regime_source,
            latent_mode=args.latent_train_mode,
        )

        zone_w_bc = zone_w.unsqueeze(0).expand_as(pred_main)
        denom = torch.clamp((mask * zone_w_bc).sum(), min=1.0)
        loss_main = (huber(pred_main, target) * mask * zone_w_bc).sum() / denom

        eps = 1e-8
        kl = sec_t * (torch.log(sec_t + eps) - torch.log(pred_sector + eps))
        loss_sec = (kl.sum(-1) * sec_m).sum() / torch.clamp(sec_m.sum(), min=1.0)

        loss_graph = (
            args.smooth_lambda * graph_losses["smooth_term"]
            - args.gate_entropy_lambda * graph_losses["gate_entropy"]
            + args.alpha_smooth_lambda * graph_losses["alpha_smooth"]
        )
        loss = loss_main + args.sector_lambda * loss_sec + loss_graph
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

    model.eval()
    with torch.no_grad():
        x_ann_f = torch.tensor(seq["x_ann_full"], device=device)
        x_q_f = torch.tensor(seq["q_full"], device=device)
        reg_f = torch.tensor(seq["regime_full"], device=device)
        sec_prior_f = torch.tensor(seq["sec_prior_full"], device=device)
        T_full = x_ann_f.shape[0]
        ann_f = [x_ann_f[t] for t in range(T_full)]
        q_f = [x_q_f[t].permute(1, 0, 2) for t in range(T_full)]
        reg_fl = [reg_f[t] for t in range(T_full)]
        sec_prior_fl = [sec_prior_f[t] for t in range(T_full)]

        pred_f, sec_f, graph_f, adj_t, gate_t, alpha_t, latent_regime_t, regime_delta_t, adj_delta_t = model(
            ann_f, q_f, reg_fl, sec_prior_fl,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            variant=args.variant,
            return_internals=True,
            smooth_regime_source=args.smooth_regime_source,
            latent_mode=args.latent_inference_mode if args.latent_inference_mode != "match_train" else args.latent_train_mode,
        )

    internals = {
        "dynamic_adj": adj_t.cpu().numpy(),
        "gate_values": gate_t.cpu().numpy(),
        "alpha_values": alpha_t.cpu().numpy(),
        "latent_regime_values": latent_regime_t.cpu().numpy(),
        "regime_delta_by_year": regime_delta_t.cpu().numpy(),
        "adj_delta_by_year": adj_delta_t.cpu().numpy(),
        "sector_proportions": sec_f[-1].cpu().numpy(),
        "gamma_geo": float(model.gamma_geo.item()),
        "gamma_mob": float(model.gamma_mob.item()),
        "smooth_loss_inference": float(graph_f["smooth_term"].item()),
        "gate_entropy_inference": float(graph_f["gate_entropy"].item()),
        "alpha_smooth_inference": float(graph_f["alpha_smooth"].item()),
        "years": seq["years_full"],
        "node_order": seq["zones"],
    }
    return pred_f[-1].cpu().numpy(), sec_f[-1].cpu().numpy(), internals


def evaluate_herald_v7(panel, a10_panel, splits, cols, q_tensor, sec_props_tensor,
                       sec_lag1_tensor, zones_sorted, years_sorted, adj_geo, adj_mob,
                       args, device):
    total_rows, sector_rows = [], []
    internals_by_year = {}

    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max = int(split["train_years_max"])
        print(f"  Fold {target_year}...", flush=True)

        seq = make_sequences_v7(
            panel, cols, q_tensor, sec_props_tensor, sec_lag1_tensor,
            zones_sorted, years_sorted, train_max, target_year,
        )
        residual, sector_props, internals = train_herald_v7(seq, adj_geo, adj_mob, args, device)
        internals["target_year"] = target_year
        internals_by_year[target_year] = internals

        mask_ = seq["test_mask"]
        y_true = seq["test_y"][mask_]
        ridge_p = seq["test_ridge"][mask_]
        zone_std = seq["zone_std"][mask_]
        y_pred = np.maximum(ridge_p + residual[mask_] * zone_std, 0.0)
        s_props = sector_props[mask_]
        zones_arr = np.asarray(zones_sorted)[mask_]
        a10_test = a10_panel[a10_panel["target_year"] == target_year].set_index("ZE2020")

        for i, (ze, yt, yp) in enumerate(zip(zones_arr, y_true, y_pred)):
            total_rows.append({
                "model": "herald_v7",
                "variant": args.variant,
                "target_year": target_year,
                "ZE2020": int(ze),
                "y_true": float(yt),
                "y_pred": float(yp),
                "ridge_pred": float(ridge_p[i]),
                "abs_error": float(abs(yt - yp)),
            })
            for si, s in enumerate(base.A10_SECTORS):
                y_true_s = float(a10_test.loc[ze, s]) if ze in a10_test.index else np.nan
                sector_rows.append({
                    "model": "herald_v7",
                    "variant": args.variant,
                    "target_year": target_year,
                    "ZE2020": int(ze),
                    "sector": s,
                    "y_true_sector": y_true_s,
                    "y_pred_sector": float(yp * s_props[i, si]),
                    "y_pred_total": float(yp),
                    "prop_pred": float(s_props[i, si]),
                })

    return total_rows, sector_rows, internals_by_year


def write_report(total_rows, sector_rows, args, internals_by_year):
    total_df = pd.DataFrame(total_rows)
    sector_df = pd.DataFrame(sector_rows)

    per_year = []
    for year, g in total_df.groupby("target_year"):
        per_year.append({"target_year": int(year), "wmape": base.wmape(g["y_true"], g["y_pred"]), "n": len(g)})
    tmdf = pd.DataFrame(per_year)
    mean_wmape = float(tmdf["wmape"].mean())
    wmape_2025 = float(tmdf.loc[tmdf["target_year"] == 2025, "wmape"].iloc[0]) if 2025 in set(tmdf["target_year"]) else np.nan

    sector_wmape = {}
    valid_sector = sector_df.dropna(subset=["y_true_sector"])
    for s in base.A10_SECTORS:
        df_s = valid_sector[valid_sector["sector"] == s]
        if len(df_s) > 0:
            sector_wmape[s] = round(base.wmape(df_s["y_true_sector"], df_s["y_pred_sector"]), 5)
    sector_wmape_mean = round(float(np.mean(list(sector_wmape.values()))), 5) if sector_wmape else np.nan

    last = internals_by_year[max(internals_by_year)]
    years_f = last["years"]
    gate_arr = last["gate_values"]
    alpha_arr = last["alpha_values"]
    gate_by_year = {int(yr): round(float(gate_arr[t].mean()), 5) for t, yr in enumerate(years_f)}
    alpha_by_year = {int(yr): round(float(alpha_arr[t].mean()), 5) for t, yr in enumerate(years_f)}

    tag = f"_{args.run_tag}" if args.run_tag else ""
    run_key = f"{args.variant}{tag}_seed_{args.seed}"
    result = {
        "variant": args.variant,
        "seed": args.seed,
        "run_tag": args.run_tag,
        "hidden_dim": args.hidden_dim,
        "total_wmape_mean": round(mean_wmape, 6),
        "total_wmape_2025": round(wmape_2025, 6) if np.isfinite(wmape_2025) else None,
        "per_year_total": {int(r.target_year): round(float(r.wmape), 6) for r in tmdf.itertuples(index=False)},
        "sector_wmape": sector_wmape,
        "sector_wmape_mean": sector_wmape_mean,
        "gate_by_year": gate_by_year,
        "alpha_by_year": alpha_by_year,
        "gamma_geo": round(last["gamma_geo"], 4),
        "gamma_mob": round(last["gamma_mob"], 4),
        "regime_delta_by_year": [round(float(x), 6) for x in last["regime_delta_by_year"]],
        "adj_delta_by_year": [round(float(x), 6) for x in last["adj_delta_by_year"]],
        "alpha_smooth_inference": round(last["alpha_smooth_inference"], 6),
    }

    existing = {}
    if args.metrics_path.exists():
        existing = json.loads(args.metrics_path.read_text(encoding="utf-8"))
    existing[run_key] = result
    args.metrics_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    lines = [
        "# HERALD V7 - adaptive Ridge/graph mixture",
        "",
        "| Run | Total WMAPE | 2025 WMAPE | Sector WMAPE |",
        "|---|---:|---:|---:|",
    ]
    for rk, rv in sorted(existing.items()):
        mw = rv["total_wmape_mean"]
        w25 = rv.get("total_wmape_2025")
        sec = rv.get("sector_wmape_mean")
        lines.append(f"| {rk} | {mw:.6f} | {w25 if w25 is not None else 'NA'} | {sec} |")
    lines += ["", f"## Per-year WMAPE - {run_key}", "", "| Year | WMAPE | alpha local mean |", "|---:|---:|---:|"]
    for r in tmdf.sort_values("target_year").itertuples(index=False):
        lines.append(f"| {int(r.target_year)} | {float(r.wmape):.6f} | {alpha_by_year.get(int(r.target_year), np.nan)} |")
    if sector_wmape:
        lines += ["", f"## A10 WMAPE - {run_key}", "", "| Sector | WMAPE |", "|---|---:|"]
        for s in sorted(sector_wmape, key=lambda x: sector_wmape[x]):
            lines.append(f"| {s} | {sector_wmape[s]:.5f} |")
    args.model_card_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n=== HERALD V7 ({run_key}) ===")
    print(f"Total WMAPE:       {mean_wmape:.6f}")
    if np.isfinite(wmape_2025):
        print(f"2025 WMAPE:        {wmape_2025:.6f}")
    print(f"Sector WMAPE mean: {sector_wmape_mean:.5f}")
    print(f"alpha 2025:        {alpha_by_year.get(2025, '?')}")
    print(f"gamma_geo={last['gamma_geo']:.3f} gamma_mob={last['gamma_mob']:.3f}")


def main():
    parser = argparse.ArgumentParser(description="HERALD V7")
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--q-hidden", type=int, default=32)
    parser.add_argument("--attn-dim", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--prior-strength-init", type=float, default=1.0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--huber-delta", type=float, default=300.0)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--smooth-lambda", type=float, default=0.01)
    parser.add_argument("--gate-entropy-lambda", type=float, default=0.001)
    parser.add_argument("--alpha-smooth-lambda", type=float, default=0.001)
    parser.add_argument("--gate-bias-init", type=float, default=2.0)
    parser.add_argument("--alpha-bias-init", type=float, default=1.5)
    parser.add_argument("--sector-lambda", type=float, default=0.1)
    parser.add_argument("--smooth-regime-source", default="explicit",
                        choices=["explicit", "none", "latent"])
    parser.add_argument("--latent-train-mode", default="normal",
                        choices=["normal", "zero", "frozen_first"])
    parser.add_argument("--latent-inference-mode", default="match_train",
                        choices=["match_train", "normal", "zero", "frozen_first"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--panel-path", type=Path, default=base.PANEL_PATH)
    parser.add_argument("--splits-path", type=Path, default=base.SPLITS_PATH)
    parser.add_argument("--side-a10-path", type=Path, default=base.SIDE_A10_PATH)
    parser.add_argument("--prediction-output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--metrics-path", type=Path, default=OUT_JSON)
    parser.add_argument("--model-card-path", type=Path, default=OUT_MD)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--variant", default="full",
                        choices=[
                            "full",
                            "ridge_graph_gate",  # alias of "full" kept for back-compat
                            "graph_only",
                            "ridge_only",
                            "fixed_graph",
                            "fixed_alpha_0.5",
                            "no_regime_gate",
                            "no_regime_graph",
                            "learned_regime_graph",
                            "learned_regime_gate",
                            "learned_regime_both",
                            "learned_regime_gate_sector_enhanced",
                            "learned_regime_both_sector_enhanced",
                            "static_adaptive",
                            "sector_enhanced",
                            "sector_lag1_only",
                        ])
    parser.add_argument("--run-tag", default="")
    args = parser.parse_args()

    base.set_seed(args.seed)
    device = torch.device(args.device)
    args.prediction_output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_path.parent.mkdir(parents=True, exist_ok=True)
    args.model_card_path.parent.mkdir(parents=True, exist_ok=True)
    base.SIDE_A10_PATH = args.side_a10_path

    print("Loading data...")
    panel = pd.read_csv(args.panel_path).sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    splits = pd.read_csv(args.splits_path)
    cols = base.feature_columns(panel, ablation="full")
    adj_geo = base.load_adjacency(base.GEO_ADJ_PATH)
    adj_mob = base.load_adjacency(base.MOB_ADJ_PATH)
    zones_sorted = sorted(panel["ZE2020"].unique())
    years_sorted = sorted(panel["target_year"].unique())

    print("Loading A10 sectoral panel...")
    a10_panel = base.load_or_build_side_a10_panel(zones_sorted)

    print("Building tensors...")
    q_tensor = base.build_quarterly_tensor(zones_sorted, years_sorted)
    sec_props_tensor = base.build_sector_props_target(a10_panel, zones_sorted, years_sorted)
    sec_lag1 = sector_lag1_tensor(sec_props_tensor)
    print(f"  Quarterly:    {q_tensor.shape}")
    print(f"  Sector props: {sec_props_tensor.shape}")
    print(f"  Sector lag1:  {sec_lag1.shape}")
    print(f"  Features:     {len(cols)}")
    print(f"  Variant:      {args.variant}  Device: {device}")

    print(f"\nTraining HERALD V7 (variant={args.variant}, seed={args.seed})...")
    total_rows, sector_rows, internals_by_year = evaluate_herald_v7(
        panel, a10_panel, splits, cols, q_tensor, sec_props_tensor,
        sec_lag1, zones_sorted, years_sorted, adj_geo, adj_mob, args, device,
    )

    tag = f"_{args.run_tag}" if args.run_tag else ""
    suffix = f"{args.variant}{tag}_seed_{args.seed}"
    out_total = args.prediction_output_dir / f"herald_v7_predictions_total_{suffix}_v1.csv"
    out_sector = args.prediction_output_dir / f"herald_v7_predictions_sector_{suffix}_v1.csv"
    out_int = args.prediction_output_dir / f"herald_v7_internals_{suffix}_v1.npz"

    pd.DataFrame(total_rows).to_csv(out_total, index=False)
    pd.DataFrame(sector_rows).to_csv(out_sector, index=False)

    last = internals_by_year[max(internals_by_year)]
    np.savez_compressed(
        out_int,
        dynamic_adj=last["dynamic_adj"],
        gate_values=last["gate_values"],
        alpha_values=last["alpha_values"],
        latent_regime_values=last["latent_regime_values"],
        regime_delta_by_year=last["regime_delta_by_year"],
        adj_delta_by_year=last["adj_delta_by_year"],
        sector_proportions=last["sector_proportions"],
        gamma_geo=np.array([last["gamma_geo"]]),
        gamma_mob=np.array([last["gamma_mob"]]),
        alpha_smooth_inference=np.array([last["alpha_smooth_inference"]]),
        years=np.array(last["years"]),
        node_order=np.array(last["node_order"]),
        sector_names=np.array(base.A10_SECTORS),
    )

    write_report(total_rows, sector_rows, args, internals_by_year)

    print(f"\nSaved: {out_total}")
    print(f"Saved: {out_sector}")
    print(f"Saved: {out_int}")
    print(f"Saved: {args.metrics_path}")
    print(f"Saved: {args.model_card_path}")


if __name__ == "__main__":
    main()
