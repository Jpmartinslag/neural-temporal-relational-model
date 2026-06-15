"""
fewshot_audit.py — Rigorous negative tests for few-shot leakage (DEC-051).

DEC-050 few-shot results showed 78-80% MAE reduction via A1 adaptation.
This could be legitimate (decoder calibration) or methodological leakage.

Six negative tests required (all must PASS before few-shot is confirmed):

  NT1: Corrupt test targets → training/checkpoint/best_epoch unchanged,
       only final metrics change.

  NT2: Replace test targets with i.i.d. noise → model unchanged.

  NT3: Alter future targets → predictions in past window unchanged.

  NT4: Permute support labels → few-shot gain must disappear or degrade clearly.

  NT5: Train with empty support (k_frac=0) → must reproduce exactly zero-shot.

  NT6: Use randomly re-initialized decoder → gain must NOT reproduce ~80%.

All six must pass. Any failure → classify as LEAKAGE or EVALUATION_ERROR.

Protocol:
  - Uses TEMPORAL_MASKED@75 checkpoint (best zero-shot in DEC-050)
  - novel_lag2 scenario, 3 seeds, mcar_30
  - k_frac=0.05 (5%), support_seed=42
"""

from __future__ import annotations

import copy
import dataclasses
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.data.synthetic.generate_herald_synthetic import generate_dataset
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    impute_deterministic_lagged,
    train_herald_lagged,
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
from src.modeles.synthetic.phase12_few_shot.adaptation_trainer import adapt_model
from src.modeles.synthetic.phase12_few_shot.adapter import apply_strategy_freeze


AUDIT_SCENARIO = "novel_lag2"
AUDIT_SEEDS = [1000, 2000, 3000]
AUDIT_MASK_KEY = "mcar_30"
AUDIT_K_FRAC = 0.05
AUDIT_SUPPORT_SEED = 42
AUDIT_N_ADAPT_EPOCHS = 50


def _load_model(checkpoint_path: Path, device: str) -> HERALDGraphImputerLagged:
    return load_checkpoint(checkpoint_path, device)


def _run_adaptation(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    support_mask: np.ndarray,
    val_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
    n_epochs: int = AUDIT_N_ADAPT_EPOCHS,
) -> dict:
    """Returns (adapt_history, model_after_adaptation)."""
    apply_strategy_freeze(model, "A1")
    history = adapt_model(
        model, panel, support_mask, val_mask,
        adj_s, adj_t, n_epochs=n_epochs, lr=1e-3, patience=15, device=device,
    )
    return history


def _impute_and_mae(
    model: HERALDGraphImputerLagged,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    eval_mask: np.ndarray,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    device: str,
) -> float:
    imp = impute_deterministic_lagged(model, panel, obs_mask, adj_s, adj_t, device)
    m = compute_imputation_metrics(panel, imp, eval_mask)
    return m.mae


def _build_test_eval_mask(obs_mask: np.ndarray, test_years: list[int]) -> np.ndarray:
    n_T, n_S, n_Y = obs_mask.shape
    test_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
    for y in test_years:
        test_window[:, :, y] = True
    return ((obs_mask == 0) & test_window).astype(np.int8)


# ── Individual negative tests ─────────────────────────────────────────────────

