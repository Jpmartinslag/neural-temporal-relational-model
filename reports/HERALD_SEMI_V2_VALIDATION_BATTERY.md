# HERALD Semi V2 - Bateria Final de Validação

## Objetivo

Validar se o HERALD Semi V2 é robusto para a França geo2025, com foco explícito em:

- desempenho médio 2021-2025;
- desempenho operacional em 2025;
- robustez por seed;
- ganho sobre V6 h64 e V7;
- ganho sobre Ridge/ARIMA/LSTM/STGNN;
- contribuição do grafo;
- contribuição dos componentes semi-supervisionados;
- qualidade setorial A10.

## Desenho Experimental

A execução é organizada por seed:

- 1 array task = 1 seed;
- dentro da task, todos os modelos daquela seed rodam em sequência;
- até 10 seeds podem rodar em paralelo com `--array=0-9%10`;
- isso preserva comparação pareada por seed e evita sobrescrita.

Seeds padrão:

```text
0 1 7 13 17 42 77 99 123 2025
```

## Blocos Rodados

### Baselines determinísticos

Rodam apenas na seed 0:

- `naive_lag1`
- `ridge_ar`
- `arima_local`
- baselines setoriais A10 lag/histórico

### Baselines neurais

Rodam em todas as seeds:

- `lstm_local`
- `dcrnn_residual`
- `graph_wavenet_residual`
- `dynamic_stgnn_residual`

### HERALD V6 h64

Rodam em todas as seeds:

- `full`
- `self_only`
- `fixed_geo_mob_only`
- `static_adaptive`
- `no_regime_in_graph`
- `no_sector_head`
- `no_quarterly`

### HERALD V7

Rodam em todas as seeds:

- `full`
- `fixed_alpha_0.5`
- `fixed_graph`
- `ridge_only`
- `graph_only`
- `sector_enhanced`
- `sector_lag1_only`

### HERALD Semi V2

Rodam em todas as seeds:

- `full_f0.10_s0.30_r0.02`
- `masked_variables_f0.10`
- `sector_denoise_s0.30`
- `ranking_aux_r0.02`
- `temporal_regime`
- `full_f0.00_s0.30_r0.02`
- `full_f0.10_s0.00_r0.02`
- `full_f0.10_s0.30_r0.00`
- `full_f0.00_s0.00_r0.00`
- `full_fixed_graph_f0.10_s0.30_r0.02`
- `full_graph_only_f0.10_s0.30_r0.02`
- `full_ridge_only_f0.10_s0.30_r0.02`

## Métricas de Validação

O dashboard final deve mostrar:

- WMAPE médio 2021-2025;
- WMAPE 2025 separado;
- wins pareados por seed;
- distribuição por seed;
- curva anual 2021-2025;
- real vs predito agregado França;
- real vs predito por zona;
- erro por zona no mapa;
- diferença Semi V2 - V6 no mapa;
- A10 nacional real vs predito;
- A10 por zona clicada;
- gamma mobilidade/geografia;
- alpha local/grafo;
- top conexões territoriais.

## Critério de Robustez

O Semi V2 pode ser defendido como robusto se:

- bate Ridge AR em 2025;
- bate ou empata V6/V7 no WMAPE médio;
- vence V6 em 2025 de forma pareada;
- não aumenta demais a variância entre seeds;
- melhora A10 ou mantém resultado competitivo;
- as ablações mostram que o ganho vem de componentes identificáveis;
- a interpretação do grafo permanece coerente.

## Comando de Lançamento no HPC

Na raiz do projeto:

```bash
bash hpc/submit_herald_semiv2_validation.sh
```

Com controle explícito:

```bash
SEEDS="0 1 7 13 17 42 77 99 123 2025" \
MAX_PARALLEL=10 \
EPOCHS=800 \
MASK_WARMUP=100 \
bash hpc/submit_herald_semiv2_validation.sh
```

## Auditoria Pós-Run

O script de submissão imprime o `OUT_ROOT`. Após terminar:

```bash
python3 hpc/audit_herald_semiv2_validation_plan.py \
  --root "$OUT_ROOT" \
  --seeds "0 1 7 13 17 42 77 99 123 2025" \
  --mode results

python3 hpc/aggregate_v7_metrics.py --root "$OUT_ROOT"

python3 src/visualisation/generate_herald_semi_v2_dashboard.py \
  --run-root "$OUT_ROOT" \
  --out "$OUT_ROOT/reports/figures/herald_semi_v2_dashboard.html"
```

Para gerar HTML offline:

```bash
python3 src/visualisation/generate_herald_semi_v2_dashboard.py \
  --run-root "$OUT_ROOT" \
  --embed-plotly \
  --out "$OUT_ROOT/reports/figures/herald_semi_v2_dashboard_offline.html"
```

