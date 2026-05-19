#!/bin/bash
# HERALD Phase 2E residual/rebound battery — safe preflight + submit.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase2e_residual_rebound_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}
REGIME_PLAN="phase2e_residual_rebound"

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}

echo "========================================================"
echo " HERALD Phase 2E — Preflight + Submit"
echo " plan     : $REGIME_PLAN"
echo " out_root : $OUT_ROOT"
echo " seeds    : $SEEDS"
echo " epochs   : $EPOCHS"
echo " warmup   : $MASK_WARMUP"
echo " device   : ${DEVICE:-auto}"
echo "========================================================"

if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi

bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/run_herald_regime_array.sbatch

python3 -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/aggregate_herald_regime_results.py

python3 -c "import ruptures; print('ruptures OK', ruptures.__version__)"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "ERROR missing input: $f" >&2; exit 1; }
done

source hpc/regime/regime_plan_configs.sh
N_EXPECTED=110
N_SEEDS=$(echo "$SEEDS" | wc -w)
N_CONFIGS=$(REGIME_PLAN="$REGIME_PLAN" plan_configs | wc -l)
N_RUNS=$((N_CONFIGS * N_SEEDS))
echo "configs=$N_CONFIGS seeds=$N_SEEDS runs=$N_RUNS expected=$N_EXPECTED"
if [ "$N_RUNS" -ne "$N_EXPECTED" ]; then
  echo "ERROR: expected $N_EXPECTED runs, got $N_RUNS" >&2
  exit 1
fi

declare -A SEEN_TAGS
while IFS= read -r line; do
  read -r mode variant source_policy label rest <<< "$line"
  tag="regime_${mode}"
  [ "$variant" != "full" ] && tag="${tag}_${variant}"
  echo "$source_policy" | grep -q "no_source" && tag="${tag}_no_source_flags"
  [ "${label:-base}" != "base" ] && tag="${tag}_${label}"
  if [ "${SEEN_TAGS[$tag]+_}" ]; then
    echo "ERROR duplicate tag: $tag" >&2
    exit 1
  fi
  SEEN_TAGS[$tag]=1
done < <(REGIME_PLAN="$REGIME_PLAN" plan_configs)
echo "tag uniqueness OK"

mkdir -p "${OUT_ROOT}"/{reports/per_run,data_processed,logs,metadata}

N_SEEDS_COUNT=$(echo "$SEEDS" | wc -w)
ARRAY_MAX=$((N_SEEDS_COUNT - 1))
sbatch \
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
  --export=ALL,OUT_ROOT="${OUT_ROOT}",SEEDS="${SEEDS}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",REGIME_PLAN="${REGIME_PLAN}",DEVICE="${DEVICE}",PANEL_PATH="${PANEL_PATH}",SPLITS_PATH="${SPLITS_PATH}",SIDE_A10_PATH="${SIDE_A10_PATH}" \
  hpc/regime/run_herald_regime_array.sbatch

echo "Submitted. Monitor: squeue -u \$USER"
echo "Results: ${OUT_ROOT}"
