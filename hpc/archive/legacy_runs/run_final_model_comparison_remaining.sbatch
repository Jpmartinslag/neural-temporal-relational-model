#!/bin/bash
#SBATCH --job-name=final-cmp-rem
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs reports reports/figures data/processed hpc_results/final_model_comparison_20260429
source "${HOME}/venvs/herald-v5-env.sh"
export PYTHON="$(command -v python)"
export OUT_ROOT="hpc_results/final_model_comparison_20260429"
export EPOCHS="${EPOCHS:-800}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "out_root=${OUT_ROOT}"
echo "epochs=${EPOCHS}"

python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
PY

bash run_final_model_comparison.sh herald
bash run_final_model_comparison.sh dashboard
