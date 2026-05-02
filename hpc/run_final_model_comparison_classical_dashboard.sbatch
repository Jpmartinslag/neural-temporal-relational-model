#!/bin/bash
#SBATCH --job-name=final-cmp-cd
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs reports reports/figures data/processed hpc_results/final_model_comparison_20260429
source "${HOME}/venvs/herald-v5-env.sh"
export PYTHON="$(command -v python)"
export OUT_ROOT="hpc_results/final_model_comparison_20260429"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "out_root=${OUT_ROOT}"

bash run_final_model_comparison.sh classical
bash run_final_model_comparison.sh dashboard
