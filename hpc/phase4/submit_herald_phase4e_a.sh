#!/bin/bash
# Submit Phase 4E-A for all 4 countries.
# 10 seeds × 4 countries = 40 array jobs.
#
# Usage:
#   bash hpc/phase4/submit_herald_phase4e_a.sh
#   EPOCHS=200 bash hpc/phase4/submit_herald_phase4e_a.sh   # quick test
#
# Outputs go to: hpc_results/herald_phase4e_a_{country}_{timestamp}_r1/

set -euo pipefail

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
SEEDS="0 1 7 13 17 42 77 99 123 2025"
N_SEEDS=10
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}

echo "=== Phase 4E-A submit  $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "    Seeds : $SEEDS"
echo "    Epochs: $EPOCHS"
echo ""

# Step 1: prepare all panels (activate herald-v5 env first)
echo "Preparing Phase 4E-A panels..."
if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi
python3 hpc/phase4/prepare_phase4e_panel.py --country all
echo ""

# Step 2: run audit (non-blocking — informational only for pre-submit check)
python3 -c "
from src.data.european_panel.schema import NON_PREDICTIVE_FIELDS, BASELINE_ANNUAL_FEATURES
print('NON_PREDICTIVE_FIELDS to exclude:', NON_PREDICTIVE_FIELDS)
print('BASELINE_ANNUAL_FEATURES:', BASELINE_ANNUAL_FEATURES)
print('Wrapper will enforce both — OK.')
"
echo ""

for COUNTRY in fr nl be pt; do
  OUT_ROOT="hpc_results/herald_phase4e_a_${COUNTRY}_${TIMESTAMP}_r1"

  # Guard: refuse to overwrite existing results
  if [ -d "$OUT_ROOT" ]; then
    echo "ERROR: $OUT_ROOT already exists — refusing to overwrite." >&2
    exit 1
  fi

  mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata}
  EXPECTED_RUNS=$N_SEEDS

  echo "  [$COUNTRY] OUT_ROOT=$OUT_ROOT"
  echo "  [$COUNTRY] Expected runs after completion: $EXPECTED_RUNS"

  JOB_ID=$(sbatch \
    --array="0-$((N_SEEDS-1))" \
    --export="ALL,COUNTRY=${COUNTRY},OUT_ROOT=${OUT_ROOT},EPOCHS=${EPOCHS},MASK_WARMUP=${MASK_WARMUP}" \
    hpc/phase4/run_herald_phase4e_a_array.sbatch \
    | awk '{print $NF}')

  echo "  [$COUNTRY] Submitted job array: $JOB_ID"
  echo ""
done

echo "=== All Phase 4E-A jobs submitted ==="
echo ""
echo "Monitor:  squeue -u \$USER"
echo ""
echo "When complete, audit each country:"
echo "  python3 hpc/phase4/audit_phase4e_a_results.py \\"
echo "    --root hpc_results/herald_phase4e_a_nl_${TIMESTAMP}_r1 \\"
echo "    --phase4a-wmape 0.058184 --country nl"
echo ""
echo "Phase 4A reference WMAPEs:"
echo "  FR: 0.020398 (V6/V7, different pipeline — informational only)"
echo "  NL: 0.058184  BE: 0.070900  PT: 0.169900"
