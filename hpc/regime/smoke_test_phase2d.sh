#!/bin/bash
# ============================================================
# HERALD Phase 2D — CPU smoke test (1 epoch, fold 2023, seed 0)
#
# Fails explicitly if:
#   - ruptures not installed
#   - torch.optim.swa_utils missing
#   - any new arg rejected by the model
#   - JSON, CSV total, CSV sector, NPZ or metadata artefact missing
#   - PELT metadata missing or breakpoints > train_max (leakage)
#   - manual flags present in non-ctrl configs
# ============================================================
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=$(date +%Y%m%d_%H%M%S)
OUT_SMOKE="hpc_results/herald_phase2d_smoke_${STAMP}"

PANEL_PATH="data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"
SPLITS_PATH="metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"
SIDE_A10_PATH="data/processed/side_creations_a10_ze2020_through_2025_v1.csv"

mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,logs,metadata}

echo "========================================================"
echo " HERALD Phase 2D — CPU Smoke Test"
echo " out : $OUT_SMOKE"
echo " date: $(date)"
echo "========================================================"

# ---- prerequisites ----
echo ""
echo "[prereq] Checking ruptures (HARD FAIL if missing)..."
"$PYTHON" -c "import ruptures; print('  ruptures OK:', ruptures.__version__)"

echo "[prereq] Checking SWA utils..."
"$PYTHON" -c "from torch.optim.swa_utils import AveragedModel; print('  SWA OK')"

echo "[prereq] Compiling sources..."
"$PYTHON" -m py_compile \
    src/modeles/herald_regime_modes.py \
    src/modeles/train_herald_v7.py \
    src/modeles/train_herald_semi_v2.py \
    src/modeles/train_herald_regime_experiment.py \
    hpc/regime/audit_herald_phase2d_stability.py
echo "  compile OK"

echo "[prereq] Checking input files..."
for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
    [ -f "$f" ] || { echo "  FAIL: missing $f" >&2; exit 1; }
done
echo "  input files OK"

# ---- smoke_common: shared training args for 1-epoch CPU run ----
# Suffix produced by semiv2: {mode}{_runtag}_seed_{seed}
# With --mode full --run-tag smoke_{label} --seed 0:
#   suffix = full_smoke_{label}_seed_0
smoke_common() {
    local label=$1
    echo \
        --panel-path "$PANEL_PATH" \
        --splits-path "$SPLITS_PATH" \
        --side-a10-path "$SIDE_A10_PATH" \
        --prediction-output-dir "${OUT_SMOKE}/data_processed" \
        --metrics-path "${OUT_SMOKE}/reports/per_run/smoke_${label}.json" \
        --model-card-path "${OUT_SMOKE}/reports/per_run/smoke_${label}.md" \
        --epochs 1 \
        --hidden-dim 16 \
        --q-hidden 8 \
        --attn-dim 8 \
        --top-k 5 \
        --mode full \
        --v7-variant learned_regime_gate_sector_enhanced \
        --feature-mask-ratio 0.10 \
        --sector-mask-ratio 0.30 \
        --sector-lambda 0.2 \
        --smooth-lambda 0.01 \
        --gate-entropy-lambda 0.001 \
        --alpha-smooth-lambda 0.001 \
        --rank-lambda 0.02 \
        --lr 0.001 \
        --huber-delta 300 \
        --gate-bias-init 2.0 \
        --alpha-bias-init 0.0 \
        --semi-warmup-epochs 0 \
        --device cpu \
        --seed 0 \
        --single-target-year 2023
}

run_smoke() {
    local label=$1
    local regime_mode=$2
    shift 2
    local extra_args=("$@")
    local meta="${OUT_SMOKE}/metadata/smoke_${label}.json"

    echo ""
    echo "--- smoke: ${label} (regime=${regime_mode}) ---"
    "$PYTHON" src/modeles/train_herald_regime_experiment.py \
        --regime-mode "$regime_mode" \
        --experiment-label "smoke_${label}" \
        --regime-metadata-path "$meta" \
        --drop-source-flags \
        --smooth-regime-source none \
        $(smoke_common "$label") \
        ${extra_args[@]+"${extra_args[@]}"} \
        --run-tag "smoke_${label}"
    echo "  done"
}

# ---- run smoke configs ----
run_smoke cand_2c    no_regime
run_smoke D1a        no_regime  --collapse-lambda 0.01 --latent-smooth-lambda 0.005
run_smoke D2a_pelt3  pelt_regime_pen3
run_smoke D2b_pelt5  pelt_regime_pen5
run_smoke D3_aba     no_regime  --alpha-balance-lambda 0.005
run_smoke D4_dro15   no_regime  --zone-dro-q45-boost 1.5
run_smoke D5_swa     no_regime  --swa-start-frac 0.2
run_smoke D6_roll9   no_regime  --window-years 9
run_smoke D7_roll7   no_regime  --window-years 7

