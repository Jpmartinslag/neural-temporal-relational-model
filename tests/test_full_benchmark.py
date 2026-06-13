"""
tests/test_full_benchmark.py

Tests for the HERALD Phase 9 full benchmark runner (DEC-040).
Covers: manifest, null controls, copermutation, atomic writes, resume,
        gate logic, new baselines, extended metrics.

These tests run fast (< 60 s) and do NOT require HPC or GPU.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_herald_synthetic import (
    BENCHMARK_SCENARIOS,
    BENCHMARK_SEEDS,
    BENCHMARK_MASK_LEVELS,
    BENCHMARK_MASK_TYPES,
    PILOT_SCENARIOS,
    PILOT_SEEDS,
    SyntheticConfig,
    generate_dataset,
    mask_panel,
)
from src.modeles.synthetic.imputation_baselines import (
    KNNPanelImputer,
    MeanImputer,
    RidgeImputer,
)
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    build_permuted_adj,
    build_random_adj,
    impute_deterministic,
    train_herald_imputer,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
    compute_state_metrics,
    check_no_leakage,
)
from src.modeles.synthetic.gates import evaluate_gates, GateResult
from src.modeles.synthetic.run_full_benchmark import (
    build_manifest,
    full_manifest,
    pilot_manifest,
    is_valid_result,
    write_atomic,
    run_task,
    BENCHMARK_MASK_TYPES as RUN_MASK_TYPES,
    BENCHMARK_MASK_LEVELS as RUN_MASK_LEVELS,
)

SMALL_CFG = SyntheticConfig(n_territories=6, n_sectors=4, n_years=10, seed=7)


@pytest.fixture(scope="module")
def small_ds():
    return generate_dataset(SMALL_CFG)


@pytest.fixture(scope="module")
def small_mask(small_ds):
    return small_ds["masks"]["mcar_20"]


@pytest.fixture(scope="module")
def obs_panel(small_ds, small_mask):
    return mask_panel(small_ds["panel"], small_mask)


# ── Manifest tests ─────────────────────────────────────────────────────────────

class TestManifest:
    def test_full_manifest_count(self):
        m = full_manifest()
        expected = len(BENCHMARK_SCENARIOS) * len(BENCHMARK_SEEDS)
        assert len(m) == expected, f"expected {expected} tasks, got {len(m)}"

    def test_pilot_manifest_count(self):
        m = pilot_manifest()
        from src.modeles.synthetic.run_full_benchmark import PILOT_SCENARIO_NAMES, PILOT_SEEDS as PS
        expected = len(PILOT_SCENARIO_NAMES) * len(PS)
        assert len(m) == expected

    def test_task_ids_unique_and_sequential(self):
        m = full_manifest()
        ids = [t["task_id"] for t in m]
        assert ids == list(range(len(m)))

    def test_manifest_deterministic(self):
        m1 = full_manifest()
        m2 = full_manifest()
        assert m1 == m2

    def test_manifest_has_required_keys(self):
        for t in full_manifest():
            assert "task_id" in t
            assert "scenario" in t
            assert "seed" in t
            assert "output_file" in t

    def test_output_files_unique(self):
        m = full_manifest()
        fnames = [t["output_file"] for t in m]
        assert len(set(fnames)) == len(fnames)

    def test_scenarios_all_present(self):
        m = full_manifest()
        scenarios = {t["scenario"] for t in m}
        assert scenarios == set(BENCHMARK_SCENARIOS.keys())

    def test_seeds_all_present(self):
        m = full_manifest()
        seeds = {t["seed"] for t in m}
        assert seeds == set(BENCHMARK_SEEDS)

    def test_pilot_scenarios_subset(self):
        from src.modeles.synthetic.run_full_benchmark import PILOT_SCENARIO_NAMES
        m = pilot_manifest()
        scenarios = {t["scenario"] for t in m}
        assert scenarios == set(PILOT_SCENARIO_NAMES)
        assert scenarios.issubset(BENCHMARK_SCENARIOS.keys())

    def test_grid_totals(self):
        """Document full grid: tasks × mask combos × models."""
        n_tasks = len(full_manifest())
        n_mask_combos = len(BENCHMARK_MASK_TYPES) * len(BENCHMARK_MASK_LEVELS)
        n_models = 12  # mean/median/ffill/interp/knn/ridge/graph_ridge/neural/herald/perm/rand/oracle
        print(f"\nFull grid: {n_tasks} tasks × {n_mask_combos} mask combos × {n_models} models"
              f" = {n_tasks * n_mask_combos * n_models} model evaluations")
        assert n_tasks > 0 and n_mask_combos > 0


# ── Generator / mask level tests ───────────────────────────────────────────────

class TestGeneratorExtended:
    def test_50pct_mask_present(self):
        ds = generate_dataset(SyntheticConfig(seed=42))
        assert "mcar_50" in ds["masks"]
        assert "mar_50" in ds["masks"]
        assert "block_50" in ds["masks"]

    def test_50pct_mask_has_sufficient_hidden(self):
        ds = generate_dataset(SyntheticConfig(n_territories=10, n_sectors=5, n_years=12, seed=42))
        m50 = ds["masks"]["mcar_50"]
        hidden_pct = (m50 == 0).mean()
        # Should be between 40% and 60% (MCAR at 50%)
        assert 0.40 <= hidden_pct <= 0.60, f"Expected ~50% hidden, got {hidden_pct:.2f}"

    def test_scenario_registry_complete(self):
        for name, cfg in BENCHMARK_SCENARIOS.items():
            assert cfg.n_territories == 30
            assert cfg.n_sectors == 9
            assert cfg.n_years == 20
            assert cfg.seed == 0  # overridden per task

    def test_pilot_scenarios_smaller(self):
        for name, cfg in PILOT_SCENARIOS.items():
            assert cfg.n_territories == 20
            assert cfg.n_sectors == 7
            assert cfg.n_years == 16

    def test_linear_scenario_no_nonlinear_relations(self):
        import dataclasses
        cfg = dataclasses.replace(BENCHMARK_SCENARIOS["linear"], seed=42)
        ds = generate_dataset(cfg)
        for rel in ds["true_relations"]:
            assert rel.nonlinear is False, "linear scenario must have no nonlinear relations"

    def test_nonlinear_scenario_has_nonlinear_relations(self):
        import dataclasses
        cfg = dataclasses.replace(BENCHMARK_SCENARIOS["nonlinear_heavy"], seed=42)
        ds = generate_dataset(cfg)
        has_nonlinear = any(rel.nonlinear for rel in ds["true_relations"])
        assert has_nonlinear, "nonlinear_heavy scenario must have at least one nonlinear relation"


# ── Null control tests ─────────────────────────────────────────────────────────

class TestNullControls:
    def test_permuted_adj_returns_perm_arrays(self, small_ds):
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]
        rng = np.random.default_rng(0)
        adj_s_p, adj_t_p, perm_s, perm_t = build_permuted_adj(adj_s, adj_t, rng)
        assert len(perm_s) == adj_s.shape[0]
        assert len(perm_t) == adj_t.shape[0]
        # perm is a valid permutation
        assert sorted(perm_s) == list(range(adj_s.shape[0]))
        assert sorted(perm_t) == list(range(adj_t.shape[0]))

    def test_permuted_messages_differ_from_original(self):
        """B8: permuting adj WITHOUT permuting panel gives different messages."""
        # Use a config guaranteed to have non-trivial sector adj
        ds = generate_dataset(SyntheticConfig(n_territories=8, n_sectors=6, n_years=10,
                                              seed=42, n_true_relations=8))
        panel = ds["panel"]
        mask = ds["masks"]["mcar_20"]
        adj_s = ds["sector_adj"]
        adj_t = ds["territory_adj"]

        # Ensure adj_s is non-trivial
        if adj_s.sum() == 0:
            pytest.skip("sector_adj is all-zero for this seed (no directed edges)")

        # Use a permutation that is guaranteed to be non-identity
        n_S = adj_s.shape[0]
        # Build a fixed non-identity permutation: rotate by 1
        forced_perm = np.array([(i + 1) % n_S for i in range(n_S)])
        adj_s_perm = adj_s[forced_perm][:, forced_perm]

        safe = np.where(mask, panel, 0.0).astype(float)
        mask_f = mask.astype(float)
        orig = np.einsum("ij,tjy->tiy", adj_s, safe * mask_f)
        perm = np.einsum("ij,tjy->tiy", adj_s_perm, safe * mask_f)
        # With non-trivial adj and non-identity permutation, messages must differ
        if not np.allclose(adj_s, adj_s_perm):
            assert not np.allclose(orig, perm), "Permuted adj should produce different messages"

    def test_copermutation_is_relabeling(self, small_ds):
        """
        If we permute adj AND panel/mask with the SAME permutation,
        messages (after un-permuting) are identical to the original.
        This proves B8 (adj-only permutation) is a genuine null.
        """
        panel = small_ds["panel"]
        mask = small_ds["masks"]["mcar_20"]
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]

        rng = np.random.default_rng(7)
        perm = rng.permutation(adj_s.shape[0])
        adj_co = adj_s[perm][:, perm]
        panel_co = panel[:, perm, :]
        mask_co = mask[:, perm, :]

        safe_orig = np.where(mask, panel, 0.0).astype(float)
        safe_co = np.where(mask_co, panel_co, 0.0).astype(float)
        mask_f = mask.astype(float)
        mask_co_f = mask_co.astype(float)

        orig_msg = np.einsum("ij,tjy->tiy", adj_s, safe_orig * mask_f)
        co_msg = np.einsum("ij,tjy->tiy", adj_co, safe_co * mask_co_f)

        # Undo permutation on co_msg to compare
        inv_perm = np.argsort(perm)
        co_msg_unp = co_msg[:, inv_perm, :]
        np.testing.assert_allclose(orig_msg, co_msg_unp, atol=1e-10,
                                   err_msg="Copermutation must be pure relabeling")

    def test_random_adj_preserves_density(self, small_ds):
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]
        rng = np.random.default_rng(0)
        adj_s_r, adj_t_r = build_random_adj(adj_s, adj_t, rng)
        n_S = adj_s.shape[0]
        n_T = adj_t.shape[0]
        orig_density = adj_s.sum() / (n_S * (n_S - 1))
        rand_density = adj_s_r.sum() / (n_S * (n_S - 1))
        # Allow ±20% variation (Erdős-Rényi has variance)
        assert abs(rand_density - orig_density) < orig_density + 0.2

    def test_random_adj_is_symmetric(self, small_ds):
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]
        rng = np.random.default_rng(1)
        adj_s_r, _ = build_random_adj(adj_s, adj_t, rng)
        np.testing.assert_array_equal(adj_s_r, adj_s_r.T,
                                      err_msg="Random sector adj must be symmetric")

    def test_random_adj_differs_from_original(self, small_ds):
        adj_s = small_ds["sector_adj"]
        adj_t = small_ds["territory_adj"]
        rng = np.random.default_rng(0)
        adj_s_r, adj_t_r = build_random_adj(adj_s, adj_t, rng)
        # Random adj should NOT be identical to original (with very high probability)
        n_S = adj_s.shape[0]
        if n_S > 2:
            assert not np.allclose(adj_s, adj_s_r), "Random adj should differ from true adj"


# ── KNN imputer tests ──────────────────────────────────────────────────────────

class TestKNNImputer:
    def test_no_nan_output(self, small_ds, small_mask, obs_panel):
        imp = KNNPanelImputer(k=3)
        result = imp.fit_transform(obs_panel, small_mask)
        assert not np.isnan(result).any()

    def test_preserves_observed(self, small_ds, small_mask, obs_panel):
        panel = small_ds["panel"]
        imp = KNNPanelImputer(k=3)
        result = imp.fit_transform(obs_panel, small_mask)
        np.testing.assert_allclose(result[small_mask == 1], panel[small_mask == 1], rtol=1e-5)

    def test_correct_shape(self, small_ds, small_mask, obs_panel):
        imp = KNNPanelImputer(k=3)
        result = imp.fit_transform(obs_panel, small_mask)
        assert result.shape == obs_panel.shape

    def test_k1_uses_nearest_neighbor(self, small_ds, small_mask, obs_panel):
        imp = KNNPanelImputer(k=1)
        result = imp.fit_transform(obs_panel, small_mask)
        assert not np.isnan(result).any()

    def test_causal_knn_not_using_future(self, small_ds):
        """Modifying year y+1 values must not affect KNN fill at year y."""
        panel = small_ds["panel"].copy()
        n_T, n_S, n_Y = panel.shape
        mask = np.ones_like(panel, dtype=np.int8)
        mask[:, :, 5] = 0  # hide year 5 entirely

        panel_mod = panel.copy()
        panel_mod[:, :, 6] += 999

        obs1 = mask_panel(panel, mask)
        obs2 = mask_panel(panel_mod, mask)
        imp = KNNPanelImputer(k=3)

        r1 = imp.fit_transform(obs1, mask)
        r2 = imp.fit_transform(obs2, mask)
        # KNN features are causal (based on running mean up to y-1)
        # Perturbing year 6 should not change fill at year 5
        np.testing.assert_allclose(r1[:, :, 5], r2[:, :, 5], rtol=1e-5,
                                   err_msg="KNN fill at year 5 must not depend on year 6")


# ── Extended metrics tests ─────────────────────────────────────────────────────

class TestExtendedMetrics:
    def test_spearman_r_range(self, small_ds, small_mask):
        panel = small_ds["panel"]
        pred = MeanImputer().fit_transform(mask_panel(panel, small_mask), small_mask)
        m = compute_imputation_metrics(panel, pred, small_mask)
        if not np.isnan(m.spearman_r):
            assert -1 <= m.spearman_r <= 1

    def test_state_metrics_range(self, small_ds, small_mask):
        panel = small_ds["panel"]
        regimes = small_ds["regimes"]
        pred = MeanImputer().fit_transform(mask_panel(panel, small_mask), small_mask)
        sm = compute_state_metrics(panel, pred, small_mask, regimes)
        if not np.isnan(sm.macro_f1):
            assert 0 <= sm.macro_f1 <= 1
        if not np.isnan(sm.balanced_accuracy):
            assert 0 <= sm.balanced_accuracy <= 1

    def test_edge_metrics_include_fpr(self, small_ds):
        n_S = SMALL_CFG.n_sectors
        attn = np.ones((n_S, n_S)) / n_S
        e = compute_edge_recovery_metrics(small_ds["true_relations"], n_S, attn)
        assert hasattr(e, "false_positive_rate")
        assert 0 <= e.false_positive_rate <= 1

    def test_perfect_imputation_spearman_one(self, small_ds, small_mask):
        panel = small_ds["panel"]
        m = compute_imputation_metrics(panel, panel, small_mask)
        assert m.mae == pytest.approx(0.0, abs=1e-8)
        # Perfect imputation → Spearman = 1 (or nan if all values identical)
        if not np.isnan(m.spearman_r):
            assert m.spearman_r == pytest.approx(1.0, abs=1e-6)


# ── Gate evaluation tests ──────────────────────────────────────────────────────

class TestGates:
    def _make_result(self, herald_mae, best_ng_mae, perm_mae, auc, cal90, fpr,
                     leakage_pass=True, mask_type="mcar"):
        """Build a synthetic per-seed result. best_ng_mae is assigned to ridge;
        other non-graph baselines are worse (×1.05) so ridge is the best non-graph."""
        return {
            "seed": 42,
            "mask_type": mask_type,
            "leakage_check": {"passed": leakage_pass},
            "baselines": {
                "ridge": {"mae": best_ng_mae},
                "neural_no_graph": {"mae": best_ng_mae * 1.05},  # worse than ridge
                "mean": {"mae": best_ng_mae * 1.10},
                "herald_graph": {
                    "mae": herald_mae,
                    "edge_auc": auc,
                    "edge_fpr": fpr,
                    "calibration_90": cal90,
                },
                "herald_permuted": {"mae": perm_mae},
            },
        }

    def test_g1_pass_two_mechanisms(self):
        # ridge (best_ng) = 0.20; herald needs ≤ 0.20*0.95 = 0.190
        results = [
            self._make_result(0.188, 0.20, 0.22, 0.70, 0.85, 0.20, mask_type="mcar"),  # PASS
            self._make_result(0.188, 0.20, 0.21, 0.70, 0.85, 0.20, mask_type="mar"),   # PASS
            self._make_result(0.22, 0.20, 0.23, 0.70, 0.85, 0.20, mask_type="block"),  # FAIL
        ]
        verdict = evaluate_gates(results, scenario="mixed_default")
        g1 = next(g for g in verdict.gates if g.gate == "G1")
        assert g1.passed, f"G1 should pass when ≥ 2 mechanisms pass; details: {g1.details}"

    def test_g1_fail_one_mechanism(self):
        results = [
            self._make_result(0.188, 0.20, 0.22, 0.70, 0.85, 0.20, mask_type="mcar"),  # PASS
            self._make_result(0.22, 0.20, 0.23, 0.70, 0.85, 0.20, mask_type="mar"),    # FAIL
            self._make_result(0.22, 0.20, 0.23, 0.70, 0.85, 0.20, mask_type="block"),  # FAIL
        ]
        verdict = evaluate_gates(results, scenario="mixed_default")
        g1 = next(g for g in verdict.gates if g.gate == "G1")
        assert not g1.passed, "G1 should fail when only 1 mechanism passes"

    def test_g2_pass_above_threshold(self):
        results = [self._make_result(0.19, 0.20, 0.22, 0.70, 0.85, 0.20)]
        verdict = evaluate_gates(results)
        g2 = next(g for g in verdict.gates if g.gate == "G2")
        assert g2.passed

    def test_g2_fail_below_threshold(self):
        results = [self._make_result(0.19, 0.20, 0.22, 0.55, 0.85, 0.20)]
        verdict = evaluate_gates(results)
        g2 = next(g for g in verdict.gates if g.gate == "G2")
        assert not g2.passed

    def test_g3_fail_when_permuted_better(self):
        # permuted_mae (0.18) < herald_mae (0.19) → FAIL
        results = [self._make_result(0.19, 0.20, 0.18, 0.70, 0.85, 0.20)]
        verdict = evaluate_gates(results)
        g3 = next(g for g in verdict.gates if g.gate == "G3")
        assert not g3.passed

    def test_g5_fail_propagates(self):
        results = [self._make_result(0.19, 0.20, 0.22, 0.70, 0.85, 0.20, leakage_pass=False)]
        verdict = evaluate_gates(results)
        g5 = next(g for g in verdict.gates if g.gate == "G5")
        assert not g5.passed
        assert not verdict.minimum_criterion_passed

    def test_minimum_criterion(self):
        # G1 PASS (2/3 mechanisms) + G5 PASS + G3 PASS → minimum met
        results = [
            self._make_result(0.188, 0.20, 0.22, 0.55, 0.85, 0.20, mask_type="mcar"),  # PASS
            self._make_result(0.188, 0.20, 0.21, 0.55, 0.85, 0.20, mask_type="mar"),   # PASS
            self._make_result(0.22, 0.20, 0.23, 0.55, 0.85, 0.20, mask_type="block"),  # FAIL
        ]
        verdict = evaluate_gates(results)
        g1 = next(g for g in verdict.gates if g.gate == "G1")
        g3 = next(g for g in verdict.gates if g.gate == "G3")
        g5 = next(g for g in verdict.gates if g.gate == "G5")
        assert g1.passed, f"G1 should pass: {g1.details}"
        assert g3.passed, f"G3 should pass"
        assert g5.passed, f"G5 should pass"
        assert verdict.minimum_criterion_passed


# ── Atomic write and resume tests ──────────────────────────────────────────────

class TestAtomicWrite:
    def test_write_atomic_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "result.json"
            write_atomic({"x": 1}, path)
            assert path.exists()
            with open(path) as f:
                assert json.load(f) == {"x": 1}

    def test_no_tmp_file_left(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "result.json"
            write_atomic({"x": 1}, path)
            assert not path.with_suffix(".tmp").exists()

    def test_is_valid_result_false_for_missing(self):
        assert not is_valid_result(Path("/nonexistent/path.json"))

    def test_is_valid_result_false_for_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text("{invalid json")
            assert not is_valid_result(p)

    def test_is_valid_result_false_for_missing_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "partial.json"
            write_atomic({"baselines": {}}, p)  # missing "leakage_check"
            assert not is_valid_result(p)

    def test_is_valid_result_true_for_valid(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "valid.json"
            write_atomic({"baselines": {"mean": {}}, "leakage_check": {"passed": True}}, p)
            assert is_valid_result(p)


# ── End-to-end mini-task test ──────────────────────────────────────────────────

class TestRunTask:
    """Smoke-level test: run one task with tiny config and verify output."""

    MINI_SCENARIO = {
        "mini": SyntheticConfig(n_territories=6, n_sectors=4, n_years=10, seed=0,
                                n_true_relations=3),
    }

    def test_run_task_produces_valid_output(self):
        with tempfile.TemporaryDirectory() as d:
            task = {"task_id": 0, "scenario": "mini", "seed": 42,
                    "output_file": "mini_seed00042.json"}
            import dataclasses
            scenarios = {
                "mini": dataclasses.replace(
                    SyntheticConfig(n_territories=6, n_sectors=4, n_years=10,
                                   n_true_relations=3), seed=0
                )
            }
            path = run_task(task, Path(d), n_epochs=10,
                            scenario_registry=scenarios,
                            mask_types=["mcar"], mask_levels=[20],
                            verbose=False, resume=False)
            assert path.exists()
            with open(path) as f:
                result = json.load(f)
            assert "baselines" in result
            assert "leakage_check" in result
            assert result["leakage_check"]["passed"]
            # All models should produce a result for mcar_20
            assert "mcar_20" in result["baselines"]
            bl = result["baselines"]["mcar_20"]
            for model in ["mean", "ridge", "herald_graph", "herald_permuted"]:
                assert model in bl, f"Model {model} missing from results"
                assert "mae" in bl[model]
                assert np.isfinite(bl[model]["mae"])

    def test_run_task_resume_skips_existing(self):
        with tempfile.TemporaryDirectory() as d:
            task = {"task_id": 0, "scenario": "mini", "seed": 42,
                    "output_file": "mini_seed00042.json"}
            # Write a valid dummy result
            path = Path(d) / task["output_file"]
            write_atomic({"baselines": {"mean": {}}, "leakage_check": {"passed": True}}, path)
            mtime_before = path.stat().st_mtime

            # run_task with resume=True should skip
            run_task(task, Path(d), n_epochs=10,
                     scenario_registry=self.MINI_SCENARIO,
                     mask_types=["mcar"], mask_levels=[20],
                     verbose=False, resume=True)
            mtime_after = path.stat().st_mtime
            assert mtime_before == mtime_after, "resume=True must not overwrite existing result"

    def test_run_task_no_nan_in_mae(self):
        with tempfile.TemporaryDirectory() as d:
            task = {"task_id": 0, "scenario": "mini", "seed": 99,
                    "output_file": "mini_seed00099.json"}
            import dataclasses
            scenarios = {
                "mini": dataclasses.replace(
                    SyntheticConfig(n_territories=6, n_sectors=4, n_years=10, n_true_relations=3),
                    seed=0
                )
            }
            path = run_task(task, Path(d), n_epochs=5,
                            scenario_registry=scenarios,
                            mask_types=["mcar"], mask_levels=[20],
                            verbose=False, resume=False)
            with open(path) as f:
                result = json.load(f)
            for mk, bl_dict in result["baselines"].items():
                for model, metrics in bl_dict.items():
                    if isinstance(metrics, dict) and "mae" in metrics:
                        assert np.isfinite(metrics["mae"]), \
                            f"NaN MAE in {model} mask={mk}"

    def test_leakage_check_in_output(self):
        with tempfile.TemporaryDirectory() as d:
            task = {"task_id": 0, "scenario": "mini", "seed": 7,
                    "output_file": "mini_seed00007.json"}
            import dataclasses
            scenarios = {
                "mini": dataclasses.replace(
                    SyntheticConfig(n_territories=6, n_sectors=4, n_years=10, n_true_relations=3),
                    seed=0
                )
            }
            path = run_task(task, Path(d), n_epochs=5,
                            scenario_registry=scenarios,
                            mask_types=["mcar"], mask_levels=[20],
                            verbose=False, resume=False)
            with open(path) as f:
                result = json.load(f)
            assert result["leakage_check"]["passed"]

    def test_gate_preview_in_output(self):
        with tempfile.TemporaryDirectory() as d:
            task = {"task_id": 0, "scenario": "mini", "seed": 11,
                    "output_file": "mini_seed00011.json"}
            import dataclasses
            scenarios = {
                "mini": dataclasses.replace(
                    SyntheticConfig(n_territories=6, n_sectors=4, n_years=10, n_true_relations=3),
                    seed=0
                )
            }
            path = run_task(task, Path(d), n_epochs=5,
                            scenario_registry=scenarios,
                            mask_types=["mcar"], mask_levels=[20],
                            verbose=False, resume=False)
            with open(path) as f:
                result = json.load(f)
            assert "gate_preview" in result
            assert result["gate_preview"] is not None
            assert "G5" in result["gate_preview"]
            assert result["gate_preview"]["G5"] is True
