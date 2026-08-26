#!/bin/bash
# Finalize HERALD leak audit after target-shuffle job completion.

set -euo pipefail

REMOTE=${REMOTE:-meso-direct}
REMOTE_ROOT=${REMOTE_ROOT:?set REMOTE_ROOT to the cluster repository path}
LOCAL_ROOT=${LOCAL_ROOT:?set LOCAL_ROOT to the local repository root}

STRICT_RUN=${STRICT_RUN:-herald_strict_exante_20260506_night_final}
STRESS_RUN=${STRESS_RUN:-herald_leak_stress_20260507_target_shuffle}
FORECAST_RUN=${FORECAST_RUN:-herald_forecast_20260506_forecast_after_strict}

cd "$LOCAL_ROOT"

echo "== Download target-shuffle leak-stress results =="
rsync -av \
  "${REMOTE}:${REMOTE_ROOT}/hpc_results/${STRESS_RUN}/" \
  "${LOCAL_ROOT}/hpc_results/${STRESS_RUN}/"

echo "== Audit strict original =="
python3 hpc/audit/audit_herald_strict_exante_results.py \
  --root "hpc_results/${STRICT_RUN}"

echo "== Audit target-shuffle stress =="
python3 hpc/audit/audit_herald_strict_exante_results.py \
  --root "hpc_results/${STRESS_RUN}"

echo "== Compare original vs target-shuffle predictions =="
python3 hpc/audit/audit_leak_stress_prediction_invariance.py \
  --original-root "hpc_results/${STRICT_RUN}" \
  --stress-root "hpc_results/${STRESS_RUN}" \
  --out-json "hpc_results/${STRESS_RUN}/reports/leak_stress_prediction_invariance.json"

echo "== Aggregate forecast, if present =="
if [ -d "hpc_results/${FORECAST_RUN}" ]; then
  python3 hpc/forecast/aggregate_herald_forecast_2026_2027.py \
    --root "hpc_results/${FORECAST_RUN}"
fi

echo "== Build final leak audit summary =="
python3 hpc/audit/write_herald_leak_audit_summary.py \
  --strict-root "hpc_results/${STRICT_RUN}" \
  --stress-root "hpc_results/${STRESS_RUN}" \
  --forecast-root "hpc_results/${FORECAST_RUN}" \
  --availability-md reports/HERALD_DATA_AVAILABILITY_CALENDAR.md \
  --out-md reports/HERALD_LEAK_AUDIT_FINAL_20260507.md

echo "DONE"
echo "Summary: reports/HERALD_LEAK_AUDIT_FINAL_20260507.md"
