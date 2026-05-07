#!/bin/bash
# ============================================================
# HERALD Semi V2 validation battery - one seed, sequential.
#
# This script is designed for SLURM arrays:
#   one array task = one seed = all configs for that seed in sequence.
#
# That gives seed-paired comparisons while allowing up to N seeds/GPU tasks
# to run in parallel with --array=0-9%10.
# ============================================================

set -euo pipefail

PYTHON=${PYTHON:-python3}
SEED=${SEED:?SEED is required}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_semiv2_validation_$(date +%Y%m%d_%H%M%S)"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
RUN_GLOBAL=${RUN_GLOBAL:-0}

RUN_TEMPORAL=${RUN_TEMPORAL:-1}
RUN_STGNN=${RUN_STGNN:-1}
RUN_V6=${RUN_V6:-1}
RUN_V7=${RUN_V7:-1}
RUN_SEMIV2=${RUN_SEMIV2:-1}

PANEL_PATH=${PANEL_PATH:-data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv}
SPLITS_PATH=${SPLITS_PATH:-metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv}
SIDE_A10_PATH=${SIDE_A10_PATH:-data/processed/side_creations_a10_ze2020_through_2025_v1.csv}

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,temporal_baselines,stgnn_reports,stgnn_data_processed}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

check_inputs() {
  require_file "$PANEL_PATH"
  require_file "$SPLITS_PATH"
  require_file "$SIDE_A10_PATH"
  require_file src/modeles/train_temporal_baselines_v1.py
  require_file src/modeles/train_dynamic_stgnn_models_v1.py
  require_file src/modeles/sector_baselines_v1.py
  require_file src/modeles/train_herald_v6.py
  require_file src/modeles/train_herald_v7.py
  require_file src/modeles/train_herald_semi_v2.py
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
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
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
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
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
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
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

run_global_once() {
  if [ "$RUN_GLOBAL" != "1" ]; then
    return 0
  fi

  run_cmd "classical baselines: naive + ridge + arima" \
    src/modeles/train_temporal_baselines_v1.py \
    --models naive_lag1 ridge_ar arima_local \
    --seed 0 \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --out-dir "$OUT_ROOT/temporal_baselines"

  run_cmd "sector baselines: lag1 + historical means" \
    src/modeles/sector_baselines_v1.py \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --metrics-path "$OUT_ROOT/reports/per_run/sector_baselines_seed_0.json" \
    --predictions-out "$OUT_ROOT/data_processed/sector_baselines_predictions_v1.csv"
}

run_temporal_seed() {
  if [ "$RUN_TEMPORAL" != "1" ]; then return 0; fi
  run_cmd "LSTM local baseline" \
    src/modeles/train_temporal_baselines_v1.py \
    --models lstm_local \
    --seed "$SEED" \
    --epochs "$EPOCHS" \
    --hidden-dim 32 \
    --lr 0.001 \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --out-dir "$OUT_ROOT/temporal_baselines"
}

run_stgnn_seed() {
  if [ "$RUN_STGNN" != "1" ]; then return 0; fi
  run_cmd "STGNN baselines: DCRNN + Graph WaveNet + Dynamic STGNN" \
    src/modeles/train_dynamic_stgnn_models_v1.py \
    --models dcrnn_residual graph_wavenet_residual dynamic_stgnn_residual \
    --seed "$SEED" \
    --epochs "$EPOCHS" \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --out-pred "$OUT_ROOT/stgnn_data_processed/dynamic_stgnn_model_predictions_seed_${SEED}_v1.csv" \
    --out-json "$OUT_ROOT/stgnn_reports/dynamic_stgnn_model_metrics_seed_${SEED}_v1.json" \
    --out-md "$OUT_ROOT/stgnn_reports/DYNAMIC_STGNN_MODEL_TRAINING_seed_${SEED}_V1.md"
}

run_v6_config() {
  local ablation=$1
  local tag=$2
  local mp="$OUT_ROOT/reports/per_run/v6ctrl_${tag}_seed_${SEED}.json"
  local mc="$OUT_ROOT/reports/per_run/v6ctrl_${tag}_seed_${SEED}.md"
  run_cmd "V6 h64 ${ablation}" \
    src/modeles/train_herald_v6.py \
    $(v6_common_args "$mp" "$mc") \
    --ablation "$ablation" \
    --seed "$SEED" \
    --run-tag "$tag"
}

run_v6_seed() {
  if [ "$RUN_V6" != "1" ]; then return 0; fi
  run_v6_config full full_h64_gate2
  run_v6_config self_only self_only_h64_gate2
  run_v6_config fixed_geo_mob_only fixed_geo_mob_h64_gate2
  run_v6_config static_adaptive static_adaptive_h64_gate2
  run_v6_config no_regime_in_graph no_regime_graph_h64_gate2
  run_v6_config no_sector_head no_sector_head_h64_gate2
  run_v6_config no_quarterly no_quarterly_h64_gate2
}

run_v7_config() {
  local variant=$1
  local tag=$2
  local mp="$OUT_ROOT/reports/per_run/v7_${tag}_seed_${SEED}.json"
  local mc="$OUT_ROOT/reports/per_run/v7_${tag}_seed_${SEED}.md"
  run_cmd "V7 ${variant}" \
    src/modeles/train_herald_v7.py \
    $(v7_common_args "$mp" "$mc") \
    --variant "$variant" \
    --seed "$SEED" \
    --run-tag "$tag"
}

run_v7_seed() {
  if [ "$RUN_V7" != "1" ]; then return 0; fi
  run_v7_config full full
  run_v7_config fixed_alpha_0.5 fixed_alpha_0.5
  run_v7_config fixed_graph fixed_graph
  run_v7_config ridge_only ridge_only
  run_v7_config graph_only graph_only
  run_v7_config sector_enhanced sector_enhanced
  run_v7_config sector_lag1_only sector_lag1_only
}

run_semiv2_config() {
  local label=$1
  local tag=$2
  local mode=$3
  local feature_mask=$4
  local sector_mask=$5
  local rank_lambda=$6
  local v7_variant=${7:-full}
  local mp="$OUT_ROOT/reports/per_run/semiv2_${tag}_seed_${SEED}.json"
  local mc="$OUT_ROOT/reports/per_run/semiv2_${tag}_seed_${SEED}.md"
  run_cmd "Semi V2 ${label}" \
    src/modeles/train_herald_semi_v2.py \
    $(semiv2_common_args "$mp" "$mc") \
    --mode "$mode" \
    --v7-variant "$v7_variant" \
    --feature-mask-ratio "$feature_mask" \
    --sector-mask-ratio "$sector_mask" \
    --rank-lambda "$rank_lambda" \
    --seed "$SEED" \
    --run-tag "$tag"
}

run_semiv2_seed() {
  if [ "$RUN_SEMIV2" != "1" ]; then return 0; fi
  run_semiv2_config "full winner f0.10 s0.30 rank0.02" full_f0.10_s0.30_r0.02 full 0.10 0.30 0.02
  run_semiv2_config "masked variables only" masked_variables_f0.10 masked_variables 0.10 0.00 0.00
  run_semiv2_config "sector denoise only" sector_denoise_s0.30 sector_denoise 0.00 0.30 0.00
  run_semiv2_config "ranking only" ranking_aux_r0.02 ranking_aux 0.00 0.00 0.02
  run_semiv2_config "temporal regime only" temporal_regime temporal_regime 0.00 0.00 0.00
  run_semiv2_config "full without feature mask" full_f0.00_s0.30_r0.02 full 0.00 0.30 0.02
  run_semiv2_config "full without sector denoise" full_f0.10_s0.00_r0.02 full 0.10 0.00 0.02
  run_semiv2_config "full without ranking" full_f0.10_s0.30_r0.00 full 0.10 0.30 0.00
  run_semiv2_config "full no SSL controls" full_f0.00_s0.00_r0.00 full 0.00 0.00 0.00
  run_semiv2_config "full with fixed graph backbone" full_fixed_graph_f0.10_s0.30_r0.02 full 0.10 0.30 0.02 fixed_graph
  run_semiv2_config "full with graph-only backbone" full_graph_only_f0.10_s0.30_r0.02 full 0.10 0.30 0.02 graph_only
  run_semiv2_config "full with ridge-only backbone" full_ridge_only_f0.10_s0.30_r0.02 full 0.10 0.30 0.02 ridge_only
}

echo "============================================================"
echo " HERALD Semi V2 validation seed battery"
echo " seed       : $SEED"
echo " out_root   : $OUT_ROOT"
echo " epochs     : $EPOCHS"
echo " warmup     : $MASK_WARMUP"
echo " run_global : $RUN_GLOBAL"
echo " blocks     : temporal=$RUN_TEMPORAL stgnn=$RUN_STGNN v6=$RUN_V6 v7=$RUN_V7 semiv2=$RUN_SEMIV2"
echo " panel      : $PANEL_PATH"
echo " splits     : $SPLITS_PATH"
echo "============================================================"

check_inputs

run_global_once
run_temporal_seed
run_stgnn_seed
run_v6_seed
run_v7_seed
run_semiv2_seed

echo ""
echo "DONE seed=$SEED"
echo "results=$OUT_ROOT"
