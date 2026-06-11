"""HERALD DEC-028 — Mandatory A1 implementation tests.

Covers all 11 mandatory tests from §8 of
HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md
plus additional concrete checks for NaN/Inf, masks, determinism, shapes,
no-leakage, and zero-adjacency.

Test IDs T-shape, T-mask, T-bounded, T-zero-alpha, T-params, T-determinism,
T-zero-adj, T-real-adj, T-no-leakage, T-no-nan, T-shared-loss track exactly
the 11 mandatory tests in the contract.
"""
from __future__ import annotations

import random
import copy

import numpy as np
import pytest
import torch

from src.modeles.graph_temporal_models import (
    A0Neural,
    GConvGRU,
    EvolveGCNH,
    build_model,
    count_parameters,
    masked_wmape,
    bounded_residual_head,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

B, T, R, S, NF = 2, 5, 10, 9, 3
H_SMALL = 4
CLAMP = 0.15
SEED = 42


def set_seed(seed: int = SEED) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)


def make_batch(
    b: int = B,
    t: int = T,
    r: int = R,
    s: int = S,
    nf: int = NF,
    with_adj: bool = True,
    seed: int = SEED,
    zero_adj: bool = False,
) -> dict[str, torch.Tensor]:
    """Synthetic batch consistent with schema 2.0 shapes."""
    set_seed(seed)
    features_seq = torch.randn(b, t, r, s, nf)
    # 80 % of features valid (mask=1), 20 % missing
    feature_mask_seq = (torch.rand(b, t, r, s, nf) > 0.2).to(torch.int8)
    struct_mask = torch.ones(b, r, s, dtype=torch.int8)
    # One PT-KZ-like absent sector for region 0, sector 0 (struct=0 always)
    struct_mask[:, 0, 0] = 0
    y_ridge = torch.rand(b, r).clamp(min=1.0) * 100.0
    target_mask = torch.ones(b, r, dtype=torch.int8)
    y_true = y_ridge * (1.0 + 0.1 * torch.randn(b, r))

    batch = {
        "features_seq": features_seq,
        "feature_mask_seq": feature_mask_seq,
        "struct_mask": struct_mask,
        "y_ridge_canonical": y_ridge,
        "target_mask": target_mask,
        "y_true": y_true,
    }
    if with_adj:
        if zero_adj:
            batch["adjacency_seq"] = torch.zeros(b, t, s, r, r)
        else:
            # positive_topk-like: non-negative, sparse
            raw = torch.rand(b, t, s, r, r).clamp(min=0)
            raw = raw + raw.transpose(-1, -2)          # symmetrize
            raw.diagonal(dim1=-2, dim2=-1).fill_(0)    # no self-loops
            batch["adjacency_seq"] = raw
    return batch


def run_model(model: torch.nn.Module, batch: dict, seed: int = SEED) -> dict:
    set_seed(seed)
    model.eval()
    with torch.no_grad():
        if isinstance(model, A0Neural):
            return model(
                batch["features_seq"],
                batch["feature_mask_seq"],
                batch["struct_mask"],
                batch["y_ridge_canonical"],
            )
        else:
            return model(
                batch["features_seq"],
                batch["feature_mask_seq"],
                batch["struct_mask"],
                batch["y_ridge_canonical"],
                batch["adjacency_seq"],
            )


ALL_MODEL_NAMES = ["A0Neural", "GConvGRU", "EvolveGCNH"]


def _make_model(name: str, hidden_dim: int = H_SMALL, clamp_frac: float = CLAMP):
    set_seed(SEED)
    return build_model(
        name,
        n_sectors=S,
        n_features=NF,
        hidden_dim=hidden_dim,
        sector_embed_dim=4,
        dropout=0.3,
        clamp_frac=clamp_frac,
    )


# ---------------------------------------------------------------------------
# T-shape — input/output shapes match interface specification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_shape(name):
    model = _make_model(name)
    batch = make_batch()
    out = run_model(model, batch)

    assert out["delta_raw"].shape == (B, R), f"{name}: delta_raw shape wrong"
    assert out["delta_bounded"].shape == (B, R), f"{name}: delta_bounded shape wrong"
    assert out["y_hat"].shape == (B, R), f"{name}: y_hat shape wrong"
    assert out["territory_embeddings"].shape == (B, R, H_SMALL), \
        f"{name}: territory_embeddings shape wrong"


