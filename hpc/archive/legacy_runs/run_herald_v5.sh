#!/bin/bash
# ============================================================
#  HERALD V5 — Complete training battery
#  V3 backbone (proven total prediction) + A10 sector head
#
#  BEFORE RUNNING:
#    1. Set PYTHON to your environment's python3 with PyTorch + sklearn
#    2. Run from the project root:  cd /path/to/dataset && bash run_herald_v5.sh
#
#  Sections:
#    A  Core ablations     (8 × 3 seeds = 24 runs) — paper main table
#    B  Sensitivity smooth (2 × seed 0  =  2 runs) — λ_smooth sensitivity
#    C  Sensitivity top-k  (2 × seed 0  =  2 runs) — graph sparsity
#    D  Sensitivity hidden (2 × seed 0  =  2 runs) — capacity
#
#  Total: 30 runs
#
#  Usage:
#    bash run_herald_v5.sh        # all sections
#    bash run_herald_v5.sh A      # only core ablations
#    bash run_herald_v5.sh B      # only smooth sensitivity
#    bash run_herald_v5.sh C      # only top-k sensitivity
#    bash run_herald_v5.sh D      # only capacity sensitivity
# ============================================================

set -e

# ── CONFIGURE THIS ────────────────────────────────────────────────────────────
PYTHON=python3          # change to your env, e.g. /opt/conda/envs/torch/bin/python3
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT=src/data/train_herald_v5.py
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

# ─── A. Core ablations ────────────────────────────────────────────────────────
# Ablation          | What it tests
# ------------------| --------------------------------------------------
# full              | Complete V5 — main result
# self_only         | No message passing — pure temporal baseline
# fixed_geo_mob_only| Fixed geo+mob graph — no learned adjacency
# static_adaptive   | Learned static adj — no temporal dynamics in graph
# no_sector_head    | Total only (= V3 equivalent) — sector head cost?
# no_quarterly      | No URSSAF quarterly — sub-annual signal importance
# no_regime         | regime_t = 0 — regime conditioning importance
# no_smooth         | λ_smooth = 0 — temporal smoothness importance

run_section_A() {
  local COUNT=0
  for ABLATION in full self_only fixed_geo_mob_only static_adaptive \
                  no_sector_head no_quarterly no_regime no_smooth; do
    for SEED in $SEEDS; do
      COUNT=$((COUNT + 1))
      run "[A-$COUNT/24] $ABLATION seed=$SEED" \
        --ablation    "$ABLATION" \
        --seed        "$SEED" \
        --epochs      $EPOCHS \
        --hidden-dim  32 --q-hidden 16 --attn-dim 8 \
        --top-k       10 --smooth-lambda 0.1 --sector-lambda 0.1 \
        --lr          0.001 --huber-delta 300
    done
  done
}

# ─── B. Sensitivity — smooth-lambda ──────────────────────────────────────────
run_section_B() {
  run "[B-1/2] smooth=0.01 seed=0" \
    --ablation full --seed 0 --epochs $EPOCHS \
    --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
    --top-k 10 --smooth-lambda 0.01 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --run-tag smooth001

  run "[B-2/2] smooth=0.5 seed=0" \
    --ablation full --seed 0 --epochs $EPOCHS \
    --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
    --top-k 10 --smooth-lambda 0.5 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --run-tag smooth05
}

# ─── C. Sensitivity — top-k ──────────────────────────────────────────────────
run_section_C() {
  run "[C-1/2] top-k=5 seed=0" \
    --ablation full --seed 0 --epochs $EPOCHS \
    --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
    --top-k 5 --smooth-lambda 0.1 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --run-tag topk5

  run "[C-2/2] top-k=20 seed=0" \
    --ablation full --seed 0 --epochs $EPOCHS \
    --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
    --top-k 20 --smooth-lambda 0.1 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --run-tag topk20
}

# ─── D. Sensitivity — hidden-dim ─────────────────────────────────────────────
run_section_D() {
  run "[D-1/2] hidden=16 seed=0" \
    --ablation full --seed 0 --epochs $EPOCHS \
    --hidden-dim 16 --q-hidden 8 --attn-dim 4 \
    --top-k 10 --smooth-lambda 0.1 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --run-tag hidden16

  run "[D-2/2] hidden=64 seed=0" \
    --ablation full --seed 0 --epochs $EPOCHS \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --top-k 10 --smooth-lambda 0.1 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --run-tag hidden64
}

# ─── Dispatch ─────────────────────────────────────────────────────────────────
echo "============================================"
echo " HERALD V5 — Training Battery"
echo " Python    : $PYTHON"
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
    echo "Unknown section: $SECTION"
    echo "Use: A | B | C | D | all"
    exit 1
    ;;
esac

echo ""
echo "============================================"
echo " Complete: $(date '+%Y-%m-%d %H:%M:%S')"
echo " Results : reports/herald_v5_metrics_v1.json"
echo "         : reports/HERALD_V5_MODEL_V1.md"
echo "============================================"
