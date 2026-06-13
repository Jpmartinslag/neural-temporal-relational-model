"""
evaluator.py — Full evaluation for Phase 12 few-shot adaptation (DEC-047).

For each (scenario, dataset_seed, k_frac, support_seed, strategy, mask_key):
  1. Load checkpoint (same for all strategies)
  2. Apply strategy freeze policy
  3. Compute graph metrics BEFORE adaptation
  4. Adapt on support labels (if k_frac > 0 and strategy is not baseline)
  5. Compute graph metrics AFTER adaptation
  6. Evaluate on imputation test cells: MAE, RMSE, Spearman, sign accuracy
  7. Compare against baselines B0/B1
  8. Verify checkpoint hash (attention must not change for Z0)

Leakage invariant: support_mask cells are NEVER in test imputation cells.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import time
from pathlib import Path

import numpy as np
import torch

from src.modeles.synthetic.herald_graph_imputer import _apply_observed
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.imputation_baselines import (
    ForwardFillImputer,
    RidgeImputer,
    _build_temporal_features,
)
from src.modeles.synthetic.evaluate_imputation import compute_imputation_metrics
from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
from src.modeles.synthetic.phase11_generalization.trainer import (
    checkpoint_hash,
    load_checkpoint,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS
from src.data.synthetic.generate_herald_synthetic import generate_dataset, mask_panel
from src.modeles.synthetic.phase12_few_shot.splits import (
    make_temporal_splits,
    make_fewshot_support_mask,
    make_eval_masks,
    make_imputation_test_mask,
    verify_disjoint_splits,
)
from src.modeles.synthetic.phase12_few_shot.adapter import apply_strategy_freeze
from src.modeles.synthetic.phase12_few_shot.adaptation_trainer import (
    adapt_model,
    ADAPTATION_EPOCHS,
    ADAPTATION_LR,
    ADAPTATION_PATIENCE,
)
from src.modeles.synthetic.phase12_few_shot.graph_metrics import compute_graph_preservation
from src.modeles.synthetic.phase12_few_shot.decoder_ablation import (
    build_decoder, replace_decoder,
)

STRATEGIES = ["Z0", "A1", "A2", "A3", "A4", "C0", "B0", "B1", "P0"]
EVAL_MASK_KEYS = ["mcar_30", "block_30"]

# ── Permuted adjacency ─────────────────────────────────────────────────────────

def _permute_adj(adj_s: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Row/column permute adj_s to destroy edge structure."""
    n = adj_s.shape[0]
    perm = rng.permutation(n)
    return adj_s[perm][:, perm]


# ── Single evaluation ──────────────────────────────────────────────────────────

