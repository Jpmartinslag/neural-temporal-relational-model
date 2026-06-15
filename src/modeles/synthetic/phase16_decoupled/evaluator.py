"""
evaluator.py — 3-mode evaluation for DEC-053.

Modes:
  ANALYTIC_GRAPH_ONLY       — directed graph metrics only (no imputation judgment)
  TEMPORAL_RECONSTRUCTION   — temporal backbone vs ffill/Ridge, no graph
  GATED_GRAPH_ASSIST        — temporal + gated residual vs all baselines

Each mode returns standardised dicts compatible with gates_dec053.
"""

from __future__ import annotations

import numpy as np
import torch

from src.modeles.synthetic.phase16_decoupled.gated_model import GatedGraphModel


# ── Baselines ─────────────────────────────────────────────────────────────────

def _ffill(panel: np.ndarray, obs_mask: np.ndarray) -> np.ndarray:
    """Forward-fill imputation per territory/sector."""
    n_T, n_S, n_Y = panel.shape
    out = np.copy(panel)
    for t in range(n_T):
        for s in range(n_S):
            last = 0.0
            for y in range(n_Y):
                if obs_mask[t, s, y]:
                    last = panel[t, s, y]
                else:
                    out[t, s, y] = last
    return out


def _ridge_impute(panel: np.ndarray, obs_mask: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """Ridge regression: predict each missing cell from observed in same year."""
    from sklearn.linear_model import Ridge
    n_T, n_S, n_Y = panel.shape
    out = np.copy(panel)
    for y in range(n_Y):
        for s in range(n_S):
            obs_row = obs_mask[:, s, y].astype(bool)
            miss_row = ~obs_row
            if miss_row.sum() == 0:
                continue
            feature_sectors = [s2 for s2 in range(n_S) if s2 != s]
            X_feat = panel[:, feature_sectors, y]  # all territories, other sectors
            X_train = X_feat[obs_row]
            y_train = panel[obs_row, s, y]
            X_miss = X_feat[miss_row]
            if X_train.shape[0] < 2:
                continue
            try:
                reg = Ridge(alpha=alpha).fit(X_train, y_train)
                out[miss_row, s, y] = reg.predict(X_miss)
            except Exception:
                pass
    return out


def _permuted_graph(
    model: GatedGraphModel,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    device: str,
    seed: int = 0,
) -> np.ndarray:
    """Permute sector-pair indices in graph head before evaluating — null control."""
    rng = np.random.default_rng(seed)
    perm = rng.permutation(model.graph_relation_head.n_S)
    orig = model.graph_relation_head.presence_logit.data.clone()
    with torch.no_grad():
        model.graph_relation_head.presence_logit.data = orig[perm, :][:, perm]
        y_perm, _ = model.predict_gated(panel, obs_mask, device)
        model.graph_relation_head.presence_logit.data = orig
    return y_perm


def _eval_mask(obs_mask: np.ndarray) -> np.ndarray:
    """Cells that are structurally present but missing: where we measure MAE."""
    return (obs_mask == 0).astype(np.float32)


def _mae(pred: np.ndarray, true: np.ndarray, mask: np.ndarray) -> float:
    n = mask.sum()
    if n == 0:
        return float("nan")
    return float(np.abs(pred - true)[mask > 0].mean())


# ── Mode 1: ANALYTIC_GRAPH_ONLY ───────────────────────────────────────────────

def evaluate_analytic_graph(
    model: GatedGraphModel,
    true_relations: list,
    sector_adj: np.ndarray | None,
) -> dict:
    """
    ANALYTIC_GRAPH_ONLY: measure graph inference quality.
    No imputation judgment; no target comparison.
    Returns metrics dict for one (scenario, seed) instance.
    """
    metrics = model.graph_relation_head.edge_metrics(true_relations, sector_adj)
    return metrics


# ── Mode 2: TEMPORAL_RECONSTRUCTION ──────────────────────────────────────────

def evaluate_temporal_reconstruction(
    model: GatedGraphModel,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    device: str,
) -> dict:
    """
    TEMPORAL_RECONSTRUCTION: temporal backbone vs ffill and Ridge.
    No graph component used.
    """
    ev_mask = _eval_mask(obs_mask)
    y_temporal = model.predict_temporal_only(panel, obs_mask, device)
    y_ffill = _ffill(panel, obs_mask)
    y_ridge = _ridge_impute(panel, obs_mask)

    return {
        "mae_temporal": _mae(y_temporal, panel, ev_mask),
        "mae_ffill": _mae(y_ffill, panel, ev_mask),
        "mae_ridge": _mae(y_ridge, panel, ev_mask),
        "n_eval_cells": int(ev_mask.sum()),
    }


# ── Mode 3: GATED_GRAPH_ASSIST ────────────────────────────────────────────────

def evaluate_gated_graph_assist(
    model: GatedGraphModel,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    sector_adj: np.ndarray | None,
    device: str,
    seed: int = 1000,
) -> dict:
    """
    GATED_GRAPH_ASSIST: gated model vs temporal-only, always-on, permuted graph.
    Returns full comparison dict including gate statistics.
    """
    ev_mask = _eval_mask(obs_mask)
    y_temporal = model.predict_temporal_only(panel, obs_mask, device)
    y_gated, gate_vals = model.predict_gated(panel, obs_mask, device)
    y_always = model.predict_graph_always_on(panel, obs_mask, device)
    y_perm = _permuted_graph(model, panel, obs_mask, device, seed=seed)
    y_ffill = _ffill(panel, obs_mask)

    gate_stats = {
        "gate_mean": float(gate_vals.mean()),
        "gate_std": float(gate_vals.std()),
        "gate_max": float(gate_vals.max()),
        "gate_frac_above_half": float((gate_vals > 0.5).mean()),
    }
    analytic = model.graph_relation_head.edge_metrics(true_relations, sector_adj)

    return {
        "mae_gated": _mae(y_gated, panel, ev_mask),
        "mae_temporal": _mae(y_temporal, panel, ev_mask),
        "mae_graph_always": _mae(y_always, panel, ev_mask),
        "mae_permuted": _mae(y_perm, panel, ev_mask),
        "mae_ffill": _mae(y_ffill, panel, ev_mask),
        "n_eval_cells": int(ev_mask.sum()),
        **gate_stats,
        **analytic,
    }


# ── Fixture-level evaluation (D3-D6) ─────────────────────────────────────────

def evaluate_fixture_results(
    model: GatedGraphModel,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    sector_adj: np.ndarray | None,
    fixture_name: str,
    device: str,
) -> dict:
    """
    Per-fixture metrics for gates D3–D6.
    Returns fixture-specific dict keyed to gate checks.
    """
    result: dict = {}

    # D3: gate=0 identity
    with torch.no_grad():
        model.gate.net[-2].bias.fill_(-100.0)   # force gate ≈ 0
    y_force_closed, _ = model.predict_gated(panel, obs_mask, device)
    y_temporal = model.predict_temporal_only(panel, obs_mask, device)
    max_delta = float(np.abs(y_force_closed - y_temporal).max())
    result["gate_zero_identity_max_delta"] = max_delta
    with torch.no_grad():
        model.gate.net[-2].bias.fill_(-5.0)   # restore

    # Gate statistics after proper training
    gate_stats = model.predict_gate_stats(panel, obs_mask, device)
    result.update(gate_stats)

    # D6: presence logit asymmetry
    if fixture_name == "F6_asymmetric_directed" and true_relations:
        r = true_relations[0]  # the single directed edge
        s, t = r.source_sector, r.target_sector
        logits = model.graph_relation_head.presence_logit.detach().cpu().numpy()
        true_dir = float(logits[t, s])    # correct direction
        false_dir = float(logits[s, t])   # false reverse
        result["presence_logit_true_minus_false"] = true_dir - false_dir

    # F5: gate inside vs outside regime window
    if fixture_name == "F5_regime_window":
        _, gate_vals = model.predict_gated(panel, obs_mask, device)
        # years 5-10 are "window" (0-indexed)
        window_mask = np.zeros_like(obs_mask)
        window_mask[:, :, 5:11] = 1.0
        outside_mask = 1.0 - window_mask
        result["gate_inside_window_mean"] = float(gate_vals[:, :, 5:11].mean())
        result["gate_outside_window_mean"] = float(gate_vals[:, :, :5].mean() * 0.5 +
                                                    gate_vals[:, :, 11:].mean() * 0.5
                                                    if gate_vals.shape[2] > 11 else
                                                    gate_vals[:, :, :5].mean())

    return result
