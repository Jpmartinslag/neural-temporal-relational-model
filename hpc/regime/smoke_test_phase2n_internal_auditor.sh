#!/bin/bash
# Smoke test for Phase 2N input-conditioned internal auditor.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2n_internal_auditor_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
DEVICE=${DEVICE:-cpu}

if [ -d "$OUT_SMOKE" ]; then
  echo "ERROR: OUT_SMOKE already exists: $OUT_SMOKE" >&2
  exit 1
fi
mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,metadata}

"$PYTHON" -m py_compile \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/aggregate_herald_regime_results.py \
  hpc/regime/audit_herald_phase2n_internal_auditor.py
echo "py_compile OK"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "MISSING input: $f" >&2; exit 1; }
done

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
    --feature-policy side5_lag1_growth1y \
    --macro-feature-set none \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --rank-lambda 0.02 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --semi-warmup-epochs 0 \
    --sector-lambda 0.2 \
    --alpha-smooth-lambda 0.001 \
    --smooth-regime-source none \
    --latent-regime-dim 5 \
    --device "$DEVICE" \
    --seed 0 \
    --single-target-year 2021
}

run_config() {
  local label=$1
  shift
  echo "--- smoke ${label} ---"
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode no_regime \
    --experiment-label "$label" \
    --drop-source-flags \
    --regime-metadata-path "${OUT_SMOKE}/metadata/${label}.json" \
    $(common_args "$label") \
    --run-tag "smoke_${label}" \
    "$@"
}

run_config L3_gate --latent-regime-dim 3 --auditor-mode none
run_config L5_gate_no_auditor --latent-regime-dim 5 --auditor-mode none
run_config AUD_lat_b001 --auditor-mode latent_scale --auditor-budget-lambda 0.001
run_config AUD_alpha_b001 --auditor-mode alpha_neutral --auditor-budget-lambda 0.001
run_config AUD_both_b001_s010 --auditor-mode both --auditor-budget-lambda 0.001 --auditor-smooth-lambda 0.010

"$PYTHON" - <<PY
import json, sys
from pathlib import Path
root = Path("${OUT_SMOKE}") / "reports" / "per_run"
expected = {
    "L3_gate": "none",
    "L5_gate_no_auditor": "none",
    "AUD_lat_b001": "latent_scale",
    "AUD_alpha_b001": "alpha_neutral",
    "AUD_both_b001_s010": "both",
}
errors = []
for label, mode in expected.items():
    p = root / f"{label}.json"
    if not p.exists():
        errors.append(f"missing json: {p}")
        continue
    run = next(iter(json.loads(p.read_text()).values()))
    if run.get("auditor_mode") != mode:
        errors.append(f"{label}: auditor_mode={run.get('auditor_mode')} expected {mode}")
    by_fold = run.get("auditor_confidence_by_fold")
    if not by_fold:
        errors.append(f"{label}: missing auditor_confidence_by_fold")
if errors:
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    sys.exit(1)
print("Phase 2N smoke metadata OK")
PY

echo "Smoke completed: ${OUT_SMOKE}"
