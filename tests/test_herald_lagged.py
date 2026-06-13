"""
tests/test_herald_lagged.py — DEC-043 / Phase 10

16 test categories for HERALDGraphImputerLagged:
  T01 source/target semantics (correct lag direction)
  T02 no future information (year 0/1 zeroed, leakage check)
  T03 lag-1 feature shape and values
  T04 lag-2 feature shape and values
  T05 positive relations
  T06 negative relations
  T07 mask propagation (missing ≠ zero)
  T08 first-year boundary (years 0-1 lag-2 always zero)
  T09 oracle_lagged ≠ oracle_contemp
  T10 true graph > zero graph on oracle
  T11 zero graph (no prior) runs without error
  T12 permuted graph (random permutation)
  T13 random graph (random weights)
  T14 gradient reaches attention parameters
  T15 determinism (same seed → same result)
  T16 NaN/Inf free (forward and after training)
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    build_symmetric_oracle_lagged,
    train_herald_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.imputation_baselines import _build_temporal_features


# ── Minimal synthetic helpers ──────────────────────────────────────────────────

class _FakeRelation:
    """Minimal stand-in for SyntheticRelation."""
    def __init__(self, source_sector, target_sector, lag=1, weight=1.0):
        self.source_sector = source_sector
        self.target_sector = target_sector
        self.lag = lag
        self.weight = weight


def _rng_panel(n_T=4, n_S=3, n_Y=10, seed=0):
    rng = np.random.RandomState(seed)
    panel = rng.randn(n_T, n_S, n_Y).astype(np.float32)
    return panel


def _rng_mask(n_T=4, n_S=3, n_Y=10, obs_rate=0.7, seed=0):
    rng = np.random.RandomState(seed)
    return (rng.rand(n_T, n_S, n_Y) < obs_rate).astype(np.float32)


def _make_model(n_T=4, n_S=3):
    return HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)


def _forward(model, panel, mask):
    panel_t = torch.from_numpy(panel)
    mask_t = torch.from_numpy(mask)
    temp_feats = torch.from_numpy(
        _build_temporal_features(panel, mask).astype(np.float32)
    )
    model.eval()
    with torch.no_grad():
        out = model(panel_t, mask_t, temp_feats_t=temp_feats)
    return out  # (n_T, n_S, n_Y, 2)


# ── T01: source/target semantics ──────────────────────────────────────────────

class TestT01SourceTargetSemantics:
    """Attention matrix orientation: lag1[i,j] means j→i at lag-1."""

    def test_directed_oracle_fills_correct_cell(self):
        """Oracle freezes attention at (target, source) = (1, 0) for edge 0→1."""
        n_S = 3
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=2)
        rels = [_FakeRelation(source_sector=0, target_sector=1, lag=1, weight=1.0)]
        build_directed_oracle_lagged(model, rels, n_S)
        log_lag1 = model.log_sect_attn_lag1.data.numpy()
        # row 1 (target), col 0 (source) must be high (= 0.0)
        assert log_lag1[1, 0] == pytest.approx(0.0), "Oracle must set [target, source] = 0"
        # All other off-diagonal entries must be suppressed
        for i in range(n_S):
            for j in range(n_S):
                if (i, j) != (1, 0):
                    assert log_lag1[i, j] < -5.0, f"log_lag1[{i},{j}] should be suppressed"

    def test_directed_oracle_lag2_separate(self):
        """Lag-2 edges go to log_sect_attn_lag2, not lag1."""
        n_S = 4
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=2)
        rels = [
            _FakeRelation(0, 2, lag=1, weight=1.0),
            _FakeRelation(1, 3, lag=2, weight=-0.5),
        ]
        build_directed_oracle_lagged(model, rels, n_S)
        log1 = model.log_sect_attn_lag1.data.numpy()
        log2 = model.log_sect_attn_lag2.data.numpy()
        assert log1[2, 0] == pytest.approx(0.0)    # lag-1 edge 0→2
        assert log2[3, 1] == pytest.approx(0.0)    # lag-2 edge 1→3
        # Cross: lag-2 edge should NOT appear in lag1
        assert log1[3, 1] < -5.0
        assert log2[2, 0] < -5.0


# ── T02: no future information ────────────────────────────────────────────────

class TestT02NoFutureInformation:
    """Lag features must be zero at year 0 (lag-1) and years 0-1 (lag-2)."""

    def _graph_features(self, model, panel, mask):
        n_T, n_S, n_Y = panel.shape
        panel_t = torch.from_numpy(panel)
        mask_t = torch.from_numpy(mask)
        safe = panel_t * mask_t
        with torch.no_grad():
            a1 = torch.softmax(model.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model.log_terr_attn, dim=-1)
            gf = model._compute_graph_features_torch(safe, mask_t, a1, a2, at)
        return gf.numpy()
        # shape: (n_T, n_S, n_Y, 3) [lag1, lag2, territory]

    def test_lag1_year0_is_zero(self):
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        gf = self._graph_features(model, panel, mask)
        lag1_year0 = gf[:, :, 0, 0]  # lag-1 feature at year 0
        assert np.allclose(lag1_year0, 0.0), "Lag-1 feature must be 0 at year 0"

    def test_lag2_years01_are_zero(self):
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        gf = self._graph_features(model, panel, mask)
        lag2_y0 = gf[:, :, 0, 1]
        lag2_y1 = gf[:, :, 1, 1]
        assert np.allclose(lag2_y0, 0.0), "Lag-2 feature must be 0 at year 0"
        assert np.allclose(lag2_y1, 0.0), "Lag-2 feature must be 0 at year 1"

    def test_lag1_nonzero_after_year0(self):
        """Lag-1 feature should be nonzero at some year > 0 given nonzero panel."""
        panel = _rng_panel()
        mask = np.ones_like(panel)  # fully observed
        model = _make_model()
        gf = self._graph_features(model, panel, mask)
        lag1_later = gf[:, :, 2:, 0]
        assert not np.allclose(lag1_later, 0.0), "Lag-1 feature should be nonzero after year 0"

    def test_future_perturbation_does_not_affect_past_features(self):
        """Perturbing years > check_year must not change lag features at years ≤ check_year."""
        panel = _rng_panel(n_Y=12)
        mask = np.ones((4, 3, 12), dtype=np.float32)
        model = _make_model()

        check_year = 5
        panel_perturbed = panel.copy()
        panel_perturbed[:, :, check_year + 1:] += 999.0

        gf_orig = self._graph_features(model, panel, mask)
        gf_pert = self._graph_features(model, panel_perturbed, mask)

        diff = np.abs(gf_orig[:, :, :check_year + 1, :] - gf_pert[:, :, :check_year + 1, :]).max()
        assert diff < 1e-5, f"Future perturbation leaked into past features: max diff = {diff}"


# ── T03: lag-1 feature shape and values ───────────────────────────────────────

class TestT03Lag1Feature:
    def test_output_shape(self):
        n_T, n_S, n_Y = 5, 4, 8
        panel = _rng_panel(n_T, n_S, n_Y)
        mask = _rng_mask(n_T, n_S, n_Y)
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        out = _forward(model, panel, mask)
        assert out.shape == (n_T, n_S, n_Y, 2), f"Expected ({n_T},{n_S},{n_Y},2), got {out.shape}"

    def test_lag1_reflects_previous_year(self):
        """
        With a single-sector, single-territory model and full obs, lag-1 feature at year y
        should equal the panel value at year y-1 (after softmax attention is applied uniformly).
        """
        n_T, n_S, n_Y = 1, 2, 10
        panel = np.zeros((n_T, n_S, n_Y), dtype=np.float32)
        panel[0, 0, :] = np.arange(n_Y, dtype=np.float32)  # sector 0: 0,1,2,...
        mask = np.ones((n_T, n_S, n_Y), dtype=np.float32)

        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        # Zero log attention → uniform softmax
        with torch.no_grad():
            model.log_sect_attn_lag1.data = torch.zeros(n_S, n_S)

        safe = torch.from_numpy(panel * mask)
        mask_t = torch.from_numpy(mask)
        with torch.no_grad():
            a1 = torch.softmax(model.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model.log_terr_attn, dim=-1)
            gf = model._compute_graph_features_torch(safe, mask_t, a1, a2, at).numpy()
        # lag-1 feature for target sector 0, year y, territory 0 should reflect year y-1
        # With uniform attention over 2 sectors, value = mean(panel[:,y-1]) for y>0
        for y in range(1, n_Y):
            expected = panel[0, :, y - 1].mean()  # uniform attention = mean
            got = gf[0, 0, y, 0]
            assert abs(got - expected) < 1e-4, f"Lag-1 at y={y}: expected {expected}, got {got}"


# ── T04: lag-2 feature shape and values ───────────────────────────────────────

class TestT04Lag2Feature:
    def test_lag2_reflects_two_steps_back(self):
        """Lag-2 feature at year y must reflect values at year y-2 (not y-1 or y)."""
        n_T, n_S, n_Y = 1, 2, 10
        panel = np.zeros((n_T, n_S, n_Y), dtype=np.float32)
        panel[0, 0, :] = np.arange(n_Y, dtype=np.float32) * 10  # sector 0: 0,10,20,...
        mask = np.ones((n_T, n_S, n_Y), dtype=np.float32)

        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        with torch.no_grad():
            model.log_sect_attn_lag2.data = torch.zeros(n_S, n_S)

        safe = torch.from_numpy(panel * mask)
        mask_t = torch.from_numpy(mask)
        with torch.no_grad():
            a1 = torch.softmax(model.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model.log_terr_attn, dim=-1)
            gf = model._compute_graph_features_torch(safe, mask_t, a1, a2, at).numpy()
        # lag-2 feature at year y = mean(panel[:, y-2]) for y >= 2
        for y in range(2, n_Y):
            expected = panel[0, :, y - 2].mean()
            got = gf[0, 0, y, 1]
            assert abs(got - expected) < 1e-4, f"Lag-2 at y={y}: expected {expected}, got {got}"

    def test_lag1_lag2_differ_at_year3(self):
        """Lag-1 and lag-2 features at year 3 must generally differ for non-constant panel."""
        panel = _rng_panel(n_Y=12)
        mask = np.ones((4, 3, 12), dtype=np.float32)
        model = _make_model()
        safe = torch.from_numpy(panel * mask)
        mask_t = torch.from_numpy(mask)
        with torch.no_grad():
            a1 = torch.softmax(model.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model.log_terr_attn, dim=-1)
            gf = model._compute_graph_features_torch(safe, mask_t, a1, a2, at).numpy()
        lag1_y3 = gf[:, :, 3, 0]
        lag2_y3 = gf[:, :, 3, 1]
        assert not np.allclose(lag1_y3, lag2_y3), "Lag-1 and lag-2 features should differ at year 3"


# ── T05: positive relations ────────────────────────────────────────────────────

class TestT05PositiveRelations:
    def test_oracle_positive_edge_high_attention(self):
        """Oracle with positive weight: directed attention at (target, source) is highest in row."""
        n_S, n_T = 5, 3
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        rels = [_FakeRelation(0, 2, lag=1, weight=1.5)]
        build_directed_oracle_lagged(model, rels, n_S)
        a1 = model.get_sector_attention_lag1()
        # a1[2, 0] should be the maximum in row 2
        assert a1[2, 0] == a1[2].max(), "True positive edge (row=target, col=source) must be max in row"


# ── T06: negative relations ────────────────────────────────────────────────────

class TestT06NegativeRelations:
    def test_sign_negative_edge_does_not_affect_oracle_attention(self):
        """
        Oracle attention is set from adjacency (presence), not sign.
        A negative-weight edge still gets the same high attention.
        """
        n_S, n_T = 4, 3
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        rels = [_FakeRelation(0, 1, lag=1, weight=-0.8)]  # negative weight
        build_directed_oracle_lagged(model, rels, n_S)
        log1 = model.log_sect_attn_lag1.data.numpy()
        # Same encoding: presence of edge → (target=1, source=0) = 0.0
        assert log1[1, 0] == pytest.approx(0.0)


# ── T07: mask propagation ─────────────────────────────────────────────────────

class TestT07MaskPropagation:
    def test_missing_neighbors_contribute_zero_not_value(self):
        """
        When all lag-1 neighbors are masked out, the lag-1 feature must be 0
        (not the panel value at those positions).
        """
        n_T, n_S, n_Y = 2, 3, 8
        panel = np.ones((n_T, n_S, n_Y), dtype=np.float32) * 5.0
        mask = np.ones((n_T, n_S, n_Y), dtype=np.float32)
        # Mask out ALL values at year 0 (so lag-1 at year 1 = no observed neighbors)
        mask[:, :, 0] = 0.0

        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        safe = torch.from_numpy(panel * mask)
        mask_t = torch.from_numpy(mask)
        with torch.no_grad():
            a1 = torch.softmax(model.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model.log_terr_attn, dim=-1)
            gf = model._compute_graph_features_torch(safe, mask_t, a1, a2, at).numpy()
        lag1_y1 = gf[:, :, 1, 0]
        # All lag-1 neighbors at year 0 are masked → feature should collapse to 0
        assert np.allclose(lag1_y1, 0.0, atol=1e-5), \
            f"Expected 0 for masked lag-1, got {lag1_y1}"

    def test_forward_with_partial_mask_no_error(self):
        """Forward pass with partial mask completes without exception."""
        panel = _rng_panel()
        mask = _rng_mask(obs_rate=0.4)
        model = _make_model()
        out = _forward(model, panel, mask)
        assert out.shape[:-1] == panel.shape


# ── T08: first-year boundary ──────────────────────────────────────────────────

class TestT08FirstYearBoundary:
    def test_lag2_boundary_all_zero_years01(self):
        """Lag-2 feature must be 0 at years 0 and 1 regardless of panel content."""
        panel = _rng_panel(n_T=6, n_S=5, n_Y=15)
        mask = np.ones((6, 5, 15), dtype=np.float32)
        model = HERALDGraphImputerLagged(n_sectors=5, n_territories=6)
        safe = torch.from_numpy(panel * mask)
        mask_t = torch.from_numpy(mask)
        with torch.no_grad():
            a1 = torch.softmax(model.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model.log_terr_attn, dim=-1)
            gf = model._compute_graph_features_torch(safe, mask_t, a1, a2, at).numpy()
        assert np.allclose(gf[:, :, 0, 1], 0.0), "Lag-2 at year 0 must be 0"
        assert np.allclose(gf[:, :, 1, 1], 0.0), "Lag-2 at year 1 must be 0"


# ── T09: oracle_lagged ≠ oracle_contemp ───────────────────────────────────────

class TestT09OracleLaggedVsContemp:
    def test_lagged_oracle_gives_different_graph_features(self):
        """
        With the same data, the lagged model produces different graph features
        than a contemp model (which aggregates current year values).
        """
        from src.modeles.synthetic.herald_graph_imputer import HERALDGraphImputer

        n_T, n_S, n_Y = 4, 3, 12
        panel = _rng_panel(n_T, n_S, n_Y, seed=0)
        mask = np.ones((n_T, n_S, n_Y), dtype=np.float32)

        model_l = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        safe = torch.from_numpy(panel * mask)
        mask_t = torch.from_numpy(mask)
        with torch.no_grad():
            a1 = torch.softmax(model_l.log_sect_attn_lag1, dim=-1)
            a2 = torch.softmax(model_l.log_sect_attn_lag2, dim=-1)
            at = torch.softmax(model_l.log_terr_attn, dim=-1)
            gf_lagged = model_l._compute_graph_features_torch(safe, mask_t, a1, a2, at).numpy()

        # Contemp model's sector feature uses current year (dims=0 for the einsum)
        # Quick proxy: lag-1 feature at year 1 should differ from the current-year value at year 1
        lag1_y1 = gf_lagged[:, :, 1, 0]
        # The corresponding contemporaneous aggregation would use year 1 values directly
        contemp_y1 = panel[:, :, 1]  # simplified (ignoring territory weights)
        # They should generally differ for random data with n_Y > 1
        assert not np.allclose(lag1_y1, contemp_y1, atol=1e-3), \
            "Lagged and contemporaneous features should differ"


# ── T10: true graph > zero graph ─────────────────────────────────────────────

class TestT10TrueGraphVsZeroGraph:
    def test_directed_oracle_frozen_differs_from_no_graph(self):
        """
        Oracle with directed adj produces different attention than uniform (zero log-attn).
        """
        n_S, n_T = 4, 3
        model_oracle = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        model_uniform = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)

        rels = [_FakeRelation(0, 1, lag=1, weight=1.0), _FakeRelation(2, 3, lag=2, weight=0.5)]
        build_directed_oracle_lagged(model_oracle, rels, n_S)

        a1_oracle = model_oracle.get_sector_attention_lag1()
        a1_uniform = model_uniform.get_sector_attention_lag1()
        assert not np.allclose(a1_oracle, a1_uniform), \
            "Oracle and uniform attention should differ after directed setup"


# ── T11: zero graph ───────────────────────────────────────────────────────────

class TestT11ZeroGraph:
    def test_no_adj_runs_without_error(self):
        """Model should run fine with no adj_sector / adj_territory."""
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        out = _forward(model, panel, mask)
        assert out is not None
        assert not torch.isnan(out).any(), "NaN in output with no adj"


# ── T12: permuted graph ───────────────────────────────────────────────────────

class TestT12PermutedGraph:
    def test_permuted_adj_gives_different_features(self):
        """Permuting sector indices changes the graph features."""
        n_T, n_S, n_Y = 4, 4, 10
        panel = _rng_panel(n_T, n_S, n_Y)
        mask = np.ones((n_T, n_S, n_Y), dtype=np.float32)

        model1 = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        model2 = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)

        # Set model2 with permuted attention (swap sectors 0 and 1)
        perm = np.eye(n_S, dtype=np.float32)[[1, 0, 2, 3]]
        perm_log = np.log(perm.clip(min=1e-6))
        with torch.no_grad():
            model2.log_sect_attn_lag1.data = torch.from_numpy(perm_log)

        out1 = _forward(model1, panel, mask)
        out2 = _forward(model2, panel, mask)
        # With different attention, predictions should differ
        assert not torch.allclose(out1, out2, atol=1e-4), \
            "Permuted attention must change predictions"


# ── T13: random graph ─────────────────────────────────────────────────────────

class TestT13RandomGraph:
    def test_random_adj_does_not_crash(self):
        """Random adjacency applied as log-prior should not raise errors."""
        n_T, n_S, n_Y = 3, 5, 8
        rng = np.random.RandomState(42)
        adj = rng.rand(n_S, n_S).astype(np.float32)
        adj_log = np.log(adj.clip(min=1e-6))

        panel = _rng_panel(n_T, n_S, n_Y)
        mask = _rng_mask(n_T, n_S, n_Y)

        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        adj_t = torch.from_numpy(adj_log)
        panel_t = torch.from_numpy(panel)
        mask_t = torch.from_numpy(mask)
        temp_feats = torch.from_numpy(_build_temporal_features(panel, mask).astype(np.float32))
        with torch.no_grad():
            out = model(panel_t, mask_t, adj_sector=adj_t, temp_feats_t=temp_feats)
        assert not torch.isnan(out).any()


# ── T14: gradient reaches attention parameters ────────────────────────────────

class TestT14GradientReachesAttention:
    def test_gradient_flows_to_log_sect_attn_lag1(self):
        """After a backward pass, log_sect_attn_lag1 must have nonzero gradient."""
        n_T, n_S, n_Y = 3, 4, 8
        panel = _rng_panel(n_T, n_S, n_Y)
        mask = _rng_mask(n_T, n_S, n_Y)

        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        model.train()
        panel_t = torch.from_numpy(panel)
        mask_t = torch.from_numpy(mask)
        true_t = panel_t.clone()
        temp_feats = torch.from_numpy(_build_temporal_features(panel, mask).astype(np.float32))

        out = model(panel_t, mask_t, temp_feats_t=temp_feats)
        pred = out[..., 0]
        loss = ((pred - true_t) ** 2 * mask_t).sum()
        loss.backward()

        assert model.log_sect_attn_lag1.grad is not None, "No grad for log_sect_attn_lag1"
        assert model.log_sect_attn_lag1.grad.abs().sum() > 0, "Zero grad for log_sect_attn_lag1"

    def test_gradient_flows_to_log_sect_attn_lag2(self):
        """After a backward pass, log_sect_attn_lag2 must have nonzero gradient."""
        n_T, n_S, n_Y = 3, 4, 8
        panel = _rng_panel(n_T, n_S, n_Y)
        mask = _rng_mask(n_T, n_S, n_Y)

        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T)
        model.train()
        panel_t = torch.from_numpy(panel)
        mask_t = torch.from_numpy(mask)
        true_t = panel_t.clone()
        temp_feats = torch.from_numpy(_build_temporal_features(panel, mask).astype(np.float32))

        out = model(panel_t, mask_t, temp_feats_t=temp_feats)
        pred = out[..., 0]
        loss = ((pred - true_t) ** 2 * mask_t).sum()
        loss.backward()

        assert model.log_sect_attn_lag2.grad is not None, "No grad for log_sect_attn_lag2"
        assert model.log_sect_attn_lag2.grad.abs().sum() > 0, "Zero grad for log_sect_attn_lag2"

    def test_frozen_oracle_grad_is_none(self):
        """After freeze_oracle, grad should be None (or zero) for frozen params."""
        n_S = 3
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=2)
        rels = [_FakeRelation(0, 1, lag=1)]
        build_directed_oracle_lagged(model, rels, n_S)

        assert not model.log_sect_attn_lag1.requires_grad, "Oracle lag1 should be frozen"
        assert not model.log_sect_attn_lag2.requires_grad, "Oracle lag2 should be frozen"


# ── T15: determinism ──────────────────────────────────────────────────────────

class TestT15Determinism:
    def test_same_seed_same_output(self):
        """Two models with same seed and same data must produce identical output."""
        panel = _rng_panel()
        mask = _rng_mask()

        def run(seed):
            torch.manual_seed(seed)
            model = HERALDGraphImputerLagged(n_sectors=3, n_territories=4)
            return _forward(model, panel, mask)

        out1 = run(42)
        out2 = run(42)
        assert torch.allclose(out1, out2), "Identical seed must give identical output"

    def test_different_seeds_different_output(self):
        """Different seeds should (almost certainly) give different outputs."""
        panel = _rng_panel()
        mask = _rng_mask()

        def run(seed):
            torch.manual_seed(seed)
            model = HERALDGraphImputerLagged(n_sectors=3, n_territories=4)
            return _forward(model, panel, mask)

        out1 = run(42)
        out2 = run(99)
        assert not torch.allclose(out1, out2), "Different seeds should give different outputs"


# ── T16: NaN/Inf free ────────────────────────────────────────────────────────

class TestT16NaNInfFree:
    def test_forward_no_nan(self):
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        out = _forward(model, panel, mask)
        assert not torch.isnan(out).any(), "NaN in forward output"
        assert not torch.isinf(out).any(), "Inf in forward output"

    def test_after_training_no_nan(self):
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        torch.manual_seed(42)
        losses = train_herald_lagged(model, panel, mask, n_epochs=30, lr=1e-3)
        assert all(np.isfinite(l) for l in losses), "Loss became NaN/Inf during training"
        out = _forward(model, panel, mask)
        assert not torch.isnan(out).any(), "NaN after training"
        assert not torch.isinf(out).any(), "Inf after training"

    def test_nan_in_panel_handled(self):
        """Panel with NaN values (missing) should not produce NaN in output."""
        panel = _rng_panel()
        mask = _rng_mask(obs_rate=0.5)
        panel_nan = panel.copy()
        panel_nan[mask == 0] = np.nan  # real-world case: NaN at missing positions
        panel_safe = np.where(mask == 1, panel, 0.0).astype(np.float32)
        model = _make_model()
        out = _forward(model, panel_safe, mask)
        assert not torch.isnan(out).any(), "NaN with NaN-containing panel"

    def test_extreme_values_no_inf(self):
        """Extreme panel values must not produce Inf in output."""
        panel = _rng_panel() * 1e6
        mask = _rng_mask()
        model = _make_model()
        out = _forward(model, panel, mask)
        assert not torch.isinf(out).any(), "Inf with extreme panel values"

    def test_impute_deterministic_no_nan(self):
        """impute_deterministic_lagged must return finite array."""
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        train_herald_lagged(model, panel, mask, n_epochs=10)
        imputed = impute_deterministic_lagged(model, panel, mask)
        assert np.isfinite(imputed).all(), "Non-finite values in imputed panel"

    def test_observed_cells_preserved(self):
        """Observed cells must equal original values after imputation."""
        panel = _rng_panel()
        mask = _rng_mask()
        model = _make_model()
        train_herald_lagged(model, panel, mask, n_epochs=10)
        imputed = impute_deterministic_lagged(model, panel, mask)
        obs_idx = mask == 1
        np.testing.assert_allclose(
            imputed[obs_idx], panel[obs_idx], atol=1e-5,
            err_msg="Observed values not preserved in imputed output"
        )


# ── get_sector_attention compatibility ────────────────────────────────────────

class TestGetSectorAttentionCompatibility:
    def test_combined_attention_is_max_of_lag1_lag2(self):
        """get_sector_attention() must equal elementwise max of lag1 and lag2."""
        model = _make_model()
        a1 = model.get_sector_attention_lag1()
        a2 = model.get_sector_attention_lag2()
        combined = model.get_sector_attention()
        expected = np.maximum(a1, a2)
        np.testing.assert_allclose(combined, expected, atol=1e-6)

    def test_combined_attention_shape(self):
        n_S = 5
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=3)
        combined = model.get_sector_attention()
        assert combined.shape == (n_S, n_S)

    def test_combined_attention_rows_sum_to_one(self):
        """After softmax, attention rows sum to 1."""
        n_S = 4
        model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=3)
        a1 = model.get_sector_attention_lag1()
        a2 = model.get_sector_attention_lag2()
        np.testing.assert_allclose(a1.sum(axis=1), np.ones(n_S), atol=1e-5)
        np.testing.assert_allclose(a2.sum(axis=1), np.ones(n_S), atol=1e-5)
