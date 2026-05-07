#!/bin/bash
# Prospective HERALD forecast for 2026/2027.
# One array task = one seed. Outputs are forecast-only and isolated from WMAPE
# validation runs.

set -euo pipefail

PYTHON=${PYTHON:-python3}
SEED=${SEED:?SEED is required}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_forecast_$(date +%Y%m%d_%H%M%S)"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
FORECAST_HORIZON=${FORECAST_HORIZON:-2}

SIDE_A10_PATH=${SIDE_A10_PATH:-data/processed/side_creations_a10_ze2020_through_2025_v1.csv}
STRICT_DIR=${STRICT_DIR:-data/processed/strict_exante_20260506}

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

check_inputs() {
  require_file src/modeles/run_herald_prospective_forecast_v1.py
  require_file src/modeles/train_herald_v6.py
  require_file src/modeles/train_herald_v7.py
  require_file src/modeles/train_herald_semi_v2.py
  require_file "$SIDE_A10_PATH"
  require_file "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_lag_only_through_2025_v1.csv"
  require_file "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_no_source_flags_through_2025_v1.csv"
}

run_one() {
  local panel_key=$1
  local panel_path=$2
  local model=$3
  local label="${panel_key}_${model}"

  echo ""
  echo ">> [seed=${SEED}] forecast ${label}  $(date '+%Y-%m-%d %H:%M:%S')"
  "$PYTHON" src/modeles/run_herald_prospective_forecast_v1.py \
    --model "$model" \
    --panel-key "$panel_key" \
    --panel-path "$panel_path" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$OUT_ROOT/reports/per_run/forecast_${label}_seed_${SEED}.json" \
    --model-card-path "$OUT_ROOT/reports/per_run/FORECAST_${label}_seed_${SEED}.md" \
    --forecast-horizon "$FORECAST_HORIZON" \
    --seed "$SEED" \
    --epochs "$EPOCHS" \
    --hidden-dim 64 \
    --q-hidden 32 \
    --attn-dim 16 \
    --top-k 10 \
    --smooth-lambda 0.01 \
    --contrast-lambda 0.0 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --sector-lambda 0.1 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --rank-lambda 0.02 \
    --semi-warmup-epochs "$MASK_WARMUP" \
    --run-tag forecast_2026_2027
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

run_panel() {
  local panel_key=$1
  local panel_path=$2
  for model in semiv2_graph_ssl semiv2_graph_nossl v7_graph_only v7_ridge_only v6_full; do
    run_one "$panel_key" "$panel_path" "$model"
  done
}

echo "============================================================"
echo " HERALD prospective forecast 2026/2027"
echo " seed       : $SEED"
echo " out_root   : $OUT_ROOT"
echo " epochs     : $EPOCHS"
echo " warmup     : $MASK_WARMUP"
echo " horizon    : $FORECAST_HORIZON"
echo "============================================================"

check_inputs

run_panel "lag_only" "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_lag_only_through_2025_v1.csv"
run_panel "no_source_flags" "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_no_source_flags_through_2025_v1.csv"

echo ""
echo "DONE forecast seed=$SEED"
echo "results=$OUT_ROOT"
