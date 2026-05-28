#!/bin/bash
# CPU smoke test for HERALD Phase 3C labor-tutor battery.
# Runs 1 epoch, 1 seed, all runnable configs (C0-C17).
# Expected artifacts: 18 JSON files.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase3c_labor_tutor_smoke_${STAMP}"}

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

export PYTHON="${PYTHON:-$(command -v python3)}"

# Shell syntax checks
bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/submit_herald_phase3c_labor_tutor.sh
echo "Shell syntax OK"

# Python compile checks
"$PYTHON" -m py_compile src/modeles/train_herald_v7.py
"$PYTHON" -m py_compile src/modeles/train_herald_semi_v2.py
"$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
"$PYTHON" -m py_compile hpc/regime/audit_herald_phase3c_labor_tutor_plan.py
"$PYTHON" -m py_compile hpc/regime/audit_herald_phase3c_labor_tutor_results.py
"$PYTHON" -m py_compile src/data/build_herald_phase3c_labor_tutor_features.py
echo "Python compile OK"

# Pre-flight audit
"$PYTHON" hpc/regime/audit_herald_phase3c_labor_tutor_plan.py \
  --labor-tutor-path "${LABOR_TUTOR_PATH:-data/processed/herald_phase3c_labor_tutor_features.csv}" \
  --panel-path "${PANEL_PATH:-data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv}"
echo "Pre-flight audit OK"

# One smoke seed
SEED=0 \
REGIME_PLAN=phase3c_labor_tutor \
EPOCHS=${EPOCHS:-1} \
MASK_WARMUP=0 \
DEVICE=${DEVICE:-cpu} \
OUT_ROOT="$OUT_SMOKE" \
LABOR_TUTOR_PATH="${LABOR_TUTOR_PATH:-data/processed/herald_phase3c_labor_tutor_features.csv}" \
PANEL_PATH="${PANEL_PATH:-data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv}" \
bash hpc/regime/run_herald_regime_seed.sh

# Artifact count: 18 configs × 1 seed = 18 JSONs
expected=18
actual=$(find "$OUT_SMOKE/reports/per_run" -name '*.json' 2>/dev/null | wc -l)
if [ "$actual" -ne "$expected" ]; then
  echo "ERROR: expected ${expected} smoke JSONs, got ${actual}" >&2
  exit 1
fi
echo "Artifact count OK: ${actual}/${expected}"

# Validate labor_tutor metadata in C3/C4 JSONs
"$PYTHON" - <<PY
import json
from pathlib import Path

root = Path("${OUT_SMOKE}")
for path in sorted((root / "reports/per_run").glob("*.json")):
    payload = json.loads(path.read_text())
    result = next(iter(payload.values()))
    label = result.get("run_tag", "")
    lf = result.get("labor_tutor_feature_set", "none")
    lc = result.get("labor_tutor_columns", [])
    is_ze = result.get("labor_tutor_is_ze_level", False)
    print(f"  {label}: labor_tutor_feature_set={lf}, ze_level={is_ze}, cols={lc}")
    if not "C0" in label:
        assert lf != "none", f"Labor-tutor config should have labor_tutor_feature_set set, got 'none' in {path}"
        assert is_ze, f"Labor-tutor config should be ze_level=True in {path}"
        assert len(lc) > 0, f"Labor-tutor config should have labor_tutor_columns in {path}"
    if "C0" in label:
        assert lf == "none", f"C0 should have labor_tutor_feature_set='none' in {path}"

print("Labor tutor metadata validation OK")
PY

echo ""
echo "============================================================"
echo " Phase 3C smoke OK"
echo " artifacts: $OUT_SMOKE"
echo " configs tested: C0-C17"
echo " blocked (not tested): activité partielle"
echo "============================================================"
