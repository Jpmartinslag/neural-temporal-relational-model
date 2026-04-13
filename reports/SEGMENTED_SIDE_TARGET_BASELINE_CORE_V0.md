# Segmented SIDE Target Baseline Core v0

Data: 2026-04-13

## Objetivo

- testar se escolher modelos diferentes por perfil de zona melhora a persistencia
- evitar vazamento: os grupos usam apenas historico ate 2021
- decidir se segmentacao territorial deve vir antes de STGNN

## Escopo

- perfil das zonas calculado com `target_year <= 2021`
- selecao de modelo feita na validacao
- teste permanece fora da selecao

## Metricas Principais

| modelo | validation WMAPE | test WMAPE | test MAE |
|---|---:|---:|---:|
| `persistence` | `3.369` | `6.664` | `276.445` |
| `ridge_autoregressive` | `4.850` | `6.406` | `265.739` |
| `moving_average_3` | `11.508` | `7.085` | `293.882` |
| `segmented_by_size_group` | `3.367` | `6.616` | `274.429` |
| `segmented_by_volatility_group` | `3.278` | `6.588` | `273.275` |
| `segmented_by_size_volatility_group` | `3.259` | `6.564` | `272.282` |

## Selecoes Por Grupo

### size_group_train_scope

| grupo | modelo selecionado | validation WMAPE | zonas |
|---|---|---:|---:|
| `large` | `persistence` | `2.918` | `70` |
| `mid_high` | `persistence` | `3.660` | `70` |
| `mid_low` | `persistence` | `4.417` | `70` |
| `small` | `ridge_autoregressive` | `7.336` | `70` |

### volatility_group_train_scope

| grupo | modelo selecionado | validation WMAPE | zonas |
|---|---|---:|---:|
| `high_vol` | `persistence` | `2.940` | `70` |
| `low_vol` | `ridge_autoregressive` | `4.054` | `70` |
| `mid_high_vol` | `persistence` | `3.816` | `70` |
| `mid_low_vol` | `persistence` | `3.519` | `70` |

### size_volatility_group_train_scope

| grupo | modelo selecionado | validation WMAPE | zonas |
|---|---|---:|---:|
| `large__high_vol` | `persistence` | `2.879` | `43` |
| `large__low_vol` | `ridge_autoregressive` | `1.877` | `3` |
| `large__mid_high_vol` | `persistence` | `3.412` | `15` |
| `large__mid_low_vol` | `persistence` | `2.413` | `9` |
| `mid_high__high_vol` | `persistence` | `3.718` | `11` |
| `mid_high__low_vol` | `ridge_autoregressive` | `3.986` | `18` |
| `mid_high__mid_high_vol` | `persistence` | `3.288` | `20` |
| `mid_high__mid_low_vol` | `persistence` | `3.411` | `21` |
| `mid_low__high_vol` | `persistence` | `3.013` | `11` |
| `mid_low__low_vol` | `ridge_autoregressive` | `4.441` | `24` |
| `mid_low__mid_high_vol` | `persistence` | `3.993` | `17` |
| `mid_low__mid_low_vol` | `persistence` | `3.761` | `18` |
| `small__high_vol` | `persistence` | `6.275` | `5` |
| `small__low_vol` | `ridge_autoregressive` | `6.514` | `25` |
| `small__mid_high_vol` | `persistence` | `8.697` | `18` |
| `small__mid_low_vol` | `ridge_autoregressive` | `5.239` | `22` |

## Leitura

- melhor validacao: `segmented_by_size_volatility_group` com WMAPE `3.259`
- melhor teste: `ridge_autoregressive` com WMAPE `6.406`
- se a segmentacao nao vencer na validacao, ela fica como diagnostico e nao como novo baseline principal
- se vencer apenas no teste, o resultado e hipotese, nao evidencia suficiente para substituir persistencia
