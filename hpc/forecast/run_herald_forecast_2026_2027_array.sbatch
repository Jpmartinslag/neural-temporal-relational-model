#!/bin/bash
#SBATCH --job-name=herald-forecast-2627
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=03:00:00

set -euo pipefail

SEEDS_ARRAY=($SEEDS)
SEED=${SEEDS_ARRAY[$SLURM_ARRAY_TASK_ID]}
export SEED

echo "SLURM_JOB_ID=${SLURM_JOB_ID}"
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}"
echo "SEED=${SEED}"
echo "HOST=$(hostname)"

bash hpc/forecast/run_herald_forecast_2026_2027_seed.sh
