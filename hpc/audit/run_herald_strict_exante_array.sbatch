#!/bin/bash
#SBATCH --job-name=herald-strict-exante
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --array=0-9%10
#SBATCH --output=%x-%A_%a.out
#SBATCH --error=%x-%A_%a.err

set -euo pipefail

SEEDS_STR=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
read -r -a SEED_ARRAY <<< "$SEEDS_STR"
SEED=${SEED_ARRAY[$SLURM_ARRAY_TASK_ID]}

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID}"
echo "array_task=${SLURM_ARRAY_TASK_ID}"
echo "seed=${SEED}"
echo "out_root=${OUT_ROOT}"
echo "python=${PYTHON:-python3}"
echo "epochs=${EPOCHS:-800}"
echo "run_global=${RUN_GLOBAL:-0}"
echo "start=$(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p "$OUT_ROOT/logs"
cp "$SLURM_SUBMIT_DIR/herald-strict-exante-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.out" "$OUT_ROOT/logs/" 2>/dev/null || true

SEED="$SEED" bash hpc/audit/run_herald_strict_exante_seed.sh

echo "end=$(date '+%Y-%m-%d %H:%M:%S')"
echo "results=${OUT_ROOT}"
