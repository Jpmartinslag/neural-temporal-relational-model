#!/bin/bash
#SBATCH --job-name=h93-grid
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=01:30:00
#SBATCH --array=0-49%25
#SBATCH --output=hpc_results/herald93/logs/grid-%A_%a.out
#SBATCH --error=hpc_results/herald93/logs/grid-%A_%a.err
set -euo pipefail

cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8

# The core grid: five methods, two scenarios, the five final seeds, width 64.
python3 hpc/herald93/run_model_benchmark.py \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --out-dir hpc_results/herald93/tasks_v2 \
  --n-zones 280 --n-score 12 --epochs 30 --widths 64
