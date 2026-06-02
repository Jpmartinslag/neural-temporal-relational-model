#!/bin/bash
# Phase 4B config registry — extended AR features (side5_full).
#
# Phase 4A showed identity adjacency disables graph smoothing; feature gap
# (only lag_1 + growth_1y vs France's 5 AR features) is the tractable lever
# without adjacency shapefiles.
#
# Phase 4B tests whether adding lag_2, lag_3, growth_2y improves forecasts.
#
# 3 configs × 20 seeds = 60 runs per country:
#   side5_full_no_tensor      — all 5 AR features, no tensor
#   side5_full_tensor_lag1    — all 5 AR features + tensor lag1 (effectifs_lag1)
#   side5_full_tensor_lag2    — all 5 AR features + tensor lag2 (2-year shift)
#
# qtensor_policy: zero | effectifs_lag1 | lag2
#   lag2: shifts tensor 2 years back (uses ty-3 data for predicting ty)
#
# Usage:
#   COUNTRY=nl source hpc/phase4/phase4b_configs.sh && phase4b_configs
#   COUNTRY=be source hpc/phase4/phase4b_configs.sh && phase4b_configs
#   COUNTRY=pt source hpc/phase4/phase4b_configs.sh && phase4b_configs

phase4b_configs() {
  local country="${COUNTRY:?COUNTRY env var required (nl|be|pt)}"

  case "$country" in
    nl|be)
      # Config 1: side5_full, no tensor — pure AR feature enrichment
      echo "side5_full_no_tensor      side5_full  zero"
      # Config 2: side5_full + employment tensor lag1
      echo "side5_full_tensor_lag1    side5_full  effectifs_lag1"
      # Config 3: side5_full + employment tensor lag2 (2-year shift)
      echo "side5_full_tensor_lag2    side5_full  lag2"
      ;;
    pt)
      # Config 1: side5_full, no tensor
      echo "side5_full_no_tensor      side5_full  zero"
      # Config 2: side5_full + sector_births tensor lag1 (⚠️ proxy)
      echo "side5_full_tensor_lag1    side5_full  effectifs_lag1"
      # Config 3: side5_full + sector_births tensor lag2
      echo "side5_full_tensor_lag2    side5_full  lag2"
      ;;
    *)
      echo "ERROR: unknown country: $country (expected nl|be|pt)" >&2
      return 1
      ;;
  esac
}

phase4b_n_configs() {
  local country="${COUNTRY:?}"
  case "$country" in
    nl|be|pt) echo 3 ;;
    *) echo 0 ;;
  esac
}
