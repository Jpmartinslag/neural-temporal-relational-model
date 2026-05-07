#!/bin/bash
#SBATCH --job-name=herald-semi
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results
source "${HOME}/venvs/herald-v5-env.sh"

export PYTHON="$(command -v python)"
export EPOCHS="${EPOCHS:-1500}"
export MASK_WARMUP="${MASK_WARMUP:-100}"
export OUT_ROOT="hpc_results/herald_semi_${SLURM_JOB_ID}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "epochs=${EPOCHS}"
echo "mask_warmup=${MASK_WARMUP}"
echo "out_root=${OUT_ROOT}"

python - <<'PY'
from pathlib import Path
import pandas as pd
import torch

required = [
    "src/data/train_herald_semi_v1.py",
    "run_herald_semi.sh",
    "metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv",
    "data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv",
    "data/processed/side_creations_a10_ze2020_through_2025_v1.csv",
    "metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv",
    "data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv",
    "data/processed/graph_adjacency_core_v0.csv",
    "data/processed/graph_adjacency_mobility_v0.csv",
]
for item in required:
    path = Path(item)
    print(item, path.exists(), path.stat().st_size if path.exists() else 0)
    if not path.exists():
        raise SystemExit(f"missing required file: {item}")

panel = pd.read_csv("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
splits = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv")
pre = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv")
a10 = pd.read_csv("data/processed/side_creations_a10_ze2020_through_2025_v1.csv")

print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
print("panel", panel.shape, int(panel.target_year.min()), int(panel.target_year.max()), panel.ZE2020.nunique())
print("splits", splits.eval_year.tolist())
print("precovid_splits", pre.eval_year.tolist())
print("a10_rows_2025", int((a10.target_year == 2025).sum()))
print("expected_runs", 65)
PY

bash -n run_herald_semi.sh
python -m py_compile src/data/train_herald_semi_v1.py

PYTHON="${PYTHON}" EPOCHS="${EPOCHS}" MASK_WARMUP="${MASK_WARMUP}" OUT_ROOT="${OUT_ROOT}" \
  bash run_herald_semi.sh all

echo "results=${OUT_ROOT}"
echo "metrics=${OUT_ROOT}/reports/herald_semi_metrics_v1.json"
echo "precovid_metrics=${OUT_ROOT}/reports/herald_semi_precovid_metrics_v1.json"
