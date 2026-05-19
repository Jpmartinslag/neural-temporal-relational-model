#!/bin/bash
# CPU/GPU smoke for Phase 2E. Runs one epoch on one fold for the new mechanisms.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2e_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
DEVICE=${DEVICE:-cpu}

mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,logs,metadata}

"$PYTHON" -c "import ruptures; print('ruptures OK', ruptures.__version__)"
"$PYTHON" -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py

common_args() {
  local label=$1
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "${OUT_SMOKE}/data_processed" \
    --metrics-path "${OUT_SMOKE}/reports/per_run/${label}.json" \
    --model-card-path "${OUT_SMOKE}/reports/per_run/${label}.md" \
    --epochs 1 \
    --hidden-dim 16 \
    --q-hidden 8 \
    --attn-dim 8 \
    --top-k 5 \
    --mode full \
    --v7-variant learned_regime_gate_sector_enhanced \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --sector-lambda 0.2 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --rank-lambda 0.02 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --semi-warmup-epochs 0 \
    --device "$DEVICE" \
    --seed 0 \
    --single-target-year 2021 \
    --run-tag "smoke_${label}"
}

run_one() {
  local label=$1
  local regime=$2
  shift 2
  echo "--- smoke ${label} regime=${regime} ---"
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode "$regime" \
    --experiment-label "$label" \
    --drop-source-flags \
    --regime-metadata-path "${OUT_SMOKE}/metadata/${label}.json" \
    $(common_args "$label") \
    "$@"
}

run_one "cand_2c" "no_regime"
run_one "E1_resid_pelt_real" "resid_pelt"
run_one "E2_velocity_causal" "recovery_velocity"
run_one "E2_velocity_perm" "recovery_velocity_permute"
run_one "E4_step_thr06" "no_regime" --latent-max-step-lambda 0.005 --latent-step-threshold 0.6
run_one "E1_E2_E4_combo_light" "resid_pelt_recovery_velocity" --latent-max-step-lambda 0.005 --latent-step-threshold 0.6

echo "Smoke completed: ${OUT_SMOKE}"
