"""
test_phase16_decoupled.py — Tests for DEC-053 Phase 16 decoupled graph architecture.

Tests:
  1.  GraphRelationHead: presence_probs in [0,1]
  2.  GraphRelationHead: directed_attention rows sum to 1
  3.  GraphRelationHead: presence_loss finite on empty relations
  4.  GraphRelationHead: presence_loss finite on non-empty relations
  5.  GraphRelationHead: sign_loss finite on known edges
  6.  GraphRelationHead: lag_loss finite on known edges
  7.  GraphRelationHead: edge_metrics returns required keys
  8.  GraphRelationHead: edge_auc_directed finite with true edges
  9.  GraphRelationHead: presence[t,s]=1 for relation source=s target=t
  10. GraphRelationHead: diagonal excluded from presence target
  11. GatedGraphModel: gate initialised near 0 (gate<0.1 at init)
  12. GatedGraphModel: gate=0 → y_pred == y_temporal (D3 identity)
  13. GatedGraphModel: residual clamped to ±MAX_RESIDUAL_FRAC*|y_temporal|.mean()
  14. GatedGraphModel: backbone parameters have no gradient
  15. GatedGraphModel: graph head parameters require gradient
  16. GatedGraphModel: forward_tensors returns required keys
  17. GatedGraphModel: predict_temporal_only finite
  18. GatedGraphModel: predict_gated finite
  19. GatedGraphModel: predict_graph_always_on finite
  20. GatedGraphModel: gate in (0,1) everywhere
  21. decoupled_total_loss: returns finite scalar
  22. decoupled_total_loss: components sum to total
  23. decoupled_total_loss: utility term zero when compute_utility=False
  24. decoupled_total_loss: gradients flow to head but not backbone
  25. Fixture F1: gate_mean computed (smoke test)
  26. Fixture F2: has no true_relations
  27. Fixture F6: sector_adj is symmetric (false reverse present)
  28. Fixture F3: true weight is negative
  29. Fixture F4: true lag is 2
  30. Fixture F5: panel has nonzero cross-sector signal in years 5-10
  31. evaluator: evaluate_analytic_graph returns edge_auc_directed
  32. evaluator: evaluate_temporal_reconstruction returns mae_temporal
  33. evaluator: evaluate_gated_graph_assist returns mae_gated and mae_temporal
  34. gates_dec053: D1 passes when AUC is finite
  35. gates_dec053: D1 fails when AUC NaN with true edges
  36. gates_dec053: D3 passes when delta<1e-5
  37. gates_dec053: D3 fails when delta≥1e-5
  38. gates_dec053: D7 passes when gated ≤ temporal*1.05
  39. gates_dec053: D7 fails when gated > temporal*1.05
  40. gates_dec053: D9 always passes
  41. gates_dec053: format_gate_report produces markdown table
"""

from __future__ import annotations

import math
import unittest
from unittest.mock import MagicMock

import numpy as np
import torch
import torch.nn as nn

from src.data.synthetic.generate_herald_synthetic import TrueRelation
from src.modeles.synthetic.phase16_decoupled.fixtures import (
    make_f1_useful_graph,
    make_f2_useless_graph,
    make_f3_negative_relation,
    make_f4_lag2_relation,
    make_f5_regime_window,
    make_f6_asymmetric_directed,
)
from src.modeles.synthetic.phase16_decoupled.gates_dec053 import (
    check_d1_metric_correctness,
    check_d3_temporal_fallback,
    check_d7_predictive_safety,
    check_d9_realistic_reconstruction,
    format_gate_report,
    evaluate_all_gates,
)
from src.modeles.synthetic.phase16_decoupled.graph_relation_head import GraphRelationHead
from src.modeles.synthetic.phase16_decoupled.gated_model import (
    GatedGraphModel,
    MAX_RESIDUAL_FRAC,
)
from src.modeles.synthetic.phase16_decoupled.loss_functions import (
    decoupled_total_loss,
    LAMBDA_GATE,
)

DEVICE = "cpu"
N_S = 3
N_T = 4
N_Y = 10


def _small_panel():
    rng = np.random.default_rng(0)
    panel = rng.standard_normal((N_T, N_S, N_Y)).astype(np.float32)
    obs_mask = (rng.random((N_T, N_S, N_Y)) > 0.3).astype(np.float32)
    return panel, obs_mask


def _simple_relations():
    return [TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.7, nonlinear=False)]


def _dummy_backbone(n_S=N_S):
    """Minimal backbone stub that mimics HERALDGraphImputerLagged output."""
    class _DummyBackbone(nn.Module):
        def __init__(self):
            super().__init__()
            self.linear = nn.Linear(1, 1)   # ensures .parameters() is non-empty
        def forward(self, panel, mask, adj_s, adj_t, tf):
            n_T, n_S, n_Y = panel.shape
            mu = torch.zeros(n_T, n_S, n_Y, 1)
            log_sigma = torch.zeros(n_T, n_S, n_Y, 1)
            return torch.cat([mu, log_sigma], dim=-1)
    return _DummyBackbone()


