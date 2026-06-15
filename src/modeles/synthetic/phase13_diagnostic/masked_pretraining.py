"""
masked_pretraining.py — Masked pretraining variants for DEC-048.

Three variants:
  NO_PRETRAINING: use Phase 11 T2 checkpoint directly (no pretraining)
  TEMPORAL_MASKED: train on temporal masked reconstruction only
  GRAPH_MASKED_MULTITASK: train with NLL + edge presence binary CE (L2 objective)

Pretraining datasets: D2 distribution (frac_nonlinear ∈ [0, 0.90]),
seeds 200-299 — disjoint from TEST_SEEDS [1000-5000] and benchmark seeds.

Key constraint: Only synthetic data has edge ground truth.
Do NOT claim this supervision is available for real country data (PT/IT/FR/NL/AT).
"""

from __future__ import annotations

import copy
import dataclasses
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.imputation_baselines import _build_temporal_features
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
)
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS
from src.modeles.synthetic.phase11_generalization.trainer import (
    _compute_nll_loss,
    checkpoint_hash,
)
from src.modeles.synthetic.phase13_diagnostic.ofat_runner import (
    compute_multitask_loss,
    MULTITASK_ALPHA,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)

# ── Constants ─────────────────────────────────────────────────────────────────

PRETRAIN_VARIANTS = ["NO_PRETRAINING", "TEMPORAL_MASKED", "GRAPH_MASKED_MULTITASK"]

# Pretrain seeds — disjoint from TEST_SEEDS [1000-5000]
PRETRAIN_SEEDS_START = 200
PRETRAIN_SEEDS_END = 300  # exclusive


def _seeds_disjoint_from_test(seeds: list[int]) -> bool:
    """Assert none of the seeds are in TEST_SEEDS [1000-5000]."""
    test_seeds_range = set(range(1000, 5001))
    return not bool(set(seeds) & test_seeds_range)


# ── Dataset generation ────────────────────────────────────────────────────────

def generate_d2_pretrain_datasets(
    n_datasets: int,
    seeds_start: int = PRETRAIN_SEEDS_START,
    mask_keys: list[str] = ("mcar_30", "block_30"),
) -> list[dict]:
    """
    Generate n_datasets with frac_nonlinear ∈ [0, 0.9].
    Seeds in [seeds_start, seeds_start + n_datasets) — disjoint from [1000-5000].
    Does NOT copy novel_lag2 (forced_lag=2) or novel_highvar (structural_break=8) configs.
    """
    seeds = list(range(seeds_start, seeds_start + n_datasets))
    assert _seeds_disjoint_from_test(seeds), f"Pretrain seeds overlap TEST_SEEDS: {seeds}"

    rng = np.random.default_rng(42 + seeds_start)
    entries = []

    for seed in seeds:
        frac_nl = float(rng.uniform(0.0, 0.90))
        # Vary parameters — avoid exact novel_lag2/novel_highvar configs
        t_radius = float(rng.uniform(0.28, 0.38))  # avoids 0.25 and 0.42
        terr_prop = float(rng.uniform(0.10, 0.22))  # avoids 0.28

        cfg = SyntheticConfig(
            n_territories=30, n_sectors=9, n_years=20,
            seed=seed,
            n_true_relations=8,
            frac_nonlinear=frac_nl,
            frac_negative=float(rng.uniform(0.30, 0.50)),
            noise_sigma_range=(0.08, 0.25),
            ar_coef_range=(0.25, 0.60),
            territory_propagation=terr_prop,
            territory_radius=t_radius,
            forced_lag=None,  # NOT forced_lag=2 (that is novel_lag2)
            structural_break_year=None,  # NOT 8 (that is novel_highvar)
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
                    "scenario": f"d2_pretrain_frac_nl_{frac_nl:.2f}",
                    "seed": seed,
                    "mask_key": mk,
                    "frac_nonlinear": frac_nl,
                })

    return entries


def _build_pretrain_val_entries() -> list[dict]:
    """Validation subset for pretraining early stopping."""
    from src.data.synthetic.generate_herald_synthetic import BENCHMARK_SCENARIOS
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


