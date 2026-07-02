#!/bin/bash
# HERALD -- France ZE2020 dynamic graph falsification HPC task, one seed.

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_dynamic_graph_falsifications_${RUN_ID}/seed_${SEED}"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
MAX_EPOCHS="${FR_ZE2020_DYNAMIC_GRAPH_MAX_EPOCHS:-250}"
TARGET_HORIZON="${FR_ZE2020_DYNAMIC_GRAPH_TARGET_HORIZON:-1}"
EDGES_PATH="${FR_ZE2020_DYNAMIC_GRAPH_EDGES:-data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv}"
if [[ "${TARGET_HORIZON}" == "1" ]]; then
  DEFAULT_EVAL_YEARS="2017 2018 2019 2020 2021 2022 2023 2024"
else
  DEFAULT_EVAL_YEARS="2018 2019 2020 2021 2022"
fi
EVAL_YEARS="${FR_ZE2020_DYNAMIC_GRAPH_EVAL_YEARS:-${DEFAULT_EVAL_YEARS}}"
SCENARIOS="${FR_ZE2020_DYNAMIC_GRAPH_FALSIFICATION_SCENARIOS:-full_control no_edges random_edge_weights random_edge_targets no_cross_ze_same_sector no_intra_ze_sector no_ze_similarity temporal_shuffle sector_shuffle}"

echo "=========================================="
echo "HERALD France ZE2020 dynamic graph falsifications -- seed ${SEED}"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "RUN_ID=${RUN_ID} OUTDIR=${OUTDIR}"
echo "EDGES_PATH=${EDGES_PATH}"
echo "=========================================="

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

"${PYTHON}" -c "import sklearn, pandas, numpy; print(f'sklearn={sklearn.__version__} pandas={pandas.__version__} numpy={numpy.__version__}')"

"${PYTHON}" - <<'PYEOF'
import sys
forbidden = ("dynamic_stgnn_feature_panel", "graph_adjacency_core_v0", "graph_adjacency_mobility_v0")
scripts = [
    "src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py",
    "src/modeles/france_ze2020/run_fr_ze2020_dynamic_graph_falsifications.py",
]
failed = False
for path in scripts:
    source_lines = open(path).read().splitlines()
    read_lines = [line for line in source_lines if "read_csv" in line or "Path(" in line or " / " in line]
    code_only = "\n".join(read_lines)
    for term in forbidden:
        if term in code_only:
            print(f"FORBIDDEN SOURCE '{term}' referenced in executable code of {path}", file=sys.stderr)
            failed = True
if failed:
    sys.exit(1)
print("Forbidden-source check: PASS")
PYEOF

"${PYTHON}" src/modeles/france_ze2020/run_fr_ze2020_dynamic_graph_falsifications.py \
  --output-dir "${OUTDIR}" \
  --edges "${EDGES_PATH}" \
  --target-horizon "${TARGET_HORIZON}" \
  --eval-years ${EVAL_YEARS} \
  --scenarios ${SCENARIOS} \
  --max-epochs "${MAX_EPOCHS}" \
  --seed "${SEED}"

echo "Dynamic graph falsification task seed=${SEED} complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Outputs in ${OUTDIR}"
