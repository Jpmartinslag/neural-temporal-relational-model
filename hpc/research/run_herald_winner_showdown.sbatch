#!/bin/bash
#SBATCH --job-name=herald-showdown
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
else
  echo "Missing HPC environment: ${HOME}/venvs/herald-v5-env.sh" >&2
  exit 1
fi

export PYTHON="${PYTHON:-$(command -v python)}"
export SECTION="${SECTION:-phase1}"
export EPOCHS="${EPOCHS:-800}"
export MASK_WARMUP="${MASK_WARMUP:-100}"
export SEEDS_P1="${SEEDS_P1:-0 1 7 13 17 42 77 99 123 200}"
export SEEDS_P2="${SEEDS_P2:-0 1 2 3 7 13 17 21 42 55 77 88 99 100 123 200 256 321 512 2025}"
export OUT_ROOT="hpc_results/herald_showdown_${SLURM_JOB_ID}"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
echo "section=${SECTION}"
echo "epochs=${EPOCHS}"
echo "out_root=${OUT_ROOT}"

# Pre-flight checks
python - <<'PY'
from pathlib import Path
import pandas as pd
import torch

required = [
    "hpc/research/run_herald_winner_showdown.sh",
    "src/modeles/train_herald_semi_v2.py",
    "src/modeles/train_herald_v7.py",
    "src/modeles/train_herald_v6.py",
    "data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv",
    "data/processed/side_creations_a10_ze2020_through_2025_v1.csv",
    "metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv",
]
for f in required:
    p = Path(f)
    ok = p.exists()
    print(f"{'OK' if ok else 'MISSING'} {f} ({p.stat().st_size if ok else 0}B)")
    if not ok:
        raise SystemExit(f"missing: {f}")

panel = pd.read_csv("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
splits = pd.read_csv("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv")
print(f"torch {torch.__version__} | cuda={torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"gpu={torch.cuda.get_device_name(0)}")
print(f"panel {panel.shape} years={sorted(panel.target_year.unique().tolist())}")
print(f"splits eval_years={splits.eval_year.tolist()}")
PY

bash -n hpc/research/run_herald_winner_showdown.sh
python -m py_compile \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_v6.py

PYTHON="${PYTHON}" \
EPOCHS="${EPOCHS}" \
MASK_WARMUP="${MASK_WARMUP}" \
SEEDS_P1="${SEEDS_P1}" \
SEEDS_P2="${SEEDS_P2}" \
OUT_ROOT="${OUT_ROOT}" \
  bash hpc/research/run_herald_winner_showdown.sh "${SECTION}"

echo "results=${OUT_ROOT}"
echo "aggregate_cmd=python hpc/research/aggregate_v7_metrics.py --root ${OUT_ROOT}"
