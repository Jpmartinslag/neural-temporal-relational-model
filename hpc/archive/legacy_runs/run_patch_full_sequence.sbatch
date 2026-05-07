#!/bin/bash
#SBATCH --job-name=v6-patch-seq
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=10:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs reports data/processed
source "${HOME}/venvs/herald-v5-env.sh"
export PYTHON="$(command -v python)"

echo "host=$(hostname)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "project=${SLURM_SUBMIT_DIR}"
echo "python=${PYTHON}"
python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
PY

echo "=== Step 1: sector baselines before patch ==="
python scripts/01_sector_baselines.py

echo "=== Step 2: official ridge AR ==="
python scripts/02_ridge_ar_official.py

echo "=== Step 3: HERALD V6 patch section D ==="
bash run_herald_v6_patch.sh D

echo "=== Step 4: select gate ==="
python scripts/03_select_gate.py

SELECTED_GATE="$(awk -F= '/^FINAL_GATE=/{print $2; exit}' reports/FINAL_GATE_SELECTION.txt)"
if [ -z "${SELECTED_GATE}" ]; then
  echo "Could not read FINAL_GATE from reports/FINAL_GATE_SELECTION.txt"
  exit 3
fi

python - <<PY
from pathlib import Path
p = Path("run_herald_v6_patch.sh")
gate = "${SELECTED_GATE}"
text = p.read_text()
lines = []
changed = False
for line in text.splitlines():
    if line.startswith("FINAL_GATE="):
        lines.append(f"FINAL_GATE={gate}   # auto-selected by scripts/03_select_gate.py")
        changed = True
    else:
        lines.append(line)
if not changed:
    raise SystemExit("FINAL_GATE line not found")
p.write_text("\\n".join(lines) + "\\n")
print(f"Updated FINAL_GATE={gate} in {p}")
PY

echo "=== Step 5: HERALD V6 patch section E ==="
bash run_herald_v6_patch.sh E

echo "=== Step 6: sector baselines after final gate ==="
python scripts/01_sector_baselines.py

echo "=== Completed patch full sequence ==="