# ── Pretraining implementations ───────────────────────────────────────────────

def pretrain_model(
    variant: str,
    n_datasets: int = 25,
    n_epochs: int = 200,
    patience: int = 20,
    device: str = "cpu",
    lr: float = 1e-3,
) -> tuple[HERALDGraphImputerLagged, dict]:
    """
    Pretrain a fresh HERALDGraphImputerLagged with specified variant.

    variant:
      "TEMPORAL_MASKED"       — MCAR 40-60% masked NLL reconstruction
      "GRAPH_MASKED_MULTITASK" — NLL + edge presence BCE (alpha=0.1 frozen)

    Returns (pretrained_model, history_dict).

    NOTE: edge ground truth ONLY EXISTS IN SYNTHETIC DATA.
    Do NOT apply GRAPH_MASKED_MULTITASK to real country data (PT/IT/FR/NL/AT).
    """
    if variant not in ("TEMPORAL_MASKED", "GRAPH_MASKED_MULTITASK"):
        raise ValueError(f"variant must be 'TEMPORAL_MASKED' or 'GRAPH_MASKED_MULTITASK', got {variant!r}")

    pretrain_entries = generate_d2_pretrain_datasets(n_datasets)
    val_entries = _build_pretrain_val_entries()

    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    rng = np.random.default_rng(99)
    best_val = float("inf")
    best_state = None
    no_improve = 0
    train_losses = []
    val_losses = []
    best_epoch = 0

    for epoch in range(n_epochs):
        model.train()
        order = rng.permutation(len(pretrain_entries))
        ep_loss = 0.0

        for idx in order:
            e = pretrain_entries[int(idx)]
            opt.zero_grad()

            if variant == "TEMPORAL_MASKED":
                # Apply extra MCAR 40-60% masking on observed cells
                extra_rate = float(rng.uniform(0.40, 0.60))
                obs_idx = np.argwhere(e["mask"] == 1)
                n_extra = max(0, round(len(obs_idx) * extra_rate))
                if n_extra > 0:
                    chosen = rng.choice(len(obs_idx), size=n_extra, replace=False)
                    masked_mask = e["mask"].copy()
                    for i in chosen:
                        t_, s_, y_ = obs_idx[i]
                        masked_mask[t_, s_, y_] = 0
                else:
                    masked_mask = e["mask"]
                loss = _compute_nll_loss(model, e["panel"], masked_mask,
                                          e["adj_s"], e["adj_t"], device)

            elif variant == "GRAPH_MASKED_MULTITASK":
                loss = compute_multitask_loss(
                    model, e["panel"], e["mask"], e["adj_s"], e["adj_t"],
                    e["true_relations"], N_SECTORS, device,
                    alpha=MULTITASK_ALPHA, include_sign=False, include_lag=False,
                )

            loss.backward()
            opt.step()
            ep_loss += float(loss)

        train_losses.append(ep_loss / max(len(pretrain_entries), 1))

        # Validation
        model.eval()
        with torch.no_grad():
            vl = [
                float(_compute_nll_loss(model, v["panel"], v["mask"],
                                         v["adj_s"], v["adj_t"], device))
                for v in val_entries
            ]
        val_loss = float(np.mean(vl))
        val_losses.append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = copy.deepcopy(model.state_dict())
            no_improve = 0
            best_epoch = epoch
        else:
            no_improve += 1
        if no_improve >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    history = {
        "variant": variant,
        "n_datasets": n_datasets,
        "n_epochs_run": len(train_losses),
        "best_epoch": best_epoch,
        "best_val_loss": float(best_val),
        "train_losses": train_losses,
        "val_losses": val_losses,
        "checkpoint_hash": checkpoint_hash(model.state_dict()),
    }
    return model, history


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_pretrained(
    model: HERALDGraphImputerLagged,
    scenario_name: str,
    test_seeds: list[int],
    test_mask_keys: list[str],
    device: str = "cpu",
) -> list[dict]:
    """
    Zero-shot evaluation after pretraining.
    Returns records with mae, edge_auc.
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

        for mk in test_mask_keys:
            if mk not in ds["masks"]:
                continue
            mask = ds["masks"][mk]

            imputed = impute_deterministic_lagged(model, panel, mask, adj_s, adj_t, device)
            m = compute_imputation_metrics(panel, imputed, mask)
            learned_attn = model.get_sector_attention()
            e = compute_edge_recovery_metrics(true_relations, N_SECTORS, learned_attn)

            records.append({
                "scenario": scenario_name,
                "seed": seed,
                "mask_key": mk,
                "mae": m.mae,
                "rmse": m.rmse,
                "edge_auc": e.auc,
                "edge_precision_at_k": e.precision_at_k,
                "n_evaluated": m.n_evaluated,
            })
    return records


# ── Full pretraining comparison ───────────────────────────────────────────────

def run_pretraining_comparison(
    n_datasets: int = 25,
    n_pretrain_epochs: int = 200,
    patience: int = 20,
    test_seeds: list[int] | None = None,
    test_mask_keys: list[str] | None = None,
    device: str = "cpu",
    base_checkpoint_path: Path | None = None,
) -> list[dict]:
    """
    Compare all 3 pretraining variants on novel_lag2 zero-shot.
    Returns list of records with variant, scenario, seed, mask_key, mae, edge_auc.
    """
    if test_seeds is None:
        test_seeds = [1000, 2000, 3000]
    if test_mask_keys is None:
        test_mask_keys = ["mcar_30", "block_30"]

    all_records = []

    # ── NO_PRETRAINING: use base checkpoint or fresh model ─────────────────
    if base_checkpoint_path is not None and base_checkpoint_path.exists():
        from src.modeles.synthetic.phase11_generalization.trainer import load_checkpoint
        no_pretrain_model = load_checkpoint(base_checkpoint_path, device=device)
        base_hash = checkpoint_hash(no_pretrain_model.state_dict())
    else:
        # Train a fresh T2 model as baseline
        from src.modeles.synthetic.phase11_generalization.trainer import (
            make_train_entries, make_val_entries, train_multi_dataset,
            PILOT_TRAIN_SEEDS, PILOT_VAL_SEEDS,
        )
        train_entries = make_train_entries("T2", PILOT_TRAIN_SEEDS)
        val_entries = make_val_entries(PILOT_VAL_SEEDS)
        no_pretrain_model, _ = train_multi_dataset(
            train_entries, val_entries, n_epochs=30, patience=5, device=device, seed=7,
        )
        base_hash = checkpoint_hash(no_pretrain_model.state_dict())

    recs_no_pretrain = evaluate_pretrained(
        no_pretrain_model, "novel_lag2", test_seeds, test_mask_keys, device
    )
    for r in recs_no_pretrain:
        r["variant"] = "NO_PRETRAINING"
        r["checkpoint_hash"] = base_hash
        r["n_pretrain_datasets"] = 0
    all_records.extend(recs_no_pretrain)

    # ── TEMPORAL_MASKED and GRAPH_MASKED_MULTITASK ─────────────────────────
    for variant in ["TEMPORAL_MASKED", "GRAPH_MASKED_MULTITASK"]:
        model, history = pretrain_model(
            variant, n_datasets=n_datasets,
            n_epochs=n_pretrain_epochs, patience=patience,
            device=device,
        )
        pretrain_hash = history["checkpoint_hash"]

        # Verify hash differs from base (pretraining changed the model)
        hash_differs = pretrain_hash != base_hash

        recs = evaluate_pretrained(model, "novel_lag2", test_seeds, test_mask_keys, device)
        for r in recs:
            r["variant"] = variant
            r["checkpoint_hash"] = pretrain_hash
            r["n_pretrain_datasets"] = n_datasets
            r["n_pretrain_epochs"] = history["n_epochs_run"]
            r["best_pretrain_epoch"] = history["best_epoch"]
            r["hash_differs_from_base"] = hash_differs
        all_records.extend(recs)

    return all_records
