#!/bin/bash
#SBATCH --job-name=herald-phase4b
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=05:00:00
#SBATCH --output=logs/%x-%A_%a.out
#SBATCH --error=logs/%x-%A_%a.err

# HERALD Phase 4B — Slurm array job (side5_full feature ablation).
# 1 task = 1 seed, all 3 Phase 4B configs for that country.

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025 3 5 11 19 23 29 31 37 101 303"}
COUNTRY=${COUNTRY:?COUNTRY env var required}
OUT_ROOT=${OUT_ROOT:?OUT_ROOT env var required}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
DEVICE=${DEVICE:-}

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

export PYTHON="${PYTHON:-$(command -v python3)}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "array_task=${IDX}"
echo "country=${COUNTRY}"
echo "seed=${SEED}"
echo "phase=4B (side5_full)"
echo "out_root=${OUT_ROOT}"
date '+start=%Y-%m-%d %H:%M:%S'

python3 - <<PY
import sys
from pathlib import Path
import torch

country = "${COUNTRY}"
base = Path("data/processed/phase4") / country

required = [
    base / "panel_ze2020.csv",
    base / "a10_ze2020.csv",
    base / "splits.csv",
    base / "adj_geo.csv",
    base / "adj_mob.csv",
    Path("hpc/phase4/run_herald_phase4b_seed.sh"),
    Path("hpc/phase4/run_herald_phase4_wrapper.py"),
    Path("hpc/phase4/phase4b_configs.sh"),
    Path("src/modeles/train_herald_regime_experiment.py"),
    Path("src/modeles/train_herald_v6.py"),
    Path("src/modeles/train_herald_v7.py"),
    Path("src/modeles/train_herald_semi_v2.py"),
]
ok = True
for f in required:
    exists = Path(f).exists()
    print(("OK      " if exists else "MISSING ") + str(f))
    if not exists:
        ok = False

# Phase 4B: verify extended columns in panel
import pandas as pd
p = pd.read_csv(base / "panel_ze2020.csv")
missing_cols = [c for c in ["side_lag_2","side_lag_3","growth_2y"] if c not in p.columns]
if missing_cols:
    ok = False
    print(f"MISSING Phase 4B columns: {missing_cols}")
else:
    print(f"Phase 4B columns OK — side_lag_2 non-NaN: {p['side_lag_2'].notna().sum()}/{len(p)}")

if not ok:
    sys.exit("Missing required files — run prepare_phase4_panel.py first")

print(f"torch={torch.__version__} cuda={torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"gpu={torch.cuda.get_device_name(0)}")
PY

bash -n hpc/phase4/run_herald_phase4b_seed.sh
python3 -m py_compile \
  hpc/phase4/run_herald_phase4_wrapper.py \
  hpc/phase4/prepare_phase4_panel.py \
  src/modeles/train_herald_regime_experiment.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_v6.py
echo "compile OK"

SEED="$SEED" \
COUNTRY="$COUNTRY" \
OUT_ROOT="$OUT_ROOT" \
EPOCHS="$EPOCHS" \
MASK_WARMUP="$MASK_WARMUP" \
DEVICE="$DEVICE" \
PYTHON="$PYTHON" \
bash hpc/phase4/run_herald_phase4b_seed.sh

date '+end=%Y-%m-%d %H:%M:%S'
echo "results=${OUT_ROOT}"
