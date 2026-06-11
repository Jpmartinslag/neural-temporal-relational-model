"""HERALD — Tests for the frugal dual-graph model (contract FROZEN_V2).

Mandatory coverage:
  - shapes of every input and output;
  - parameter budget at H=4 and H=8 (<= 10,000);
  - per-seed determinism (eval mode);
  - absence of NaN/Inf;
  - structural and observational masks;
  - no-graph fallback (territory_adj_mask=0);
  - real adjacency changes the result;
  - learned sector graph receives gradient;
  - sector adjacency: zero diagonal, symmetry, non-negativity;
  - no per-territory parameter;
  - no target access in forward;
  - backward through all four losses;
  - batch with B > 1.

Torch lives in the ``mlearning`` conda env; this test is skipped if torch is
unavailable.
"""
from __future__ import annotations

import inspect

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.modeles.dual_graph_models import (  # noqa: E402
    DualGraphModel,
    build_dual_graph_model,
    compute_class_weights,
    compute_pos_weight,
    count_parameters,
    dual_graph_loss,
    masked_huber_loss,
    sector_graph_sparsity,
    sector_graph_stability,
    territory_message,
    weighted_bce_loss,
    weighted_ce_loss,
)

R, S, T, NF = 6, 9, 5, 6


def _make_batch(B: int = 2, seed: int = 0):
    """Synthetic dual-graph batch matching the tensor schema."""
    rng = np.random.default_rng(seed)
    features = rng.standard_normal((B, T, R, S, NF)).astype(np.float32)
    fmask = (rng.random((B, T, R, S, NF)) > 0.05).astype(np.uint8)

    # Territory adjacency: positive top-k-ish symmetric per (B,T,S).
    adj = np.zeros((B, T, S, R, R), dtype=np.float32)
    for b in range(B):
        for t in range(T):
            for s in range(S):
                m = rng.random((R, R)).astype(np.float32)
                m = (m + m.T) / 2
                np.fill_diagonal(m, 0.0)
                m[m < 0.6] = 0.0
                adj[b, t, s] = m
    adj_mask = (adj.sum(axis=(-1, -2)) > 0).astype(np.uint8)   # (B,T,S)
    # Force one early step with no graph to exercise the fallback path.
    adj[:, 0] = 0.0
    adj_mask[:, 0] = 0

    struct_mask = np.ones((B, R, S), dtype=np.uint8)

    tmask = (rng.random((B, R, S)) > 0.1).astype(np.uint8)
    log_growth = rng.standard_normal((B, R, S)).astype(np.float32)
    regime = rng.integers(0, 3, (B, R, S)).astype(np.int64)
    recovery = (rng.random((B, R, S)) > 0.85).astype(np.int64)
    emergence = (rng.random((B, R, S)) > 0.9).astype(np.int64)
    # Inject missing labels (-1) outside the target mask.
    regime[tmask == 0] = -1
    recovery[tmask == 0] = -1
    emergence[tmask == 0] = -1

    batch = {
        "features_seq": torch.tensor(features),
        "feature_mask_seq": torch.tensor(fmask),
        "territory_adj_seq": torch.tensor(adj),
        "territory_adj_mask": torch.tensor(adj_mask),
        "struct_mask": torch.tensor(struct_mask),
    }
    targets = {
        "target_log_growth": torch.tensor(log_growth),
        "target_regime": torch.tensor(regime),
        "target_recovery": torch.tensor(recovery),
        "target_emergence": torch.tensor(emergence),
        "target_mask": torch.tensor(tmask),
    }
    return batch, targets


def _run(model, batch):
    return model(
        batch["features_seq"],
        batch["feature_mask_seq"],
        batch["territory_adj_seq"],
        batch["territory_adj_mask"],
        batch["struct_mask"],
    )


# ---------------------------------------------------------------------------
# T01 — output shapes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("H", [4, 8])
def test_output_shapes(H):
    B = 2
    model = build_dual_graph_model(hidden_dim=H).eval()
    batch, _ = _make_batch(B)
    out = _run(model, batch)
    assert out["pred_log_growth"].shape == (B, R, S)
    assert out["regime_logits"].shape == (B, R, S, 3)
    assert out["recovery_logits"].shape == (B, R, S)
    assert out["emergence_logits"].shape == (B, R, S)
    assert out["node_embeddings"].shape == (B, R, S, H)
    assert out["territory_embeddings"].shape == (B, R, H)
    assert out["sector_embeddings"].shape == (B, S, H)
    assert out["sector_adj_learned"].shape == (B, T, S, S)


