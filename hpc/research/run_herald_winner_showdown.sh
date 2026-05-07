#!/bin/bash
# ============================================================
# HERALD Winner Showdown Battery
#
# Compara os candidatos finalistas contra Ridge AR e controles
# com conjunto expandido de seeds para decisão robusta.
#
# Fases:
#   phase1  : 10 seeds × 3 candidatos + controles (confirmação rápida)
#   phase2  : 20 seeds × 2 finalistas  (decisão final de estabilidade)
#   showdown: phase1 + phase2
#
# Uso típico (gerar manifest para array SLURM):
#   EMIT_MANIFEST=1 MANIFEST_FILE=manifest_showdown.txt \
#     OUT_ROOT=hpc_results/herald_showdown_$(date +%Y%m%d_%H%M%S) \
#     SECTION=phase1 \
#     bash hpc/research/run_herald_winner_showdown.sh
#
# Uso serial local (smoke test):
#   EPOCHS=5 SEEDS="0 7" SECTION=phase1 \
#     OUT_ROOT=hpc_results/showdown_test \
#     bash hpc/research/run_herald_winner_showdown.sh
# ============================================================

set -euo pipefail

PYTHON=${PYTHON:-python3}
SECTION=${SECTION:-phase1}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_showdown_$(date +%Y%m%d_%H%M%S)"}

# Seeds phase 1: 10 seeds (inclui seeds problemáticas 77 e 2025)
SEEDS_P1=${SEEDS_P1:-"0 1 7 13 17 42 77 99 123 200"}
# Seeds phase 2: 20 seeds (estabilidade)
SEEDS_P2=${SEEDS_P2:-"0 1 2 3 7 13 17 21 42 55 77 88 99 100 123 200 256 321 512 2025"}

EMIT_MANIFEST=${EMIT_MANIFEST:-0}
MANIFEST_FILE=${MANIFEST_FILE:-"$OUT_ROOT/manifest_showdown.txt"}

PANEL_PATH=data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
SPLITS_PATH=metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
SIDE_A10_PATH=data/processed/side_creations_a10_ze2020_through_2025_v1.csv

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs}

if [ "$EMIT_MANIFEST" = "1" ]; then
  : > "$MANIFEST_FILE"
fi

# ---- helpers ----
__shell_quote() {
  local out=""
  for part in "$@"; do
    if [ -z "$out" ]; then
      out=$(printf '%q' "$part")
    else
      out="$out $(printf '%q' "$part")"
    fi
  done
  printf '%s' "$out"
}

run() {
  local label=$1
  shift
  if [ "$EMIT_MANIFEST" = "1" ]; then
    {
      printf '# %s\n' "$label"
      printf '%s %s\n' "$(printf '%q' "$PYTHON")" "$(__shell_quote "$@")"
    } >> "$MANIFEST_FILE"
  else
    echo ""
    echo ">> $label  $(date '+%Y-%m-%d %H:%M:%S')"
    "$PYTHON" "$@"
    echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
  fi
}

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
  require_file src/modeles/train_herald_semi_v2.py
  require_file src/modeles/train_herald_v7.py
  require_file src/modeles/train_herald_v6.py
}

# ---- common args builders ----
semi_v2_args() {
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 --alpha-smooth-lambda 0.001 \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --epochs "$EPOCHS" \
    --semi-warmup-epochs "$MASK_WARMUP"
}

v7_args() {
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --epochs "$EPOCHS"
}

v6_args() {
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --hidden-dim 64 \
    --epochs "$EPOCHS"
}

# ---- model runners ----
run_semi_full_hybrid() {
  local seeds=$1
  local count=0
  for seed in $seeds; do
    count=$((count + 1))
    local tag="semiv2_full_f0.10_s0.30_r0.02_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/${tag}.json"
    local mc="$OUT_ROOT/reports/per_run/${tag}.md"
    run "[SHOWDOWN semi/full_hybrid $count] seed=$seed" \
      src/modeles/train_herald_semi_v2.py \
      $(semi_v2_args "$mp" "$mc") \
      --mode full \
      --feature-mask-ratio 0.10 \
      --sector-mask-ratio 0.30 \
      --rank-lambda 0.02 \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_semi_masked() {
  local seeds=$1
  local count=0
  for seed in $seeds; do
    count=$((count + 1))
    local tag="semiv2_masked_variables_f0.10_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/${tag}.json"
    local mc="$OUT_ROOT/reports/per_run/${tag}.md"
    run "[SHOWDOWN semi/masked_variables $count] seed=$seed" \
      src/modeles/train_herald_semi_v2.py \
      $(semi_v2_args "$mp" "$mc") \
      --mode masked_variables \
      --feature-mask-ratio 0.10 \
      --sector-mask-ratio 0.00 \
      --rank-lambda 0.00 \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_v7_fixed_alpha() {
  local seeds=$1
  local count=0
  for seed in $seeds; do
    count=$((count + 1))
    local tag="v7_fixed_alpha_0.5_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/${tag}.json"
    local mc="$OUT_ROOT/reports/per_run/${tag}.md"
    run "[SHOWDOWN v7/fixed_alpha_0.5 $count] seed=$seed" \
      src/modeles/train_herald_v7.py \
      $(v7_args "$mp" "$mc") \
      --variant fixed_alpha_0.5 \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_v6_h64_full() {
  local seeds=$1
  local count=0
  for seed in $seeds; do
    count=$((count + 1))
    local tag="v6ctrl_h64_full_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/${tag}.json"
    local mc="$OUT_ROOT/reports/per_run/${tag}.md"
    run "[SHOWDOWN V6 h64_full $count] seed=$seed" \
      src/modeles/train_herald_v6.py \
      $(v6_args "$mp" "$mc") \
      --ablation full \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

# ---- phases ----
run_phase1() {
  echo "=== PHASE 1: Direction confirmation (${SEEDS_P1}) ==="
  run_semi_full_hybrid "$SEEDS_P1"
  run_semi_masked      "$SEEDS_P1"
  run_v7_fixed_alpha   "$SEEDS_P1"
  run_v6_h64_full      "$SEEDS_P1"
}

run_phase2() {
  echo "=== PHASE 2: Stability (${SEEDS_P2}) ==="
  # Only top-2 candidates: semi/full_hybrid and semi/masked_variables
  run_semi_full_hybrid "$SEEDS_P2"
  run_semi_masked      "$SEEDS_P2"
}

echo "============================================================"
echo " HERALD Winner Showdown"
echo " Python      : $PYTHON"
echo " Section     : $SECTION"
echo " Epochs      : $EPOCHS"
echo " Mask warmup : $MASK_WARMUP"
echo " Seeds P1    : $SEEDS_P1"
echo " Seeds P2    : $SEEDS_P2"
echo " Out         : $OUT_ROOT"
echo " Emit mft    : $EMIT_MANIFEST"
[ "$EMIT_MANIFEST" = "1" ] && echo " Manifest    : $MANIFEST_FILE"
echo "============================================================"

check_inputs

case "$SECTION" in
  phase1)    run_phase1 ;;
  phase2)    run_phase2 ;;
  showdown)  run_phase1; run_phase2 ;;
  *)
    echo "Usage: phase1 | phase2 | showdown"
    exit 1
    ;;
esac

echo ""
echo "Results in: $OUT_ROOT"
echo "Per-run JSONs in: $OUT_ROOT/reports/per_run/"
echo "Aggregate with: python hpc/research/aggregate_v7_metrics.py --root $OUT_ROOT"
