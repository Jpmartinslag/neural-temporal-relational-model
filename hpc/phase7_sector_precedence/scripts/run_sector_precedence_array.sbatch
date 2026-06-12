#!/bin/bash
#SBATCH --job-name=herald_phase7_sector_precedence
#SBATCH --array=0-709
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --constraint=mpi
#SBATCH --output=/home/jpdark/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/phase7_sector_precedence/logs/task_%06a.out
#SBATCH --error=/home/jpdark/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/phase7_sector_precedence/logs/task_%06a.err
#SBATCH --partition=normal

set -euo pipefail

REPO=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset
PYTHON=/home/jpmartinsd/.conda/envs/herald-v5/bin/python
MANIFEST="${REPO}/hpc/phase7_sector_precedence/configs/task_manifest.json"
PANEL="${REPO}/data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
OUT_DIR="${REPO}/hpc_results/phase7_sector_precedence/raw"
SCRIPT="${REPO}/hpc/phase7_sector_precedence/scripts/run_sector_precedence_task.py"

TASK_ID="${SLURM_ARRAY_TASK_ID}"

mkdir -p "${OUT_DIR}"
mkdir -p "$(dirname "${REPO}/hpc_results/phase7_sector_precedence/logs/placeholder")"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting task ${TASK_ID} on $(hostname)"

"${PYTHON}" "${SCRIPT}" \
    --manifest "${MANIFEST}" \
    --task-id "${TASK_ID}" \
    --panel "${PANEL}" \
    --output-dir "${OUT_DIR}"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) task ${TASK_ID} done"
