#!/bin/bash
#SBATCH --job-name=phase7_pt_muni
#SBATCH --array=0-207
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=hpc_results/phase7_pt_municipal/logs/task_%a.out
#SBATCH --error=hpc_results/phase7_pt_municipal/logs/task_%a.err
#SBATCH --partition=normal
#SBATCH --constraint=mpi

# DEC-064: Phase 7 sector precedence — PT municipal (278 municipalities, observed_births)
# 208 tasks = 13 windows × 2 scenarios × 8 source sectors
# Each task: 7 targets × (999 perms + 500 bootstraps) ~30 min/task @ 8G

set -euo pipefail

REPO="${REPO_ROOT:?set REPO_ROOT to the repository root}"
PYTHON="${PYTHON:-python3}"
PANEL=$REPO/data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv
MANIFEST=$REPO/data/processed/phase7_pt_municipal/hpc_task_manifest.json
RAW_DIR=$REPO/hpc_results/phase7_pt_municipal/raw
RESULTS_DIR=$REPO/data/processed/phase7_pt_municipal/results

mkdir -p "$RAW_DIR" "$RESULTS_DIR" "$REPO/hpc_results/phase7_pt_municipal/logs"

cd "$REPO"
export PYTHONPATH="$REPO"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting task ${SLURM_ARRAY_TASK_ID} on $(hostname)"

"${PYTHON}" hpc/phase7_sector_precedence/scripts/run_sector_precedence_task.py \
    --manifest "$MANIFEST" \
    --task-id "$SLURM_ARRAY_TASK_ID" \
    --panel "$PANEL" \
    --output-dir "$RAW_DIR"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) task ${SLURM_ARRAY_TASK_ID} done"
