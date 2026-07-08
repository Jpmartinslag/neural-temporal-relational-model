#!/bin/bash
# HERALD -- France ZE2020 top-3 entry falsification HPC task.

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"
: "${SCENARIO:?SCENARIO must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_top3_entry_${RUN_ID}/${SCENARIO}/seed_${SEED}"
MAX_EPOCHS="${FR_ZE2020_TOP3_ENTRY_MAX_EPOCHS:-120}"
EVAL_YEARS="${FR_ZE2020_TOP3_ENTRY_EVAL_YEARS:-2017 2018 2019 2020 2021 2022}"
FEATURE_CONFIGS="${FR_ZE2020_TOP3_ENTRY_FEATURE_CONFIGS:-no_relation_features base_formula_features shuffled_relation_features}"

echo "=========================================="
echo "HERALD France ZE2020 top-3 entry falsification"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "RUN_ID=${RUN_ID}"
echo "SCENARIO=${SCENARIO}"
echo "SEED=${SEED}"
echo "OUTDIR=${OUTDIR}"
echo "MAX_EPOCHS=${MAX_EPOCHS}"
echo "EVAL_YEARS=${EVAL_YEARS}"
echo "FEATURE_CONFIGS=${FEATURE_CONFIGS}"
echo "=========================================="

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

required_files=(
  src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py
  src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py
  src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py
  src/modeles/france_ze2020/train_fr_ze2020_sector_ranking.py
  data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
)
for path in "${required_files[@]}"; do
  if [[ ! -f "${path}" ]]; then
    echo "ERROR: required file not found: ${path}" >&2
    exit 1
  fi
done

"${PYTHON}" -c "import sklearn, pandas, numpy; print(f'sklearn={sklearn.__version__} pandas={pandas.__version__} numpy={numpy.__version__}')"

"${PYTHON}" - <<'PYEOF'
import sys
forbidden = ("dynamic_stgnn_feature_panel", "graph_adjacency_core_v0", "graph_adjacency_mobility_v0")
scripts = [
    "src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py",
    "src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py",
    "src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py",
    "src/modeles/france_ze2020/train_fr_ze2020_sector_ranking.py",
]
failed = False
for path in scripts:
    lines = open(path).read().splitlines()
    executable_lines = [line for line in lines if "read_csv" in line or "Path(" in line or "RANKING_PANEL_PATH" in line]
    code_only = "\n".join(executable_lines)
    for term in forbidden:
        if term in code_only:
            print(f"FORBIDDEN SOURCE '{term}' referenced in executable code of {path}", file=sys.stderr)
            failed = True
if failed:
    sys.exit(1)
print("Forbidden-source check: PASS")
PYEOF

"${PYTHON}" - <<'PYEOF'
import pandas as pd
path = "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"
df = pd.read_csv(path, dtype={"ze2020": str}, nrows=5)
required = {
    "ze2020",
    "sector_code",
    "decision_year",
    "future_growth_3y",
    "sector_rank_in_ze_year_t",
    "ranking_feature_complete",
}
missing = required - set(df.columns)
if missing:
    raise SystemExit(f"Top-3 entry panel schema missing columns: {sorted(missing)}")
print(f"Top-3 entry panel read-only validation: PASS ({path})")
PYEOF

"${PYTHON}" src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py \
  --output-dir "${OUTDIR}" \
  --target-horizon 3 \
  --eval-years ${EVAL_YEARS} \
  --seeds "${SEED}" \
  --scenarios "${SCENARIO}" \
  --feature-configs ${FEATURE_CONFIGS} \
  --max-epochs "${MAX_EPOCHS}"

echo "Top-3 entry falsification task complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Outputs in ${OUTDIR}"
