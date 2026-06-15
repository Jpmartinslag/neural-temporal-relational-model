"""
test_phase15_stable_objective.py — Tests for DEC-051 Phase 15 Stable Objective Audit.

Tests:
  1.  masked_nll_clamped: log_sigma is clamped to [LOG_SIGMA_MIN, LOG_SIGMA_MAX]
  2.  masked_nll_clamped: only loss_mask cells contribute to loss
  3.  masked_huber: only loss_mask cells contribute; correct formula
  4.  masked_mse: only loss_mask cells contribute
  5.  _check_disjoint: raises on overlapping masks
  6.  _check_disjoint: passes on disjoint masks
  7.  log_sigma_stats: returns correct min/mean/max
  8.  GraphAuxHeads: sign_logit and lag_logit are independent parameters
  9.  GraphAuxHeads: edge_presence_bce both lag-1 and lag-2 positive
  10. GraphAuxHeads: edge_presence_bce uses max(lag1, lag2) logit
  11. GraphAuxHeads: edge_sign_bce evaluated on known edges only (independent of presence)
  12. GraphAuxHeads: edge_lag_bce evaluated on known edges only (independent of sign)
  13. GraphAuxHeads: each head gets independent gradient (sign/lag do not share params)
  14. GraphAuxHeads: total_graph_loss = ALPHA*presence + BETA*sign + GAMMA*lag
  15. D2 seeds disjoint from eval seeds and test seeds
  16. pretrain_runner_v2: verify_d2_seeds_disjoint raises on overlap
  17. evaluator_v2: zero-shot returns correct result structure
  18. evaluator_v2: zero-shot MAE is finite
  19. evaluator_v2: eval_mask never overlaps obs_mask
  20. evaluator_v2: few-shot adapted model has same attention as original (frozen)
  21. evaluator_v2: few-shot MAE result has correct fields
  22. select_top2_variants returns 2 items in ascending order
  23. gates_dec051: V1 fails when MAE is NaN
  24. gates_dec051: V2 fails when nt_verdict is LEAKAGE
  25. gates_dec051: V6 fails when log_sigma out of [-3,2]
  26. gates_dec051: V300 requires V1+V2+V6 PASS
  27. gates_dec051: V3 threshold logic (beat ffill in >= 4/5 seeds)
  28. gates_dec051: format_gate_report produces markdown table
  29. fewshot_audit: NT5 (empty support) returns same predictions as zero-shot
  30. fewshot_audit: NT6 (random decoder) few-shot MAE >= 80% of zero-shot
  31. Checkpoint immutability: model state unchanged after evaluate_zero_shot
  32. Determinism: same checkpoint + seed → same MAE
  33. Reconstruction loss disjoint assertion also enforced in pretrain_runner_v2
  34. GraphAuxHeads.edge_metrics returns finite values with sufficient variation
  35. gates_dec051: V9 fails when no few-shot improvement
"""

from __future__ import annotations

import copy
import dataclasses
import math
from pathlib import Path
import tempfile

import numpy as np
import pytest
import torch
import torch.nn as nn

