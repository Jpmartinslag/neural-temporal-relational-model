#!/bin/bash
# ============================================================
# HERALD V7 Research Battery - geo2025
#
# Two execution modes:
#
#   1. EMIT_MANIFEST=0 (default): runs each command sequentially, like before.
#      Per-run metrics paths are unique, so no race conditions even if you
#      launch several SECTIONs in parallel (different OUT_ROOTs).
#
#   2. EMIT_MANIFEST=1: emits commands to $MANIFEST_FILE and exits without
#      executing anything. Feed that manifest to the SLURM array sbatch
#      (hpc/research/run_herald_v7_array.sbatch) for true GPU-level parallelism.
#
# Sections:
#   smoke       : fast wiring check, no ARIMA
#   baselines   : naive, ridge, ARIMA, LSTM, DCRNN, Graph WaveNet, Dynamic STGNN
#   sector_baselines : A10 lag1_by_zone + hist_mean_by_zone (sector reference)
#   controls    : V6 h64 controls
#   semi_probe  : Semi V1 probes
#   semi_v2     : Semi V2 economic SSL alternatives
#   v7          : V7 variants (full, ridge_only, sector_lag1_only, ...)
#   all         : all of the above
#
# Examples:
#   # generate manifest (no execution):
#   EMIT_MANIFEST=1 MANIFEST_FILE=hpc_results/manifest.txt \
#     OUT_ROOT=hpc_results/herald_v7_g25_$(date +%Y%m%d_%H%M%S) \
#     bash hpc/research/run_herald_v7_research_battery.sh all
#
#   # local serial run of a single section:
#   bash hpc/research/run_herald_v7_research_battery.sh sector_baselines
# ============================================================

set -euo pipefail

PYTHON=${PYTHON:-python3}
SECTION=${1:-all}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
CLASSICAL_MODELS=${CLASSICAL_MODELS:-"naive_lag1 ridge_ar arima_local"}
REQUIRE_V7=${REQUIRE_V7:-0}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_v7_research_geo2025_$(date +%Y%m%d_%H%M%S)"}

EMIT_MANIFEST=${EMIT_MANIFEST:-0}
MANIFEST_FILE=${MANIFEST_FILE:-"$OUT_ROOT/manifest.txt"}

PANEL_PATH=data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
SPLITS_PATH=metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
SPLITS_PRECOVID=metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv
SIDE_A10_PATH=data/processed/side_creations_a10_ze2020_through_2025_v1.csv

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,temporal_baselines,stgnn_reports,stgnn_data_processed}

if [ "$EMIT_MANIFEST" = "1" ]; then
  : > "$MANIFEST_FILE"
fi

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

check_inputs() {
  require_file "$PANEL_PATH"
  require_file "$SPLITS_PATH"
  require_file "$SPLITS_PRECOVID"
  require_file "$SIDE_A10_PATH"
  require_file src/modeles/train_herald_v6.py
  require_file src/modeles/train_herald_semi_v1.py
  require_file src/modeles/train_herald_semi_v2.py
  require_file src/modeles/train_herald_v7.py
  require_file src/modeles/sector_baselines_v1.py
  require_file src/modeles/train_temporal_baselines_v1.py
  require_file src/modeles/train_dynamic_stgnn_models_v1.py
}

