from pathlib import Path

import pandas as pd

from hpc.france_ze2020_relation_objective.audit_fr_ze2020_relation_objective_hpc_results import (
    build_report,
    find_seed_dirs,
    gate_g5_output_separation,
)


def _write_seed(base: Path, seed: int, *, real_lift: float = 0.12, shuffle_lift: float = 0.03) -> None:
    seed_dir = base / f"seed_{seed}"
    seed_dir.mkdir(parents=True)
    rows = []
    for scenario, ap, best_formula, lift in [
        ("dual_endpoint_matched_negatives", 0.95, 0.95 - real_lift, real_lift),
        ("dual_endpoint_temporal_sector_shuffle", 0.65, 0.65 - shuffle_lift, shuffle_lift),
    ]:
        rows.append(
            {
                "eval_year": "mean",
                "falsification_scenario": scenario,
                "negative_strategy": "dual_endpoint_matched_hard",
                "model_or_score": "relation_logit",
                "score_family": "local_learner",
                "average_precision": ap,
                "roc_auc": ap - 0.02,
                "n_rows": 100,
                "n_positive": 50,
                "claim_status": "relation_lift_over_formulas_audit_exploratory_not_recommendation",
                "best_formula_ap": best_formula,
                "best_formula_auc": best_formula - 0.02,
                "ap_lift_over_best_formula": lift,
                "auc_lift_over_best_formula": lift - 0.01,
            }
        )
    pd.DataFrame(rows).to_csv(
        seed_dir / "fr_ze2020_relation_lift_over_formulas_metrics_v1.csv",
        index=False,
    )


def test_find_seed_dirs(tmp_path):
    _write_seed(tmp_path, 42)
    _write_seed(tmp_path, 43)
    assert set(find_seed_dirs(tmp_path)) == {42, 43}


def test_relation_objective_hpc_report_passes_clean_fixture(tmp_path):
    for seed in [42, 43, 44]:
        _write_seed(tmp_path, seed)
    report = build_report(tmp_path, expected_seeds=[42, 43, 44])
    assert report["gates"]["G1_no_errors"]["passed"] is True
    assert report["gates"]["G2_real_lift_over_formula"]["passed"] is True
    assert report["gates"]["G3_shuffle_degradation"]["passed"] is True
    assert report["gates"]["G4_lift_stability"]["passed"] is True
    assert report["gates"]["G5_output_separation"]["passed"] is True


def test_relation_objective_hpc_report_fails_missing_seed(tmp_path):
    _write_seed(tmp_path, 42)
    report = build_report(tmp_path, expected_seeds=[42, 43])
    assert report["gates"]["G1_no_errors"]["passed"] is False
    assert report["gates"]["G1_no_errors"]["missing_seeds"] == [43]


def test_relation_objective_hpc_report_fails_small_lift(tmp_path):
    for seed in [42, 43, 44]:
        _write_seed(tmp_path, seed, real_lift=0.01)
    report = build_report(tmp_path, expected_seeds=[42, 43, 44])
    assert report["gates"]["G2_real_lift_over_formula"]["passed"] is False


def test_relation_objective_hpc_report_fails_weak_shuffle_drop(tmp_path):
    for seed in [42, 43, 44]:
        _write_seed(tmp_path, seed, real_lift=0.12, shuffle_lift=0.10)
    report = build_report(tmp_path, expected_seeds=[42, 43, 44])
    assert report["gates"]["G3_shuffle_degradation"]["passed"] is True
    seed_dir = tmp_path / "seed_44"
    df = pd.read_csv(seed_dir / "fr_ze2020_relation_lift_over_formulas_metrics_v1.csv")
    df.loc[df["falsification_scenario"] == "dual_endpoint_temporal_sector_shuffle", "average_precision"] = 0.88
    df.to_csv(seed_dir / "fr_ze2020_relation_lift_over_formulas_metrics_v1.csv", index=False)
    report = build_report(tmp_path, expected_seeds=[42, 43, 44])
    assert report["gates"]["G3_shuffle_degradation"]["passed"] is False


def test_gate_g5_flags_forbidden_claim_status():
    metrics = pd.DataFrame({"claim_status": ["causal_effect_validated"]})
    assert gate_g5_output_separation(metrics)["passed"] is False
