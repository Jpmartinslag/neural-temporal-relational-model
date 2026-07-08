#!/bin/bash
# HERALD -- submit France ZE2020 top-3 entry falsification HPC batch.
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
OUTDIR="hpc_results/fr_ze2020_top3_entry_${RUN_ID}"
LOGDIR="${OUTDIR}/logs"

echo "=========================================="
echo "France ZE2020 top-3 entry HPC -- RUN_ID=${RUN_ID}"
echo "=========================================="

required_files=(
  hpc/france_ze2020_top3_entry/run_fr_ze2020_top3_entry_task.sh
  hpc/france_ze2020_top3_entry/run_fr_ze2020_top3_entry_array.sbatch
  hpc/france_ze2020_top3_entry/audit_fr_ze2020_top3_entry_hpc_results.py
  src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py
  src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py
  src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py
  data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
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

mkdir -p "${LOGDIR}"

SBATCH_CMD=(sbatch
  "--output=${LOGDIR}/task_%a.out"
  "--error=${LOGDIR}/task_%a.err"
  "--export=ALL,RUN_ID=${RUN_ID}"
  "hpc/france_ze2020_top3_entry/run_fr_ze2020_top3_entry_array.sbatch"
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
