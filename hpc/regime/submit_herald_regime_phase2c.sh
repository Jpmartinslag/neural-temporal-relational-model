#!/bin/bash
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase2c_critical_${STAMP}"}

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
REGIME_PLAN=${REGIME_PLAN:-phase2c_critical}
DEVICE=${DEVICE:-}

echo "Phase2C critical submit wrapper"
echo "OUT_ROOT=$OUT_ROOT"
echo "SEEDS=$SEEDS"
echo "REGIME_PLAN=$REGIME_PLAN"

OUT_ROOT="$OUT_ROOT" \
SEEDS="$SEEDS" \
EPOCHS="$EPOCHS" \
MASK_WARMUP="$MASK_WARMUP" \
MAX_PARALLEL="$MAX_PARALLEL" \
REGIME_PLAN="$REGIME_PLAN" \
DEVICE="$DEVICE" \
bash hpc/regime/submit_herald_regime_discovery.sh
