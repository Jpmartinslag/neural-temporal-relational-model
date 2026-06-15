"""
fewshot_audit.py — Rigorous negative tests for few-shot leakage (DEC-051/DEC-052).

DEC-050 few-shot results showed 78-80% MAE reduction via A1 adaptation.
This could be legitimate (decoder calibration) or methodological leakage.

Six negative tests (all must PASS):

  NT1: Corrupt test targets → model weights UNCHANGED; only evaluation metric changes.
       Two adaptations with same seed + identical support inputs must yield identical
       parameters. Only the metric computed against corrupted targets differs.

  NT2: Replace test targets with i.i.d. noise → model weights UNCHANGED.
       Same as NT1: support/val inputs identical; test corruption invisible to training.

  NT3: Alter future targets → predictions in past window unchanged.

  NT4: Permute support labels → few-shot gain must disappear or degrade clearly.

  NT5: Train with empty support (k_frac=0) → must reproduce zero-shot exactly.

  NT6: Use randomly re-initialized decoder → gain must NOT reproduce ~80%.

DEC-052 corrections (2026-06-15):
  - Root cause of NT1/NT2 failure: Dropout non-determinism (DROPOUT=0.1).
    Two adaptation calls with identical inputs produced different params due to
    different random dropout masks. No real leakage found.
  - Fix: adapt_seed parameter now required; torch.manual_seed called before each
    adaptation to make dropout masks reproducible.
  - Semantic fix (per DEC-052 spec §6): NT1/NT2 now adapt ONCE on original panel,
    evaluate TWICE (original vs corrupted targets). This cleanly separates training
    from evaluation and proves test cells cannot influence adapted weights.
  - Leakage test (§6): two adaptations with SAME seed — one original panel, one
    corrupted — must yield bit-identical parameters (since test cells are zeroed by
    support_mask in _build_temporal_features).
  - Mask disjointness assertions added.

Protocol:
  - TEMPORAL_MASKED_NLL_CLAMPED@75 checkpoint
  - novel_lag2 scenario, 3 seeds, mcar_30
  - k_frac=0.05 (5%), support_seed=42
  - ADAPT_SEED=12345 (fixed before results, not tuned)
"""

from __future__ import annotations

