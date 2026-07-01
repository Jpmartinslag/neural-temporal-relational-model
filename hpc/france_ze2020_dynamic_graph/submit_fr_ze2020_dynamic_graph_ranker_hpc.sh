#!/bin/bash
# HERALD -- submit France ZE2020 dynamic graph ranker HPC.
# Dry-run unless --confirm-submit is passed.

set -euo pipefail

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
cd "${WORKDIR}"

CONFIRM=0
for arg in "$@"; do
  if [[ "${arg}" == "--confirm-submit" ]]; then
    CONFIRM=1
  fi
done

RUN_ID="$(date +%Y%m%d_%H%M%S)"
OUTDIR="hpc_results/fr_ze2020_dynamic_graph_ranker_${RUN_ID}"
LOGDIR="${OUTDIR}/logs"

echo "=========================================="
echo "France ZE2020 dynamic graph ranker submit -- RUN_ID=${RUN_ID}"
echo "=========================================="

if [[ ! -f "src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py" ]]; then
  echo "ERROR: dynamic graph ranker script not found -- did you rsync first?" >&2
  exit 1
fi
if [[ ! -f "data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv" ]]; then
  echo "ERROR: dynamic graph nodes not found -- did you rsync first?" >&2
  exit 1
fi
if [[ ! -f "data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv" ]]; then
  echo "ERROR: dynamic graph edges not found -- did you rsync first?" >&2
  exit 1
fi
if ! command -v sbatch >/dev/null 2>&1; then
  echo "ERROR: sbatch not found on this host" >&2
  exit 1
fi

mkdir -p "${LOGDIR}"

SBATCH_CMD=(sbatch
  "--output=${LOGDIR}/task_%a.out"
  "--error=${LOGDIR}/task_%a.err"
  "--export=ALL,RUN_ID=${RUN_ID}"
  "hpc/france_ze2020_dynamic_graph/run_fr_ze2020_dynamic_graph_ranker_array.sbatch"
)

echo "Prepared command:"
printf '  %q' "${SBATCH_CMD[@]}"
echo ""

if [[ "${CONFIRM}" -eq 1 ]]; then
  echo "--confirm-submit received -- submitting now."
  "${SBATCH_CMD[@]}"
  echo "Submitted. Monitor with: squeue -u \$USER"
  echo "Results will land in: ${OUTDIR}/"
else
  echo "DRY RUN -- no job submitted (pass --confirm-submit to actually submit)."
fi

