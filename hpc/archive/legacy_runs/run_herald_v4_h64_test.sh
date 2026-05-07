#!/bin/bash
# HERALD V4 — Hidden=64 bottleneck test
#
# Tests whether increasing hidden_dim from 32 to 64 resolves the sector_agg
# bottleneck that caused self_only to beat full in V4 (32).
#
# Runs only the 3 ablations needed to confirm or refute the hypothesis:
#   full          — main model with larger capacity
#   self_only     — must be beaten by full to confirm fix
#   no_sector_gate — tests if sector gate still helps at h=64
#
# 3 ablations × 3 seeds = 9 runs
# Usage: bash run_herald_v4_h64_test.sh

set -e

PYTHON=/home/jpdark/miniconda3/envs/mineru/bin/python3
SCRIPT=src/data/train_herald_v4.py

EPOCHS=800
SEEDS="0 7 42"
HIDDEN=64
Q_HIDDEN=16
ATTN_DIM=8

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%H:%M:%S')"
  $PYTHON $SCRIPT "$@"
  echo "   done  $(date '+%H:%M:%S')"
}

echo "============================================"
echo " HERALD V4 — Hidden=64 Bottleneck Test"
echo " hidden_dim : $HIDDEN  (was 32)"
echo " q_hidden   : $Q_HIDDEN  (unchanged)"
echo " attn_dim   : $ATTN_DIM  (unchanged)"
echo " Epochs     : $EPOCHS"
echo " Seeds      : $SEEDS"
echo " Start      : $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

COUNT=0
for ABLATION in full self_only no_sector_gate; do
  for SEED in $SEEDS; do
    COUNT=$((COUNT + 1))
    run "[$COUNT/9] $ABLATION seed=$SEED h=$HIDDEN" \
      --ablation    "$ABLATION" \
      --seed        "$SEED" \
      --epochs      $EPOCHS \
      --hidden-dim  $HIDDEN \
      --q-hidden    $Q_HIDDEN \
      --attn-dim    $ATTN_DIM \
      --top-k       10 \
      --smooth-lambda 0.1 \
      --lr          0.001 \
      --huber-delta 300 \
      --run-tag     h64
  done
done

echo ""
echo "============================================"
echo " Done: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo " Key question: does full_h64 beat self_only_h64 in 3/3 seeds?"
echo " Check: reports/herald_v4_metrics_v1.json"
echo "============================================"
