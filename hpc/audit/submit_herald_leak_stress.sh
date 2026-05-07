#!/bin/bash
# Submit target-shuffle leakage stress test.

set -euo pipefail

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
MAX_PARALLEL=${MAX_PARALLEL:-10}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_leak_stress_${STAMP}"}
STRICT_DIR=${STRICT_DIR:-data/processed/leak_stress_20260507}
SPLITS_PATH=${SPLITS_PATH:-$STRICT_DIR/dynamic_stgnn_walk_forward_splits_strict_2024_2025_v1.csv}
DEPENDENCY_JOB=${DEPENDENCY_JOB:-}

echo "Preparing target-shuffle leak stress inputs..."
"$PYTHON" hpc/audit/prepare_herald_leak_stress_inputs.py --out-dir "$STRICT_DIR"

echo "Preflight syntax..."
bash -n hpc/audit/run_herald_strict_exante_seed.sh
bash -n hpc/audit/run_herald_strict_exante_array.sbatch
"$PYTHON" -m py_compile hpc/audit/prepare_herald_leak_stress_inputs.py

N_SEEDS=$(wc -w <<< "$SEEDS")
if [ "$N_SEEDS" -ne 10 ]; then
  echo "Expected 10 seeds, got ${N_SEEDS}: ${SEEDS}" >&2
  exit 1
fi

if [ -e "$OUT_ROOT" ]; then
  echo "OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi
mkdir -p "$OUT_ROOT/logs"

SBATCH_ARGS=(
  --array=0-9%${MAX_PARALLEL}
  --output="${OUT_ROOT}/logs/herald-leak-stress-%A_%a.out"
  --error="${OUT_ROOT}/logs/herald-leak-stress-%A_%a.err"
  --export=ALL,SEEDS="${SEEDS}",OUT_ROOT="${OUT_ROOT}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",PYTHON="${PYTHON}",RUN_GLOBAL=0,STRICT_DIR="${STRICT_DIR}",SPLITS_PATH="${SPLITS_PATH}"
)

if [ -n "$DEPENDENCY_JOB" ]; then
  SBATCH_ARGS+=(--dependency=afterok:${DEPENDENCY_JOB})
fi

echo "Submitting target-shuffle leak stress battery..."
echo "  OUT_ROOT=${OUT_ROOT}"
echo "  STRICT_DIR=${STRICT_DIR}"
echo "  DEPENDENCY_JOB=${DEPENDENCY_JOB:-none}"
echo "  SEEDS=${SEEDS}"
echo "  MAX_PARALLEL=${MAX_PARALLEL}"

sbatch "${SBATCH_ARGS[@]}" hpc/audit/run_herald_strict_exante_array.sbatch

echo "Submit done."