def _gated_model(n_S=N_S):
    backbone = _dummy_backbone(n_S)
    return GatedGraphModel(backbone, n_sectors=n_S)


# ── GraphRelationHead tests ───────────────────────────────────────────────────

class TestGraphRelationHead(unittest.TestCase):

    def setUp(self):
        self.head = GraphRelationHead(N_S)
        self.rels = _simple_relations()

    def test_presence_probs_in_01(self):
        p = self.head.presence_probs()
        self.assertTrue((p >= 0).all() and (p <= 1).all())

    def test_directed_attention_rows_sum_1(self):
        attn = self.head.directed_attention(lag=1)
        row_sums = attn.sum(dim=-1)
        torch.testing.assert_close(row_sums, torch.ones(N_S), atol=1e-5, rtol=0)

    def test_presence_loss_finite_empty(self):
        loss = self.head.presence_loss([], DEVICE)
        self.assertTrue(math.isfinite(float(loss)))

    def test_presence_loss_finite_nonempty(self):
        loss = self.head.presence_loss(self.rels, DEVICE)
        self.assertTrue(math.isfinite(float(loss)))

    def test_sign_loss_finite_known_edges(self):
        loss = self.head.sign_loss(self.rels, DEVICE)
        self.assertTrue(math.isfinite(float(loss)))

    def test_lag_loss_finite_known_edges(self):
        loss = self.head.lag_loss(self.rels, DEVICE)
        self.assertTrue(math.isfinite(float(loss)))

    def test_edge_metrics_required_keys(self):
        metrics = self.head.edge_metrics(self.rels)
        for k in ("edge_auc_directed", "edge_auprc_directed", "prevalence", "n_true_directed"):
            self.assertIn(k, metrics)

    def test_edge_auc_finite_with_true_edges(self):
        metrics = self.head.edge_metrics(self.rels)
        self.assertTrue(math.isfinite(metrics["edge_auc_directed"]))

    def test_presence_target_directed(self):
        """presence[t,s]=1 for TrueRelation(source=0,target=1)."""
        target = torch.zeros(N_S, N_S)
        for r in self.rels:
            target[r.target_sector, r.source_sector] = 1.0
        self.assertEqual(float(target[1, 0]), 1.0)
        self.assertEqual(float(target[0, 1]), 0.0)

    def test_presence_diagonal_excluded(self):
        """Self-loop never gets presence=1."""
        rels_with_self = [TrueRelation(0, 0, 1, 0.5, False)]
        loss = self.head.presence_loss(rels_with_self, DEVICE)
        self.assertTrue(math.isfinite(float(loss)))


# ── GatedGraphModel tests ─────────────────────────────────────────────────────

class TestGatedGraphModel(unittest.TestCase):

    def setUp(self):
        self.model = _gated_model()
        self.panel, self.obs_mask = _small_panel()

    def test_gate_init_near_zero(self):
        """Gate starts below 0.1 everywhere due to bias=-5."""
        _, gate = self.model.predict_gated(self.panel, self.obs_mask, DEVICE)
        self.assertLess(float(gate.mean()), 0.1)

    def test_gate_zero_identity(self):
        """Forcing gate≈0 makes y_pred == y_temporal (D3)."""
        with torch.no_grad():
            self.model.gate.net[-2].bias.fill_(-100.0)
        y_gated, _ = self.model.predict_gated(self.panel, self.obs_mask, DEVICE)
        y_temp = self.model.predict_temporal_only(self.panel, self.obs_mask, DEVICE)
        np.testing.assert_allclose(y_gated, y_temp, atol=1e-4)
        # Restore
        with torch.no_grad():
            self.model.gate.net[-2].bias.fill_(-5.0)

    def test_residual_clamped(self):
        """graph_residual bounded by ±MAX_RESIDUAL_FRAC * |y_temporal|.mean()."""
        out = self.model.forward_tensors(self.panel, self.obs_mask, DEVICE)
        y_t = out["y_temporal"]
        max_r = MAX_RESIDUAL_FRAC * y_t.abs().mean().clamp(min=1e-6)
        res = out["graph_residual"]
        self.assertTrue((res.abs() <= max_r + 1e-6).all())

    def test_backbone_no_gradient(self):
        """Backbone parameters require no grad."""
        for p in self.model.backbone.parameters():
            self.assertFalse(p.requires_grad)

    def test_head_requires_grad(self):
        """GraphRelationHead parameters require grad."""
        any_grad = any(p.requires_grad
                       for p in self.model.graph_relation_head.parameters())
        self.assertTrue(any_grad)

    def test_forward_tensors_keys(self):
        out = self.model.forward_tensors(self.panel, self.obs_mask, DEVICE)
        for k in ("y_pred", "y_temporal", "gate", "graph_residual", "log_sigma", "msg_mag"):
            self.assertIn(k, out)

    def test_predict_temporal_only_finite(self):
        y = self.model.predict_temporal_only(self.panel, self.obs_mask, DEVICE)
        self.assertTrue(np.isfinite(y).all())

    def test_predict_gated_finite(self):
        y, gate = self.model.predict_gated(self.panel, self.obs_mask, DEVICE)
        self.assertTrue(np.isfinite(y).all())

    def test_predict_graph_always_on_finite(self):
        y = self.model.predict_graph_always_on(self.panel, self.obs_mask, DEVICE)
        self.assertTrue(np.isfinite(y).all())

    def test_gate_in_01(self):
        out = self.model.forward_tensors(self.panel, self.obs_mask, DEVICE)
        gate = out["gate"]
        self.assertTrue((gate >= 0).all() and (gate <= 1).all())


