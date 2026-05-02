#!/bin/bash
# ============================================================
# HERALD Semi Total Battery — geo2025 / through_2025
#
# Objetivo:
#   Comparar V3, V6 final, controle de capacidade h64 e variantes
#   semi-supervisionadas em uma única bateria isolada.
#
# Uso:
#   PYTHON=python3 EPOCHS=800 bash run_herald_semi_total_geo2025.sh all
#   PYTHON=python3 EPOCHS=5 SEEDS="0" bash run_herald_semi_total_geo2025.sh smoke
#
# Saídas:
#   hpc_results/herald_semi_total_geo2025_YYYYMMDD_HHMMSS/
#   Default:
#     HERALD/Semi: 21 configs x 10 seeds = 210 runs
#     Baselines: Ridge/Naive/ARIMA deterministic + LSTM/STGNN with 10 seeds
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SECTION=${1:-all}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
CLASSICAL_MODELS=${CLASSICAL_MODELS:-"naive_lag1 ridge_ar arima_local"}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_semi_total_geo2025_$(date +%Y%m%d_%H%M%S)"}

PANEL_PATH=data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
SPLITS_PATH=metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
SPLITS_PRECOVID=metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv
SIDE_A10_PATH=data/processed/side_creations_a10_ze2020_through_2025_v1.csv

mkdir -p "$OUT_ROOT"/{reports,data_processed,logs,temporal_baselines,stgnn_reports,stgnn_data_processed}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1"
    exit 1
  fi
}

check_inputs() {
  require_file "$PANEL_PATH"
  require_file "$SPLITS_PATH"
  require_file "$SPLITS_PRECOVID"
  require_file "$SIDE_A10_PATH"
  "$PYTHON" - <<'PY'
try:
    import torch
    print("Torch:", torch.__version__)
    print("CUDA :", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU  :", torch.cuda.get_device_name(0))
except Exception as exc:
    raise SystemExit(f"PyTorch check failed: {type(exc).__name__}: {exc}")
PY
}

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%Y-%m-%d %H:%M:%S')"
  "$PYTHON" "$@"
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

run_classical_baselines() {
  run "[BASELINES classical] $CLASSICAL_MODELS" \
    src/data/train_temporal_baselines_v1.py \
    --models $CLASSICAL_MODELS \
    --seed 0 \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --out-dir "$OUT_ROOT/temporal_baselines"
}

run_lstm_baseline() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[BASELINES LSTM $count] seed=$seed" \
      src/data/train_temporal_baselines_v1.py \
      --models lstm_local \
      --seed "$seed" \
      --epochs "$EPOCHS" \
      --hidden-dim 32 \
      --lr 0.001 \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --out-dir "$OUT_ROOT/temporal_baselines"
  done
}

run_stgnn_baselines() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[BASELINES STGNN $count] DCRNN + GraphWaveNet + DynamicSTGNN seed=$seed" \
      src/data/train_dynamic_stgnn_models_v1.py \
      --models dcrnn_residual graph_wavenet_residual dynamic_stgnn_residual \
      --seed "$seed" \
      --epochs "$EPOCHS" \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --out-pred "$OUT_ROOT/stgnn_data_processed/dynamic_stgnn_model_predictions_seed_${seed}_v1.csv" \
      --out-json "$OUT_ROOT/stgnn_reports/dynamic_stgnn_model_metrics_seed_${seed}_v1.json" \
      --out-md "$OUT_ROOT/stgnn_reports/DYNAMIC_STGNN_MODEL_TRAINING_seed_${seed}_V1.md"
  done
}

run_baselines() {
  run_classical_baselines
  run_lstm_baseline
  run_stgnn_baselines
}

v6_common_args() {
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
    --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
    --ablation full --epochs "$EPOCHS"
}

