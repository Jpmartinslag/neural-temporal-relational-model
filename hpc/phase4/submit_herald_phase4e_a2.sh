#!/bin/bash
# Submit Phase 4E-A2 equivalence battery for all 4 countries.
# 10 seeds x 4 countries x 1 best-equivalence config = 40 runs.

set -euo pipefail

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
SEEDS="0 1 7 13 17 42 77 99 123 2025"
N_SEEDS=10
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}

echo "=== Phase 4E-A2 submit $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "Seeds : $SEEDS"
echo "Epochs: $EPOCHS"

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

python3 hpc/phase4/prepare_phase4e_panel.py --country all
python3 -m py_compile hpc/phase4/run_herald_phase4e_a2_wrapper.py

for COUNTRY in fr nl be pt; do
  OUT_ROOT="hpc_results/herald_phase4e_a2_${COUNTRY}_${TIMESTAMP}_r1"
  if [ -d "$OUT_ROOT" ]; then
    echo "ERROR: $OUT_ROOT already exists; refusing overwrite." >&2
    exit 1
  fi
  mkdir -p "$OUT_ROOT"/{reports/per_run,reports/sector,data_processed,logs,metadata}
  echo "[$COUNTRY] OUT_ROOT=$OUT_ROOT expected_runs=$N_SEEDS"
  JOB_ID=$(sbatch \
    --array="0-$((N_SEEDS-1))" \
    --export="ALL,COUNTRY=${COUNTRY},OUT_ROOT=${OUT_ROOT},EPOCHS=${EPOCHS},MASK_WARMUP=${MASK_WARMUP},SEEDS=${SEEDS}" \
    hpc/phase4/run_herald_phase4e_a2_array.sbatch \
    | awk '{print $NF}')
  echo "[$COUNTRY] job=$JOB_ID"
done

echo "Monitor: squeue -u \$USER"
