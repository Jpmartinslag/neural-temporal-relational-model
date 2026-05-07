#!/bin/bash
# ============================================================
# HERALD — final model comparison battery
#
# Usage:
#   bash run_final_model_comparison.sh [classical|lstm|stgnn|herald|dashboard|all]
#
# Families kept separated under:
#   hpc_results/final_model_comparison_20260429/
#
# CONFIGURE:
#   PYTHON=/path/to/python-with-torch-and-statsmodels
#   EPOCHS=800
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SECTION=${1:-all}
SEEDS="0 1 7 13 42 99 123"
EPOCHS=${EPOCHS:-800}
OUT_ROOT=${OUT_ROOT:-hpc_results/final_model_comparison_20260429}

mkdir -p "$OUT_ROOT"/{reports,logs,data_processed,stgnn_reports,stgnn_data_processed}

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
  run "[CLASSICAL] naive_lag1 + arima_local" \
    src/data/train_temporal_baselines_v1.py \
    --models naive_lag1 arima_local \
    --seed 0 \
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
      --out-pred "$OUT_ROOT/stgnn_data_processed/dynamic_stgnn_model_predictions_seed_${seed}_v1.csv" \
      --out-json "$OUT_ROOT/stgnn_reports/dynamic_stgnn_model_metrics_seed_${seed}_v1.json" \
      --out-md "$OUT_ROOT/stgnn_reports/DYNAMIC_STGNN_MODEL_TRAINING_seed_${seed}_V1.md"
  done
}

run_herald() {
  bash run_herald_v3_v6_compare.sh all
  cp reports/herald_v3_metrics_v1.json "$OUT_ROOT/reports/herald_v3_metrics_v1.json"
  cp reports/herald_v6_metrics_v1.json "$OUT_ROOT/reports/herald_v6_metrics_v1.json" 2>/dev/null || true
  cp hpc_results/patch_robustness_20260429/reports/herald_v6_metrics_section_E_final_ablation.json "$OUT_ROOT/reports/herald_v6_metrics_section_E_final_ablation.json" 2>/dev/null || true
  cp hpc_results/patch_robustness_20260429/reports/sector_baselines_v1.csv "$OUT_ROOT/reports/sector_baselines_v1.csv" 2>/dev/null || true
  cp hpc_results/patch_robustness_20260429/reports/ridge_ar_official_v1.json "$OUT_ROOT/reports/ridge_ar_official_v1.json" 2>/dev/null || true
  cp data/processed/herald_v3_predictions_full_seed_*_v1.csv "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp data/processed/herald_v3_internals_full_seed_*_v1.npz "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp data/processed/herald_v6_predictions_total_full_final_gate2.0_seed_*_v1.csv "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp data/processed/herald_v6_predictions_sector_full_final_gate2.0_seed_*_v1.csv "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp data/processed/herald_v6_internals_full_final_gate2.0_seed_*_v1.npz "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp hpc_results/patch_robustness_20260429/section_E_final_ablation/data_processed/herald_v6_predictions_total_*_final_gate2.0_seed_*_v1.csv "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp hpc_results/patch_robustness_20260429/section_E_final_ablation/data_processed/herald_v6_predictions_sector_*_final_gate2.0_seed_*_v1.csv "$OUT_ROOT/data_processed/" 2>/dev/null || true
  cp hpc_results/patch_robustness_20260429/section_E_final_ablation/data_processed/herald_v6_internals_*_final_gate2.0_seed_*_v1.npz "$OUT_ROOT/data_processed/" 2>/dev/null || true
}

run_dashboard() {
  run "[DASHBOARD] HERALD comparison dashboard" \
    src/data/plot_herald_v3_v6_dashboard.py \
    --v3-json "$OUT_ROOT/reports/herald_v3_metrics_v1.json" \
    --v6-json "$OUT_ROOT/reports/herald_v6_metrics_section_E_final_ablation.json" \
    --v6-data-dir "$OUT_ROOT/data_processed" \
    --sector-csv "$OUT_ROOT/reports/sector_baselines_v1.csv" \
    --ridge-json "$OUT_ROOT/reports/ridge_ar_official_v1.json" \
    --stgnn-glob "$OUT_ROOT/stgnn_reports/dynamic_stgnn_model_metrics_seed_*_v1.json" \
    --temporal-json "$OUT_ROOT/temporal_baselines/reports/final_temporal_baselines_metrics_v1.json" \
    --out "$OUT_ROOT/reports/figures/final_model_comparison_dashboard_v1.html"
}

echo "============================================"
echo " HERALD Final Model Comparison Battery"
echo " Python : $PYTHON"
echo " Section: $SECTION"
echo " Seeds  : $SEEDS"
echo " Epochs : $EPOCHS"
echo " Out    : $OUT_ROOT"
echo "============================================"
check_env

case "$SECTION" in
  classical) run_classical ;;
  lstm) run_lstm ;;
  stgnn) run_stgnn ;;
  herald) run_herald ;;
  dashboard) run_dashboard ;;
  all) run_classical; run_lstm; run_stgnn; run_herald; run_dashboard ;;
  *)
    echo "Unknown section: $SECTION"
    echo "Use: classical | lstm | stgnn | herald | dashboard | all"
    exit 1
    ;;
esac

echo ""
echo "Results stored under: $OUT_ROOT"
