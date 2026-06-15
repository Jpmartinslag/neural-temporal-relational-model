"""
ofat_runner.py — OFAT axes D, M, L, S for DEC-048 failure cause diagnostic.

Each axis isolates one factor:
  D: data quantity (10/25/50 datasets) and diversity (D0/D1/D2)
  M: architecture type (M0=ffill, M1=temporal-only, M2=contemp graph,
                        M3=lagged graph, M4=oracle lagged)
  L: training objective (L0=NLL, L1=masked NLL, L2=NLL+edge BCE, L3=multitask)
  S: shift intensity (S0 in-dist, S1 moderate, S2=novel_lag2, S3=novel_highvar)

Gradient diagnostics: norm of attention vs decoder vs territory params.

Key constraint: alpha=0.1 for auxiliary losses is FROZEN — do not change.
"""

from __future__ import annotations

import copy
import dataclasses
import time
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.data.synthetic.generate_herald_synthetic import (
    SyntheticConfig,
    generate_dataset,
    BENCHMARK_SCENARIOS,
)
from src.modeles.synthetic.herald_graph_imputer import (
    _prep_tensors,
    _apply_observed,
    impute_deterministic,
    train_herald_imputer,
    HERALDGraphImputer,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    train_herald_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.imputation_baselines import (
    ForwardFillImputer,
    _build_temporal_features,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
)
from src.modeles.synthetic.phase11_generalization.splits import (
    NOVEL_TEST_SCENARIOS,
)
from src.modeles.synthetic.phase11_generalization.trainer import (
    _compute_nll_loss,
    train_multi_dataset,
    checkpoint_hash,
)

# ── Constants ─────────────────────────────────────────────────────────────────

N_SECTORS = 9
N_TERRITORIES = 30
HIDDEN_DIM = 64
DROPOUT = 0.1

# D2 training seeds — disjoint from TEST_SEEDS [1000-5000] and benchmark seeds [42/123/456/789/1337]
TRAINING_SEEDS_D2 = list(range(200, 300))

# Test seeds used for zero-shot evaluation
PILOT_TEST_SEEDS = [1000, 2000, 3000]

# Alpha for auxiliary losses — FROZEN before execution
MULTITASK_ALPHA = 0.1


# ── Data generation helpers ───────────────────────────────────────────────────

def _build_d0_entries(n_datasets: int, mask_keys: list[str] = ("mcar_30", "block_30")) -> list[dict]:
    """D0: linear only — mirror of T1/T2 Phase 11 but fewer datasets."""
    base = BENCHMARK_SCENARIOS["linear"]
    entries = []
    seeds = list(range(10, 10 + n_datasets))
    for seed in seeds:
        cfg = dataclasses.replace(base, seed=seed)
        ds = generate_dataset(cfg)
        for mk in mask_keys:
            if mk in ds["masks"]:
                entries.append({
                    "panel": ds["panel"],
                    "mask": ds["masks"][mk],
                    "adj_s": ds["sector_adj"],
                    "adj_t": ds["territory_adj"],
                    "true_relations": ds["true_relations"],
                    "scenario": "linear",
                    "seed": seed,
                    "mask_key": mk,
                })
    return entries


def _build_d1_entries(
    n_datasets: int,
    mask_keys: list[str] = ("mcar_30", "block_30"),
    seeds_start: int = 200,
) -> list[dict]:
    """D1: frac_nonlinear ∈ [0.0, 0.50]."""
    entries = []
    seeds = list(range(seeds_start, seeds_start + n_datasets))
    rng = np.random.default_rng(777)
    for seed in seeds:
        frac_nl = float(rng.uniform(0.0, 0.50))
        cfg = SyntheticConfig(
            n_territories=30, n_sectors=9, n_years=20,
            seed=seed,
            n_true_relations=8,
            frac_nonlinear=frac_nl,
            frac_negative=0.4,
            noise_sigma_range=(0.08, 0.18),
            ar_coef_range=(0.3, 0.6),
            territory_propagation=0.15,
            territory_radius=0.35,
        )
        ds = generate_dataset(cfg)
        for mk in mask_keys:
            if mk in ds["masks"]:
                entries.append({
                    "panel": ds["panel"],
                    "mask": ds["masks"][mk],
                    "adj_s": ds["sector_adj"],
                    "adj_t": ds["territory_adj"],
                    "true_relations": ds["true_relations"],
                    "scenario": f"d1_frac_nl_{frac_nl:.2f}",
                    "seed": seed,
                    "mask_key": mk,
                })
    return entries


def _build_d2_entries(
    n_datasets: int,
    mask_keys: list[str] = ("mcar_30", "block_30"),
    seeds_start: int = 200,
) -> list[dict]:
    """
    D2: frac_nonlinear ∈ [0.0, 0.90].
    Does NOT copy exact novel_lag2/novel_highvar configs:
    - no forced_lag=2, no structural_break_year=8, no territory_radius=0.25/0.42
    """
    entries = []
    seeds = list(range(seeds_start, seeds_start + n_datasets))
    rng = np.random.default_rng(888)
    for seed in seeds:
        frac_nl = float(rng.uniform(0.0, 0.90))
        # Vary territory_radius within [0.28, 0.38] — avoids 0.25 (novel_lag2) and 0.42 (novel_highvar)
        t_radius = float(rng.uniform(0.28, 0.38))
        cfg = SyntheticConfig(
            n_territories=30, n_sectors=9, n_years=20,
            seed=seed,
            n_true_relations=8,
            frac_nonlinear=frac_nl,
            frac_negative=float(rng.uniform(0.3, 0.5)),
            noise_sigma_range=(0.08, 0.25),
            ar_coef_range=(0.25, 0.60),
            territory_propagation=float(rng.uniform(0.10, 0.22)),
            territory_radius=t_radius,
            forced_lag=None,  # mixed lag — NOT forced_lag=2
        )
        ds = generate_dataset(cfg)
        for mk in mask_keys:
            if mk in ds["masks"]:
                entries.append({
                    "panel": ds["panel"],
                    "mask": ds["masks"][mk],
                    "adj_s": ds["sector_adj"],
                    "adj_t": ds["territory_adj"],
                    "true_relations": ds["true_relations"],
                    "scenario": f"d2_frac_nl_{frac_nl:.2f}",
                    "seed": seed,
                    "mask_key": mk,
                })
    return entries


def _build_val_entries() -> list[dict]:
    """Validation on nonlinear_heavy seed=100 (Phase 11 val convention)."""
    base = BENCHMARK_SCENARIOS["nonlinear_heavy"]
    cfg = dataclasses.replace(base, seed=100)
    ds = generate_dataset(cfg)
    return [{
        "panel": ds["panel"],
        "mask": ds["masks"]["mcar_30"],
        "adj_s": ds["sector_adj"],
        "adj_t": ds["territory_adj"],
        "true_relations": ds["true_relations"],
        "scenario": "nonlinear_heavy",
        "seed": 100,
        "mask_key": "mcar_30",
    }]


def _eval_on_novel_lag2(
    model: HERALDGraphImputerLagged,
    test_seeds: list[int],
    mask_keys: list[str],
    device: str,
) -> list[dict]:
    """Zero-shot evaluation on novel_lag2 scenario."""
    base_cfg = NOVEL_TEST_SCENARIOS["novel_lag2"]
    records = []
    for seed in test_seeds:
        cfg = dataclasses.replace(base_cfg, seed=seed)
        ds = generate_dataset(cfg)
        for mk in mask_keys:
            if mk not in ds["masks"]:
                continue
            panel = ds["panel"]
            mask = ds["masks"][mk]
            adj_s = ds["sector_adj"]
            adj_t = ds["territory_adj"]
            imputed = impute_deterministic_lagged(model, panel, mask, adj_s, adj_t, device)
            m = compute_imputation_metrics(panel, imputed, mask)
            learned_attn = model.get_sector_attention()
            e = compute_edge_recovery_metrics(ds["true_relations"], N_SECTORS, learned_attn)
            records.append({
                "scenario": "novel_lag2",
                "seed": seed,
                "mask_key": mk,
                "mae": m.mae,
                "edge_auc": e.auc,
            })
    return records


# ── Axis D — Data quantity and diversity ─────────────────────────────────────

def run_axis_d(
    device: str = "cpu",
    seeds: list[int] | None = None,
    n_epochs: int = 30,
    patience: int = 5,
    n_datasets_list: list[int] | None = None,
) -> list[dict]:
    """
    OFAT over data quantity (10/25/50) and diversity (D0/D1/D2).
    For each (n_datasets, diversity) combination:
      - Train a fresh HERALDGraphImputerLagged
      - Evaluate zero-shot on novel_lag2
    Returns list of records.
    """
    if seeds is None:
        seeds = PILOT_TEST_SEEDS
    if n_datasets_list is None:
        n_datasets_list = [10, 25]
    val_entries = _build_val_entries()

    records = []
    for n_ds in n_datasets_list:
        for diversity in ["D0", "D1", "D2"]:
            t0 = time.time()
            if diversity == "D0":
                train_entries = _build_d0_entries(n_ds)
            elif diversity == "D1":
                train_entries = _build_d1_entries(n_ds)
            else:
                train_entries = _build_d2_entries(n_ds)

            model, history = train_multi_dataset(
                train_entries, val_entries,
                n_epochs=n_epochs, patience=patience, device=device, seed=7,
            )
            eval_recs = _eval_on_novel_lag2(model, seeds, ["mcar_30", "block_30"], device)
            elapsed = time.time() - t0

            for r in eval_recs:
                records.append({
                    "axis": "D",
                    "n_datasets": n_ds,
                    "diversity": diversity,
                    "scenario": r["scenario"],
                    "seed": r["seed"],
                    "mask_key": r["mask_key"],
                    "mae": r["mae"],
                    "edge_auc": r["edge_auc"],
                    "best_epoch": history["best_epoch"],
                    "val_loss": history["best_val_loss"],
                    "elapsed_s": elapsed,
                    "n_train_entries": len(train_entries),
                })
    return records


# ── Axis M — Architecture contribution ───────────────────────────────────────

def run_axis_m(
    device: str = "cpu",
    seeds: list[int] | None = None,
    n_epochs: int = 30,
    mask_key: str = "mcar_30",
) -> list[dict]:
    """
    OFAT over architecture type, local training on novel_lag2 (per seed).
    M0: ffill (control, no training)
    M1: temporal-only (lagged model, adj=0 sector, adj=0 territory)
    M2: contemporaneous graph (HERALDGraphImputer — Phase 9 arch)
    M3: lagged graph (HERALDGraphImputerLagged, standard)
    M4: oracle lagged (frozen attention from true_relations)

    All models trained locally on each test seed's dataset.
    """
    if seeds is None:
        seeds = PILOT_TEST_SEEDS

    base_cfg = NOVEL_TEST_SCENARIOS["novel_lag2"]
    records = []

    for seed in seeds:
        cfg = dataclasses.replace(base_cfg, seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        adj_s = ds["sector_adj"]
        adj_t = ds["territory_adj"]
        true_relations = ds["true_relations"]
        n_T, n_S, n_Y = panel.shape

        if mask_key not in ds["masks"]:
            continue
        mask = ds["masks"][mask_key]

        # M0: ffill
        ffill = ForwardFillImputer().fit(panel, mask)
        imputed_ffill = ffill.transform(panel, mask)
        m_ffill = compute_imputation_metrics(panel, imputed_ffill, mask)
        records.append({
            "axis": "M", "model_type": "M0_ffill", "seed": seed,
            "mask_key": mask_key, "mae": m_ffill.mae,
            "edge_auc": float("nan"), "local_epochs": 0,
        })

        # M1: temporal-only (adj_sector=0, adj_territory=0)
        zeros_s = np.zeros((n_S, n_S), dtype=np.float32)
        zeros_t = np.zeros((n_T, n_T), dtype=np.float32)
        m1 = HERALDGraphImputerLagged(n_S, n_T, HIDDEN_DIM, DROPOUT)
        train_herald_lagged(m1, panel, mask, zeros_s, zeros_t,
                            n_epochs=n_epochs, lr=1e-3, device=device)
        imputed_m1 = impute_deterministic_lagged(m1, panel, mask, zeros_s, zeros_t, device)
        met_m1 = compute_imputation_metrics(panel, imputed_m1, mask)
        records.append({
            "axis": "M", "model_type": "M1_temporal_only", "seed": seed,
            "mask_key": mask_key, "mae": met_m1.mae,
            "edge_auc": float("nan"), "local_epochs": n_epochs,
        })

        # M2: contemporaneous graph (HERALDGraphImputer)
        m2 = HERALDGraphImputer(n_S, n_T, hidden_dim=32, dropout=0.15)
        train_herald_imputer(m2, panel, mask, adj_s, adj_t,
                             n_epochs=n_epochs, lr=1e-3, device=device)
        imputed_m2 = impute_deterministic(m2, panel, mask, adj_s, adj_t, device)
        met_m2 = compute_imputation_metrics(panel, imputed_m2, mask)
        e_m2 = compute_edge_recovery_metrics(true_relations, n_S, m2.get_sector_attention())
        records.append({
            "axis": "M", "model_type": "M2_contemp_graph", "seed": seed,
            "mask_key": mask_key, "mae": met_m2.mae,
            "edge_auc": e_m2.auc, "local_epochs": n_epochs,
        })

        # M3: lagged graph
        m3 = HERALDGraphImputerLagged(n_S, n_T, HIDDEN_DIM, DROPOUT)
        train_herald_lagged(m3, panel, mask, adj_s, adj_t,
                            n_epochs=n_epochs, lr=1e-3, device=device)
        imputed_m3 = impute_deterministic_lagged(m3, panel, mask, adj_s, adj_t, device)
        met_m3 = compute_imputation_metrics(panel, imputed_m3, mask)
        e_m3 = compute_edge_recovery_metrics(true_relations, n_S, m3.get_sector_attention())
        records.append({
            "axis": "M", "model_type": "M3_lagged_graph", "seed": seed,
            "mask_key": mask_key, "mae": met_m3.mae,
            "edge_auc": e_m3.auc, "local_epochs": n_epochs,
        })

        # M4: oracle lagged
        m4 = HERALDGraphImputerLagged(n_S, n_T, HIDDEN_DIM, DROPOUT)
        build_directed_oracle_lagged(m4, true_relations, n_S)
        # Train only MLP (attention frozen by build_directed_oracle_lagged)
        train_herald_lagged(m4, panel, mask, adj_s, adj_t,
                            n_epochs=n_epochs, lr=1e-3, device=device)
        imputed_m4 = impute_deterministic_lagged(m4, panel, mask, adj_s, adj_t, device)
        met_m4 = compute_imputation_metrics(panel, imputed_m4, mask)
        e_m4 = compute_edge_recovery_metrics(true_relations, n_S, m4.get_sector_attention())
        records.append({
            "axis": "M", "model_type": "M4_oracle_lagged", "seed": seed,
            "mask_key": mask_key, "mae": met_m4.mae,
            "edge_auc": e_m4.auc, "local_epochs": n_epochs,
        })

        # Graph contribution: M3 with true adj vs M3 with zero adj
        imputed_m3_nograph = impute_deterministic_lagged(m3, panel, mask, zeros_s, zeros_t, device)
        graph_contribution = float(np.abs(imputed_m3 - imputed_m3_nograph).mean())
        # Patch last M3 record
        for rec in reversed(records):
            if rec["model_type"] == "M3_lagged_graph" and rec["seed"] == seed:
                rec["graph_contribution"] = graph_contribution
                break

    return records


# ── Multitask loss (L2/L3) ───────────────────────────────────────────────────

def compute_multitask_loss(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    true_relations: list,
    n_sectors: int,
    device: str,
    alpha: float = MULTITASK_ALPHA,
    include_sign: bool = False,
    include_lag: bool = False,
) -> torch.Tensor:
    """
    NLL + alpha * edge_BCE (L2).
    With include_sign=True and include_lag=True: NLL + edge + sign + lag (L3).

    alpha=0.1 is FROZEN before execution — do not change.

    Edge target: edge_target[target_sector, source_sector] = 1 for lag-1 true edges.
    Uses model.log_sect_attn_lag1 (pre-softmax) as logit for binary CE.
    """
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    ).to(device)

    out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    log_sigma = out[..., 1]
    sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
    nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
    nll_loss = (nll * mask_t).sum() / mask_t.sum().clamp(min=1)

    # Build edge binary target
    edge_target = torch.zeros(n_sectors, n_sectors, device=device)
    sign_target = torch.full((n_sectors, n_sectors), 0.5, device=device)  # neutral default
    lag2_target = torch.zeros(n_sectors, n_sectors, device=device)  # 1 if lag-2

    for r in true_relations:
        s, t_ = r.source_sector, r.target_sector
        if s < n_sectors and t_ < n_sectors:
            if r.lag == 1:
                edge_target[t_, s] = 1.0
                sign_target[t_, s] = 1.0 if r.weight > 0 else 0.0
            elif r.lag == 2:
                lag2_target[t_, s] = 1.0

    # Off-diagonal mask
    off_diag = ~torch.eye(n_sectors, dtype=torch.bool, device=device)
    attn_lag1_flat = model.log_sect_attn_lag1[off_diag]
    edge_target_flat = edge_target[off_diag]
    edge_loss = F.binary_cross_entropy_with_logits(attn_lag1_flat, edge_target_flat)

    total_loss = nll_loss + alpha * edge_loss

    if include_sign:
        # Sign: on true lag-1 edges only
        lag1_edge_mask = edge_target.bool() & off_diag
        if lag1_edge_mask.sum() > 0:
            attn_sign_flat = model.log_sect_attn_lag1[lag1_edge_mask]
            sign_target_flat = sign_target[lag1_edge_mask]
            sign_loss = F.binary_cross_entropy_with_logits(attn_sign_flat, sign_target_flat)
            total_loss = total_loss + alpha * sign_loss

    if include_lag:
        # Lag: predict which lag (1 vs 2) using max of lag1 vs lag2 attention logits
        attn_lag2 = model.log_sect_attn_lag2
        lag2_target_flat = lag2_target[off_diag]
        # Score: lag2 dominates if log_sect_attn_lag2 > log_sect_attn_lag1
        lag_score = (attn_lag2 - model.log_sect_attn_lag1)[off_diag]
        lag_loss = F.binary_cross_entropy_with_logits(lag_score, lag2_target_flat)
        total_loss = total_loss + alpha * lag_loss

    return total_loss


def _train_with_objective(
    train_entries: list[dict],
    val_entries: list[dict],
    objective: str,  # "L0", "L1", "L2", "L3"
    n_sectors: int,
    n_epochs: int = 30,
    patience: int = 5,
    lr: float = 1e-3,
    device: str = "cpu",
) -> tuple[HERALDGraphImputerLagged, dict]:
    """
    Train with specified objective.
    L0: standard NLL on all observed
    L1: NLL on MCAR-40-60% randomly masked cells (masked reconstruction)
    L2: NLL + edge BCE (alpha=0.1 frozen)
    L3: NLL + edge BCE + sign BCE + lag BCE (alpha=0.1 frozen for each term)
    """
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    rng = np.random.default_rng(42)

    best_val = float("inf")
    best_state = None
    no_improve = 0
    history = {"train_losses": [], "val_losses": [], "best_epoch": 0}

    for epoch in range(n_epochs):
        model.train()
        order = rng.permutation(len(train_entries))
        ep_loss = 0.0

        for idx in order:
            e = train_entries[int(idx)]
            opt.zero_grad()

            if objective == "L0":
                loss = _compute_nll_loss(model, e["panel"], e["mask"],
                                         e["adj_s"], e["adj_t"], device)
            elif objective == "L1":
                # Masked reconstruction: apply additional random MCAR 40-60% on observed cells
                extra_rate = float(rng.uniform(0.40, 0.60))
                obs_idx = np.argwhere(e["mask"] == 1)
                n_extra = max(0, round(len(obs_idx) * extra_rate))
                extra_hidden = rng.choice(len(obs_idx), size=n_extra, replace=False)
                masked_mask = e["mask"].copy()
                for i in extra_hidden:
                    t_, s_, y_ = obs_idx[i]
                    masked_mask[t_, s_, y_] = 0
                loss = _compute_nll_loss(model, e["panel"], masked_mask,
                                         e["adj_s"], e["adj_t"], device)
            elif objective == "L2":
                loss = compute_multitask_loss(
                    model, e["panel"], e["mask"], e["adj_s"], e["adj_t"],
                    e["true_relations"], n_sectors, device,
                    alpha=MULTITASK_ALPHA, include_sign=False, include_lag=False,
                )
            elif objective == "L3":
                loss = compute_multitask_loss(
                    model, e["panel"], e["mask"], e["adj_s"], e["adj_t"],
                    e["true_relations"], n_sectors, device,
                    alpha=MULTITASK_ALPHA, include_sign=True, include_lag=True,
                )
            else:
                raise ValueError(f"Unknown objective: {objective}")

            loss.backward()
            opt.step()
            ep_loss += float(loss)

        history["train_losses"].append(ep_loss / max(len(train_entries), 1))

        # Val
        model.eval()
        with torch.no_grad():
            vl = [
                float(_compute_nll_loss(model, v["panel"], v["mask"],
                                        v["adj_s"], v["adj_t"], device))
                for v in val_entries
            ]
        val_loss = float(np.mean(vl))
        history["val_losses"].append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = copy.deepcopy(model.state_dict())
            no_improve = 0
            history["best_epoch"] = epoch
        else:
            no_improve += 1
        if no_improve >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    history["best_val_loss"] = float(best_val)
    history["objective"] = objective
    return model, history


# ── Axis L — Training objective ───────────────────────────────────────────────

def run_axis_l(
    best_data_config: dict | None = None,
    device: str = "cpu",
    seeds: list[int] | None = None,
    n_epochs: int = 30,
    patience: int = 5,
) -> list[dict]:
    """
    OFAT over training objective (L0..L3).
    Uses best data config from Axis D if available, else defaults to D2/25.
    """
    if seeds is None:
        seeds = PILOT_TEST_SEEDS
    val_entries = _build_val_entries()

    # Determine data config
    if best_data_config is not None:
        n_ds = best_data_config.get("n_datasets", 25)
        diversity = best_data_config.get("diversity", "D2")
    else:
        n_ds = 25
        diversity = "D2"

    if diversity == "D0":
        train_entries = _build_d0_entries(n_ds)
    elif diversity == "D1":
        train_entries = _build_d1_entries(n_ds)
    else:
        train_entries = _build_d2_entries(n_ds)

    records = []
    for objective in ["L0", "L1", "L2", "L3"]:
        t0 = time.time()
        model, history = _train_with_objective(
            train_entries, val_entries, objective, N_SECTORS,
            n_epochs=n_epochs, patience=patience, device=device,
        )
        eval_recs = _eval_on_novel_lag2(model, seeds, ["mcar_30", "block_30"], device)
        elapsed = time.time() - t0
        for r in eval_recs:
            records.append({
                "axis": "L",
                "objective": objective,
                "n_datasets": n_ds,
                "diversity": diversity,
                "scenario": r["scenario"],
                "seed": r["seed"],
                "mask_key": r["mask_key"],
                "mae": r["mae"],
                "edge_auc": r["edge_auc"],
                "best_epoch": history["best_epoch"],
                "val_loss": history["best_val_loss"],
                "elapsed_s": elapsed,
            })
    return records


# ── Axis S — Shift intensity ──────────────────────────────────────────────────

def run_axis_s(
    base_model: HERALDGraphImputerLagged | None = None,
    device: str = "cpu",
    test_seeds: list[int] | None = None,
) -> list[dict]:
    """
    OFAT over shift intensity. Uses provided T2 model (or fresh model) zero-shot.
    S0: in-distribution (linear, similar to training)
    S1: moderate shift (frac_nonlinear=0.50)
    S2: novel_lag2 (frac_nonlinear=0.85, forced_lag=2)
    S3: novel_highvar (frac_nonlinear=0.90, structural_break)

    If no model provided, builds a fresh D2/25 trained model.
    """
    if test_seeds is None:
        test_seeds = [1000, 2000, 3000]

    # Shift level configs
    s0_cfg = SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0, n_true_relations=8,
        frac_nonlinear=0.0, frac_negative=0.4,
        noise_sigma_range=(0.08, 0.18),
        ar_coef_range=(0.3, 0.6),
        territory_propagation=0.15, territory_radius=0.35,
    )
    s1_cfg = SyntheticConfig(
        n_territories=30, n_sectors=9, n_years=20,
        seed=0, n_true_relations=8,
        frac_nonlinear=0.50, frac_negative=0.4,
        noise_sigma_range=(0.10, 0.22),
        ar_coef_range=(0.28, 0.58),
        territory_propagation=0.18, territory_radius=0.30,
    )
    s2_cfg = NOVEL_TEST_SCENARIOS["novel_lag2"]
    s3_cfg = NOVEL_TEST_SCENARIOS["novel_highvar"]

    shift_configs = {
        "S0_indist": s0_cfg,
        "S1_moderate": s1_cfg,
        "S2_novel_lag2": s2_cfg,
        "S3_novel_highvar": s3_cfg,
    }

    # If no model, train one
    if base_model is None:
        train_entries = _build_d2_entries(25)
        val_entries = _build_val_entries()
        base_model, _ = train_multi_dataset(
            train_entries, val_entries, n_epochs=30, patience=5, device=device, seed=7,
        )

    records = []
    for shift_name, base_cfg in shift_configs.items():
        # Compute ffill baseline for ratio
        ffill_maes = []
        model_maes = []
        edge_aucs = []

        for seed in test_seeds:
            cfg = dataclasses.replace(base_cfg, seed=seed)
            ds = generate_dataset(cfg)
            panel = ds["panel"]
            adj_s = ds["sector_adj"]
            adj_t = ds["territory_adj"]
            true_relations = ds["true_relations"]
            mk = "mcar_30"
            if mk not in ds["masks"]:
                continue
            mask = ds["masks"][mk]

            # ffill
            ff = ForwardFillImputer().fit(panel, mask)
            imp_ff = ff.transform(panel, mask)
            m_ff = compute_imputation_metrics(panel, imp_ff, mask)
            ffill_maes.append(m_ff.mae)

            # model (zero-shot)
            imp_model = impute_deterministic_lagged(base_model, panel, mask, adj_s, adj_t, device)
            m_model = compute_imputation_metrics(panel, imp_model, mask)
            model_maes.append(m_model.mae)

            e = compute_edge_recovery_metrics(true_relations, N_SECTORS, base_model.get_sector_attention())
            edge_aucs.append(e.auc)

        for i, seed in enumerate(test_seeds):
            if i >= len(model_maes):
                break
            records.append({
                "axis": "S",
                "shift_level": shift_name,
                "seed": seed,
                "mask_key": "mcar_30",
                "mae": model_maes[i],
                "ffill_mae": ffill_maes[i],
                "mae_ratio": model_maes[i] / max(ffill_maes[i], 1e-8),
                "edge_auc": edge_aucs[i],
            })

    return records


