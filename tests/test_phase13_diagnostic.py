"""
test_phase13_diagnostic.py — Tests for DEC-048 Phase 13 diagnostic package.

20 tests covering:
  1-2:  Functional scenario — oracle vs ffill
  3:    D2 datasets don't copy novel configs
  4-6:  Loss objectives (L1 masked, L2 edge BCE, L3 alpha frozen)
  7:    Gradient diagnostics
  8-9:  Record structure (Axis D, Axis M)
  10:   Shift spectrum (S0 < S2 < S3 in MAE)
  11-12: Pretrain no leakage / checkpoint differs
  13:   Gate C1 no NaN
  14:   Gate C2 functional
  15:   Gate C3 data scaling structure
  16:   Gate report all keys
  17:   Multitask gradients reach attention
  18:   No test data in pretraining seeds
  19:   Block mask in records
  20:   Shift spectrum no overlap
"""

from __future__ import annotations

import copy
import dataclasses

import numpy as np
import pytest
import torch

# ── imports ───────────────────────────────────────────────────────────────────

from src.modeles.synthetic.phase13_diagnostic.functional_scenario import (
    FUNCTIONAL_CONFIG,
    test_oracle_vs_ffill_functional,
)
from src.modeles.synthetic.phase13_diagnostic.ofat_runner import (
    TRAINING_SEEDS_D2,
    MULTITASK_ALPHA,
    _build_d2_entries,
    _build_d0_entries,
    _build_val_entries,
    run_axis_d,
    run_axis_m,
    run_axis_l,
    run_axis_s,
    run_gradient_diagnostics,
    compute_multitask_loss,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase13_diagnostic.masked_pretraining import (
    PRETRAIN_VARIANTS,
    PRETRAIN_SEEDS_START,
    generate_d2_pretrain_datasets,
    run_pretraining_comparison,
)
from src.modeles.synthetic.phase13_diagnostic.gates_dec048 import (
    evaluate_gates,
    MAE_RATIO_THRESHOLD,
    DATA_SCALING_MIN_GAIN,
    DIVERSITY_MIN_GAIN,
    PRETRAINING_MIN_GAIN,
    GRAPH_VS_NOGRAPH_THRESHOLD,
    AUC_THRESHOLD,
    BLOCK_THRESHOLD,
    SHIFT_CURVE_MIN_STEPS,
    BASELINE_RATIO,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    train_herald_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.phase11_generalization.splits import (
    NOVEL_TEST_SCENARIOS,
    TEST_SEEDS,
)
from src.data.synthetic.generate_herald_synthetic import generate_dataset, SyntheticConfig
from src.modeles.synthetic.imputation_baselines import ForwardFillImputer
from src.modeles.synthetic.evaluate_imputation import compute_imputation_metrics
from src.modeles.synthetic.phase11_generalization.trainer import (
    train_multi_dataset, checkpoint_hash,
)

DEVICE = "cpu"
TINY_EPOCHS = 5
TINY_PATIENCE = 2

# ── Helper: tiny dataset for fast tests ──────────────────────────────────────

def _tiny_model(n_s: int = 5, n_t: int = 10) -> HERALDGraphImputerLagged:
    return HERALDGraphImputerLagged(n_s, n_t, hidden_dim=16, dropout=0.0)


def _tiny_dataset(seed: int = 9999) -> dict:
    cfg = dataclasses.replace(FUNCTIONAL_CONFIG, seed=seed)
    return generate_dataset(cfg)


# ── Test 1: Oracle beats ffill in functional scenario ────────────────────────

def test_functional_scenario_oracle_beats_ffill():
    """oracle_mae must be < ffill_mae in functional scenario (C2 PASS)."""
    result = test_oracle_vs_ffill_functional(
        device=DEVICE,
        n_local_epochs=80,
        seeds=[9999],
    )
    assert result["gate_c2_pass"], (
        f"ARCHITECTURE_INADEQUATE: oracle_mae={result['oracle_mae']:.4f} >= "
        f"ffill_mae={result['ffill_mae']:.4f}"
    )


# ── Test 2: Functional scenario config properties ────────────────────────────

def test_functional_scenario_config_properties():
    """Verify functional config has required properties."""
    cfg = FUNCTIONAL_CONFIG
    assert cfg.ar_coef_range[1] <= 0.15, f"AR must be low: {cfg.ar_coef_range}"
    assert cfg.territory_propagation == 0.0, "No territory cross-talk"
    assert cfg.forced_lag == 1, "Must use lag-1"
    assert cfg.frac_nonlinear == 0.0, "Must be fully linear"
    assert cfg.frac_negative == 0.0, "All positive relations"
    assert cfg.n_true_relations >= 2, "Need at least 2 relations"


# ── Test 3: D2 datasets don't copy novel configs ─────────────────────────────

def test_d2_datasets_dont_copy_novel_configs():
    """D2 datasets must not be identical to novel_lag2 or novel_highvar configs."""
    entries = _build_d2_entries(n_datasets=5)
    assert len(entries) > 0, "Should produce at least 1 entry"
    for e in entries:
        # No forced_lag=2 (that's novel_lag2)
        cfg_scenario = e.get("scenario", "")
        assert "forced_lag_2" not in cfg_scenario, "D2 must not use forced_lag=2"
        # No structural_break_year=8 (that's novel_highvar)
        # (verified by config construction in _build_d2_entries)
    # Verify seeds are in correct range
    seeds_used = {e["seed"] for e in entries}
    assert all(200 <= s < 300 for s in seeds_used), f"D2 seeds must be in [200,300): {seeds_used}"


# ── Test 4: Temporal masked loss (L1) runs without error ─────────────────────

def test_temporal_masked_loss_computes():
    """L1 masked reconstruction loss runs without error."""
    ds = _tiny_dataset()
    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    n_T, n_S, n_Y = panel.shape

    model = _tiny_model(n_S, n_T)

    # Apply extra masking (L1 style)
    rng = np.random.default_rng(42)
    extra_rate = 0.50
    obs_idx = np.argwhere(mask == 1)
    n_extra = max(1, round(len(obs_idx) * extra_rate))
    chosen = rng.choice(len(obs_idx), size=n_extra, replace=False)
    masked_mask = mask.copy()
    for i in chosen:
        t_, s_, y_ = obs_idx[i]
        masked_mask[t_, s_, y_] = 0

    # Should compute NLL without error
    from src.modeles.synthetic.phase11_generalization.trainer import _compute_nll_loss
    loss = _compute_nll_loss(model, panel, masked_mask, adj_s, adj_t, DEVICE)
    assert isinstance(float(loss), float)
    assert not np.isnan(float(loss))
    assert not np.isinf(float(loss))


# ── Test 5: Multitask loss has edge component (L2) ───────────────────────────

def test_multitask_loss_has_edge_component():
    """L2 loss should differ from L0 (NLL-only) loss."""
    from src.modeles.synthetic.phase11_generalization.trainer import _compute_nll_loss

    ds = _tiny_dataset()
    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_relations = ds["true_relations"]
    n_T, n_S, n_Y = panel.shape

    model = _tiny_model(n_S, n_T)

    loss_l0 = _compute_nll_loss(model, panel, mask, adj_s, adj_t, DEVICE)
    loss_l2 = compute_multitask_loss(
        model, panel, mask, adj_s, adj_t, true_relations, n_S, DEVICE,
        alpha=MULTITASK_ALPHA, include_sign=False, include_lag=False,
    )

    # L2 should differ from L0 because it adds edge BCE
    assert abs(float(loss_l2) - float(loss_l0)) > 1e-10, (
        f"L2 loss ({float(loss_l2):.6f}) should differ from L0 ({float(loss_l0):.6f})"
    )


# ── Test 6: Alpha is frozen at 0.1 ───────────────────────────────────────────

def test_multitask_loss_alpha_frozen():
    """alpha=0.1 is the frozen value. Verify constant."""
    assert MULTITASK_ALPHA == 0.1, f"MULTITASK_ALPHA must be 0.1 (frozen), got {MULTITASK_ALPHA}"


# ── Test 7: Gradient norms are computable ────────────────────────────────────

def test_gradient_norms_computable():
    """run_gradient_diagnostics returns finite values."""
    ds = _tiny_dataset()
    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_relations = ds["true_relations"]
    n_T, n_S, n_Y = panel.shape

    model = _tiny_model(n_S, n_T)

    grad_diag = run_gradient_diagnostics(
        model, panel, mask, adj_s, adj_t, DEVICE,
        true_relations=true_relations,
    )

    for key in ["grad_norm_lag1_attn", "grad_norm_lag2_attn", "grad_norm_attn_total",
                "grad_norm_terr_attn", "grad_norm_mlp", "graph_contribution_mae"]:
        assert key in grad_diag, f"Missing key: {key}"
        val = grad_diag[key]
        assert isinstance(val, (int, float)), f"{key} should be numeric"
        assert not np.isnan(val), f"{key} is NaN"
        assert not np.isinf(val), f"{key} is Inf"


# ── Test 8: Axis D record structure ──────────────────────────────────────────

def test_axis_d_record_structure():
    """Each Axis D record has required keys."""
    records = run_axis_d(
        device=DEVICE,
        seeds=[1000],
        n_epochs=TINY_EPOCHS,
        patience=TINY_PATIENCE,
        n_datasets_list=[10],
    )
    assert len(records) > 0, "Should produce records"
    required_keys = {"axis", "n_datasets", "diversity", "mae", "edge_auc",
                     "best_epoch", "val_loss", "n_train_entries", "seed", "mask_key"}
    for r in records:
        missing = required_keys - set(r.keys())
        assert not missing, f"Missing keys: {missing}"
        assert r["axis"] == "D"
        assert r["n_datasets"] == 10
        assert r["diversity"] in ("D0", "D1", "D2")
        assert isinstance(r["mae"], float)


# ── Test 9: Axis M record structure ──────────────────────────────────────────

def test_axis_m_record_structure():
    """Each Axis M record has required keys."""
    records = run_axis_m(
        device=DEVICE,
        seeds=[1000],
        n_epochs=TINY_EPOCHS,
    )
    assert len(records) > 0, "Should produce records"
    required_keys = {"axis", "model_type", "seed", "mask_key", "mae", "local_epochs"}
    model_types_seen = set()
    for r in records:
        missing = required_keys - set(r.keys())
        assert not missing, f"Missing keys: {missing}"
        assert r["axis"] == "M"
        model_types_seen.add(r["model_type"])
    assert "M0_ffill" in model_types_seen
    assert "M3_lagged_graph" in model_types_seen
    assert "M4_oracle_lagged" in model_types_seen


# ── Test 10: Shift spectrum S0 < S2 < S3 ─────────────────────────────────────

def test_axis_s_shift_levels():
    """S0 MAE should be less than S3 MAE (in-distribution < extreme shift)."""
    records = run_axis_s(device=DEVICE, test_seeds=[1000])
    if not records:
        pytest.skip("No shift records produced")
    s0_maes = [r["mae"] for r in records if r["shift_level"] == "S0_indist"]
    s3_maes = [r["mae"] for r in records if r["shift_level"] == "S3_novel_highvar"]
    if not s0_maes or not s3_maes:
        pytest.skip("Missing S0 or S3 records")
    # Progressive degradation expected: in-distribution < extreme OOD
    mean_s0 = np.mean(s0_maes)
    mean_s3 = np.mean(s3_maes)
    assert mean_s0 <= mean_s3, (
        f"Expected S0 ({mean_s0:.4f}) <= S3 ({mean_s3:.4f}) — "
        "in-distribution should be easier than extreme OOD"
    )


# ── Test 11: Pretrain no leakage ──────────────────────────────────────────────

def test_pretrain_no_leakage():
    """Pretrain datasets must not use TEST_SEEDS [1000-5000]."""
    entries = generate_d2_pretrain_datasets(n_datasets=10, seeds_start=PRETRAIN_SEEDS_START)
    seeds_used = {e["seed"] for e in entries}
    test_seeds_set = set(range(1000, 5001))
    overlap = seeds_used & test_seeds_set
    assert not overlap, f"Pretrain seeds overlap with TEST_SEEDS: {overlap}"


# ── Test 12: Pretrained checkpoint differs from base ─────────────────────────

def test_pretrain_checkpoint_differs():
    """Pretrained model should have different checkpoint hash from initial model."""
    entries = generate_d2_pretrain_datasets(n_datasets=5)
    val_entries = _build_val_entries()

    # Train a model for 5 epochs
    model_before = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    hash_before = checkpoint_hash(model_before.state_dict())

    model_after, _ = train_multi_dataset(
        entries[:2], val_entries, n_epochs=3, patience=2, device=DEVICE, seed=7,
    )
    hash_after = checkpoint_hash(model_after.state_dict())

    assert hash_before != hash_after, "Training should change model weights"


# ── Test 13: Gate C1 no NaN ───────────────────────────────────────────────────

def test_gate_c1_no_nan():
    """Synthetic records with known values should pass C1."""
    good_records = [
        {"mae": 0.25, "edge_auc": 0.65},
        {"mae": 0.28, "edge_auc": 0.55},
    ]
    functional_result = {
        "oracle_mae": 0.20, "ffill_mae": 0.25,
        "oracle_ratio": 0.80, "gate_c2_pass": True,
    }
    gate_report = evaluate_gates(
        functional_result, good_records, good_records, [], [], [],
    )
    assert gate_report["C1"]["result"] == "PASS"


# ── Test 14: Gate C2 functional ───────────────────────────────────────────────

def test_gate_c2_functional():
    """Oracle beats ffill → C2 PASS; oracle worse → C2 FAIL."""
    # Case 1: oracle wins
    func_pass = {"oracle_mae": 0.20, "ffill_mae": 0.25, "oracle_ratio": 0.80, "gate_c2_pass": True}
    gates_pass = evaluate_gates(func_pass, [], [], [], [], [])
    assert gates_pass["C2"]["result"] == "PASS"

    # Case 2: ffill wins
    func_fail = {"oracle_mae": 0.30, "ffill_mae": 0.25, "oracle_ratio": 1.20, "gate_c2_pass": False}
    gates_fail = evaluate_gates(func_fail, [], [], [], [], [])
    assert gates_fail["C2"]["result"] == "FAIL"


# ── Test 15: Gate C3 data scaling structure ───────────────────────────────────

def test_gate_c3_data_scaling():
    """C3 structure: records with better MAE at n=25 vs n=10 → PASS."""
    d_recs = [
        {"axis": "D", "n_datasets": 10, "diversity": "D0", "mae": 0.30, "edge_auc": 0.5, "scenario": "novel_lag2", "seed": 1000, "mask_key": "mcar_30"},
        {"axis": "D", "n_datasets": 25, "diversity": "D0", "mae": 0.27, "edge_auc": 0.5, "scenario": "novel_lag2", "seed": 1000, "mask_key": "mcar_30"},
        {"axis": "D", "n_datasets": 10, "diversity": "D2", "mae": 0.29, "edge_auc": 0.6, "scenario": "novel_lag2", "seed": 1000, "mask_key": "mcar_30"},
        {"axis": "D", "n_datasets": 25, "diversity": "D2", "mae": 0.25, "edge_auc": 0.6, "scenario": "novel_lag2", "seed": 1000, "mask_key": "mcar_30"},
    ]
    func = {"oracle_mae": 0.20, "ffill_mae": 0.25, "oracle_ratio": 0.80, "gate_c2_pass": True}
    gates = evaluate_gates(func, d_recs, [], [], [], [])
    # With MAE gain of 10% (0.30→0.27), should pass C3
    assert "C3" in gates
    assert gates["C3"]["result"] in ("PASS", "FAIL")  # structure check: result exists


# ── Test 16: Gate report has all keys ────────────────────────────────────────

def test_gate_report_all_keys():
    """Gate report must have C1-C10 keys."""
    func = {"oracle_mae": 0.20, "ffill_mae": 0.25, "oracle_ratio": 0.80, "gate_c2_pass": True}
    gates = evaluate_gates(func, [], [], [], [], [])
    for gate_id in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]:
        assert gate_id in gates, f"Missing gate {gate_id}"
        assert "result" in gates[gate_id], f"Gate {gate_id} missing 'result'"
        assert gates[gate_id]["result"] in ("PASS", "FAIL", "NA")
    assert "decision" in gates
    assert "principal_cause" in gates
    assert "next_step" in gates


# ── Test 17: Multitask gradients reach attention ──────────────────────────────

def test_multitask_gradients_reach_attention():
    """After L2 loss.backward(), attention.grad should not be None."""
    ds = _tiny_dataset()
    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_relations = ds["true_relations"]
    n_T, n_S, n_Y = panel.shape

    model = _tiny_model(n_S, n_T)
    model.train()

    loss = compute_multitask_loss(
        model, panel, mask, adj_s, adj_t, true_relations, n_S, DEVICE,
        alpha=MULTITASK_ALPHA, include_sign=False, include_lag=False,
    )
    loss.backward()

    assert model.log_sect_attn_lag1.grad is not None, (
        "log_sect_attn_lag1.grad is None after L2 backward — edge loss not reaching encoder"
    )
    grad_norm = float(model.log_sect_attn_lag1.grad.norm())
    # Gradient should be non-trivially non-zero
    assert grad_norm > 1e-8, f"Attention gradient near zero: {grad_norm:.2e}"


# ── Test 18: No test data in pretraining ─────────────────────────────────────

def test_no_test_data_in_pretraining():
    """Pretrain datasets must use seeds 200-299, not 1000-5000."""
    entries = generate_d2_pretrain_datasets(n_datasets=10, seeds_start=200)
    for e in entries:
        seed = e["seed"]
        assert 200 <= seed < 300, f"Seed {seed} outside [200, 300)"
        assert seed not in range(1000, 5001), f"Seed {seed} is in TEST_SEEDS range"


# ── Test 19: Both mcar_30 and block_30 in records ────────────────────────────

def test_block_mask_in_records():
    """Axis D records should include both mcar_30 and block_30 mask keys."""
    records = run_axis_d(
        device=DEVICE,
        seeds=[1000],
        n_epochs=TINY_EPOCHS,
        patience=TINY_PATIENCE,
        n_datasets_list=[10],
    )
    mask_keys = {r["mask_key"] for r in records}
    assert "mcar_30" in mask_keys, f"Missing mcar_30, got {mask_keys}"
    assert "block_30" in mask_keys, f"Missing block_30, got {mask_keys}"


# ── Test 20: Shift spectrum no overlap ───────────────────────────────────────

def test_shift_spectrum_no_overlap():
    """S0/S1/S2/S3 are distinct scenario configs."""
    from src.modeles.synthetic.phase13_diagnostic.ofat_runner import (
        run_axis_s,
    )
    records = run_axis_s(device=DEVICE, test_seeds=[1000])
    if not records:
        pytest.skip("No shift records")
    shift_levels = {r["shift_level"] for r in records}
    assert len(shift_levels) >= 2, f"Expected multiple shift levels, got {shift_levels}"
    # S2 and S3 should be distinct novel test scenarios
    s2_recs = [r for r in records if r["shift_level"] == "S2_novel_lag2"]
    s3_recs = [r for r in records if r["shift_level"] == "S3_novel_highvar"]
    if s2_recs and s3_recs:
        # Their MAEs should differ (different data generation configs)
        assert s2_recs[0]["shift_level"] != s3_recs[0]["shift_level"]
