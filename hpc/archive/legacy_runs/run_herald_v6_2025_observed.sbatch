#!/bin/bash
#SBATCH --job-name=v6-obs2025
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs reports/figures hpc_results
source "${HOME}/venvs/herald-v5-env.sh"

export PYTHON="$(command -v python)"
export EPOCHS="${EPOCHS:-800}"
export RUN_TAG="${RUN_TAG:-observed2025_geo2025}"
export OUTPUT_ROOT="hpc_results/herald_v6_${RUN_TAG}_${SLURM_JOB_ID}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "epochs=${EPOCHS}"
echo "run_tag=${RUN_TAG}"
echo "output_root=${OUTPUT_ROOT}"

python - <<'PY'
import pandas as pd
import torch

panel = pd.read_csv("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
splits = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv")
a10 = pd.read_csv("data/processed/side_creations_a10_ze2020_through_2025_v1.csv")

print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
print("panel_years", int(panel.target_year.min()), int(panel.target_year.max()))
print("panel_rows", len(panel), "zones", panel.ZE2020.nunique())
print("rows_2025", int((panel.target_year == 2025).sum()))
print("target_2025_sum", int(panel.loc[panel.target_year == 2025, "side_establishment_creations_official"].sum()))
print("splits", splits.eval_year.tolist())
print("a10_rows_2025", int((a10.target_year == 2025).sum()))
PY

PYTHON="${PYTHON}" RUN_TAG="${RUN_TAG}" OUTPUT_ROOT="${OUTPUT_ROOT}" \
  bash run_herald_v6_2025_observed.sh full

python src/data/plot_herald_v6_2025_dashboard.py \
  --hpc-path "${OUTPUT_ROOT}" \
  --out "${OUTPUT_ROOT}/reports/figures/herald_v6_observed2025_geo2025_dashboard_v1.html"

echo "dashboard=${OUTPUT_ROOT}/reports/figures/herald_v6_observed2025_geo2025_dashboard_v1.html"
