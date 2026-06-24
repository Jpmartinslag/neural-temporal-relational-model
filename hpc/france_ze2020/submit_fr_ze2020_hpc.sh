#!/bin/bash
# HERALD -- France ZE2020 HPC submit wrapper.
#
# See reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md section 8. Prepares
# and validates the submission, but only calls `sbatch` if invoked with
# --confirm-submit. Without that flag, prints the exact command that would
# run and exits 0 -- safe to call as a dry-run from any automation.
#
# Usage:
#   bash hpc/france_ze2020/submit_fr_ze2020_hpc.sh                 # dry-run
#   bash hpc/france_ze2020/submit_fr_ze2020_hpc.sh --confirm-submit # real submit

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
OUTDIR="hpc_results/fr_ze2020_hpc_${RUN_ID}"
LOGDIR="${OUTDIR}/logs"

echo "=========================================="
echo "France ZE2020 HPC submit -- RUN_ID=${RUN_ID}"
echo "=========================================="

# Validate prerequisites before even considering a submit.
if [[ ! -f "src/modeles/france_ze2020/train_fr_ze2020_baselines.py" ]]; then
  echo "ERROR: training scripts not found -- did you rsync first?" >&2
  exit 1
fi
if [[ ! -f "data/processed/france_ze2020/fr_ze2020_sector_panel.csv" ]]; then
  echo "ERROR: FR ZE2020 panels not found -- did you rsync first?" >&2
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
  "hpc/france_ze2020/run_fr_ze2020_hpc_array.sbatch"
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
  exit 0
fi