# Quote a command line array for safe storage in the manifest.
__shell_quote() {
  local out=""
  local part
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

# ---- baselines ----
run_classical_baselines() {
  run "[BASELINES classical] $CLASSICAL_MODELS" \
    src/modeles/train_temporal_baselines_v1.py \
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
      src/modeles/train_temporal_baselines_v1.py \
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
    run "[BASELINES STGNN $count] seed=$seed" \
      src/modeles/train_dynamic_stgnn_models_v1.py \
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

# ---- sector baselines (A10 lag1_by_zone, hist_mean_by_zone) ----
run_sector_baselines() {
  local mp="$OUT_ROOT/reports/per_run/sector_baselines.json"
  local pred="$OUT_ROOT/data_processed/sector_baselines_predictions_v1.csv"
  run "[SECTOR BASELINES] lag1+hist_mean" \
    src/modeles/sector_baselines_v1.py \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --metrics-path "$mp" \
    --predictions-out "$pred"
}

# ---- V6 controls ----
v6_common_args() {
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
    --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --epochs "$EPOCHS"
}

run_v6_control() {
  local label=$1
  local ablation=$2
  local tag=$3
  local splits=${4:-$SPLITS_PATH}
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    local rkey="${tag}_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/v6ctrl_${rkey}.json"
    local mc="$OUT_ROOT/reports/per_run/v6ctrl_${rkey}.md"
    run "[$label $count] seed=$seed" \
      src/modeles/train_herald_v6.py \
      $(v6_common_args "$mp" "$mc") \
      --splits-path "$splits" \
      --ablation "$ablation" \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_controls() {
  run_v6_control "V6 h64 full reference" full v7ctrl_h64_full
  run_v6_control "V6 h64 self_only" self_only v7ctrl_h64_self_only
  run_v6_control "V6 h64 fixed_geo_mob_only" fixed_geo_mob_only v7ctrl_h64_fixed_geo_mob
  run_v6_control "V6 h64 no_regime_in_graph" no_regime_in_graph v7ctrl_h64_no_regime_graph
  run_v6_control "V6 h64 static_adaptive" static_adaptive v7ctrl_h64_static_adaptive
  run_v6_control "V6 h64 no_sector_head" no_sector_head v7ctrl_h64_no_sector_head
  run_v6_control "V6 h64 precovid full" full v7ctrl_h64_precovid "$SPLITS_PRECOVID"
}

# ---- Semi V1 probe ----
semi_common_args() {
  local mp=$1
  local mc=$2
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
    --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
    --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --ablation full --epochs "$EPOCHS" \
    --mask-warmup-epochs "$MASK_WARMUP"
}

run_semi_probe_config() {
  local label=$1
  local tag=$2
  local ratio=$3
  local strategy=$4
  local semi_lambda=$5
  local semi_target=$6
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    local rkey="${tag}_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/semiv1_${rkey}.json"
    local mc="$OUT_ROOT/reports/per_run/semiv1_${rkey}.md"
    run "[$label $count] seed=$seed" \
      src/modeles/train_herald_semi_v1.py \
      $(semi_common_args "$mp" "$mc") \
      --mask-ratio "$ratio" \
      --mask-strategy "$strategy" \
      --semi-lambda "$semi_lambda" \
      --semi-target "$semi_target" \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_semi_probe() {
  run_semi_probe_config "Semi control h64 mask0.0" v7semi_h64_mask0.0_control 0.0 random 0.0 total
  run_semi_probe_config "Semi mask0.30 random" v7semi_h64_mask0.30_random 0.30 random 0.0 total
  run_semi_probe_config "Semi A10 target lambda0.05" v7semi_h64_mask0.10_lam0.05_a10 0.10 random 0.05 a10
  run_semi_probe_config "Semi total+A10 lambda0.05" v7semi_h64_mask0.10_lam0.05_total_a10 0.10 random 0.05 total_a10
}

# ---- Semi V2 ----
semi_v2_common_args() {
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

run_semi_v2_config() {
  local label=$1
  local tag=$2
  local mode=$3
  local feature_mask=$4
  local sector_mask=$5
  local rank_lambda=$6
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    local rkey="${tag}_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/semiv2_${rkey}.json"
    local mc="$OUT_ROOT/reports/per_run/semiv2_${rkey}.md"
    run "[$label $count] seed=$seed" \
      src/modeles/train_herald_semi_v2.py \
      $(semi_v2_common_args "$mp" "$mc") \
      --mode "$mode" \
      --feature-mask-ratio "$feature_mask" \
      --sector-mask-ratio "$sector_mask" \
      --rank-lambda "$rank_lambda" \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_semi_v2() {
  run_semi_v2_config "Semi V2 masked economic variables" \
    semiv2_masked_variables_f0.10 masked_variables 0.10 0.00 0.00
  run_semi_v2_config "Semi V2 sector denoise" \
    semiv2_sector_denoise_s0.30 sector_denoise 0.00 0.30 0.00
  run_semi_v2_config "Semi V2 ranking auxiliary" \
    semiv2_ranking_aux_l0.02 ranking_aux 0.00 0.00 0.02
  run_semi_v2_config "Semi V2 temporal regime" \
    semiv2_temporal_regime temporal_regime 0.00 0.00 0.00
  run_semi_v2_config "Semi V2 full economic SSL" \
    semiv2_full_f0.10_s0.30_r0.02 full 0.10 0.30 0.02
}

# ---- V7 ----
v7_common_args() {
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
    --gate-bias-init 2.0 --alpha-bias-init 0.0 \
    --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
    --epochs "$EPOCHS"
}

run_v7_config() {
  local label=$1
  local variant=$2
  local tag=$3
  local count=0
  for seed in $SEEDS; do
    count=$((count + 1))
    local rkey="${tag}_seed_${seed}"
    local mp="$OUT_ROOT/reports/per_run/v7_${rkey}.json"
    local mc="$OUT_ROOT/reports/per_run/v7_${rkey}.md"
    run "[$label $count] seed=$seed" \
      src/modeles/train_herald_v7.py \
      $(v7_common_args "$mp" "$mc") \
      --variant "$variant" \
      --seed "$seed" \
      --run-tag "$tag"
  done
}

run_v7() {
  if [ ! -f src/modeles/train_herald_v7.py ]; then
    echo "Missing src/modeles/train_herald_v7.py."
    [ "$REQUIRE_V7" = "1" ] && exit 1
    echo "Skipping V7."
    return 0
  fi

  # canonical V7 (was 'full' AND 'ridge_graph_gate'; kept ONE to avoid duplicate runs)
  run_v7_config "V7 full"             full              v7_full
  run_v7_config "V7 ridge_only"       ridge_only        v7_ridge_only
  run_v7_config "V7 graph_only"       graph_only        v7_graph_only
  run_v7_config "V7 fixed_graph"      fixed_graph       v7_fixed_graph
  run_v7_config "V7 fixed_alpha_0.5"  fixed_alpha_0.5   v7_fixed_alpha_0.5
  run_v7_config "V7 no_regime_gate"   no_regime_gate    v7_no_regime_gate
  run_v7_config "V7 no_regime_graph"  no_regime_graph   v7_no_regime_graph
  run_v7_config "V7 sector_enhanced"  sector_enhanced   v7_sector_enhanced
  run_v7_config "V7 sector_lag1_only" sector_lag1_only  v7_sector_lag1_only
}

# ---- smoke ----
run_smoke() {
  local old_epochs=$EPOCHS
  local old_seeds=$SEEDS
  local old_classical=$CLASSICAL_MODELS
  EPOCHS=5
  SEEDS="0"
  CLASSICAL_MODELS="naive_lag1 ridge_ar"
  run_classical_baselines
  run_sector_baselines
  run_v6_control "SMOKE V6 h64 full" full smoke_v7ctrl_h64_full
  run_semi_v2_config "SMOKE Semi V2 masked variables" smoke_semiv2_masked_variables masked_variables 0.10 0.00 0.00
  run_v7_config "SMOKE V7 full" full smoke_v7_full
  run_v7_config "SMOKE V7 ridge_only" ridge_only smoke_v7_ridge_only
  EPOCHS=$old_epochs
  SEEDS=$old_seeds
  CLASSICAL_MODELS=$old_classical
}

echo "============================================================"
echo " HERALD V7 Research Battery - geo2025"
echo " Python      : $PYTHON"
echo " Section     : $SECTION"
echo " Epochs      : $EPOCHS"
echo " Seeds       : $SEEDS"
echo " Mask warmup : $MASK_WARMUP"
echo " Require V7  : $REQUIRE_V7"
echo " Out         : $OUT_ROOT"
echo " Panel       : $PANEL_PATH"
echo " Emit mft    : $EMIT_MANIFEST"
[ "$EMIT_MANIFEST" = "1" ] && echo " Manifest    : $MANIFEST_FILE"
echo "============================================================"

check_inputs

case "$SECTION" in
  smoke)             run_smoke ;;
  baselines)         run_baselines ;;
  sector_baselines)  run_sector_baselines ;;
  controls)          run_controls ;;
  semi_probe)        run_semi_probe ;;
  semi_v2)           run_semi_v2 ;;
  v7)                run_v7 ;;
  all)
    run_baselines
    run_sector_baselines
    run_controls
    run_semi_probe
    run_semi_v2
    run_v7
    ;;
  *)
    echo "Usage: smoke | baselines | sector_baselines | controls | semi_probe | semi_v2 | v7 | all"
    exit 1
    ;;
esac

if [ "$EMIT_MANIFEST" = "1" ]; then
  echo ""
  echo "Manifest written: $MANIFEST_FILE"
  echo "Lines: $(grep -cv '^#' "$MANIFEST_FILE" || true)"
else
  echo ""
  echo "Results in: $OUT_ROOT"
  echo "Per-run JSONs in: $OUT_ROOT/reports/per_run/"
  echo "Aggregate them with: python hpc/research/aggregate_v7_metrics.py --root $OUT_ROOT"
fi