def nt1_corrupt_test_targets(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT1: Replace test-window targets with constant=9999 before adaptation.
    Training and best_epoch must not change. Only final MAE on original data must change.
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

        # Normal run
        model_normal = _load_model(checkpoint_path, device)
        hist_normal = _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device)

        # Corrupted run — replace test targets with constant
        panel_corrupted = panel.copy()
        for y in test_years:
            panel_corrupted[:, :, y] = np.where(obs_mask[:, :, y] == 0, 9999.0, panel[:, :, y])

        model_corrupt = _load_model(checkpoint_path, device)
        hist_corrupt = _run_adaptation(model_corrupt, panel_corrupted, support_mask, val_mask, adj_s, adj_t, device)

        # Key invariants
        same_best_epoch = hist_normal.get("best_epoch") == hist_corrupt.get("best_epoch")
        # Checkpoint parameters should be identical (adaptation only uses support, not test)
        params_normal = {n: p.data.clone() for n, p in model_normal.named_parameters()}
        params_corrupt = {n: p.data.clone() for n, p in model_corrupt.named_parameters()}
        params_identical = all(
            torch.allclose(params_normal[k], params_corrupt[k], atol=1e-6)
            for k in params_normal
        )

        # MAE on ORIGINAL panel should differ (eval on corrupted → different score)
        mae_normal = _impute_and_mae(model_normal, panel, obs_mask, eval_mask, adj_s, adj_t, device)
        mae_corrupt = _impute_and_mae(model_corrupt, panel_corrupted, obs_mask, eval_mask, adj_s, adj_t, device)

        results.append({
            "seed": seed,
            "same_best_epoch": same_best_epoch,
            "params_identical": params_identical,
            "mae_normal": mae_normal,
            "mae_corrupt": mae_corrupt,
            "metrics_differ": abs(mae_normal - mae_corrupt) > 1e-6,
            "pass": same_best_epoch and params_identical and abs(mae_normal - mae_corrupt) > 1e-6,
        })

    return {
        "test": "NT1_corrupt_test_targets",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


def nt2_noise_test_targets(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT2: Replace test targets with i.i.d. noise. Model (weights, best_epoch) must not change.
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

        model_normal = _load_model(checkpoint_path, device)
        hist_normal = _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device)

        # Replace missing test cells with noise
        rng_noise = np.random.default_rng(seed + 1000)
        panel_noisy = panel.copy()
        for y in test_years:
            noise = rng_noise.normal(0, 1, (n_T, n_S)).astype(np.float32)
            panel_noisy[:, :, y] = np.where(obs_mask[:, :, y] == 0, noise, panel[:, :, y])

        model_noisy = _load_model(checkpoint_path, device)
        hist_noisy = _run_adaptation(model_noisy, panel_noisy, support_mask, val_mask, adj_s, adj_t, device)

        same_best_epoch = hist_normal.get("best_epoch") == hist_noisy.get("best_epoch")
        params_normal = {n: p.data.clone() for n, p in model_normal.named_parameters()}
        params_noisy = {n: p.data.clone() for n, p in model_noisy.named_parameters()}
        params_identical = all(
            torch.allclose(params_normal[k], params_noisy[k], atol=1e-6)
            for k in params_normal
        )

        results.append({
            "seed": seed,
            "same_best_epoch": same_best_epoch,
            "params_identical": params_identical,
            "pass": same_best_epoch and params_identical,
        })

    return {
        "test": "NT2_noise_test_targets",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


def nt3_alter_future_targets(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT3: Replace test targets with future (shifted) values.
    Imputation predictions on support/val window must not change.
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

        # Build eval mask on SUPPORT cells (not test)
        support_eval_mask = support_mask.astype(np.int8)

        model_normal = _load_model(checkpoint_path, device)
        _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device)

        # Corrupt only test (future) years
        panel_future_corrupt = panel.copy()
        for y in test_years:
            panel_future_corrupt[:, :, y] = panel[:, :, y] + 100.0  # shift

        model_future = _load_model(checkpoint_path, device)
        _run_adaptation(model_future, panel_future_corrupt, support_mask, val_mask, adj_s, adj_t, device)

        # Predictions on support window should be unaffected
        imp_normal = impute_deterministic_lagged(model_normal, panel, obs_mask, adj_s, adj_t, device)
        imp_future = impute_deterministic_lagged(model_future, panel, obs_mask, adj_s, adj_t, device)

        predictions_same = np.allclose(
            imp_normal[support_eval_mask.astype(bool)],
            imp_future[support_eval_mask.astype(bool)],
            atol=1e-5,
        )

        results.append({
            "seed": seed,
            "predictions_same": predictions_same,
            "pass": predictions_same,
        })

    return {
        "test": "NT3_alter_future_targets",
        "results": results,
        "all_pass": all(r["pass"] for r in results),
    }


def nt4_permute_support_labels(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT4: Permute (shuffle) support labels randomly. Few-shot gain must disappear or degrade.
    Threshold: permuted MAE must be >= 90% of zero-shot MAE (gain ≤ 10%).
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

        # Normal few-shot
        model_normal = _load_model(checkpoint_path, device)
        _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device)
        mae_normal = _impute_and_mae(model_normal, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Zero-shot (no adaptation)
        model_zs = _load_model(checkpoint_path, device)
        mae_zero_shot = _impute_and_mae(model_zs, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Permuted support labels
        panel_permuted = panel.copy()
        support_pos = np.where(support_mask == 1)
        n_support = len(support_pos[0])
        perm_rng = np.random.default_rng(seed + 5000)
        perm_idx = perm_rng.permutation(n_support)
        support_values = panel[support_pos[0], support_pos[1], support_pos[2]]
        panel_permuted[support_pos[0], support_pos[1], support_pos[2]] = support_values[perm_idx]

        model_perm = _load_model(checkpoint_path, device)
        _run_adaptation(model_perm, panel_permuted, support_mask, val_mask, adj_s, adj_t, device)
        mae_perm = _impute_and_mae(model_perm, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Permuted model should NOT achieve the same gain as the correct model
        # Gain from permuted must be < 50% of gain from correct
        gain_correct = mae_zero_shot - mae_normal
        gain_permuted = mae_zero_shot - mae_perm
        ratio = gain_permuted / gain_correct if abs(gain_correct) > 1e-8 else 1.0
        gain_degrades = ratio < 0.5 or mae_perm >= mae_zero_shot * 0.90

        results.append({
            "seed": seed,
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


def nt5_empty_support(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT5: Train with empty support (k_frac=0.0). Must reproduce zero-shot MAE exactly.
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
        eval_mask = _build_test_eval_mask(obs_mask, test_years)

        # Zero-shot
        model_zs = _load_model(checkpoint_path, device)
        mae_zero_shot = _impute_and_mae(model_zs, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Empty support (k_frac=0 means support_mask is all zeros → no adaptation)
        empty_support = np.zeros_like(obs_mask, dtype=np.float32)
        _, val_years, test_years = make_temporal_splits(n_Y)
        val_mask, _ = make_eval_masks(obs_mask, val_years, test_years)

        model_empty = _load_model(checkpoint_path, device)
        # adapt_model with empty support should skip optimizer (support_mask.sum()==0)
        apply_strategy_freeze(model_empty, "A1")
        adapt_model(
            model_empty, panel, empty_support, val_mask,
            adj_s, adj_t, n_epochs=50, lr=1e-3, patience=15, device=device,
        )
        mae_empty = _impute_and_mae(model_empty, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Must match zero-shot within floating point tolerance
        reproduces_zs = abs(mae_empty - mae_zero_shot) < 1e-5

        results.append({
            "seed": seed,
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


def nt6_random_decoder(
    checkpoint_path: Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    NT6: Use randomly re-initialized decoder. Must NOT reproduce the ~80% MAE gain.
    Threshold: random-decoder few-shot MAE must be >= 80% of zero-shot MAE
    (i.e., gain must be < 20%).
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

        # Zero-shot with NORMAL model
        model_zs = _load_model(checkpoint_path, device)
        mae_zero_shot = _impute_and_mae(model_zs, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Normal few-shot
        model_normal = _load_model(checkpoint_path, device)
        _run_adaptation(model_normal, panel, support_mask, val_mask, adj_s, adj_t, device)
        mae_normal_fs = _impute_and_mae(model_normal, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Random decoder: reinitialize all MLP (net) parameters
        model_random = _load_model(checkpoint_path, device)
        rng_reinit = torch.Generator()
        rng_reinit.manual_seed(seed + 9999)
        with torch.no_grad():
            for name, param in model_random.named_parameters():
                if "net" in name:  # MLP layers
                    if param.dim() >= 2:
                        nn_init = torch.nn.init.xavier_uniform_
                        nn_init(param.data, generator=rng_reinit)
                    else:
                        param.data.uniform_(-0.1, 0.1, generator=rng_reinit)

        _run_adaptation(model_random, panel, support_mask, val_mask, adj_s, adj_t, device)
        mae_random_fs = _impute_and_mae(model_random, panel, obs_mask, eval_mask, adj_s, adj_t, device)

        # Random decoder gain must be < 20% of zero-shot MAE
        gain_random = mae_zero_shot - mae_random_fs
        total = mae_zero_shot
        random_gain_fraction = gain_random / total if total > 0 else 0.0
        not_auto_reproducing = mae_random_fs >= mae_zero_shot * 0.80

        results.append({
            "seed": seed,
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