# ---------------------------------------------------------------------------
# T02 — parameter budget at H=4 and H=8
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("H", [4, 8])
@pytest.mark.parametrize("temporal", [False, True])
def test_parameter_budget(H, temporal):
    model = build_dual_graph_model(hidden_dim=H, temporal_sector_graph=temporal)
    n = count_parameters(model)
    assert n <= 10_000, f"H={H} temporal={temporal}: {n} > 10000 params"


def test_invalid_hidden_dim_rejected():
    with pytest.raises(ValueError):
        build_dual_graph_model(hidden_dim=16)


# ---------------------------------------------------------------------------
# T03 — determinism per seed (eval mode)
# ---------------------------------------------------------------------------

def test_seed_determinism():
    batch, _ = _make_batch(2, seed=1)
    torch.manual_seed(42)
    m1 = build_dual_graph_model(hidden_dim=8).eval()
    torch.manual_seed(42)
    m2 = build_dual_graph_model(hidden_dim=8).eval()
    out1 = _run(m1, batch)
    out2 = _run(m2, batch)
    for key in out1:
        assert torch.allclose(out1[key], out2[key], atol=1e-6), f"non-deterministic {key}"


# ---------------------------------------------------------------------------
# T04 — no NaN / Inf in any output
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("use_terr,use_sect", [(True, True), (True, False),
                                                (False, True), (False, False)])
def test_no_nan_inf(use_terr, use_sect):
    model = build_dual_graph_model(
        hidden_dim=8, use_territory_graph=use_terr, use_sector_graph=use_sect
    ).eval()
    batch, _ = _make_batch(2, seed=3)
    out = _run(model, batch)
    for key, value in out.items():
        assert torch.isfinite(value).all(), f"non-finite values in {key}"


def test_no_nan_with_fully_missing_node():
    """A node with all features missing must not produce NaN."""
    model = build_dual_graph_model(hidden_dim=8).eval()
    batch, _ = _make_batch(2, seed=4)
    batch["feature_mask_seq"][:, :, 0, 0, :] = 0  # node (r=0,s=0) fully missing
    out = _run(model, batch)
    for value in out.values():
        assert torch.isfinite(value).all()


# ---------------------------------------------------------------------------
# T05 — structural and observational masks
# ---------------------------------------------------------------------------

def test_struct_mask_derived_when_none():
    model = build_dual_graph_model(hidden_dim=4).eval()
    batch, _ = _make_batch(2, seed=5)
    out_explicit = _run(model, batch)
    out_derived = model(
        batch["features_seq"], batch["feature_mask_seq"],
        batch["territory_adj_seq"], batch["territory_adj_mask"], None,
    )
    # All nodes structurally present and observed → derived mask equals explicit.
    assert torch.allclose(
        out_explicit["pred_log_growth"], out_derived["pred_log_growth"], atol=1e-6
    )


def test_observation_mask_blocks_unobserved_neighbours():
    """Invalid neighbours must not contribute to the territory message."""
    B = 1
    h = torch.randn(B, R, S, 8)
    adj = torch.ones(B, S, R, R)
    for s in range(S):
        adj[0, s].fill_diagonal_(0.0)
    adj_mask = torch.ones(B, S)
    valid_all = torch.ones(B, R, S, dtype=torch.bool)
    valid_drop = valid_all.clone()
    valid_drop[0, 1, :] = False  # region 1 invalid everywhere
    msg_all = territory_message(h, adj, valid_all, adj_mask)
    msg_drop = territory_message(h, adj, valid_drop, adj_mask)
    assert not torch.allclose(msg_all, msg_drop)


# ---------------------------------------------------------------------------
# T06 — no-graph fallback (territory_adj_mask=0)
# ---------------------------------------------------------------------------

