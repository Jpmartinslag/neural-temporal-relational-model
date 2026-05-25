#!/bin/bash
# Shared submit body for late HERALD regime phases.
#
# This file is sourced by phase-specific submit scripts after they define:
#   REGIME_PLAN OUT_ROOT EXPECTED_CONFIGS SEEDS EPOCHS MASK_WARMUP MAX_PARALLEL
#   PANEL_PATH SPLITS_PATH SIDE_A10_PATH
set -euo pipefail

N_SEEDS=$(echo "$SEEDS" | wc -w)
EXPECTED=$((EXPECTED_CONFIGS * N_SEEDS))
EXCLUDE_NODE=${EXCLUDE_NODE:-hpcgpu02}

echo "========================================================"
echo " HERALD ${REGIME_PLAN}"
echo " out_root : $OUT_ROOT"
echo " expected : $EXPECTED runs ($EXPECTED_CONFIGS configs × $N_SEEDS seeds)"
echo " seeds    : $SEEDS"
echo " epochs   : $EPOCHS"
echo " exclude  : ${EXCLUDE_NODE:-none}"
echo "========================================================"

if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi

bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/run_herald_regime_array.sbatch
bash -n hpc/regime/submit_herald_phase_template.sh
echo "bash -n OK"

python3 -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/aggregate_herald_regime_results.py
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

mkdir -p "${OUT_ROOT}"/{reports/per_run,data_processed,logs,metadata}

ARRAY_MAX=$((N_SEEDS - 1))
SBATCH_ARGS=(--parsable --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}")
if [ -n "${EXCLUDE_NODE:-}" ]; then
  SBATCH_ARGS+=(--exclude="${EXCLUDE_NODE}")
fi
SBATCH_ARGS+=(--export=ALL,OUT_ROOT="${OUT_ROOT}",SEEDS="${SEEDS}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",REGIME_PLAN="${REGIME_PLAN}",DEVICE="${DEVICE}",PANEL_PATH="${PANEL_PATH}",SPLITS_PATH="${SPLITS_PATH}",SIDE_A10_PATH="${SIDE_A10_PATH}")

JOB_ID=$(sbatch "${SBATCH_ARGS[@]}" hpc/regime/run_herald_regime_array.sbatch)

echo ""
echo "Submitted ${REGIME_PLAN}"
echo "Job ID   : ${JOB_ID}"
echo "OUT_ROOT : ${OUT_ROOT}"
echo "Runs     : ${EXPECTED}"
echo ""
echo "Monitor:"
echo "  squeue -u \$USER"
echo "  sacct -j ${JOB_ID} --format=JobID,JobName%40,State,ExitCode,Elapsed"
echo "  find ${OUT_ROOT}/reports/per_run -name '*.json' | wc -l"
echo "  tail -f ${OUT_ROOT}/logs/*.out"
echo ""
echo "Aggregate:"
echo "  python3 hpc/regime/aggregate_herald_regime_results.py --root ${OUT_ROOT}"
