"""
evaluator.py — Zero-shot evaluation for Phase 11 generalization (DEC-045)

INVARIANTS (safety contract):
  1. No optimizer or parameter updates during evaluation.
  2. No statistics computed from test panel (no normalization, no whitening).
  3. Model loaded from checkpoint; checkpoint hash verified before/after.
  4. model.eval() + torch.no_grad() always active during test forward passes.

Seven models evaluated per (scenario, seed, mask):
  ffill                  : forward-fill baseline
  ridge                  : Ridge regression baseline (causal, trained on observed train-window)
  no_graph               : HERALDGraphImputerLagged trained from scratch, adj_s=0
  herald_contemp         : HERALDGraphImputer (contemporaneous, Phase 9)
  herald_lagged          : LOADED FROM CHECKPOINT (zero-shot, no adaptation)
  herald_lagged_permuted : same checkpoint, permuted adj_s
  oracle_lagged          : same checkpoint, directed oracle adj frozen
"""

from __future__ import annotations

import copy
import dataclasses
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import average_precision_score

REPO_ROOT = Path(__file__).resolve().parents[4]
import sys
sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_herald_synthetic import (
    BENCHMARK_SCENARIOS,
    generate_dataset,
    mask_panel,
)
from src.modeles.synthetic.imputation_baselines import ForwardFillImputer, RidgeImputer
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    build_permuted_adj,
    train_herald_imputer,
    impute_deterministic,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    train_herald_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
    check_no_leakage,
)
from src.modeles.synthetic.phase11_generalization.trainer import (
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
    checkpoint_hash,
    save_checkpoint,
    load_checkpoint,
    make_train_entries,
    make_val_entries,
    train_multi_dataset,
    DEFAULT_EPOCHS,
    DEFAULT_LR,
    DEFAULT_PATIENCE,
    STRATEGY_SCENARIOS,
)
from src.modeles.synthetic.phase11_generalization.splits import (
    NOVEL_TEST_SCENARIOS,
    TEST_SEEDS,
    PILOT_TEST_SEEDS,
    PILOT_TEST_MASK_KEYS,
    FULL_TEST_MASK_KEYS,
    TEST_SCENARIO_NAMES,
    PILOT_TRAIN_SEEDS,
    VAL_SEEDS,
    PILOT_VAL_SEEDS,
    TRAIN_SEEDS,
)

CONTEMP_N_EPOCHS = 200  # Phase 9 contemporaneous baseline epochs
CONTEMP_HIDDEN_DIM = 64
NO_GRAPH_EPOCHS = 150   # no_graph model epochs (local training per test instance)


def _compute_auprc(true_rels: list, n_sectors: int, attn: np.ndarray) -> tuple[float, float]:
    """Returns (auprc, prevalence). Convention: attn[target, source]."""
    true_adj = np.zeros((n_sectors, n_sectors))
    for rel in true_rels:
        if rel.source_sector < n_sectors and rel.target_sector < n_sectors:
            true_adj[rel.source_sector, rel.target_sector] = 1
    rows, cols = np.where(~np.eye(n_sectors, dtype=bool))
    y_true = true_adj[rows, cols]
    y_score = attn[cols, rows]
    n_true = int(y_true.sum())
    prevalence = n_true / len(y_true) if len(y_true) > 0 else 0.0
    if n_true == 0 or n_true == len(y_true):
        return float("nan"), prevalence
    try:
        return float(average_precision_score(y_true, y_score)), prevalence
    except Exception:
        return float("nan"), prevalence


def _eval_mae(true_panel: np.ndarray, pred: np.ndarray, mask: np.ndarray) -> float:
    hidden = mask == 0
    if hidden.sum() == 0:
        return float("nan")
    return float(np.abs(true_panel[hidden] - pred[hidden]).mean())


