#!/bin/bash
# ============================================================
#  HERALD V6 — corrected dynamic graph training battery
#
#  CONFIGURE: set PYTHON to your Python with PyTorch + sklearn.
#
#  Usage:
#    bash run_herald_v6.sh        # all sections
#    bash run_herald_v6.sh A      # core ablations, 10 x 7 seeds
#    bash run_herald_v6.sh B      # hyperparameter grid, seed 0
#    bash run_herald_v6.sh C      # best config x 10 seeds, edit BEST_* first
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SCRIPT=src/data/train_herald_v6.py
EPOCHS=${EPOCHS:-800}
CORE_SEEDS="0 1 7 13 42 99 123"
BEST_SEEDS="0 1 3 7 13 17 42 77 99 123"
SECTION=${1:-all}

# Fill these after inspecting Section B.
BEST_HIDDEN=32
BEST_Q_HIDDEN=16
BEST_ATTN=8
BEST_SMOOTH=0.01
BEST_CONTRAST=0.0
BEST_TOPK=10
BEST_GATE_BIAS=2.0

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%H:%M:%S')"
  $PYTHON $SCRIPT "$@"
  echo "   done  $(date '+%H:%M:%S')"
}

check_environment() {
  $PYTHON - <<'PY'
import torch
print(" Torch     :", torch.__version__)
print(" CUDA      :", torch.cuda.is_available())
print(" Device    :", "cuda" if torch.cuda.is_available() else "cpu")
if torch.cuda.is_available():
    print(" GPU       :", torch.cuda.get_device_name(0))
PY
}

base_args() {
  echo --epochs "$EPOCHS" \
       --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
       --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
       --gate-bias-init 1.0 --gate-entropy-lambda 0.001 \
       --sector-lambda 0.1 --lr 0.001 --huber-delta 300
}

run_section_A() {
  local COUNT=0
  for ABLATION in full self_only fixed_geo_mob_only static_adaptive \
                  contrast_loss no_regime_in_graph regime_exclusive \
                  no_sector_head no_quarterly no_smooth_no_contrast; do
    for SEED in $CORE_SEEDS; do
      COUNT=$((COUNT + 1))
      run "[A-$COUNT/70] $ABLATION seed=$SEED" \
        --ablation "$ABLATION" --seed "$SEED" $(base_args)
    done
  done
}

run_section_B() {
  local COUNT=0

  for SMOOTH in 0.005 0.01 0.05; do
    for CONTRAST in 0.0 0.01 0.05; do
      COUNT=$((COUNT + 1))
      run "[B-$COUNT/17] smooth=$SMOOTH contrast=$CONTRAST seed=0" \
        --ablation full --seed 0 --epochs "$EPOCHS" \
        --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
        --top-k 10 --smooth-lambda "$SMOOTH" --contrast-lambda "$CONTRAST" \
        --gate-bias-init 1.0 --gate-entropy-lambda 0.001 \
        --sector-lambda 0.1 --lr 0.001 --huber-delta 300 \
        --run-tag "smooth${SMOOTH}_contrast${CONTRAST}"
    done
  done

  for HIDDEN in 32 64; do
    COUNT=$((COUNT + 1))
    if [ "$HIDDEN" = "64" ]; then QH=32; ATTN=16; else QH=16; ATTN=8; fi
    run "[B-$COUNT/17] hidden=$HIDDEN seed=0" \
      --ablation full --seed 0 --epochs "$EPOCHS" \
      --hidden-dim "$HIDDEN" --q-hidden "$QH" --attn-dim "$ATTN" \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-bias-init 1.0 --gate-entropy-lambda 0.001 \
      --sector-lambda 0.1 --lr 0.001 --huber-delta 300 \
      --run-tag "hidden${HIDDEN}"
  done

  for GATE_BIAS in 0.0 1.0 2.0; do
    COUNT=$((COUNT + 1))
    run "[B-$COUNT/17] gate_bias=$GATE_BIAS seed=0" \
      --ablation full --seed 0 --epochs "$EPOCHS" \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-bias-init "$GATE_BIAS" --gate-entropy-lambda 0.001 \
      --sector-lambda 0.1 --lr 0.001 --huber-delta 300 \
      --run-tag "gate${GATE_BIAS}"
  done

  for TOPK in 5 10 15; do
    COUNT=$((COUNT + 1))
    run "[B-$COUNT/17] top_k=$TOPK seed=0" \
      --ablation full --seed 0 --epochs "$EPOCHS" \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --top-k "$TOPK" --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-bias-init 1.0 --gate-entropy-lambda 0.001 \
      --sector-lambda 0.1 --lr 0.001 --huber-delta 300 \
      --run-tag "topk${TOPK}"
  done
}

run_section_C() {
  local COUNT=0
  for SEED in $BEST_SEEDS; do
    COUNT=$((COUNT + 1))
    run "[C-$COUNT/10] best_config seed=$SEED" \
      --ablation full --seed "$SEED" --epochs "$EPOCHS" \
      --hidden-dim "$BEST_HIDDEN" --q-hidden "$BEST_Q_HIDDEN" --attn-dim "$BEST_ATTN" \
      --top-k "$BEST_TOPK" --smooth-lambda "$BEST_SMOOTH" --contrast-lambda "$BEST_CONTRAST" \
      --gate-bias-init "$BEST_GATE_BIAS" --gate-entropy-lambda 0.001 \
      --sector-lambda 0.1 --lr 0.001 --huber-delta 300 \
      --run-tag best
  done
}

echo "============================================"
echo " HERALD V6 — Training Battery"
echo " Python    : $PYTHON"
echo " Section   : $SECTION"
echo " Epochs    : $EPOCHS"
echo " Core seeds: $CORE_SEEDS"
echo " Start     : $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
check_environment

case "$SECTION" in
  A)   run_section_A ;;
  B)   run_section_B ;;
  C)   run_section_C ;;
  all)
    run_section_A
    run_section_B
    run_section_C
    ;;
  *)
    echo "Unknown section: $SECTION"
    echo "Use: A | B | C | all"
    exit 1
    ;;
esac

echo ""
echo "============================================"
echo " Complete: $(date '+%Y-%m-%d %H:%M:%S')"
echo " Results : reports/herald_v6_metrics_v1.json"
echo "         : reports/HERALD_V6_MODEL_V1.md"
echo "============================================"
