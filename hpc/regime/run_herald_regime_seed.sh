#!/bin/bash
# ============================================================
# HERALD regime discovery battery - one seed, sequential.
#
# One SLURM array task = one seed = four regime hypotheses.
# Outputs are isolated under OUT_ROOT and never touch dashboard artifacts.
# ============================================================

set -euo pipefail

PYTHON=${PYTHON:-python3}
SEED=${SEED:?SEED is required}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_discovery_$(date +%Y%m%d_%H%M%S)"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
REGIME_PLAN=${REGIME_PLAN:-discovery}
DEVICE=${DEVICE:-}

PANEL_PATH=${PANEL_PATH:-data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv}
SPLITS_PATH=${SPLITS_PATH:-metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv}
SIDE_A10_PATH=${SIDE_A10_PATH:-data/processed/side_creations_a10_ze2020_through_2025_v1.csv}

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata}

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
  require_file src/modeles/train_herald_regime_experiment.py
  require_file src/modeles/herald_regime_modes.py
  require_file src/modeles/train_herald_semi_v2.py
  require_file src/modeles/train_herald_v7.py
  require_file src/modeles/train_herald_v6.py
}

common_args() {
  local mp=$1
  local mc=$2
  local variant=$3
  local sector_lambda=$4
  local alpha_smooth_lambda=$5
  local smooth_lambda=$6
  local smooth_regime_source=$7
  local latent_train_mode=$8
  local latent_inference_mode=$9
  local regime_seq_transform=${10}
  local single_target_year=${11}
  # Phase 2D stability params (default to inactive when omitted)
  local collapse_lambda=${12:-0.0}
  local latent_smooth_lambda=${13:-0.0}
  local alpha_balance_lambda=${14:-0.0}
  local zone_dro_boost=${15:-1.0}
  local swa_start_frac=${16:-0.0}
  local window_years=${17:-0}
  local latent_max_step_lambda=${18:-0.0}
  local latent_step_threshold=${19:-0.6}
  local feature_policy=${20:-current_clean}
  local macro_feature_set=${21:-none}
  local latent_regime_dim=${22:-3}
  local latent_dim_l1_lambda=${23:-0.0}
  local latent_dim_auto_mask=${24:-fixed}
  local latent_dim_mask_type=${25:-sigmoid}
  local latent_dim_beta_start=${26:-none}
  local latent_dim_beta_end=${27:-none}
  local latent_group_lasso_lambda=${28:-0.0}
  local auditor_mode=${29:-none}
  local auditor_budget_lambda=${30:-0.0}
  local auditor_smooth_lambda=${31:-0.0}
  local auditor_bias_init=${32:-2.0}
  local residual_shrinkage_mode=${33:-none}
  local residual_shrinkage_value=${34:-1.0}
  local residual_shrinkage_min=${35:-0.0}
  local residual_shrinkage_max=${36:-1.25}
  local tutor_feature_set=${37:-none}
  local tutor_state_transform=${38:-none}
  local labor_tutor_feature_set=${39:-none}
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --top-k 10 \
    --smooth-lambda "$smooth_lambda" \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda "$alpha_smooth_lambda" \
    --sector-lambda "$sector_lambda" \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --hidden-dim 64 \
    --q-hidden 32 \
    --attn-dim 16 \
    --mode full \
    --v7-variant "$variant" \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --rank-lambda 0.02 \
    --smooth-regime-source "$smooth_regime_source" \
    --latent-train-mode "$latent_train_mode" \
    --latent-inference-mode "$latent_inference_mode" \
    --regime-seq-transform "$regime_seq_transform" \
    --semi-warmup-epochs "$MASK_WARMUP" \
    --epochs "$EPOCHS" \
    --collapse-lambda "$collapse_lambda" \
    --latent-smooth-lambda "$latent_smooth_lambda" \
    --alpha-balance-lambda "$alpha_balance_lambda" \
    --zone-dro-q45-boost "$zone_dro_boost" \
    --swa-start-frac "$swa_start_frac" \
    --latent-max-step-lambda "$latent_max_step_lambda" \
    --latent-step-threshold "$latent_step_threshold" \
    --latent-regime-dim "${latent_regime_dim:-3}" \
    --latent-dim-l1-lambda "${latent_dim_l1_lambda:-0.0}" \
    --latent-dim-mask-type "${latent_dim_mask_type:-sigmoid}" \
    --latent-group-lasso-lambda "${latent_group_lasso_lambda:-0.0}" \
    --auditor-mode "${auditor_mode:-none}" \
    --auditor-budget-lambda "${auditor_budget_lambda:-0.0}" \
    --auditor-smooth-lambda "${auditor_smooth_lambda:-0.0}" \
    --auditor-bias-init "${auditor_bias_init:-2.0}" \
    --residual-shrinkage-mode "${residual_shrinkage_mode:-none}" \
    --residual-shrinkage-value "${residual_shrinkage_value:-1.0}" \
    --residual-shrinkage-min "${residual_shrinkage_min:-0.0}" \
    --residual-shrinkage-max "${residual_shrinkage_max:-1.25}" \
    --tutor-feature-set "${tutor_feature_set:-none}" \
    --tutor-state-transform "${tutor_state_transform:-none}" \
    --labor-tutor-feature-set "${labor_tutor_feature_set:-none}" \
    --labor-tutor-path "${LABOR_TUTOR_PATH:-data/processed/herald_phase3c_labor_tutor_features.csv}"
  if [ "${latent_dim_auto_mask:-fixed}" = "auto" ] || [ "${latent_dim_auto_mask:-fixed}" = "hard_concrete" ]; then
    echo --latent-dim-auto-mask
  fi
  if [ "${latent_dim_beta_start:-none}" != "none" ]; then
    echo --latent-dim-beta-start "$latent_dim_beta_start"
  fi
  if [ "${latent_dim_beta_end:-none}" != "none" ]; then
    echo --latent-dim-beta-end "$latent_dim_beta_end"
  fi
  if [ "${window_years:-0}" -gt 0 ] 2>/dev/null; then
    echo --window-years "$window_years"
  fi
  if [ "$single_target_year" != "all" ]; then
    echo --single-target-year "$single_target_year"
  fi
  if [ -n "$DEVICE" ]; then
    echo --device "$DEVICE"
  fi
}

