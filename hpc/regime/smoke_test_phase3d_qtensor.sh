#!/bin/bash
# CPU smoke test for HERALD Phase 3D q_tensor ablation battery.
# Runs 1 epoch, 1 seed, 6 configs (Q0, Q1, Q3-Q6; Q2 excluded — not fold-safe).
# Expected artifacts: 6 JSON files.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase3d_qtensor_smoke_${STAMP}"}

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
bash -n hpc/regime/submit_herald_phase3d_qtensor.sh
echo "Shell syntax OK"

# Python compile checks
"$PYTHON" -m py_compile src/modeles/train_herald_v7.py
"$PYTHON" -m py_compile src/modeles/train_herald_semi_v2.py
"$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
"$PYTHON" -m py_compile hpc/regime/audit_herald_phase3d_qtensor_results.py
echo "Python compile OK"

# Config count preflight
n_configs=$(REGIME_PLAN=phase3d_qtensor bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs' | grep -v "^#" | grep -c '.')
if [ "$n_configs" -ne 6 ]; then
  echo "ERROR: expected 6 configs, got ${n_configs}" >&2
  exit 1
fi
echo "Config count OK: ${n_configs}"

# q_tensor policy values
echo "Config policies:"
REGIME_PLAN=phase3d_qtensor bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs' | \
  awk '{print "  col4="$4, "col41="$41}'

# One smoke seed
SEED=0 \
REGIME_PLAN=phase3d_qtensor \
EPOCHS=${EPOCHS:-1} \
MASK_WARMUP=0 \
DEVICE=${DEVICE:-cpu} \
OUT_ROOT="$OUT_SMOKE" \
bash hpc/regime/run_herald_regime_seed.sh

# Artifact count: 6 configs × 1 seed = 6 JSONs
expected=6
actual=$(find "$OUT_SMOKE/reports/per_run" -name '*.json' 2>/dev/null | wc -l)
if [ "$actual" -ne "$expected" ]; then
  echo "ERROR: expected ${expected} smoke JSONs, got ${actual}" >&2
  exit 1
fi
echo "Artifact count OK: ${actual}/${expected}"

# Validate quarterly_tensor_policy metadata
"$PYTHON" - <<PY
import json
from pathlib import Path

root = Path("${OUT_SMOKE}")
expected_policies = {
    "Q0_real": "real",
    "Q1_zero": "zero",
    "Q3_spatial_perm": "spatial_perm",
    "Q4_effectifs_only": "effectifs_only",
    "Q5_masse_only": "masse_only",
    "Q6_lag1": "lag1",
}
# Q2 (temporal_perm) excluded: global year permutation is not fold-safe.
found = {}
for path in sorted((root / "reports/per_run").glob("*.json")):
    payload = json.loads(path.read_text())
    result = next(iter(payload.values()))
    tag = result.get("run_tag", "")
    pol = result.get("quarterly_tensor_policy", "MISSING")
    zeroed = result.get("quarterly_tensor_zeroed", None)
    channels = result.get("q_tensor_channels_active", None)
    print(f"  {tag}: policy={pol}")
    for label, exp_pol in expected_policies.items():
        if label in tag:
            found[label] = pol
            assert pol == exp_pol, f"Expected policy={exp_pol!r} for {label}, got {pol!r}"
            break

missing = set(expected_policies) - set(found)
if missing:
    raise AssertionError(f"Missing configs: {missing}")

print("Quarterly tensor policy metadata validation OK")
PY

echo ""
echo "============================================================"
echo " Phase 3D q_tensor smoke OK"
echo " artifacts: $OUT_SMOKE"
echo " configs tested: Q0, Q1, Q3-Q6 (Q2 temporal_perm excluded)"
echo "============================================================"
