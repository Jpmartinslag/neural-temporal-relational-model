#!/bin/bash
#SBATCH --job-name=phase7_pt_muni
#SBATCH --array=0-207
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=hpc_results/phase7_pt_municipal/logs/task_%a.log
#SBATCH --error=hpc_results/phase7_pt_municipal/logs/task_%a.err
#SBATCH --partition=cpu

# DEC-064: Phase 7 sector precedence — PT municipal (278 municipalities, observed_births)
# 208 tasks = 13 windows × 2 scenarios × 8 source sectors
# Each task: 7 targets × (999 perms + 500 bootstraps) ~30 min/task @ 4G

set -euo pipefail

REPO=/home/jpdark/Downloads/project_recomm/dataset
PANEL=$REPO/data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv
MANIFEST=$REPO/data/processed/phase7_pt_municipal/hpc_task_manifest.json
RAW_DIR=$REPO/hpc_results/phase7_pt_municipal/raw
RESULTS_DIR=$REPO/data/processed/phase7_pt_municipal/results

mkdir -p "$RAW_DIR" "$RESULTS_DIR" "$REPO/hpc_results/phase7_pt_municipal/logs"

cd "$REPO"
export PYTHONPATH="$REPO"

python hpc/phase7_sector_precedence/scripts/run_sector_precedence_task.py \
    --manifest "$MANIFEST" \
    --task-id "$SLURM_ARRAY_TASK_ID" \
    --panel "$PANEL" \
    --output-dir "$RAW_DIR"

echo "Task $SLURM_ARRAY_TASK_ID complete."
