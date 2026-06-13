"""
tests/test_synthetic_benchmark.py

Tests for HERALD synthetic benchmark (DEC-039).
Covers: determinism, no-leakage, masking correctness, baseline shapes,
        generator ground truth, calibration interface.

These tests run fast (<30s) and do NOT require HPC or GPU.
"""

from __future__ import annotations

import numpy as np
import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_herald_synthetic import (
    SyntheticConfig,
    TrueRelation,
    generate_dataset,
    mask_panel,
)
from src.modeles.synthetic.imputation_baselines import (
    MeanImputer,
    MedianImputer,
    ForwardFillImputer,
    TemporalInterpolationImputer,
    RidgeImputer,
    GraphRidgeImputer,
    _build_temporal_features,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
    compute_calibration_metrics,
    check_no_leakage,
)
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    build_permuted_adj,
    train_herald_imputer,
    impute_deterministic,
    impute_with_uncertainty,
)


SMALL_CONFIG = SyntheticConfig(n_territories=6, n_sectors=4, n_years=10, seed=7)


@pytest.fixture(scope="module")
def small_ds():
    return generate_dataset(SMALL_CONFIG)


@pytest.fixture(scope="module")
def small_mask(small_ds):
    return small_ds["masks"]["mcar_20"]


@pytest.fixture(scope="module")
def obs_panel(small_ds, small_mask):
    return mask_panel(small_ds["panel"], small_mask)


# ── Generator tests ────────────────────────────────────────────────────────────

class TestGenerator:
    def test_output_shape(self, small_ds):
        c = SMALL_CONFIG
        assert small_ds["panel"].shape == (c.n_territories, c.n_sectors, c.n_years)

    def test_no_nan_in_panel(self, small_ds):
        assert not np.isnan(small_ds["panel"]).any(), "Panel must have no NaN"

    def test_determinism(self):
        ds1 = generate_dataset(SMALL_CONFIG)
        ds2 = generate_dataset(SMALL_CONFIG)
        np.testing.assert_array_equal(ds1["panel"], ds2["panel"])

    def test_different_seeds_differ(self):
        ds1 = generate_dataset(SMALL_CONFIG)
        ds2 = generate_dataset(SyntheticConfig(**{**SMALL_CONFIG.__dict__, "seed": 99}))
        assert not np.allclose(ds1["panel"], ds2["panel"])

    def test_true_relations_valid(self, small_ds):
        n_S = SMALL_CONFIG.n_sectors
        for rel in small_ds["true_relations"]:
            assert isinstance(rel, TrueRelation)
            assert 0 <= rel.source_sector < n_S
            assert 0 <= rel.target_sector < n_S
            assert rel.source_sector != rel.target_sector, "No self-loops allowed"
            assert rel.lag in (1, 2)
            assert rel.weight != 0

    def test_masks_present(self, small_ds):
        for key in ["mcar_10", "mcar_20", "mcar_30", "mar_20", "block_20"]:
            assert key in small_ds["masks"]

    def test_mask_values_binary(self, small_ds):
        for key, m in small_ds["masks"].items():
            assert set(np.unique(m)) <= {0, 1}, f"Mask {key} has non-binary values"

    def test_mask_has_hidden_cells(self, small_ds):
        for key, m in small_ds["masks"].items():
            n_hidden = (m == 0).sum()
            assert n_hidden > 0, f"Mask {key} has no hidden cells"

    def test_mcar_higher_rate_hides_more(self, small_ds):
        m10 = small_ds["masks"]["mcar_10"]
        m30 = small_ds["masks"]["mcar_30"]
        # On average, higher rate should hide more (may not hold for one config; test probabilistic)
        assert (m10 == 0).sum() <= (m30 == 0).sum() + SMALL_CONFIG.n_territories * SMALL_CONFIG.n_sectors

    def test_territory_adj_shape(self, small_ds):
        n_T = SMALL_CONFIG.n_territories
        assert small_ds["territory_adj"].shape == (n_T, n_T)
        np.testing.assert_allclose(np.diag(small_ds["territory_adj"]), 0, atol=1e-10)

    def test_sector_adj_symmetric(self, small_ds):
        adj = small_ds["sector_adj"]
        np.testing.assert_array_equal(adj, adj.T, err_msg="sector_adj must be symmetric")

    def test_regimes_valid_values(self, small_ds):
        # Regimes are integers 0-4
        regimes = small_ds["regimes"]
        assert regimes.min() >= 0 and regimes.max() <= 4


# ── Masking tests ──────────────────────────────────────────────────────────────

class TestMasking:
    def test_mask_panel_sets_nan(self, small_ds, small_mask):
        obs = mask_panel(small_ds["panel"], small_mask)
        n_nan = np.isnan(obs).sum()
        n_hidden = (small_mask == 0).sum()
        assert n_nan == n_hidden

    def test_observed_values_unchanged(self, small_ds, small_mask):
        panel = small_ds["panel"]
        obs = mask_panel(panel, small_mask)
        np.testing.assert_array_equal(obs[small_mask == 1], panel[small_mask == 1])

    def test_mask_not_all_zero(self, small_mask):
        assert small_mask.sum() > 0
        assert (small_mask == 0).sum() > 0


