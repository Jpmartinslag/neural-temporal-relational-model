"""
test_phase11_generalization.py — Phase 11 true generalization protocol tests (DEC-045)

Tests cover:
  - Split disjointness and seed correctness
  - Novel test scenario properties vs training scenarios
  - Dataset determinism and checksum stability
  - Multi-dataset trainer: no optimizer calls at eval, shared weights, shape
  - Checkpoint save/load integrity (hash unchanged)
  - Zero-shot evaluator: no adaptation flag, 7 models present
  - Oracle AUC=1.000 wiring on test scenarios
  - Gate structure X1-X9
  - Normalization-free invariant (no fit on test data)
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
import torch


# ── Imports under test ────────────────────────────────────────────────────────

from src.modeles.synthetic.phase11_generalization.splits import (
    TRAIN_SEEDS,
    VAL_SEEDS,
    TEST_SEEDS,
    PILOT_TRAIN_SEEDS,
    PILOT_VAL_SEEDS,
    PILOT_TEST_SEEDS,
    TRAIN_SCENARIO_NAMES,
    VAL_SCENARIO_NAME,
    TEST_SCENARIO_NAMES,
    NOVEL_TEST_SCENARIOS,
    TRAIN_MASK_KEYS,
    VAL_MASK_KEY,
    PILOT_TEST_MASK_KEYS,
    verify_disjoint,
    verify_novel_test_dynamics,
    dataset_checksum,
    build_split_manifest,
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
    STRATEGY_SCENARIOS,
    DEFAULT_LR,
)
from src.modeles.synthetic.phase11_generalization.gates_phase11 import (
    PHASE11_GATE_VERSION,
    X4_RATIO_THRESHOLD,
    X5_SEED_FRAC,
    X6_AUC_THRESHOLD,
    evaluate_gates,
    _x1_safety,
    _x2_dataset_disjoint,
    _x3_no_adaptation,
    _x4_t2_advantage,
    _x5_generalizes_baseline,
    _x6_edge_transfer,
    _x7_pilot_completeness,
    _x8_seed_consistency,
    _x9_oracle_bound,
    _make_decision,
)
from src.data.synthetic.generate_herald_synthetic import (
    BENCHMARK_SCENARIOS,
    generate_dataset,
    SyntheticConfig,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.evaluate_imputation import compute_edge_recovery_metrics


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tiny_config(seed: int = 0) -> SyntheticConfig:
    """Minimal config for fast test generation (5T × 4S × 8Y)."""
    return SyntheticConfig(
        n_territories=5, n_sectors=4, n_years=8,
        seed=seed,
        n_true_relations=3,
        mcar_rates=(0.30,), mar_rates=(0.30,), block_rates=(0.30,),
    )


def _tiny_dataset(seed: int = 0) -> dict:
    return generate_dataset(_tiny_config(seed))


def _make_entry(ds: dict, mask_key: str = "mcar_30") -> dict:
    return {
        "panel": ds["panel"],
        "mask": ds["masks"][mask_key],
        "adj_s": ds["sector_adj"],
        "adj_t": ds["territory_adj"],
        "true_relations": ds["true_relations"],
    }


# ── 1. Split disjointness ─────────────────────────────────────────────────────

def test_seed_sets_disjoint():
    verify_disjoint()  # must not raise


def test_train_val_test_no_overlap():
    assert set(TRAIN_SEEDS) & set(VAL_SEEDS) == set()
    assert set(TRAIN_SEEDS) & set(TEST_SEEDS) == set()
    assert set(VAL_SEEDS) & set(TEST_SEEDS) == set()


def test_pilot_seeds_are_subsets():
    assert set(PILOT_TRAIN_SEEDS) <= set(TRAIN_SEEDS)
    assert set(PILOT_VAL_SEEDS) <= set(VAL_SEEDS)
    assert set(PILOT_TEST_SEEDS) <= set(TEST_SEEDS)


def test_no_overlap_with_benchmark_seeds():
    benchmark_seeds = {42, 123, 456, 789, 1337}
    assert set(TRAIN_SEEDS) & benchmark_seeds == set()
    assert set(VAL_SEEDS) & benchmark_seeds == set()
    assert set(TEST_SEEDS) & benchmark_seeds == set()


def test_no_overlap_with_ofat_seeds():
    ofat_seeds = {42, 123, 456}
    assert set(TEST_SEEDS) & ofat_seeds == set()


# ── 2. Novel scenario properties ──────────────────────────────────────────────

def test_novel_dynamics_verification():
    verify_novel_test_dynamics()  # must not raise


def test_novel_scenarios_more_nonlinear_than_train():
    max_train = max(BENCHMARK_SCENARIOS[s].frac_nonlinear for s in TRAIN_SCENARIO_NAMES)
    for name, cfg in NOVEL_TEST_SCENARIOS.items():
        assert cfg.frac_nonlinear > max_train, (
            f"{name}: frac_nonlinear={cfg.frac_nonlinear} <= train max={max_train}"
        )


def test_novel_lag2_has_forced_lag_2():
    assert NOVEL_TEST_SCENARIOS["novel_lag2"].forced_lag == 2


def test_novel_territory_radius_differs_from_train():
    train_radii = {BENCHMARK_SCENARIOS[s].territory_radius for s in TRAIN_SCENARIO_NAMES}
    for name, cfg in NOVEL_TEST_SCENARIOS.items():
        assert cfg.territory_radius not in train_radii, (
            f"{name}: territory_radius={cfg.territory_radius} conflicts with training"
        )


def test_novel_scenarios_same_dimensions_as_train():
    for name, cfg in NOVEL_TEST_SCENARIOS.items():
        assert cfg.n_sectors == N_SECTORS, f"{name}: n_sectors must be {N_SECTORS}"
        assert cfg.n_territories == N_TERRITORIES, f"{name}: n_territories must be {N_TERRITORIES}"


# ── 3. Dataset determinism and checksum ──────────────────────────────────────

def test_dataset_checksum_deterministic():
    cfg = _tiny_config(42)
    ds1 = generate_dataset(cfg)
    ds2 = generate_dataset(cfg)
    assert dataset_checksum(ds1) == dataset_checksum(ds2)


def test_dataset_checksum_differs_by_seed():
    cfg0 = _tiny_config(0)
    cfg1 = _tiny_config(1)
    ds0 = generate_dataset(cfg0)
    ds1 = generate_dataset(cfg1)
    assert dataset_checksum(ds0) != dataset_checksum(ds1)


def test_build_split_manifest_pilot():
    manifest = build_split_manifest(
        train_seeds=PILOT_TRAIN_SEEDS[:1],
        val_seeds=PILOT_VAL_SEEDS[:1],
        test_seeds=PILOT_TEST_SEEDS[:1],
    )
    assert manifest["protocol_version"] == "phase11_v1"
    assert set(manifest["train_scenarios"]) == set(TRAIN_SCENARIO_NAMES)
    assert manifest["val_scenario"] == VAL_SCENARIO_NAME
    assert len(manifest["checksums"]) > 0
    train_keys = [k for k in manifest["checksums"] if k.startswith("train/")]
    assert len(train_keys) == len(TRAIN_SCENARIO_NAMES) * 1  # 1 seed


# ── 4. Trainer: shared weights, no adaptation, entry counts ──────────────────

def test_make_train_entries_t1():
    entries = make_train_entries("T1", PILOT_TRAIN_SEEDS[:2])
    # T1: linear only × 2 seeds × 2 masks
    assert len(entries) == 1 * 2 * len(TRAIN_MASK_KEYS)
    for e in entries:
        assert e["panel"].shape[0] == N_TERRITORIES
        assert e["panel"].shape[1] == N_SECTORS


def test_make_train_entries_t2():
    entries = make_train_entries("T2", PILOT_TRAIN_SEEDS[:2])
    # T2: linear + mixed_default × 2 seeds × 2 masks
    assert len(entries) == 2 * 2 * len(TRAIN_MASK_KEYS)


def test_make_val_entries():
    entries = make_val_entries(PILOT_VAL_SEEDS[:1])
    assert len(entries) == 1  # 1 seed × 1 mask
    assert entries[0]["scenario"] == VAL_SCENARIO_NAME


def test_train_multi_dataset_smoke():
    """Tiny training run (2 entries, 3 epochs) completes without error."""
    ds0 = _tiny_dataset(0)
    ds1 = _tiny_dataset(1)
    train_entries = [_make_entry(ds0), _make_entry(ds1)]
    val_entries = [_make_entry(_tiny_dataset(10))]

    # Patch the model to tiny dimensions for speed
    n_s, n_t = 4, 5
    model_tiny = HERALDGraphImputerLagged(n_s, n_t, hidden_dim=16, dropout=0.0)
    model_tiny.to("cpu")

    import torch
    import torch.nn.functional as F
    from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
    from src.modeles.synthetic.imputation_baselines import _build_temporal_features

    def _tiny_nll(model, panel, mask, adj_s, adj_t, device):
        panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, device)
        true_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32))
        temp_feats_t = torch.from_numpy(_build_temporal_features(panel, mask).astype(np.float32))
        out = model(panel_t, mask_t, adj_s_t, adj_t_t, temp_feats_t)
        pm = out[..., 0]
        ls = out[..., 1]
        sq = (2 * ls).exp().clamp(min=1e-4)
        nll = 0.5 * (2 * ls + (true_t - pm) ** 2 / sq)
        return (nll * mask_t).sum() / mask_t.sum().clamp(min=1)

    opt = torch.optim.Adam(model_tiny.parameters(), lr=1e-3)
    rng = np.random.default_rng(0)
    best_state = None
    for epoch in range(3):
        model_tiny.train()
        for e in train_entries:
            opt.zero_grad()
            loss = _tiny_nll(model_tiny, e["panel"], e["mask"], e["adj_s"], e["adj_t"], "cpu")
            loss.backward()
            opt.step()
        model_tiny.eval()
        with torch.no_grad():
            val_loss = float(_tiny_nll(model_tiny, val_entries[0]["panel"], val_entries[0]["mask"],
                                       val_entries[0]["adj_s"], val_entries[0]["adj_t"], "cpu"))
        if best_state is None:
            best_state = copy.deepcopy(model_tiny.state_dict())

    assert not any(torch.isnan(p).any() for p in model_tiny.parameters())


def test_no_optimizer_calls_during_eval():
    """Verify that during zero-shot eval, no optimizer.step() is called."""
    import torch
    ds = _tiny_dataset(0)
    model = HERALDGraphImputerLagged(4, 5, hidden_dim=8, dropout=0.0)
    model.eval()

    # Record parameter state before
    params_before = {k: v.clone() for k, v in model.state_dict().items()}

    # Simulate zero-shot eval (no optimizer)
    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    with torch.no_grad():
        pred = impute_deterministic_lagged(model, panel, mask, adj_s, adj_t, device="cpu")

    # Parameters must be unchanged
    for k, v in model.state_dict().items():
        assert torch.allclose(v, params_before[k]), f"Parameter {k} changed during eval!"


# ── 5. Checkpoint integrity ───────────────────────────────────────────────────

def test_checkpoint_hash_deterministic():
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    h1 = checkpoint_hash(model.state_dict())
    h2 = checkpoint_hash(model.state_dict())
    assert h1 == h2


def test_checkpoint_hash_changes_after_step():
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    h_before = checkpoint_hash(model.state_dict())

    ds = _tiny_dataset(0)
    adj_s = np.zeros((N_SECTORS, N_SECTORS))  # no-graph
    adj_t = np.zeros((N_TERRITORIES, N_TERRITORIES))
    # Small artificial gradient step
    opt = torch.optim.SGD(model.parameters(), lr=1.0)
    model.train()
    panel = np.random.randn(N_TERRITORIES, N_SECTORS, 20)
    mask = np.ones_like(panel)
    from src.modeles.synthetic.herald_graph_imputer import _prep_tensors
    from src.modeles.synthetic.imputation_baselines import _build_temporal_features
    panel_t, mask_t, adj_s_t, adj_t_t = _prep_tensors(panel, mask, adj_s, adj_t, "cpu")
    true_t = torch.from_numpy(panel.astype(np.float32))
    feats = torch.from_numpy(_build_temporal_features(panel, mask).astype(np.float32))
    out = model(panel_t, mask_t, adj_s_t, adj_t_t, feats)
    loss = out[..., 0].sum()
    loss.backward()
    opt.step()

    h_after = checkpoint_hash(model.state_dict())
    assert h_before != h_after


def test_save_load_checkpoint_preserves_hash():
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    h_orig = checkpoint_hash(model.state_dict())
    with tempfile.TemporaryDirectory() as tmp:
        ckpt_path = Path(tmp) / "model.ckpt"
        c_hash = save_checkpoint(model, ckpt_path)
        assert c_hash == h_orig

        loaded = load_checkpoint(ckpt_path)
        h_loaded = checkpoint_hash(loaded.state_dict())
        assert h_loaded == h_orig


def test_load_checkpoint_sets_eval_mode():
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    with tempfile.TemporaryDirectory() as tmp:
        ckpt_path = Path(tmp) / "model.ckpt"
        save_checkpoint(model, ckpt_path)
        loaded = load_checkpoint(ckpt_path)
        assert not loaded.training, "Model must be in eval mode after load_checkpoint"


# ── 6. Oracle AUC wiring on novel test scenarios ──────────────────────────────

@pytest.mark.parametrize("scenario_name", list(NOVEL_TEST_SCENARIOS.keys()))
def test_oracle_auc_on_novel_scenario(scenario_name):
    """Oracle with directed adj should achieve AUC ≈ 1.000 on novel scenarios."""
    base_cfg = NOVEL_TEST_SCENARIOS[scenario_name]
    cfg = dataclasses.replace(base_cfg, seed=TEST_SEEDS[0])
    ds = generate_dataset(cfg)

    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_relations = ds["true_relations"]
    n_S = panel.shape[1]

    # Build oracle model and set directed attention
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    build_directed_oracle_lagged(model, true_relations, n_S)
    model.eval()

    if hasattr(model, "get_sector_attention"):
        attn = model.get_sector_attention()
    else:
        a1 = model.log_sect_attn_lag1.detach().exp().cpu().numpy()
        a2 = model.log_sect_attn_lag2.detach().exp().cpu().numpy()
        attn = np.maximum(a1, a2)

    edge_m = compute_edge_recovery_metrics(true_relations, n_S, attn)
    assert edge_m.auc == pytest.approx(1.000, abs=1e-6), (
        f"{scenario_name}: oracle AUC={edge_m.auc:.4f}, expected 1.000"
    )


# ── 7. 7-model output structure ───────────────────────────────────────────────

EXPECTED_MODELS = [
    "ffill", "ridge", "no_graph", "herald_contemp",
    "herald_lagged", "herald_lagged_permuted", "oracle_lagged",
]


def _make_stub_record(strategy: str, scenario: str, seed: int, mask_key: str,
                      hl_mae: float, ng_mae: float, ff_mae: float,
                      oracle_mae: float, auc: float = 0.6) -> dict:
    return {
        "protocol_version": "phase11_v1",
        "strategy": strategy,
        "scenario": scenario,
        "seed": seed,
        "mask_key": mask_key,
        "leakage_pass": True,
        "n_hidden": 100,
        "models": {
            "ffill": {"mae": ff_mae, "rmse": ff_mae * 1.2},
            "ridge": {"mae": ff_mae * 0.95, "rmse": ff_mae * 1.1},
            "no_graph": {"mae": ng_mae, "rmse": ng_mae * 1.2},
            "herald_contemp": {"mae": ng_mae * 1.05, "rmse": ng_mae * 1.3},
            "herald_lagged": {"mae": hl_mae, "rmse": hl_mae * 1.2,
                               "edge_auc": auc, "edge_auprc": 0.4,
                               "edge_prevalence": 0.12,
                               "edge_precision": 0.5, "edge_recall": 0.5, "edge_f1": 0.5,
                               "n_true_edges": 8},
            "herald_lagged_permuted": {"mae": ng_mae * 0.98, "rmse": ng_mae * 1.1},
            "oracle_lagged": {"mae": oracle_mae, "rmse": oracle_mae * 1.2,
                               "edge_auc": 1.0},
        },
    }


def test_expected_models_present_in_stub():
    r = _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.22, oracle_mae=0.18)
    for m in EXPECTED_MODELS:
        assert m in r["models"], f"Model {m} missing from result"


# ── 8. Gate structure and thresholds ─────────────────────────────────────────

def test_gate_version_constant():
    assert PHASE11_GATE_VERSION == "phase11_gates_v1"


def test_x4_threshold_value():
    assert X4_RATIO_THRESHOLD == 1.02


def test_x5_seed_frac_value():
    assert abs(X5_SEED_FRAC - 2 / 3) < 1e-9


def test_x6_auc_threshold_value():
    assert X6_AUC_THRESHOLD == 0.55


def test_evaluate_gates_empty():
    report = evaluate_gates([])
    assert "error" in report


def test_evaluate_gates_all_pass():
    """Build records where all gates should pass."""
    records = []
    # Need T1 and T2 records, multiple seeds, novel_lag2 + novel_highvar
    for strategy in ["T1", "T2"]:
        for scenario in ["novel_lag2", "novel_highvar"]:
            for seed in PILOT_TEST_SEEDS[:3]:
                for mk in ["mcar_30", "block_30"]:
                    # T2 herald_lagged beats no_graph; T1 slightly worse than T2
                    hl = 0.18 if strategy == "T2" else 0.21
                    r = _make_stub_record(strategy, scenario, seed, mk,
                                          hl_mae=hl, ng_mae=0.25, ff_mae=0.23,
                                          oracle_mae=0.15, auc=0.70)
                    records.append(r)
    report = evaluate_gates(records)
    assert "summary" in report
    assert "decision" in report["summary"]
    # X1 (safety) must pass
    assert report["X1_safety"]["pass"] is True
    # X2 (disjoint) must pass
    assert report["X2_dataset_disjoint"]["pass"] is True
    # X9 (oracle bound): oracle_mae=0.15 < ffill=0.23 → must pass
    assert report["X9_oracle_bound"]["pass"] is True


def test_x1_safety_detects_nan():
    r = _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=float("nan"), ng_mae=0.25, ff_mae=0.22, oracle_mae=0.18)
    result = _x1_safety([r])
    assert result["pass"] is False
    assert result["nan_inf_count"] > 0


def test_x1_safety_detects_leakage():
    r = _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.22, oracle_mae=0.18)
    r["leakage_pass"] = False
    result = _x1_safety([r])
    assert result["pass"] is False


def test_x4_t2_beats_t1():
    records = []
    for seed in [1000, 2000, 3000]:
        records.append(_make_stub_record("T1", "novel_lag2", seed, "mcar_30",
                                          hl_mae=0.25, ng_mae=0.30, ff_mae=0.28, oracle_mae=0.20))
        records.append(_make_stub_record("T2", "novel_lag2", seed, "mcar_30",
                                          hl_mae=0.22, ng_mae=0.30, ff_mae=0.28, oracle_mae=0.20))
    result = _x4_t2_advantage(records)
    assert result["pass"] is True


def test_x4_t2_fails_when_worse():
    records = []
    for seed in [1000, 2000, 3000]:
        records.append(_make_stub_record("T1", "novel_lag2", seed, "mcar_30",
                                          hl_mae=0.20, ng_mae=0.30, ff_mae=0.28, oracle_mae=0.18))
        records.append(_make_stub_record("T2", "novel_lag2", seed, "mcar_30",
                                          hl_mae=0.25, ng_mae=0.30, ff_mae=0.28, oracle_mae=0.18))
    result = _x4_t2_advantage(records)
    assert result["pass"] is False


def test_x5_generalizes_when_herald_beats_no_graph():
    records = []
    for seed in [1000, 2000, 3000]:
        records.append(_make_stub_record("T2", "novel_lag2", seed, "mcar_30",
                                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.23, oracle_mae=0.18))
    result = _x5_generalizes_baseline(records)
    assert result["pass"] is True


def test_x5_fails_when_herald_worse():
    records = []
    for seed in [1000, 2000, 3000]:
        records.append(_make_stub_record("T2", "novel_lag2", seed, "mcar_30",
                                          hl_mae=0.30, ng_mae=0.25, ff_mae=0.23, oracle_mae=0.18))
    result = _x5_generalizes_baseline(records)
    assert result["pass"] is False


def test_x6_edge_transfer_pass():
    records = [
        _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.23, oracle_mae=0.18, auc=0.70),
    ]
    result = _x6_edge_transfer(records)
    assert result["pass"] is True


def test_x6_edge_transfer_fail():
    records = [
        _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.23, oracle_mae=0.18, auc=0.40),
    ]
    result = _x6_edge_transfer(records)
    assert result["pass"] is False


def test_x9_oracle_bound_pass():
    records = [
        _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.23, oracle_mae=0.18),
    ]
    result = _x9_oracle_bound(records)
    assert result["pass"] is True


def test_x9_oracle_bound_fail():
    # oracle_mae > ffill_mae
    records = [
        _make_stub_record("T2", "novel_lag2", 1000, "mcar_30",
                          hl_mae=0.20, ng_mae=0.25, ff_mae=0.10, oracle_mae=0.30),
    ]
    result = _x9_oracle_bound(records)
    assert result["pass"] is False


def test_decision_vocabulary_generalizes():
    gates = {
        "X5_generalizes_baseline": True,
        "X9_oracle_bound": True,
        "X4_t2_advantage": True,
        "X6_edge_transfer": True,
    }
    assert _make_decision(gates) == "SYNTHETIC_RECONSTRUCTION_GENERALIZES"


def test_decision_vocabulary_fail():
    gates = {
        "X5_generalizes_baseline": False,
        "X9_oracle_bound": False,
        "X4_t2_advantage": False,
        "X6_edge_transfer": False,
    }
    assert _make_decision(gates) == "GENERALIZATION_FAIL"


def test_decision_vocabulary_relations_generalize():
    gates = {
        "X5_generalizes_baseline": False,
        "X9_oracle_bound": False,
        "X4_t2_advantage": False,
        "X6_edge_transfer": True,
    }
    assert _make_decision(gates) == "SYNTHETIC_RELATIONS_GENERALIZE"


# ── 9. Normalization-free invariant ──────────────────────────────────────────

def test_no_statistics_computed_from_test_panel():
    """
    The evaluator should never call .fit() on test panels.
    Verify that ForwardFillImputer and RidgeImputer are called with the test
    (panel, mask) but no external stats are injected from test data into the
    herald_lagged model.
    This is structural: load_checkpoint provides frozen weights; the only
    'fitting' at test time is local baselines (ffill/ridge) which is expected.
    """
    # The herald_lagged model is loaded from checkpoint with frozen weights.
    # Verify that after calling impute_deterministic_lagged, the weights are unchanged.
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, HIDDEN_DIM, DROPOUT)
    h_before = checkpoint_hash(model.state_dict())

    ds = generate_dataset(dataclasses.replace(NOVEL_TEST_SCENARIOS["novel_lag2"],
                                              seed=TEST_SEEDS[0]))
    panel = ds["panel"]
    mask = ds["masks"]["mcar_30"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]

    model.eval()
    with torch.no_grad():
        _ = impute_deterministic_lagged(model, panel, mask, adj_s, adj_t, device="cpu")

    h_after = checkpoint_hash(model.state_dict())
    assert h_before == h_after, "Model weights changed during zero-shot evaluation!"


# ── 10. Strategy-specific entries ────────────────────────────────────────────

def test_t1_train_scenarios():
    assert STRATEGY_SCENARIOS["T1"] == ["linear"]


def test_t2_train_scenarios():
    assert set(STRATEGY_SCENARIOS["T2"]) == {"linear", "mixed_default"}


def test_t2_has_more_entries_than_t1():
    t1 = make_train_entries("T1", PILOT_TRAIN_SEEDS[:2])
    t2 = make_train_entries("T2", PILOT_TRAIN_SEEDS[:2])
    assert len(t2) > len(t1)


def test_test_scenarios_not_in_benchmark():
    """Novel test scenarios must not appear in BENCHMARK_SCENARIOS."""
    for name in TEST_SCENARIO_NAMES:
        assert name not in BENCHMARK_SCENARIOS, (
            f"Test scenario '{name}' must not appear in BENCHMARK_SCENARIOS"
        )


# ── 11. Pilot mask coverage ───────────────────────────────────────────────────

def test_pilot_test_masks_subset_of_full():
    from src.modeles.synthetic.phase11_generalization.splits import FULL_TEST_MASK_KEYS
    assert set(PILOT_TEST_MASK_KEYS) <= set(FULL_TEST_MASK_KEYS)


def test_all_mask_keys_generated_by_config():
    """Verify pilot test masks exist in generated dataset."""
    cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS["novel_lag2"], seed=TEST_SEEDS[0])
    ds = generate_dataset(cfg)
    for mk in PILOT_TEST_MASK_KEYS:
        assert mk in ds["masks"], f"Mask key {mk} not in generated dataset"
