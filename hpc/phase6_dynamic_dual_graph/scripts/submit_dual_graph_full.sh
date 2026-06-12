#!/bin/bash
# P6_DDEG_S1 — Full study submit wrapper
# Run from repo root on meso:
#   bash hpc/phase6_dynamic_dual_graph/scripts/submit_dual_graph_full.sh
#
# Pre-flight checks: 275 unique combos, round-trip ID, tensor checksums,
# pilot outputs, corrected C7/C8 in source, no ZE2020/L1 imports,
# then sbatch. Only submits if ALL checks pass.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO"

# ── Python discovery ───────────────────────────────────────────────────────
if [ -x "$HOME/.conda/envs/herald-v5/bin/python" ]; then
    PYTHON="$HOME/.conda/envs/herald-v5/bin/python"
elif [ -x "$HOME/miniconda3/envs/mlearning/bin/python" ]; then
    PYTHON="$HOME/miniconda3/envs/mlearning/bin/python"
elif [ -x "$HOME/anaconda3/envs/mlearning/bin/python" ]; then
    PYTHON="$HOME/anaconda3/envs/mlearning/bin/python"
else
    PYTHON="$(command -v python3)"
fi

SBATCH="hpc/phase6_dynamic_dual_graph/scripts/run_dual_graph_array.sbatch"
TASK_PY="hpc/phase6_dynamic_dual_graph/scripts/run_dual_graph_task.py"

echo "====  P6_DDEG_S1 pre-flight  ===="
echo "repo=$REPO  python=$PYTHON"
echo ""

FAIL=0

# ── 1. py_compile ─────────────────────────────────────────────────────────
echo "1. py_compile..."
PYTHONPATH="$REPO" "$PYTHON" -m py_compile \
    src/modeles/dual_graph_models.py \
    src/modeles/train_dual_graph_experiment.py \
    "$TASK_PY" \
    hpc/phase6_dynamic_dual_graph/scripts/audit_dual_graph_hpc_results.py \
    && echo "   OK" || { echo "   FAIL: py_compile"; FAIL=1; }

# ── 2. bash -n ────────────────────────────────────────────────────────────
echo "2. bash -n on sbatch and submit..."
bash -n "$SBATCH" && echo "   $SBATCH: OK" || { echo "   FAIL: bash -n $SBATCH"; FAIL=1; }
bash -n "$0"      && echo "   $0: OK"     || { echo "   FAIL: bash -n $0"; FAIL=1; }

# ── 3. 275 unique combos + round-trip ─────────────────────────────────────
echo "3. Combo/round-trip audit..."
PYTHONPATH="$REPO" "$PYTHON" - << 'PYEOF'
import sys
sys.path.insert(0, ".")
from hpc.phase6_dynamic_dual_graph.scripts.run_dual_graph_task import (
    decode_task, encode_task, FOLDS, CONTROL_ORDER, SEEDS, N_FOLDS, N_CONTROLS, N_SEEDS, _STRIDE)

total = N_FOLDS * N_CONTROLS * N_SEEDS
assert total == 275, f"Expected 275 combos, got {total}"

combos = set()
for tid in range(total):
    fold, ctrl, seed = decode_task(tid)
    combos.add((fold, ctrl, seed))
    rt = encode_task(fold, ctrl, seed)
    assert rt == tid, f"Round-trip fail: task {tid} → ({fold},{ctrl},{seed}) → {rt}"

assert len(combos) == 275, f"Duplicate combos: {len(combos)} unique"

# Verify boundary tasks
f0, c0, s0 = decode_task(0)
assert f0 == 2021 and c0 == "C0_persistence" and s0 == 42, f"task 0 wrong: {f0,c0,s0}"
f274, c274, s274 = decode_task(274)
assert f274 == 2025, f"task 274 fold wrong: {f274}"
assert c274 == "C10_ardeco_temporal_perm", f"task 274 ctrl wrong: {c274}"
assert s274 == 46, f"task 274 seed wrong: {s274}"

# Verify output names are unique
names = set()
for tid in range(total):
    fold, ctrl, seed = decode_task(tid)
    names.add(f"{ctrl}__fr{fold}__seed{seed}.json")
assert len(names) == 275, f"Output name collision: {len(names)} unique"

print(f"   OK: 275 unique combos, round-trip correct, boundary tasks valid, no name collisions")
PYEOF
[ $? -eq 0 ] || FAIL=1

# ── 4. Corrected C7/C8 in source ──────────────────────────────────────────
echo "4. C7/C8 correction check..."
python3 -c "
src = open('src/modeles/train_dual_graph_experiment.py').read()
assert 'territory_graph' in src, 'C7 territory_graph perm missing'
assert 'sector_identity' in src, 'C8 sector_identity perm missing'
assert 'targets_unchanged' in src, 'targets_unchanged guard missing'
assert 'targets_canonical\": True' in src, 'targets_canonical flag missing'
# Ensure joint co-permutation guard exists
assert 'degenerate null' in src, 'degenerate null guard missing'
print('   OK: C7/C8 corrected, targets_unchanged guard present')
" || { echo "   FAIL: C7/C8 check"; FAIL=1; }