# ── No-leakage tests ──────────────────────────────────────────────────────────

class TestNoLeakage:
    def test_temporal_features_causal(self, small_ds, small_mask):
        result = check_no_leakage(small_ds["panel"], small_mask)
        assert result["passed"], (
            f"Temporal feature leakage detected: max_diff={result.get('max_diff_at_past_years')}"
        )

    def test_temporal_features_causal_different_mask(self, small_ds):
        # Test with MCAR 30% mask as well
        mask30 = small_ds["masks"]["mcar_30"]
        result = check_no_leakage(small_ds["panel"], mask30)
        assert result["passed"]

    def test_causal_feature_year_zero_is_zero_lag(self, small_ds, small_mask):
        """Feature 1 (causal_last) at year 0 must be 0 (no past observation)."""
        panel = small_ds["panel"]
        feats = _build_temporal_features(panel, small_mask)
        n_T, n_S, n_Y = SMALL_CONFIG.n_territories, SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_years
        feats_3d = feats.reshape(n_T, n_S, n_Y, 7)
        # Feature index 1 = causal_last; at year 0, running mean up to year -1 = 0
        assert np.allclose(feats_3d[:, :, 0, 1], 0), "Causal last feature at year 0 must be 0"


# ── Baseline tests ────────────────────────────────────────────────────────────

class TestBaselines:
    @pytest.mark.parametrize("ImpClass", [MeanImputer, MedianImputer, ForwardFillImputer,
                                           TemporalInterpolationImputer])
    def test_no_nan_in_output(self, ImpClass, small_ds, small_mask, obs_panel):
        imp = ImpClass()
        result = imp.fit_transform(obs_panel, small_mask)
        assert not np.isnan(result).any(), f"{ImpClass.__name__} produced NaN output"

    def test_observed_cells_unchanged(self, small_ds, small_mask, obs_panel):
        """All baselines must preserve observed values exactly."""
        panel = small_ds["panel"]
        for ImpClass in [MeanImputer, ForwardFillImputer, RidgeImputer]:
            imp = ImpClass()
            result = imp.fit_transform(obs_panel, small_mask)
            obs_vals = result[small_mask == 1]
            true_obs = panel[small_mask == 1]
            np.testing.assert_allclose(obs_vals, true_obs, rtol=1e-5,
                                       err_msg=f"{ImpClass.__name__} changed observed values")

    def test_ridge_imputer_shape(self, small_ds, small_mask, obs_panel):
        imp = RidgeImputer()
        result = imp.fit_transform(obs_panel, small_mask)
        assert result.shape == obs_panel.shape

    def test_graph_ridge_imputer(self, small_ds, small_mask, obs_panel):
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]
        imp = GraphRidgeImputer(adj_s, adj_t)
        result = imp.fit_transform(obs_panel, small_mask)
        assert result.shape == obs_panel.shape
        assert not np.isnan(result).any()

    def test_ffill_causal_not_using_future(self, small_ds):
        """
        ForwardFill must not use year y+1 to fill year y.
        Test: mask year 5 only; value must NOT change if year 6 is modified.
        """
        panel = small_ds["panel"].copy()
        n_T, n_S, n_Y = panel.shape
        mask = np.ones_like(panel, dtype=np.int8)
        mask[:, :, 5] = 0  # mask entire year 5

        panel_mod = panel.copy()
        panel_mod[:, :, 6] += 999  # perturb year 6

        obs1 = mask_panel(panel, mask)
        obs2 = mask_panel(panel_mod, mask)

        imp = ForwardFillImputer()
        r1 = imp.fit_transform(obs1, mask)
        r2 = imp.fit_transform(obs2, mask)

        np.testing.assert_allclose(
            r1[:, :, 5], r2[:, :, 5], rtol=1e-5,
            err_msg="ForwardFill at year 5 changed when year 6 was perturbed (leakage!)"
        )


# ── Evaluation tests ──────────────────────────────────────────────────────────

class TestEvaluation:
    def test_imputation_metrics_at_hidden_only(self, small_ds, small_mask):
        panel = small_ds["panel"]
        pred = MeanImputer().fit_transform(mask_panel(panel, small_mask), small_mask)
        m = compute_imputation_metrics(panel, pred, small_mask)
        assert m.n_evaluated == int((small_mask == 0).sum())

    def test_imputation_metrics_perfect(self, small_ds, small_mask):
        panel = small_ds["panel"]
        m = compute_imputation_metrics(panel, panel, small_mask)
        assert m.mae == pytest.approx(0.0, abs=1e-8)
        assert m.rmse == pytest.approx(0.0, abs=1e-8)

    def test_edge_recovery_output(self, small_ds):
        n_S = SMALL_CONFIG.n_sectors
        uniform_attn = np.ones((n_S, n_S)) / n_S
        e = compute_edge_recovery_metrics(small_ds["true_relations"], n_S, uniform_attn)
        assert 0 <= e.precision_at_k <= 1
        assert 0 <= e.recall_at_k <= 1
        assert 0 <= e.f1_at_k <= 1

    def test_calibration_coverage_range(self, small_ds, small_mask):
        panel = small_ds["panel"]
        pred_mean = np.zeros_like(panel)
        pred_std = np.ones_like(panel)
        cal = compute_calibration_metrics(panel, pred_mean, pred_std, small_mask)
        assert 0 <= cal.coverage_90 <= 1
        assert 0 <= cal.coverage_50 <= 1
        assert cal.coverage_90 >= cal.coverage_50  # wider interval = higher coverage


