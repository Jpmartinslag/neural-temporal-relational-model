#!/bin/bash
# Run one HERALD Phase 4E-A seed for one country.
# Phase 4E-A: sanity check — European canonical panel vs Phase 4A.
#
# Required env vars:
#   SEED      — integer seed
#   COUNTRY   — fr | nl | be | pt
#   OUT_ROOT  — output directory
#
# Optional:
#   EPOCHS       — training epochs (default 800)
#   MASK_WARMUP  — semi-supervision warmup (default 100)
#   DEVICE       — cpu | cuda (default: auto)
#   PYTHON       — python binary (default: python3)

set -euo pipefail

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

PYTHON=${PYTHON:-$(command -v python3)}
SEED=${SEED:?SEED is required}
COUNTRY=${COUNTRY:?COUNTRY is required (fr|nl|be|pt)}
OUT_ROOT=${OUT_ROOT:?"OUT_ROOT is required"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
DEVICE=${DEVICE:-}

PHASE4E_BASE="data/processed/phase4e/${COUNTRY}"

export PHASE4E_COUNTRY="$COUNTRY"
export PHASE4E_PANEL="${PHASE4E_BASE}/panel_ze2020.csv"
export PHASE4E_SPLITS="${PHASE4E_BASE}/splits.csv"
export PHASE4E_SIDE_A10="${PHASE4E_BASE}/a10_ze2020.csv"
export PHASE4E_GEO_ADJ="${PHASE4E_BASE}/adj_geo.csv"
export PHASE4E_MOB_ADJ="${PHASE4E_BASE}/adj_mob.csv"

mkdir -p "$OUT_ROOT"/{reports/per_run,reports/sector,data_processed,logs,metadata}

check_inputs() {
  for f in "$PHASE4E_PANEL" "$PHASE4E_SPLITS" "$PHASE4E_SIDE_A10" \
            "$PHASE4E_GEO_ADJ" "$PHASE4E_MOB_ADJ"; do
    if [ ! -f "$f" ]; then
      echo "ERROR: Missing required file: $f" >&2
      echo "Run: python3 hpc/phase4/prepare_phase4e_panel.py --country ${COUNTRY}" >&2
      exit 1
    fi
  done
}

run_config() {
  local label="$1"
  local qtensor_policy="$2"

  local run_tag="phase4e_a_${COUNTRY}_${label}"
  local out_json="${OUT_ROOT}/reports/per_run/${run_tag}_seed_${SEED}.json"
  local out_md="${OUT_ROOT}/reports/per_run/${run_tag}_seed_${SEED}.md"
  local meta_path="${OUT_ROOT}/metadata/${run_tag}_seed_${SEED}.json"
  local pred_dir="${OUT_ROOT}/data_processed"

  echo ">> [${COUNTRY}][seed=${SEED}] config=${label} qtensor=${qtensor_policy}  $(date '+%Y-%m-%d %H:%M:%S')"

  PHASE4E_CONFIG_LABEL="$label" \
  PHASE4_TENSOR_POLICY="$qtensor_policy" \
  "$PYTHON" hpc/phase4/run_herald_phase4e_a_wrapper.py \
    --regime-mode no_regime \
    --quarterly-tensor-policy "${qtensor_policy}" \
    --feature-policy current_clean \
    --macro-feature-set none \
    --experiment-label "${label}" \
    --regime-metadata-path "$meta_path" \
    --mode full \
    --v7-variant learned_regime_gate_sector_enhanced \
    --smooth-regime-source none \
    --latent-train-mode normal \
    --latent-inference-mode match_train \
    --regime-seq-transform none \
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
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --rank-lambda 0.02 \
    --latent-regime-dim 5 \
    --auditor-mode none \
    --residual-shrinkage-mode train_opt \
    --residual-shrinkage-value 1.0 \
    --residual-shrinkage-min 0.0 \
    --residual-shrinkage-max 1.25 \
    --tutor-feature-set none \
    --tutor-state-transform none \
    --panel-path "$PHASE4E_PANEL" \
    --splits-path "$PHASE4E_SPLITS" \
    --side-a10-path "$PHASE4E_SIDE_A10" \
    --prediction-output-dir "$pred_dir" \
    --metrics-path "$out_json" \
    --model-card-path "$out_md" \
    --semi-warmup-epochs "$MASK_WARMUP" \
    --epochs "$EPOCHS" \
    --seed "$SEED" \
    --run-tag "$run_tag" \
    ${DEVICE:+--device "$DEVICE"}

  echo "   done: $out_json"
}

source hpc/phase4/phase4e_a_configs.sh

echo "=== Phase 4E-A [${COUNTRY}] seed=${SEED}  $(date '+%Y-%m-%d %H:%M:%S') ==="
check_inputs

while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  label=$(echo "$line" | awk '{print $1}')
  qtensor_policy=$(echo "$line" | awk '{print $2}')
  run_config "$label" "$qtensor_policy"
done < <(phase4e_a_configs)

echo "=== Phase 4E-A [${COUNTRY}] seed=${SEED} complete  $(date '+%Y-%m-%d %H:%M:%S') ==="
