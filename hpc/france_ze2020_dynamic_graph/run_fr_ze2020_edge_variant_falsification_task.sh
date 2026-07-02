#!/bin/bash
# HERALD -- France ZE2020 dynamic edge variant falsification HPC task.

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"
: "${EDGE_VARIANT_NAME:?EDGE_VARIANT_NAME must be set}"
: "${EDGE_VARIANT_PATH:?EDGE_VARIANT_PATH must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_dynamic_edge_variants_${RUN_ID}/${EDGE_VARIANT_NAME}/seed_${SEED}"
MAX_EPOCHS="${FR_ZE2020_DYNAMIC_EDGE_MAX_EPOCHS:-120}"
TARGET_HORIZON="${FR_ZE2020_DYNAMIC_EDGE_TARGET_HORIZON:-1}"
EVAL_YEARS="${FR_ZE2020_DYNAMIC_EDGE_EVAL_YEARS:-2017 2018 2019 2020 2021 2022 2023 2024}"
SCENARIOS="${FR_ZE2020_DYNAMIC_EDGE_SCENARIOS:-full_control no_edges random_edge_weights random_edge_targets no_cross_ze_same_sector no_intra_ze_sector no_ze_similarity temporal_shuffle sector_shuffle}"

echo "=========================================="
echo "HERALD France ZE2020 dynamic edge variant falsification"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "RUN_ID=${RUN_ID}"
echo "EDGE_VARIANT_NAME=${EDGE_VARIANT_NAME}"
echo "EDGE_VARIANT_PATH=${EDGE_VARIANT_PATH}"
echo "SEED=${SEED}"
echo "OUTDIR=${OUTDIR}"
echo "=========================================="

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

if [[ ! -f "${EDGE_VARIANT_PATH}" ]]; then
  echo "ERROR: edge variant file not found: ${EDGE_VARIANT_PATH}" >&2
  exit 1
fi

"${PYTHON}" -c "import sklearn, pandas, numpy; print(f'sklearn={sklearn.__version__} pandas={pandas.__version__} numpy={numpy.__version__}')"

"${PYTHON}" - <<'PYEOF'
import sys
forbidden = ("dynamic_stgnn_feature_panel", "graph_adjacency_core_v0", "graph_adjacency_mobility_v0")
scripts = [
    "src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py",
    "src/modeles/france_ze2020/run_fr_ze2020_dynamic_graph_falsifications.py",
    "src/data/france_ze2020/build_fr_ze2020_dynamic_edge_variants.py",
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
  --edges "${EDGE_VARIANT_PATH}" \
  --output-dir "${OUTDIR}" \
  --target-horizon "${TARGET_HORIZON}" \
  --eval-years ${EVAL_YEARS} \
  --scenarios ${SCENARIOS} \
  --max-epochs "${MAX_EPOCHS}" \
  --seed "${SEED}"

echo "Dynamic edge variant task complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Outputs in ${OUTDIR}"
