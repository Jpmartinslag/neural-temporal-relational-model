#!/bin/bash
# Phase 4E-C config definitions.
#
# Purpose: EU macro-signal ablation on top of Phase 4E-B per-country winners.
# Phase 4A/4D are leakage-affected and are NOT used as baselines.
# Phase 4E-B clean winners per country:
#   FR -> b2_side2_zero   (policy, side5_lag1_growth1y, zero)
#   NL -> b0_baseline_annual (baseline, 5 causal features, zero tensor)
#   BE -> b3_current_clean_zero (policy, current_clean, zero)
#   PT -> b5_side2_emp_lag1  (policy, side5_lag1_growth1y, effectifs_lag1, employment eurostat)
#
# Format (7 fields, space-separated):
#   label  wrapper_type  feature_policy  qtensor_policy  qtensor_path  qtensor_col  macro_feature_set
#
# wrapper_type:
#   baseline -> run_herald_phase4e_a_wrapper.py  (hardcoded 5 causal features, zero tensor)
#   policy   -> run_herald_phase4e_a2_wrapper.py (trainer feature_policy + qtensor)
#
# macro_feature_set values: none | eu_gdp | eu_labor | eu_esi | eu_all | eu_all_perm
# eu_all_perm = same cols as eu_all but permuted across years (falsification control, c5)

phase4e_c_configs() {
  local country="${COUNTRY:?COUNTRY env var required (fr|nl|be|pt)}"

  case "$country" in
    fr)
      # FR winner: b2_side2_zero -> policy, side5_lag1_growth1y, zero
      echo "c0_winner_4e_b  policy   side5_lag1_growth1y  zero           none  none  none"
      echo "c1_gdp          policy   side5_lag1_growth1y  zero           none  none  eu_gdp"
      echo "c2_labor        policy   side5_lag1_growth1y  zero           none  none  eu_labor"
      echo "c3_esi          policy   side5_lag1_growth1y  zero           none  none  eu_esi"
      echo "c4_all_eu       policy   side5_lag1_growth1y  zero           none  none  eu_all"
      echo "c5_all_eu_perm  policy   side5_lag1_growth1y  zero           none  none  eu_all_perm"
      ;;
    nl)
      # NL winner: b0_baseline_annual -> baseline wrapper (5 causal lags + zero tensor)
      echo "c0_winner_4e_b  baseline current_clean        zero           none  none  none"
      echo "c1_gdp          baseline current_clean        zero           none  none  eu_gdp"
      echo "c2_labor        baseline current_clean        zero           none  none  eu_labor"
      echo "c3_esi          baseline current_clean        zero           none  none  eu_esi"
      echo "c4_all_eu       baseline current_clean        zero           none  none  eu_all"
      echo "c5_all_eu_perm  baseline current_clean        zero           none  none  eu_all_perm"
      ;;
    be)
      # BE winner: b3_current_clean_zero -> policy, current_clean, zero
      echo "c0_winner_4e_b  policy   current_clean        zero           none  none  none"
      echo "c1_gdp          policy   current_clean        zero           none  none  eu_gdp"
      echo "c2_labor        policy   current_clean        zero           none  none  eu_labor"
      echo "c3_esi          policy   current_clean        zero           none  none  eu_esi"
      echo "c4_all_eu       policy   current_clean        zero           none  none  eu_all"
      echo "c5_all_eu_perm  policy   current_clean        zero           none  none  eu_all_perm"
      ;;
    pt)
      # PT winner: b5_side2_emp_lag1 -> policy, side5_lag1_growth1y, effectifs_lag1, employment eurostat
      local qt_path="data/external/portugal/processed/portugal_qtensor_employment_eurostat_nuts3.csv"
      echo "c0_winner_4e_b  policy   side5_lag1_growth1y  effectifs_lag1 ${qt_path}  jobs  none"
      echo "c1_gdp          policy   side5_lag1_growth1y  effectifs_lag1 ${qt_path}  jobs  eu_gdp"
      echo "c2_labor        policy   side5_lag1_growth1y  effectifs_lag1 ${qt_path}  jobs  eu_labor"
      echo "c3_esi          policy   side5_lag1_growth1y  effectifs_lag1 ${qt_path}  jobs  eu_esi"
      echo "c4_all_eu       policy   side5_lag1_growth1y  effectifs_lag1 ${qt_path}  jobs  eu_all"
      echo "c5_all_eu_perm  policy   side5_lag1_growth1y  effectifs_lag1 ${qt_path}  jobs  eu_all_perm"
      ;;
    *)
      echo "ERROR: unknown country: $country (expected fr|nl|be|pt)" >&2
      return 1
      ;;
  esac
}

export -f phase4e_c_configs
