#!/bin/bash
# ============================================================
#  HERALD V6 - observed 2025 validation panel
#
#  Uses additive through_2025 artifacts and writes all outputs to
#  an isolated output root so the older V6 runs are not overwritten.
#
#  Usage:
#    PYTHON=python3 bash run_herald_v6_2025_observed.sh
#    PYTHON=python3 bash run_herald_v6_2025_observed.sh full
#    PYTHON=python3 bash run_herald_v6_2025_observed.sh ablations
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SCRIPT=src/data/train_herald_v6.py
EPOCHS=${EPOCHS:-800}
SEEDS=${SEEDS:-"0 1 7 13 42 99 123"}
SECTION=${1:-full}
RUN_TAG=${RUN_TAG:-observed2025_gate2}
OUTPUT_ROOT=${OUTPUT_ROOT:-"hpc_results/herald_v6_observed2025_$(date +%Y%m%d_%H%M%S)"}

PANEL_PATH=data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
SPLITS_PATH=metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
SIDE_A10_PATH=data/processed/side_creations_a10_ze2020_through_2025_v1.csv

mkdir -p "$OUTPUT_ROOT/data_processed" "$OUTPUT_ROOT/reports" "$OUTPUT_ROOT/logs"

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%H:%M:%S')"
  $PYTHON "$SCRIPT" "$@"
  echo "   done  $(date '+%H:%M:%S')"
}

check_env() {
  $PYTHON - <<'PY'
import torch
print(" Torch:", torch.__version__)
print(" CUDA :", torch.cuda.is_available())
if torch.cuda.is_available():
    print(" GPU  :", torch.cuda.get_device_name(0))
PY
}

base_args() {
  echo --epochs "$EPOCHS" \
       --panel-path "$PANEL_PATH" \
       --splits-path "$SPLITS_PATH" \
       --side-a10-path "$SIDE_A10_PATH" \
       --prediction-output-dir "$OUTPUT_ROOT/data_processed" \
       --metrics-path "$OUTPUT_ROOT/reports/herald_v6_observed2025_metrics_v1.json" \
       --model-card-path "$OUTPUT_ROOT/reports/HERALD_V6_OBSERVED2025_MODEL_V1.md" \
       --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
       --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
       --gate-bias-init 2.0 --gate-entropy-lambda 0.001 \
       --sector-lambda 0.1 --lr 0.001 --huber-delta 300 \
       --run-tag "$RUN_TAG"
}

run_full() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[full-$count/7] seed=$seed" \
      --ablation full --seed "$seed" $(base_args)
  done
}

run_ablations() {
  local count=0
  local ablations="full self_only fixed_geo_mob_only static_adaptive no_regime_in_graph no_quarterly no_sector_head"
  local total=$((7 * 7))
  for ablation in $ablations; do
    for seed in $SEEDS; do
      count=$((count + 1))
      run "[ablations-$count/$total] $ablation seed=$seed" \
        --ablation "$ablation" --seed "$seed" $(base_args)
    done
  done
}

echo "============================================"
echo " HERALD V6 - observed 2025"
echo " Python     : $PYTHON"
echo " Section    : $SECTION"
echo " Epochs     : $EPOCHS"
echo " Seeds      : $SEEDS"
echo " Run tag    : $RUN_TAG"
echo " Output root: $OUTPUT_ROOT"
echo " Start      : $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
check_env

case "$SECTION" in
  full) run_full ;;
  ablations) run_ablations ;;
  *)
    echo "Unknown section: $SECTION"
    echo "Use: full | ablations"
    exit 1
    ;;
esac

echo ""
echo "============================================"
echo " Complete: $(date '+%Y-%m-%d %H:%M:%S')"
echo " Results : $OUTPUT_ROOT"
echo "============================================"
