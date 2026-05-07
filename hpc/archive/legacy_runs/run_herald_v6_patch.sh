#!/bin/bash
# ============================================================
#  HERALD V6 — PATCH DE ROBUSTEZ
#
#  Seções:
#    D  — gate sweep: full x {1.5, 2.0, 2.5} x 7 seeds
#    E  — bateria final: 7 ablações x 7 seeds com FINAL_GATE
#
#  Uso:
#    bash run_herald_v6_patch.sh D          # gate sweep (~21 runs)
#    bash run_herald_v6_patch.sh E          # ablações finais (~49 runs)
#    bash run_herald_v6_patch.sh D && \
#      python3 scripts/03_select_gate.py && \
#      bash run_herald_v6_patch.sh E        # sequência completa
#
#  IMPORTANTE: depois de rodar D, inspecione os resultados com
#    python3 scripts/03_select_gate.py
#  e edite FINAL_GATE abaixo antes de rodar E.
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SCRIPT=src/data/train_herald_v6.py
EPOCHS=${EPOCHS:-800}
CORE_SEEDS="0 1 7 13 42 99 123"
SECTION=${1:-D}

# ── Configuração base (congelada) ────────────────────────────
HIDDEN=32
Q_HIDDEN=16
ATTN=8
TOP_K=10
SMOOTH=0.01
CONTRAST=0.0
GATE_ENTROPY=0.001
SECTOR_LAMBDA=0.1
LR=0.001
HUBER=300

# ── Definir aqui após rodar D e inspecionar com 03_select_gate.py ──
FINAL_GATE=2.0   # EDITAR se necessário

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%H:%M:%S')"
  $PYTHON $SCRIPT "$@"
  echo "   done  $(date '+%H:%M:%S')"
}

check_env() {
  $PYTHON - <<'PY'
import torch
print(" Torch:", torch.__version__)
print(" CUDA :", torch.cuda.is_available())
if torch.cuda.is_available():
    print(" GPU  :", torch.cuda.get_device_name(0))
PY
}

base_args() {
  echo --epochs "$EPOCHS" \
       --hidden-dim "$HIDDEN" --q-hidden "$Q_HIDDEN" --attn-dim "$ATTN" \
       --top-k "$TOP_K" --smooth-lambda "$SMOOTH" --contrast-lambda "$CONTRAST" \
       --gate-entropy-lambda "$GATE_ENTROPY" \
       --sector-lambda "$SECTOR_LAMBDA" --lr "$LR" --huber-delta "$HUBER"
}

# ── Seção D: Gate sweep ───────────────────────────────────────
run_section_D() {
  local COUNT=0
  local TOTAL=$((3 * 7))
  for GATE in 1.5 2.0 2.5; do
    for SEED in $CORE_SEEDS; do
      COUNT=$((COUNT + 1))
      run "[D-$COUNT/$TOTAL] full gate=$GATE seed=$SEED" \
        --ablation full --seed "$SEED" \
        --gate-bias-init "$GATE" \
        --run-tag "gate${GATE}" \
        $(base_args)
    done
  done
}

# ── Seção E: Bateria final ────────────────────────────────────
# Todas as ablações com o FINAL_GATE selecionado.
# Rodar APENAS depois de inspecionar a seção D.
run_section_E() {
  local COUNT=0
  local ABLATIONS="full self_only fixed_geo_mob_only static_adaptive no_regime_in_graph no_quarterly no_sector_head"
  local N_ABL=7
  local TOTAL=$((N_ABL * 7))
  local TAG="final_gate${FINAL_GATE}"

  echo ""
  echo "Gate selecionado para bateria final: $FINAL_GATE"
  echo "Run-tag: $TAG"

  for ABLATION in $ABLATIONS; do
    for SEED in $CORE_SEEDS; do
      COUNT=$((COUNT + 1))
      run "[E-$COUNT/$TOTAL] $ABLATION gate=$FINAL_GATE seed=$SEED" \
        --ablation "$ABLATION" --seed "$SEED" \
        --gate-bias-init "$FINAL_GATE" \
        --run-tag "$TAG" \
        $(base_args)
    done
  done
}

# ── Main ─────────────────────────────────────────────────────
echo "============================================"
echo " HERALD V6 — Patch de Robustez"
echo " Python  : $PYTHON"
echo " Seção   : $SECTION"
echo " Epochs  : $EPOCHS"
echo " Seeds   : $CORE_SEEDS"
echo " Start   : $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
check_env

case "$SECTION" in
  D) run_section_D ;;
  E) run_section_E ;;
  *)
    echo "Seção desconhecida: $SECTION"
    echo "Use: D (gate sweep) | E (ablações finais)"
    exit 1
    ;;
esac

echo ""
echo "============================================"
echo " Completo: $(date '+%Y-%m-%d %H:%M:%S')"
echo " Resultados: reports/herald_v6_metrics_v1.json"
echo "============================================"
