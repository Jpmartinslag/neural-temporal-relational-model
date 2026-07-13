import json
from pathlib import Path

import pandas as pd

from hpc.france_ze2020_top3_entry_lift.audit_fr_ze2020_top3_entry_lift_hpc_results import (
    EXPECTED_SCENARIOS,
    EXPECTED_SEEDS,
    audit_run,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HPC_DIR = REPO_ROOT / "hpc/france_ze2020_top3_entry_lift"


def test_top3_entry_lift_hpc_scripts_exist_and_are_dry_run_safe():
    submit = (HPC_DIR / "submit_fr_ze2020_top3_entry_lift_hpc.sh").read_text()
    array = (HPC_DIR / "run_fr_ze2020_top3_entry_lift_array.sbatch").read_text()
    task = (HPC_DIR / "run_fr_ze2020_top3_entry_lift_task.sh").read_text()
    assert "--confirm-submit" in submit
    assert "DRY RUN" in submit
    assert "#SBATCH --array=0-19" in array
    assert "SCENARIOS=(full_control temporal_shuffle sector_shuffle target_shuffle)" in array
    assert "FR_ZE2020_TOP3_ENTRY_LIFT_MAX_EPOCHS" in task
    assert "run_fr_ze2020_top3_entry_lift_falsifications.py" in task


def test_top3_entry_lift_hpc_scripts_have_no_forbidden_claim_terms():
    forbidden_terms = [
        "recommended" + "_action",
        "policy" + "_action",
        "causal" + "_effect",
        "causal" + "_impact",
    ]
    for path in HPC_DIR.glob("*"):
        if path.is_file():
            text = path.read_text()
            for term in forbidden_terms:
                assert term not in text


def _write_task_outputs(task_dir: Path, scenario: str, seed: int, lift_ndcg: float) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    metrics = pd.DataFrame(
        [
            {
                "model": "mlp_entry_classifier",
                "precision_at_k": 0.5,
                "hit_rate_at_k": 0.9,
                "ndcg_at_k": lift_ndcg,
                "falsification_scenario": scenario,
                "feature_config": "base_plus_target_aligned_lifts",
                "seed": seed,
                "claim_status": "top3_entry_lift_falsification_not_recommendation",
            },
            {
                "model": "mlp_entry_classifier",
                "precision_at_k": 0.45,
                "hit_rate_at_k": 0.85,
                "ndcg_at_k": 0.62,
                "falsification_scenario": scenario,
                "feature_config": "base_formula_features",
                "seed": seed,
                "claim_status": "top3_entry_lift_falsification_not_recommendation",
            },
            {
                "model": "mlp_entry_classifier",
                "precision_at_k": 0.4,
                "hit_rate_at_k": 0.8,
                "ndcg_at_k": 0.5,
                "falsification_scenario": scenario,
                "feature_config": "no_relation_features",
                "seed": seed,
                "claim_status": "top3_entry_lift_falsification_not_recommendation",
            },
            {
                "model": "mlp_entry_classifier",
                "precision_at_k": 0.43,
                "hit_rate_at_k": 0.82,
                "ndcg_at_k": 0.55,
                "falsification_scenario": scenario,
                "feature_config": "shuffled_target_aligned_lifts",
                "seed": seed,
                "claim_status": "top3_entry_lift_falsification_not_recommendation",
            },
        ]
    )
    metrics.to_csv(task_dir / "fr_ze2020_top3_entry_lift_falsification_metrics_v1.csv", index=False)
    pd.DataFrame(
        [
            {
                "ze2020": "0051",
                "sector_code": "BE",
                "decision_year": 2020,
                "score": 0.7,
                "claim_status": "top3_entry_lift_falsification_not_recommendation",
            }
        ]
    ).to_csv(task_dir / "fr_ze2020_top3_entry_lift_falsification_predictions_v1.csv", index=False)
    metrics.to_csv(task_dir / "fr_ze2020_top3_entry_lift_falsification_summary_v1.csv", index=False)
    (task_dir / "fr_ze2020_top3_entry_lift_falsification_run_v1.json").write_text(
        json.dumps({"claim_status": "top3_entry_lift_falsification_not_recommendation"}) + "\n"
    )


def test_top3_entry_lift_hpc_audit_on_synthetic_run(tmp_path):
    run_dir = tmp_path / "fr_ze2020_top3_entry_lift_test"
    for scenario in EXPECTED_SCENARIOS:
        for seed in EXPECTED_SEEDS:
            lift = 0.7
            if scenario == "temporal_shuffle":
                lift = 0.6
            if scenario == "sector_shuffle":
                lift = 0.58
            if scenario == "target_shuffle":
                lift = 0.40
            _write_task_outputs(run_dir / scenario / f"seed_{seed}", scenario, seed, lift)

    report = audit_run(run_dir)
    assert report["n_task_dirs"] == 20
    assert report["gates"]["G1_complete_outputs"] is True
    assert report["gates"]["G2_lift_beats_no_relation_mlp"] is True
    assert report["gates"]["G3_lift_beats_base_formula_mlp"] is True
    assert report["gates"]["G4_lift_beats_shuffled_lift_mlp"] is True
    assert report["gates"]["G5_temporal_and_sector_shuffle_degrade_lift_mlp"] is True
    assert report["gates"]["G6_output_separation"] is True
    assert report["gates"]["G7_target_shuffle_degrades_lift_mlp"] is True
    assert report["paired_comparisons"]["lift_vs_shuffled_lift"]["win_rate"] == 1.0
