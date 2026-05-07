#!/bin/bash
# Submit the strict ex-ante leakage check on the Mésocentre.

set -euo pipefail

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
MAX_PARALLEL=${MAX_PARALLEL:-10}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_strict_exante_${STAMP}"}

echo "Preparing strict ex-ante inputs..."
"$PYTHON" hpc/audit/prepare_herald_strict_exante_inputs.py

echo "Preflight syntax..."
bash -n hpc/audit/run_herald_strict_exante_seed.sh
bash -n hpc/audit/run_herald_strict_exante_array.sbatch

N_SEEDS=$(wc -w <<< "$SEEDS")
if [ "$N_SEEDS" -ne 10 ]; then
  echo "Expected 10 seeds, got ${N_SEEDS}: ${SEEDS}" >&2
  exit 1
fi

mkdir -p "$OUT_ROOT/logs"

echo "Submitting strict ex-ante battery..."
echo "  OUT_ROOT=${OUT_ROOT}"
echo "  SEEDS=${SEEDS}"
echo "  MAX_PARALLEL=${MAX_PARALLEL}"

sbatch \
  --array=0-9%${MAX_PARALLEL} \
  --output="${OUT_ROOT}/logs/herald-strict-exante-%A_%a.out" \
  --error="${OUT_ROOT}/logs/herald-strict-exante-%A_%a.err" \
  --export=ALL,SEEDS="${SEEDS}",OUT_ROOT="${OUT_ROOT}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",PYTHON="${PYTHON}",RUN_GLOBAL=0 \
  hpc/audit/run_herald_strict_exante_array.sbatch

echo "Submit done."
