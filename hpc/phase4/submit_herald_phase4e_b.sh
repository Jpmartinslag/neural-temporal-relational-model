#!/bin/bash
# Submit Phase 4E-B causal feature-policy ablation for all 4 countries.
# 10 seeds × (FR/NL/BE 4 configs + PT 6 configs) = 180 runs.

set -euo pipefail

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
SEEDS="0 1 7 13 17 42 77 99 123 2025"
N_SEEDS=10
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}

echo "=== Phase 4E-B submit $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "Seeds : $SEEDS"
echo "Epochs: $EPOCHS"

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

python3 hpc/phase4/prepare_phase4e_panel.py --country all
python3 -m py_compile hpc/phase4/run_herald_phase4e_a_wrapper.py hpc/phase4/run_herald_phase4e_a2_wrapper.py
bash -n hpc/phase4/phase4e_b_configs.sh hpc/phase4/run_herald_phase4e_b_seed.sh hpc/phase4/run_herald_phase4e_b_array.sbatch

for COUNTRY in fr nl be pt; do
  n_configs=$(COUNTRY="$COUNTRY" bash -lc 'source hpc/phase4/phase4e_b_configs.sh && phase4e_b_configs | wc -l')
  OUT_ROOT="hpc_results/herald_phase4e_b_${COUNTRY}_${TIMESTAMP}_r1"
  if [ -d "$OUT_ROOT" ]; then
    echo "ERROR: $OUT_ROOT already exists; refusing overwrite." >&2
    exit 1
  fi
  mkdir -p "$OUT_ROOT"/{reports/per_run,reports/sector,data_processed,logs,metadata}
  echo "[$COUNTRY] OUT_ROOT=$OUT_ROOT expected_runs=$((N_SEEDS * n_configs)) configs=$n_configs"
  JOB_ID=$(sbatch \
    --array="0-$((N_SEEDS-1))" \
    --export="ALL,COUNTRY=${COUNTRY},OUT_ROOT=${OUT_ROOT},EPOCHS=${EPOCHS},MASK_WARMUP=${MASK_WARMUP},SEEDS=${SEEDS}" \
    hpc/phase4/run_herald_phase4e_b_array.sbatch \
    | awk '{print $NF}')
  echo "[$COUNTRY] job=$JOB_ID"
done

echo "Monitor: squeue -u \$USER"
echo "Audit after completion:"
echo "  python3 hpc/phase4/audit_phase4e_b_results.py --root-fr ... --root-nl ... --root-be ... --root-pt ..."