semi_common_args() {
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$OUT_ROOT/reports/herald_semi_total_metrics_v1.json" \
    --model-card-path "$OUT_ROOT/reports/HERALD_SEMI_TOTAL_MODEL_V1.md" \
    --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
    --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
    --ablation full --epochs "$EPOCHS" \
    --mask-warmup-epochs "$MASK_WARMUP"
}

run_v3_full() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[01 V3 full $count/10] seed=$seed" \
      src/data/train_herald_v3.py \
      --ablation full --seed "$seed" --epochs "$EPOCHS" \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --prediction-output-dir "$OUT_ROOT/data_processed" \
      --metrics-path "$OUT_ROOT/reports/herald_v3_total_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_V3_TOTAL_MODEL_V1.md" \
      --history-output-dir "$OUT_ROOT/reports" \
      --run-tag total_geo2025
  done
}

run_v6_h32_no_semi() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[02 V6 h32 no semi $count/10] seed=$seed" \
      src/data/train_herald_v6.py \
      $(v6_common_args) \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --metrics-path "$OUT_ROOT/reports/herald_v6_total_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_V6_TOTAL_MODEL_V1.md" \
      --seed "$seed" --run-tag total_h32_no_semi
  done
}

run_v6_h64_no_semi() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[03 V6 h64 no semi $count/10] seed=$seed" \
      src/data/train_herald_v6.py \
      $(v6_common_args) \
      --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
      --metrics-path "$OUT_ROOT/reports/herald_v6_total_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_V6_TOTAL_MODEL_V1.md" \
      --seed "$seed" --run-tag total_h64_no_semi
  done
}

run_semi_config() {
  local label=$1
  local tag=$2
  local hidden=$3
  local q_hidden=$4
  local attn=$5
  local ratio=$6
  local strategy=$7
  local semi_lambda=$8
  local semi_target=$9
  local splits=${10:-$SPLITS_PATH}
  local metrics=${11:-$OUT_ROOT/reports/herald_semi_total_metrics_v1.json}
  local card=${12:-$OUT_ROOT/reports/HERALD_SEMI_TOTAL_MODEL_V1.md}

  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[$label $count] seed=$seed" \
      src/data/train_herald_semi_v1.py \
      $(semi_common_args) \
      --splits-path "$splits" \
      --metrics-path "$metrics" \
      --model-card-path "$card" \
      --hidden-dim "$hidden" --q-hidden "$q_hidden" --attn-dim "$attn" \
      --mask-ratio "$ratio" --mask-strategy "$strategy" \
      --semi-lambda "$semi_lambda" --semi-target "$semi_target" \
      --seed "$seed" --run-tag "$tag"
  done
}

