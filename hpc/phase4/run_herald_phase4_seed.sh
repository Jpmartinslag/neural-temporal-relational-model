#!/bin/bash
# Run one HERALD Phase 4 seed for one country (all configs sequentially).
#
# Required env vars:
#   SEED      — integer seed
#   COUNTRY   — nl | be | pt
#   OUT_ROOT  — output directory (must not exist)
#
# Optional:
#   EPOCHS       — training epochs (default 800)
#   MASK_WARMUP  — semi-supervision warmup epochs (default 100)
#   DEVICE       — cpu | cuda (default: auto)
#   PYTHON       — python binary (default: python3)

set -euo pipefail

PYTHON=${PYTHON:-$(command -v python3)}
SEED=${SEED:?SEED is required}
COUNTRY=${COUNTRY:?COUNTRY is required (nl|be|pt)}
OUT_ROOT=${OUT_ROOT:?"OUT_ROOT is required"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
DEVICE=${DEVICE:-}

PHASE4_BASE="data/processed/phase4/${COUNTRY}"
export PHASE4_PANEL="${PHASE4_BASE}/panel_ze2020.csv"
export PHASE4_SPLITS="${PHASE4_BASE}/splits.csv"
export PHASE4_SIDE_A10="${PHASE4_BASE}/a10_ze2020.csv"
export PHASE4_GEO_ADJ="${PHASE4_BASE}/adj_geo.csv"
export PHASE4_MOB_ADJ="${PHASE4_BASE}/adj_mob.csv"
export PHASE4_COUNTRY="$COUNTRY"

case "$COUNTRY" in
  nl)
    export PHASE4_QTENSOR="data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv"
    export PHASE4_QTENSOR_COL="jobs"
    ;;
  be)
    export PHASE4_QTENSOR="data/external/belgium/processed/belgium_qtensor_jobs_panel.csv"
    export PHASE4_QTENSOR_COL="jobs"
    ;;
  pt)
    export PHASE4_QTENSOR="data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv"
    export PHASE4_QTENSOR_COL="births"
    ;;
  *)
    echo "ERROR: unknown country: $COUNTRY" >&2
    exit 1
    ;;
esac

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata}

check_inputs() {
  for f in "$PHASE4_PANEL" "$PHASE4_SPLITS" "$PHASE4_SIDE_A10" \
            "$PHASE4_GEO_ADJ" "$PHASE4_MOB_ADJ" "$PHASE4_QTENSOR"; do
    if [ ! -f "$f" ]; then
      echo "Missing required file: $f" >&2
      echo "Run: python3 hpc/phase4/prepare_phase4_panel.py --country ${COUNTRY}" >&2
      exit 1
    fi
  done
  "$PYTHON" -m py_compile hpc/phase4/run_herald_phase4_wrapper.py
  "$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
}

run_config() {
  local label="$1"
  local feature_policy="$2"
  local qtensor_policy="$3"

  local tag="phase4_${COUNTRY}_${label}"
  local mp="$OUT_ROOT/reports/per_run/${tag}_seed_${SEED}.json"
  local mc="$OUT_ROOT/reports/per_run/${tag}_seed_${SEED}.md"
  local meta="$OUT_ROOT/metadata/${tag}_seed_${SEED}.json"

  for existing in "$mp" "$mc" "$meta"; do
    if [ -e "$existing" ]; then
      echo "Refusing to overwrite: $existing" >&2
      exit 1
    fi
  done

  echo ""
  echo ">> [${COUNTRY}][seed=${SEED}] config=${label} features=${feature_policy} qtensor=${qtensor_policy}  $(date '+%Y-%m-%d %H:%M:%S')"

  local device_arg=()
  if [ -n "$DEVICE" ]; then
    device_arg=(--device "$DEVICE")
  fi

  "$PYTHON" hpc/phase4/run_herald_phase4_wrapper.py \
    --regime-mode no_regime \
    --drop-source-flags \
    --feature-policy "${feature_policy// /}" \
    --macro-feature-set none \
    --quarterly-tensor-policy "${qtensor_policy// /}" \
    --panel-path "$PHASE4_PANEL" \
    --splits-path "$PHASE4_SPLITS" \
    --side-a10-path "$PHASE4_SIDE_A10" \
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$mp" \
    --model-card-path "$mc" \
    --regime-metadata-path "$meta" \
    --experiment-label "${label// /}" \
    --top-k 10 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --sector-lambda 0.2 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --hidden-dim 64 \
    --q-hidden 32 \
    --attn-dim 16 \
    --mode full \
    --v7-variant learned_regime_gate_sector_enhanced \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --rank-lambda 0.02 \
    --smooth-regime-source none \
    --latent-train-mode normal \
    --latent-inference-mode match_train \
    --regime-seq-transform none \
    --semi-warmup-epochs "$MASK_WARMUP" \
    --epochs "$EPOCHS" \
    --latent-regime-dim 5 \
    --auditor-mode none \
    --residual-shrinkage-mode train_opt \
    --residual-shrinkage-value 1.0 \
    --residual-shrinkage-min 0.0 \
    --residual-shrinkage-max 1.25 \
    --tutor-feature-set none \
    --tutor-state-transform none \
    --labor-tutor-feature-set none \
    --labor-tutor-path data/processed/herald_phase3c_labor_tutor_features.csv \
    --seed "$SEED" \
    --run-tag "$tag" \
    "${device_arg[@]+"${device_arg[@]}"}"

  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

echo "============================================================"
echo " HERALD Phase 4 — ${COUNTRY^^} seed battery"
echo " country  : $COUNTRY"
echo " seed     : $SEED"
echo " out_root : $OUT_ROOT"
echo " epochs   : $EPOCHS"
echo " warmup   : $MASK_WARMUP"
echo " device   : ${DEVICE:-auto}"
echo "============================================================"

check_inputs

# shellcheck source=phase4_configs.sh
source "$(dirname "$0")/phase4_configs.sh"

while IFS= read -r line; do
  label=$(echo "$line" | awk '{print $1}')
  feature_policy=$(echo "$line" | awk '{print $2}')
  qtensor_policy=$(echo "$line" | awk '{print $3}')
  run_config "$label" "$feature_policy" "$qtensor_policy"
done < <(phase4_configs)

echo ""
echo "DONE seed=$SEED country=$COUNTRY"
echo "results=$OUT_ROOT"
