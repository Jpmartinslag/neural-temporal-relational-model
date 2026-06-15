"""
evaluator.py — Zero-shot and few-shot evaluation for each pretraining checkpoint.

7 model comparison per checkpoint:
  ffill, ridge, no_graph (herald, adj=0), herald_lagged (zero-shot),
  herald_permuted, oracle_lagged, (baseline reference)

Plus: graph_contribution = |MAE(no_graph) - MAE(herald_lagged)| (can be negative if
     no_graph is better — tracked directionally in records).

CRITICAL CONSTRAINT: oracle_lagged uses true_relations ground truth which is
SYNTHETIC-ONLY. This model cannot be applied to real country data.
"""

from __future__ import annotations

import copy
import dataclasses
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
from src.modeles.synthetic.herald_graph_imputer import _prep_tensors, build_permuted_adj
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    impute_deterministic_lagged,
    train_herald_lagged,
)
from src.modeles.synthetic.imputation_baselines import ForwardFillImputer, RidgeImputer
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
)
from src.modeles.synthetic.phase11_generalization.splits import (
    NOVEL_TEST_SCENARIOS,
    TEST_SEEDS,
)
from src.modeles.synthetic.phase11_generalization.trainer import (
    checkpoint_hash,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
    load_checkpoint,
)
from src.modeles.synthetic.phase12_few_shot.splits import (
    make_temporal_splits,
    make_fewshot_support_mask,
    make_eval_masks,
)
from src.modeles.synthetic.phase12_few_shot.adapter import (
    apply_strategy_freeze,
)
from src.modeles.synthetic.phase12_few_shot.adaptation_trainer import (
    adapt_model,
)

# Oracle local training epochs (short — oracle already has correct attention)
ORACLE_LOCAL_EPOCHS: int = 50


def _load_model(checkpoint_path: Path, device: str) -> HERALDGraphImputerLagged:
    """Load model from checkpoint path."""
    return load_checkpoint(checkpoint_path, device=device)


