#!/bin/bash
# HERALD Phase 2J fair flag comparison — safe preflight + submit.
#
# Compares HERALD no-flags (SIDE2 clean) vs HERALD with-flags (SIDE2 clean)
# using the same input set for both: side_lag_1 + growth_1y only.
#
# 2 configs × 10 seeds = 20 runs, one SLURM array task per seed.
# Each task runs both configs sequentially within the same GPU allocation.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
REGIME_PLAN=phase2j_fair_flag
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase2j_fair_flag_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}

EXPECTED_CONFIGS=2
N_SEEDS=$(echo "$SEEDS" | wc -w)
EXPECTED=$((EXPECTED_CONFIGS * N_SEEDS))

echo "========================================================"
echo " HERALD Phase 2J — fair flag comparison"
echo " plan     : $REGIME_PLAN"
echo " out_root : $OUT_ROOT"
echo " panel    : $PANEL_PATH"
echo " seeds    : $SEEDS"
echo " epochs   : $EPOCHS"
echo " warmup   : $MASK_WARMUP"
echo " expected : $EXPECTED runs ($EXPECTED_CONFIGS configs × $N_SEEDS seeds)"
echo " device   : ${DEVICE:-auto}"
echo ""
echo " Variants:"
echo "   lag1_growth1y_nf    : no_regime + learned_regime_gate_sector_enhanced"
echo "                         (no is_covid_year, no is_post_covid_rebound)"
echo "   lag1_growth1y_flags : manual_flags + full"
echo "                         (is_covid_year + is_post_covid_rebound in inputs)"
echo " Common inputs: side_lag_1, growth_1y — no flores, no side_stock,"
echo "                no source flags, no macro"
echo "========================================================"

# Anti-overwrite: OUT_ROOT must not exist.
if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  echo "       Use a different STAMP or OUT_ROOT to avoid overwriting results." >&2
  exit 1
fi

# Syntax checks.
bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/run_herald_regime_array.sbatch
bash -n hpc/regime/submit_herald_phase2j_fair_flag.sh
bash -n hpc/regime/smoke_test_phase2j_fair_flag.sh
echo "bash -n syntax checks OK"

# Python compile checks.
python3 -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/aggregate_herald_regime_results.py \
  hpc/regime/audit_herald_phase2j_fair_flag.py
echo "py_compile OK"

# Input files.
for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "ERROR missing input: $f" >&2; exit 1; }
done
echo "input files OK"

# Config count.
source hpc/regime/regime_plan_configs.sh
N_CONFIGS=$(REGIME_PLAN="$REGIME_PLAN" plan_configs | wc -l)
N_RUNS=$((N_CONFIGS * N_SEEDS))
echo "configs=$N_CONFIGS seeds=$N_SEEDS runs=$N_RUNS expected=$EXPECTED"
if [ "$N_RUNS" -ne "$EXPECTED" ]; then
  echo "ERROR: expected $EXPECTED runs, got $N_RUNS" >&2
  exit 1
fi

# Tag uniqueness within Phase 2J.
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

# Preflight feature audit.
python3 hpc/regime/audit_herald_phase2j_fair_flag.py
echo "feature policy audit OK"

# Anti-overwrite: check that existing Phase 2I results won't be touched.
PHASE2I_ROOT="hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1"
if [ -d "$PHASE2I_ROOT" ]; then
  echo "Phase 2I results exist at $PHASE2I_ROOT — Phase 2J uses separate OUT_ROOT, no collision."
fi

mkdir -p "${OUT_ROOT}"/{reports/per_run,data_processed,logs,metadata}

ARRAY_MAX=$((N_SEEDS - 1))
JOB_ID=$(sbatch --parsable \
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
  --export=ALL,OUT_ROOT="${OUT_ROOT}",SEEDS="${SEEDS}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",REGIME_PLAN="${REGIME_PLAN}",DEVICE="${DEVICE}",PANEL_PATH="${PANEL_PATH}",SPLITS_PATH="${SPLITS_PATH}",SIDE_A10_PATH="${SIDE_A10_PATH}" \
  hpc/regime/run_herald_regime_array.sbatch)

echo ""
echo "========================================================"
echo " Submitted Phase 2J"
echo " Job ID   : ${JOB_ID}"
echo " OUT_ROOT : ${OUT_ROOT}"
echo " Array    : 0-${ARRAY_MAX}%${MAX_PARALLEL}  (one task per seed)"
echo " Runs     : ${EXPECTED} total (${N_CONFIGS} configs × ${N_SEEDS} seeds)"
echo "========================================================"
echo ""
echo "Monitor:"
echo "  squeue -u \$USER"
echo "  sacct -j ${JOB_ID} --format=JobID,JobName%40,State,ExitCode,Elapsed"
echo "  tail -f ${OUT_ROOT}/logs/*.out"
echo ""
echo "Recover results:"
echo "  rsync -av meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/${OUT_ROOT}/ ${OUT_ROOT}/"
echo ""
echo "Aggregate after completion:"
echo "  python3 hpc/regime/aggregate_herald_regime_results.py --root ${OUT_ROOT}"
echo ""
echo "Final audit:"
echo "  python3 hpc/regime/audit_herald_phase2j_fair_flag.py"
