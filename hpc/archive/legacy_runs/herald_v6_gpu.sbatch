#!/bin/bash
#SBATCH --job-name=herald-v6
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=1-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

SECTION="${1:-all}"
PROJECT_DIR="${SLURM_SUBMIT_DIR}"
ENV_SH="${HOME}/venvs/herald-v5-env.sh"

cd "${PROJECT_DIR}"
mkdir -p logs reports data/processed

if [ ! -f "${ENV_SH}" ]; then
  echo "Missing ${ENV_SH}"
  echo "Prepare the Python environment first."
  exit 2
fi

source "${ENV_SH}"
export PYTHON="$(command -v python)"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "section=${SECTION}"
echo "project=${PROJECT_DIR}"
echo "python=${PYTHON}"
python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
PY

bash run_herald_v6.sh "${SECTION}"