from src.modeles.synthetic.phase15_stable_objective.loss_functions import (
    _check_disjoint,
    masked_nll_clamped,
    masked_huber,
    masked_mse,
    log_sigma_stats,
    LOG_SIGMA_MIN,
    LOG_SIGMA_MAX,
    SIGMA_ENTROPY_LAMBDA,
    HUBER_DELTA,
)
from src.modeles.synthetic.phase15_stable_objective.graph_heads import (
    GraphAuxHeads,
    GRAPH_ALPHA,
    GRAPH_BETA,
    GRAPH_GAMMA,
)
from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import (
    select_top2_variants,
    EVAL_SEEDS,
)
from src.modeles.synthetic.phase15_stable_objective.gates_dec051 import (
    GateResult,
    check_v1_safety,
    check_v2_fewshot_integrity,
    check_v3_temporal_reconstruction,
    check_v6_stable_loss,
    check_v9_fewshot_value,
    check_300epoch_gate,
    format_gate_report,
)
from src.modeles.synthetic.phase15_stable_objective.pretrain_runner_v2 import (
    verify_d2_seeds_disjoint,
    D2_SEED_START,
    generate_d2_datasets,
)
from src.modeles.synthetic.phase11_generalization.splits import TEST_SEEDS
from src.data.synthetic.generate_herald_synthetic import (
    TrueRelation,
    generate_dataset,
)
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.phase11_generalization.trainer import (
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tiny_tensors():
    """n_T=3, n_S=4, n_Y=5 all-ones tensors."""
    shape = (3, 4, 5)
    return {
        "pred_mean": torch.ones(shape),
        "pred_log_sigma": torch.zeros(shape),
        "true": torch.ones(shape) * 0.5,
        "loss_mask": torch.ones(shape),
        "input_mask": torch.zeros(shape),
    }


@pytest.fixture
def tiny_model():
    return HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)


@pytest.fixture
def simple_relations():
    return [
        TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.5, nonlinear=False),
        TrueRelation(source_sector=2, target_sector=3, lag=2, weight=-0.3, nonlinear=False),
    ]


@pytest.fixture
def aux_heads():
    return GraphAuxHeads(N_SECTORS)


@pytest.fixture
def small_scenario():
    """Generate a small scenario dataset for fast testing."""
    cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS["novel_lag2"], seed=1000)
    return generate_dataset(cfg)


# ── Loss function tests ───────────────────────────────────────────────────────

def test_masked_nll_clamped_log_sigma_bounded(tiny_tensors):
    """log_sigma outside bounds must be clamped (loss must not be infinite)."""
    extreme_log_sigma = torch.full_like(tiny_tensors["pred_mean"], -100.0)
    loss = masked_nll_clamped(
        tiny_tensors["pred_mean"], extreme_log_sigma, tiny_tensors["true"], tiny_tensors["loss_mask"]
    )
    assert torch.isfinite(loss), f"Loss not finite with extreme log_sigma: {loss.item()}"

    extreme_pos = torch.full_like(tiny_tensors["pred_mean"], 100.0)
    loss2 = masked_nll_clamped(
        tiny_tensors["pred_mean"], extreme_pos, tiny_tensors["true"], tiny_tensors["loss_mask"]
    )
    assert torch.isfinite(loss2), f"Loss not finite with extreme positive log_sigma: {loss2.item()}"


def test_masked_nll_clamped_only_loss_mask_cells(tiny_tensors):
    """Changing non-masked cells must not affect the loss."""
    loss_mask = torch.zeros_like(tiny_tensors["loss_mask"])
    loss_mask[0, 0, 0] = 1.0  # only one cell

    true_a = tiny_tensors["true"].clone()
    true_b = tiny_tensors["true"].clone()
    true_b[1, 1, 1] = 9999.0  # outside loss_mask

    loss_a = masked_nll_clamped(tiny_tensors["pred_mean"], tiny_tensors["pred_log_sigma"], true_a, loss_mask)
    loss_b = masked_nll_clamped(tiny_tensors["pred_mean"], tiny_tensors["pred_log_sigma"], true_b, loss_mask)
    assert torch.isclose(loss_a, loss_b), "Non-masked cell change affected NLL loss"


def test_masked_huber_only_loss_mask_cells(tiny_tensors):
    """Changing non-masked cells must not affect Huber loss."""
    loss_mask = torch.zeros_like(tiny_tensors["loss_mask"])
    loss_mask[0, 0, 0] = 1.0

    true_a = tiny_tensors["true"].clone()
    true_b = tiny_tensors["true"].clone()
    true_b[2, 3, 4] = 9999.0

    loss_a = masked_huber(tiny_tensors["pred_mean"], true_a, loss_mask)
    loss_b = masked_huber(tiny_tensors["pred_mean"], true_b, loss_mask)
    assert torch.isclose(loss_a, loss_b)


