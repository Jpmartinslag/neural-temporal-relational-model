"""
Tests for hpc/france_ze2020/audit_fr_ze2020_hpc_results.py -- the
post-collection HPC gate audit (descriptive only, no auto-promotion). Uses
small synthetic seed directories, not real HPC output (none exists yet --
nothing has been submitted, see HERALD_19_FR_ZE2020_HPC_SPEC.md).
"""

from pathlib import Path

import pandas as pd
import pytest

from hpc.france_ze2020.audit_fr_ze2020_hpc_results import (
    build_report,
    find_seed_dirs,
    gate_g5_output_separation,
)


def _write_seed(base: Path, seed: int, *, persistence_wmape: float, candidate_wmape: float) -> None:
    seed_dir = base / f"seed_{seed}"
    seed_dir.mkdir(parents=True)

    pd.DataFrame(
        {
            "eval_year": [2024, 2025],
            "model": ["persistence"] * 2,
            "n_test": [280, 280],
            "n_train_years": [4, 5],
            "wmape": [persistence_wmape, persistence_wmape],
            "claim_status": ["exploratory_smoke"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_baseline_metrics_v1.csv", index=False)

    pd.DataFrame(
        {
            "eval_year": [2024, 2025],
            "model": ["ridge_relational"] * 2,
            "n_test": [280, 280],
            "n_train_years": [4, 5],
            "wmape": [candidate_wmape, candidate_wmape],
            "claim_status": ["relational_smoke_result"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_relational_baseline_metrics_v1.csv", index=False)

    pd.DataFrame(
        {
            "eval_year": [2024, 2025],
            "model": ["mlp_relational"] * 2,
            "n_test": [280, 280],
            "n_train_years": [4, 5],
            "wmape": [candidate_wmape, candidate_wmape],
            "claim_status": ["neural_relational_smoke"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_neural_relational_metrics_v1.csv", index=False)

    pd.DataFrame(
        {
            "feature": ["lag_1"],
            "importance_score": [0.5],
            "eval_year": [2025],
            "claim_status": ["neural_relational_smoke"],
        }
    ).to_csv(seed_dir / "fr_ze2020_neural_relational_feature_signals_v1.csv", index=False)

    pd.DataFrame(
        {
            "eval_year": [2024, 2025],
            "model": ["persistence_sector", "graph_mlp"],
            "n_test": [2520, 2520],
            "n_train_years": [4, 5],
            "wmape": [persistence_wmape, candidate_wmape],
            "claim_status": ["sector_graph_smoke"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_sector_graph_metrics_v1.csv", index=False)

    pd.DataFrame(
        {
            "source_node": ["0051_GI"],
            "target_node": ["0052_GI"],
            "year": [2025],
            "relation_type": ["cross_ze_same_sector"],
            "learned_or_aggregated_weight": [0.9],
            "signal_strength": [0.9],
            "claim_status": ["sector_graph_smoke"],
        }
    ).to_csv(seed_dir / "fr_ze2020_sector_graph_relation_signals_v1.csv", index=False)


@pytest.fixture
def results_dir(tmp_path) -> Path:
    _write_seed(tmp_path, 42, persistence_wmape=0.08, candidate_wmape=0.20)
    _write_seed(tmp_path, 43, persistence_wmape=0.08, candidate_wmape=0.19)
    return tmp_path


def test_find_seed_dirs(results_dir):
    seed_dirs = find_seed_dirs(results_dir)
    assert set(seed_dirs.keys()) == {42, 43}


def test_g1_passes_when_all_files_present_and_finite(results_dir):
    report = build_report(results_dir, expected_seeds=[42, 43])
    assert report["gates"]["G1_no_errors"]["passed"] is True


def test_g1_fails_when_a_seed_is_missing(results_dir):
    report = build_report(results_dir, expected_seeds=[42, 43, 44])
    g1 = report["gates"]["G1_no_errors"]
    assert g1["passed"] is False
    assert 44 in g1["missing_seeds"]


def test_g3_fails_when_candidate_never_beats_baseline(results_dir):
    """Candidate WMAPE (0.19-0.20) is always worse than baseline (0.08) in
    this fixture -- mirrors the real smoke result (HERALD_18/19)."""
    report = build_report(results_dir, expected_seeds=[42, 43])
    g3 = report["gates"]["G3_beats_baseline"]
    assert g3["passed"] is False
    assert g3["per_candidate"]["mlp_relational"]["wins"] == 0


def test_g3_passes_when_candidate_consistently_beats_baseline(tmp_path):
    _write_seed(tmp_path, 42, persistence_wmape=0.20, candidate_wmape=0.05)
    _write_seed(tmp_path, 43, persistence_wmape=0.20, candidate_wmape=0.05)
    _write_seed(tmp_path, 44, persistence_wmape=0.20, candidate_wmape=0.05)
    report = build_report(tmp_path, expected_seeds=[42, 43, 44])
    g3 = report["gates"]["G3_beats_baseline"]
    assert g3["passed"] is True


def test_g4_signal_stability_full_overlap_when_identical_edges(results_dir):
    report = build_report(results_dir, expected_seeds=[42, 43])
    g4 = report["gates"]["G4_signal_stability"]
    assert g4["mean_overlap"] == pytest.approx(1.0)
    assert g4["passed"] is True


def test_g5_flags_a_forbidden_recommendation_column(tmp_path):
    seed_dir = tmp_path / "seed_42"
    seed_dir.mkdir(parents=True)
    pd.DataFrame({"model": ["x"], "wmape": [0.1], "recommendation": ["buy"]}).to_csv(
        seed_dir / "fr_ze2020_baseline_metrics_v1.csv", index=False
    )
    result = gate_g5_output_separation({42: seed_dir})
    assert result["passed"] is False
    assert any("fr_ze2020_baseline_metrics_v1.csv" in v for v in result["violations"])


def test_report_never_contains_a_promotion_instruction(results_dir):
    report = build_report(results_dir, expected_seeds=[42, 43])
    assert report["claim_status"] == "hpc_gate_audit_descriptive_only"
    caveat = report["caveat"].lower()
    assert "no causal claim" in caveat
    assert "no automatic" in caveat or "no recommendation" in caveat
    assert "human decision" in caveat
