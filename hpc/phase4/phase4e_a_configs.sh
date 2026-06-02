#!/bin/bash
# Phase 4E-A config definitions — one config per country.
#
# Format: label  qtensor_policy
# (no graph_file field — always identity, handled by seed script)
#
# Phase 4E-A purpose: sanity check that European canonical panel
# reproduces Phase 4A without architectural changes.
# - Features: BASELINE_ANNUAL_FEATURES only (lag1/2/3, growth_1y/2y)
# - No COVID/rebound flags as input (NON_PREDICTIVE_FIELDS excluded by wrapper)
# - No tensor
# - Identity graph

phase4e_a_configs() {
  echo "baseline_annual  zero"
}

export -f phase4e_a_configs
