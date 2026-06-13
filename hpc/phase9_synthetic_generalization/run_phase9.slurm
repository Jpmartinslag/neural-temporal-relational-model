#!/bin/bash
#SBATCH --job-name=herald_phase9_synth
#SBATCH --output=hpc/phase9_synthetic_generalization/logs/phase9_%A_%a.out
#SBATCH --error=hpc/phase9_synthetic_generalization/logs/phase9_%A_%a.err
#SBATCH --array=0-19
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:45:00
#SBATCH --partition=cpu

# ──────────────────────────────────────────────────────────────────────────────
# HERALD Phase 9 — Synthetic Benchmark (DEC-040)
#
# Array: 20 tasks (4 scenarios × 5 seeds)
# Each task: 12 models × 9 mask combos (3 types × 3 levels)
#
# Prerequisites (mandatory before submission):
#   1. Local pilot PASS (6/6 tasks, no NaN, leakage=True)
#   2. All 86 tests PASS
#   3. Cluster smoke PASS (--task-id 0 --n-epochs 50)
#
# Do NOT submit without explicit authorisation.
# Do NOT adjust gate thresholds after results are observed.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Environment ───────────────────────────────────────────────────────────────
PROJECT_ROOT="${PROJECT_ROOT:-$HOME/project_recomm/dataset}"
OUTPUT_DIR="${PROJECT_ROOT}/data/processed/synthetic_benchmark/full"
LOG_DIR="${PROJECT_ROOT}/hpc/phase9_synthetic_generalization/logs"
N_EPOCHS=500

cd "${PROJECT_ROOT}"
mkdir -p "${OUTPUT_DIR}" "${LOG_DIR}"

# ── Python environment ────────────────────────────────────────────────────────
# Adjust to match cluster setup:
#   conda: source activate herald_env
#   venv:  source .venv/bin/activate
#   module: module load python/3.10
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate herald_env 2>/dev/null || true
fi

# ── Task dispatch ─────────────────────────────────────────────────────────────
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID}"
echo "NODE=$(hostname)"
echo "START=$(date -Iseconds)"

python src/modeles/synthetic/run_full_benchmark.py \
    --task-id "${SLURM_ARRAY_TASK_ID}" \
    --output-dir "${OUTPUT_DIR}" \
    --n-epochs "${N_EPOCHS}" \
    --confirm-full-run

EXIT_CODE=$?
echo "END=$(date -Iseconds)"
echo "EXIT_CODE=${EXIT_CODE}"

if [ "${EXIT_CODE}" -ne 0 ]; then
    echo "ERROR: task ${SLURM_ARRAY_TASK_ID} failed with exit code ${EXIT_CODE}" >&2
    exit "${EXIT_CODE}"
fi

# ── Post-task gate check (informational only, not fail-stop per task) ─────────
# The full gate evaluation runs post-hoc once all 20 tasks complete.
echo "Task ${SLURM_ARRAY_TASK_ID} completed successfully."
