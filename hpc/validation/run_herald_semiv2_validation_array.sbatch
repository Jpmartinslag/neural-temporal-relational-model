#!/bin/bash
#SBATCH --job-name=herald-semiv2-val
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x-%A_%a.out
#SBATCH --error=logs/%x-%A_%a.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_semiv2_validation_${SLURM_JOB_ID}"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}

read -r -a SEED_ARRAY <<< "$SEEDS"
IDX=${SLURM_ARRAY_TASK_ID:-0}
if [ "$IDX" -ge "${#SEED_ARRAY[@]}" ]; then
  echo "Array index ${IDX} outside SEEDS length ${#SEED_ARRAY[@]}" >&2
  exit 1
fi
SEED=${SEED_ARRAY[$IDX]}

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
else
  echo "No known HERALD Python environment found." >&2
  exit 1
fi

export PYTHON="${PYTHON:-$(command -v python)}"
export SEED
export OUT_ROOT
export EPOCHS
export MASK_WARMUP
export RUN_GLOBAL=0
if [ "$IDX" = "0" ]; then
  export RUN_GLOBAL=1
fi

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "array_task=${IDX}"
echo "seed=${SEED}"
echo "out_root=${OUT_ROOT}"
echo "python=${PYTHON}"
echo "epochs=${EPOCHS}"
echo "run_global=${RUN_GLOBAL}"
date '+start=%Y-%m-%d %H:%M:%S'

python - <<'PY'
from pathlib import Path
import pandas as pd
import torch

required = [
    "hpc/validation/run_herald_semiv2_validation_seed.sh",
    "src/modeles/train_temporal_baselines_v1.py",
    "src/modeles/train_dynamic_stgnn_models_v1.py",
    "src/modeles/sector_baselines_v1.py",
    "src/modeles/train_herald_v6.py",
    "src/modeles/train_herald_v7.py",
    "src/modeles/train_herald_semi_v2.py",
    "data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv",
    "metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv",
    "data/processed/side_creations_a10_ze2020_through_2025_v1.csv",
]
for f in required:
    p = Path(f)
    print(("OK      " if p.exists() else "MISSING ") + f)
    if not p.exists():
        raise SystemExit(f"missing: {f}")
panel = pd.read_csv("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
splits = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv")
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"gpu={torch.cuda.get_device_name(0)}")
print(f"panel_shape={panel.shape}")
print(f"years={sorted(panel.target_year.unique().tolist())}")
print(f"eval_years={splits.eval_year.tolist()}")
if sorted(splits.eval_year.tolist()) != [2021, 2022, 2023, 2024, 2025]:
    raise SystemExit("Unexpected eval years; expected 2021-2025.")
PY

bash -n hpc/validation/run_herald_semiv2_validation_seed.sh
python -m py_compile \
  src/modeles/train_temporal_baselines_v1.py \
  src/modeles/train_dynamic_stgnn_models_v1.py \
  src/modeles/sector_baselines_v1.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py

bash hpc/validation/run_herald_semiv2_validation_seed.sh

date '+end=%Y-%m-%d %H:%M:%S'
echo "results=${OUT_ROOT}"
