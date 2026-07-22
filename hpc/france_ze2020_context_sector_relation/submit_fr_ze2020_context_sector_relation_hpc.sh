#!/bin/bash
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
OUTDIR="hpc_results/fr_ze2020_context_sector_relation_${RUN_ID}"
LOGDIR="${OUTDIR}/logs"
mkdir -p "${LOGDIR}"

required_files=(
  hpc/france_ze2020_context_sector_relation/run_fr_ze2020_context_sector_relation_task.sh
  hpc/france_ze2020_context_sector_relation/run_fr_ze2020_context_sector_relation_array.sbatch
  hpc/france_ze2020_context_sector_relation/audit_fr_ze2020_context_sector_relation_hpc.py
  src/modeles/france_ze2020/run_fr_ze2020_context_conditioned_sector_relation_gate.py
)
for path in "${required_files[@]}"; do
  if [[ ! -f "${path}" ]]; then
    echo "ERROR: required file not found: ${path}" >&2
    exit 1
  fi
done
if ! command -v sbatch >/dev/null 2>&1; then
  echo "ERROR: sbatch not found on this host" >&2
  exit 1
fi

SBATCH_CMD=(
  sbatch
  "--output=${LOGDIR}/task_%a.out"
  "--error=${LOGDIR}/task_%a.err"
  "--export=ALL,RUN_ID=${RUN_ID}"
  hpc/france_ze2020_context_sector_relation/run_fr_ze2020_context_sector_relation_array.sbatch
)

printf 'Prepared command:'
printf ' %q' "${SBATCH_CMD[@]}"
printf '\n'
if [[ "${CONFIRM}" -eq 1 ]]; then
  "${SBATCH_CMD[@]}"
  echo "Results: ${OUTDIR}/"
else
  echo "DRY RUN -- pass --confirm-submit to submit."
fi
