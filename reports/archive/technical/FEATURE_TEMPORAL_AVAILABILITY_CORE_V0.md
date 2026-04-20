# Feature Temporal Availability Core v0

Data: 2026-04-13

## Objetivo

- verificar se as adicoes recentes foram preservadas
- separar aumento de profundidade de features de aumento de anos supervisionados
- definir quais pacotes fazem sentido antes de novos modelos

## Conclusao Curta

- as alteracoes recentes foram preservadas no painel e no tensor
- elas melhoram a cobertura observada das features na janela `2019-2024`
- elas ainda nao aumentam sozinhas o numero de anos supervisionados do tensor rico
- `side_creations_et_total` e o unico candidato atual que permite uma serie longa sozinho, mas ele e lag do proprio alvo

## Estado Atual

- nos core: `280`
- anos de feature no painel atual: `[2019, 2020, 2021, 2022, 2023, 2024]`
- anos do target SIDE: `2012-2024`
- features auditadas: `19`

## Features Com Maior Profundidade Atual

| feature | papel | anos observados core | obs treino tensor | nota |
|---|---|---|---:|---|
| `side_creations_et_total` | `target_history_lag` | `2019,2020,2021,2022,2023` | `840` | target history lag; valid for t->t+1 if timing is explicit; not an independent external covariate |
| `side_stocks_et_total` | `economic_stock` | `2019,2020,2021,2023` | `840` | usable in current rich annual package |
| `side_stocks_ul_total` | `economic_stock` | `2019,2020,2021,2023` | `840` | usable in current rich annual package |
| `bpe_facilities_per_1000_pop` | `services` | `2021,2023,2024` | `280` | useful depth but does not extend the current feature window backward |
| `bpe_facilities_total` | `services` | `2021,2023,2024` | `280` | useful depth but does not extend the current feature window backward |
| `flores_et_total` | `employment_establishment_stock` | `2019,2020,2021` | `840` | usable in current rich annual package |

## Candidato A Serie Longa

- `side_creations_et_total`: target history lag; valid for t->t+1 if timing is explicit; not an independent external covariate

## Plano Por Ano

| feature_year | target_year | features disponiveis no painel atual | pacote rico atual | serie longa SIDE creations |
|---:|---:|---:|---|---|
| 2012 | 2013 | 0 | `False` | `True` |
| 2013 | 2014 | 0 | `False` | `True` |
| 2014 | 2015 | 0 | `False` | `True` |
| 2015 | 2016 | 0 | `False` | `True` |
| 2016 | 2017 | 0 | `False` | `True` |
| 2017 | 2018 | 0 | `False` | `True` |
| 2018 | 2019 | 0 | `False` | `True` |
| 2019 | 2020 | 5 | `True` | `True` |
| 2020 | 2021 | 6 | `True` | `True` |
| 2021 | 2022 | 16 | `True` | `True` |
| 2022 | 2023 | 8 | `True` | `True` |
| 2023 | 2024 | 6 | `True` | `True` |

## Decisao Recomendada

- manter dois pacotes separados
- pacote rico: `2019-2023 -> 2020-2024`, mais features, menos anos
- pacote longo: `2012-2023 -> 2013-2024`, inicialmente com lags SIDE e poucas covariaveis historicas
- nao misturar os dois sem nome explicito, porque eles respondem perguntas metodologicas diferentes