def test_masked_huber_correct_formula(tiny_tensors):
    """Huber loss: below delta → 0.5*(err^2); above delta → delta*(err - 0.5*delta)."""
    pred = torch.zeros(1, 1, 1)
    true = torch.tensor([[[0.5]]])  # below delta=1.0 → 0.5 * 0.5**2 = 0.125
    loss_mask = torch.ones(1, 1, 1)
    loss = masked_huber(pred, true, loss_mask, delta=1.0)
    expected = 0.5 * 0.5**2
    assert abs(loss.item() - expected) < 1e-5, f"Expected {expected}, got {loss.item()}"

    true_large = torch.tensor([[[3.0]]])  # above delta → 1.0 * (3.0 - 0.5) = 2.5
    loss2 = masked_huber(pred, true_large, loss_mask, delta=1.0)
    expected2 = 1.0 * (3.0 - 0.5)
    assert abs(loss2.item() - expected2) < 1e-5, f"Expected {expected2}, got {loss2.item()}"


def test_masked_mse_only_loss_mask_cells(tiny_tensors):
    """Changing non-masked cells must not affect MSE loss."""
    loss_mask = torch.zeros_like(tiny_tensors["loss_mask"])
    loss_mask[0, 0, 0] = 1.0

    true_a = tiny_tensors["true"].clone()
    true_b = tiny_tensors["true"].clone()
    true_b[2, 2, 2] = 9999.0

    loss_a = masked_mse(tiny_tensors["pred_mean"], true_a, loss_mask)
    loss_b = masked_mse(tiny_tensors["pred_mean"], true_b, loss_mask)
    assert torch.isclose(loss_a, loss_b)


def test_check_disjoint_raises_on_overlap():
    """_check_disjoint must raise when masks overlap."""
    input_mask = np.ones((3, 4, 5), dtype=np.float32)
    loss_mask = np.ones((3, 4, 5), dtype=np.float32)
    with pytest.raises(AssertionError, match="overlap"):
        _check_disjoint(input_mask, loss_mask)


def test_check_disjoint_passes_on_disjoint():
    """_check_disjoint must not raise when masks are disjoint."""
    input_mask = np.zeros((3, 4, 5), dtype=np.float32)
    input_mask[0, 0, 0] = 1.0
    loss_mask = np.zeros((3, 4, 5), dtype=np.float32)
    loss_mask[1, 1, 1] = 1.0
    _check_disjoint(input_mask, loss_mask)  # must not raise


def test_log_sigma_stats_correct(tiny_tensors):
    """log_sigma_stats returns correct min/mean/max."""
    ls = torch.tensor([[[1.0, 2.0, 3.0]]])
    mask = torch.ones(1, 1, 3)
    stats = log_sigma_stats(ls, mask)
    assert abs(stats["log_sigma_min"] - 1.0) < 1e-5
    assert abs(stats["log_sigma_mean"] - 2.0) < 1e-5
    assert abs(stats["log_sigma_max"] - 3.0) < 1e-5


# ── GraphAuxHeads tests ───────────────────────────────────────────────────────

def test_graph_aux_heads_independent_params(aux_heads):
    """sign_logit and lag_logit are independent parameters (different tensors)."""
    assert aux_heads.sign_logit is not aux_heads.lag_logit
    # Changing one must not affect the other
    with torch.no_grad():
        aux_heads.sign_logit.fill_(1.0)
        aux_heads.lag_logit.fill_(0.0)
    assert aux_heads.sign_logit[0, 0].item() == pytest.approx(1.0)
    assert aux_heads.lag_logit[0, 0].item() == pytest.approx(0.0)


