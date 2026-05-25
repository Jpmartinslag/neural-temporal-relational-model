#!/bin/bash
# Smoke test for Phase 2M latent auto-regulation.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2m_latent_autoreg_smoke_${STAMP}"}
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
  hpc/regime/aggregate_herald_regime_results.py
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

run_config L3_gate --latent-regime-dim 3
run_config HC5_l0_100 --latent-regime-dim 5 --latent-dim-auto-mask --latent-dim-mask-type hard_concrete --latent-dim-l1-lambda 0.100
run_config HC5_l0_050_anneal --latent-regime-dim 5 --latent-dim-auto-mask --latent-dim-mask-type hard_concrete --latent-dim-l1-lambda 0.050 --latent-dim-beta-start 0.6666667 --latent-dim-beta-end 0.3333333
run_config GL5_020 --latent-regime-dim 5 --latent-group-lasso-lambda 0.020
run_config CD5_kl_001 --latent-regime-dim 5 --latent-dim-auto-mask --latent-dim-mask-type concrete_dropout --latent-dim-l1-lambda 0.001 --latent-dim-beta-start 0.6666667 --latent-dim-beta-end 0.3333333

"$PYTHON" - <<PY
import json, sys
from pathlib import Path
root = Path("${OUT_SMOKE}") / "reports" / "per_run"
expected = {
    "L3_gate": False,
    "HC5_l0_100": True,
    "HC5_l0_050_anneal": True,
    "GL5_020": False,
    "CD5_kl_001": True,
}
errors = []
for label, has_mask in expected.items():
    p = root / f"{label}.json"
    if not p.exists():
        errors.append(f"missing json: {p}")
        continue
    run = next(iter(json.loads(p.read_text()).values()))
    if run.get("latent_dim_auto_mask") != has_mask:
        errors.append(f"{label}: auto_mask={run.get('latent_dim_auto_mask')} expected {has_mask}")
    if "latent_group_norm_values" not in run:
        errors.append(f"{label}: missing latent_group_norm_values")
    if has_mask and not run.get("latent_dim_mask_values"):
        errors.append(f"{label}: missing mask values")
if errors:
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    sys.exit(1)
print("Phase 2M smoke metadata OK")
PY

echo "Smoke completed: ${OUT_SMOKE}"
