"""
functional_scenario.py — Controlled scenario where oracle must beat ffill (DEC-048 gate C2).

Design: low-AR target sector, single directed lag-1 source sector.
ffill predicts near-zero change; oracle correctly uses source sector's past.
If oracle_mae > ffill_mae in this scenario, classify as ARCHITECTURE_INADEQUATE.

Config properties:
  - n_territories=10, n_sectors=5, n_years=20
  - frac_nonlinear=0.0 (pure linear, no tanh complications)
  - frac_negative=0.0 (all positive relations — oracle knows they are amplifying)
  - ar_coef_range=(0.05, 0.15) — low AR: sector's own past matters little
  - territory_propagation=0.0 — no territory cross-talk (clean signal)
  - forced_lag=1 — single lag, clean signal
  - n_true_relations=3 (sparse — few relations, each identifiable)
  - weight_range=(0.5, 0.8) — strong weights so source matters more than AR
"""

from __future__ import annotations

import copy
import dataclasses

import numpy as np
import torch

from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    train_herald_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.imputation_baselines import ForwardFillImputer
from src.modeles.synthetic.evaluate_imputation import compute_imputation_metrics

# ── Canonical functional scenario config ─────────────────────────────────────

FUNCTIONAL_CONFIG = SyntheticConfig(
    n_territories=10,
    n_sectors=5,
    n_years=20,
    seed=9999,
    n_true_relations=3,
    weight_range=(0.5, 0.8),
    frac_nonlinear=0.0,
    frac_negative=0.0,
    ar_coef_range=(0.05, 0.15),
    territory_propagation=0.0,
    territory_radius=0.4,
    noise_sigma_range=(0.05, 0.10),
    forced_lag=1,
)


def _make_functional_dataset(seed: int = 9999) -> dict:
    """Generate a single functional scenario dataset with specified seed."""
    cfg = dataclasses.replace(FUNCTIONAL_CONFIG, seed=seed)
    return generate_dataset(cfg)


def test_oracle_vs_ffill_functional(
    device: str = "cpu",
    n_local_epochs: int = 200,
    mask_key: str = "mcar_30",
    seeds: list[int] | None = None,
) -> dict:
    """
    Train oracle model locally on functional_scenario.
    Also train a standard lagged model (M3) from scratch on the same data.

    Returns:
      {oracle_mae, ffill_mae, m3_mae, ffill_wins, n_true_relations,
       ar_coef_mean, oracle_ratio, m3_ratio, gate_c2_pass, seeds_tested}
    """
    if seeds is None:
        seeds = [9999, 9998, 9997]

    oracle_maes = []
    ffill_maes = []
    m3_maes = []

    for seed in seeds:
        ds = _make_functional_dataset(seed=seed)
        panel = ds["panel"]
        true_relations = ds["true_relations"]
        adj_s = ds["sector_adj"]
        adj_t = ds["territory_adj"]

        if mask_key not in ds["masks"]:
            # fallback to mcar_30
            mk = "mcar_30"
        else:
            mk = mask_key
        mask = ds["masks"][mk]

        n_T, n_S, n_Y = panel.shape

        # ── Forward fill (M0) ──────────────────────────────────────────────
        ffill = ForwardFillImputer().fit(panel, mask)
        imputed_ffill = ffill.transform(panel, mask)
        m_ffill = compute_imputation_metrics(panel, imputed_ffill, mask)
        ffill_maes.append(m_ffill.mae)

        # ── Oracle lagged (M4) — freeze attention, train MLP ──────────────
        oracle_model = HERALDGraphImputerLagged(n_S, n_T, hidden_dim=64, dropout=0.1)
        build_directed_oracle_lagged(oracle_model, true_relations, n_S)
        # Train only MLP (attention frozen)
        oracle_model.to(device)
        oracle_model.train()
        opt = torch.optim.Adam(
            [p for p in oracle_model.parameters() if p.requires_grad], lr=1e-3
        )
        from src.modeles.synthetic.imputation_baselines import _build_temporal_features
        from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
        panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, device)
        true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32)).to(device)
        temp_feats_t = torch.from_numpy(
            _build_temporal_features(panel, mask).astype(np.float32)
        ).to(device)

        for _ in range(n_local_epochs):
            opt.zero_grad()
            out = oracle_model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
            pred_mean = out[..., 0]
            log_sigma = out[..., 1]
            sigma_sq = (2 * log_sigma).exp().clamp(min=1e-4)
            nll = 0.5 * (2 * log_sigma + (true_t - pred_mean) ** 2 / sigma_sq)
            loss = (nll * mask_t).sum() / mask_t.sum().clamp(min=1)
            loss.backward()
            opt.step()

        imputed_oracle = impute_deterministic_lagged(oracle_model, panel, mask, adj_s, adj_t, device)
        m_oracle = compute_imputation_metrics(panel, imputed_oracle, mask)
        oracle_maes.append(m_oracle.mae)

        # ── Standard lagged (M3) — train from scratch, uniform adj ────────
        m3_model = HERALDGraphImputerLagged(n_S, n_T, hidden_dim=64, dropout=0.1)
        train_herald_lagged(m3_model, panel, mask, adj_s, adj_t,
                            n_epochs=n_local_epochs, lr=1e-3, device=device)
        imputed_m3 = impute_deterministic_lagged(m3_model, panel, mask, adj_s, adj_t, device)
        m_m3 = compute_imputation_metrics(panel, imputed_m3, mask)
        m3_maes.append(m_m3.mae)

    mean_oracle = float(np.mean(oracle_maes))
    mean_ffill = float(np.mean(ffill_maes))
    mean_m3 = float(np.mean(m3_maes))

    # Estimate mean ar_coef (from config range midpoint)
    ar_coef_mean = float(np.mean(FUNCTIONAL_CONFIG.ar_coef_range))

    gate_c2_pass = mean_oracle < mean_ffill

    return {
        "oracle_mae": mean_oracle,
        "ffill_mae": mean_ffill,
        "m3_mae": mean_m3,
        "ffill_wins": mean_ffill < mean_oracle,
        "gate_c2_pass": gate_c2_pass,
        "oracle_ratio": mean_oracle / max(mean_ffill, 1e-8),
        "m3_ratio": mean_m3 / max(mean_ffill, 1e-8),
        "n_true_relations": FUNCTIONAL_CONFIG.n_true_relations,
        "ar_coef_mean": ar_coef_mean,
        "seeds_tested": seeds,
        "oracle_maes_per_seed": oracle_maes,
        "ffill_maes_per_seed": ffill_maes,
        "m3_maes_per_seed": m3_maes,
    }
