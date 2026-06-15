"""
evaluator_v2.py — Zero-shot and few-shot evaluation for DEC-051.

Evaluation protocol:
  - Zero-shot: pass pretrained checkpoint to scenario, no parameter update.
  - Few-shot (top-2 val-selected only): decoder-only fine-tune on support set.
  - Scenarios: novel_lag2, novel_highvar.
  - Masks: mcar_30, block_30.
  - Seeds: 5 seeds per variant/scenario/mask (FROZEN before results).
  - Few-shot k_frac: 5% and 10% of observed cells as support.

Selection rule: top-2 variants chosen by val_loss (nonlinear_heavy, mcar_30).
Test is NEVER touched for selection. No threshold selection on test.

Gate metrics returned:
  MAE, RMSE, MAE_ffill, MAE_nogr, edge_auc, edge_auprc,
  sign_acc, lag_acc, log_sigma_{min,mean,max}, val_loss.
"""

from __future__ import annotations

import copy
import dataclasses
from pathlib import Path
from typing import NamedTuple

import numpy as np
import torch

from src.data.synthetic.generate_herald_synthetic import generate_dataset
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS
from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.imputation_baselines import (
    _build_temporal_features,
    ForwardFillImputer,
)
from src.modeles.synthetic.phase11_generalization.trainer import (
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase15_stable_objective.loss_functions import (
    masked_nll_clamped,
    log_sigma_stats,
)
from src.modeles.synthetic.phase15_stable_objective.graph_heads import GraphAuxHeads

# ── Frozen evaluation constants ────────────────────────────────────────────────
EVAL_SCENARIOS: list[str] = ["novel_lag2", "novel_highvar"]
EVAL_MASKS: list[str] = ["mcar_30", "block_30"]
EVAL_SEEDS: list[int] = [1000, 2000, 3000, 4000, 5000]

FEWSHOT_K_FRACS: list[float] = [0.05, 0.10]
FEWSHOT_SUPPORT_SEED: int = 42
FEWSHOT_N_ADAPT_EPOCHS: int = 50
FEWSHOT_PATIENCE: int = 10


class ZeroShotResult(NamedTuple):
    variant: str
    epoch_budget: int
    scenario: str
    mask_key: str
    seed: int
    mae: float
    rmse: float
    mae_ffill: float
    mae_nogr: float
    log_sigma_min: float
    log_sigma_mean: float
    log_sigma_max: float
    edge_auc: float
    edge_auprc: float
    sign_acc: float
    lag_acc: float


class FewShotResult(NamedTuple):
    variant: str
    epoch_budget: int
    scenario: str
    mask_key: str
    seed: int
    k_frac: float
    mae_zeroshot: float
    mae_fewshot: float
    mae_ffill: float
    mae_reduction_pct: float  # (mae_zeroshot - mae_fewshot) / mae_zeroshot * 100


def _load_model(checkpoint_path: str | Path, device: str) -> HERALDGraphImputerLagged:
    model = HERALDGraphImputerLagged(
        N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=DROPOUT
    ).to(device)
    state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state)
    return model


def _load_heads(heads_path: str | Path | None, device: str) -> GraphAuxHeads | None:
    if heads_path is None or not Path(heads_path).exists():
        return None
    heads = GraphAuxHeads(N_SECTORS).to(device)
    heads.load_state_dict(torch.load(heads_path, map_location=device))
    return heads


