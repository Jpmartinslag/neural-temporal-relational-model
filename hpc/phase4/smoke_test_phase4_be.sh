#!/bin/bash
# CPU smoke test — HERALD Phase 4 Belgique.
# 1 seed × 1 epoch × 3 configs = 3 JSON artifacts expected.
set -euo pipefail

COUNTRY=be
export COUNTRY

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase4_be_smoke_${STAMP}"}

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

export PYTHON="${PYTHON:-$(command -v python3)}"

bash -n hpc/phase4/run_herald_phase4_seed.sh
bash -n hpc/phase4/phase4_configs.sh
bash -n hpc/phase4/submit_herald_phase4_be.sh
echo "Shell syntax OK"

"$PYTHON" -m py_compile hpc/phase4/prepare_phase4_panel.py
"$PYTHON" -m py_compile hpc/phase4/run_herald_phase4_wrapper.py
"$PYTHON" -m py_compile hpc/phase4/audit_phase4_results.py
"$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
echo "Python compile OK"

"$PYTHON" hpc/phase4/prepare_phase4_panel.py --country be
echo "Panel preparation OK"

n_configs=$(COUNTRY=$COUNTRY bash -c 'source hpc/phase4/phase4_configs.sh && phase4_configs' | grep -c '.')
echo "Configs: $n_configs"
COUNTRY=$COUNTRY bash -c 'source hpc/phase4/phase4_configs.sh && phase4_configs' | \
  awk '{printf "  label=%-24s feature_policy=%-22s qtensor=%s\n", $1, $2, $3}'

SEED=0 \
COUNTRY="$COUNTRY" \
OUT_ROOT="$OUT_SMOKE" \
EPOCHS=1 \
MASK_WARMUP=0 \
DEVICE=${DEVICE:-cpu} \
PYTHON="$PYTHON" \
bash hpc/phase4/run_herald_phase4_seed.sh

expected=3
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
expected_labels = {"baseline_side2", "qtensor_jobs_lag1", "no_qtensor_control"}
found_labels = set()

for path in sorted((root / "reports/per_run").glob("*.json")):
    payload = json.loads(path.read_text())
    result = next(iter(payload.values()))
    tag = result.get("run_tag", "")
    wmape = result.get("total_wmape_mean", result.get("wmape_mean", None))
    print(f"  {tag}: wmape_mean={wmape}")
    for label in expected_labels:
        if label in tag:
            found_labels.add(label)

missing = expected_labels - found_labels
if missing:
    raise AssertionError(f"Missing configs in smoke: {missing}")

print("Config labels OK:", sorted(found_labels))
PY

echo ""
echo "============================================================"
echo " Phase 4 BE smoke OK"
echo " artifacts: $OUT_SMOKE"
echo " configs:   baseline_side2 / qtensor_jobs_lag1 / no_qtensor_control"
echo " ⚠️  brisure TVA 2018 flagged — check per-year WMAPE for 2018+ anomalies"
echo "============================================================"