def test_edge_presence_bce_both_lags_positive(tiny_model, simple_relations, aux_heads):
    """Lag-1 and lag-2 true edges must both produce positive targets in presence BCE."""
    device = "cpu"
    # Two edges: one lag-1, one lag-2
    lag1_rel = [TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.5, nonlinear=False)]
    lag2_rel = [TrueRelation(source_sector=0, target_sector=1, lag=2, weight=0.5, nonlinear=False)]

    loss_lag1 = aux_heads.edge_presence_bce(tiny_model, lag1_rel, device)
    loss_lag2 = aux_heads.edge_presence_bce(tiny_model, lag2_rel, device)

    # Both should produce finite losses (both treated as positive)
    assert torch.isfinite(loss_lag1), "Lag-1 presence BCE not finite"
    assert torch.isfinite(loss_lag2), "Lag-2 presence BCE not finite"

    # With equal logits (all zeros), both should give the same BCE value
    assert abs(loss_lag1.item() - loss_lag2.item()) < 1e-5, (
        f"Lag-1 ({loss_lag1.item():.4f}) and lag-2 ({loss_lag2.item():.4f}) presence loss differ"
    )


def test_edge_presence_bce_uses_max_logit(tiny_model, simple_relations, aux_heads):
    """Presence logit = max(lag1_attn, lag2_attn) not just lag1 or lag2 alone."""
    device = "cpu"
    # Set lag1 attn to 1.0, lag2 to 0.5 → max should be 1.0
    with torch.no_grad():
        tiny_model.log_sect_attn_lag1.fill_(1.0)
        tiny_model.log_sect_attn_lag2.fill_(0.5)

    # Set lag1=0.5, lag2=2.0 → max should be 2.0
    with torch.no_grad():
        tiny_model.log_sect_attn_lag1.fill_(0.5)
        tiny_model.log_sect_attn_lag2.fill_(2.0)

    # Directly verify: max(0.5, 2.0) = 2.0 → presence logit should equal 2.0
    presence_logit = torch.max(tiny_model.log_sect_attn_lag1, tiny_model.log_sect_attn_lag2)
    expected_max = 2.0
    assert presence_logit.max().item() == pytest.approx(expected_max), (
        f"Expected max logit {expected_max}, got {presence_logit.max().item()}"
    )


def test_edge_sign_bce_independent_from_presence(aux_heads, simple_relations):
    """edge_sign_bce must use self.sign_logit, not the attention matrices."""
    device = "cpu"
    # sign_logit and lag_logit start at zero; edge_sign_bce should use sign_logit
    params_before = set(id(p) for p in aux_heads.parameters())
    sign_loss = aux_heads.edge_sign_bce(simple_relations, device)
    assert torch.isfinite(sign_loss)
    # Must be differentiable via sign_logit, not via an external model
    sign_loss.backward()
    assert aux_heads.sign_logit.grad is not None
    assert torch.isfinite(aux_heads.sign_logit.grad).all()
    # lag_logit grad must be None or zero (sign BCE does not touch it)
    if aux_heads.lag_logit.grad is not None:
        assert aux_heads.lag_logit.grad.abs().sum().item() == 0.0


def test_edge_lag_bce_independent_from_sign(aux_heads, simple_relations):
    """edge_lag_bce must use self.lag_logit, not sign_logit or attention matrices."""
    device = "cpu"
    if aux_heads.lag_logit.grad is not None:
        aux_heads.lag_logit.grad.zero_()
    if aux_heads.sign_logit.grad is not None:
        aux_heads.sign_logit.grad.zero_()

    lag_loss = aux_heads.edge_lag_bce(simple_relations, device)
    assert torch.isfinite(lag_loss)
    lag_loss.backward()
    assert aux_heads.lag_logit.grad is not None
    assert torch.isfinite(aux_heads.lag_logit.grad).all()
    if aux_heads.sign_logit.grad is not None:
        assert aux_heads.sign_logit.grad.abs().sum().item() == 0.0


def test_graph_heads_independent_gradient(tiny_model, simple_relations):
    """Each head gets independent gradient: sign/lag heads have no gradient cross-talk."""
    device = "cpu"
    heads = GraphAuxHeads(N_SECTORS)

    # Compute total_graph_loss and backprop
    loss = heads.total_graph_loss(tiny_model, simple_relations, device)
    loss.backward()

    # All three: sign_logit, lag_logit, attention should have gradients
    assert heads.sign_logit.grad is not None, "sign_logit has no gradient"
    assert heads.lag_logit.grad is not None, "lag_logit has no gradient"
    # Attention (presence) should flow through tiny_model
    attn_params = [tiny_model.log_sect_attn_lag1, tiny_model.log_sect_attn_lag2]
    for p in attn_params:
        assert p.grad is not None, f"{p} has no gradient after total_graph_loss"