run_regime() {
  local mode=$1
  local variant=${2:-full}
  local source_policy=${3:-with_source_flags}
  local label=${4:-base}
  local sector_lambda=${5:-0.1}
  local alpha_smooth_lambda=${6:-0.001}
  local smooth_lambda=${7:-0.01}
  local smooth_regime_source=${8:-explicit}
  local latent_train_mode=${9:-normal}
  local latent_inference_mode=${10:-match_train}
  local regime_seq_transform=${11:-none}
  local single_target_year=${12:-all}
  # Phase 2D stability params (positional 13-17, default to inactive)
  local collapse_lambda=${13:-0.0}
  local latent_smooth_lambda=${14:-0.0}
  local alpha_balance_lambda=${15:-0.0}
  local zone_dro_boost=${16:-1.0}
  local swa_start_frac=${17:-0.0}
  local window_years=${18:-0}
  local latent_max_step_lambda=${19:-0.0}
  local latent_step_threshold=${20:-0.6}
  local feature_policy=${21:-current_clean}
  local macro_feature_set=${22:-none}
  local latent_regime_dim=${23:-3}
  local latent_dim_l1_lambda=${24:-0.0}
  local latent_dim_auto_mask=${25:-fixed}
  local latent_dim_mask_type=${26:-sigmoid}
  local latent_dim_beta_start=${27:-none}
  local latent_dim_beta_end=${28:-none}
  local latent_group_lasso_lambda=${29:-0.0}
  local auditor_mode=${30:-none}
  local auditor_budget_lambda=${31:-0.0}
  local auditor_smooth_lambda=${32:-0.0}
  local auditor_bias_init=${33:-2.0}
  local residual_shrinkage_mode=${34:-none}
  local residual_shrinkage_value=${35:-1.0}
  local residual_shrinkage_min=${36:-0.0}
  local residual_shrinkage_max=${37:-1.25}
  local tutor_feature_set=${38:-none}
  local tutor_state_transform=${39:-none}
  local labor_tutor_feature_set=${40:-none}
  local quarterly_tensor_policy=${41:-real}
  local tag="regime_${mode}"
  if [ "$variant" != "full" ]; then
    tag="${tag}_${variant}"
  fi
  if [ "$source_policy" = "no_source_flags" ]; then
    tag="${tag}_no_source_flags"
  elif [ "$source_policy" != "with_source_flags" ]; then
    echo "Unknown source_policy=${source_policy}" >&2
    exit 1
  fi
  if [ "$label" != "base" ]; then
    tag="${tag}_${label}"
  fi
  local suffix="full_${tag}_seed_${SEED}"
  local mp="$OUT_ROOT/reports/per_run/${tag}_seed_${SEED}.json"
  local mc="$OUT_ROOT/reports/per_run/${tag}_seed_${SEED}.md"
  local meta="$OUT_ROOT/metadata/${tag}_seed_${SEED}.json"
  local out_total="$OUT_ROOT/data_processed/herald_semi_v2_predictions_total_${suffix}_v1.csv"
  local out_sector="$OUT_ROOT/data_processed/herald_semi_v2_predictions_sector_${suffix}_v1.csv"
  local out_int="$OUT_ROOT/data_processed/herald_semi_v2_internals_${suffix}_v1.npz"

  for existing in "$mp" "$mc" "$meta" "$out_total" "$out_sector" "$out_int"; do
    if [ -e "$existing" ]; then
      echo "Refusing to overwrite existing artifact: $existing" >&2
      exit 1
    fi
  done

  echo ""
  if [ "${latent_dim_auto_mask:-fixed}" = "hard_concrete" ]; then
    latent_dim_mask_type="hard_concrete"
  fi
  echo ">> [seed=${SEED}] HERALD regime=${mode} variant=${variant} source_policy=${source_policy} label=${label} feature_policy=${feature_policy} macro_feature_set=${macro_feature_set} q_tensor_policy=${quarterly_tensor_policy} tutor=${tutor_feature_set}:${tutor_state_transform} sector_lambda=${sector_lambda} alpha_smooth=${alpha_smooth_lambda} smooth=${smooth_lambda} smooth_source=${smooth_regime_source} latent_train=${latent_train_mode} latent_inf=${latent_inference_mode} regime_transform=${regime_seq_transform} fold=${single_target_year} latent_dim=${latent_regime_dim} l1=${latent_dim_l1_lambda} auto_mask=${latent_dim_auto_mask} mask_type=${latent_dim_mask_type} beta=${latent_dim_beta_start}->${latent_dim_beta_end} group_lasso=${latent_group_lasso_lambda} auditor=${auditor_mode} auditor_budget=${auditor_budget_lambda} auditor_smooth=${auditor_smooth_lambda} shrink=${residual_shrinkage_mode}:${residual_shrinkage_value}  $(date '+%Y-%m-%d %H:%M:%S')"
  local source_args=()
  if [ "$source_policy" = "no_source_flags" ]; then
    source_args+=(--drop-source-flags)
  fi
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode "$mode" \
    --experiment-label "$label" \
    --feature-policy "$feature_policy" \
    --macro-feature-set "$macro_feature_set" \
    --quarterly-tensor-policy "$quarterly_tensor_policy" \
    ${source_args[@]+"${source_args[@]}"} \
    --regime-metadata-path "$meta" \
    $(common_args "$mp" "$mc" "$variant" "$sector_lambda" "$alpha_smooth_lambda" "$smooth_lambda" "$smooth_regime_source" "$latent_train_mode" "$latent_inference_mode" "$regime_seq_transform" "$single_target_year" "$collapse_lambda" "$latent_smooth_lambda" "$alpha_balance_lambda" "$zone_dro_boost" "$swa_start_frac" "$window_years" "$latent_max_step_lambda" "$latent_step_threshold" "$feature_policy" "$macro_feature_set" "$latent_regime_dim" "$latent_dim_l1_lambda" "$latent_dim_auto_mask" "$latent_dim_mask_type" "$latent_dim_beta_start" "$latent_dim_beta_end" "$latent_group_lasso_lambda" "$auditor_mode" "$auditor_budget_lambda" "$auditor_smooth_lambda" "$auditor_bias_init" "$residual_shrinkage_mode" "$residual_shrinkage_value" "$residual_shrinkage_min" "$residual_shrinkage_max" "$tutor_feature_set" "$tutor_state_transform" "$labor_tutor_feature_set") \
    --seed "$SEED" \
    --run-tag "$tag"
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

echo "============================================================"
echo " HERALD regime discovery battery"
echo " seed     : $SEED"
echo " out_root : $OUT_ROOT"
echo " epochs   : $EPOCHS"
echo " warmup   : $MASK_WARMUP"
echo " plan     : $REGIME_PLAN"
echo " device   : ${DEVICE:-auto}"
echo " panel    : $PANEL_PATH"
echo " splits   : $SPLITS_PATH"
echo "============================================================"

check_inputs

# Load plan_configs() from the dedicated file (no training code there).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=regime_plan_configs.sh
source "${SCRIPT_DIR}/regime_plan_configs.sh"

echo "Planned artifacts for seed=${SEED}:"
while read -r mode variant source_policy label sector_lambda alpha_smooth_lambda smooth_lambda smooth_regime_source latent_train_mode latent_inference_mode regime_seq_transform single_target_year collapse_lambda latent_smooth_lambda alpha_balance_lambda zone_dro_boost swa_start_frac window_years latent_max_step_lambda latent_step_threshold feature_policy macro_feature_set latent_regime_dim latent_dim_l1_lambda latent_dim_auto_mask latent_dim_mask_type latent_dim_beta_start latent_dim_beta_end latent_group_lasso_lambda auditor_mode auditor_budget_lambda auditor_smooth_lambda auditor_bias_init residual_shrinkage_mode residual_shrinkage_value residual_shrinkage_min residual_shrinkage_max tutor_feature_set tutor_state_transform labor_tutor_feature_set quarterly_tensor_policy; do
  tag="regime_${mode}"
  if [ "$variant" != "full" ]; then
    tag="${tag}_${variant}"
  fi
  if [ "$source_policy" = "no_source_flags" ]; then
    tag="${tag}_no_source_flags"
  fi
  if [ "${label:-base}" != "base" ]; then
    tag="${tag}_${label}"
  fi
  suffix="full_${tag}_seed_${SEED}"
  echo "  ${tag}:"
  echo "    $OUT_ROOT/reports/per_run/${tag}_seed_${SEED}.json"
  echo "    $OUT_ROOT/data_processed/herald_semi_v2_predictions_total_${suffix}_v1.csv"
  echo "    $OUT_ROOT/data_processed/herald_semi_v2_predictions_sector_${suffix}_v1.csv"
  echo "    $OUT_ROOT/data_processed/herald_semi_v2_internals_${suffix}_v1.npz"
done < <(plan_configs)

while read -r mode variant source_policy label sector_lambda alpha_smooth_lambda smooth_lambda smooth_regime_source latent_train_mode latent_inference_mode regime_seq_transform single_target_year collapse_lambda latent_smooth_lambda alpha_balance_lambda zone_dro_boost swa_start_frac window_years latent_max_step_lambda latent_step_threshold feature_policy macro_feature_set latent_regime_dim latent_dim_l1_lambda latent_dim_auto_mask latent_dim_mask_type latent_dim_beta_start latent_dim_beta_end latent_group_lasso_lambda auditor_mode auditor_budget_lambda auditor_smooth_lambda auditor_bias_init residual_shrinkage_mode residual_shrinkage_value residual_shrinkage_min residual_shrinkage_max tutor_feature_set tutor_state_transform labor_tutor_feature_set quarterly_tensor_policy; do
  run_regime "$mode" "$variant" "$source_policy" "$label" "$sector_lambda" "$alpha_smooth_lambda" "$smooth_lambda" "$smooth_regime_source" "$latent_train_mode" "$latent_inference_mode" "$regime_seq_transform" "$single_target_year" "${collapse_lambda:-0.0}" "${latent_smooth_lambda:-0.0}" "${alpha_balance_lambda:-0.0}" "${zone_dro_boost:-1.0}" "${swa_start_frac:-0.0}" "${window_years:-0}" "${latent_max_step_lambda:-0.0}" "${latent_step_threshold:-0.6}" "${feature_policy:-current_clean}" "${macro_feature_set:-none}" "${latent_regime_dim:-3}" "${latent_dim_l1_lambda:-0.0}" "${latent_dim_auto_mask:-fixed}" "${latent_dim_mask_type:-sigmoid}" "${latent_dim_beta_start:-none}" "${latent_dim_beta_end:-none}" "${latent_group_lasso_lambda:-0.0}" "${auditor_mode:-none}" "${auditor_budget_lambda:-0.0}" "${auditor_smooth_lambda:-0.0}" "${auditor_bias_init:-2.0}" "${residual_shrinkage_mode:-none}" "${residual_shrinkage_value:-1.0}" "${residual_shrinkage_min:-0.0}" "${residual_shrinkage_max:-1.25}" "${tutor_feature_set:-none}" "${tutor_state_transform:-none}" "${labor_tutor_feature_set:-none}" "${quarterly_tensor_policy:-real}"
done < <(plan_configs)

echo ""
echo "DONE seed=$SEED"
echo "results=$OUT_ROOT"
