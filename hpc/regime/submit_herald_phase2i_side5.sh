#!/bin/bash
# HERALD Phase 2I SIDE5 audit — safe preflight + submit.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
REGIME_PLAN=phase2i_side5_audit
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase2i_side5_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}

EXPECTED_CONFIGS=9
N_SEEDS=$(echo "$SEEDS" | wc -w)
EXPECTED=$((EXPECTED_CONFIGS * N_SEEDS))

echo "========================================================"
echo " HERALD Phase 2I — SIDE5 Preflight + Submit"
echo " plan     : $REGIME_PLAN"
echo " out_root : $OUT_ROOT"
echo " panel    : $PANEL_PATH"
echo " seeds    : $SEEDS"
echo " epochs   : $EPOCHS"
echo " warmup   : $MASK_WARMUP"
echo " expected : $EXPECTED runs ($EXPECTED_CONFIGS configs × $N_SEEDS seeds)"
echo " device   : ${DEVICE:-auto}"
echo "========================================================"

if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi

bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/run_herald_regime_array.sbatch
bash -n hpc/regime/submit_herald_phase2i_side5.sh
bash -n hpc/regime/smoke_test_phase2i_side5.sh
echo "bash -n syntax checks OK"

python3 -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/aggregate_herald_regime_results.py \
  hpc/regime/audit_herald_phase2i_side5_plan.py
echo "py_compile OK"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "ERROR missing input: $f" >&2; exit 1; }
done
echo "input files OK"

source hpc/regime/regime_plan_configs.sh
N_CONFIGS=$(REGIME_PLAN="$REGIME_PLAN" plan_configs | wc -l)
N_RUNS=$((N_CONFIGS * N_SEEDS))
echo "configs=$N_CONFIGS seeds=$N_SEEDS runs=$N_RUNS expected=$EXPECTED"
if [ "$N_RUNS" -ne "$EXPECTED" ]; then
  echo "ERROR: expected $EXPECTED runs, got $N_RUNS" >&2
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
echo "tag uniqueness OK ($N_CONFIGS unique tags)"

python3 hpc/regime/audit_herald_phase2i_side5_plan.py
echo "feature policy audit OK"

mkdir -p "${OUT_ROOT}"/{reports/per_run,data_processed,logs,metadata}

ARRAY_MAX=$((N_SEEDS - 1))
sbatch \
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
  --export=ALL,OUT_ROOT="${OUT_ROOT}",SEEDS="${SEEDS}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",REGIME_PLAN="${REGIME_PLAN}",DEVICE="${DEVICE}",PANEL_PATH="${PANEL_PATH}",SPLITS_PATH="${SPLITS_PATH}",SIDE_A10_PATH="${SIDE_A10_PATH}" \
  hpc/regime/run_herald_regime_array.sbatch

echo "Submitted. Monitor: squeue -u \$USER"
echo "Results: ${OUT_ROOT}"
