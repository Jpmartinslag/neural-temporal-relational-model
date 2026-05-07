#!/bin/bash
#SBATCH --job-name=geo2025-cmp
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=1-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results reports/figures
source "${HOME}/venvs/herald-v5-env.sh"

export PYTHON="$(command -v python)"
export EPOCHS="${EPOCHS:-800}"
export RUN_TAG="${RUN_TAG:-final_geo2025_gate2.0}"
export OUT_ROOT="hpc_results/final_model_comparison_geo2025_${SLURM_JOB_ID}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "epochs=${EPOCHS}"
echo "run_tag=${RUN_TAG}"
echo "out_root=${OUT_ROOT}"

python - <<'PY'
import pandas as pd
import statsmodels
import sklearn
import torch

panel = pd.read_csv("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
splits = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv")
a10 = pd.read_csv("data/processed/side_creations_a10_ze2020_through_2025_v1.csv")
q = pd.read_csv("data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv")

print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
print("sklearn", sklearn.__version__)
print("statsmodels", statsmodels.__version__)
print("panel_years", int(panel.target_year.min()), int(panel.target_year.max()))
print("panel_rows", len(panel), "zones", panel.ZE2020.nunique())
print("rows_2025", int((panel.target_year == 2025).sum()))
print("target_2025_sum", int(panel.loc[panel.target_year == 2025, "side_establishment_creations_official"].sum()))
print("splits", splits.eval_year.tolist())
print("a10_rows_2025", int((a10.target_year == 2025).sum()))
print("urssaf_rows", len(q))
PY

bash -n run_final_model_comparison_geo2025.sh
python -m py_compile \
  src/data/train_temporal_baselines_v1.py \
  src/data/train_dynamic_stgnn_models_v1.py \
  src/data/train_herald_v3.py \
  src/data/train_herald_v6.py \
  src/data/plot_herald_v3_v6_dashboard.py \
  src/data/plot_herald_v6_2025_dashboard.py

PYTHON="${PYTHON}" RUN_TAG="${RUN_TAG}" OUT_ROOT="${OUT_ROOT}" \
  bash run_final_model_comparison_geo2025.sh all

echo "results=${OUT_ROOT}"
echo "comparison_dashboard=${OUT_ROOT}/reports/figures/final_model_comparison_geo2025_dashboard_v1.html"
echo "v6_dashboard=${OUT_ROOT}/reports/figures/herald_v6_observed2025_geo2025_dashboard_v1.html"