# ── Gradient diagnostics ──────────────────────────────────────────────────────

def run_gradient_diagnostics(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str = "cpu",
    true_relations: list | None = None,
) -> dict:
    """
    Compute gradient norms of attention vs decoder vs territory params.
    Also measures graph contribution (MAE with adj vs without).

    Returns dict with gradient norms and graph contribution metric.
    """
    model = model.to(device)
    model.train()

    # Zero all grads
    for p in model.parameters():
        if p.grad is not None:
            p.grad.zero_()

    # Forward + backward with NLL
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    ).to(device)

    out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred_mean = out[..., 0]
    log_sigma = out[..., 1]
    sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
    nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
    loss = (nll * mask_t).sum() / mask_t.sum().clamp(min=1)
    loss.backward()

    def _norm(param: nn.Parameter) -> float:
        if param.grad is None:
            return 0.0
        return float(param.grad.norm().item())

    grad_lag1 = _norm(model.log_sect_attn_lag1)
    grad_lag2 = _norm(model.log_sect_attn_lag2)
    grad_terr = _norm(model.log_terr_attn)
    grad_attn = grad_lag1 + grad_lag2

    # MLP decoder gradient
    grad_mlp = 0.0
    for p in model.net.parameters():
        grad_mlp += _norm(p)

    # Graph contribution: MAE(with_adj) vs MAE(no_adj)
    model.eval()
    n_T, n_S, n_Y = panel.shape
    zeros_s = np.zeros((n_S, n_S), dtype=np.float32)
    zeros_t = np.zeros((n_T, n_T), dtype=np.float32)

    with torch.no_grad():
        imp_with = impute_deterministic_lagged(model, panel, mask, adj_s, adj_t, device)
        imp_without = impute_deterministic_lagged(model, panel, mask, zeros_s, zeros_t, device)

    hidden = mask == 0
    graph_contribution_mae = float(np.abs(imp_with[hidden] - imp_without[hidden]).mean()) if hidden.sum() > 0 else 0.0

    result = {
        "grad_norm_lag1_attn": grad_lag1,
        "grad_norm_lag2_attn": grad_lag2,
        "grad_norm_attn_total": grad_attn,
        "grad_norm_terr_attn": grad_terr,
        "grad_norm_mlp": grad_mlp,
        "graph_contribution_mae": graph_contribution_mae,
        "attn_grad_near_zero": grad_attn < 1e-5,
    }

    # If multitask loss: check grad norms after L2 loss
    if true_relations is not None and len(true_relations) > 0:
        for p in model.parameters():
            if p.grad is not None:
                p.grad.zero_()
        model.train()
        n_s = panel.shape[1]
        loss_l2 = compute_multitask_loss(
            model, panel, mask, adj_s, adj_t,
            true_relations, n_s, device,
            alpha=MULTITASK_ALPHA, include_sign=False, include_lag=False,
        )
        loss_l2.backward()
        result["grad_norm_lag1_attn_l2"] = _norm(model.log_sect_attn_lag1)
        result["grad_norm_lag2_attn_l2"] = _norm(model.log_sect_attn_lag2)
        result["l2_attn_grad_near_zero"] = (
            result["grad_norm_lag1_attn_l2"] + result["grad_norm_lag2_attn_l2"]
        ) < 1e-5

    return result