def test_territory_fallback_when_masked():
    """With territory_adj_mask all-zero, the territory message is exactly zero,
    so the result matches a model run with the territory graph disabled."""
    model = build_dual_graph_model(hidden_dim=8, use_sector_graph=False).eval()
    batch, _ = _make_batch(2, seed=6)
    batch["territory_adj_mask"] = torch.zeros_like(batch["territory_adj_mask"])
    out_masked = _run(model, batch)

    model_nograph = build_dual_graph_model(
        hidden_dim=8, use_territory_graph=False, use_sector_graph=False
    )
    model_nograph.load_state_dict(model.state_dict())
    model_nograph.eval()
    out_nograph = _run(model_nograph, batch)
    assert torch.allclose(
        out_masked["pred_log_growth"], out_nograph["pred_log_growth"], atol=1e-6
    )


# ---------------------------------------------------------------------------
# T07 — real adjacency changes the result
# ---------------------------------------------------------------------------

def test_real_adjacency_changes_output():
    model = build_dual_graph_model(hidden_dim=8, use_sector_graph=False).eval()
    batch, _ = _make_batch(2, seed=7)
    out_real = _run(model, batch)

    zero_batch = dict(batch)
    zero_batch["territory_adj_seq"] = torch.zeros_like(batch["territory_adj_seq"])
    zero_batch["territory_adj_mask"] = torch.zeros_like(batch["territory_adj_mask"])
    out_zero = _run(model, zero_batch)
    assert not torch.allclose(
        out_real["pred_log_growth"], out_zero["pred_log_growth"], atol=1e-5
    )


# ---------------------------------------------------------------------------
# T08 — learned sector graph receives gradient
# ---------------------------------------------------------------------------

def test_sector_graph_gets_gradient():
    model = build_dual_graph_model(hidden_dim=8).train()
    batch, targets = _make_batch(2, seed=8)
    out = _run(model, batch)
    losses = dual_graph_loss(out, targets, targets["target_mask"])
    losses["total"].backward()
    assert model.sector_base.grad is not None
    assert torch.isfinite(model.sector_base.grad).all()
    assert model.sector_base.grad.abs().sum() > 0


# ---------------------------------------------------------------------------
# T09 — sector adjacency: diagonal, symmetry, non-negativity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("temporal", [False, True])
def test_sector_adjacency_structure(temporal):
    model = build_dual_graph_model(hidden_dim=8, temporal_sector_graph=temporal).eval()
    batch, _ = _make_batch(2, seed=9)
    out = _run(model, batch)
    adj = out["sector_adj_learned"]                       # (B,T,S,S)
    assert (adj >= 0).all(), "sector adjacency must be non-negative"
    diag = torch.diagonal(adj, dim1=-2, dim2=-1)
    assert torch.allclose(diag, torch.zeros_like(diag), atol=1e-7), "diagonal not zero"
    assert torch.allclose(adj, adj.transpose(-1, -2), atol=1e-6), "not symmetric"


# ---------------------------------------------------------------------------
# T10 — no per-territory parameter
# ---------------------------------------------------------------------------

def test_no_per_territory_parameter():
    model = build_dual_graph_model(hidden_dim=8)
    for name, p in model.named_parameters():
        assert R not in tuple(p.shape), f"parameter {name} scales with regions: {p.shape}"


def test_shared_weights_across_regions():
    """Permuting regions consistently must permute outputs, not change values."""
    model = build_dual_graph_model(hidden_dim=8, use_territory_graph=False).eval()
    batch, _ = _make_batch(1, seed=11)
    out = _run(model, batch)
    perm = torch.randperm(R)
    pbatch = {
        "features_seq": batch["features_seq"][:, :, perm],
        "feature_mask_seq": batch["feature_mask_seq"][:, :, perm],
        "territory_adj_seq": batch["territory_adj_seq"][:, :, :, perm][:, :, :, :, perm],
        "territory_adj_mask": batch["territory_adj_mask"],
        "struct_mask": batch["struct_mask"][:, perm],
    }
    out_perm = model(
        pbatch["features_seq"], pbatch["feature_mask_seq"],
        pbatch["territory_adj_seq"], pbatch["territory_adj_mask"], pbatch["struct_mask"],
    )
    assert torch.allclose(
        out["pred_log_growth"][:, perm], out_perm["pred_log_growth"], atol=1e-5
    )


# ---------------------------------------------------------------------------
# T11 — no target access in forward
# ---------------------------------------------------------------------------

