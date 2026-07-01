#!/bin/bash
# HERALD -- France ZE2020 dynamic graph ranker HPC task, one seed.

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_dynamic_graph_ranker_${RUN_ID}/seed_${SEED}"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
MAX_EPOCHS="${FR_ZE2020_DYNAMIC_GRAPH_MAX_EPOCHS:-250}"
TARGET_HORIZON="${FR_ZE2020_DYNAMIC_GRAPH_TARGET_HORIZON:-1}"
if [[ "${TARGET_HORIZON}" == "1" ]]; then
  DEFAULT_EVAL_YEARS="2017 2018 2019 2020 2021 2022 2023 2024"
else
  DEFAULT_EVAL_YEARS="2018 2019 2020 2021 2022"
fi
EVAL_YEARS="${FR_ZE2020_DYNAMIC_GRAPH_EVAL_YEARS:-${DEFAULT_EVAL_YEARS}}"

echo "=========================================="
echo "HERALD France ZE2020 dynamic graph ranker -- seed ${SEED}"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "RUN_ID=${RUN_ID} OUTDIR=${OUTDIR}"
echo "=========================================="

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

"${PYTHON}" -c "import sklearn, pandas, numpy; print(f'sklearn={sklearn.__version__} pandas={pandas.__version__} numpy={numpy.__version__}')"

"${PYTHON}" - <<'PYEOF'
import sys
forbidden = ("dynamic_stgnn_feature_panel", "graph_adjacency_core_v0", "graph_adjacency_mobility_v0")
scripts = [
    "src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py",
    "src/data/france_ze2020/build_fr_ze2020_dynamic_graph_inputs.py",
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

"${PYTHON}" - <<'PYEOF'
import pandas as pd
nodes = pd.read_csv("data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv", nrows=5)
edges = pd.read_csv("data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv", nrows=5)
required_nodes = {"node_id", "ze2020", "sector_code", "decision_year", "future_growth_1y", "future_growth_3y"}
required_edges = {"source_node_id", "target_node_id", "decision_year", "edge_type", "edge_weight"}
if missing := required_nodes - set(nodes.columns):
    raise SystemExit(f"Dynamic graph nodes missing columns: {sorted(missing)}")
if missing := required_edges - set(edges.columns):
    raise SystemExit(f"Dynamic graph edges missing columns: {sorted(missing)}")
print("Dynamic graph input read-only validation: PASS")
PYEOF

"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py \
  --output-dir "${OUTDIR}" \
  --target-horizon "${TARGET_HORIZON}" \
  --eval-years ${EVAL_YEARS} \
  --max-epochs "${MAX_EPOCHS}" \
  --seed "${SEED}"

echo "Dynamic graph ranker task seed=${SEED} complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Outputs in ${OUTDIR}"

