#!/bin/bash
#SBATCH --job-name=h96-grid
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --array=0-119%24
#SBATCH --output=hpc_results/herald96/logs/grid-%A_%a.out
#SBATCH --error=hpc_results/herald96/logs/grid-%A_%a.err
set -euo pipefail
cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

# Two scenarios by three scales by four supports by five seeds, eighty zones. The seeds
# 9961-9965 have never been generated; every calibration decision was taken on 9951.
python3 hpc/herald96/run_neural_granger.py \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --out-dir hpc_results/herald96/tasks --n-zones 80 --n-score 12
