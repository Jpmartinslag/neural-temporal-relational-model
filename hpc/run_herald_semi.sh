#!/bin/bash
# ============================================================
# HERALD Semi — bateria completa para cluster
#
# Irmão do V6 com mascaramento espacial. Saídas completamente
# isoladas (prefixo herald_semi_). Seguro em paralelo com V6.
#
# Seções:
#   baseline    — mask=0.0 com 15 seeds (controlo limpo vs V6)
#   main        — mask=0.10 random com 15 seeds (config principal)
#   sensitivity — curva mask_ratio: 0.05/0.15/0.20/0.30 com 5 seeds
#   block       — mask=0.10 estratégia block com 5 seeds
#   hidden64    — mask=0.10 hidden_dim=64 com 5 seeds
#   precovid    — mask=0.10 splits pré-COVID com 5 seeds (estabilidade A_t)
#   all         — tudo acima
#
# Uso:
#   PYTHON=python3 EPOCHS=1500 bash run_herald_semi.sh all
#   PYTHON=python3 EPOCHS=1500 bash run_herald_semi.sh main
# ============================================================

set -e

PYTHON=${PYTHON:-python3}
SECTION=${1:-main}
EPOCHS=${EPOCHS:-1500}
MASK_WARMUP=${MASK_WARMUP:-100}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_semi_$(date +%Y%m%d_%H%M%S)"}

PANEL_PATH=data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
SPLITS_PATH=metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
SPLITS_PRECOVID=metadata/dynamic_stgnn_walk_forward_splits_precovid_v1.csv
SIDE_A10_PATH=data/processed/side_creations_a10_ze2020_through_2025_v1.csv

# 15 seeds para configurações principais
SEEDS_MAIN="0 1 2 3 5 7 11 13 17 19 23 42 77 99 123"
# 5 seeds para ablações
SEEDS_ABL="0 7 13 42 99"
# 5 seeds para pré-COVID
SEEDS_PRE="0 7 13 42 99"

mkdir -p "$OUT_ROOT"/{reports,data_processed}

BASE_ARGS=(
  --panel-path "$PANEL_PATH"
  --splits-path "$SPLITS_PATH"
  --side-a10-path "$SIDE_A10_PATH"
  --prediction-output-dir "$OUT_ROOT/data_processed"
  --metrics-path "$OUT_ROOT/reports/herald_semi_metrics_v1.json"
  --model-card-path "$OUT_ROOT/reports/HERALD_SEMI_MODEL_V1.md"
  --hidden-dim 32 --q-hidden 16 --attn-dim 8
  --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0
  --gate-entropy-lambda 0.001 --sector-lambda 0.1
  --lr 0.001 --huber-delta 300 --gate-bias-init 2.0
  --ablation full --epochs "$EPOCHS"
  --mask-warmup-epochs "$MASK_WARMUP"
)

run() {
  local label=$1; shift
  echo ""
  echo ">> $label  $(date '+%Y-%m-%d %H:%M:%S')"
  "$PYTHON" "$@"
  echo "   done  $(date '+%Y-%m-%d %H:%M:%S')"
}