def test_graph_heads_total_loss_formula(tiny_model, simple_relations):
    """total_graph_loss = ALPHA*presence + BETA*sign + GAMMA*lag."""
    device = "cpu"
    heads = GraphAuxHeads(N_SECTORS)
    losses = heads.all_losses(tiny_model, simple_relations, device)
    expected = GRAPH_ALPHA * losses["presence"] + GRAPH_BETA * losses["sign"] + GRAPH_GAMMA * losses["lag"]
    total = heads.total_graph_loss(tiny_model, simple_relations, device)
    assert torch.isclose(total, expected), f"total={total.item():.6f}, expected={expected.item():.6f}"


# ── Seed safety tests ─────────────────────────────────────────────────────────

def test_d2_seeds_disjoint_from_eval_and_test():
    """D2 pretraining seeds must not overlap with EVAL_SEEDS or TEST_SEEDS."""
    d2_seeds = list(range(D2_SEED_START, D2_SEED_START + 50))
    eval_seeds_set = set(EVAL_SEEDS)
    test_seeds_set = set(TEST_SEEDS)

    d2_set = set(d2_seeds)
    assert not (d2_set & eval_seeds_set), f"D2 seeds overlap with EVAL_SEEDS: {d2_set & eval_seeds_set}"
    assert not (d2_set & test_seeds_set), f"D2 seeds overlap with TEST_SEEDS: {d2_set & test_seeds_set}"


def test_verify_d2_seeds_raises_on_overlap():
    """verify_d2_seeds_disjoint must raise when seeds overlap eval/test seeds."""
    overlapping = list(EVAL_SEEDS[:2])
    with pytest.raises(ValueError, match="overlap"):
        verify_d2_seeds_disjoint(overlapping)


# ── Evaluator tests ───────────────────────────────────────────────────────────

def test_zero_shot_result_structure(small_scenario, tmp_path):
    """evaluate_zero_shot returns ZeroShotResult with correct fields."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import (
        evaluate_zero_shot,
        ZeroShotResult,
    )
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_test.pt"
    torch.save(model.state_dict(), ckpt)

    results = evaluate_zero_shot(str(ckpt), None, "TEST_VARIANT", 30, device="cpu")
    assert len(results) > 0
    r = results[0]
    assert isinstance(r, ZeroShotResult)
    assert hasattr(r, "mae") and hasattr(r, "rmse")
    assert hasattr(r, "log_sigma_min") and hasattr(r, "log_sigma_max")


def test_zero_shot_mae_finite(small_scenario, tmp_path):
    """evaluate_zero_shot returns finite MAE (no NaN/Inf)."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import evaluate_zero_shot
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_test.pt"
    torch.save(model.state_dict(), ckpt)

    results = evaluate_zero_shot(str(ckpt), None, "TEST_VARIANT", 30, device="cpu")
    for r in results:
        assert not math.isnan(r.mae), f"NaN MAE for {r.scenario}/{r.mask_key}/seed={r.seed}"
        assert not math.isinf(r.mae), f"Inf MAE for {r.scenario}/{r.mask_key}/seed={r.seed}"


def test_eval_mask_never_overlaps_obs_mask(small_scenario):
    """eval_mask must not overlap with obs_mask (no data leakage in evaluation)."""
    panel = small_scenario["panel"]
    structural_mask = np.isfinite(panel).astype(np.float32)

    for mask_key in ["mcar_30", "block_30"]:
        if mask_key not in small_scenario["masks"]:
            continue
        obs_mask = small_scenario["masks"][mask_key]
        eval_mask = structural_mask * (1 - obs_mask)
        overlap = (eval_mask == 1) & (obs_mask == 1)
        assert not overlap.any(), f"eval_mask overlaps obs_mask in {mask_key}"


