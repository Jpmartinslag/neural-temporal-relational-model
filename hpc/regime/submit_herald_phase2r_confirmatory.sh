#!/bin/bash
# HERALD Phase 2R confirmatory battery — safe preflight + submit.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
REGIME_PLAN=phase2r_confirmatory
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase2r_confirmatory_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025 2026 2027 2028 2029 2030 2031 2032 2033 2034 2035"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
EXPECTED_CONFIGS=13

source hpc/regime/submit_herald_phase_template.sh