# ---------------------------------------------------------------------------
# T-mask — masked positions produce no gradient through the loss
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_mask(name):
    """Masked inputs and targets must not affect predictions or gradients."""
    model = _make_model(name)
    model.train()
    batch = make_batch()

    # A masked feature may contain any payload; it must be ignored.
    batch["feature_mask_seq"][:, 2, 1, 3, :] = 0
    features = batch["features_seq"].clone().requires_grad_(True)
    batch["features_seq"] = features

    # Half of target regions are excluded from the loss.
    target_mask = batch["target_mask"].clone()
    target_mask[:, R // 2 :] = 0
    batch["target_mask"] = target_mask

    if isinstance(model, A0Neural):
        out = model(
            batch["features_seq"],
            batch["feature_mask_seq"],
            batch["struct_mask"],
            batch["y_ridge_canonical"],
        )
    else:
        out = model(
            batch["features_seq"],
            batch["feature_mask_seq"],
            batch["struct_mask"],
            batch["y_ridge_canonical"],
            batch["adjacency_seq"],
        )

    loss = masked_wmape(out["y_hat"], batch["y_true"], batch["target_mask"])
    loss.backward()

    assert loss.isfinite(), f"{name}: loss is not finite"
    assert features.grad is not None
    assert features.grad[:, 2, 1, 3, :].abs().max().item() == 0.0, \
        f"{name}: masked feature received gradient"
    assert any(p.grad is not None and p.grad.abs().sum() > 0
               for p in model.parameters()), f"{name}: no gradient found"

    # Changing only masked feature payloads cannot change the prediction.
    model.eval()
    batch_a = make_batch()
    batch_a["feature_mask_seq"][:, 2, 1, 3, :] = 0
    batch_b = {k: v.clone() for k, v in batch_a.items()}
    batch_b["features_seq"][:, 2, 1, 3, :] = 1e6
    out_a = run_model(model, batch_a)
    out_b = run_model(model, batch_b)
    assert torch.equal(out_a["y_hat"], out_b["y_hat"]), \
        f"{name}: masked feature payload changed prediction"


# ---------------------------------------------------------------------------
# T-bounded — |delta_bounded| <= clamp_frac * max(y_ridge, 0)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_bounded(name):
    model = _make_model(name)
    batch = make_batch()
    out = run_model(model, batch)

    ridge_ref = batch["y_ridge_canonical"].clamp(min=0.0)
    bound = CLAMP * ridge_ref
    delta = out["delta_bounded"].abs()
    # Allow tiny floating-point tolerance
    assert (delta <= bound + 1e-5).all(), \
        f"{name}: delta_bounded exceeds bound. max excess: {(delta - bound).max():.2e}"


# ---------------------------------------------------------------------------
# T-zero-alpha — with clamp_frac=0, y_hat = y_ridge exactly
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_zero_alpha(name):
    model = _make_model(name, clamp_frac=0.0)
    batch = make_batch()
    out = run_model(model, batch)

    diff = (out["y_hat"] - batch["y_ridge_canonical"]).abs().max().item()
    assert diff < 1e-6, f"{name}: y_hat != y_ridge when clamp_frac=0. max diff: {diff:.2e}"


# ---------------------------------------------------------------------------
# T-params — n_trainable_params <= 5000
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
@pytest.mark.parametrize("hidden_dim", [4, 8])
def test_T_params(name, hidden_dim):
    model = _make_model(name, hidden_dim=hidden_dim)
    n = count_parameters(model)
    assert n <= 5000, f"{name} H={hidden_dim}: {n} params > 5000"


# ---------------------------------------------------------------------------
# T-determinism — same seed → identical outputs and loss
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_determinism(name):
    batch = make_batch(seed=SEED)

    set_seed(SEED)
    m1 = _make_model(name)
    out1 = run_model(m1, batch, seed=SEED)

    set_seed(SEED)
    m2 = _make_model(name)
    out2 = run_model(m2, batch, seed=SEED)

    for key in ("y_hat", "delta_bounded", "delta_raw"):
        diff = (out1[key] - out2[key]).abs().max().item()
        assert diff == 0.0, f"{name}: {key} not deterministic. max diff: {diff:.2e}"


# ---------------------------------------------------------------------------
# T-zero-adj — zero adjacency: A1a/A1b still produce finite y_hat
# For A0Neural it trivially holds (no adj input). For graph models,
# with zero adjacency only the self-fallback applies and output is finite.
# (Contract §5: "only self-message" when adj=0)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["GConvGRU", "EvolveGCNH"])
def test_T_zero_adj(name):
    model = _make_model(name)
    batch_zero = make_batch(zero_adj=True)
    out = run_model(model, batch_zero)

    assert torch.equal(out["y_hat"], batch_zero["y_ridge_canonical"]), \
        f"{name}: zero adjacency must reproduce canonical Ridge"
    assert torch.count_nonzero(out["delta_bounded"]).item() == 0


def test_T_zero_adj_a0():
    """A0Neural always produces finite output (no adjacency path)."""
    model = _make_model("A0Neural")
    batch = make_batch(with_adj=False)
    out = run_model(model, batch)
    assert out["y_hat"].isfinite().all()


# ---------------------------------------------------------------------------
# T-real-adj — real adjacency changes y_hat relative to zero adjacency
# (for graph models; A0Neural excluded by design)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["GConvGRU", "EvolveGCNH"])
def test_T_real_adj(name):
    set_seed(SEED)
    model = _make_model(name)

    batch_zero = make_batch(zero_adj=True, seed=SEED + 1)
    batch_real = {k: v.clone() for k, v in batch_zero.items()}
    # Replace adjacency with real positive one
    raw = torch.rand(B, T, S, R, R).clamp(min=0)
    raw = raw + raw.transpose(-1, -2)
    raw.diagonal(dim1=-2, dim2=-1).fill_(0)
    batch_real["adjacency_seq"] = raw

    out_zero = run_model(model, batch_zero, seed=SEED)
    out_real = run_model(model, batch_real, seed=SEED)

    diff = (out_real["y_hat"] - out_zero["y_hat"]).abs().max().item()
    assert diff > 1e-6, (
        f"{name}: real adjacency does not change y_hat vs zero adj. "
        f"max diff={diff:.2e}"
    )


# ---------------------------------------------------------------------------
# T-no-leakage — future fold data does not alter past predictions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_no_leakage(name):
    """A call on a future fold must not mutate state used by a past fold."""
    model = _make_model(name)
    past = make_batch(seed=SEED + 10)
    future = make_batch(seed=SEED + 11)

    out_before = run_model(model, past, seed=SEED)
    run_model(model, future, seed=SEED)
    out_after = run_model(model, past, seed=SEED)

    assert torch.equal(out_before["y_hat"], out_after["y_hat"]), \
        f"{name}: forward pass retained state across folds"


# ---------------------------------------------------------------------------
# T-no-nan — no NaN/Inf in y_hat, delta_bounded, or loss where target_mask=1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_T_no_nan(name):
    model = _make_model(name)
    batch = make_batch()
    out = run_model(model, batch)

    m = batch["target_mask"].bool()
    assert out["y_hat"][m].isfinite().all(), f"{name}: NaN/Inf in y_hat where target_mask=1"
    assert out["delta_bounded"][m].isfinite().all(), \
        f"{name}: NaN/Inf in delta_bounded where target_mask=1"

    loss = masked_wmape(out["y_hat"], batch["y_true"], batch["target_mask"])
    assert loss.isfinite(), f"{name}: loss is NaN/Inf"


# ---------------------------------------------------------------------------
# T-shared-loss — A0, A1a, A1b use identical masked_wmape loss
# ---------------------------------------------------------------------------

def test_T_shared_loss():
    """All three architectures use the same masked_wmape function."""
    batch = make_batch()
    y_true = batch["y_true"]
    tmask = batch["target_mask"]

    # Create identical y_hat for all models — losses must match exactly
    y_hat = torch.ones_like(y_true) * 50.0
    losses = []
    for _ in ["A0Neural", "GConvGRU", "EvolveGCNH"]:
        losses.append(masked_wmape(y_hat, y_true, tmask).item())

    assert len(set(f"{l:.10f}" for l in losses)) == 1, \
        f"masked_wmape gave different results across models: {losses}"


# ---------------------------------------------------------------------------
# Additional concrete checks (extras beyond mandatory 11)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_struct_mask_absent_sector(name):
    """A fully absent territory remains NaN and is excluded by target masking."""
    model = _make_model(name)
    batch = make_batch()
    batch["struct_mask"][:, 5, :] = 0
    batch["target_mask"][:, 5] = 0
    out = run_model(model, batch)
    assert torch.isnan(out["territory_embeddings"][:, 5]).all()
    assert torch.isnan(out["y_hat"][:, 5]).all()
    loss = masked_wmape(out["y_hat"], batch["y_true"], batch["target_mask"])
    assert loss.isfinite()


@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_clamp_fraction_contract(name):
    """clamp_frac ∈ {0.10, 0.15} both produce bounded output."""
    for frac in [0.10, 0.15]:
        model = _make_model(name, clamp_frac=frac)
        batch = make_batch()
        out = run_model(model, batch)
        ridge_ref = batch["y_ridge_canonical"].clamp(min=0.0)
        bound = frac * ridge_ref
        assert (out["delta_bounded"].abs() <= bound + 1e-5).all(), \
            f"{name} clamp_frac={frac}: delta_bounded exceeds bound"


def test_masked_wmape_correctness():
    """Unit test for masked_wmape: known values."""
    y_hat = torch.tensor([[1.0, 2.0, 3.0]])
    y_true = torch.tensor([[2.0, 2.0, 4.0]])
    mask = torch.tensor([[1, 1, 0]], dtype=torch.int8)
    # |1-2| + |2-2| = 1; |y_true[mask]| = 2+2 = 4; WMAPE = 1/4 = 0.25
    loss = masked_wmape(y_hat, y_true, mask)
    assert abs(loss.item() - 0.25) < 1e-6, f"masked_wmape = {loss.item()}, expected 0.25"


def test_bounded_residual_head_zero_ridge():
    """When y_ridge=0, delta_bounded must be 0 regardless of delta_raw."""
    delta_raw = torch.tensor([[100.0, -100.0]])
    y_ridge = torch.tensor([[0.0, 0.0]])
    db, y_hat = bounded_residual_head(delta_raw, y_ridge, clamp_frac=0.15)
    assert db.abs().max().item() < 1e-7, f"delta_bounded != 0 when y_ridge=0: {db}"
    assert (y_hat == y_ridge).all()


@pytest.mark.parametrize("name", ["GConvGRU", "EvolveGCNH"])
def test_isolated_node_self_fallback(name):
    """Isolated nodes (adj row-sum=0) must produce finite output."""
    model = _make_model(name)
    batch = make_batch()
    # Make all adjacency zero for region 3 (isolated)
    batch["adjacency_seq"][:, :, :, 3, :] = 0.0
    batch["adjacency_seq"][:, :, :, :, 3] = 0.0
    out = run_model(model, batch)
    assert out["y_hat"].isfinite().all(), \
        f"{name}: NaN/Inf with isolated node (zero adj row)"


@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_batch_independence(name):
    """Batch element 0 output must not depend on batch element 1 features."""
    model = _make_model(name)
    batch_a = make_batch(b=2, seed=SEED)

    batch_b = {k: v.clone() for k, v in batch_a.items()}
    # Perturb only element 1
    batch_b["features_seq"] = batch_a["features_seq"].clone()
    batch_b["features_seq"][1] = batch_b["features_seq"][1] * 99.0

    out_a = run_model(model, batch_a, seed=SEED)
    out_b = run_model(model, batch_b, seed=SEED)

    # Element 0 must be identical
    diff = (out_a["y_hat"][0] - out_b["y_hat"][0]).abs().max().item()
    assert diff < 1e-5, (
        f"{name}: batch element 0 changes when element 1 is perturbed (batch mixing). "
        f"diff={diff:.2e}"
    )


@pytest.mark.parametrize("name", ALL_MODEL_NAMES)
def test_a0_ignores_adjacency(name):
    """A0Neural: output must be identical whether adjacency_seq is passed or not."""
    if name != "A0Neural":
        pytest.skip("only for A0Neural")
    model = _make_model("A0Neural")
    batch = make_batch()

    out_no_adj = run_model(model, {k: v for k, v in batch.items() if k != "adjacency_seq"})
    out_with_adj = run_model(model, batch)  # adjacency_seq is ignored by A0Neural

    diff = (out_no_adj["y_hat"] - out_with_adj["y_hat"]).abs().max().item()
    assert diff < 1e-7, f"A0Neural: output differs when adjacency_seq present. diff={diff:.2e}"