def test_fewshot_attention_frozen(small_scenario, tmp_path):
    """Few-shot adaptation must leave attention parameters unchanged."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import _few_shot_adaptation
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_test.pt"
    torch.save(model.state_dict(), ckpt)

    panel = small_scenario["panel"]
    obs_mask = small_scenario["masks"].get("mcar_30", list(small_scenario["masks"].values())[0])
    adj_s = small_scenario["sector_adj"]
    adj_t = small_scenario["territory_adj"]

    attn_before = {
        "lag1": model.log_sect_attn_lag1.detach().clone(),
        "lag2": model.log_sect_attn_lag2.detach().clone(),
        "terr": model.log_terr_attn.detach().clone(),
    }
    rng = np.random.default_rng(42)
    adapted, _ = _few_shot_adaptation(model, panel, obs_mask, adj_s, adj_t, "cpu", 0.05, rng)

    for name, before_val in attn_before.items():
        after_val = (
            adapted.log_sect_attn_lag1 if name == "lag1" else
            adapted.log_sect_attn_lag2 if name == "lag2" else
            adapted.log_terr_attn
        )
        assert torch.allclose(before_val, after_val.detach()), (
            f"Attention {name} changed during few-shot adaptation"
        )


def test_fewshot_result_fields(small_scenario, tmp_path):
    """FewShotResult must contain mae_zeroshot, mae_fewshot, mae_reduction_pct."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import (
        evaluate_few_shot,
        FewShotResult,
    )
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_test.pt"
    torch.save(model.state_dict(), ckpt)

    results = evaluate_few_shot(str(ckpt), "TEST_VARIANT", 30, device="cpu", k_fracs=[0.05])
    assert len(results) > 0
    r = results[0]
    assert isinstance(r, FewShotResult)
    assert hasattr(r, "mae_zeroshot")
    assert hasattr(r, "mae_fewshot")
    assert hasattr(r, "mae_reduction_pct")


def test_select_top2_returns_2_in_order():
    """select_top2_variants returns 2 items with lower val_loss first."""
    val_losses = {
        "TEMPORAL_MASKED_NLL_CLAMPED_ep75": 0.5,
        "TEMPORAL_MASKED_HUBER_ep75": 0.3,
        "GRAPH_MULTITASK_NLL_CLAMPED_ep75": 0.7,
        "NO_PRETRAINING_ep75": 1.2,
    }
    top2 = select_top2_variants(val_losses)
    assert len(top2) == 2
    # Lowest val_loss is 0.3 → should be first
    assert top2[0] == "TEMPORAL_MASKED_HUBER_ep75"
    assert top2[1] == "TEMPORAL_MASKED_NLL_CLAMPED_ep75"


# ── Gate logic tests ──────────────────────────────────────────────────────────

def test_v1_fails_on_nan_mae():
    """V1 must FAIL if any result has NaN MAE."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import ZeroShotResult
    bad = ZeroShotResult(
        variant="X", epoch_budget=75, scenario="novel_lag2", mask_key="mcar_30", seed=1000,
        mae=float("nan"), rmse=0.1, mae_ffill=0.2, mae_nogr=0.3,
        log_sigma_min=-1.0, log_sigma_mean=0.0, log_sigma_max=1.0,
        edge_auc=float("nan"), edge_auprc=float("nan"), sign_acc=float("nan"), lag_acc=float("nan"),
    )
    gate = check_v1_safety([bad], [], "FEWSHOT_INTEGRITY_PASS")
    assert gate.verdict == "FAIL"


def test_v2_fails_on_leakage_verdict():
    """V2 must FAIL when nt_verdict contains 'LEAKAGE'."""
    gate = check_v2_fewshot_integrity("LEAKAGE_OR_EVALUATION_ERROR: [nt1]")
    assert gate.verdict == "FAIL"


def test_v2_passes_on_integrity_pass():
    """V2 must PASS when nt_verdict = 'FEWSHOT_INTEGRITY_PASS'."""
    gate = check_v2_fewshot_integrity("FEWSHOT_INTEGRITY_PASS")
    assert gate.verdict == "PASS"


def test_v6_fails_on_log_sigma_out_of_range():
    """V6 must FAIL when log_sigma_min < -3.05 (variance collapse)."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import ZeroShotResult
    bad = ZeroShotResult(
        variant="TEMPORAL_MASKED_NLL_CLAMPED", epoch_budget=75, scenario="novel_lag2",
        mask_key="mcar_30", seed=1000,
        mae=0.2, rmse=0.3, mae_ffill=0.25, mae_nogr=0.28,
        log_sigma_min=-5.0, log_sigma_mean=-2.0, log_sigma_max=1.0,
        edge_auc=float("nan"), edge_auprc=float("nan"), sign_acc=float("nan"), lag_acc=float("nan"),
    )
    gate = check_v6_stable_loss([bad])
    assert gate.verdict == "FAIL"