# ── 5. No ZE2020 / L1 imports ─────────────────────────────────────────────
echo "5. No ZE2020/old L1 imports..."
python3 -c "
import ast, pathlib
src = pathlib.Path('src/modeles/train_dual_graph_experiment.py').read_text()
tree = ast.parse(src)
FORBIDDEN = ('g1_l1', 'ze2020', 'g1_l2_edges', 'edges.csv', '.geojson')
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        for tok in FORBIDDEN:
            assert tok not in node.value.lower(), f'Forbidden token {tok!r} in constant'
print('   OK: no ZE2020 or old L1 edge references')
" || { echo "   FAIL: ZE2020/L1 check"; FAIL=1; }

# ── 6. Tensor files exist and checksums match ──────────────────────────────
echo "6. Tensor checksum verification..."
PYTHONPATH="$REPO" "$PYTHON" - << 'PYEOF'
import json, hashlib
from pathlib import Path

BASE = Path(".")
TENSOR_DIR = BASE / "data/processed/dual_graph_tensors"
MANIFEST = TENSOR_DIR / "manifest.json"

for yr in [2021, 2022, 2023, 2024, 2025]:
    p = TENSOR_DIR / f"fr_{yr}.npz"
    assert p.exists(), f"Missing tensor: {p}"

if MANIFEST.exists():
    manifest = json.loads(MANIFEST.read_text())
    for f in manifest.get("folds", []):
        yr = f.get("eval_year")
        expected = f.get("sha256")
        if expected and yr:
            p = TENSOR_DIR / f"fr_{yr}.npz"
            h = hashlib.sha256()
            with open(p, "rb") as fp:
                for chunk in iter(lambda: fp.read(1 << 20), b""):
                    h.update(chunk)
            actual = h.hexdigest()
            assert actual == expected, f"Checksum mismatch fr_{yr}: expected {expected[:16]}... got {actual[:16]}..."
print("   OK: 5 tensor files present, checksums verified")
PYEOF
[ $? -eq 0 ] || FAIL=1

# ── 7. Pilot outputs check ─────────────────────────────────────────────────
echo "7. Pilot outputs check..."
PYTHONPATH="$REPO" "$PYTHON" - << 'PYEOF'
import json
from pathlib import Path

pilot_dir = Path("data/processed/dual_graph_pilot_all_folds")
gate_file = pilot_dir / "gate_result.json"
leakage_file = pilot_dir / "leakage_audit.json"

assert gate_file.exists(), f"Missing pilot gate_result: {gate_file}"
gate = json.loads(gate_file.read_text())
print(f"   Pilot gate: {gate['decision']}")
print(f"   Criteria: {sum(gate['criteria'].values())}/7 pass")

assert leakage_file.exists(), f"Missing pilot leakage_audit: {leakage_file}"
leakage = json.loads(leakage_file.read_text())
# Check all folds have leakage_ok
for fold, rec in leakage.items():
    ok = rec.get("leakage_ok")
    assert ok, f"Leakage FAIL in fold {fold}: {rec}"
print(f"   Pilot leakage: all folds OK")

per_run = pilot_dir / "per_run"
n = len(list(per_run.glob("*.json"))) if per_run.exists() else 0
print(f"   Pilot per_run outputs: {n} (expected 110 = 5 folds × 11 controls × 2 seeds)")
PYEOF
[ $? -eq 0 ] || FAIL=1

# ── 8. git diff --check ───────────────────────────────────────────────────
echo "8. git diff --check..."
git diff --check && echo "   OK" || { echo "   WARN: whitespace issues in diff"; }

# ── Final check ───────────────────────────────────────────────────────────
echo ""
if [ $FAIL -ne 0 ]; then
    echo "PRE-FLIGHT FAILED — not submitting. Fix errors above."
    exit 1
fi

echo "==== PRE-FLIGHT PASSED ===="
echo ""
echo "Submitting array 0-274 (limit %20)..."
mkdir -p "$REPO/hpc_results/dual_graph_s1/logs"

JOB_OUTPUT=$(sbatch "$SBATCH")
echo "$JOB_OUTPUT"
JOB_ID=$(echo "$JOB_OUTPUT" | grep -oP '\d+')
echo ""
echo "Submitted job ID: $JOB_ID"
echo ""
echo "Monitor with:"
echo "  squeue -j $JOB_ID"
echo "  sacct -j $JOB_ID --format=JobID,State,Elapsed,MaxRSS,ExitCode"
echo "  tail -f $REPO/hpc_results/dual_graph_s1/logs/ddeg_${JOB_ID}_0.out"
