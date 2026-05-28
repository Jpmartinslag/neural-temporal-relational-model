#!/bin/bash
# CPU smoke test for HERALD Phase 3E q_tensor architecture selection battery.
# Runs 1 epoch, 1 seed, 12 configs (Q0-Q12 minus Q2).
# Expected artifacts: 12 JSON files.
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase3e_qtensor_arch_smoke_${STAMP}"}

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

export PYTHON="${PYTHON:-$(command -v python3)}"

bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
bash -n hpc/regime/submit_herald_phase3e_qtensor_arch.sh
echo "Shell syntax OK"

"$PYTHON" -m py_compile src/modeles/train_herald_v7.py
"$PYTHON" -m py_compile src/modeles/train_herald_semi_v2.py
"$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
"$PYTHON" -m py_compile hpc/regime/audit_herald_phase3e_qtensor_arch_results.py
echo "Python compile OK"

n_configs=$(REGIME_PLAN=phase3e_qtensor_arch bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs' | grep -v "^#" | grep -c '.')
if [ "$n_configs" -ne 12 ]; then
  echo "ERROR: expected 12 configs, got ${n_configs}" >&2
  exit 1
fi
echo "Config count OK: ${n_configs}"

echo "Config policies:"
REGIME_PLAN=phase3e_qtensor_arch bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs' | \
  awk '{printf "  NF=%-3s col4=%-32s col5=%-5s col41=%s\n", NF, $4, $5, $41}'

SEED=0 \
REGIME_PLAN=phase3e_qtensor_arch \
EPOCHS=${EPOCHS:-1} \
MASK_WARMUP=0 \
DEVICE=${DEVICE:-cpu} \
OUT_ROOT="$OUT_SMOKE" \
bash hpc/regime/run_herald_regime_seed.sh

expected=12
actual=$(find "$OUT_SMOKE/reports/per_run" -name '*.json' 2>/dev/null | wc -l)
if [ "$actual" -ne "$expected" ]; then
  echo "ERROR: expected ${expected} smoke JSONs, got ${actual}" >&2
  exit 1
fi
echo "Artifact count OK: ${actual}/${expected}"

"$PYTHON" - <<PY
import json
from pathlib import Path

root = Path("${OUT_SMOKE}")
expected_policies = {
    "Q0_real":                     "real",
    "Q1_zero":                     "zero",
    "Q3_spatial_perm":             "spatial_perm",
    "Q4_effectifs_only":           "effectifs_only",
    "Q5_masse_only":               "masse_only",
    "Q6_lag1":                     "lag1",
    "Q7_effectifs_lag1":           "effectifs_lag1",
    "Q8_masse_lag1":               "masse_lag1",
    "Q9_lag2":                     "lag2",
    "Q10_effectifs_spatial_perm":  "effectifs_spatial_perm",
    "Q11_lag1_spatial_perm":       "lag1_spatial_perm",
    "Q12_effectifs_lag1_a10guard": "effectifs_lag1",
}
found = {}
for path in sorted((root / "reports/per_run").glob("*.json")):
    payload = json.loads(path.read_text())
    result = next(iter(payload.values()))
    tag = result.get("run_tag", "")
    pol = result.get("quarterly_tensor_policy", "MISSING")
    print(f"  {tag[-60:]}: policy={pol}")
    for label, exp_pol in expected_policies.items():
        if label in tag:
            found[label] = pol
            assert pol == exp_pol, f"Expected policy={exp_pol!r} for {label}, got {pol!r} in {path}"
            break

missing = set(expected_policies) - set(found)
if missing:
    raise AssertionError(f"Missing configs in smoke output: {missing}")

print("quarterly_tensor_policy metadata OK")
PY

echo ""
echo "============================================================"
echo " Phase 3E q_tensor arch smoke OK"
echo " artifacts: $OUT_SMOKE"
echo " configs tested: Q0, Q1, Q3-Q12"
echo "============================================================"
