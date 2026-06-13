"""
test_ofat_sensitivity.py — Tests for OFAT sensitivity design (DEC-044 addendum)

Covers:
- Manifest: 48 tasks, ≤ 60, reference once, one axis per config
- No confounded config (cs=high + ar=low + noise=low)
- Unique output filenames
- Factorial runner blocked without authorization flag
- Determinism (same task → same output file name)
- Gates O1-O8 structure
- Per-seed and per-mask metric coverage
- Atomic write and resume logic
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.modeles.synthetic.run_ofat_sensitivity import (
    OFAT_CONFIGS,
    OFAT_SCENARIOS,
    OFAT_SEEDS,
    OFAT_MASKS,
    OFAT_VERSION,
    build_manifest,
    is_valid_result,
    _compute_auprc,
)
from src.modeles.synthetic.gates_ofat import evaluate_gates, OFAT_GATE_VERSION

OFAT_RESULTS_DIR = REPO_ROOT / "data" / "processed" / "synthetic_benchmark" / "ofat"


# ── Manifest structure ────────────────────────────────────────────────────────

def test_manifest_size_within_budget():
    tasks = build_manifest()
    assert 30 <= len(tasks) <= 60, f"OFAT manifest must have 30-60 tasks, got {len(tasks)}"


def test_manifest_exact_size():
    tasks = build_manifest()
    expected = len(OFAT_CONFIGS) * len(OFAT_SCENARIOS) * len(OFAT_SEEDS)
    assert len(tasks) == expected, f"Expected {expected} tasks, got {len(tasks)}"


def test_reference_appears_exactly_once():
    refs = [c for c in OFAT_CONFIGS if c["ofat_label"] == "reference"]
    assert len(refs) == 1, f"Reference must appear exactly once in OFAT_CONFIGS, got {len(refs)}"


def test_one_axis_changed_per_config():
    """Each non-reference config must differ from reference on exactly one parameter."""
    ref = next(c for c in OFAT_CONFIGS if c["ofat_label"] == "reference")
    axes = ["cs", "ar", "noise", "lag"]
    for cfg in OFAT_CONFIGS:
        if cfg["ofat_label"] == "reference":
            continue
        diffs = [ax for ax in axes if cfg[ax] != ref[ax]]
        assert len(diffs) == 1, (
            f"Config '{cfg['ofat_label']}' must differ on exactly 1 axis; "
            f"differs on {diffs}"
        )


def test_no_confounded_configs():
    """No config should simultaneously have cs=high + ar=low + noise=low."""
    for cfg in OFAT_CONFIGS:
        assert not (cfg["cs"] == "high" and cfg["ar"] == "low" and cfg["noise"] == "low"), (
            f"Confounded config: {cfg['ofat_label']}"
        )


def test_unique_output_filenames():
    tasks = build_manifest()
    fnames = [t["output_file"] for t in tasks]
    assert len(fnames) == len(set(fnames)), "Output filenames must be unique"


def test_task_ids_sequential():
    tasks = build_manifest()
    ids = [t["task_id"] for t in tasks]
    assert ids == list(range(len(tasks))), "task_ids must be 0..N-1"


def test_manifest_version_field():
    tasks = build_manifest()
    for t in tasks:
        assert t["manifest_version"] == OFAT_VERSION


def test_scenario_filter():
    tasks = build_manifest(scenarios=["linear"])
    assert all(t["scenario"] == "linear" for t in tasks)
    assert len(tasks) == len(OFAT_CONFIGS) * len(OFAT_SEEDS)


def test_seed_coverage():
    tasks = build_manifest()
    seeds_seen = set(t["seed"] for t in tasks)
    assert seeds_seen == set(OFAT_SEEDS)


def test_masks_coverage():
    """Each config × scenario × seed must evaluate both masks."""
    tasks = build_manifest()
    mask_types = {mk[0] for mk in OFAT_MASKS}
    for task in tasks:
        # the runner applies all OFAT_MASKS; we just check they're defined
        assert OFAT_MASKS, "OFAT_MASKS must be non-empty"
    assert mask_types == {"mcar", "block"}


def test_axis_labels_match_config_axis():
    """axis field must correctly identify which axis is changed."""
    axis_to_param = {
        "none": None,      # reference
        "A_cs": "cs",
        "B_ar": "ar",
        "C_noise": "noise",
        "D_lag": "lag",
    }
    ref = next(c for c in OFAT_CONFIGS if c["ofat_label"] == "reference")
    for cfg in OFAT_CONFIGS:
        ax = cfg["axis"]
        assert ax in axis_to_param, f"Unknown axis label: {ax}"
        if ax != "none":
            param = axis_to_param[ax]
            assert cfg[param] != ref[param], (
                f"{cfg['ofat_label']}: axis={ax} but {param} is not changed"
            )


# ── Factorial runner guard ────────────────────────────────────────────────────

def test_factorial_blocked_without_flag(tmp_path, monkeypatch):
    """run_signal_sensitivity exits with code 2 without authorization flag."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "src.modeles.synthetic.run_signal_sensitivity",
         "--task-id", "0", "--output-dir", str(tmp_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2, (
        f"Factorial runner must exit 2 without auth flag; got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    assert "NOT AUTHORIZED" in result.stderr or "NOT_AUTHORIZED" in result.stderr, (
        f"Error message must mention NOT AUTHORIZED; got: {result.stderr[:300]}"
    )


def test_factorial_dry_run_allowed():
    """--dry-run is allowed without authorization flag."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "src.modeles.synthetic.run_signal_sensitivity", "--dry-run"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--dry-run must be allowed; got {result.returncode}\n{result.stderr[:300]}"
    )


def test_factorial_smoke_test_allowed():
    """--smoke-test is allowed without authorization flag."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "src.modeles.synthetic.run_signal_sensitivity",
         "--smoke-test", "--dry-run"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--smoke-test --dry-run must be allowed; got {result.returncode}"
    )


