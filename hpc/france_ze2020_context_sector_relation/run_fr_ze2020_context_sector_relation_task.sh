#!/bin/bash
# France ZE2020 context-conditioned sector-relation gate, one seed per task.

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_context_sector_relation_${RUN_ID}/seed_${SEED}"
MAX_EPOCHS="${FR_ZE2020_CONTEXT_RELATION_MAX_EPOCHS:-500}"
EVAL_YEARS="${FR_ZE2020_CONTEXT_RELATION_EVAL_YEARS:-2019 2020 2021 2022 2023 2024 2025}"
FOLDS="${FR_ZE2020_CONTEXT_RELATION_FOLDS:-0 1 2 3 4}"

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

required_files=(
  src/modeles/france_ze2020/run_fr_ze2020_context_conditioned_sector_relation_gate.py
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
)
for path in "${required_files[@]}"; do
  if [[ ! -f "${path}" ]]; then
    echo "ERROR: required file not found: ${path}" >&2
    exit 1
  fi
done

echo "France ZE2020 context-conditioned sector-relation gate"
echo "RUN_ID=${RUN_ID} SEED=${SEED} MAX_EPOCHS=${MAX_EPOCHS}"
echo "EVAL_YEARS=${EVAL_YEARS} FOLDS=${FOLDS}"
"${PYTHON}" -c "import numpy, pandas, sklearn; print(f'numpy={numpy.__version__} pandas={pandas.__version__} sklearn={sklearn.__version__}')"

"${PYTHON}" src/modeles/france_ze2020/run_fr_ze2020_context_conditioned_sector_relation_gate.py \
  --output-dir "${OUTDIR}" \
  --eval-years ${EVAL_YEARS} \
  --seeds "${SEED}" \
  --folds ${FOLDS} \
  --max-epochs "${MAX_EPOCHS}"

echo "Task complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
