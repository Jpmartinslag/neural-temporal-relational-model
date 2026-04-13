# Rich vs Long SIDE Target Comparison Core v0

Data: 2026-04-13

## Objetivo

- comparar o pacote rico e o pacote longo com target oficial `SIDE`
- evitar misturar profundidade de features com numero de anos supervisionados
- definir o proximo baseline controlado

## Pacotes

| pacote | amostras | splits | papel |
|---|---:|---|---|
| `rich_temporal_baselines` | `5` | `{'train': 3, 'validation': 1, 'test': 1}` | shorter annual window, official SIDE target, temporal/spatial baselines |
| `rich_feature_augmented` | `5` | `` | same rich window plus current external features and masks |
| `long_history_side_lags` | `8` | `{'test': 2, 'train': 5, 'validation': 1}` | longer supervised window using only official SIDE target history |

## Melhores Resultados Por Pacote

| pacote | split | melhor modelo | WMAPE | MAE |
|---|---|---|---:|---:|
| `rich_temporal_baselines` | `validation` | `persistence` | `3.566` | `140.582` |
| `rich_temporal_baselines` | `test` | `ridge_autoregressive` | `3.326` | `144.825` |
| `rich_feature_augmented` | `validation` | `persistence` | `3.566` | `140.582` |
| `rich_feature_augmented` | `test` | `persistence` | `9.470` | `412.307` |
| `long_history_side_lags` | `validation` | `persistence` | `3.369` | `134.650` |
| `long_history_side_lags` | `test` | `ridge_autoregressive` | `6.406` | `265.739` |

## Features Relevantes Para Um Hibrido Controlado

| feature | papel | anos observados | obs treino | nota |
|---|---|---|---:|---|
| `side_creations_et_total` | `target_history_lag` | `2019,2020,2021,2022,2023` | `840` | target history lag; valid for t->t+1 if timing is explicit; not an independent external covariate |
| `side_stocks_et_total` | `economic_stock` | `2019,2020,2021,2023` | `840` | usable in current rich annual package |
| `side_stocks_ul_total` | `economic_stock` | `2019,2020,2021,2023` | `840` | usable in current rich annual package |
| `flores_et_total` | `employment_establishment_stock` | `2019,2020,2021` | `840` | usable in current rich annual package |

## Leitura

- o pacote rico preserva as features adicionadas e deve ser usado para testar covariaveis
- o pacote longo aumenta anos supervisionados, mas mede memoria temporal do proprio alvo
- a persistencia continua sendo o benchmark decisivo na validacao
- features externas amplas continuam fracas quando entram todas juntas

## Proximo Passo

- construir um baseline hibrido controlado
- usar `SIDE` lags como base temporal
- adicionar poucas features com boa cobertura: `side_stocks_et_total`, `side_stocks_ul_total`, `flores_et_total`
- manter `side_creations_et_total` explicitamente rotulado como target-history lag
