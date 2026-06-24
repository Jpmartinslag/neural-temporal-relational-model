#!/bin/bash
# HERALD -- France ZE2020 HPC smoke test.
#
# See reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md section 8. Runs ONE
# small configuration directly (no sbatch -- same pattern already used by
# hpc/phase10_synthetic_lagged/README.md's smoke step: a plain conda/python
# invocation on the login or an interactive node, not a queued job). Must
# pass before any array submission is considered.

set -euo pipefail

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
OUTDIR="${WORKDIR}/hpc_results/fr_ze2020_smoke_$(date +%Y%m%d_%H%M%S)"

cd "${WORKDIR}"
mkdir -p "${OUTDIR}"

echo "=========================================="
echo "France ZE2020 HPC smoke test"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Output: ${OUTDIR}"
echo "=========================================="

"${PYTHON}" -c "import sklearn, pandas, numpy; print(f'sklearn={sklearn.__version__} pandas={pandas.__version__} numpy={numpy.__version__}')"

# Small config: 1 seed, few epochs, 2 eval years only -- a few seconds,
# not the full 5-seed/300-epoch/7-year array.
"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_baselines.py \
    --output-dir "${OUTDIR}" --eval-years 2024 2025

"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py \
    --output-dir "${OUTDIR}" --eval-years 2024 2025

"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py \
    --output-dir "${OUTDIR}" --eval-years 2024 2025 --max-epochs 20 --seed 42

"${PYTHON}" src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py \
    --output-dir "${OUTDIR}" --eval-years 2024 2025 --max-epochs 20 --seed 42

echo "------------------------------------------"
echo "Verifying smoke outputs..."
"${PYTHON}" - <<PYEOF
import pandas as pd
import numpy as np
import sys

outdir = "${OUTDIR}"
files = [
    "fr_ze2020_baseline_metrics_v1.csv",
    "fr_ze2020_relational_baseline_metrics_v1.csv",
    "fr_ze2020_neural_relational_metrics_v1.csv",
    "fr_ze2020_neural_relational_feature_signals_v1.csv",
    "fr_ze2020_sector_graph_metrics_v1.csv",
    "fr_ze2020_sector_graph_relation_signals_v1.csv",
]
ok = True
for f in files:
    path = f"{outdir}/{f}"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"MISSING: {path}")
        ok = False
        continue
    if df.empty:
        print(f"EMPTY: {path}")
        ok = False
        continue
    # +-Inf only -- NaN can be legitimate here (e.g. n_train_years is None
    # for the persistence model, which does no fitting; already verified
    # correct by each script's own test suite). Inf would mean a real bug
    # (e.g. the division-by-zero edge case documented in HERALD_17 section
    # 12 for the sector pipeline), so that is what this smoke check guards.
    numeric = df.select_dtypes(include=[np.number])
    if np.isinf(numeric.to_numpy(dtype=float)).any():
        print(f"INFINITE VALUES: {path}")
        ok = False
    print(f"OK: {path} ({len(df)} rows)")

if not ok:
    print("SMOKE TEST FAILED")
    sys.exit(1)
print("SMOKE TEST PASS -- all outputs present, non-empty, finite.")
PYEOF

echo "Smoke output dir: ${OUTDIR}"