import copy
import dataclasses
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from src.data.synthetic.generate_herald_synthetic import generate_dataset
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.evaluate_imputation import compute_imputation_metrics
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS
from src.modeles.synthetic.phase11_generalization.trainer import (
    checkpoint_hash,
    load_checkpoint,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase12_few_shot.splits import (
    make_temporal_splits,
    make_fewshot_support_mask,
    make_eval_masks,
)
from src.modeles.synthetic.phase12_few_shot.adaptation_trainer import (
    adapt_model,
    _set_adapt_seed,
)
from src.modeles.synthetic.phase12_few_shot.adapter import apply_strategy_freeze


# ── Frozen constants (set before any results, DEC-051) ────────────────────────
AUDIT_SCENARIO = "novel_lag2"
AUDIT_SEEDS = [1000, 2000, 3000]
AUDIT_MASK_KEY = "mcar_30"
AUDIT_K_FRAC = 0.05
AUDIT_SUPPORT_SEED = 42
AUDIT_N_ADAPT_EPOCHS = 50
ADAPT_SEED = 12345  # fixed seed for all adaptation calls in NT1/NT2/NT3/NT4/NT5/NT6


def _load_model(checkpoint_path: Path, device: str) -> HERALDGraphImputerLagged:
    return load_checkpoint(checkpoint_path, device)


def _model_hash(model: HERALDGraphImputerLagged) -> str:
    return checkpoint_hash(model.state_dict())


def _param_diff(model_a: HERALDGraphImputerLagged, model_b: HERALDGraphImputerLagged) -> dict:
    """Compute max/mean absolute parameter difference."""
    diffs = []
    for (na, pa), (nb, pb) in zip(
        model_a.named_parameters(), model_b.named_parameters()
    ):
        assert na == nb, f"Parameter name mismatch: {na} vs {nb}"
        diffs.append((pa.data - pb.data).abs().flatten())
    all_diffs = torch.cat(diffs)
    return {
        "max_abs_param_diff": float(all_diffs.max()),
        "mean_abs_param_diff": float(all_diffs.mean()),
    }


def _run_adaptation(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    support_mask: np.ndarray,
    val_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
    n_epochs: int = AUDIT_N_ADAPT_EPOCHS,
    adapt_seed: int = ADAPT_SEED,
) -> dict:
    """Adapt model with deterministic seed. Returns history dict."""
    apply_strategy_freeze(model, "A1")
    history = adapt_model(
        model, panel, support_mask, val_mask,
        adj_s, adj_t, n_epochs=n_epochs, lr=1e-3, patience=15,
        device=device, adapt_seed=adapt_seed,
    )
    return history


def _impute(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> np.ndarray:
    return impute_deterministic_lagged(model, panel, obs_mask, adj_s, adj_t, device)


def _mae_at_eval_cells(
    imp: np.ndarray,
    panel: np.ndarray,
    eval_mask: np.ndarray,
) -> float:
    """MAE at eval_mask==1 cells (missing test cells).

    eval_mask convention: 1 = cells to evaluate on, 0 = ignore.
    This is the OPPOSITE of compute_imputation_metrics(mask) which uses mask==0.
    """
    cells = eval_mask == 1
    if cells.sum() == 0:
        return float("nan")
    return float(np.abs(imp[cells] - panel[cells]).mean())


def _impute_and_mae(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    eval_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> float:
    """MAE at eval_mask==1 cells (convention: 1=evaluate here)."""
    imp = _impute(model, panel, obs_mask, adj_s, adj_t, device)
    return _mae_at_eval_cells(imp, panel, eval_mask)


def _build_test_eval_mask(obs_mask: np.ndarray, test_years: list[int]) -> np.ndarray:
    n_T, n_S, n_Y = obs_mask.shape
    test_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
    for y in test_years:
        test_window[:, :, y] = True
    return ((obs_mask == 0) & test_window).astype(np.int8)


def _assert_masks_disjoint(
    support_mask: np.ndarray,
    val_mask: np.ndarray,
    eval_mask: np.ndarray,
) -> None:
    """Verify that support / val / test masks are mutually disjoint."""
    assert not np.any((support_mask == 1) & (val_mask == 1)), \
        "support_mask ∩ val_mask ≠ ∅"
    assert not np.any((support_mask == 1) & (eval_mask == 1)), \
        "support_mask ∩ test_mask ≠ ∅"
    assert not np.any((val_mask == 1) & (eval_mask == 1)), \
        "val_mask ∩ test_mask ≠ ∅"


# ── NT1: Corrupt test targets ─────────────────────────────────────────────────

def nt1_corrupt_test_targets(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT1 (DEC-052 corrected semantics):

    Leakage test — two adaptations with SAME seed:
      A: original panel + support_mask → model_A
      B: corrupted panel (test cells = 9999) + support_mask → model_B
      Since support_mask zeros out test years in _build_temporal_features,
      the loss and gradients are IDENTICAL → model_A must equal model_B.

    Evaluation sensitivity test:
      Predictions from model_A (one inference pass):
        metric_orig   = MAE(predictions, panel_original,  eval_mask)
        metric_corrupt = MAE(predictions, panel_corrupted, eval_mask)
      metrics must differ (evaluation target change is visible).

    Pass criteria: hash(model_A) == hash(model_B) AND metric_orig != metric_corrupt.
    """
    results = []
    for seed in AUDIT_SEEDS:
        cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS[AUDIT_SCENARIO], seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        obs_mask = ds["masks"][AUDIT_MASK_KEY]
        adj_s, adj_t = ds["sector_adj"], ds["territory_adj"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)
        rng = np.random.default_rng(AUDIT_SUPPORT_SEED)
        support_mask, _ = make_fewshot_support_mask(obs_mask, support_years, AUDIT_K_FRAC, rng)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)
        eval_mask = _build_test_eval_mask(obs_mask, test_years)

        # Mask disjointness assertions
        _assert_masks_disjoint(support_mask, val_mask, eval_mask)

        # Corrupted panel: only test cells (where obs_mask==0 in test window) are changed
        panel_corrupted = panel.copy()
        for y in test_years:
            panel_corrupted[:, :, y] = np.where(
                obs_mask[:, :, y] == 0, 9999.0, panel[:, :, y]
            )

        # ── Leakage test: two adaptations, same seed, different panel ──────────
        model_a = _load_model(checkpoint_path, device)
        hist_a = _run_adaptation(model_a, panel, support_mask, val_mask, adj_s, adj_t, device,
                                  adapt_seed=ADAPT_SEED)

        model_b = _load_model(checkpoint_path, device)
        hist_b = _run_adaptation(model_b, panel_corrupted, support_mask, val_mask, adj_s, adj_t, device,
                                  adapt_seed=ADAPT_SEED)

        hash_a = _model_hash(model_a)
        hash_b = _model_hash(model_b)
        pdiff = _param_diff(model_a, model_b)
        same_best_epoch = hist_a.get("best_epoch") == hist_b.get("best_epoch")
        params_identical = hash_a == hash_b

        # ── Evaluation sensitivity: adapt once (model_a), evaluate twice ───────
        # Same imputed values; only the ground-truth targets differ.
        imp_a = _impute(model_a, panel, obs_mask, adj_s, adj_t, device)
        mae_orig = _mae_at_eval_cells(imp_a, panel, eval_mask)
        mae_corrupt = _mae_at_eval_cells(imp_a, panel_corrupted, eval_mask)
        metrics_differ = abs(mae_orig - mae_corrupt) > 1e-6

        results.append({
            "seed": seed,
            "adapt_seed": ADAPT_SEED,
            "same_best_epoch": same_best_epoch,
            "params_identical": params_identical,
            "hash_a": hash_a,
            "hash_b": hash_b,
            **pdiff,
            "mae_orig": mae_orig,
            "mae_corrupt": mae_corrupt,
            "metrics_differ": metrics_differ,
            "train_loss_a": hist_a.get("train_loss", []),
            "train_loss_b": hist_b.get("train_loss", []),
            "best_epoch_a": hist_a.get("best_epoch", -1),
            "best_epoch_b": hist_b.get("best_epoch", -1),
            "pass": params_identical and same_best_epoch and metrics_differ,
        })

    return {
        "test": "NT1_corrupt_test_targets",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


# ── NT2: Noisy test targets ───────────────────────────────────────────────────

def nt2_noise_test_targets(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT2 (DEC-052 corrected semantics):

    Leakage test — two adaptations with SAME seed:
      A: original panel → model_A
      B: noisy panel (test cells = i.i.d. noise) → model_B
      Hash(model_A) must equal Hash(model_B).

    Same principle as NT1: support_mask zeroes test-year values in _build_temporal_features,
    so the loss and gradients are identical regardless of test cell values in panel.
    """
    results = []
    for seed in AUDIT_SEEDS:
        cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS[AUDIT_SCENARIO], seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        obs_mask = ds["masks"][AUDIT_MASK_KEY]
        adj_s, adj_t = ds["sector_adj"], ds["territory_adj"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)
        rng = np.random.default_rng(AUDIT_SUPPORT_SEED)
        support_mask, _ = make_fewshot_support_mask(obs_mask, support_years, AUDIT_K_FRAC, rng)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)
        eval_mask = _build_test_eval_mask(obs_mask, test_years)

        _assert_masks_disjoint(support_mask, val_mask, eval_mask)

        rng_noise = np.random.default_rng(seed + 1000)
        panel_noisy = panel.copy()
        for y in test_years:
            noise = rng_noise.normal(0, 1, (n_T, n_S)).astype(np.float32)
            panel_noisy[:, :, y] = np.where(obs_mask[:, :, y] == 0, noise, panel[:, :, y])

        # Two adaptations with same seed
        model_a = _load_model(checkpoint_path, device)
        hist_a = _run_adaptation(model_a, panel, support_mask, val_mask, adj_s, adj_t, device,
                                  adapt_seed=ADAPT_SEED)

        model_b = _load_model(checkpoint_path, device)
        hist_b = _run_adaptation(model_b, panel_noisy, support_mask, val_mask, adj_s, adj_t, device,
                                  adapt_seed=ADAPT_SEED)

        hash_a = _model_hash(model_a)
        hash_b = _model_hash(model_b)
        pdiff = _param_diff(model_a, model_b)
        same_best_epoch = hist_a.get("best_epoch") == hist_b.get("best_epoch")
        params_identical = hash_a == hash_b

        results.append({
            "seed": seed,
            "adapt_seed": ADAPT_SEED,
            "same_best_epoch": same_best_epoch,
            "params_identical": params_identical,
            "hash_a": hash_a,
            "hash_b": hash_b,
            **pdiff,
            "best_epoch_a": hist_a.get("best_epoch", -1),
            "best_epoch_b": hist_b.get("best_epoch", -1),
            "train_loss_a": hist_a.get("train_loss", []),
            "train_loss_b": hist_b.get("train_loss", []),
            "pass": params_identical and same_best_epoch,
        })

    return {
        "test": "NT2_noise_test_targets",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


# ── NT3: Alter future targets ─────────────────────────────────────────────────

def nt3_alter_future_targets(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT3: Replace test targets with shifted values (+100).
    Predictions in support/val window must not change (atol=1e-5).
    Uses fixed adapt_seed for both adaptations.
    """
    results = []
    for seed in AUDIT_SEEDS:
        cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS[AUDIT_SCENARIO], seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        obs_mask = ds["masks"][AUDIT_MASK_KEY]
        adj_s, adj_t = ds["sector_adj"], ds["territory_adj"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)
        rng = np.random.default_rng(AUDIT_SUPPORT_SEED)
        support_mask, _ = make_fewshot_support_mask(obs_mask, support_years, AUDIT_K_FRAC, rng)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)

        support_eval_mask = support_mask.astype(np.int8)

        model_normal = _load_model(checkpoint_path, device)
        _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device,
                         adapt_seed=ADAPT_SEED)

        panel_future_corrupt = panel.copy()
        for y in test_years:
            panel_future_corrupt[:, :, y] = panel[:, :, y] + 100.0

        model_future = _load_model(checkpoint_path, device)
        _run_adaptation(model_future, panel_future_corrupt, support_mask, val_mask, adj_s, adj_t, device,
                         adapt_seed=ADAPT_SEED)

        imp_normal = impute_deterministic_lagged(model_normal, panel, obs_mask, adj_s, adj_t, device)
        imp_future = impute_deterministic_lagged(model_future, panel, obs_mask, adj_s, adj_t, device)

        predictions_same = np.allclose(
            imp_normal[support_eval_mask.astype(bool)],
            imp_future[support_eval_mask.astype(bool)],
            atol=1e-5,
        )

        results.append({
            "seed": seed,
            "adapt_seed": ADAPT_SEED,
            "predictions_same": predictions_same,
            "pass": predictions_same,
        })

    return {
        "test": "NT3_alter_future_targets",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


# ── NT4: Permute support labels ───────────────────────────────────────────────

def nt4_permute_support_labels(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT4: Permute support labels randomly. Few-shot gain must disappear or degrade.
    Threshold: permuted MAE >= 90% of zero-shot MAE (gain ≤ 10%).
    Uses fixed adapt_seed for all adaptations.
    """
    results = []
    for seed in AUDIT_SEEDS:
        cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS[AUDIT_SCENARIO], seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        obs_mask = ds["masks"][AUDIT_MASK_KEY]
        adj_s, adj_t = ds["sector_adj"], ds["territory_adj"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)
        rng = np.random.default_rng(AUDIT_SUPPORT_SEED)
        support_mask, _ = make_fewshot_support_mask(obs_mask, support_years, AUDIT_K_FRAC, rng)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)
        eval_mask = _build_test_eval_mask(obs_mask, test_years)
        _assert_masks_disjoint(support_mask, val_mask, eval_mask)

        model_normal = _load_model(checkpoint_path, device)
        _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device,
                         adapt_seed=ADAPT_SEED)
        mae_normal = _impute_and_mae(model_normal, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        model_zs = _load_model(checkpoint_path, device)
        mae_zero_shot = _impute_and_mae(model_zs, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        panel_permuted = panel.copy()
        support_pos = np.where(support_mask == 1)
        n_support = len(support_pos[0])
        perm_rng = np.random.default_rng(seed + 5000)
        perm_idx = perm_rng.permutation(n_support)
        support_values = panel[support_pos[0], support_pos[1], support_pos[2]]
        panel_permuted[support_pos[0], support_pos[1], support_pos[2]] = support_values[perm_idx]

        model_perm = _load_model(checkpoint_path, device)
        _run_adaptation(model_perm, panel_permuted, support_mask, val_mask, adj_s, adj_t, device,
                         adapt_seed=ADAPT_SEED)
        mae_perm = _impute_and_mae(model_perm, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        gain_correct = mae_zero_shot - mae_normal
        gain_permuted = mae_zero_shot - mae_perm
        ratio = gain_permuted / gain_correct if abs(gain_correct) > 1e-8 else 1.0
        gain_degrades = ratio < 0.5 or mae_perm >= mae_zero_shot * 0.90

        results.append({
            "seed": seed,
            "adapt_seed": ADAPT_SEED,
            "mae_zero_shot": mae_zero_shot,
            "mae_fewshot_normal": mae_normal,
            "mae_fewshot_permuted": mae_perm,
            "gain_correct": gain_correct,
            "gain_permuted": gain_permuted,
            "ratio": ratio,
            "gain_degrades": gain_degrades,
            "pass": gain_degrades,
        })

    return {
        "test": "NT4_permute_support_labels",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


# ── NT5: Empty support ────────────────────────────────────────────────────────

def nt5_empty_support(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT5: Train with empty support (k_frac=0). Must reproduce zero-shot MAE exactly.
    """
    results = []
    for seed in AUDIT_SEEDS:
        cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS[AUDIT_SCENARIO], seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        obs_mask = ds["masks"][AUDIT_MASK_KEY]
        adj_s, adj_t = ds["sector_adj"], ds["territory_adj"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)
        eval_mask = _build_test_eval_mask(obs_mask, test_years)

        model_zs = _load_model(checkpoint_path, device)
        mae_zero_shot = _impute_and_mae(model_zs, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        empty_support = np.zeros_like(obs_mask, dtype=np.float32)
        _, val_years, test_years = make_temporal_splits(n_Y)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)

        model_empty = _load_model(checkpoint_path, device)
        apply_strategy_freeze(model_empty, "A1")
        adapt_model(
            model_empty, panel, empty_support, val_mask,
            adj_s, adj_t, n_epochs=50, lr=1e-3, patience=15,
            device=device, adapt_seed=ADAPT_SEED,
        )
        mae_empty = _impute_and_mae(model_empty, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        reproduces_zs = abs(mae_empty - mae_zero_shot) < 1e-5

        results.append({
            "seed": seed,
            "adapt_seed": ADAPT_SEED,
            "mae_zero_shot": mae_zero_shot,
            "mae_empty_support": mae_empty,
            "reproduces_zs": reproduces_zs,
            "pass": reproduces_zs,
        })

    return {
        "test": "NT5_empty_support",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


# ── NT6: Random decoder ───────────────────────────────────────────────────────

def nt6_random_decoder(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT6: Use randomly re-initialized decoder. Must NOT reproduce ~80% MAE gain.
    Threshold: random-decoder few-shot MAE must be >= 80% of zero-shot MAE.
    """
    results = []
    for seed in AUDIT_SEEDS:
        cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS[AUDIT_SCENARIO], seed=seed)
        ds = generate_dataset(cfg)
        panel = ds["panel"]
        obs_mask = ds["masks"][AUDIT_MASK_KEY]
        adj_s, adj_t = ds["sector_adj"], ds["territory_adj"]
        n_T, n_S, n_Y = panel.shape

        support_years, val_years, test_years = make_temporal_splits(n_Y)
        rng = np.random.default_rng(AUDIT_SUPPORT_SEED)
        support_mask, _ = make_fewshot_support_mask(obs_mask, support_years, AUDIT_K_FRAC, rng)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)
        eval_mask = _build_test_eval_mask(obs_mask, test_years)

        model_zs = _load_model(checkpoint_path, device)
        mae_zero_shot = _impute_and_mae(model_zs, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        model_normal = _load_model(checkpoint_path, device)
        _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device,
                         adapt_seed=ADAPT_SEED)
        mae_normal_fs = _impute_and_mae(model_normal, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        model_random = _load_model(checkpoint_path, device)
        rng_reinit = torch.Generator()
        rng_reinit.manual_seed(seed + 9999)
        with torch.no_grad():
            for name, param in model_random.named_parameters():
                if "net" in name:
                    if param.dim() >= 2:
                        nn.init.xavier_uniform_(param.data, generator=rng_reinit)
                    else:
                        param.data.uniform_(-0.1, 0.1, generator=rng_reinit)

        _run_adaptation(model_random, panel, support_mask, val_mask, adj_s, adj_t, device,
                         adapt_seed=ADAPT_SEED)
        mae_random_fs = _impute_and_mae(model_random, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        gain_random = mae_zero_shot - mae_random_fs
        total = mae_zero_shot
        random_gain_fraction = gain_random / total if total > 0 else 0.0
        not_auto_reproducing = mae_random_fs >= mae_zero_shot * 0.80

        results.append({
            "seed": seed,
            "adapt_seed": ADAPT_SEED,
            "mae_zero_shot": mae_zero_shot,
            "mae_fewshot_normal": mae_normal_fs,
            "mae_fewshot_random_decoder": mae_random_fs,
            "random_gain_fraction": random_gain_fraction,
            "not_auto_reproducing": not_auto_reproducing,
            "pass": not_auto_reproducing,
        })

    return {
        "test": "NT6_random_decoder",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


# ── Run all negative tests ────────────────────────────────────────────────────

def run_all_negative_tests(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """Run all 6 negative tests. Returns dict with per-test results and overall verdict."""
    tests = {
        "NT1": nt1_corrupt_test_targets(checkpoint_path, device),
        "NT2": nt2_noise_test_targets(checkpoint_path, device),
        "NT3": nt3_alter_future_targets(checkpoint_path, device),
        "NT4": nt4_permute_support_labels(checkpoint_path, device),
        "NT5": nt5_empty_support(checkpoint_path, device),
        "NT6": nt6_random_decoder(checkpoint_path, device),
    }
    all_pass = all(t["all_pass"] for t in tests.values())
    failing = [k for k, t in tests.items() if not t["all_pass"]]

    verdict = "FEWSHOT_INTEGRITY_PASS" if all_pass else f"LEAKAGE_OR_EVALUATION_ERROR: {failing}"

    return {
        "verdict": verdict,
        "all_pass": all_pass,
        "failing_tests": failing,
        "tests": tests,
    }
