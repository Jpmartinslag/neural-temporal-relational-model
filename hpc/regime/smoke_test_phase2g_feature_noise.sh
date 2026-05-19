#!/bin/bash
# CPU/GPU smoke for Phase 2G feature-noise ablations.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2g_feature_noise_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
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
  echo "--- smoke ${label} feature_policy=${feature_policy} ---"
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode no_regime \
    --experiment-label "$label" \
    --feature-policy "$feature_policy" \
    --drop-source-flags \
    --regime-metadata-path "${OUT_SMOKE}/metadata/${label}.json" \
    $(common_args "$label")
}

run_one "current_clean" "current_clean"
run_one "no_urssaf" "no_urssaf"
run_one "minimal_side_only" "minimal_side_only"

"$PYTHON" - <<PY
import json
from pathlib import Path
root = Path("${OUT_SMOKE}") / "metadata"
expected = {
    "current_clean": (False, 20),
    "no_urssaf": (True, 20),
    "minimal_side_only": (True, 5),
}
for label, (qzero, nfeat) in expected.items():
    data = json.loads((root / f"{label}.json").read_text())
    assert data["feature_policy"] == label, data
    assert data["quarterly_tensor_zeroed"] is qzero, data
    assert data["annual_feature_count"] == nfeat, data
print("feature-policy metadata OK")
PY

echo "Smoke completed: ${OUT_SMOKE}"