# ── Baseline: mask=0.0, 15 seeds ─────────────────────────────────────────────
# Controlo limpo com a mesma arquitetura mas sem mascaramento.
# Permite isolar o efeito do mascaramento do efeito de outros hiperparâmetros.
run_baseline() {
  local n=${#SEEDS_MAIN[@]}; local count=0
  for seed in $SEEDS_MAIN; do
    count=$((count+1))
    run "[BASELINE $count] mask=0.0 seed=$seed" \
      src/data/train_herald_semi_v1.py \
      "${BASE_ARGS[@]}" \
      --mask-ratio 0.0 --seed "$seed" \
      --run-tag semi_mask0.0
  done
}

# ── Main: mask=0.10 random, 15 seeds ─────────────────────────────────────────
# Configuração principal. 15 seeds dá poder estatístico para comparar
# A_t(semi) vs A_t(v6) e WMAPE semi vs baseline.
run_main() {
  local count=0
  for seed in $SEEDS_MAIN; do
    count=$((count+1))
    run "[MAIN $count/15] mask=0.10 random seed=$seed" \
      src/data/train_herald_semi_v1.py \
      "${BASE_ARGS[@]}" \
      --mask-ratio 0.10 --mask-strategy random --seed "$seed" \
      --run-tag semi_mask0.10
  done
}

# ── Sensitivity: curva de mask_ratio ─────────────────────────────────────────
# Encontra o ratio ótimo. Cada ratio com 5 seeds para estabilidade.
run_sensitivity() {
  for ratio in 0.05 0.15 0.20 0.30; do
    local count=0
    for seed in $SEEDS_ABL; do
      count=$((count+1))
      run "[SENSITIVITY mask=$ratio $count/5] seed=$seed" \
        src/data/train_herald_semi_v1.py \
        "${BASE_ARGS[@]}" \
        --mask-ratio "$ratio" --mask-strategy random --seed "$seed" \
        --run-tag "semi_mask${ratio}"
    done
  done
}

# ── Block masking: mask=0.10 block, 5 seeds ───────────────────────────────────
# Estratégia mais agressiva: mesmas zonas mascaradas por epoch inteiro.
# Força o grafo a substituir completamente o sinal de certas zonas.
run_block() {
  local count=0
  for seed in $SEEDS_ABL; do
    count=$((count+1))
    run "[BLOCK $count/5] mask=0.10 block seed=$seed" \
      src/data/train_herald_semi_v1.py \
      "${BASE_ARGS[@]}" \
      --mask-ratio 0.10 --mask-strategy block --seed "$seed" \
      --run-tag semi_mask0.10_block
  done
}

# ── Hidden 64: maior capacidade com mascaramento ──────────────────────────────
# Testa se o gargalo é capacidade do modelo vs sinal do mascaramento.
run_hidden64() {
  local count=0
  for seed in $SEEDS_ABL; do
    count=$((count+1))
    run "[HIDDEN64 $count/5] mask=0.10 hidden=64 seed=$seed" \
      src/data/train_herald_semi_v1.py \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PATH" \
      --side-a10-path "$SIDE_A10_PATH" \
      --prediction-output-dir "$OUT_ROOT/data_processed" \
      --metrics-path "$OUT_ROOT/reports/herald_semi_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_SEMI_MODEL_V1.md" \
      --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
      --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
      --ablation full --epochs "$EPOCHS" \
      --mask-warmup-epochs "$MASK_WARMUP" \
      --mask-ratio 0.10 --mask-strategy random --seed "$seed" \
      --run-tag semi_mask0.10_h64
  done
}

# ── Pré-COVID: validação de estabilidade de A_t ───────────────────────────────
# Treina com splits 2016-2019 (sem COVID). Compara A_t(precovid) vs A_t(full).
# Arestas presentes nos dois grafos = correlações estruturais.
# Arestas só no full = possíveis artefatos do choque COVID/rebound.
run_precovid() {
  local count=0
  for seed in $SEEDS_PRE; do
    count=$((count+1))
    run "[PRECOVID $count/5] mask=0.10 splits_precovid seed=$seed" \
      src/data/train_herald_semi_v1.py \
      --panel-path "$PANEL_PATH" \
      --splits-path "$SPLITS_PRECOVID" \
      --side-a10-path "$SIDE_A10_PATH" \
      --prediction-output-dir "$OUT_ROOT/data_processed" \
      --metrics-path "$OUT_ROOT/reports/herald_semi_precovid_metrics_v1.json" \
      --model-card-path "$OUT_ROOT/reports/HERALD_SEMI_PRECOVID_MODEL_V1.md" \
      --hidden-dim 32 --q-hidden 16 --attn-dim 8 \
      --top-k 10 --smooth-lambda 0.01 --contrast-lambda 0.0 \
      --gate-entropy-lambda 0.001 --sector-lambda 0.1 \
      --lr 0.001 --huber-delta 300 --gate-bias-init 2.0 \
      --ablation full --epochs "$EPOCHS" \
      --mask-warmup-epochs "$MASK_WARMUP" \
      --mask-ratio 0.10 --mask-strategy random --seed "$seed" \
      --run-tag semi_mask0.10_precovid
  done
}

# ─────────────────────────────────────────────────────────────────────────────

echo "============================================================"
echo " HERALD Semi — Bateria Cluster Completa"
echo " Python      : $PYTHON"
echo " Section     : $SECTION"
echo " Epochs      : $EPOCHS"
echo " Mask warmup : $MASK_WARMUP epochs"
echo " Out         : $OUT_ROOT"
echo "------------------------------------------------------------"
echo " Seeds main  : $SEEDS_MAIN  (n=15)"
echo " Seeds abl   : $SEEDS_ABL   (n=5)"
echo " Seeds pre   : $SEEDS_PRE   (n=5)"
echo "------------------------------------------------------------"
echo " Runs estimados por seção:"
echo "   baseline   : 15 runs"
echo "   main       : 15 runs"
echo "   sensitivity:  4 ratios × 5 seeds = 20 runs"
echo "   block      :  5 runs"
echo "   hidden64   :  5 runs"
echo "   precovid   :  5 runs"
echo "   all        : 65 runs total"
echo "============================================================"

case "$SECTION" in
  baseline)    run_baseline ;;
  main)        run_main ;;
  sensitivity) run_sensitivity ;;
  block)       run_block ;;
  hidden64)    run_hidden64 ;;
  precovid)    run_precovid ;;
  all)
    run_baseline
    run_main
    run_sensitivity
    run_block
    run_hidden64
    run_precovid
    ;;
  *)
    echo "Uso: baseline | main | sensitivity | block | hidden64 | precovid | all"
    exit 1
    ;;
esac

echo ""
echo "Resultados em: $OUT_ROOT"
echo ""
echo "Análise pós-treino:"
echo "  1. WMAPE:      comparar main vs baseline vs V6"
echo "  2. A_latente:  A_semi.mean(axis=0) - (gamma_mob*A_mob + gamma_geo*A_geo)"
echo "  3. Estabilidade: intersecção A_t(precovid) ∩ A_t(full) = correlações estruturais"
echo "  4. Sensitivity: curva WMAPE vs mask_ratio para encontrar ótimo"
echo "  5. Block vs random: qual estratégia produz A_t mais informativo"
