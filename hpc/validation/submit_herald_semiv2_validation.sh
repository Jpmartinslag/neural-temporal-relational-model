#!/bin/bash
# Prepare and submit the HERALD Semi V2 validation battery.
#
# Usage on the HPC project root:
#   bash hpc/validation/submit_herald_semiv2_validation.sh
#
# Optional:
#   SEEDS="0 1 7 13 17 42 77 99 123 2025" MAX_PARALLEL=10 EPOCHS=800 \
#     bash hpc/validation/submit_herald_semiv2_validation.sh

set -euo pipefail

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
MAX_PARALLEL=${MAX_PARALLEL:-10}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_semiv2_validation_$(date +%Y%m%d_%H%M%S)"}

mkdir -p "$OUT_ROOT" logs

python3 hpc/validation/audit_herald_semiv2_validation_plan.py \
  --root "$OUT_ROOT" \
  --seeds "$SEEDS" \
  --mode expected

N=$(wc -w <<< "$SEEDS" | tr -d ' ')
if [ "$N" -lt 1 ]; then
  echo "No seeds provided." >&2
  exit 1
fi
LAST=$((N - 1))

echo ""
echo "Submitting HERALD Semi V2 validation"
echo "  seeds       : $SEEDS"
echo "  n_tasks     : $N"
echo "  max_parallel: $MAX_PARALLEL"
echo "  epochs      : $EPOCHS"
echo "  warmup      : $MASK_WARMUP"
echo "  out_root    : $OUT_ROOT"
echo ""

sbatch --array=0-${LAST}%${MAX_PARALLEL} \
  --export=ALL,SEEDS="$SEEDS",OUT_ROOT="$OUT_ROOT",EPOCHS="$EPOCHS",MASK_WARMUP="$MASK_WARMUP" \
  hpc/validation/run_herald_semiv2_validation_array.sbatch

echo ""
echo "After completion:"
echo "  python3 hpc/validation/audit_herald_semiv2_validation_plan.py --root '$OUT_ROOT' --seeds '$SEEDS' --mode results"
echo "  python3 hpc/research/aggregate_v7_metrics.py --root '$OUT_ROOT'"
echo "  python3 src/visualisation/generate_herald_semi_v2_dashboard.py --run-root '$OUT_ROOT' --out '$OUT_ROOT/reports/figures/herald_semi_v2_dashboard.html'"
