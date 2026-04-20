# Feature Selection Audit Core v0

Data: 2026-04-13

Objetivo:

- auditar as 23 features do pacote tensorial com target oficial SIDE
- identificar features sem sinal no treino
- calcular correlacao com o target usando apenas valores observados
- produzir recomendacao de subconjunto para os primeiros experimentos

## Regra Metodologica

- todas as metricas foram calculadas exclusivamente no split de treino
- a correlacao usa apenas celulas com `x_mask = 1` (observadas realmente)
- features com `train_obs_rate = 0` nao tem nenhuma observacao real no treino

## Sumario

- total de features: `25`
- incluidas diretamente: `12`
- incluidas com sinalizacao: `11`
- excluidas (sem observacao no treino): `2`
- features estaticas: `6`
- features dinamicas: `19`

## Features Excluidas

- `flores_presential_unit_loc_total`: train_obs_rate=`0.000` — sem observacao real no treino, apenas imputacao
- `flores_productive_unit_loc_total`: train_obs_rate=`0.000` — sem observacao real no treino, apenas imputacao

Leitura: estas features nao devem ser interpretadas em modelos Phase 1.
Qualquer peso aprendido sobre elas reflete imputacao, nao sinal economico.

## Features Sinalizadas (esparsas, mas com alguma observacao)

- `jobs_lt_total`: train_obs_rate=`0.333`, corr_target=`0.994`, n_pares=`280`
- `active_lr_total`: train_obs_rate=`0.333`, corr_target=`0.987`, n_pares=`280`
- `employed_lr_total`: train_obs_rate=`0.333`, corr_target=`0.987`, n_pares=`280`
- `unemployed_lr_total`: train_obs_rate=`0.333`, corr_target=`0.985`, n_pares=`280`
- `population_total`: train_obs_rate=`0.333`, corr_target=`0.983`, n_pares=`280`
- `bpe_facilities_total`: train_obs_rate=`0.333`, corr_target=`0.928`, n_pares=`280`
- `bpe_evolution_commune_type_presence_total`: train_obs_rate=`0.333`, corr_target=`0.682`, n_pares=`280`
- `jobs_lt_per_1000_pop`: train_obs_rate=`0.333`, corr_target=`0.342`, n_pares=`280`
- `side_stocks_et_per_1000_pop`: train_obs_rate=`0.333`, corr_target=`0.214`, n_pares=`280`
- `bpe_facilities_per_1000_pop`: train_obs_rate=`0.333`, corr_target=`-0.144`, n_pares=`280`
- `unemployment_rate_est`: train_obs_rate=`0.333`, corr_target=`0.033`, n_pares=`280`

## Top 5 por Correlacao Absoluta com Target (treino, observado)

- `side_creations_et_total`: corr=`0.999`, train_obs_rate=`1.000`
- `side_stocks_ul_total`: corr=`0.998`, train_obs_rate=`1.000`
- `side_stocks_et_total`: corr=`0.998`, train_obs_rate=`1.000`
- `jobs_lt_total`: corr=`0.994`, train_obs_rate=`0.333`
- `active_lr_total`: corr=`0.987`, train_obs_rate=`0.333`

## Tabela Completa

| feature_name | type | train_obs | global_obs | corr_target | class | rec |
|---|---|---|---|---|---|---|
| `flores_presential_unit_loc_total` | dynamic | 0.00 | 0.00 | n/a | useless_no_train_obs | **exclude** |
| `flores_productive_unit_loc_total` | dynamic | 0.00 | 0.00 | n/a | useless_no_train_obs | **exclude** |
| `side_creations_et_total` | dynamic | 1.00 | 1.00 | 0.999 | well_covered | **include** |
| `side_stocks_ul_total` | dynamic | 1.00 | 0.80 | 0.998 | well_covered | **include** |
| `side_stocks_et_total` | dynamic | 1.00 | 0.80 | 0.998 | well_covered | **include** |
| `flores_et_total` | dynamic | 1.00 | 0.60 | 0.937 | well_covered | **include** |
| `filosofi_s_dir_tax_di_weighted_proxy` | dynamic | 0.67 | 0.40 | -0.439 | moderate_train_coverage | **include** |
| `static_zan_artif_per_pop21` | static | 1.00 | 1.00 | -0.261 | well_covered | **include** |
| `filosofi_s_hh_tax_weighted_proxy` | dynamic | 0.67 | 0.40 | 0.204 | moderate_train_coverage | **include** |
| `static_pop_growth_2018_2023` | static | 1.00 | 1.00 | 0.182 | well_covered | **include** |
| `static_pop_growth_2021_2023` | static | 1.00 | 1.00 | 0.161 | well_covered | **include** |
| `static_zan_artif_per_surface` | static | 1.00 | 1.00 | 0.159 | well_covered | **include** |
| `static_zan_communes_count` | static | 1.00 | 1.00 | 0.062 | well_covered | **include** |
| `static_nb_com` | static | 1.00 | 1.00 | 0.062 | well_covered | **include** |
| `jobs_lt_total` | dynamic | 0.33 | 0.40 | 0.994 | sparse_low_train_coverage | **include_flagged** |
| `active_lr_total` | dynamic | 0.33 | 0.40 | 0.987 | sparse_low_train_coverage | **include_flagged** |
| `employed_lr_total` | dynamic | 0.33 | 0.40 | 0.987 | sparse_low_train_coverage | **include_flagged** |
| `unemployed_lr_total` | dynamic | 0.33 | 0.40 | 0.985 | sparse_low_train_coverage | **include_flagged** |
| `population_total` | dynamic | 0.33 | 0.40 | 0.983 | sparse_low_train_coverage | **include_flagged** |
| `bpe_facilities_total` | dynamic | 0.33 | 0.40 | 0.928 | sparse_low_train_coverage | **include_flagged** |
| `bpe_evolution_commune_type_presence_total` | dynamic | 0.33 | 0.20 | 0.682 | sparse_low_train_coverage | **include_flagged** |
| `jobs_lt_per_1000_pop` | dynamic | 0.33 | 0.40 | 0.342 | sparse_low_train_coverage | **include_flagged** |
| `side_stocks_et_per_1000_pop` | dynamic | 0.33 | 0.40 | 0.214 | sparse_low_train_coverage | **include_flagged** |
| `bpe_facilities_per_1000_pop` | dynamic | 0.33 | 0.40 | -0.144 | sparse_low_train_coverage | **include_flagged** |
| `unemployment_rate_est` | dynamic | 0.33 | 0.40 | 0.033 | sparse_low_train_coverage | **include_flagged** |

## Decisao

- `flores_presential_unit_loc_total` e `flores_productive_unit_loc_total` sao excluidas dos experimentos Phase 1
- a exclusao e justificada por ausencia total de observacao no treino, nao por baixa importancia tematica
- essas features podem voltar em versoes futuras com extensao temporal do FLORES historico
- features esparsas (train_obs_rate < 0.34) sao incluidas com sinalizacao explícita
- o subconjunto recomendado para Phase 1 fica com `21` features efetivas

## Proxima Etapa

- construir grafo de mobilidade a partir de `DS_RP_NAVETTES_PRINC_2022`
- substituir adjacencia geografica estatica por adjacencia de fluxo economico
- repetir baseline espacial com o novo grafo antes de qualquer STGNN