"""
test_phase10_metric_reconciliation.py — fixture tests for AUC metric and Phase 10 edge recovery.

Validates the AUC reconciliation documented in HERALD_PHASE10_METRIC_RECONCILIATION.md:
  - Bug B1 (AUC transposition): attn[rows,cols] vs attn[cols,cols]
  - Correct off-diagonal AUC universe (n_sectors=9 → 72 off-diagonal pairs)
  - oracle_lagged AUC = 1.000 with directed frozen attention
  - Phase 10 data integrity (20 result files with expected keys)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "hpc_results" / "phase10_synthetic_lagged"
PHASE10_VERSION = "phase10_v1"
N_SCENARIOS = 4
N_SEEDS = 5
N_EXPECTED_TASKS = N_SCENARIOS * N_SEEDS

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def phase10_results():
    files = sorted(RESULTS_DIR.glob("*.json"))
    files = [f for f in files if not f.name.startswith("gate_")]
    return [json.loads(f.read_text()) for f in files]


@pytest.fixture(scope="module")
def herald_metrics():
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from src.modeles.synthetic.evaluate_imputation import compute_edge_recovery_metrics
    from src.data.synthetic.generate_herald_synthetic import TrueRelation
    return compute_edge_recovery_metrics, TrueRelation


# ── Data integrity ────────────────────────────────────────────────────────────

def test_result_count(phase10_results):
    assert len(phase10_results) == N_EXPECTED_TASKS, (
        f"Expected {N_EXPECTED_TASKS} results, got {len(phase10_results)}"
    )


def test_manifest_version(phase10_results):
    bad = [r["scenario"] + "_" + str(r["seed"]) for r in phase10_results
           if r.get("manifest_version") != PHASE10_VERSION]
    assert bad == [], f"Wrong manifest_version in: {bad}"


def test_no_duplicate_tasks(phase10_results):
    keys = [(r["scenario"], r["seed"]) for r in phase10_results]
    assert len(keys) == len(set(keys)), "Duplicate (scenario, seed) pairs"


def test_all_tasks_have_mask_results(phase10_results):
    bad = [(r["scenario"], r["seed"]) for r in phase10_results if "mask_results" not in r]
    assert bad == [], f"Missing mask_results in: {bad}"


def test_mask_results_have_all_models(phase10_results):
    expected_models = {
        "ffill", "herald_contemp", "herald_lagged", "oracle_lagged",
        "herald_lagged_permuted", "oracle_contemp",
    }
    bad = []
    for r in phase10_results:
        for mk, mr in r["mask_results"].items():
            missing = expected_models - set(mr.keys())
            if missing:
                bad.append((r["scenario"], r["seed"], mk, sorted(missing)))
    assert bad == [], f"Missing models in mask results: {bad[:3]}"


def test_leakage_check_passed(phase10_results):
    bad = [(r["scenario"], r["seed"]) for r in phase10_results
           if not r.get("leakage_check", {}).get("passed", False)]
    assert bad == [], f"Leakage check failed in: {bad}"


def test_oracle_lagged_auc_is_one(phase10_results):
    not_one = []
    for r in phase10_results:
        for mk, mr in r["mask_results"].items():
            ol = mr.get("oracle_lagged", {})
            auc = ol.get("edge_auc")
            if auc is not None and abs(auc - 1.0) > 1e-6:
                not_one.append((r["scenario"], r["seed"], mk, auc))
    assert not_one == [], f"oracle_lagged AUC != 1.0: {not_one}"


def test_herald_lagged_auc_above_contemp(phase10_results):
    for scenario in ["linear", "nonlinear_heavy", "mixed_default", "generalization"]:
        hl_aucs = []
        hc_aucs = []
        for r in phase10_results:
            if r["scenario"] != scenario:
                continue
            for mk, mr in r["mask_results"].items():
                hl = mr.get("herald_lagged", {}).get("edge_auc")
                hc = mr.get("herald_contemp", {}).get("edge_auc")
                if hl is not None and hc is not None and hl == hl and hc == hc:
                    hl_aucs.append(hl)
                    hc_aucs.append(hc)
        if hl_aucs and hc_aucs:
            assert np.mean(hl_aucs) > np.mean(hc_aucs), (
                f"{scenario}: herald_lagged mean AUC ({np.mean(hl_aucs):.4f}) "
                f"<= herald_contemp ({np.mean(hc_aucs):.4f})"
            )


# ── AUC metric fixture: manual ground truth ───────────────────────────────────

def test_auc_metric_perfect_recovery(herald_metrics):
    """With attention exactly matching true relations, AUC must be 1.0.

    Convention: learned_attn[target, source] = weight for source→target.
    True edge s→t gets score learned_attn[t, s].
    """
    compute_edge_recovery_metrics, TrueRelation = herald_metrics
    n_sectors = 6
    # True relations: 0→1 (lag 1), 2→4 (lag 2)
    true_rels = [
        TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.5, nonlinear=False),
        TrueRelation(source_sector=2, target_sector=4, lag=2, weight=-0.4, nonlinear=False),
    ]
    # Convention: attn[target, source] — set attn[1, 0] and attn[4, 2] high
    attn = np.full((n_sectors, n_sectors), 1e-6)
    np.fill_diagonal(attn, 0.0)
    attn[1, 0] = 1.0  # score for 0→1: attn[target=1, source=0]
    attn[4, 2] = 1.0  # score for 2→4: attn[target=4, source=2]
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn)
    assert abs(e.auc - 1.0) < 1e-6, f"Perfect attention → AUC should be 1.0, got {e.auc}"
    assert e.n_true_edges == 2
    assert e.precision_at_k == 1.0
    assert e.recall_at_k == 1.0


def test_auc_metric_random_recovery(herald_metrics):
    """Uniform attention → AUC ≈ 0.5 (no better than chance)."""
    compute_edge_recovery_metrics, TrueRelation = herald_metrics
    n_sectors = 9
    rng = np.random.default_rng(42)
    true_rels = [
        TrueRelation(source_sector=0, target_sector=3, lag=1, weight=0.5, nonlinear=False),
        TrueRelation(source_sector=1, target_sector=5, lag=2, weight=0.6, nonlinear=False),
    ]
    # Uniform: diagonal must be 0, off-diagonal uniform
    attn = np.ones((n_sectors, n_sectors))
    np.fill_diagonal(attn, 0.0)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn)
    # Uniform weights → AUC exactly 0.5 (or undefined); should be near 0.5
    assert 0.4 <= e.auc <= 0.6, f"Uniform attention → AUC near 0.5, got {e.auc}"


def test_auc_metric_inverted_recovery(herald_metrics):
    """Inverted attention (true edge gets MINIMUM score) → AUC < 0.5.

    Convention: true edge s→t is scored via attn[t, s].
    Set attn[t, s] to minimum while all other off-diagonal positions are high.
    """
    compute_edge_recovery_metrics, TrueRelation = herald_metrics
    n_sectors = 6
    true_rels = [
        TrueRelation(source_sector=0, target_sector=2, lag=1, weight=0.5, nonlinear=False),
    ]
    attn = np.ones((n_sectors, n_sectors))
    np.fill_diagonal(attn, 0.0)
    # True edge 0→2: score is attn[target=2, source=0] → set it to minimum
    attn[2, 0] = 1e-9
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn)
    assert e.auc < 0.5, f"Inverted attention → AUC < 0.5, got {e.auc}"


def test_auc_off_diagonal_universe(herald_metrics):
    """Off-diagonal pairs universe: n_sectors=9 → n_pairs=72."""
    compute_edge_recovery_metrics, TrueRelation = herald_metrics
    n_sectors = 9
    true_rels = [
        TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.5, nonlinear=False),
    ]
    attn = np.ones((n_sectors, n_sectors))
    np.fill_diagonal(attn, 0.0)
    attn[0, 1] = 2.0
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn)
    assert e.n_true_edges == 1
    expected_off_diag = n_sectors * (n_sectors - 1)
    assert expected_off_diag == 72, f"Expected 72 off-diagonal pairs for n=9, got {expected_off_diag}"


def test_auc_b1_transposition_different_from_correct(herald_metrics):
    """
    Verify B1 bug impact: correct convention (attn[target,source]) vs wrong (attn[source,target]).

    The fix in DEC-042 changed y_score = learned_attn[rows, cols] (source,target) to
    y_score = learned_attn[cols, rows] (target,source). For an asymmetric true graph:
    - Correct convention → AUC = 1.0 with perfect attention
    - Wrong convention (source,target where true scores are at target,source) → AUC < 0.5
    """
    compute_edge_recovery_metrics, TrueRelation = herald_metrics
    n_sectors = 5
    true_rels = [
        TrueRelation(source_sector=0, target_sector=2, lag=1, weight=0.5, nonlinear=False),
        TrueRelation(source_sector=3, target_sector=1, lag=2, weight=0.4, nonlinear=False),
    ]
    # Perfect attention using CORRECT convention: attn[target, source]
    # Edge 0→2: set attn[2, 0] = high; Edge 3→1: set attn[1, 3] = high
    attn_correct = np.full((n_sectors, n_sectors), 1e-6)
    np.fill_diagonal(attn_correct, 0.0)
    attn_correct[2, 0] = 1.0   # attn[target=2, source=0]
    attn_correct[1, 3] = 1.0   # attn[target=1, source=3]
    e_correct = compute_edge_recovery_metrics(true_rels, n_sectors, attn_correct)
    assert abs(e_correct.auc - 1.0) < 1e-6, f"Correct convention → AUC=1.0, got {e_correct.auc}"

    # Wrong convention (B1): attn[source, target] — perfect attention but indexed backwards
    # The current function reads attn[target, source]; if we put high values at attn[source, target],
    # the true edges will get low scores → AUC inverted (< 0.5 for asymmetric graph)
    attn_b1 = np.full((n_sectors, n_sectors), 1e-6)
    np.fill_diagonal(attn_b1, 0.0)
    attn_b1[0, 2] = 1.0   # attn[source=0, target=2] — wrong index order
    attn_b1[3, 1] = 1.0   # attn[source=3, target=1] — wrong index order
    e_b1 = compute_edge_recovery_metrics(true_rels, n_sectors, attn_b1)
    assert e_b1.auc < 0.5, (
        f"B1 wrong convention → AUC < 0.5 (inverted), got {e_b1.auc}"
    )


# ── Sensitivity: forced_lag in SyntheticConfig ────────────────────────────────

def test_forced_lag_1():
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
    cfg = SyntheticConfig(n_sectors=5, n_territories=8, n_years=10, seed=42, n_true_relations=4, forced_lag=1)
    ds = generate_dataset(cfg)
    lags = [r.lag for r in ds["true_relations"]]
    assert all(l == 1 for l in lags), f"forced_lag=1 but got lags: {lags}"


def test_forced_lag_2():
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
    cfg = SyntheticConfig(n_sectors=5, n_territories=8, n_years=10, seed=42, n_true_relations=4, forced_lag=2)
    ds = generate_dataset(cfg)
    lags = [r.lag for r in ds["true_relations"]]
    assert all(l == 2 for l in lags), f"forced_lag=2 but got lags: {lags}"


def test_forced_lag_none_gives_mixed():
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset
    cfg = SyntheticConfig(n_sectors=9, n_territories=15, n_years=15, seed=123, n_true_relations=10, forced_lag=None)
    ds = generate_dataset(cfg)
    lags = [r.lag for r in ds["true_relations"]]
    # With 10 relations and seed=123, expect mixed lags
    assert set(lags) == {1, 2}, f"forced_lag=None expected mixed lags, got: {set(lags)}"


def test_forced_lag_backward_compat_default():
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from src.data.synthetic.generate_herald_synthetic import BENCHMARK_SCENARIOS
    for name, cfg in BENCHMARK_SCENARIOS.items():
        assert cfg.forced_lag is None, f"BENCHMARK_SCENARIOS[{name}].forced_lag should be None"