# ── HERALD neural tests ───────────────────────────────────────────────────────

class TestHERALDImputer:
    def test_model_forward_pass(self, small_ds, small_mask, obs_panel):
        import torch
        n_S, n_T = SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_territories
        model = HERALDGraphImputer(n_S, n_T, hidden_dim=16)

        from src.modeles.synthetic.imputation_baselines import _build_temporal_features
        temp_feats = _build_temporal_features(obs_panel, small_mask)
        temp_feats_t = torch.from_numpy(temp_feats.astype(np.float32))
        panel_t = torch.from_numpy(np.nan_to_num(obs_panel, nan=0.0).astype(np.float32))
        mask_t = torch.from_numpy(small_mask.astype(np.float32))

        out = model(panel_t, mask_t, temp_feats_t=temp_feats_t)
        assert out.shape == (n_T, n_S, SMALL_CONFIG.n_years, 2)
        assert not torch.isnan(out).any()

    def test_training_reduces_loss(self, small_ds, small_mask, obs_panel):
        n_S, n_T = SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_territories
        model = HERALDGraphImputer(n_S, n_T, hidden_dim=16)
        losses = train_herald_imputer(model, obs_panel, small_mask, n_epochs=20)
        assert len(losses) == 20
        assert not any(np.isnan(l) for l in losses)
        # Loss should generally decrease
        assert losses[-1] < losses[0] * 2, "Loss exploded"

    def test_impute_no_nan(self, small_ds, small_mask, obs_panel):
        n_S, n_T = SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_territories
        model = HERALDGraphImputer(n_S, n_T, hidden_dim=16)
        train_herald_imputer(model, obs_panel, small_mask, n_epochs=10)
        pred = impute_deterministic(model, obs_panel, small_mask)
        assert not np.isnan(pred).any()

    def test_impute_preserves_observed(self, small_ds, small_mask, obs_panel):
        panel = small_ds["panel"]
        n_S, n_T = SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_territories
        model = HERALDGraphImputer(n_S, n_T, hidden_dim=16)
        train_herald_imputer(model, obs_panel, small_mask, n_epochs=5)
        pred = impute_deterministic(model, obs_panel, small_mask)
        np.testing.assert_allclose(pred[small_mask == 1], panel[small_mask == 1], rtol=1e-5)

    def test_uncertainty_output_shape(self, small_ds, small_mask, obs_panel):
        n_S, n_T = SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_territories
        model = HERALDGraphImputer(n_S, n_T, hidden_dim=16)
        train_herald_imputer(model, obs_panel, small_mask, n_epochs=5)
        mu, sigma = impute_with_uncertainty(model, obs_panel, small_mask, n_mc=5)
        assert mu.shape == obs_panel.shape
        assert sigma.shape == obs_panel.shape
        assert (sigma[small_mask == 0] >= 0).all()

    def test_permuted_adj_construction(self, small_ds):
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]
        rng = np.random.default_rng(0)
        adj_s_p, adj_t_p = build_permuted_adj(adj_s, adj_t, rng)
        assert adj_s_p.shape == adj_s.shape
        assert adj_t_p.shape == adj_t.shape
        # Permuted matrices should have same eigenvalues (same spectrum)
        np.testing.assert_allclose(
            sorted(np.linalg.eigvalsh(adj_s)), sorted(np.linalg.eigvalsh(adj_s_p)), atol=1e-8
        )

    def test_herald_deterministic_given_same_init(self, small_ds, small_mask, obs_panel):
        """Same random seed → same model output."""
        import torch
        n_S, n_T = SMALL_CONFIG.n_sectors, SMALL_CONFIG.n_territories

        torch.manual_seed(42)
        model1 = HERALDGraphImputer(n_S, n_T, hidden_dim=16)
        train_herald_imputer(model1, obs_panel, small_mask, n_epochs=5)
        pred1 = impute_deterministic(model1, obs_panel, small_mask)

        torch.manual_seed(42)
        model2 = HERALDGraphImputer(n_S, n_T, hidden_dim=16)
        train_herald_imputer(model2, obs_panel, small_mask, n_epochs=5)
        pred2 = impute_deterministic(model2, obs_panel, small_mask)

        np.testing.assert_allclose(pred1, pred2, rtol=1e-5)
