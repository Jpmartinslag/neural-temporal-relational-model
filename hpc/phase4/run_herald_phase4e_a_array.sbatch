#!/bin/bash
#SBATCH --job-name=herald-phase4ea
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=3:00:00
#SBATCH --output=logs/%x-%A_%a.out
#SBATCH --error=logs/%x-%A_%a.err

# HERALD Phase 4E-A — Slurm array job.
# 1 task = 1 seed × 1 config (baseline_annual) per country.
# Phase 4E-A runs 1 config only → ~30-60 min per seed → 3h has generous margin.

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs hpc_results

SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
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
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

echo "Phase 4E-A [${COUNTRY}] seed=${SEED}  node=$(hostname)  $(date '+%Y-%m-%d %H:%M:%S')"

# Python preflight: verify phase4e panels exist
python3 - <<'PYEOF'
import sys, os
from pathlib import Path
base = Path(os.environ.get("SLURM_SUBMIT_DIR", "."))
country = os.environ["COUNTRY"]
p4e = base / f"data/processed/phase4e/{country}"
required = ["panel_ze2020.csv", "splits.csv", "a10_ze2020.csv", "adj_geo.csv", "adj_mob.csv"]
missing = [f for f in required if not (p4e / f).exists()]
if missing:
    print(f"PREFLIGHT FAIL [{country.upper()}]: Phase 4E panel missing: {missing}", file=sys.stderr)
    print(f"Run: python3 hpc/phase4/prepare_phase4e_panel.py --country {country}", file=sys.stderr)
    sys.exit(1)
print(f"Preflight OK [{country.upper()}]: Phase 4E-A panel files present")
PYEOF

SEED="$SEED" \
COUNTRY="$COUNTRY" \
OUT_ROOT="$OUT_ROOT" \
EPOCHS="$EPOCHS" \
MASK_WARMUP="$MASK_WARMUP" \
${DEVICE:+DEVICE="$DEVICE"} \
bash hpc/phase4/run_herald_phase4e_a_seed.sh

echo "Phase 4E-A [${COUNTRY}] seed=${SEED} finished  $(date '+%Y-%m-%d %H:%M:%S')"