# ---- validation checks ----
echo ""
echo "========================================================"
echo " Post-run validation checks"
echo "========================================================"

check_fail=0

# Artefact suffix: semiv2 constructs "full_smoke_{label}_seed_0"
# from --mode full --run-tag smoke_{label} --seed 0
artefact_suffix() { echo "full_smoke_${1}_seed_0"; }

check_artefacts() {
    local label=$1
    local sfx
    sfx=$(artefact_suffix "$label")
    local dp="${OUT_SMOKE}/data_processed"
    local rp="${OUT_SMOKE}/reports/per_run"
    local mt="${OUT_SMOKE}/metadata"

    local ok=1
    # 1. per-run metrics JSON (written to --metrics-path by semiv2)
    local json_f="${rp}/smoke_${label}.json"
    # 2. CSV total predictions
    local csv_total="${dp}/herald_semi_v2_predictions_total_${sfx}_v1.csv"
    # 3. CSV sector predictions
    local csv_sector="${dp}/herald_semi_v2_predictions_sector_${sfx}_v1.csv"
    # 4. NPZ internals
    local npz_f="${dp}/herald_semi_v2_internals_${sfx}_v1.npz"
    # 5. regime metadata JSON (written to --regime-metadata-path by experiment wrapper)
    local meta_f="${mt}/smoke_${label}.json"

    for f in "$json_f" "$csv_total" "$csv_sector" "$npz_f" "$meta_f"; do
        if [ ! -f "$f" ]; then
            echo "  FAIL ${label}: missing $(basename "$f")"
            check_fail=1
            ok=0
        fi
    done
    [ "$ok" -eq 1 ] && echo "  OK ${label}: all 5 artefacts present"
}

check_no_manual_flags() {
    local label=$1
    local meta="${OUT_SMOKE}/metadata/smoke_${label}.json"
    if [ ! -f "$meta" ]; then
        echo "  SKIP ${label}: metadata missing (already reported)"
        return
    fi
    local result
    result=$("$PYTHON" -c "
import json
m = json.load(open('${meta}'))
ok = (not m.get('manual_flags_in_annual_features', False) and
      not m.get('manual_flags_in_regime_vector', False))
print('ok' if ok else 'FAIL: manual flags present')
")
    if [ "$result" != "ok" ]; then
        echo "  FAIL ${label}: $result"
        check_fail=1
    else
        echo "  OK ${label}: no manual flags"
    fi
}

check_pelt_causality() {
    local label=$1
    local meta="${OUT_SMOKE}/metadata/smoke_${label}.json"
    if [ ! -f "$meta" ]; then
        echo "  SKIP ${label}: metadata missing (already reported)"
        return
    fi
    local result
    result=$("$PYTHON" -c "
import json
m = json.load(open('${meta}'))
bkps = m.get('pelt_breakpoints_by_train_max')
if bkps is None:
    print('FAIL: pelt_breakpoints_by_train_max missing from metadata')
    exit()
errs = []
for tm_str, years in bkps.items():
    tm = int(tm_str)
    bad = [y for y in years if y > tm]
    if bad:
        errs.append(f'leakage train_max={tm}: {bad}')
if errs:
    print('FAIL: ' + '; '.join(errs))
else:
    print(f'ok: {len(bkps)} fold(s), breakpoints=' + str({k: v for k, v in bkps.items()}))
")
    if [[ "$result" == FAIL* ]]; then
        echo "  FAIL ${label}: $result"
        check_fail=1
    else
        echo "  OK ${label}: PELT causal — $result"
    fi
}

# All smoke configs
ALL_LABELS=(cand_2c D1a D3_aba D4_dro15 D5_swa D6_roll9 D7_roll7)
PELT_LABELS=(D2a_pelt3 D2b_pelt5)

echo ""
echo "--- Artefact presence (5 types each) ---"
for lbl in "${ALL_LABELS[@]}" "${PELT_LABELS[@]}"; do
    check_artefacts "$lbl"
done

echo ""
echo "--- Manual flag absence (non-ctrl configs) ---"
for lbl in "${ALL_LABELS[@]}" "${PELT_LABELS[@]}"; do
    check_no_manual_flags "$lbl"
done

echo ""
echo "--- PELT causality (breakpoints <= train_max) ---"
for lbl in "${PELT_LABELS[@]}"; do
    check_pelt_causality "$lbl"
done

# ---- final result ----
echo ""
echo "========================================================"
if [ "$check_fail" -eq 0 ]; then
    echo " SMOKE TEST PASSED — Phase 2D ready for GPU launch"
    echo " Artefacts: $OUT_SMOKE"
    echo ""
    echo " Next step (on HPC):"
    echo "   bash hpc/regime/submit_herald_phase2d_stability.sh"
else
    echo " SMOKE TEST FAILED — fix errors above before GPU launch"
    exit 1
fi
echo "========================================================"