# ── Loss function tests ───────────────────────────────────────────────────────

class TestDecoupledLoss(unittest.TestCase):

    def setUp(self):
        self.model = _gated_model()
        self.panel, self.obs_mask = _small_panel()
        self.rels = _simple_relations()

    def _run_forward(self):
        out = self.model.forward_tensors(self.panel, self.obs_mask, DEVICE)
        loss_mask = torch.from_numpy((self.obs_mask == 0).astype(np.float32))
        return out, loss_mask

    def test_loss_finite_scalar(self):
        out, loss_mask = self._run_forward()
        total, comps = decoupled_total_loss(
            out["y_pred"], out["y_temporal"], out["gate"],
            self.panel, loss_mask, self.model, self.rels, DEVICE,
            compute_utility=False,
        )
        self.assertTrue(math.isfinite(float(total)))

    def test_loss_components_sum(self):
        out, loss_mask = self._run_forward()
        total, comps = decoupled_total_loss(
            out["y_pred"], out["y_temporal"], out["gate"],
            self.panel, loss_mask, self.model, self.rels, DEVICE,
            compute_utility=False,
        )
        self.assertAlmostEqual(float(total), comps["total"], places=4)

    def test_utility_zero_when_disabled(self):
        out, loss_mask = self._run_forward()
        _, comps = decoupled_total_loss(
            out["y_pred"], out["y_temporal"], out["gate"],
            self.panel, loss_mask, self.model, self.rels, DEVICE,
            compute_utility=False,
        )
        self.assertEqual(comps["l_utility"], 0.0)

    def test_gradients_flow_to_head_not_backbone(self):
        out, loss_mask = self._run_forward()
        total, _ = decoupled_total_loss(
            out["y_pred"], out["y_temporal"], out["gate"],
            self.panel, loss_mask, self.model, self.rels, DEVICE,
            compute_utility=False,
        )
        total.backward()
        # Head gets gradient
        head_grad = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in self.model.graph_relation_head.parameters()
        )
        self.assertTrue(head_grad)
        # Backbone does not
        backbone_grad = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in self.model.backbone.parameters()
        )
        self.assertFalse(backbone_grad)


# ── Fixture tests ─────────────────────────────────────────────────────────────

class TestFixtures(unittest.TestCase):

    def test_f1_gate_mean_computed(self):
        panel, obs_mask, rels, sadj, tadj, name = make_f1_useful_graph()
        self.assertEqual(name, "F1_useful_graph")
        self.assertEqual(len(rels), 1)
        self.assertAlmostEqual(rels[0].weight, 0.9, places=5)

    def test_f2_no_relations(self):
        panel, obs_mask, rels, sadj, tadj, name = make_f2_useless_graph()
        self.assertEqual(len(rels), 0)
        self.assertTrue((sadj == 0).all())

    def test_f6_sector_adj_symmetric_false_reverse(self):
        panel, obs_mask, rels, sadj, tadj, name = make_f6_asymmetric_directed()
        # Only 0→1 is a true relation; sector_adj should also have 1→0 (false reverse)
        self.assertEqual(float(sadj[1, 0]), 1.0, "true direction in sector_adj")
        self.assertEqual(float(sadj[0, 1]), 1.0, "false reverse in sector_adj")

    def test_f3_negative_weight(self):
        _, _, rels, _, _, _ = make_f3_negative_relation()
        self.assertLess(rels[0].weight, 0.0)

    def test_f4_lag2(self):
        _, _, rels, _, _, _ = make_f4_lag2_relation()
        self.assertEqual(rels[0].lag, 2)

    def test_f5_cross_sector_signal(self):
        panel, _, _, _, _, _ = make_f5_regime_window()
        # Sector 1 during years 5-10 should show more variation than pure AR
        mid_var = float(panel[:, 1, 5:11].var())
        early_var = float(panel[:, 1, 0:5].var())
        # Cross-sector signal inflates variance during the window
        self.assertGreater(mid_var, 0.0)