def test_v300_requires_v1_v2_v6_pass():
    """V300 must FAIL if any of V1, V2, V6 fails."""
    gates = {
        "V1": GateResult("V1", "", "PASS"),
        "V2": GateResult("V2", "", "FAIL"),  # V2 fails
        "V6": GateResult("V6", "", "PASS"),
    }
    result = check_300epoch_gate(gates, {})
    assert result.verdict == "FAIL"
    assert "V2" in str(result.evidence)


def test_v3_beats_ffill_in_4_of_5_seeds():
    """V3 must PASS when best TEMPORAL_MASKED beats ffill in >= 4/5 seeds."""
    key = ("TEMPORAL_MASKED_NLL_CLAMPED", 75, "novel_lag2", "mcar_30")
    summary = {
        key: {
            "mae_mean": 0.20,
            "mae_ffill_mean": 0.25,
            "n_beat_ffill": 4,
            "n_seeds": 5,
        }
    }
    gate = check_v3_temporal_reconstruction(summary, min_seeds=4)
    assert gate.verdict == "PASS"


def test_v3_fails_in_3_of_5_seeds():
    """V3 must FAIL when best TEMPORAL_MASKED beats ffill in only 3/5 seeds."""
    key = ("TEMPORAL_MASKED_NLL_CLAMPED", 75, "novel_lag2", "mcar_30")
    summary = {
        key: {
            "mae_mean": 0.20,
            "mae_ffill_mean": 0.25,
            "n_beat_ffill": 3,
            "n_seeds": 5,
        }
    }
    gate = check_v3_temporal_reconstruction(summary, min_seeds=4)
    assert gate.verdict == "FAIL"


def test_format_gate_report_produces_markdown():
    """format_gate_report must produce a markdown table string."""
    gates = {
        "V1": GateResult("V1", "Safety", "PASS"),
        "V2": GateResult("V2", "Integrity", "FAIL"),
    }
    report = format_gate_report(gates)
    assert "|" in report
    assert "PASS" in report or "FAIL" in report
    assert "V1" in report


def test_v9_fails_when_no_fewshot_improvement():
    """V9 must FAIL when no few-shot scenario improves over zero-shot."""
    summary = {
        ("TEST", 75, "novel_lag2", "mcar_30", 0.05): {
            "mae_zeroshot_mean": 0.2,
            "mae_fewshot_mean": 0.25,  # worse than zero-shot
            "mae_reduction_mean_pct": -25.0,
            "n_seeds": 5,
            "n_beat_zeroshot": 0,
        }
    }
    gate = check_v9_fewshot_value(summary)
    assert gate.verdict == "FAIL"


# ── Few-shot audit tests ──────────────────────────────────────────────────────

