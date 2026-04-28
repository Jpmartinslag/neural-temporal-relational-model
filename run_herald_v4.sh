#!/bin/bash
# HERALD V4 — Complete training battery
#
# Sections:
#   A. Core ablations      (8 ablations × 3 seeds = 24 runs)  — paper main table
#   B. Sensitivity smooth  (2 variants × 1 seed  =  2 runs)  — smooth-lambda sensitivity
#   C. Sensitivity top-k   (2 variants × 1 seed  =  2 runs)  — top-k sensitivity
#   D. Sensitivity hidden  (2 variants × 1 seed  =  2 runs)  — capacity sensitivity
#
# Total: 30 runs
#
# Usage: bash run_herald_v4.sh [section]
#   section: A | B | C | D | all (default: all)

set -e

PYTHON=/home/jpdark/miniconda3/envs/mineru/bin/python3
SCRIPT=src/data/train_herald_v4.py

EPOCHS=800
SEEDS="0 7 42"
SECTION=${1:-all}

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%H:%M:%S')"
  $PYTHON $SCRIPT "$@"
  echo "   done  $(date '+%H:%M:%S')"
}

# ─── A. Core ablations ─────────────────────────────────────────────────────────
# Each ablation × 3 seeds — goes into the paper main ablation table.
#
# Ablation               | What it tests
# ---------------------- | ------------------------------------------
# full                   | Complete V4
# self_only              | No message passing — pure temporal
# fixed_geo_mob_only     | Fixed geo+mob graph — no learned adj
# static_adaptive        | Learned static adj — no temporal dynamics
# no_sector_gate         | Scalar gate (V3-like) — no sector specificity
# no_quarterly           | No URSSAF quarterly — quarterly contribution
# no_regime              | regime_t = 0 — regime conditioning contribution
# no_smooth              | smooth_lambda = 0 — temporal smoothness contribution

run_section_A() {
  local COUNT=0
  for ABLATION in full self_only fixed_geo_mob_only static_adaptive \
                  no_sector_gate no_quarterly no_regime no_smooth; do
    for SEED in $SEEDS; do
      COUNT=$((COUNT + 1))
      run "[A-$COUNT/24] $ABLATION seed=$SEED" \
        --ablation "$ABLATION" --seed "$SEED" \
        --epochs $EPOCHS \
        --hidden-dim 32 --sector-hidden 16 --q-hidden 16 --attn-dim 8 \
        --top-k 10 --smooth-lambda 0.1 \
        --lr 0.001 --huber-delta 300
    done
  done
}

# ─── B. Sensitivity — smooth-lambda ───────────────────────────────────────────
# Tests whether WMAPE is stable across smooth-lambda values.
# Runs full ablation, seed 0 only, with --run-tag to avoid overwriting.

run_section_B() {
  run "[B-1/2] full smooth=0.01 seed=0" \
    --ablation full --seed 0 \
    --epochs $EPOCHS \
    --hidden-dim 32 --sector-hidden 16 --q-hidden 16 --attn-dim 8 \
    --top-k 10 --smooth-lambda 0.01 \
    --lr 0.001 --huber-delta 300 \
    --run-tag smooth001

  run "[B-2/2] full smooth=0.5 seed=0" \
    --ablation full --seed 0 \
    --epochs $EPOCHS \
    --hidden-dim 32 --sector-hidden 16 --q-hidden 16 --attn-dim 8 \
    --top-k 10 --smooth-lambda 0.5 \
    --lr 0.001 --huber-delta 300 \
    --run-tag smooth05
}

# ─── C. Sensitivity — top-k ───────────────────────────────────────────────────
# Tests whether graph sparsity level matters.

run_section_C() {
  run "[C-1/2] full top-k=5 seed=0" \
    --ablation full --seed 0 \
    --epochs $EPOCHS \
    --hidden-dim 32 --sector-hidden 16 --q-hidden 16 --attn-dim 8 \
    --top-k 5 --smooth-lambda 0.1 \
    --lr 0.001 --huber-delta 300 \
    --run-tag topk5

  run "[C-2/2] full top-k=20 seed=0" \
    --ablation full --seed 0 \
    --epochs $EPOCHS \
    --hidden-dim 32 --sector-hidden 16 --q-hidden 16 --attn-dim 8 \
    --top-k 20 --smooth-lambda 0.1 \
    --lr 0.001 --huber-delta 300 \
    --run-tag topk20
}

# ─── D. Sensitivity — hidden-dim ──────────────────────────────────────────────
# Tests whether results hold with smaller and larger capacity.

run_section_D() {
  run "[D-1/2] full hidden=16 seed=0" \
    --ablation full --seed 0 \
    --epochs $EPOCHS \
    --hidden-dim 16 --q-hidden 8 --attn-dim 4 \
    --top-k 10 --smooth-lambda 0.1 \
    --lr 0.001 --huber-delta 300 \
    --run-tag hidden16

  run "[D-2/2] full hidden=64 seed=0" \
    --ablation full --seed 0 \
    --epochs $EPOCHS \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --top-k 10 --smooth-lambda 0.1 \
    --lr 0.001 --huber-delta 300 \
    --run-tag hidden64
}

# ─── Dispatch ─────────────────────────────────────────────────────────────────

echo "============================================"
echo " HERALD V4 — Training Battery"
echo " Section   : $SECTION"
echo " Epochs    : $EPOCHS"
echo " Seeds     : $SEEDS"
echo " Start     : $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

case "$SECTION" in
  A)   run_section_A ;;
  B)   run_section_B ;;
  C)   run_section_C ;;
  D)   run_section_D ;;
  all)
    run_section_A
    run_section_B
    run_section_C
    run_section_D
    ;;
  *)
    echo "Unknown section: $SECTION. Use A, B, C, D or all."
    exit 1
    ;;
esac

echo ""
echo "============================================"
echo " Complete: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
