#!/bin/bash
# Submit prospective HERALD 2026/2027 forecasts.

set -euo pipefail

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
MAX_PARALLEL=${MAX_PARALLEL:-10}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
FORECAST_HORIZON=${FORECAST_HORIZON:-2}
PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_forecast_${STAMP}"}
DEPENDENCY_JOB=${DEPENDENCY_JOB:-}

echo "Preflight syntax..."
bash -n hpc/forecast/run_herald_forecast_2026_2027_seed.sh
bash -n hpc/forecast/run_herald_forecast_2026_2027_array.sbatch
"$PYTHON" -m py_compile src/modeles/run_herald_prospective_forecast_v1.py
"$PYTHON" -m py_compile hpc/forecast/aggregate_herald_forecast_2026_2027.py

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
  --output="${OUT_ROOT}/logs/herald-forecast-%A_%a.out"
  --error="${OUT_ROOT}/logs/herald-forecast-%A_%a.err"
  --export=ALL,SEEDS="${SEEDS}",OUT_ROOT="${OUT_ROOT}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",FORECAST_HORIZON="${FORECAST_HORIZON}",PYTHON="${PYTHON}"
)

if [ -n "$DEPENDENCY_JOB" ]; then
  SBATCH_ARGS+=(--dependency=afterok:${DEPENDENCY_JOB})
fi

echo "Submitting prospective forecast..."
echo "  OUT_ROOT=${OUT_ROOT}"
echo "  DEPENDENCY_JOB=${DEPENDENCY_JOB:-none}"
echo "  SEEDS=${SEEDS}"
echo "  MAX_PARALLEL=${MAX_PARALLEL}"

sbatch "${SBATCH_ARGS[@]}" hpc/forecast/run_herald_forecast_2026_2027_array.sbatch

echo "Submit done."
