#!/bin/bash
# Phase 4E-B config definitions.
#
# Purpose: causal feature-policy ablation on the canonical European panel.
# Phase 4A/4D are leakage-affected and are not used as valid baselines.
#
# Format:
#   label  wrapper_type  feature_policy  qtensor_policy  qtensor_path  qtensor_col
#
# wrapper_type:
#   baseline  -> use run_herald_phase4e_a_wrapper.py (fixed 5 causal annual features)
#   policy    -> use run_herald_phase4e_a2_wrapper.py (trainer feature_policy)

phase4e_b_configs() {
  local country="${COUNTRY:?COUNTRY env var required (fr|nl|be|pt)}"

  echo "b0_baseline_annual       baseline current_clean        zero           none                                                            none"
  echo "b1_side5_full_zero       policy   side5_full           zero           none                                                            none"
  echo "b2_side2_zero            policy   side5_lag1_growth1y  zero           none                                                            none"
  echo "b3_current_clean_zero    policy   current_clean        zero           none                                                            none"

  case "$country" in
    pt)
      echo "b4_side2_births_lag1     policy   side5_lag1_growth1y  effectifs_lag1 data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv births"
      echo "b5_side2_emp_lag1        policy   side5_lag1_growth1y  effectifs_lag1 data/external/portugal/processed/portugal_qtensor_employment_eurostat_nuts3.csv jobs"
      ;;
    fr|nl|be)
      ;;
    *)
      echo "ERROR: unknown country: $country (expected fr|nl|be|pt)" >&2
      return 1
      ;;
  esac
}

export -f phase4e_b_configs