def evaluate_checkpoint(
    checkpoint_path: Path,
    checkpoint_hash_expected: str | None,
    scenario_name: str,
    test_seeds: list[int],
    mask_keys: list[str],
    device: str = "cpu",
) -> list[dict]:
    """
    Zero-shot evaluation for a given checkpoint on novel test scenarios.

    7 models evaluated per (scenario, seed, mask):
      1. ffill               — ForwardFillImputer
      2. ridge               — RidgeImputer (temporal features only)
      3. no_graph            — herald_lagged with adj_s=0, adj_t=0
      4. herald_lagged       — standard zero-shot with true adj
      5. herald_permuted     — herald_lagged with permuted adj (null)
      6. oracle_lagged       — frozen oracle attention + MLP trained locally
      7. (optional) AUPRC for edge structure

    graph_contribution = MAE(no_graph) - MAE(herald_lagged)
      Positive = graph helps; Negative = graph hurts; Can be 0.

    Returns flat list of records (one per model × scenario × seed × mask).

    NOTE: oracle_lagged uses true_relations (SYNTHETIC-ONLY).
    """
    if scenario_name not in NOVEL_TEST_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name!r}")

    base_cfg = NOVEL_TEST_SCENARIOS[scenario_name]
    records = []

    for seed in test_seeds:
        cfg = dataclasses.replace(base_cfg, seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        adj_s = ds["sector_adj"]
        adj_t = ds["territory_adj"]
        true_relations = ds["true_relations"]
        n_T, n_S, n_Y = panel.shape

        zeros_s = np.zeros((n_S, n_S), dtype=np.float32)
        zeros_t = np.zeros((n_T, n_T), dtype=np.float32)

        for mk in mask_keys:
            if mk not in ds["masks"]:
                continue
            mask = ds["masks"][mk]

            # ── 1. ffill ───────────────────────────────────────────────────
            ff = ForwardFillImputer().fit(panel, mask)
            imp_ff = ff.transform(panel, mask)
            m_ff = compute_imputation_metrics(panel, imp_ff, mask)
            records.append(_make_record(
                "ffill", scenario_name, seed, mk,
                mae=m_ff.mae, edge_auc=float("nan"),
                graph_contribution=float("nan"),
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint_hash_expected or "",
            ))

            # ── 2. ridge ──────────────────────────────────────────────────
            ridge = RidgeImputer().fit(panel, mask)
            imp_ridge = ridge.transform(panel, mask)
            m_ridge = compute_imputation_metrics(panel, imp_ridge, mask)
            records.append(_make_record(
                "ridge", scenario_name, seed, mk,
                mae=m_ridge.mae, edge_auc=float("nan"),
                graph_contribution=float("nan"),
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint_hash_expected or "",
            ))

            # ── Load pretrained model ──────────────────────────────────────
            model = _load_model(checkpoint_path, device)

            # ── 3. no_graph — herald with zeros adj ────────────────────────
            imp_nograph = impute_deterministic_lagged(model, panel, mask, zeros_s, zeros_t, device)
            m_nograph = compute_imputation_metrics(panel, imp_nograph, mask)
            records.append(_make_record(
                "no_graph", scenario_name, seed, mk,
                mae=m_nograph.mae, edge_auc=float("nan"),
                graph_contribution=float("nan"),
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint_hash_expected or "",
            ))

            # ── 4. herald_lagged — zero-shot with true adj ─────────────────
            imp_herald = impute_deterministic_lagged(model, panel, mask, adj_s, adj_t, device)
            m_herald = compute_imputation_metrics(panel, imp_herald, mask)
            learned_attn = model.get_sector_attention()
            edge_metrics = compute_edge_recovery_metrics(true_relations, N_SECTORS, learned_attn)
            graph_contribution = m_nograph.mae - m_herald.mae  # signed: positive=graph helps
            records.append(_make_record(
                "herald_lagged", scenario_name, seed, mk,
                mae=m_herald.mae, edge_auc=edge_metrics.auc,
                graph_contribution=graph_contribution,
                auprc=float("nan"),  # AUPRC computed separately in gates
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint_hash_expected or "",
                n_true_edges=edge_metrics.n_true_edges,
                edge_precision_at_k=edge_metrics.precision_at_k,
            ))

            # ── 5. herald_permuted — null graph ────────────────────────────
            rng_perm = np.random.default_rng(seed + 13)
            adj_s_perm, adj_t_perm, _, _ = build_permuted_adj(adj_s, adj_t, rng_perm)
            model_perm = _load_model(checkpoint_path, device)
            imp_perm = impute_deterministic_lagged(model_perm, panel, mask, adj_s_perm, adj_t_perm, device)
            m_perm = compute_imputation_metrics(panel, imp_perm, mask)
            records.append(_make_record(
                "herald_permuted", scenario_name, seed, mk,
                mae=m_perm.mae, edge_auc=float("nan"),
                graph_contribution=float("nan"),
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint_hash_expected or "",
            ))

            # ── 6. oracle_lagged — frozen attention, MLP trained locally ───
            oracle_model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
            build_directed_oracle_lagged(oracle_model, true_relations, N_SECTORS)
            train_herald_lagged(
                oracle_model, panel, mask, adj_s, adj_t,
                n_epochs=ORACLE_LOCAL_EPOCHS, lr=1e-3, device=device,
            )
            imp_oracle = impute_deterministic_lagged(oracle_model, panel, mask, adj_s, adj_t, device)
            m_oracle = compute_imputation_metrics(panel, imp_oracle, mask)
            records.append(_make_record(
                "oracle_lagged", scenario_name, seed, mk,
                mae=m_oracle.mae, edge_auc=1.0,  # oracle = perfect AUC by construction
                graph_contribution=float("nan"),
                checkpoint_path=str(checkpoint_path),
                checkpoint_hash=checkpoint_hash_expected or "",
            ))

    return records


def evaluate_fewshot(
    checkpoint_path: Path,
    checkpoint_hash_expected: str | None,
    scenario_name: str,
    test_seeds: list[int],
    k_fracs: list[float],
    support_seeds: list[int],
    mask_keys: list[str],
    device: str = "cpu",
    n_adapt_epochs: int = 50,
) -> list[dict]:
    """
    Few-shot A1 (decoder-only, frozen attention) evaluation.

    Uses make_temporal_splits and make_fewshot_support_mask from phase12.
    Temporal split: 65%/15%/20% (support/val/test).
    Test cells: hidden (obs_mask=0) in test_years window.

    INVARIANT: support cells never overlap with test cells.

    Returns flat list of records with n_labels, n_years_support, k_frac fields.
    """
    if scenario_name not in NOVEL_TEST_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name!r}")

    base_cfg = NOVEL_TEST_SCENARIOS[scenario_name]
    records = []

    for seed in test_seeds:
        cfg = dataclasses.replace(base_cfg, seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        adj_s = ds["sector_adj"]
        adj_t = ds["territory_adj"]
        true_relations = ds["true_relations"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)

        for mk in mask_keys:
            if mk not in ds["masks"]:
                continue
            obs_mask = ds["masks"][mk]

            # Val and test masks for evaluation (observed cells in those windows)
            val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)
            # Imputation evaluation: hidden cells in test_years
            test_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
            for y in test_years:
                test_window[:, :, y] = True
            imputation_mask = ((obs_mask == 0) & test_window).astype(np.int8)

            for k_frac in k_fracs:
                for fseed in support_seeds:
                    rng_fs = np.random.default_rng(fseed)
                    support_mask, support_info = make_fewshot_support_mask(
                        obs_mask, support_years, k_frac, rng_fs
                    )

                    # Load fresh model for each adaptation
                    model = _load_model(checkpoint_path, device)
                    # Apply A1 strategy: freeze attention, unfreeze net
                    apply_strategy_freeze(model, "A1")

                    # Adapt (or skip for k_frac=0.0)
                    adapt_history = adapt_model(
                        model, panel, support_mask, val_mask,
                        adj_s, adj_t,
                        n_epochs=n_adapt_epochs, lr=1e-3, patience=15,
                        device=device,
                    )

                    # Evaluate on imputation_mask (hidden test cells)
                    if imputation_mask.sum() > 0:
                        imp = impute_deterministic_lagged(model, panel, obs_mask, adj_s, adj_t, device)
                        m = compute_imputation_metrics(panel, imp, imputation_mask)
                        mae_test = m.mae
                        n_evaluated = m.n_evaluated
                    else:
                        mae_test = float("nan")
                        n_evaluated = 0

                    # Edge recovery (for graph preservation check)
                    learned_attn = model.get_sector_attention()
                    edge_metrics = compute_edge_recovery_metrics(
                        true_relations, N_SECTORS, learned_attn
                    )

                    n_labels = support_info["n_selected"]
                    n_years_support = len(support_years)

                    records.append({
                        "model_type": "fewshot_A1",
                        "scenario": scenario_name,
                        "seed": seed,
                        "mask_key": mk,
                        "k_frac": k_frac,
                        "k_frac_actual": support_info["k_frac_actual"],
                        "fewshot_seed": fseed,
                        "n_labels": n_labels,
                        "n_years_support": n_years_support,
                        "n_territories": n_T,
                        "n_sectors": n_S,
                        "mae": mae_test,
                        "n_evaluated": n_evaluated,
                        "edge_auc": edge_metrics.auc,
                        "adapted": adapt_history["adapted"],
                        "best_adapt_epoch": adapt_history["best_epoch"],
                        "is_extreme_low_shot": support_info.get("is_extreme_low_shot", False),
                        "checkpoint_path": str(checkpoint_path),
                        "checkpoint_hash": checkpoint_hash_expected or "",
                        "eval_type": "fewshot",
                        "graph_contribution": float("nan"),
                    })

    return records