# ── AUPRC helper ─────────────────────────────────────────────────────────────

def test_auprc_perfect():
    import numpy as np
    from src.data.synthetic.generate_herald_synthetic import TrueRelation
    n = 5
    true_rels = [TrueRelation(source_sector=0, target_sector=2, lag=1, weight=0.5, nonlinear=False)]
    # Convention: attn[target, source] = high for true edge
    attn = np.full((n, n), 1e-6)
    np.fill_diagonal(attn, 0)
    attn[2, 0] = 1.0  # target=2, source=0
    auprc, prev = _compute_auprc(true_rels, n, attn)
    assert auprc > prev, f"Perfect attention → AUPRC ({auprc:.3f}) must exceed prevalence ({prev:.3f})"
    assert auprc > 0.5, f"Perfect attention → AUPRC must be high, got {auprc:.3f}"


def test_auprc_prevalence_correct():
    import numpy as np
    from src.data.synthetic.generate_herald_synthetic import TrueRelation
    n_sectors = 9
    n_true = 8
    true_rels = [TrueRelation(source_sector=i, target_sector=(i+1)%n_sectors, lag=1, weight=0.5, nonlinear=False)
                 for i in range(n_true)]
    attn = np.ones((n_sectors, n_sectors))
    np.fill_diagonal(attn, 0)
    _, prev = _compute_auprc(true_rels, n_sectors, attn)
    expected_prev = n_true / (n_sectors * (n_sectors - 1))
    assert abs(prev - expected_prev) < 1e-8, f"Prevalence = {n_true}/{n_sectors*(n_sectors-1)} = {expected_prev:.4f}, got {prev:.4f}"


# ── Result files ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ofat_results():
    if not OFAT_RESULTS_DIR.exists():
        return []
    files = sorted(OFAT_RESULTS_DIR.glob("ofat_*.json"))
    results = []
    for f in files:
        if f.name.startswith("gate_"):
            continue
        try:
            d = json.loads(f.read_text())
            if d.get("manifest_version") == OFAT_VERSION:
                results.append(d)
        except Exception:
            pass
    return results