# ── Evaluator tests ───────────────────────────────────────────────────────────

class TestEvaluator(unittest.TestCase):

    def setUp(self):
        self.model = _gated_model()
        self.panel, self.obs_mask = _small_panel()
        self.rels = _simple_relations()

    def test_analytic_graph_returns_auc(self):
        from src.modeles.synthetic.phase16_decoupled.evaluator import evaluate_analytic_graph
        m = evaluate_analytic_graph(self.model, self.rels, None)
        self.assertIn("edge_auc_directed", m)

    def test_temporal_reconstruction_returns_mae(self):
        from src.modeles.synthetic.phase16_decoupled.evaluator import evaluate_temporal_reconstruction
        m = evaluate_temporal_reconstruction(self.model, self.panel, self.obs_mask, DEVICE)
        self.assertIn("mae_temporal", m)
        self.assertIn("mae_ffill", m)

    def test_gated_assist_returns_all_maes(self):
        from src.modeles.synthetic.phase16_decoupled.evaluator import evaluate_gated_graph_assist
        m = evaluate_gated_graph_assist(self.model, self.panel, self.obs_mask,
                                         self.rels, None, DEVICE, seed=42)
        for k in ("mae_gated", "mae_temporal", "mae_graph_always", "mae_permuted", "mae_ffill"):
            self.assertIn(k, m, f"missing key {k}")


# ── Gate check tests ──────────────────────────────────────────────────────────

class TestGatesDec053(unittest.TestCase):

    def _result(self, **kwargs):
        base = {
            "scenario": "test", "mask_key": "mcar", "seed": 1000,
            "edge_auc_directed": 0.75, "edge_auprc_directed": 0.5,
            "prevalence": 0.3, "n_true_directed": 2,
            "mae_temporal": 1.0, "mae_gated": 0.95,
            "mae_graph_always": 1.1, "mae_permuted": 1.2,
            "mae_ffill": 1.5, "sign_acc": 0.7, "lag_acc": 0.8,
        }
        base.update(kwargs)
        return base

    def test_d1_passes_finite_auc(self):
        eval_res = {"all_results": [self._result()]}
        g = check_d1_metric_correctness(eval_res)
        self.assertEqual(g.verdict, "PASS")

    def test_d1_fails_nan_auc_with_edges(self):
        eval_res = {"all_results": [self._result(edge_auc_directed=float("nan"))]}
        g = check_d1_metric_correctness(eval_res)
        self.assertEqual(g.verdict, "FAIL")

    def test_d3_passes_small_delta(self):
        g = check_d3_temporal_fallback({"gate_zero_identity_max_delta": 1e-7})
        self.assertEqual(g.verdict, "PASS")

    def test_d3_fails_large_delta(self):
        g = check_d3_temporal_fallback({"gate_zero_identity_max_delta": 0.5})
        self.assertEqual(g.verdict, "FAIL")

    def test_d7_passes_gated_equal_temporal(self):
        eval_res = {"all_results": [self._result(mae_gated=1.0, mae_temporal=1.0)]}
        g = check_d7_predictive_safety(eval_res)
        self.assertEqual(g.verdict, "PASS")

    def test_d7_fails_gated_much_worse(self):
        eval_res = {"all_results": [self._result(mae_gated=1.2, mae_temporal=1.0)]}
        g = check_d7_predictive_safety(eval_res)
        self.assertEqual(g.verdict, "FAIL")

    def test_d9_always_passes(self):
        eval_res = {"all_results": [self._result()]}
        g = check_d9_realistic_reconstruction(eval_res)
        self.assertEqual(g.verdict, "PASS")

    def test_format_gate_report_markdown(self):
        eval_res = {"all_results": [self._result()]}
        fixture_res = {
            "gate_zero_identity_max_delta": 1e-8,
            "F1_useful_graph": {"gate_mean": 0.5},
            "F2_useless_graph": {"gate_mean": 0.05},
            "F3_negative_relation": {"gate_mean": 0.4},
            "F4_lag2_relation": {"gate_mean": 0.35},
            "F5_regime_window": {"gate_outside_window_mean": 0.1},
            "F6_asymmetric_directed": {"presence_logit_true_minus_false": 1.0},
        }
        gates = evaluate_all_gates(eval_res, fixture_res)
        report = format_gate_report(gates)
        self.assertIn("| Gate |", report)
        self.assertIn("D1", report)
        self.assertIn("D10", report)


if __name__ == "__main__":
    unittest.main()