def test_forward_has_no_target_argument():
    sig = inspect.signature(DualGraphModel.forward)
    names = " ".join(sig.parameters).lower()
    assert "target" not in names, "forward must not take any target argument"


# ---------------------------------------------------------------------------
# T12 — backward through all four task losses
# ---------------------------------------------------------------------------

def test_backward_all_four_losses():
    model = build_dual_graph_model(hidden_dim=8).train()
    batch, targets = _make_batch(2, seed=12)

    cw = compute_class_weights(targets["target_regime"], 3)
    rpw = compute_pos_weight(targets["target_recovery"])
    epw = compute_pos_weight(targets["target_emergence"])

    out = _run(model, batch)
    for head in ("growth", "regime", "recovery", "emergence"):
        model.zero_grad()
        out = _run(model, batch)
        losses = dual_graph_loss(
            out, targets, targets["target_mask"],
            class_weights=cw, recovery_pos_weight=rpw, emergence_pos_weight=epw,
        )
        losses[head].backward()
        grads = [p.grad for p in model.parameters() if p.grad is not None]
        assert grads, f"loss '{head}' produced no gradients"
        assert all(torch.isfinite(g).all() for g in grads), f"non-finite grad for {head}"


def test_total_loss_finite_and_components_present():
    model = build_dual_graph_model(hidden_dim=8).train()
    batch, targets = _make_batch(2, seed=13)
    out = _run(model, batch)
    losses = dual_graph_loss(out, targets, targets["target_mask"])
    for key in ("total", "growth", "regime", "recovery", "emergence", "sparse", "stable"):
        assert key in losses
        assert torch.isfinite(losses[key]).all()


# ---------------------------------------------------------------------------
# T13 — batch with B > 1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("B", [1, 2, 4])
def test_variable_batch_size(B):
    model = build_dual_graph_model(hidden_dim=8).eval()
    batch, _ = _make_batch(B, seed=14)
    out = _run(model, batch)
    assert out["pred_log_growth"].shape[0] == B
    assert torch.isfinite(out["pred_log_growth"]).all()


def test_batch_independence():
    """Sample 0 in a B=2 batch must match the same sample run alone (eval)."""
    model = build_dual_graph_model(hidden_dim=8).eval()
    batch2, _ = _make_batch(2, seed=15)
    out2 = _run(model, batch2)
    single = {k: v[:1] for k, v in batch2.items()}
    out1 = _run(model, single)
    assert torch.allclose(
        out2["pred_log_growth"][:1], out1["pred_log_growth"], atol=1e-5
    )


# ---------------------------------------------------------------------------
# T14 — loss helpers honour masks and ignore -1 labels
# ---------------------------------------------------------------------------

def test_losses_ignore_missing_labels():
    B = 2
    logits3 = torch.randn(B, R, S, 3, requires_grad=True)
    logits1 = torch.randn(B, R, S, requires_grad=True)
    regime = torch.full((B, R, S), -1, dtype=torch.int64)
    mask = torch.zeros(B, R, S, dtype=torch.uint8)
    # all masked / missing → zero loss, still differentiable
    l_ce = weighted_ce_loss(logits3, regime, mask)
    l_bce = weighted_bce_loss(logits1, regime, mask)
    assert float(l_ce.detach()) == 0.0
    assert float(l_bce.detach()) == 0.0


def test_masked_huber_only_uses_mask():
    pred = torch.zeros(1, R, S)
    target = torch.ones(1, R, S)
    mask = torch.zeros(1, R, S, dtype=torch.uint8)
    mask[0, 0, 0] = 1
    loss = masked_huber_loss(pred, target, mask)
    # single masked cell, |0-1|=1, huber(delta=1)=0.5
    assert abs(float(loss) - 0.5) < 1e-6


def test_class_weights_inverse_frequency():
    labels = torch.tensor([0, 0, 0, 1, 2])  # 3:1:1
    w = compute_class_weights(labels, 3)
    # rarer classes get higher weight
    assert w[1] > w[0] and w[2] > w[0]


def test_graph_regularizers_finite():
    adj = torch.rand(2, T, S, S)
    assert torch.isfinite(sector_graph_sparsity(adj)).all()
    assert torch.isfinite(sector_graph_stability(adj)).all()
    # single-step sequence → zero stability
    assert float(sector_graph_stability(adj[:, :1])) == 0.0
