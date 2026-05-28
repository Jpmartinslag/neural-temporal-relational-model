#!/bin/bash
# HERALD Phase 3B tutor-signal screen.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
REGIME_PLAN=phase3b_tutor_signal_screen
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase3b_tutor_signal_screen_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
EXPECTED_CONFIGS=11

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

python3 - <<'PY'
import pandas as pd
from pathlib import Path

panel = Path("data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv")
required = {
    "fr_climat_affaires_t_minus_1",
    "fr_climat_emploi_t_minus_1",
    "fr_bdf_conj_services_climate_t_minus_1",
    "fr_bdf_gstix_comp_t_minus_1",
}
df = pd.read_csv(panel, nrows=10)
missing = sorted(required - set(df.columns))
if missing:
    raise SystemExit(f"missing tutor columns in {panel}: {missing}")
print("tutor signal columns OK")
PY

source hpc/regime/submit_herald_phase_template.sh
