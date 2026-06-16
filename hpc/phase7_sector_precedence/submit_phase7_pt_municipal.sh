#!/bin/bash
# DEC-064: Submit Phase 7 PT municipal array job.
# Run from REPO ROOT after verifying panel and manifest are current.
#
# PRECONDITIONS (verify before submitting):
#   1. Panel built:   data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv
#   2. Manifest built: data/processed/phase7_pt_municipal/hpc_task_manifest.json
#   3. Smoke PASSED:  data/processed/phase7_pt_municipal/dec064_gates_smoke.json
#   4. Commit hash in manifest matches HEAD: git rev-parse HEAD
#
# DO NOT submit without explicit authorisation (DEC-064 constraint).

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
MANIFEST="$REPO/data/processed/phase7_pt_municipal/hpc_task_manifest.json"
PANEL="$REPO/data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv"

echo "=== DEC-064 Phase 7 PT Municipal — Pre-submit checks ==="

# Check panel
[ -f "$PANEL" ] || { echo "ERROR: Panel not found: $PANEL"; exit 1; }
echo "  Panel: OK"

# Check manifest
[ -f "$MANIFEST" ] || { echo "ERROR: Manifest not found: $MANIFEST"; exit 1; }
N_TASKS=$(python3 -c "import json; m=json.loads(open('$MANIFEST').read()); print(len(m))")
echo "  Manifest: $N_TASKS tasks"

# Check smoke gate
SMOKE_GATES="$REPO/data/processed/phase7_pt_municipal/dec064_gates_smoke.json"
[ -f "$SMOKE_GATES" ] || { echo "ERROR: Smoke gates not found — run smoke first"; exit 1; }
SMOKE_DEC=$(python3 -c "import json; print(json.loads(open('$SMOKE_GATES').read())['decision'])")
echo "  Smoke decision: $SMOKE_DEC"
[[ "$SMOKE_DEC" == *"COMPLETE"* || "$SMOKE_DEC" == *"READY"* ]] || { echo "ERROR: Smoke not PASS"; exit 1; }

# Verify commit hash in manifest matches HEAD
MANIFEST_COMMIT=$(python3 -c "import json; m=json.loads(open('$MANIFEST').read()); print(m[0]['commit_sha'])")
HEAD_COMMIT=$(git -C "$REPO" rev-parse HEAD)
if [ "$MANIFEST_COMMIT" != "$HEAD_COMMIT" ]; then
    echo "WARNING: Manifest commit ($MANIFEST_COMMIT) != HEAD ($HEAD_COMMIT)"
    echo "  Regenerate manifest if panel changed: python src/modeles/real_world/prepare_dec064_hpc_manifest.py"
fi

echo ""
echo "Submit command (run manually after review):"
echo "  sbatch --array=0-$((N_TASKS-1)) $REPO/hpc/phase7_sector_precedence/run_phase7_pt_municipal_array.sbatch"
echo ""
echo "After all tasks complete, merge results:"
echo "  python hpc/phase7_sector_precedence/scripts/merge_sector_precedence_results.py \\"
echo "    --raw-dir hpc_results/phase7_pt_municipal/raw \\"
echo "    --manifest data/processed/phase7_pt_municipal/hpc_task_manifest.json \\"
echo "    --out-dir data/processed/phase7_pt_municipal/results"
echo ""
echo "Then re-run gates:"
echo "  PYTHONPATH=. python src/modeles/real_world/run_dec064_pt_municipal_phase7.py"
