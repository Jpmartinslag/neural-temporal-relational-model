#!/bin/bash
#SBATCH --job-name=herald-phase4eb
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=4:00:00
#SBATCH --output=logs/%x-%A_%a.out
#SBATCH --error=logs/%x-%A_%a.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
COUNTRY=${COUNTRY:?COUNTRY env var required}
OUT_ROOT=${OUT_ROOT:?OUT_ROOT env var required}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
DEVICE=${DEVICE:-}

read -r -a SEED_ARRAY <<< "$SEEDS"
IDX=${SLURM_ARRAY_TASK_ID:-0}
if [ "$IDX" -ge "${#SEED_ARRAY[@]}" ]; then
  echo "Array index ${IDX} outside SEEDS length ${#SEED_ARRAY[@]}" >&2
  exit 1
fi
SEED=${SEED_ARRAY[$IDX]}

echo "Phase 4E-B [${COUNTRY}] seed=${SEED} node=$(hostname) $(date '+%Y-%m-%d %H:%M:%S')"

SEED="$SEED" \
COUNTRY="$COUNTRY" \
OUT_ROOT="$OUT_ROOT" \
EPOCHS="$EPOCHS" \
MASK_WARMUP="$MASK_WARMUP" \
${DEVICE:+DEVICE="$DEVICE"} \
bash hpc/phase4/run_herald_phase4e_b_seed.sh

echo "Phase 4E-B [${COUNTRY}] seed=${SEED} finished $(date '+%Y-%m-%d %H:%M:%S')"
