#!/bin/bash
# Phase 4E-A2 config definitions.
#
# Purpose: equivalence check against the best Phase 4A country protocol while
# keeping the canonical Phase 4E European panel.
#
# Format:
#   label  feature_policy  qtensor_policy  qtensor_path  qtensor_col
#
# qtensor_path/qtensor_col are "none" unless the country needs a real tensor.

phase4e_a2_configs() {
  local country="${COUNTRY:?COUNTRY env var required (fr|nl|be|pt)}"

  case "$country" in
    fr)
      # Informational France anchor in the international pipeline.
      echo "fr_side2                 side5_lag1_growth1y  zero           none                                                            none"
      ;;
    nl)
      # Phase 4A best: no_qtensor_control = current_clean + zero + identity.
      echo "nl_best4a_current_clean  current_clean        zero           none                                                            none"
      ;;
    be)
      # Phase 4A best: baseline_side2 = lag1 + growth1y + zero + identity.
      echo "be_best4a_side2          side5_lag1_growth1y  zero           none                                                            none"
      ;;
    pt)
      # Phase 4A best: sector_births_lag1 = side2 + births-proxy tensor lag1.
      # This is a strict equivalence test, not the final European employment tensor claim.
      echo "pt_best4a_births_lag1    side5_lag1_growth1y  effectifs_lag1 data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv births"
      ;;
    *)
      echo "ERROR: unknown country: $country (expected fr|nl|be|pt)" >&2
      return 1
      ;;
  esac
}

export -f phase4e_a2_configs
