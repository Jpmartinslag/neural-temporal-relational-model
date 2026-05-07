#!/bin/bash
#SBATCH --job-name=semi-total-g25
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=4-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
else
  echo "Missing HPC environment file: ${HOME}/venvs/herald-v5-env.sh"
  exit 1
fi

export PYTHON="${PYTHON:-$(command -v python)}"
export SECTION="${SECTION:-all}"
export EPOCHS="${EPOCHS:-800}"
export MASK_WARMUP="${MASK_WARMUP:-100}"
export SEEDS="${SEEDS:-0 1 7 13 17 42 77 99 123 2025}"
export CLASSICAL_MODELS="${CLASSICAL_MODELS:-naive_lag1 ridge_ar arima_local}"
export OUT_ROOT="hpc_results/herald_semi_total_geo2025_${SLURM_JOB_ID}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "section=${SECTION}"
echo "epochs=${EPOCHS}"
echo "mask_warmup=${MASK_WARMUP}"
echo "seeds=${SEEDS}"
echo "classical_models=${CLASSICAL_MODELS}"
echo "out_root=${OUT_ROOT}"

python - <<'PY'
from pathlib import Path
import pandas as pd
import torch
import statsmodels

required = [
    "run_herald_semi_total_geo2025.sh",
    "scripts/summarize_herald_semi_total.py",
    "src/data/train_herald_v3.py",
    "src/data/train_herald_v6.py",
    "src/data/train_herald_semi_v1.py",
    "src/data/train_temporal_baselines_v1.py",
    "src/data/train_dynamic_stgnn_models_v1.py",
    "data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv",
    "data/processed/side_creations_a10_ze2020_through_2025_v1.csv",
    "metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv",
    "metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv",
    "data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv",
    "data/processed/graph_adjacency_core_v0.csv",
    "data/processed/graph_adjacency_mobility_v0.csv",
]
for item in required:
    path = Path(item)
    print(item, path.exists(), path.stat().st_size if path.exists() else 0)
    if not path.exists():
        raise SystemExit(f"missing required file: {item}")

panel = pd.read_csv("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
splits = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv")
pre = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv")
a10 = pd.read_csv("data/processed/side_creations_a10_ze2020_through_2025_v1.csv")

print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("statsmodels", statsmodels.__version__)
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
print("panel", panel.shape, int(panel.target_year.min()), int(panel.target_year.max()), panel.ZE2020.nunique())
print("target_2025_sum", int(panel.loc[panel.target_year == 2025, "side_establishment_creations_official"].sum()))
print("splits", splits.eval_year.tolist())
print("precovid_splits", pre.eval_year.tolist())
print("a10_rows_2025", int((a10.target_year == 2025).sum()))
print("expected_herald_semi_runs", 210)
print("expected_baseline_model_runs", 43)
print("expected_total_model_runs", 253)
PY

bash -n run_herald_semi_total_geo2025.sh
python -m py_compile \
  src/data/train_herald_v3.py \
  src/data/train_herald_v6.py \
  src/data/train_herald_semi_v1.py \
  src/data/train_temporal_baselines_v1.py \
  src/data/train_dynamic_stgnn_models_v1.py \
  scripts/summarize_herald_semi_total.py

PYTHON="${PYTHON}" EPOCHS="${EPOCHS}" MASK_WARMUP="${MASK_WARMUP}" SEEDS="${SEEDS}" CLASSICAL_MODELS="${CLASSICAL_MODELS}" OUT_ROOT="${OUT_ROOT}" \
  bash run_herald_semi_total_geo2025.sh "${SECTION}"

python scripts/summarize_herald_semi_total.py "${OUT_ROOT}"

echo "results=${OUT_ROOT}"
echo "summary=${OUT_ROOT}/reports/HERALD_SEMI_TOTAL_SUMMARY.md"
echo "v3_metrics=${OUT_ROOT}/reports/herald_v3_total_metrics_v1.json"
echo "v6_metrics=${OUT_ROOT}/reports/herald_v6_total_metrics_v1.json"
echo "semi_metrics=${OUT_ROOT}/reports/herald_semi_total_metrics_v1.json"
echo "semi_precovid_metrics=${OUT_ROOT}/reports/herald_semi_total_precovid_metrics_v1.json"