def evaluate_one(
    scenario_name: str,
    dataset_seed: int,
    k_frac: float,
    support_seed: int,
    strategy: str,
    mask_key: str,
    checkpoint_path: Path,
    checkpoint_hash_before: str,
    device: str = "cpu",
    n_adapt_epochs: int = ADAPTATION_EPOCHS,
    adapt_lr: float = ADAPTATION_LR,
    adapt_patience: int = ADAPTATION_PATIENCE,
    decoder_variant: str = "mlp_relu",
    bottleneck: int = 16,
) -> dict:
    """
    Evaluate one (scenario, seed, k_frac, support_seed, strategy, mask_key) combination.
    Returns a result record dict with all metrics.
    """
    t0 = time.time()

    # ── Generate dataset ──────────────────────────────────────────────────────
    import dataclasses as dc
    base_cfg = NOVEL_TEST_SCENARIOS[scenario_name]
    cfg = dc.replace(base_cfg, seed=dataset_seed)
    ds = generate_dataset(cfg)

    panel = ds["panel"]                   # (n_T, n_S, n_Y)
    true_relations = ds["true_relations"]
    adj_s = ds["sector_adj"]              # (n_S, n_S)
    adj_t = ds["territory_adj"]           # (n_T, n_T)
    n_T, n_S, n_Y = panel.shape

    if mask_key not in ds["masks"]:
        return {"error": f"mask_key {mask_key!r} not found in dataset"}

    obs_mask = ds["masks"][mask_key]      # (n_T, n_S, n_Y) 1=observed 0=hidden

    # ── Temporal splits ───────────────────────────────────────────────────────
    support_years, val_years, test_years = make_temporal_splits(n_Y)

    # ── Support selection ─────────────────────────────────────────────────────
    rng = np.random.default_rng(support_seed)
    support_mask, support_info = make_fewshot_support_mask(
        obs_mask, support_years, k_frac, rng
    )
    val_mask_obs, _ = make_eval_masks(obs_mask, val_years, test_years)
    # val for early stopping = observed cells in val window
    val_mask_obs, test_mask_obs = make_eval_masks(obs_mask, val_years, test_years)
    # imputation test = HIDDEN cells in test window
    imputation_test_mask = make_imputation_test_mask(obs_mask, test_years)

    # ── Leakage check ─────────────────────────────────────────────────────────
    hidden_mask = (obs_mask == 0).astype(np.int8)
    try:
        verify_disjoint_splits(support_mask, val_mask_obs, test_mask_obs, hidden_mask)
        leakage_pass = True
    except AssertionError as e:
        leakage_pass = False

    # Explicit check: support cells must not overlap imputation test cells
    support_test_overlap = int((support_mask.astype(bool) & imputation_test_mask.astype(bool)).sum())
    if support_test_overlap > 0:
        leakage_pass = False

    n_hidden_test = int(imputation_test_mask.sum())

    # ── Baseline strategies (B0=ffill, B1=Ridge) ─────────────────────────────
    if strategy in {"B0", "B1"}:
        if strategy == "B0":
            imp = ForwardFillImputer()
        else:
            imp = RidgeImputer()
        imp.fit(panel, obs_mask)
        imputed = imp.transform(panel, obs_mask)

        if n_hidden_test == 0:
            metrics = {"mae": float("nan"), "rmse": float("nan"),
                       "spearman_r": float("nan"), "sign_accuracy": float("nan"),
                       "n_evaluated": 0}
        else:
            m = compute_imputation_metrics(panel, imputed, imputation_test_mask == 0)
            # Note: compute_imputation_metrics expects hidden=mask==0
            # Our imputation_test_mask==1 means "test hidden cells"
            # Build correct evaluation mask: test hidden cells = imputation_test_mask
            test_hidden_eval = np.ones_like(obs_mask)
            test_hidden_eval[imputation_test_mask == 1] = 0
            m2 = compute_imputation_metrics(panel, imputed, test_hidden_eval)
            metrics = {
                "mae": m2.mae,
                "rmse": m2.rmse,
                "spearman_r": m2.spearman_r,
                "sign_accuracy": m2.sign_accuracy,
                "n_evaluated": m2.n_evaluated,
            }

        return {
            "scenario": scenario_name,
            "dataset_seed": dataset_seed,
            "k_frac": k_frac,
            "support_seed": support_seed,
            "strategy": strategy,
            "mask_key": mask_key,
            "mae": metrics["mae"],
            "rmse": metrics["rmse"],
            "spearman_r": metrics["spearman_r"],
            "sign_accuracy": metrics["sign_accuracy"],
            "n_support": support_info["n_selected"],
            "n_hidden_test": n_hidden_test,
            "n_labels": support_info["n_selected"],
            "n_years": n_Y,
            "n_territories": n_T,
            "n_sectors": n_S,
            "leakage_pass": leakage_pass,
            "graph_preserved": None,
            "auc_before": None,
            "auc_after": None,
            "auc_change": None,
            "adapted": False,
            "is_extreme_low_shot": support_info.get("is_extreme_low_shot", False),
            "runtime_s": time.time() - t0,
            "decoder_variant": decoder_variant,
        }

    # ── Load checkpoint ───────────────────────────────────────────────────────
    model = load_checkpoint(checkpoint_path, device=device)
    loaded_hash = checkpoint_hash(model.state_dict())
    assert loaded_hash == checkpoint_hash_before, (
        f"Checkpoint hash mismatch: expected {checkpoint_hash_before!r}, "
        f"got {loaded_hash!r}"
    )

    # Decoder ablation (diagnostic only)
    if decoder_variant != "mlp_relu":
        new_net = build_decoder(decoder_variant)
        replace_decoder(model, new_net)

    # ── Graph metrics BEFORE adaptation ──────────────────────────────────────
    attn_before = model.get_sector_attention()  # (n_S, n_S)

    # ── Apply freeze strategy ─────────────────────────────────────────────────
    adj_s_eval = adj_s
    if strategy == "C0":
        # Zero adjacency — no graph signal
        adj_s_eval = np.zeros_like(adj_s)
    elif strategy == "P0":
        # Permuted adjacency — destroys edge structure
        perm_rng = np.random.default_rng(support_seed + 9999)
        adj_s_eval = _permute_adj(adj_s, perm_rng)

    freeze_audit = apply_strategy_freeze(model, strategy, bottleneck=bottleneck)

    # ── Adapt model ───────────────────────────────────────────────────────────
    adapt_history = adapt_model(
        model=model,
        panel=panel,
        support_mask=support_mask,
        val_mask=val_mask_obs,
        adj_s=adj_s_eval,
        adj_t=adj_t,
        n_epochs=n_adapt_epochs,
        lr=adapt_lr,
        patience=adapt_patience,
        device=device,
    )

    # ── Graph metrics AFTER adaptation ────────────────────────────────────────
    attn_after = model.get_sector_attention()  # (n_S, n_S)

    graph_pres = compute_graph_preservation(
        attn_before, attn_after, true_relations, n_S
    )

    # For Z0: verify checkpoint hash did not change
    if strategy == "Z0":
        post_hash = checkpoint_hash(model.state_dict())
        assert post_hash == checkpoint_hash_before, (
            f"Z0: checkpoint hash changed after zero-shot eval! "
            f"{checkpoint_hash_before!r} → {post_hash!r}"
        )

    # ── Imputation evaluation on test hidden cells ────────────────────────────
    model.eval()
    imputed_raw = impute_deterministic_lagged(
        model, panel, obs_mask, adj_s_eval, adj_t, device=device
    )

    if n_hidden_test == 0:
        imputation_metrics = {
            "mae": float("nan"), "rmse": float("nan"),
            "spearman_r": float("nan"), "sign_accuracy": float("nan"),
            "n_evaluated": 0,
        }
    else:
        # Evaluate on imputation_test_mask cells (hidden in test window)
        # compute_imputation_metrics takes mask where 0=hidden
        # Build: 0 everywhere except imputation_test_mask cells (which are 0 in obs_mask)
        eval_mask = np.ones_like(obs_mask)
        eval_mask[imputation_test_mask == 1] = 0
        m = compute_imputation_metrics(panel, imputed_raw, eval_mask)
        imputation_metrics = {
            "mae": m.mae,
            "rmse": m.rmse,
            "spearman_r": m.spearman_r,
            "sign_accuracy": m.sign_accuracy,
            "n_evaluated": m.n_evaluated,
        }

    return {
        "scenario": scenario_name,
        "dataset_seed": dataset_seed,
        "k_frac": k_frac,
        "support_seed": support_seed,
        "strategy": strategy,
        "mask_key": mask_key,
        "mae": imputation_metrics["mae"],
        "rmse": imputation_metrics["rmse"],
        "spearman_r": imputation_metrics["spearman_r"],
        "sign_accuracy": imputation_metrics["sign_accuracy"],
        "n_support": support_info["n_selected"],
        "n_hidden_test": n_hidden_test,
        "n_labels": support_info["n_selected"],
        "n_years": n_Y,
        "n_territories": n_T,
        "n_sectors": n_S,
        "leakage_pass": leakage_pass,
        "graph_preserved": graph_pres["graph_preserved"],
        "auc_before": graph_pres["auc_before"],
        "auc_after": graph_pres["auc_after"],
        "auc_change": graph_pres["auc_change"],
        "attn_correlation": graph_pres["attn_correlation"],
        "mean_weight_change": graph_pres["mean_weight_change"],
        "adapted": adapt_history.get("adapted", False),
        "best_epoch": adapt_history.get("best_epoch", 0),
        "is_extreme_low_shot": support_info.get("is_extreme_low_shot", False),
        "n_trainable_params": freeze_audit.get("total_trainable", 0),
        "runtime_s": time.time() - t0,
        "decoder_variant": decoder_variant,
    }