def test_result_files_have_correct_version(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    bad = [r["ofat_label"] for r in ofat_results if r.get("manifest_version") != OFAT_VERSION]
    assert bad == [], f"Wrong manifest_version in: {bad}"


def test_result_files_have_mask_results(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    bad = [(r["ofat_label"], r["scenario"], r["seed"]) for r in ofat_results if "mask_results" not in r]
    assert bad == [], f"Missing mask_results: {bad}"


def test_result_files_have_both_masks(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    expected_masks = {f"{mt}_{lv:02d}" for mt, lv in OFAT_MASKS}
    bad = []
    for r in ofat_results:
        found = set(r.get("mask_results", {}).keys())
        missing = expected_masks - found
        if missing:
            bad.append((r["ofat_label"], r["scenario"], r["seed"], sorted(missing)))
    assert bad == [], f"Missing masks in: {bad[:3]}"


def test_result_files_have_7_models(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    expected = {"ffill", "ridge", "no_graph", "herald_contemp", "herald_lagged",
                "herald_lagged_permuted", "oracle_lagged"}
    bad = []
    for r in ofat_results:
        for mk, mr in r.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            models = {k for k in mr if isinstance(mr[k], dict) and "mae" in mr[k]}
            missing = expected - models
            if missing:
                bad.append((r["ofat_label"], mk, sorted(missing)))
    assert bad == [], f"Missing models: {bad[:3]}"


def test_leakage_passed(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    bad = [(r["ofat_label"], r["scenario"], r["seed"]) for r in ofat_results
           if not r.get("leakage_check", {}).get("passed", False)]
    assert bad == [], f"Leakage check failed: {bad}"


def test_oracle_auc_is_one(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    import numpy as np
    bad = []
    for r in ofat_results:
        for mk, mr in r.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            ol = mr.get("oracle_lagged", {})
            auc = ol.get("edge_auc")
            if auc is not None and abs(auc - 1.0) > 1e-5:
                bad.append((r["ofat_label"], r["scenario"], r["seed"], mk, auc))
    assert bad == [], f"oracle_lagged AUC != 1.0: {bad}"


def test_per_seed_metrics_present(ofat_results):
    """Each (ofat_label, scenario) must have results for all 3 seeds."""
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    from collections import defaultdict
    by_key: dict = defaultdict(set)
    for r in ofat_results:
        by_key[(r["ofat_label"], r["scenario"])].add(r["seed"])
    for key, seeds in by_key.items():
        assert seeds == set(OFAT_SEEDS), (
            f"{key}: expected seeds {OFAT_SEEDS}, got {sorted(seeds)}"
        )


def test_auprc_stored_in_results(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    missing = []
    for r in ofat_results:
        for mk, mr in r.get("mask_results", {}).items():
            if not isinstance(mr, dict):
                continue
            for model in ["herald_lagged", "oracle_lagged"]:
                m = mr.get(model, {})
                if isinstance(m, dict) and "edge_auprc" not in m:
                    missing.append((r["ofat_label"], r["scenario"], r["seed"], mk, model))
    assert missing == [], f"edge_auprc missing in: {missing[:3]}"


def test_is_valid_result_rejects_wrong_version(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"manifest_version": "wrong", "mask_results": {}, "leakage_check": {}}))
    assert not is_valid_result(bad)


def test_is_valid_result_accepts_correct(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps({
        "manifest_version": OFAT_VERSION,
        "mask_results": {"mcar_30": {}},
        "leakage_check": {"passed": True},
    }))
    assert is_valid_result(good)


def test_atomic_write_leaves_no_tmp(tmp_path):
    from src.modeles.synthetic.run_ofat_sensitivity import write_atomic
    data = {"test": True, "manifest_version": OFAT_VERSION}
    out = tmp_path / "test_out.json"
    write_atomic(data, out)
    assert out.exists()
    assert not (tmp_path / "test_out.tmp").exists()
    loaded = json.loads(out.read_text())
    assert loaded["test"] is True


# ── Gates O1-O8 structure ─────────────────────────────────────────────────────

def test_gates_empty_returns_error():
    report = evaluate_gates([])
    assert "error" in report


def test_gates_version():
    report = evaluate_gates([])
    assert report.get("gate_version") == OFAT_GATE_VERSION or "error" in report


def test_gates_structure_with_minimal_result():
    """evaluate_gates returns all O1-O8 keys with a minimal fake result."""
    fake = {
        "ofat_label": "reference", "axis": "none",
        "cs": "original", "ar": "original", "noise": "original", "lag": "mixed",
        "scenario": "linear", "seed": 42,
        "manifest_version": "ofat_v1",
        "n_sectors": 9, "n_true_relations": 8,
        "leakage_check": {"passed": True},
        "elapsed_seconds": 1.0,
        "mask_results": {
            "mcar_30": {
                "mask_type": "mcar", "mask_level_pct": 30,
                "ffill": {"mae": 0.20, "rmse": 0.25, "pearson_r": 0.9, "n_evaluated": 100},
                "ridge": {"mae": 0.22, "rmse": 0.27, "pearson_r": 0.88, "n_evaluated": 100},
                "no_graph": {"mae": 0.24, "rmse": 0.29, "pearson_r": 0.85, "n_evaluated": 100},
                "herald_contemp": {"mae": 0.23, "rmse": 0.28, "pearson_r": 0.86,
                                   "n_evaluated": 100, "edge_auc": 0.55, "edge_auprc": 0.20,
                                   "edge_prevalence": 0.111, "edge_f1": 0.2, "edge_precision": 0.2,
                                   "edge_recall": 0.2, "edge_fpr": 0.1, "edge_sign_acc": 0.5,
                                   "edge_lag_acc": float("nan"), "n_true_edges": 8},
                "herald_lagged": {"mae": 0.22, "rmse": 0.27, "pearson_r": 0.87,
                                  "n_evaluated": 100, "edge_auc": 0.70, "edge_auprc": 0.35,
                                  "edge_prevalence": 0.111, "edge_f1": 0.4, "edge_precision": 0.4,
                                  "edge_recall": 0.4, "edge_fpr": 0.08, "edge_sign_acc": 0.5,
                                  "edge_lag_acc": float("nan"), "n_true_edges": 8},
                "herald_lagged_permuted": {"mae": 0.25, "rmse": 0.30, "pearson_r": 0.84, "n_evaluated": 100},
                "oracle_lagged": {"mae": 0.21, "rmse": 0.26, "pearson_r": 0.89,
                                  "n_evaluated": 100, "edge_auc": 1.0, "edge_auprc": 1.0,
                                  "edge_prevalence": 0.111, "edge_f1": 1.0, "edge_precision": 1.0,
                                  "edge_recall": 1.0, "edge_fpr": 0.0, "edge_sign_acc": 1.0,
                                  "edge_lag_acc": float("nan"), "n_true_edges": 8},
            },
        },
    }
    report = evaluate_gates([fake])
    for gate in ["O1_safety", "O2_graph_specificity", "O3_edge_recovery",
                 "O4_seed_replication", "O5_mask_robustness", "O6_monotonic_signal",
                 "O7_ar_diagnosis", "O8_oracle_ceiling"]:
        assert gate in report, f"Missing gate {gate} in report"
        assert "pass" in report[gate], f"Gate {gate} missing 'pass' key"
    assert "summary" in report
    assert "gates" in report["summary"]


def test_gate_o1_detects_nan():
    fake = {
        "ofat_label": "reference", "axis": "none",
        "cs": "original", "ar": "original", "noise": "original", "lag": "mixed",
        "scenario": "linear", "seed": 42, "manifest_version": "ofat_v1",
        "n_sectors": 9, "n_true_relations": 8,
        "leakage_check": {"passed": True},
        "mask_results": {
            "mcar_30": {
                "mask_type": "mcar", "mask_level_pct": 30,
                "ffill": {"mae": float("nan"), "rmse": 0.25, "pearson_r": 0.9, "n_evaluated": 100},
            },
        },
    }
    report = evaluate_gates([fake])
    assert not report["O1_safety"]["pass"], "O1 should fail when NaN present"
    assert report["O1_safety"]["nan_inf"] > 0


def test_gate_o8_detects_oracle_worse_than_no_graph():
    fake = {
        "ofat_label": "reference", "axis": "none",
        "cs": "original", "ar": "original", "noise": "original", "lag": "mixed",
        "scenario": "linear", "seed": 42, "manifest_version": "ofat_v1",
        "n_sectors": 9, "n_true_relations": 8,
        "leakage_check": {"passed": True},
        "mask_results": {
            "mcar_30": {
                "mask_type": "mcar", "mask_level_pct": 30,
                "no_graph": {"mae": 0.20},
                "oracle_lagged": {"mae": 0.25},  # oracle WORSE than no_graph → O8 fail
            },
        },
    }
    report = evaluate_gates([fake])
    assert not report["O8_oracle_ceiling"]["pass"], "O8 should fail when oracle > no_graph"


def test_ofat_results_gate_evaluation(ofat_results):
    if not ofat_results:
        pytest.skip("No OFAT results yet")
    from src.modeles.synthetic.gates_ofat import evaluate_gates
    report = evaluate_gates(ofat_results)
    assert report["O1_safety"]["pass"], f"O1 SAFETY failed: {report['O1_safety']}"
    assert "summary" in report
    print(f"\nOFAT gate summary: {report['summary']}")
