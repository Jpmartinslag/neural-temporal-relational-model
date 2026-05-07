#!/bin/bash
# Strict ex-ante leakage check for HERALD Semi V2 graph_only.
#
# One array task = one seed. The script runs a narrow set of controls on two
# strict panel variants without overwriting the main validation battery.

set -euo pipefail

PYTHON=${PYTHON:-python3}
SEED=${SEED:?SEED is required}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_strict_exante_$(date +%Y%m%d_%H%M%S)"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
RUN_GLOBAL=${RUN_GLOBAL:-0}

SIDE_A10_PATH=${SIDE_A10_PATH:-data/processed/side_creations_a10_ze2020_through_2025_v1.csv}
STRICT_DIR=${STRICT_DIR:-data/processed/strict_exante_20260506}
SPLITS_PATH=${SPLITS_PATH:-$STRICT_DIR/dynamic_stgnn_walk_forward_splits_strict_2024_2025_v1.csv}

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,temporal_baselines}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

check_inputs() {
  require_file hpc/audit/prepare_herald_strict_exante_inputs.py
  require_file src/modeles/train_temporal_baselines_v1.py
  require_file src/modeles/train_herald_v6.py
  require_file src/modeles/train_herald_v7.py
  require_file src/modeles/train_herald_semi_v2.py
  require_file "$SIDE_A10_PATH"
  require_file "$SPLITS_PATH"
  require_file "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_lag_only_through_2025_v1.csv"
  require_file "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_no_source_flags_through_2025_v1.csv"
}

run_cmd() {
  local label=$1
  shift
  echo ""
  echo ">> [seed=${SEED}] ${label}  $(date '+%Y-%m-%d %H:%M:%S')"
  "$PYTHON" "$@"
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

v6_common_args() {
  local panel=$1
  local mp=$2
  local mc=$3
  echo \
    --panel-path "$panel" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 \
    --smooth-lambda 0.01 \
    --contrast-lambda 0.0 \
    --gate-entropy-lambda 0.001 \
    --sector-lambda 0.1 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --hidden-dim 64 \
    --q-hidden 32 \
    --attn-dim 16 \
    --epochs "$EPOCHS"
}

v7_common_args() {
  local panel=$1
  local mp=$2
  local mc=$3
  echo \
    --panel-path "$panel" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --sector-lambda 0.1 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --hidden-dim 64 \
    --q-hidden 32 \
    --attn-dim 16 \
    --epochs "$EPOCHS"
}

semiv2_common_args() {
  local panel=$1
  local mp=$2
  local mc=$3
  echo \
    --panel-path "$panel" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --sector-lambda 0.1 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --hidden-dim 64 \
    --q-hidden 32 \
    --attn-dim 16 \
    --epochs "$EPOCHS" \
    --semi-warmup-epochs "$MASK_WARMUP"
}

run_panel() {
  local panel_key=$1
  local panel_path=$2
  local tag_prefix="strict_${panel_key}"

  if [ "$RUN_GLOBAL" = "1" ]; then
    run_cmd "${panel_key}: Ridge/naive/ARIMA 2024-2025" \
      src/modeles/train_temporal_baselines_v1.py \
      --models naive_lag1 ridge_ar arima_local \
      --seed 0 \
      --panel-path "$panel_path" \
      --splits-path "$SPLITS_PATH" \
      --out-dir "$OUT_ROOT/temporal_baselines/${panel_key}"
  fi

  run_cmd "${panel_key}: Semi V2 graph_only" \
    src/modeles/train_herald_semi_v2.py \
    $(semiv2_common_args "$panel_path" "$OUT_ROOT/reports/per_run/${tag_prefix}_semiv2_graph_only_seed_${SEED}.json" "$OUT_ROOT/reports/per_run/${tag_prefix}_semiv2_graph_only_seed_${SEED}.md") \
    --mode full \
    --v7-variant graph_only \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --rank-lambda 0.02 \
    --seed "$SEED" \
    --run-tag "${tag_prefix}_graph_only_f0.10_s0.30_r0.02"

  run_cmd "${panel_key}: Semi V2 no-SSL graph_only control" \
    src/modeles/train_herald_semi_v2.py \
    $(semiv2_common_args "$panel_path" "$OUT_ROOT/reports/per_run/${tag_prefix}_semiv2_graph_only_nossl_seed_${SEED}.json" "$OUT_ROOT/reports/per_run/${tag_prefix}_semiv2_graph_only_nossl_seed_${SEED}.md") \
    --mode full \
    --v7-variant graph_only \
    --feature-mask-ratio 0.00 \
    --sector-mask-ratio 0.00 \
    --rank-lambda 0.00 \
    --seed "$SEED" \
    --run-tag "${tag_prefix}_graph_only_nossl"

  run_cmd "${panel_key}: V7 graph_only" \
    src/modeles/train_herald_v7.py \
    $(v7_common_args "$panel_path" "$OUT_ROOT/reports/per_run/${tag_prefix}_v7_graph_only_seed_${SEED}.json" "$OUT_ROOT/reports/per_run/${tag_prefix}_v7_graph_only_seed_${SEED}.md") \
    --variant graph_only \
    --seed "$SEED" \
    --run-tag "${tag_prefix}_graph_only"

  run_cmd "${panel_key}: V7 ridge_only" \
    src/modeles/train_herald_v7.py \
    $(v7_common_args "$panel_path" "$OUT_ROOT/reports/per_run/${tag_prefix}_v7_ridge_only_seed_${SEED}.json" "$OUT_ROOT/reports/per_run/${tag_prefix}_v7_ridge_only_seed_${SEED}.md") \
    --variant ridge_only \
    --seed "$SEED" \
    --run-tag "${tag_prefix}_ridge_only"

  run_cmd "${panel_key}: V6 full" \
    src/modeles/train_herald_v6.py \
    $(v6_common_args "$panel_path" "$OUT_ROOT/reports/per_run/${tag_prefix}_v6_full_seed_${SEED}.json" "$OUT_ROOT/reports/per_run/${tag_prefix}_v6_full_seed_${SEED}.md") \
    --ablation full \
    --seed "$SEED" \
    --run-tag "${tag_prefix}_full_h64_gate2"

  run_cmd "${panel_key}: V6 self_only" \
    src/modeles/train_herald_v6.py \
    $(v6_common_args "$panel_path" "$OUT_ROOT/reports/per_run/${tag_prefix}_v6_self_only_seed_${SEED}.json" "$OUT_ROOT/reports/per_run/${tag_prefix}_v6_self_only_seed_${SEED}.md") \
    --ablation self_only \
    --seed "$SEED" \
    --run-tag "${tag_prefix}_self_only_h64_gate2"
}

echo "============================================================"
echo " HERALD strict ex-ante leakage check"
echo " seed       : $SEED"
echo " out_root   : $OUT_ROOT"
echo " epochs     : $EPOCHS"
echo " warmup     : $MASK_WARMUP"
echo " run_global : $RUN_GLOBAL"
echo " splits     : $SPLITS_PATH"
echo "============================================================"

check_inputs

run_panel "lag_only" "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_lag_only_through_2025_v1.csv"
run_panel "no_source_flags" "$STRICT_DIR/dynamic_stgnn_feature_panel_strict_no_source_flags_through_2025_v1.csv"

echo ""
echo "DONE strict seed=$SEED"
echo "results=$OUT_ROOT"
