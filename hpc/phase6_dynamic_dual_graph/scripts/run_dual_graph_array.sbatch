#!/bin/bash
#SBATCH --job-name=ddeg_s1
#SBATCH --array=0-274%20
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --constraint=mpi
#SBATCH --output=hpc_results/dual_graph_s1/logs/ddeg_%A_%a.out
#SBATCH --error=hpc_results/dual_graph_s1/logs/ddeg_%A_%a.err

# P6_DDEG_S1 — Dynamic Dual Economic Graph — HPC array
# 5 folds × 11 controls × 5 seeds = 275 jobs
# Run from repo root: sbatch hpc/phase6_dynamic_dual_graph/scripts/run_dual_graph_array.sbatch

set -euo pipefail

# SLURM_SUBMIT_DIR is the directory from which sbatch was called (the repo root).
REPO="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
cd "$REPO"

# ── Python (discover in priority order) ────────────────────────────────────
if [ -x "$HOME/.conda/envs/herald-v5/bin/python" ]; then
    PYTHON="$HOME/.conda/envs/herald-v5/bin/python"
elif [ -x "$HOME/miniconda3/envs/mlearning/bin/python" ]; then
    PYTHON="$HOME/miniconda3/envs/mlearning/bin/python"
elif [ -x "$HOME/anaconda3/envs/mlearning/bin/python" ]; then
    PYTHON="$HOME/anaconda3/envs/mlearning/bin/python"
else
    PYTHON="$(command -v python3)"
fi

echo "==== DDEG_S1 task=${SLURM_ARRAY_TASK_ID} job=${SLURM_JOB_ID} ===="
echo "host=$(hostname)  python=$PYTHON"
echo "repo=$REPO"

# ── thread limits (CPU-only, no GPU requested) ─────────────────────────────
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# ── create log dir before Slurm writes to it ──────────────────────────────
mkdir -p "$REPO/hpc_results/dual_graph_s1/logs"

# ── run single task ────────────────────────────────────────────────────────
PYTHONPATH="$REPO" "$PYTHON" \
    hpc/phase6_dynamic_dual_graph/scripts/run_dual_graph_task.py \
    --out-root "$REPO/hpc_results/dual_graph_s1"

echo "==== task=${SLURM_ARRAY_TASK_ID} EXIT $? ===="
