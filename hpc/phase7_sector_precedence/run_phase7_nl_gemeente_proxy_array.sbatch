#!/bin/bash
#SBATCH --job-name=phase7_nl_gemeente
#SBATCH --array=0-251
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=03:00:00
#SBATCH --output=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/phase7_nl_gemeente_proxy/logs/task_%a.out
#SBATCH --error=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/phase7_nl_gemeente_proxy/logs/task_%a.err
#SBATCH --partition=normal
#SBATCH --constraint=mpi

# DEC-065: Phase 7 sector precedence — NL gemeente proxy (355 gemeenten, proxy_disaggregated_by_stock_share)
# 252 tasks = 14 windows × 2 scenarios × 9 source sectors
# Each task: 8 targets × (999 perms + 500 bootstraps) ~42-53 min/task @ 8G
# evidence_type=proxy_disaggregated_by_stock_share — NOT observed births

set -euo pipefail

REPO=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset
PYTHON=/home/jpmartinsd/.conda/envs/herald-v5/bin/python
PANEL=$REPO/data/processed/phase7_nl_gemeente_proxy/nl_gemeente_phase7_panel.csv
MANIFEST=$REPO/data/processed/phase7_nl_gemeente_proxy/hpc_task_manifest.json
RAW_DIR=$REPO/hpc_results/phase7_nl_gemeente_proxy/raw
LOG_DIR=$REPO/hpc_results/phase7_nl_gemeente_proxy/logs

mkdir -p "$RAW_DIR" "$LOG_DIR"

cd "$REPO"
export PYTHONPATH="$REPO"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting task ${SLURM_ARRAY_TASK_ID} on $(hostname)"

"${PYTHON}" hpc/phase7_sector_precedence/scripts/run_sector_precedence_task.py \
    --manifest "$MANIFEST" \
    --task-id "$SLURM_ARRAY_TASK_ID" \
    --panel "$PANEL" \
    --output-dir "$RAW_DIR"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) task ${SLURM_ARRAY_TASK_ID} done"