# ── Pilot runner ───────────────────────────────────────────────────────────────

def run_pilot(
    checkpoint_path: Path,
    checkpoint_hash_before: str,
    scenarios: list = None,
    dataset_seeds: list = None,
    k_fracs: list = None,
    support_seeds: list = None,
    strategies: list = None,
    mask_keys: list = None,
    device: str = "cpu",
    output_path: Path = None,
    decoder_variant: str = "mlp_relu",
    n_adapt_epochs: int = ADAPTATION_EPOCHS,
    adapt_patience: int = ADAPTATION_PATIENCE,
    adapt_lr: float = ADAPTATION_LR,
    bottleneck: int = 16,
) -> list[dict]:
    """
    Run pilot evaluation. Saves records atomically. Supports resume.
    Returns list of result dicts.
    """
    from src.modeles.synthetic.phase12_few_shot.splits import (
        PILOT_FEWSHOT_SEEDS, PILOT_K_FRACS,
    )

    scenarios = scenarios or ["novel_lag2"]
    dataset_seeds = dataset_seeds or [1000, 2000, 3000]
    k_fracs = k_fracs or PILOT_K_FRACS
    support_seeds = support_seeds or PILOT_FEWSHOT_SEEDS
    strategies = strategies or ["Z0", "A1", "A2", "A4", "C0", "B0", "B1", "P0"]
    mask_keys = mask_keys or EVAL_MASK_KEYS

    # Load existing records for resume
    existing: list[dict] = []
    if output_path and output_path.exists():
        try:
            existing = json.loads(output_path.read_text())
        except Exception:
            existing = []

    done_keys: set = set()
    for rec in existing:
        key = (
            rec.get("scenario"), rec.get("dataset_seed"), rec.get("k_frac"),
            rec.get("support_seed"), rec.get("strategy"), rec.get("mask_key"),
        )
        if "error" not in rec:
            done_keys.add(key)

    records: list[dict] = list(existing)

    total = len(scenarios) * len(dataset_seeds) * len(k_fracs) * len(support_seeds) * len(strategies) * len(mask_keys)
    n_done = len(done_keys)
    print(f"Phase 12 pilot: {total} combinations, {n_done} already done, resuming...")

    for scenario in scenarios:
        for dseed in dataset_seeds:
            for kf in k_fracs:
                for sseed in support_seeds:
                    for strat in strategies:
                        for mk in mask_keys:
                            key = (scenario, dseed, kf, sseed, strat, mk)
                            if key in done_keys:
                                continue
                            try:
                                rec = evaluate_one(
                                    scenario_name=scenario,
                                    dataset_seed=dseed,
                                    k_frac=kf,
                                    support_seed=sseed,
                                    strategy=strat,
                                    mask_key=mk,
                                    checkpoint_path=checkpoint_path,
                                    checkpoint_hash_before=checkpoint_hash_before,
                                    device=device,
                                    n_adapt_epochs=n_adapt_epochs,
                                    adapt_lr=adapt_lr,
                                    adapt_patience=adapt_patience,
                                    decoder_variant=decoder_variant,
                                    bottleneck=bottleneck,
                                )
                            except Exception as e:
                                rec = {
                                    "scenario": scenario, "dataset_seed": dseed,
                                    "k_frac": kf, "support_seed": sseed,
                                    "strategy": strat, "mask_key": mk,
                                    "error": str(e),
                                }
                            records.append(rec)
                            n_done += 1
                            if n_done % 10 == 0:
                                print(f"  {n_done}/{total} done...")

                            # Atomic save
                            if output_path:
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                tmp = output_path.parent / (output_path.stem + ".tmp")
                                tmp.write_text(json.dumps(records, indent=2))
                                tmp.rename(output_path)

    print(f"Pilot complete: {len(records)} records.")
    return records
