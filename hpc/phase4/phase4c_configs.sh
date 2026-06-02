#!/bin/bash
# Phase 4 config registry — international batteries (NL / BE / PT).
#
# All configs use the winning France architecture:
#   regime_mode  : no_regime (learned_regime_gate_sector_enhanced)
#   feature_policy: side5_lag1_growth1y (baseline_side2) OR current_clean (no_qtensor_control)
#   No source flags (no FLORES/URSSAF flags in international data)
#   latent_regime_dim: 5
#
# Output: one line per config, tab-separated:
#   label  feature_policy  qtensor_policy
#
# qtensor_policy: zero | effectifs_lag1
#   zero          → tensor completely zeroed (baseline, control)
#   effectifs_lag1 → lag-1 employment/births signal (channel 0, lag-1 shift)
#
# Usage:
#   COUNTRY=nl source hpc/phase4/phase4c_configs.sh && phase4c_configs
#   COUNTRY=be source hpc/phase4/phase4c_configs.sh && phase4c_configs
#   COUNTRY=pt source hpc/phase4/phase4c_configs.sh && phase4c_configs

phase4c_configs() {
  local country="${COUNTRY:?COUNTRY env var required (nl|be|pt)}"

  case "$country" in
    nl|be)
      # Config 1: baseline — 2 SIDE features, no tensor
      echo "baseline_side2        side5_lag1_growth1y  zero"
      # Config 2: + Q7-equivalent employment tensor lag1
      echo "qtensor_jobs_lag1     side5_lag1_growth1y  effectifs_lag1"
      # Config 3: all available features, no tensor (ablation control)
      echo "no_qtensor_control    current_clean        zero"
      ;;
    pt)
      # Config 1: baseline — 2 SIDE features, no tensor
      echo "baseline_side2        side5_lag1_growth1y  zero"
      # Config 2: + sector_births_tensor lag1 (⚠️ proxy — NOT Q7 effectifs)
      echo "sector_births_lag1    side5_lag1_growth1y  effectifs_lag1"
      # Config 3: all available features, no tensor (ablation control)
      echo "no_qtensor_control    current_clean        zero"
      ;;
    *)
      echo "ERROR: unknown country: $country (expected nl|be|pt)" >&2
      return 1
      ;;
  esac
}

phase4_n_configs() {
  local country="${COUNTRY:?}"
  case "$country" in
    nl|be|pt) echo 3 ;;
    *) echo 0 ;;
  esac
}
