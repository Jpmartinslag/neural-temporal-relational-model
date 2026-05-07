#!/bin/bash
# ============================================================
# HERALD — V3/V6 comparison battery
#
# Usage:
#   bash run_herald_v3_v6_compare.sh v3
#   bash run_herald_v3_v6_compare.sh v6
#   bash run_herald_v3_v6_compare.sh all
#
# Notes:
# - V3 has no run-tag support; it writes the standard V3 artifact names.
# - V6 uses the final robust config with run-tag final_gate2.0.
# - Use PYTHON=/path/to/python if python3 is not the torch environment.
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SECTION=${1:-all}
SEEDS="0 1 7 13 42 99 123"
EPOCHS=${EPOCHS:-800}

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%Y-%m-%d %H:%M:%S')"
  $PYTHON "$@"
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

check_env() {
  $PYTHON - <<'PY'
import torch
print("Torch:", torch.__version__)
print("CUDA :", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU  :", torch.cuda.get_device_name(0))
PY
}

run_v3() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[V3-$count/7] full seed=$seed" \
      src/data/train_herald_v3.py \
      --ablation full --seed "$seed" --epochs "$EPOCHS"
  done
}

run_v6() {
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    run "[V6-$count/7] full gate=2.0 seed=$seed" \
      src/data/train_herald_v6.py \
      --ablation full --seed "$seed" --epochs "$EPOCHS" \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
      --lr 0.001 --huber-delta 300 \
      --gate-bias-init 2.0 --run-tag final_gate2.0
  done
}

echo "============================================"
echo " HERALD V3/V6 Comparison Battery"
echo " Python : $PYTHON"
echo " Section: $SECTION"
echo " Seeds  : $SEEDS"
echo " Epochs : $EPOCHS"
echo "============================================"
check_env

case "$SECTION" in
  v3) run_v3 ;;
  v6) run_v6 ;;
  all) run_v3; run_v6 ;;
  *)
    echo "Unknown section: $SECTION"
    echo "Use: v3 | v6 | all"
    exit 1
    ;;
esac

echo ""
echo "Generate dashboard with:"
echo "  $PYTHON src/data/plot_herald_v3_v6_dashboard.py"
