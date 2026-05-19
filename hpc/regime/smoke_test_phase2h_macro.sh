#!/bin/bash
# Smoke for Phase 2H macro features. Requires a macro-augmented panel.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2h_macro_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
DEVICE=${DEVICE:-cpu}

mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,logs,metadata}

"$PYTHON" -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py

"$PYTHON" - <<PY
import pandas as pd
panel = pd.read_csv("${PANEL_PATH}")
required = [
    "fr_climat_affaires_t_minus_1",
    "fr_climat_emploi_t_minus_1",
    "fr_bdf_conj_services_climate_t_minus_1",
    "fr_bdf_gstix_comp_t_minus_1",
]
missing = [c for c in required if c not in panel.columns]
if missing:
    raise SystemExit(f"missing macro columns in ${PANEL_PATH}: {missing}")
print("macro columns OK", panel[required].isna().mean().to_dict())
PY

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
  local feature_policy=$2
  local macro_feature_set=$3
  echo "--- smoke ${label} feature_policy=${feature_policy} macro=${macro_feature_set} ---"
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode no_regime \
    --experiment-label "$label" \
    --feature-policy "$feature_policy" \
    --macro-feature-set "$macro_feature_set" \
    --drop-source-flags \
    --regime-metadata-path "${OUT_SMOKE}/metadata/${label}.json" \
    $(common_args "$label")
}

run_one "best_simplified" "no_flores_no_side_stock_a10" "none"
run_one "best_climat_affaires_emploi" "no_flores_no_side_stock_a10" "climat_affaires_emploi"
run_one "best_bdf_conj_gstix" "no_flores_no_side_stock_a10" "bdf_conj_gstix"
run_one "best_insee_bdf_core" "no_flores_no_side_stock_a10" "insee_bdf_core"

echo "Smoke completed: ${OUT_SMOKE}"
