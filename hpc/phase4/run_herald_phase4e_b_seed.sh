#!/bin/bash
# Run one HERALD Phase 4E-B seed for one country.

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
OUT_ROOT=${OUT_ROOT:?OUT_ROOT is required}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
DEVICE=${DEVICE:-}

PHASE4E_BASE="data/processed/phase4e/${COUNTRY}"
export PHASE4E_PHASE="4E-B"
export PHASE4E_COUNTRY="$COUNTRY"
export PHASE4E_PANEL="${PHASE4E_BASE}/panel_ze2020.csv"
export PHASE4E_SPLITS="${PHASE4E_BASE}/splits.csv"
export PHASE4E_SIDE_A10="${PHASE4E_BASE}/a10_ze2020.csv"
export PHASE4E_GEO_ADJ="${PHASE4E_BASE}/adj_geo.csv"
export PHASE4E_MOB_ADJ="${PHASE4E_BASE}/adj_mob.csv"

mkdir -p "$OUT_ROOT"/{reports/per_run,reports/sector,data_processed,logs,metadata}

for f in "$PHASE4E_PANEL" "$PHASE4E_SPLITS" "$PHASE4E_SIDE_A10" "$PHASE4E_GEO_ADJ" "$PHASE4E_MOB_ADJ"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: missing file: $f" >&2
    exit 1
  fi
done

run_config() {
  local label="$1"
  local wrapper_type="$2"
  local feature_policy="$3"
  local qtensor_policy="$4"
  local qtensor_path="$5"
  local qtensor_col="$6"

  local run_tag="phase4e_b_${COUNTRY}_${label}"
  local out_json="${OUT_ROOT}/reports/per_run/${run_tag}_seed_${SEED}.json"
  local out_md="${OUT_ROOT}/reports/per_run/${run_tag}_seed_${SEED}.md"
  local meta_path="${OUT_ROOT}/metadata/${run_tag}_seed_${SEED}.json"

  for existing in "$out_json" "$out_md" "$meta_path"; do
    if [ -e "$existing" ]; then
      echo "Refusing to overwrite: $existing" >&2
      exit 1
    fi
  done

  if [ "$qtensor_path" != "none" ] && [ ! -f "$qtensor_path" ]; then
    echo "ERROR: missing qtensor file: $qtensor_path" >&2
    exit 1
  fi

  echo ">> [${COUNTRY}][seed=${SEED}] label=${label} wrapper=${wrapper_type} features=${feature_policy} qtensor=${qtensor_policy}"

  local wrapper="hpc/phase4/run_herald_phase4e_a2_wrapper.py"
  local feature_arg="$feature_policy"
  local tensor_arg="$qtensor_policy"
  if [ "$wrapper_type" = "baseline" ]; then
    wrapper="hpc/phase4/run_herald_phase4e_a_wrapper.py"
    feature_arg="current_clean"
    tensor_arg="zero"
  elif [ "$wrapper_type" != "policy" ]; then
    echo "ERROR: unknown wrapper_type=${wrapper_type}" >&2
    exit 1
  fi

  PHASE4E_CONFIG_LABEL="$label" \
  PHASE4E_FEATURE_POLICY="$feature_policy" \
  PHASE4E_TENSOR_POLICY="$qtensor_policy" \
  PHASE4E_QTENSOR="$qtensor_path" \
  PHASE4E_QTENSOR_COL="$qtensor_col" \
  "$PYTHON" "$wrapper" \
    --regime-mode no_regime \
    --drop-source-flags \
    --quarterly-tensor-policy "$tensor_arg" \
    --feature-policy "$feature_arg" \
    --macro-feature-set none \
    --experiment-label "$label" \
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
    --prediction-output-dir "$OUT_ROOT/data_processed" \
    --metrics-path "$out_json" \
    --model-card-path "$out_md" \
    --semi-warmup-epochs "$MASK_WARMUP" \
    --epochs "$EPOCHS" \
    --seed "$SEED" \
    --run-tag "$run_tag" \
    ${DEVICE:+--device "$DEVICE"}

  echo "   done: $out_json"
}

source hpc/phase4/phase4e_b_configs.sh

while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  label=$(echo "$line" | awk '{print $1}')
  wrapper_type=$(echo "$line" | awk '{print $2}')
  feature_policy=$(echo "$line" | awk '{print $3}')
  qtensor_policy=$(echo "$line" | awk '{print $4}')
  qtensor_path=$(echo "$line" | awk '{print $5}')
  qtensor_col=$(echo "$line" | awk '{print $6}')
  run_config "$label" "$wrapper_type" "$feature_policy" "$qtensor_policy" "$qtensor_path" "$qtensor_col"
done < <(phase4e_b_configs)
