#!/bin/bash
# CPU smoke for Phase 3 tutor-gate Block A.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase3_tutor_gate_block_a_smoke_${STAMP}"}

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

export PYTHON="${PYTHON:-$(command -v python3)}"

SEED=0 \
REGIME_PLAN=phase3_tutor_gate_block_a \
EPOCHS=${EPOCHS:-1} \
MASK_WARMUP=0 \
DEVICE=${DEVICE:-cpu} \
OUT_ROOT="$OUT_SMOKE" \
PANEL_PATH=${PANEL_PATH:-data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv} \
bash hpc/regime/run_herald_regime_seed.sh

expected=5
actual=$(find "$OUT_SMOKE/reports/per_run" -name '*.json' | wc -l)
if [ "$actual" -ne "$expected" ]; then
  echo "ERROR: expected ${expected} smoke JSONs, got ${actual}" >&2
  exit 1
fi

python3 - <<PY
import json
from pathlib import Path
root = Path("${OUT_SMOKE}")
for path in sorted((root / "reports/per_run").glob("*.json")):
    payload = json.loads(path.read_text())
    result = next(iter(payload.values()))
    label = result.get("run_tag", "")
    if "T5" in label or "T6" in label or "T2" in label:
        cols = result.get("tutor_columns", [])
        if not cols:
            raise SystemExit(f"missing tutor columns in {path}")
print("phase3 tutor smoke OK")
PY
