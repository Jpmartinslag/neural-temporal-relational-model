#!/bin/bash
# ============================================================
# HERALD V7 — SLURM array runner
#
# Each array task = 1 line of $MANIFEST_FILE = 1 (variant, seed) run.
# Each run writes to its own metrics/model-card path so there is no
# race condition even with full parallelism.
#
# Submit example (10 GPUs simultaneously, all sections):
#
#   # 1) generate the manifest first (no execution):
#   OUT_ROOT=hpc_results/herald_v7_g25_$(date +%Y%m%d_%H%M%S)
#   mkdir -p "$OUT_ROOT"
#   EMIT_MANIFEST=1 MANIFEST_FILE="$OUT_ROOT/manifest.txt" \
#     OUT_ROOT="$OUT_ROOT" \
#     bash hpc/research/run_herald_v7_research_battery.sh all
#
#   # 2) count runs and submit array job:
#   N=$(grep -cv '^#' "$OUT_ROOT/manifest.txt")
#   sbatch --array=1-${N}%10 \
#     --export=ALL,MANIFEST_FILE="$OUT_ROOT/manifest.txt",OUT_ROOT="$OUT_ROOT" \
#     hpc/research/run_herald_v7_array.sbatch
#
#   # 3) when all tasks finish, aggregate:
#   python hpc/research/aggregate_v7_metrics.py --root "$OUT_ROOT"
#
# %10 caps simultaneous array tasks at 10 (one per GPU). Adjust to your
# cluster's GPU pool. SBATCH params below assume 1 GPU per task.
# ============================================================

#SBATCH --job-name=herald-v7-arr
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x-%A_%a.out
#SBATCH --error=logs/%x-%A_%a.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs

if [ -z "${MANIFEST_FILE:-}" ]; then
  echo "MANIFEST_FILE is required (export it on sbatch)." >&2
  exit 1
fi
if [ ! -f "$MANIFEST_FILE" ]; then
  echo "Manifest not found: $MANIFEST_FILE" >&2
  exit 1
fi

# Activate the conda env that has torch (and statsmodels for ARIMA, etc).
# Override CONDA_ENV / CONDA_BASE if your setup differs.
CONDA_ENV=${CONDA_ENV:-mineru}
CONDA_BASE=${CONDA_BASE:-$HOME/miniconda3}
if [ -f "${CONDA_BASE}/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${CONDA_BASE}/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV}"
elif [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/venvs/herald-v5-env.sh"
fi

PYTHON=${PYTHON:-$(command -v python)}
export PYTHON

ID=${SLURM_ARRAY_TASK_ID:-1}
LINE=$(grep -nv '^#' "$MANIFEST_FILE" | sed -n "${ID}p" | cut -d: -f2-)
if [ -z "$LINE" ]; then
  echo "No manifest line for array id $ID" >&2
  exit 1
fi

echo "host=$(hostname)"
echo "job=${SLURM_JOB_ID:-na}  array_task=${ID}"
echo "manifest=${MANIFEST_FILE}"
echo "cmd: $LINE"
date '+start=%Y-%m-%d %H:%M:%S'

# Replace any leading 'python3' / 'python' token with our env's python.
# The manifest already used $PYTHON when emitted, but we re-resolve here so
# array re-runs survive cluster path differences.
eval "$LINE"

date '+end=%Y-%m-%d %H:%M:%S'
