from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from hpc.france_ze2020_context_sector_relation.audit_fr_ze2020_context_sector_relation_hpc import (
    EXPECTED_FOLDS,
    EXPECTED_SEEDS,
    EXPECTED_YEARS,
    METRICS_NAME,
    audit_run,
)
from src.modeles.france_ze2020.run_fr_ze2020_context_conditioned_sector_relation_gate import (
    CLAIM_STATUS,
    VIEW_NAMES,
)

ROOT = Path(__file__).resolve().parents[1]
HPC_DIR = ROOT / "hpc/france_ze2020_context_sector_relation"


def test_hpc_package_has_expected_files() -> None:
    expected = {
        "README.md",
        "run_fr_ze2020_context_sector_relation_task.sh",
        "run_fr_ze2020_context_sector_relation_array.sbatch",
        "submit_fr_ze2020_context_sector_relation_hpc.sh",
        "audit_fr_ze2020_context_sector_relation_hpc.py",
    }
    assert expected == {path.name for path in HPC_DIR.iterdir() if path.is_file()}


def test_submitter_is_dry_run_by_default() -> None:
    text = (HPC_DIR / "submit_fr_ze2020_context_sector_relation_hpc.sh").read_text()
    assert "CONFIRM=0" in text
    assert "--confirm-submit" in text
    assert 'if [[ "${CONFIRM}" -eq 1 ]]' in text


def test_array_and_audit_share_fixed_population() -> None:
    array_text = (
        HPC_DIR / "run_fr_ze2020_context_sector_relation_array.sbatch"
    ).read_text()
    task_text = (
        HPC_DIR / "run_fr_ze2020_context_sector_relation_task.sh"
    ).read_text()
    assert "#SBATCH --array=0-4" in array_text
    assert EXPECTED_SEEDS == [42, 43, 44, 45, 46]
    assert EXPECTED_YEARS == list(range(2019, 2026))
    assert EXPECTED_FOLDS == list(range(5))
    assert "2019 2020 2021 2022 2023 2024 2025" in task_text
    assert "0 1 2 3 4" in task_text


def test_task_writes_seed_isolated_output() -> None:
    text = (HPC_DIR / "run_fr_ze2020_context_sector_relation_task.sh").read_text()
    assert "seed_${SEED}" in text
    assert "--max-epochs" in text
    assert ":-500" in text


def test_hpc_auditor_aggregates_complete_seed_outputs() -> None:
    control_mae = {
        "no_source_mlp": 1.1,
        "pooled_linear_relation": 1.1,
        "context_conditioned_mlp": 1.0,
        "source_shuffled_mlp": 1.2,
        "context_shuffled_mlp": 1.2,
        "target_shuffled_mlp": 1.2,
    }
    with TemporaryDirectory() as directory:
        run_dir = Path(directory)
        for seed in EXPECTED_SEEDS:
            rows = []
            for year in EXPECTED_YEARS:
                for fold in EXPECTED_FOLDS:
                    for view in VIEW_NAMES:
                        rows.append(
                            {
                                "view": view,
                                "seed": seed,
                                "eval_year": year,
                                "ze_fold": fold,
                                "n_train": 1000,
                                "n_test": 100,
                                "n_train_years": 4,
                                "train_test_ze_overlap": 0,
                                "mae": control_mae[view],
                                "r2": 0.1,
                                "model_n_iter": 20,
                                "model_converged": 1,
                                "target_shuffled": int(
                                    view == "target_shuffled_mlp"
                                ),
                                "claim_status": CLAIM_STATUS,
                            }
                        )
            seed_dir = run_dir / f"seed_{seed}"
            seed_dir.mkdir()
            pd.DataFrame(rows).to_csv(seed_dir / METRICS_NAME, index=False)
        report = audit_run(run_dir)
    assert report["n_metric_rows"] == 1050
    assert all(report["integrity"].values())
    assert report["gate"]["gate_pass"] is True