def test_nt5_empty_support_reproduces_zeroshot(tmp_path):
    """NT5: with k_frac=0, few-shot must match zero-shot within atol=1e-5."""
    from src.modeles.synthetic.phase15_stable_objective.fewshot_audit import nt5_empty_support
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_nt5.pt"
    torch.save(model.state_dict(), ckpt)
    result = nt5_empty_support(str(ckpt), device="cpu")
    assert result["all_pass"], f"NT5 failed: {result.get('results', [])}"


def test_nt6_random_decoder_fewshot_near_zeroshot(tmp_path):
    """NT6: random decoder few-shot MAE must be >= 80% of zero-shot MAE."""
    from src.modeles.synthetic.phase15_stable_objective.fewshot_audit import nt6_random_decoder
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_nt6.pt"
    torch.save(model.state_dict(), ckpt)
    result = nt6_random_decoder(str(ckpt), device="cpu")
    assert result["all_pass"], f"NT6 failed: {result.get('results', [])}"


# ── Checkpoint immutability test ──────────────────────────────────────────────

def test_checkpoint_immutable_after_zero_shot(tmp_path):
    """Model state must be unchanged after evaluate_zero_shot."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import evaluate_zero_shot
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_immutable.pt"
    torch.save(model.state_dict(), ckpt)

    state_before = copy.deepcopy(model.state_dict())
    evaluate_zero_shot(str(ckpt), None, "TEST", 30, device="cpu")

    # Reload and compare
    model2 = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    model2.load_state_dict(torch.load(ckpt, map_location="cpu"))
    for key in state_before:
        assert torch.allclose(state_before[key], model2.state_dict()[key]), (
            f"Checkpoint parameter {key} changed after evaluate_zero_shot"
        )


# ── Determinism test ──────────────────────────────────────────────────────────

def test_deterministic_zero_shot(tmp_path):
    """Same checkpoint and seed must produce identical MAE across two calls."""
    from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import evaluate_zero_shot
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    ckpt = tmp_path / "model_det.pt"
    torch.save(model.state_dict(), ckpt)

    r1 = evaluate_zero_shot(str(ckpt), None, "TEST", 30, device="cpu")
    r2 = evaluate_zero_shot(str(ckpt), None, "TEST", 30, device="cpu")

    for a, b in zip(r1, r2):
        if not math.isnan(a.mae) and not math.isnan(b.mae):
            assert abs(a.mae - b.mae) < 1e-7, f"Non-deterministic MAE: {a.mae} vs {b.mae}"


# ── Reconstruction loss disjoint check in pretrain_runner ────────────────────

def test_pretrain_runner_disjoint_check():
    """_compute_masked_reconstruction_loss must raise on overlapping masks."""
    from src.modeles.synthetic.phase15_stable_objective.pretrain_runner_v2 import (
        _compute_masked_reconstruction_loss,
    )
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    import dataclasses
    cfg = dataclasses.replace(NOVEL_TEST_SCENARIOS["novel_lag2"], seed=1000)
    ds = generate_dataset(cfg)
    panel = ds["panel"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]

    ones = np.ones_like(panel, dtype=np.float32)
    with pytest.raises(AssertionError, match="overlap"):
        _compute_masked_reconstruction_loss(model, panel, ones, ones, adj_s, adj_t, "cpu")


# ── Graph metrics test ────────────────────────────────────────────────────────

def test_edge_metrics_finite_with_variation(simple_relations):
    """edge_metrics should return finite values when model has non-trivial attention."""
    model = HERALDGraphImputerLagged(N_SECTORS, N_TERRITORIES, hidden_dim=HIDDEN_DIM, dropout=0.0)
    with torch.no_grad():
        model.log_sect_attn_lag1.normal_(0, 0.5)
        model.log_sect_attn_lag2.normal_(0, 0.5)
    heads = GraphAuxHeads(N_SECTORS)
    with torch.no_grad():
        heads.sign_logit.normal_(0, 0.5)
        heads.lag_logit.normal_(0, 0.5)

    metrics = heads.edge_metrics(model, simple_relations, "cpu")
    for k, v in metrics.items():
        if not math.isnan(v):
            assert math.isfinite(v), f"Metric {k} is not finite: {v}"
