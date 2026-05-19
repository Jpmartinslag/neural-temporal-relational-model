#!/bin/bash
# ============================================================
# HERALD Phase 2D stability battery — submit script with safe preflight.
#
# Usage (from project root on HPC):
#   bash hpc/regime/submit_herald_phase2d_stability.sh
#
# Remote (from local machine):
#   ssh meso-direct "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
#     bash hpc/regime/submit_herald_phase2d_stability.sh"
#
# IMPORTANT: run smoke test first:
#   bash hpc/regime/smoke_test_phase2d.sh
#
# Preflight guarantee: this script never executes model training.
# plan_configs() is loaded from regime_plan_configs.sh which contains
# only the function definition — no training or I/O code.
# ============================================================
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase2d_stability_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}
REGIME_PLAN="phase2d_stability"

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}

echo "========================================================"
echo " HERALD Phase 2D — Preflight + Submit"
echo " plan     : $REGIME_PLAN"
echo " out_root : $OUT_ROOT"
echo " seeds    : $SEEDS"
echo " epochs   : $EPOCHS"
echo " warmup   : $MASK_WARMUP"
echo " device   : ${DEVICE:-auto}"
echo "========================================================"

# ---- 1. preflight: OUT_ROOT must be unique (no overwrite) ----
echo ""
echo "[preflight] Checking OUT_ROOT uniqueness..."
if [ -d "$OUT_ROOT" ]; then
    echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
    echo "       Set STAMP or OUT_ROOT to a new unique value." >&2
    exit 1
fi
echo "  OK: $OUT_ROOT does not exist yet"

# ---- 2. preflight: syntax checks (safe, no training) ----
echo "[preflight] Syntax checking shell scripts..."
bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/run_herald_regime_array.sbatch
echo "  OK: shell syntax"

echo "[preflight] Compiling Python sources..."
python3 -m py_compile \
    src/modeles/herald_regime_modes.py \
    src/modeles/train_herald_v7.py \
    src/modeles/train_herald_semi_v2.py \
    src/modeles/train_herald_regime_experiment.py \
    hpc/regime/aggregate_herald_regime_results.py \
    hpc/regime/audit_herald_phase2d_stability.py
echo "  OK: all sources compile"

# ---- 3. preflight: ruptures HARD FAIL (PELT modes require it) ----
echo "[preflight] Checking ruptures (required for D2a/D2b PELT configs)..."
if ! python3 -c "import ruptures" 2>/dev/null; then
    echo "ERROR: ruptures is not installed." >&2
    echo "       Phase 2D includes D2a_pelt3 and D2b_pelt5 which require ruptures." >&2
    echo "       Install with: pip install ruptures" >&2
    exit 1
fi
python3 -c "import ruptures; print('  OK: ruptures', ruptures.__version__)"

# ---- 4. preflight: list 12 configs × 10 seeds = 120 runs ----
echo "[preflight] Listing configs from regime_plan_configs.sh (no training)..."

# Source ONLY the plan function file — safe, contains no execution code.
# shellcheck source=regime_plan_configs.sh
source hpc/regime/regime_plan_configs.sh

N_EXPECTED=120
N_SEEDS=$(echo "$SEEDS" | wc -w)
N_CONFIGS=$(REGIME_PLAN="$REGIME_PLAN" plan_configs | wc -l)
N_RUNS=$((N_CONFIGS * N_SEEDS))

echo "  Configs : $N_CONFIGS"
echo "  Seeds   : $N_SEEDS ($SEEDS)"
echo "  Runs    : $N_RUNS (expected $N_EXPECTED)"

if [ "$N_RUNS" -ne "$N_EXPECTED" ]; then
    echo "ERROR: expected $N_EXPECTED runs but plan × seeds = $N_RUNS" >&2
    exit 1
fi
echo "  OK: $N_EXPECTED runs confirmed"

# ---- 5. preflight: verify run tags are unique ----
echo "[preflight] Verifying run tag uniqueness..."
declare -A SEEN_TAGS
DUPLICATE=0
while IFS= read -r line; do
    read -r mode variant source_policy label rest <<< "$line"
    tag="regime_${mode}"
    [ "$variant" != "full" ] && tag="${tag}_${variant}"
    echo "$source_policy" | grep -q "no_source" && tag="${tag}_no_source_flags"
    [ "${label:-base}" != "base" ] && tag="${tag}_${label}"
    if [ "${SEEN_TAGS[$tag]+_}" ]; then
        echo "  ERROR: duplicate tag: $tag" >&2
        DUPLICATE=1
    fi
    SEEN_TAGS[$tag]=1
done < <(REGIME_PLAN="$REGIME_PLAN" plan_configs)

if [ "$DUPLICATE" -eq 1 ]; then
    echo "ERROR: duplicate run tags detected" >&2
    exit 1
fi
echo "  OK: all $N_CONFIGS tags unique"

# ---- 6. create OUT_ROOT dirs ----
mkdir -p "${OUT_ROOT}"/{reports/per_run,data_processed,logs,metadata}

# ---- 7. submit SLURM array ----
echo ""
echo "[submit] Submitting SLURM array..."
N_SEEDS_COUNT=$(echo "$SEEDS" | wc -w)
ARRAY_MAX=$((N_SEEDS_COUNT - 1))

sbatch \
    --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
    --export=ALL,OUT_ROOT="${OUT_ROOT}",SEEDS="${SEEDS}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",REGIME_PLAN="${REGIME_PLAN}",DEVICE="${DEVICE}",PANEL_PATH="${PANEL_PATH}",SPLITS_PATH="${SPLITS_PATH}",SIDE_A10_PATH="${SIDE_A10_PATH}" \
    hpc/regime/run_herald_regime_array.sbatch

echo ""
echo "========================================================"
echo " Submitted. Monitor:"
echo "   squeue -u \$USER"
echo "   tail -f logs/herald-regime-<JOBID>_0.out"
echo ""
echo " After all jobs complete (ExitCode 0:0):"
echo "   python3 hpc/regime/aggregate_herald_regime_results.py \\"
echo "     --root ${OUT_ROOT}"
echo "   python3 hpc/regime/audit_herald_phase2d_stability.py \\"
echo "     --root ${OUT_ROOT}"
echo "========================================================"
