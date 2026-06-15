"""
gated_model.py — Decoupled temporal + gated graph residual (DEC-053).

prediction = y_temporal + gate * clamp(graph_residual, ±max_r)

Components:
  B. TemporalDecoder  — frozen HERALDGraphImputerLagged, adj=0
  C. GraphMessageExpert — small MLP on directed messages from GraphRelationHead
  D. UtilityGate       — small sigmoid MLP; gate=0 reproduces temporal exactly

Invariants:
  gate in [0, 1] at all times (sigmoid output)
  graph_residual clamped to ±MAX_RESIDUAL_FRAC * |y_temporal|.mean()
  gate=0 → prediction == y_temporal exactly (initialised near 0 via bias=-5)
  No target values in gate inputs
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.phase16_decoupled.graph_relation_head import GraphRelationHead

# Frozen before experiment
MAX_RESIDUAL_FRAC: float = 0.15
GATE_HIDDEN: int = 8


class GraphMessageExpert(nn.Module):
    """Maps directed graph messages to a per-cell residual correction."""

    def __init__(self, hidden: int = GATE_HIDDEN):
        super().__init__()
        # inputs: [msg_lag1_magnitude, msg_lag2_magnitude] per cell → residual scalar
        self.net = nn.Sequential(
            nn.Linear(2, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, msg1: torch.Tensor, msg2: torch.Tensor) -> torch.Tensor:
        """
        msg1, msg2: (n_T, n_S, n_Y) directed message magnitudes at lag 1/2.
        Returns residual (n_T, n_S, n_Y).
        """
        x = torch.stack([msg1, msg2], dim=-1)    # (n_T, n_S, n_Y, 2)
        return self.net(x).squeeze(-1)           # (n_T, n_S, n_Y)


class UtilityGate(nn.Module):
    """
    Sigmoid gate ∈ [0,1] per (territory, sector, year) cell.
    Inputs: temporal_prediction (normalised), message_magnitude, obs_fraction.
    Initialised near 0 (gate starts closed): final bias = -5.
    """

    def __init__(self, hidden: int = GATE_HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
            nn.Sigmoid(),
        )
        # Initialise near-zero gate
        with torch.no_grad():
            self.net[-2].bias.fill_(-5.0)

    def forward(
        self,
        y_temporal: torch.Tensor,     # (n_T, n_S, n_Y) — no grad, no target
        msg_mag: torch.Tensor,        # (n_T, n_S, n_Y) message magnitude
        obs_mask: torch.Tensor,       # (n_T, n_S, n_Y)
    ) -> torch.Tensor:
        # Normalise temporal prediction: centre/scale per batch
        y_scale = y_temporal.abs().mean().clamp(min=1e-6)
        y_norm = y_temporal / y_scale

        # obs fraction per sector (mean over T and Y)
        obs_frac = obs_mask.mean(dim=(0, 2), keepdim=True).expand_as(y_temporal)

        x = torch.stack([y_norm, msg_mag, obs_frac], dim=-1)   # (n_T, n_S, n_Y, 3)
        return self.net(x).squeeze(-1)                          # (n_T, n_S, n_Y)


class GatedGraphModel(nn.Module):
    """
    Decoupled graph-temporal model.

    Only graph_relation_head, graph_expert, gate are trainable.
    Temporal backbone is frozen.
    """

    def __init__(
        self,
        temporal_backbone: HERALDGraphImputerLagged,
        n_sectors: int,
        max_residual_frac: float = MAX_RESIDUAL_FRAC,
    ):
        super().__init__()
        self.n_S = n_sectors
        self.max_residual_frac = max_residual_frac

        # Component B: frozen temporal backbone
        self.backbone = temporal_backbone
        for p in self.backbone.parameters():
            p.requires_grad_(False)

        # Components C and D: trainable
        self.graph_relation_head = GraphRelationHead(n_sectors)
        self.graph_expert = GraphMessageExpert()
        self.gate = UtilityGate()

    # ── Core forward ──────────────────────────────────────────────────────────

    def _temporal_pred(
        self, panel: np.ndarray, obs_mask: np.ndarray, device: str
    ) -> tuple[np.ndarray, np.ndarray]:
        """Temporal-only prediction using frozen backbone with adj=0."""
        n_S = panel.shape[1]
        zeros_s = np.zeros((n_S, n_S), dtype=np.float32)
        zeros_t = np.zeros((panel.shape[0], panel.shape[0]), dtype=np.float32)
        panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(
            panel, obs_mask, zeros_s, zeros_t, device
        )
        tf = _build_temporal_features(panel, obs_mask).astype(np.float32)
        tf_t = torch.from_numpy(tf).to(device)
        with torch.no_grad():
            out = self.backbone(panel_t, mask_t, adj_s_t, adj_t_t, tf_t)
        return out[..., 0].cpu().numpy(), out[..., 1].cpu().numpy()

    def _directed_messages(
        self,
        panel: np.ndarray,
        obs_mask: np.ndarray,
        device: str,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Directed graph messages from GraphRelationHead.
        Returns (msg1, msg2) each of shape (n_T, n_S, n_Y).

        msg_lag1[t, tgt, y] = Σ_src attn1[tgt,src] * panel[t,src,y-1] * obs[t,src,y-1]
        msg_lag2[t, tgt, y] = Σ_src attn2[tgt,src] * panel[t,src,y-2] * obs[t,src,y-2]
        """
        n_T, n_S, n_Y = panel.shape
        attn1 = self.graph_relation_head.directed_attention(lag=1)  # (n_S, n_S)
        attn2 = self.graph_relation_head.directed_attention(lag=2)  # (n_S, n_S)

        p_t = torch.from_numpy(panel.astype(np.float32)).to(device)    # (n_T, n_S, n_Y)
        m_t = torch.from_numpy(obs_mask.astype(np.float32)).to(device) # (n_T, n_S, n_Y)

        msg1 = torch.zeros(n_T, n_S, n_Y, device=device)
        msg2 = torch.zeros(n_T, n_S, n_Y, device=device)

        for y in range(n_Y):
            if y >= 1:
                src_vals = p_t[:, :, y - 1] * m_t[:, :, y - 1]    # (n_T, n_S)
                # msg1[:, tgt, y] = Σ_src attn1[tgt, src] * src_vals[:, src]
                msg1[:, :, y] = src_vals @ attn1.T   # (n_T, n_S) @ (n_S, n_S) = (n_T, n_S)
            if y >= 2:
                src_vals2 = p_t[:, :, y - 2] * m_t[:, :, y - 2]
                msg2[:, :, y] = src_vals2 @ attn2.T

        return msg1, msg2

    def forward_tensors(
        self,
        panel: np.ndarray,
        obs_mask: np.ndarray,
        device: str,
    ) -> dict:
        """
        Full forward pass. Returns dict with:
          y_pred, y_temporal, gate, graph_residual, log_sigma
        """
        # Temporal prediction (frozen, no graph)
        y_temp_np, log_sigma_np = self._temporal_pred(panel, obs_mask, device)
        y_temporal = torch.from_numpy(y_temp_np).to(device)
        log_sigma = torch.from_numpy(log_sigma_np).to(device)

        # Directed messages
        msg1, msg2 = self._directed_messages(panel, obs_mask, device)

        # Graph residual
        raw_residual = self.graph_expert(msg1, msg2)           # (n_T, n_S, n_Y)
        max_r = self.max_residual_frac * y_temporal.abs().mean().clamp(min=1e-6)
        graph_residual = raw_residual.clamp(-max_r, max_r)

        # Gate (no target in inputs)
        obs_t = torch.from_numpy(obs_mask.astype(np.float32)).to(device)
        msg_mag = (msg1.abs() + msg2.abs()) / 2.0
        gate = self.gate(y_temporal.detach(), msg_mag.detach(), obs_t)  # gate uses no-grad temp

        # Final prediction
        y_pred = y_temporal + gate * graph_residual

        return {
            "y_pred": y_pred,
            "y_temporal": y_temporal,
            "gate": gate,
            "graph_residual": graph_residual,
            "log_sigma": log_sigma,
            "msg_mag": msg_mag,
        }

    # ── 3 evaluation modes ────────────────────────────────────────────────────

    @torch.no_grad()
    def predict_temporal_only(
        self, panel: np.ndarray, obs_mask: np.ndarray, device: str
    ) -> np.ndarray:
        """Mode B: temporal-only prediction, no graph influence."""
        y, _ = self._temporal_pred(panel, obs_mask, device)
        return y

    @torch.no_grad()
    def predict_gated(
        self, panel: np.ndarray, obs_mask: np.ndarray, device: str
    ) -> tuple[np.ndarray, np.ndarray]:
        """Mode GATED: y_temporal + gate * residual. Returns (y_pred, gate)."""
        out = self.forward_tensors(panel, obs_mask, device)
        return out["y_pred"].cpu().numpy(), out["gate"].cpu().numpy()

    @torch.no_grad()
    def predict_graph_always_on(
        self, panel: np.ndarray, obs_mask: np.ndarray, device: str
    ) -> np.ndarray:
        """Mode GRAPH_ALWAYS: gate forced to 1, uses full residual."""
        y_temp_np, _ = self._temporal_pred(panel, obs_mask, device)
        y_temporal = torch.from_numpy(y_temp_np).to(device)
        msg1, msg2 = self._directed_messages(panel, obs_mask, device)
        raw_residual = self.graph_expert(msg1, msg2)
        max_r = self.max_residual_frac * y_temporal.abs().mean().clamp(min=1e-6)
        graph_residual = raw_residual.clamp(-max_r, max_r)
        return (y_temporal + graph_residual).cpu().numpy()

    @torch.no_grad()
    def predict_gate_stats(
        self, panel: np.ndarray, obs_mask: np.ndarray, device: str
    ) -> dict:
        """Returns gate distribution statistics."""
        _, gate = self.predict_gated(panel, obs_mask, device)
        return {
            "gate_mean": float(gate.mean()),
            "gate_median": float(np.median(gate)),
            "gate_std": float(gate.std()),
            "gate_frac_above_half": float((gate > 0.5).mean()),
            "gate_max": float(gate.max()),
            "gate_min": float(gate.min()),
        }
