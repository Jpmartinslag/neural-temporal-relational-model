#!/bin/bash
# HERALD -- France ZE2020 relation objective HPC task.

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_relation_objective_${RUN_ID}/seed_${SEED}"
EVAL_YEARS="${FR_ZE2020_RELATION_EVAL_YEARS:-2017 2018 2019 2020 2021 2022 2023 2024 2025}"
SCENARIOS="${FR_ZE2020_RELATION_SCENARIOS:-dual_endpoint_matched_negatives dual_endpoint_temporal_sector_shuffle dual_profile_hard_negatives dual_profile_temporal_sector_shuffle pair_distance_hard_negatives source_preserving_endpoint_matched_negatives target_preserving_endpoint_matched_negatives source_distance_target_preserving_negatives}"
POSITIVE_EDGE_STATES="${FR_ZE2020_RELATION_POSITIVE_STATES:-new_relation}"
NODE_FEATURE_LAG="${FR_ZE2020_RELATION_NODE_FEATURE_LAG:-1}"
MAX_ITER="${FR_ZE2020_RELATION_MAX_ITER:-500}"

echo "=========================================="
echo "HERALD France ZE2020 relation objective"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "RUN_ID=${RUN_ID}"
echo "SEED=${SEED}"
echo "OUTDIR=${OUTDIR}"
echo "SCENARIOS=${SCENARIOS}"
echo "EVAL_YEARS=${EVAL_YEARS}"
echo "=========================================="

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

required_files=(
  src/modeles/france_ze2020/audit_fr_ze2020_relation_lift_over_formulas.py
  src/modeles/france_ze2020/audit_fr_ze2020_anchor_peripheral_signal.py
  src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz
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
    "src/modeles/france_ze2020/audit_fr_ze2020_relation_lift_over_formulas.py",
    "src/modeles/france_ze2020/audit_fr_ze2020_anchor_peripheral_signal.py",
    "src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py",
]
failed = False
for path in scripts:
    lines = open(path).read().splitlines()
    executable_lines = [line for line in lines if "read_csv" in line or "Path(" in line or "DEFAULT_" in line]
    code_only = "\n".join(executable_lines)
    for term in forbidden:
        if term in code_only:
            print(f"FORBIDDEN SOURCE '{term}' referenced in executable code of {path}", file=sys.stderr)
            failed = True
if failed:
    sys.exit(1)
print("Forbidden-source check: PASS")
PYEOF

"${PYTHON}" src/modeles/france_ze2020/audit_fr_ze2020_relation_lift_over_formulas.py \
  --output-dir "${OUTDIR}" \
  --scenarios ${SCENARIOS} \
  --eval-years ${EVAL_YEARS} \
  --positive-edge-states ${POSITIVE_EDGE_STATES} \
  --node-feature-lag "${NODE_FEATURE_LAG}" \
  --seed "${SEED}" \
  --max-iter "${MAX_ITER}"

echo "Relation objective task complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Outputs in ${OUTDIR}"