def evaluate_model_on_dataset(
    ds: dict,
    mask_key: str,
    herald_checkpoint_path: Path,
    checkpoint_hash_before: str,
    device: str = "cpu",
    no_graph_epochs: int = NO_GRAPH_EPOCHS,
    contemp_epochs: int = CONTEMP_N_EPOCHS,
) -> dict[str, Any]:
    """
    Run all 7 models on a single test (ds, mask_key) pair.
    Herald-lagged is loaded from checkpoint — NO adaptation, NO optimizer calls.

    Returns a result dict with MAE and edge metrics per model.
    """
    panel = ds["panel"]
    mask = ds["masks"][mask_key]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_relations = ds["true_relations"]
    n_S = panel.shape[1]

    # Leakage check
    leakage = check_no_leakage(panel, mask)

    results: dict[str, Any] = {
        "mask_key": mask_key,
        "leakage_pass": bool(leakage),
        "n_hidden": int((mask == 0).sum()),
        "models": {},
    }

    # ── 1. ffill ─────────────────────────────────────────────────────────────
    ff = ForwardFillImputer().fit(panel, mask).transform(panel, mask)
    m = compute_imputation_metrics(panel, ff, mask)
    results["models"]["ffill"] = {"mae": m.mae, "rmse": m.rmse}

    # ── 2. ridge ─────────────────────────────────────────────────────────────
    rr = RidgeImputer().fit(panel, mask).transform(panel, mask)
    m = compute_imputation_metrics(panel, rr, mask)
    results["models"]["ridge"] = {"mae": m.mae, "rmse": m.rmse}

    # ── 3. no_graph: HERALDGraphImputerLagged with adj_s=0 (local train) ───
    zeros_adj = np.zeros_like(adj_s)
    ng_model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    train_herald_lagged(ng_model, panel, mask, zeros_adj, adj_t,
                        n_epochs=no_graph_epochs, device=device)
    ng_pred = impute_deterministic_lagged(ng_model, panel, mask, zeros_adj, adj_t, device=device)
    m = compute_imputation_metrics(panel, ng_pred, mask)
    results["models"]["no_graph"] = {"mae": m.mae, "rmse": m.rmse}

    # ── 4. herald_contemp: Phase 9 contemporaneous model (local train) ──────
    hc_model = HERALDGraphImputer(N_SECTORS, N_TERRITORIES, CONTEMP_HIDDEN_DIM)
    train_herald_imputer(hc_model, panel, mask, adj_s, adj_t,
                         n_epochs=contemp_epochs, device=device)
    hc_pred = impute_deterministic(hc_model, panel, mask, adj_s, adj_t, device=device)
    m = compute_imputation_metrics(panel, hc_pred, mask)
    results["models"]["herald_contemp"] = {"mae": m.mae, "rmse": m.rmse}

    # ── 5. herald_lagged: ZERO-SHOT from checkpoint (NO adaptation) ─────────
    # Verify checkpoint hasn't been modified since training
    ckpt_model = load_checkpoint(herald_checkpoint_path, device=device)
    hash_after_load = checkpoint_hash(ckpt_model.state_dict())
    assert hash_after_load == checkpoint_hash_before, (
        f"Checkpoint hash mismatch! before={checkpoint_hash_before}, after={hash_after_load}. "
        "This indicates the model was modified between training and evaluation."
    )
    # model.eval() is set by load_checkpoint; no optimizer created
    hl_pred = impute_deterministic_lagged(ckpt_model, panel, mask, adj_s, adj_t, device=device)
    m = compute_imputation_metrics(panel, hl_pred, mask)
    attn = ckpt_model.get_sector_attention() if hasattr(ckpt_model, "get_sector_attention") else ckpt_model.log_sect_attn_lag1.detach().exp().cpu().numpy()
    edge_m = compute_edge_recovery_metrics(true_relations, n_S, attn)
    auprc, prevalence = _compute_auprc(true_relations, n_S, attn)
    results["models"]["herald_lagged"] = {
        "mae": m.mae, "rmse": m.rmse,
        "edge_auc": edge_m.auc,
        "edge_auprc": auprc,
        "edge_prevalence": prevalence,
        "edge_precision": edge_m.precision_at_k,
        "edge_recall": edge_m.recall_at_k,
        "edge_f1": edge_m.f1_at_k,
    }

    # ── 6. herald_lagged_permuted: same checkpoint, permuted adj_s ──────────
    rng_perm = np.random.default_rng(42)
    perm_adj_s, _perm_adj_t, *_ = build_permuted_adj(adj_s, adj_t, rng_perm)
    perm_model = load_checkpoint(herald_checkpoint_path, device=device)
    hp_pred = impute_deterministic_lagged(perm_model, panel, mask, perm_adj_s, adj_t, device=device)
    m = compute_imputation_metrics(panel, hp_pred, mask)
    results["models"]["herald_lagged_permuted"] = {"mae": m.mae, "rmse": m.rmse}

    # ── 7. oracle_lagged: same checkpoint but directed oracle attention ──────
    oracle_model = load_checkpoint(herald_checkpoint_path, device=device)
    build_directed_oracle_lagged(oracle_model, true_relations, n_S)
    oracle_model.eval()  # ensure eval after oracle injection
    oracle_pred = impute_deterministic_lagged(oracle_model, panel, mask, adj_s, adj_t, device=device)
    m = compute_imputation_metrics(panel, oracle_pred, mask)
    oracle_attn = oracle_model.get_sector_attention() if hasattr(oracle_model, "get_sector_attention") else oracle_model.log_sect_attn_lag1.detach().exp().cpu().numpy()
    oracle_edge = compute_edge_recovery_metrics(true_relations, n_S, oracle_attn)
    results["models"]["oracle_lagged"] = {
        "mae": m.mae, "rmse": m.rmse,
        "edge_auc": float(oracle_edge.auc),
    }

    return results


def run_evaluation(
    strategy: str,
    herald_checkpoint_path: Path,
    checkpoint_hash_before: str,
    test_seeds: list[int],
    test_mask_keys: list[str],
    device: str = "cpu",
    no_graph_epochs: int = NO_GRAPH_EPOCHS,
) -> list[dict]:
    """
    Zero-shot evaluation of trained model on all novel test scenarios.
    Returns list of result records (one per scenario × seed × mask).
    """
    records = []
    for scenario_name, base_cfg in NOVEL_TEST_SCENARIOS.items():
        for seed in test_seeds:
            cfg = dataclasses.replace(base_cfg, seed=seed)
            ds = generate_dataset(cfg)
            for mk in test_mask_keys:
                if mk not in ds["masks"]:
                    continue
                t0 = time.time()
                res = evaluate_model_on_dataset(
                    ds, mk, herald_checkpoint_path, checkpoint_hash_before, device,
                    no_graph_epochs=no_graph_epochs,
                )
                elapsed = time.time() - t0
                records.append({
                    "protocol_version": "phase11_v1",
                    "strategy": strategy,
                    "scenario": scenario_name,
                    "seed": seed,
                    "mask_key": mk,
                    "elapsed_s": round(elapsed, 2),
                    **res,
                })
    return records