run_semi_all() {
  run_semi_config "04 semi h32 mask0.10 random" \
    total_h32_semi_mask0.10_random 32 16 8 0.10 random 0.0 total

  run_semi_config "05 semi h64 mask0.0 control" \
    total_h64_semi_mask0.0_control 64 32 16 0.0 random 0.0 total
  run_semi_config "06 semi h64 mask0.05 random" \
    total_h64_semi_mask0.05_random 64 32 16 0.05 random 0.0 total
  run_semi_config "07 semi h64 mask0.10 random" \
    total_h64_semi_mask0.10_random 64 32 16 0.10 random 0.0 total
  run_semi_config "08 semi h64 mask0.15 random" \
    total_h64_semi_mask0.15_random 64 32 16 0.15 random 0.0 total
  run_semi_config "09 semi h64 mask0.20 random" \
    total_h64_semi_mask0.20_random 64 32 16 0.20 random 0.0 total
  run_semi_config "10 semi h64 mask0.30 random" \
    total_h64_semi_mask0.30_random 64 32 16 0.30 random 0.0 total

  run_semi_config "11 semi h64 mask0.10 block" \
    total_h64_semi_mask0.10_block 64 32 16 0.10 block 0.0 total
  run_semi_config "12 semi h64 mask0.20 block" \
    total_h64_semi_mask0.20_block 64 32 16 0.20 block 0.0 total
  run_semi_config "13 semi h64 mask0.10 spatial_block" \
    total_h64_semi_mask0.10_spatial_block 64 32 16 0.10 spatial_block 0.0 total
  run_semi_config "14 semi h64 mask0.20 spatial_block" \
    total_h64_semi_mask0.20_spatial_block 64 32 16 0.20 spatial_block 0.0 total

  run_semi_config "15 semi h64 lambda0.01 total" \
    total_h64_semi_mask0.10_random_lam0.01_total 64 32 16 0.10 random 0.01 total
  run_semi_config "16 semi h64 lambda0.05 total" \
    total_h64_semi_mask0.10_random_lam0.05_total 64 32 16 0.10 random 0.05 total
  run_semi_config "17 semi h64 lambda0.10 total" \
    total_h64_semi_mask0.10_random_lam0.10_total 64 32 16 0.10 random 0.10 total

  run_semi_config "18 semi h64 lambda0.05 A10" \
    total_h64_semi_mask0.10_random_lam0.05_a10 64 32 16 0.10 random 0.05 a10
  run_semi_config "19 semi h64 lambda0.05 total+A10" \
    total_h64_semi_mask0.10_random_lam0.05_total_a10 64 32 16 0.10 random 0.05 total_a10

  local old_warmup=$MASK_WARMUP
  MASK_WARMUP=0
  run_semi_config "20 semi h64 mask0.10 warmup0" \
    total_h64_semi_mask0.10_random_warmup0 64 32 16 0.10 random 0.0 total "$SPLITS_PATH"

  MASK_WARMUP=100
  run_semi_config "21 semi h64 mask0.10 precovid" \
    total_h64_semi_mask0.10_precovid 64 32 16 0.10 random 0.0 total \
    "$SPLITS_PRECOVID" \
    "$OUT_ROOT/reports/herald_semi_total_precovid_metrics_v1.json" \
    "$OUT_ROOT/reports/HERALD_SEMI_TOTAL_PRECOVID_MODEL_V1.md"
  MASK_WARMUP=$old_warmup
}

run_smoke() {
  local old_epochs=$EPOCHS
  local old_seeds=$SEEDS
  EPOCHS=5
  SEEDS="0"
  CLASSICAL_MODELS="naive_lag1 ridge_ar"
  run_classical_baselines
  run_v6_h32_no_semi
  run_semi_config "SMOKE semi h64 mask0.10 random" \
    smoke_h64_semi_mask0.10_random 64 32 16 0.10 random 0.0 total
  EPOCHS=$old_epochs
  SEEDS=$old_seeds
}

echo "============================================================"
echo " HERALD Semi Total Battery - geo2025"
echo " Python      : $PYTHON"
echo " Section     : $SECTION"
echo " Epochs      : $EPOCHS"
echo " Seeds       : $SEEDS"
echo " Mask warmup : $MASK_WARMUP"
echo " Out         : $OUT_ROOT"
echo " Panel       : $PANEL_PATH"
echo " Splits      : $SPLITS_PATH"
echo "============================================================"

check_inputs

case "$SECTION" in
  baselines) run_baselines ;;
  v3)        run_v3_full ;;
  v6)        run_v6_h32_no_semi; run_v6_h64_no_semi ;;
  semi)      run_semi_all ;;
  smoke)     run_smoke ;;
  all)       run_baselines; run_v3_full; run_v6_h32_no_semi; run_v6_h64_no_semi; run_semi_all ;;
  *)
    echo "Uso: baselines | v3 | v6 | semi | smoke | all"
    exit 1
    ;;
esac

echo ""
echo "Resultados em: $OUT_ROOT"
echo "Métricas:"
echo "  $OUT_ROOT/reports/herald_v3_total_metrics_v1.json"
echo "  $OUT_ROOT/reports/herald_v6_total_metrics_v1.json"
echo "  $OUT_ROOT/reports/herald_semi_total_metrics_v1.json"
echo "  $OUT_ROOT/reports/herald_semi_total_precovid_metrics_v1.json"