def _predict(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (pred_mean, pred_log_sigma) arrays, shape (n_T, n_S, n_Y)."""
    model.eval()
    with torch.no_grad():
        panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, device)
        temp_feats_t = torch.from_numpy(
            _build_temporal_features(panel, mask).astype(np.float32)
        ).to(device)
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
    pred = out.cpu().numpy()
    return pred[..., 0], pred[..., 1]


def _compute_mae_rmse(
    pred_mean: np.ndarray,
    panel: np.ndarray,
    eval_mask: np.ndarray,
) -> tuple[float, float]:
    """MAE and RMSE on eval_mask cells vs panel ground truth."""
    cells = eval_mask == 1
    if cells.sum() == 0:
        return float("nan"), float("nan")
    err = np.abs(pred_mean[cells] - panel[cells])
    mae = float(err.mean())
    rmse = float(np.sqrt((err**2).mean()))
    return mae, rmse


def _ffill_baseline(
    panel: np.ndarray, mask: np.ndarray, eval_mask: np.ndarray
) -> float:
    pred = ForwardFillImputer().fit(panel, mask).transform(panel, mask)
    cells = eval_mask == 1
    if cells.sum() == 0:
        return float("nan")
    return float(np.abs(pred[cells] - panel[cells]).mean())


def _nogr_baseline(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    eval_mask: np.ndarray,
    device: str,
) -> float:
    """No-graph: HERALD model with zeroed adjacency matrices."""
    zeros_s = np.zeros_like(adj_s)
    zeros_t = np.zeros_like(adj_t)
    pred_mean, _ = _predict(model, panel, mask, zeros_s, zeros_t, device)
    cells = eval_mask == 1
    if cells.sum() == 0:
        return float("nan")
    return float(np.abs(pred_mean[cells] - panel[cells]).mean())


def evaluate_zero_shot(
    checkpoint_path: str | Path,
    heads_path: str | Path | None,
    variant: str,
    epoch_budget: int,
    device: str = "cpu",
) -> list[ZeroShotResult]:
    """
    Evaluate one checkpoint on all EVAL_SCENARIOS × EVAL_MASKS × EVAL_SEEDS.
    Returns list of ZeroShotResult (one per (scenario, mask, seed)).
    """
    model = _load_model(checkpoint_path, device)
    heads = _load_heads(heads_path, device)

    results = []
    for scenario in EVAL_SCENARIOS:
        base_cfg = NOVEL_TEST_SCENARIOS[scenario]
        for seed in EVAL_SEEDS:
            cfg = dataclasses.replace(base_cfg, seed=seed)
            ds = generate_dataset(cfg)
            panel = ds["panel"]
            adj_s = ds["sector_adj"]
            adj_t = ds["territory_adj"]
            true_relations = ds["true_relations"]

            for mask_key in EVAL_MASKS:
                if mask_key not in ds["masks"]:
                    continue
                obs_mask = ds["masks"][mask_key]
                # eval_mask: structural zeros that are observed in ground truth
                structural_mask = np.isfinite(panel).astype(np.float32)
                eval_mask = structural_mask * (1 - obs_mask)

                pred_mean, pred_log_sigma = _predict(model, panel, obs_mask, adj_s, adj_t, device)
                mae, rmse = _compute_mae_rmse(pred_mean, panel, eval_mask)
                mae_ffill = _ffill_baseline(panel, obs_mask, eval_mask)
                mae_nogr = _nogr_baseline(model, panel, obs_mask, adj_s, adj_t, eval_mask, device)

                # log_sigma stats on eval cells
                pred_ls_t = torch.from_numpy(pred_log_sigma.astype(np.float32))
                eval_mask_t = torch.from_numpy(eval_mask.astype(np.float32))
                ls_stats = log_sigma_stats(pred_ls_t, eval_mask_t)

                # Graph metrics (only if heads available and true_relations non-empty)
                if heads is not None and true_relations:
                    g_metrics = heads.edge_metrics(model, true_relations, device)
                else:
                    g_metrics = {
                        "edge_auc": float("nan"),
                        "edge_auprc": float("nan"),
                        "sign_acc": float("nan"),
                        "lag_acc": float("nan"),
                    }

                results.append(ZeroShotResult(
                    variant=variant,
                    epoch_budget=epoch_budget,
                    scenario=scenario,
                    mask_key=mask_key,
                    seed=seed,
                    mae=mae,
                    rmse=rmse,
                    mae_ffill=mae_ffill,
                    mae_nogr=mae_nogr,
                    log_sigma_min=ls_stats["log_sigma_min"],
                    log_sigma_mean=ls_stats["log_sigma_mean"],
                    log_sigma_max=ls_stats["log_sigma_max"],
                    edge_auc=g_metrics["edge_auc"],
                    edge_auprc=g_metrics["edge_auprc"],
                    sign_acc=g_metrics["sign_acc"],
                    lag_acc=g_metrics["lag_acc"],
                ))

    return results


def _few_shot_adaptation(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
    k_frac: float,
    support_rng: np.random.Generator,
) -> tuple[HERALDGraphImputerLagged, float]:
    """
    Decoder-only fine-tune on k_frac of observed cells as support.
    Attention parameters (log_sect_attn_lag1/lag2, log_terr_attn) are frozen.
    Returns (adapted_model, support_loss_final).
    """
    adapted = copy.deepcopy(model)

    # Build support mask: k_frac of observed positions
    observed_pos = np.where(obs_mask == 1)
    n_obs = len(observed_pos[0])
    n_support = max(1, int(k_frac * n_obs))
    support_idx = support_rng.choice(n_obs, n_support, replace=False)
    support_positions = tuple(arr[support_idx] for arr in observed_pos)

    support_mask_input = obs_mask.copy()
    support_mask_input[support_positions] = 0  # hide from input
    support_loss_mask = np.zeros_like(obs_mask, dtype=np.float32)
    support_loss_mask[support_positions] = 1.0  # predict these

    # Freeze attention, only update decoder (net) params
    attn_names = {"log_sect_attn_lag1", "log_sect_attn_lag2", "log_terr_attn"}
    decoder_params = [
        p for name, p in adapted.named_parameters() if name not in attn_names
    ]
    for p in adapted.parameters():
        p.requires_grad = False
    for p in decoder_params:
        p.requires_grad = True

    optimizer = torch.optim.Adam(decoder_params, lr=1e-3)

    panel_t, _, adj_s_t, adj_t_t = _prep_tensors(
        panel, support_mask_input, adj_s, adj_t, device
    )
    input_mask_t = torch.from_numpy(support_mask_input.astype(np.float32)).to(device)
    loss_mask_t = torch.from_numpy(support_loss_mask.astype(np.float32)).to(device)
    true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
    temp_feats_t = torch.from_numpy(
        _build_temporal_features(panel, support_mask_input).astype(np.float32)
    ).to(device)

    best_loss = float("inf")
    best_state = copy.deepcopy(adapted.state_dict())
    no_improve = 0

    adapted.train()
    for _ in range(FEWSHOT_N_ADAPT_EPOCHS):
        optimizer.zero_grad()
        out = adapted(panel_t, input_mask_t, adj_s_t, adj_t_t, temp_feats_t)
        pred_mean = out[..., 0]
        pred_log_sigma = out[..., 1]
        loss = masked_nll_clamped(pred_mean, pred_log_sigma, true_t, loss_mask_t)
        if torch.isnan(loss) or torch.isinf(loss):
            break
        loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder_params, max_norm=1.0)
        optimizer.step()

        l = loss.item()
        if l < best_loss - 1e-6:
            best_loss = l
            best_state = copy.deepcopy(adapted.state_dict())
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= FEWSHOT_PATIENCE:
                break

    adapted.load_state_dict(best_state)
    for p in adapted.parameters():
        p.requires_grad = True

    return adapted, best_loss


def evaluate_few_shot(
    checkpoint_path: str | Path,
    variant: str,
    epoch_budget: int,
    device: str = "cpu",
    k_fracs: list[float] | None = None,
) -> list[FewShotResult]:
    """
    Few-shot evaluation on all EVAL_SCENARIOS × EVAL_MASKS × EVAL_SEEDS × k_fracs.
    Checkpoint is loaded fresh for each (scenario, seed, mask) combination.
    """
    if k_fracs is None:
        k_fracs = FEWSHOT_K_FRACS

    results = []
    for scenario in EVAL_SCENARIOS:
        base_cfg = NOVEL_TEST_SCENARIOS[scenario]
        for seed in EVAL_SEEDS:
            cfg = dataclasses.replace(base_cfg, seed=seed)
            ds = generate_dataset(cfg)
            panel = ds["panel"]
            adj_s = ds["sector_adj"]
            adj_t = ds["territory_adj"]

            for mask_key in EVAL_MASKS:
                if mask_key not in ds["masks"]:
                    continue
                obs_mask = ds["masks"][mask_key]
                structural_mask = np.isfinite(panel).astype(np.float32)
                eval_mask = structural_mask * (1 - obs_mask)

                # Zero-shot MAE (reference)
                model_zs = _load_model(checkpoint_path, device)
                pred_mean_zs, _ = _predict(model_zs, panel, obs_mask, adj_s, adj_t, device)
                mae_zs, _ = _compute_mae_rmse(pred_mean_zs, panel, eval_mask)
                mae_ffill = _ffill_baseline(panel, obs_mask, eval_mask)

                for k_frac in k_fracs:
                    # Load fresh model for each k_frac (avoid adaptation leak between k_fracs)
                    model_fs = _load_model(checkpoint_path, device)
                    support_rng = np.random.default_rng(FEWSHOT_SUPPORT_SEED + seed)

                    adapted_model, _ = _few_shot_adaptation(
                        model_fs, panel, obs_mask, adj_s, adj_t, device, k_frac, support_rng
                    )

                    pred_mean_fs, _ = _predict(adapted_model, panel, obs_mask, adj_s, adj_t, device)
                    mae_fs, _ = _compute_mae_rmse(pred_mean_fs, panel, eval_mask)

                    reduction = (
                        (mae_zs - mae_fs) / mae_zs * 100
                        if (mae_zs > 0 and not np.isnan(mae_zs))
                        else float("nan")
                    )

                    results.append(FewShotResult(
                        variant=variant,
                        epoch_budget=epoch_budget,
                        scenario=scenario,
                        mask_key=mask_key,
                        seed=seed,
                        k_frac=k_frac,
                        mae_zeroshot=mae_zs,
                        mae_fewshot=mae_fs,
                        mae_ffill=mae_ffill,
                        mae_reduction_pct=reduction,
                    ))

    return results


def select_top2_variants(
    val_results: dict[str, float],
) -> list[str]:
    """
    Select top-2 variants by val_loss (ascending).
    val_results: {variant_key: val_loss_float}
    variant_key = f"{variant}_ep{epoch_budget}"
    """
    sorted_variants = sorted(val_results.items(), key=lambda x: x[1])
    top2 = [k for k, _ in sorted_variants[:2]]
    return top2


def aggregate_zero_shot(results: list[ZeroShotResult]) -> dict:
    """Aggregate MAE/RMSE by variant × epoch_budget × scenario × mask_key."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in results:
        key = (r.variant, r.epoch_budget, r.scenario, r.mask_key)
        groups[key].append(r)

    summary = {}
    for key, rlist in groups.items():
        maes = [r.mae for r in rlist if not np.isnan(r.mae)]
        rmses = [r.rmse for r in rlist if not np.isnan(r.rmse)]
        ffills = [r.mae_ffill for r in rlist if not np.isnan(r.mae_ffill)]
        n_beat_ffill = sum(1 for r in rlist if (not np.isnan(r.mae) and not np.isnan(r.mae_ffill) and r.mae < r.mae_ffill))
        n_seeds = len(rlist)

        summary[key] = {
            "mae_mean": float(np.mean(maes)) if maes else float("nan"),
            "mae_std": float(np.std(maes)) if maes else float("nan"),
            "rmse_mean": float(np.mean(rmses)) if rmses else float("nan"),
            "mae_ffill_mean": float(np.mean(ffills)) if ffills else float("nan"),
            "n_beat_ffill": n_beat_ffill,
            "n_seeds": n_seeds,
            "frac_beat_ffill": n_beat_ffill / n_seeds if n_seeds > 0 else float("nan"),
            "log_sigma_mean": float(np.mean([r.log_sigma_mean for r in rlist if not np.isnan(r.log_sigma_mean)])) if rlist else float("nan"),
        }
    return summary


def aggregate_few_shot(results: list[FewShotResult]) -> dict:
    """Aggregate few-shot metrics by variant × epoch_budget × scenario × mask_key × k_frac."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in results:
        key = (r.variant, r.epoch_budget, r.scenario, r.mask_key, r.k_frac)
        groups[key].append(r)

    summary = {}
    for key, rlist in groups.items():
        reductions = [r.mae_reduction_pct for r in rlist if not np.isnan(r.mae_reduction_pct)]
        mae_zs = [r.mae_zeroshot for r in rlist if not np.isnan(r.mae_zeroshot)]
        mae_fs = [r.mae_fewshot for r in rlist if not np.isnan(r.mae_fewshot)]
        n_seeds = len(rlist)
        n_beat = sum(1 for r in rlist if (not np.isnan(r.mae_fewshot) and not np.isnan(r.mae_zeroshot) and r.mae_fewshot < r.mae_zeroshot))

        summary[key] = {
            "mae_reduction_mean_pct": float(np.mean(reductions)) if reductions else float("nan"),
            "mae_reduction_std_pct": float(np.std(reductions)) if reductions else float("nan"),
            "mae_zeroshot_mean": float(np.mean(mae_zs)) if mae_zs else float("nan"),
            "mae_fewshot_mean": float(np.mean(mae_fs)) if mae_fs else float("nan"),
            "n_seeds": n_seeds,
            "n_beat_zeroshot": n_beat,
        }
    return summary