def _make_record(
    model_type: str,
    scenario: str,
    seed: int,
    mask_key: str,
    mae: float,
    edge_auc: float,
    graph_contribution: float,
    checkpoint_path: str = "",
    checkpoint_hash: str = "",
    auprc: float = float("nan"),
    n_true_edges: int = 0,
    edge_precision_at_k: float = float("nan"),
) -> dict:
    return {
        "model_type": model_type,
        "scenario": scenario,
        "seed": seed,
        "mask_key": mask_key,
        "mae": mae,
        "edge_auc": edge_auc,
        "auprc": auprc,
        "graph_contribution": graph_contribution,
        "checkpoint_path": checkpoint_path,
        "checkpoint_hash": checkpoint_hash,
        "n_true_edges": n_true_edges,
        "edge_precision_at_k": edge_precision_at_k,
        "eval_type": "zero_shot",
    }


def run_full_evaluation(
    pretrain_results: dict[str, dict[int, dict]],
    output_dir: Path,
    device: str = "cpu",
    test_seeds: list[int] | None = None,
    mask_keys: list[str] | None = None,
    k_fracs: list[float] | None = None,
    fewshot_support_seeds: list[int] | None = None,
    scenario_names: list[str] | None = None,
) -> list[dict]:
    """
    For each variant × budget × scenario × seed × mask:
      - zero-shot evaluation (7 models)
      - few-shot evaluation A1 (k=0.05, k=0.10)

    Returns flat list of records.
    """
    if test_seeds is None:
        from src.modeles.synthetic.phase11_generalization.splits import TEST_SEEDS
        test_seeds = TEST_SEEDS
    if mask_keys is None:
        mask_keys = ["mcar_30"]
    if k_fracs is None:
        k_fracs = [0.05, 0.10]
    if fewshot_support_seeds is None:
        from src.modeles.synthetic.phase12_few_shot.splits import PILOT_FEWSHOT_SEEDS
        fewshot_support_seeds = PILOT_FEWSHOT_SEEDS
    if scenario_names is None:
        from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS
        scenario_names = list(NOVEL_TEST_SCENARIOS.keys())

    all_records: list[dict] = []

    for variant, budget_results in pretrain_results.items():
        for budget, result in budget_results.items():
            chkpt_path = Path(result["checkpoint_path"])
            chkpt_hash = result["checkpoint_hash"]

            if not chkpt_path.exists():
                continue

            for scenario in scenario_names:
                # Zero-shot
                zs_recs = evaluate_checkpoint(
                    checkpoint_path=chkpt_path,
                    checkpoint_hash_expected=chkpt_hash,
                    scenario_name=scenario,
                    test_seeds=test_seeds,
                    mask_keys=mask_keys,
                    device=device,
                )
                for r in zs_recs:
                    r["variant"] = variant
                    r["epoch_budget"] = budget
                all_records.extend(zs_recs)

                # Few-shot
                fs_recs = evaluate_fewshot(
                    checkpoint_path=chkpt_path,
                    checkpoint_hash_expected=chkpt_hash,
                    scenario_name=scenario,
                    test_seeds=test_seeds,
                    k_fracs=k_fracs,
                    support_seeds=fewshot_support_seeds,
                    mask_keys=mask_keys,
                    device=device,
                )
                for r in fs_recs:
                    r["variant"] = variant
                    r["epoch_budget"] = budget
                all_records.extend(fs_recs)

    return all_records
