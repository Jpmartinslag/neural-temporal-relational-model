#!/bin/bash
# HERALD -- France ZE2020 HPC task (one seed).
#
# See reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md. Called by
# run_fr_ze2020_hpc_array.sbatch, one invocation per array index (one seed).
# Runs the 4 existing FR ZE2020 training scripts directly via their own
# CLIs -- no new model, no torch (sklearn only, not installed/needed
# differently here than in train_fr_ze2020_*.py). Never reads
# dynamic_stgnn_feature_panel* or graph_adjacency_core_v0/mobility_v0.csv
# (inherited guarantee from each script's own tests).
#
# Required env vars (set by the .sbatch array job):
#   RUN_ID   -- timestamp identifying this HPC run (e.g. 20260624_180000)
#   SEED     -- this task's seed (one of 42,43,44,45,46)
#
# Output: hpc_results/fr_ze2020_hpc_${RUN_ID}/seed_${SEED}/*.csv

set -euo pipefail

: "${RUN_ID:?RUN_ID must be set}"
: "${SEED:?SEED must be set}"

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_hpc_${RUN_ID}/seed_${SEED}"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
MAX_EPOCHS="${FR_ZE2020_MAX_EPOCHS:-300}"
EVAL_YEARS="${FR_ZE2020_EVAL_YEARS:-2019 2020 2021 2022 2023 2024 2025}"

echo "=========================================="
echo "HERALD France ZE2020 HPC task -- seed ${SEED}"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "RUN_ID=${RUN_ID} OUTDIR=${OUTDIR}"
echo "=========================================="

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

# Environment sanity (no torch needed for this track -- sklearn only).
"${PYTHON}" -c "import sklearn, pandas, numpy; print(f'sklearn={sklearn.__version__} pandas={pandas.__version__} numpy={numpy.__version__}')"

# Fail-closed: refuse to run if any forbidden source is referenced by the
# executable code (not docstrings) of the 4 scripts -- defense in depth,
# each script's own pytest suite already checks this; this re-checks at
# HPC runtime in case a future edit regresses it.
"${PYTHON}" - <<'PYEOF'
import ast, sys
forbidden = ("dynamic_stgnn_feature_panel", "graph_adjacency_core_v0", "graph_adjacency_mobility_v0")
scripts = [
    "src/modeles/france_ze2020/train_fr_ze2020_baselines.py",
    "src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py",
    "src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py",
    "src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py",
]
failed = False
for path in scripts:
    source = open(path).read()
    docstring = ast.get_docstring(ast.parse(source)) or ""
    code_only = source.replace(docstring, "")
    for term in forbidden:
        if term in code_only:
            print(f"FORBIDDEN SOURCE '{term}' referenced in executable code of {path}", file=sys.stderr)
            failed = True
if failed:
    sys.exit(1)
print("Forbidden-source check: PASS (4/4 scripts clean)")
PYEOF

# 1. Temporal baseline (deterministic, no seed -- run once per task for a
#    complete per-seed bundle, cost is <1s).
"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_baselines.py \
    --output-dir "${OUTDIR}" \
    --eval-years ${EVAL_YEARS}

# 2. Relational baseline (deterministic, no seed).
"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py \
    --output-dir "${OUTDIR}" \
    --eval-years ${EVAL_YEARS}

# 3. Neural relational smoke (this task's seed) -- writes feature_signals.
"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py \
    --output-dir "${OUTDIR}" \
    --eval-years ${EVAL_YEARS} \
    --max-epochs "${MAX_EPOCHS}" \
    --seed "${SEED}"

# 4. Sector graph smoke (this task's seed) -- writes relation_signals.
"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py \
    --output-dir "${OUTDIR}" \
    --eval-years ${EVAL_YEARS} \
    --max-epochs "${MAX_EPOCHS}" \
    --seed "${SEED}"

echo "Task seed=${SEED} complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Outputs in ${OUTDIR}"
