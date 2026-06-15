"""
gate_variants.py — Ablation variants for DEC-054 oracle utility gate experiment.

Variants:
    G0 — reference indirect (no utility supervision, weak L1)
    G1 — supervised utility (lambda_utility=0.1, small L1)
    G2 — supervised utility, no L1 (lambda_utility=1.0, lambda_gate=0.0)
    G3 — oracle gate (analytical, no training)
    T0 — temporal-only baseline
    A0 — graph always-on (gate=1)
    P0 — graph permuted (gate from trained model, permuted attention)

FROZEN before results (DEC-054).
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass

import numpy as np
import torch
import torch.optim as optim

from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.phase16_decoupled.gated_model import GatedGraphModel
from src.modeles.synthetic.phase16_decoupled.graph_relation_head import GraphRelationHead
from src.modeles.synthetic.phase16_decoupled.utility_target import (
    LAMBDA_RELATION,
    compute_oracle_correction,
    make_utility_target,
    pos_weight_for_utility,
)

# ── Frozen variant table ──────────────────────────────────────────────────────
VARIANTS_ABLATION = [
    ("G0", 0.0, 0.01),   # reference indirect: no utility supervision, weak L1
    ("G1", 0.1, 0.001),  # supervised: utility loss, tiny L1
    ("G2", 1.0, 0.0),    # supervised no L1: strong utility, zero L1
]
# G3 = oracle gate (computed analytically, no training)
# T0 = temporal-only baseline (backbone, no expert)
# A0 = graph always-on (gate=1)
# P0 = graph permuted (gate from trained model, permuted attention)


@dataclass
class GateConfig:
    name: str
    lambda_utility: float
    lambda_gate: float


def variant_loss(
    y_pred: torch.Tensor,
    y_temporal: torch.Tensor,
    gate: torch.Tensor,
    true_np: np.ndarray,
    loss_mask_t: torch.Tensor,
    model: GatedGraphModel,
    true_relations: list,
    device: str,
    utility_target_t: torch.Tensor | None,   # precomputed, None if lambda_utility==0
    config: GateConfig,
) -> tuple[torch.Tensor, dict]:
    """
    Compute total loss for a given gate variant.

    Components:
        L_recon    = MSE on loss_mask cells
        L_relation = sum of presence + sign + lag losses (weighted by LAMBDA_RELATION)
        L_utility  = weighted BCE(gate, utility_target) on missing cells (if supervised)
        L_gate     = mean(gate) regularisation toward closed

    Returns (total_loss, component_dict).
    """
    true_t = torch.from_numpy(
        np.nan_to_num(true_np, nan=0.0).astype(np.float32)
    ).to(device)

    # L_recon: MSE on missing cells
    n_cells = loss_mask_t.sum().clamp(min=1)
    l_recon = ((y_pred - true_t) ** 2 * loss_mask_t).sum() / n_cells

    # L_relation: graph head losses (presence + sign + lag)
    graph_losses = model.graph_relation_head.all_losses(true_relations, device)
    l_relation_sum = sum(graph_losses.values())

    # L_utility: supervised BCE with pos_weight if applicable
    l_utility = torch.tensor(0.0, device=device)
    if config.lambda_utility > 0.0 and utility_target_t is not None:
        eps = 1e-7
        util_t = utility_target_t.to(device)
        gate_clamped = gate.clamp(eps, 1.0 - eps)

        # Compute pos_weight from numpy arrays (precomputed)
        loss_mask_np = loss_mask_t.detach().cpu().numpy()
        util_np = util_t.detach().cpu().numpy()
        pw_val = pos_weight_for_utility(util_np, loss_mask_np)
        pw = torch.tensor(pw_val, dtype=torch.float32, device=device)

        # Weighted BCE manually, applied only on loss_mask cells
        bce_per_cell = -(
            pw * util_t * torch.log(gate_clamped + eps)
            + (1.0 - util_t) * torch.log(1.0 - gate_clamped + eps)
        )
        l_utility = (bce_per_cell * loss_mask_t).sum() / n_cells

    # L_gate: L1 toward closed gate
    l_gate = gate.mean()

    total = (
        l_recon
        + LAMBDA_RELATION * l_relation_sum
        + config.lambda_utility * l_utility
        + config.lambda_gate * l_gate
    )

    components = {
        "l_recon": float(l_recon),
        "l_relation": float(l_relation_sum),
        "l_utility": float(l_utility),
        "l_gate": float(l_gate),
        "total": float(total),
    }
    return total, components


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def train_gate_variant(
    config: GateConfig,
    backbone: HERALDGraphImputerLagged,
    n_sectors: int,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    device: str,
    seed: int,
    max_epochs: int = 75,
    patience: int = 10,
    lr: float = 1e-3,
) -> tuple:
    """
    Train a GatedGraphModel under the given GateConfig.

    Steps:
    1. Create fresh GatedGraphModel (backbone frozen)
    2. Precompute utility_target if config.lambda_utility > 0
    3. Training loop with variant_loss, Adam, grad clip=1.0
    4. Early stopping on patience

    Returns (trained_model, history, utility_stats)
        utility_stats: dict with prevalence etc., or None if not supervised
    """
    _set_seed(seed)

    model = GatedGraphModel(backbone, n_sectors).to(device)
    model.train()

    params = (
        list(model.graph_relation_head.parameters())
        + list(model.graph_expert.parameters())
        + list(model.gate.parameters())
    )
    opt = optim.Adam(params, lr=lr)
    loss_mask_np = (obs_mask == 0).astype(np.float32)
    loss_mask_t = torch.from_numpy(loss_mask_np).to(device)

    # Precompute utility target (only if supervised)
    utility_target_t: torch.Tensor | None = None
    utility_stats: dict | None = None

    if config.lambda_utility > 0.0:
        # Get temporal prediction for oracle computation
        with torch.no_grad():
            y_temporal_np = model.predict_temporal_only(panel, obs_mask, device)
        oracle_corr = compute_oracle_correction(panel, obs_mask, true_relations)
        y_oracle_np = y_temporal_np + oracle_corr
        util_np, prevalence, stats = make_utility_target(
            panel, obs_mask, y_temporal_np, y_oracle_np, loss_mask_np
        )
        utility_target_t = torch.from_numpy(util_np).to(device)
        utility_stats = {"prevalence": prevalence, **stats}

    history = []
    best_loss = math.inf
    patience_count = 0

    for epoch in range(max_epochs):
        model.train()
        opt.zero_grad()

        out = model.forward_tensors(panel, obs_mask, device)
        total_loss, components = variant_loss(
            out["y_pred"], out["y_temporal"], out["gate"],
            panel, loss_mask_t,
            model, true_relations, device,
            utility_target_t=utility_target_t,
            config=config,
        )
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()

        epoch_loss = components["total"]
        history.append({"epoch": epoch, **components})

        if epoch_loss < best_loss - 1e-5:
            best_loss = epoch_loss
            patience_count = 0
        else:
            patience_count += 1
        if patience_count >= patience:
            break

    return model, history, utility_stats


def eval_all_variants(
    trained_models: dict,          # {name: GatedGraphModel or None}
    backbone: HERALDGraphImputerLagged,
    n_sectors: int,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    device: str,
    seed_for_permutation: int = 0,
) -> dict:
    """
    Evaluate all variants on the given (panel, obs_mask) dataset.

    Variants evaluated:
        G0, G1, G2 — from trained_models
        G3 — oracle gate (y_temporal + oracle_correction, no expert)
        T0 — temporal-only (backbone)
        A0 — graph always-on (gate=1)
        P0 — permuted attention (null control)

    Metrics per variant:
        mae_temporal, mae_gated, gate_mean, gate_mean_useful, gate_mean_useless
        auroc, auprc  (utility discrimination on OOS missing cells)
        max_regression  (max(mae_gated - mae_temporal, 0) / mae_temporal)

    Returns dict of {variant_name: metrics_dict}.
    """
    from sklearn.metrics import average_precision_score, roc_auc_score

    loss_mask_np = (obs_mask == 0).astype(np.float32)
    n_total_missing = int(loss_mask_np.sum())

    # ── Temporal reference ────────────────────────────────────────────────────
    # Use G1 model if available, else G0; for T0 we just need any backbone wrapper
    ref_model_name = next(
        (k for k in ["G1", "G0", "G2"] if k in trained_models and trained_models[k] is not None),
        None,
    )
    if ref_model_name is not None:
        ref_model = trained_models[ref_model_name]
    else:
        # Fallback: create a bare model just for temporal prediction
        ref_model = GatedGraphModel(backbone, n_sectors).to(device)

    with torch.no_grad():
        y_temporal_np = ref_model.predict_temporal_only(panel, obs_mask, device)

    # Oracle correction (for G3 and utility target)
    oracle_corr = compute_oracle_correction(panel, obs_mask, true_relations)
    y_oracle_np = y_temporal_np + oracle_corr

    # Utility target for AUROC computation (on OOS missing cells)
    util_np, prevalence, _stats = make_utility_target(
        panel, obs_mask, y_temporal_np, y_oracle_np, loss_mask_np
    )

    def _mae_missing(pred: np.ndarray) -> float:
        if n_total_missing == 0:
            return float("nan")
        return float(np.abs(pred - panel)[loss_mask_np > 0.5].mean())

    def _gate_stats(gate_vals: np.ndarray) -> dict:
        """Compute gate mean at useful / useless cells."""
        out: dict = {"gate_mean": float(gate_vals.mean())}
        useful_mask = (util_np > 0.5) & (loss_mask_np > 0.5)
        useless_mask = (util_np < 0.5) & (loss_mask_np > 0.5)
        out["gate_mean_useful"] = (
            float(gate_vals[useful_mask].mean()) if useful_mask.any() else float("nan")
        )
        out["gate_mean_useless"] = (
            float(gate_vals[useless_mask].mean()) if useless_mask.any() else float("nan")
        )
        return out

    def _auroc_auprc(gate_vals: np.ndarray) -> dict:
        """AUROC / AUPRC of gate discriminating useful vs useless cells."""
        missing = loss_mask_np > 0.5
        if not missing.any():
            return {"auroc": float("nan"), "auprc": float("nan")}
        g_at_miss = gate_vals[missing]
        u_at_miss = util_np[missing]
        n_classes = len(np.unique(u_at_miss))
        if n_classes < 2:
            return {"auroc": float("nan"), "auprc": float("nan")}
        try:
            auroc = float(roc_auc_score(u_at_miss, g_at_miss))
            auprc = float(average_precision_score(u_at_miss, g_at_miss))
        except Exception:
            auroc, auprc = float("nan"), float("nan")
        return {"auroc": auroc, "auprc": auprc}

    def _regression(mae_gated: float, mae_temp: float) -> float:
        if math.isnan(mae_gated) or math.isnan(mae_temp) or mae_temp < 1e-10:
            return float("nan")
        return max(mae_gated - mae_temp, 0.0) / mae_temp

    results: dict = {}
    mae_temporal = _mae_missing(y_temporal_np)

    # ── G0, G1, G2 ────────────────────────────────────────────────────────────
    for name, model in trained_models.items():
        if model is None:
            continue
        with torch.no_grad():
            y_gated_np, gate_np = model.predict_gated(panel, obs_mask, device)
        mae_gated = _mae_missing(y_gated_np)
        results[name] = {
            "mae_temporal": mae_temporal,
            "mae_gated": mae_gated,
            "max_regression": _regression(mae_gated, mae_temporal),
            **_gate_stats(gate_np),
            **_auroc_auprc(gate_np),
        }

    # ── G3: oracle gate (y_temporal + oracle_correction) ─────────────────────
    mae_g3 = _mae_missing(y_oracle_np)
    # Oracle "gate" = utility target (binary indicator for useful cells)
    results["G3"] = {
        "mae_temporal": mae_temporal,
        "mae_gated": mae_g3,
        "max_regression": _regression(mae_g3, mae_temporal),
        **_gate_stats(util_np),
        "auroc": 1.0,   # oracle perfectly discriminates by definition
        "auprc": float(prevalence) if prevalence > 0 else float("nan"),
    }

    # ── T0: temporal-only baseline ────────────────────────────────────────────
    results["T0"] = {
        "mae_temporal": mae_temporal,
        "mae_gated": mae_temporal,  # same (no graph)
        "gate_mean": 0.0,
        "gate_mean_useful": 0.0,
        "gate_mean_useless": 0.0,
        "max_regression": 0.0,
        "auroc": float("nan"),
        "auprc": float("nan"),
    }

    # ── A0: graph always-on ───────────────────────────────────────────────────
    if ref_model_name is not None:
        model_for_always = trained_models[ref_model_name]
        with torch.no_grad():
            y_always_np = model_for_always.predict_graph_always_on(panel, obs_mask, device)
        mae_always = _mae_missing(y_always_np)
        # Gate is 1 everywhere for always-on
        ones_gate = np.ones_like(util_np)
        results["A0"] = {
            "mae_temporal": mae_temporal,
            "mae_gated": mae_always,
            "max_regression": _regression(mae_always, mae_temporal),
            **_gate_stats(ones_gate),
            **_auroc_auprc(ones_gate),
        }

    # ── P0: permuted attention (null control) ─────────────────────────────────
    if ref_model_name is not None:
        model_for_perm = trained_models[ref_model_name]
        rng_perm = np.random.default_rng(seed_for_permutation)
        perm = rng_perm.permutation(model_for_perm.graph_relation_head.n_S)
        orig_logits = model_for_perm.graph_relation_head.presence_logit.data.clone()
        with torch.no_grad():
            model_for_perm.graph_relation_head.presence_logit.data = (
                orig_logits[perm, :][:, perm]
            )
            y_perm_np, gate_perm_np = model_for_perm.predict_gated(panel, obs_mask, device)
            model_for_perm.graph_relation_head.presence_logit.data = orig_logits
        mae_perm = _mae_missing(y_perm_np)
        results["P0"] = {
            "mae_temporal": mae_temporal,
            "mae_gated": mae_perm,
            "max_regression": _regression(mae_perm, mae_temporal),
            **_gate_stats(gate_perm_np),
            **_auroc_auprc(gate_perm_np),
        }

    # Add prevalence to all variants (shared context)
    for v in results.values():
        v["utility_prevalence"] = prevalence

    return results
