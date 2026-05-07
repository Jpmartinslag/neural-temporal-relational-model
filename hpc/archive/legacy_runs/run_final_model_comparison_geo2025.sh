#!/bin/bash
# ============================================================
# HERALD — final model comparison battery on SIDE geo2025 panel
#
# This reruns every model family on the same through_2025 artifacts:
#   data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
#   metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
#   data/processed/side_creations_a10_ze2020_through_2025_v1.csv
#
# Usage:
#   PYTHON=python3 bash run_final_model_comparison_geo2025.sh [classical|lstm|stgnn|herald|forecast|dashboard|all]
#
# Output root is isolated by default:
#   hpc_results/final_model_comparison_geo2025_YYYYMMDD_HHMMSS/
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SECTION=${1:-all}
SEEDS=${SEEDS:-"0 1 7 13 42 99 123"}
EPOCHS=${EPOCHS:-800}
RUN_TAG=${RUN_TAG:-final_geo2025_gate2.0}
OUT_ROOT=${OUT_ROOT:-"hpc_results/final_model_comparison_geo2025_$(date +%Y%m%d_%H%M%S)"}

PANEL_PATH=data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
SPLITS_PATH=metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
SIDE_A10_PATH=data/processed/side_creations_a10_ze2020_through_2025_v1.csv

mkdir -p "$OUT_ROOT"/{reports,logs,data_processed,stgnn_reports,stgnn_data_processed,temporal_baselines}

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%Y-%m-%d %H:%M:%S')"
  "$PYTHON" "$@"
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

check_env() {
  "$PYTHON" - <<'PY'
try:
    import torch
    print("Torch:", torch.__version__)
    print("CUDA :", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU  :", torch.cuda.get_device_name(0))
except Exception as exc:
    print("Torch unavailable:", type(exc).__name__, exc)
try:
    import statsmodels
    print("statsmodels:", statsmodels.__version__)
except Exception as exc:
    print("statsmodels unavailable:", type(exc).__name__, exc)
PY
}

run_classical() {
  run "[CLASSICAL] naive_lag1 + ridge_ar + arima_local" \
    src/data/train_temporal_baselines_v1.py \
    --models naive_lag1 ridge_ar arima_local \
    --seed 0 \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --out-dir "$OUT_ROOT/temporal_baselines"
}

run_lstm() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[LSTM-$count/7] lstm_local seed=$seed" \
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

run_stgnn() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[STGNN-$count/7] DCRNN + GraphWaveNet + DynamicSTGNN seed=$seed" \
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

run_herald() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[V3-$count/7] full geo2025 seed=$seed" \
      src/data/train_herald_v3.py \
      --ablation full --seed "$seed" --epochs "$EPOCHS" \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --prediction-output-dir "$OUT_ROOT/data_processed" \
      --metrics-path "$OUT_ROOT/reports/herald_v3_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_V3_MODEL_V1.md" \
      --history-output-dir "$OUT_ROOT/reports" \
      --run-tag final_geo2025
  done

  count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[V6-$count/7] full geo2025 gate=2.0 seed=$seed" \
      src/data/train_herald_v6.py \
      --ablation full --seed "$seed" --epochs "$EPOCHS" \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --side-a10-path "$SIDE_A10_PATH" \
      --prediction-output-dir "$OUT_ROOT/data_processed" \
      --metrics-path "$OUT_ROOT/reports/herald_v6_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_V6_MODEL_V1.md" \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
      --lr 0.001 --huber-delta 300 \
      --gate-bias-init 2.0 --run-tag "$RUN_TAG"
  done
}

run_forecast() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[FORECAST-$count/7] V6 prospective 2026-2027 seed=$seed" \
      src/data/train_herald_v6.py \
      --ablation full --seed "$seed" --epochs "$EPOCHS" \
      --forecast-horizon 2 --forecast-only \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --side-a10-path "$SIDE_A10_PATH" \
      --prediction-output-dir "$OUT_ROOT/data_processed" \
      --metrics-path "$OUT_ROOT/reports/herald_v6_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_V6_MODEL_V1.md" \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
      --lr 0.001 --huber-delta 300 \
      --gate-bias-init 2.0 --run-tag "${RUN_TAG}_forecast"
  done
}

run_dashboard() {
  run "[DASHBOARD] final comparison dashboard geo2025" \
    src/data/plot_herald_v3_v6_dashboard.py \
    --v3-json "$OUT_ROOT/reports/herald_v3_metrics_v1.json" \
    --v6-json "$OUT_ROOT/reports/herald_v6_metrics_v1.json" \
    --v6-ablation-json "$OUT_ROOT/reports/herald_v6_metrics_v1.json" \
    --v6-run-tag "$RUN_TAG" \
    --v6-data-dir "$OUT_ROOT/data_processed" \
    --stgnn-glob "$OUT_ROOT/stgnn_reports/dynamic_stgnn_model_metrics_seed_*_v1.json" \
    --temporal-json "$OUT_ROOT/temporal_baselines/reports/final_temporal_baselines_metrics_v1.json" \
    --out "$OUT_ROOT/reports/figures/final_model_comparison_geo2025_dashboard_v1.html"

  run "[DASHBOARD] HERALD 2025 observed dashboard geo2025" \
    src/data/plot_herald_v6_2025_dashboard.py \
    --hpc-path "$OUT_ROOT" \
    --forecast-data-dir "$OUT_ROOT/data_processed" \
    --out "$OUT_ROOT/reports/figures/herald_v6_observed2025_geo2025_dashboard_v1.html"
}

echo "============================================"
echo " HERALD Final Model Comparison Battery - geo2025"
echo " Python : $PYTHON"
echo " Section: $SECTION"
echo " Seeds  : $SEEDS"
echo " Epochs : $EPOCHS"
echo " Run tag: $RUN_TAG"
echo " Panel  : $PANEL_PATH"
echo " Splits : $SPLITS_PATH"
echo " Out    : $OUT_ROOT"
echo "============================================"
check_env

case "$SECTION" in
  classical) run_classical ;;
  lstm) run_lstm ;;
  stgnn) run_stgnn ;;
  herald) run_herald ;;
  forecast) run_forecast ;;
  dashboard) run_dashboard ;;
  all) run_classical; run_lstm; run_stgnn; run_herald; run_forecast; run_dashboard ;;
  *)
    echo "Unknown section: $SECTION"
    echo "Use: classical | lstm | stgnn | herald | forecast | dashboard | all"
    exit 1
    ;;
esac

echo ""
echo "Results stored under: $OUT_ROOT"
