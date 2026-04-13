# Temporal Regime SIDE Baseline Core v0

Data: 2026-04-13

## Objetivo

- testar regra simples entre persistencia e ridge
- usar apenas crescimento agregado observado no ano de feature
- manter `oracle_regime_not_usable` apenas como teto diagnostico

## Resultado Agregado

| papel | modelo | WMAPE medio | WMAPE mediano | folds |
|---|---|---:|---:|---:|
| `test` | `oracle_regime_not_usable` | `4.302` | `3.126` | `4` |
| `test` | `ridge_autoregressive` | `7.554` | `8.348` | `4` |
| `test` | `persistence` | `7.680` | `6.518` | `4` |
| `test` | `temporal_regime` | `9.143` | `8.914` | `4` |
| `validation` | `oracle_regime_not_usable` | `3.862` | `2.955` | `4` |
| `validation` | `temporal_regime` | `5.447` | `5.394` | `4` |
| `validation` | `persistence` | `6.304` | `3.765` | `4` |
| `validation` | `ridge_autoregressive` | `7.134` | `6.686` | `4` |

## Teste Por Fold

| fold | modelo | crescimento observado | WMAPE | selecionado |
|---:|---|---:|---:|---|
| `2020` | `oracle_regime_not_usable` | `0.035` | `8.346` | `` |
| `2020` | `persistence` | `0.035` | `14.317` | `` |
| `2020` | `ridge_autoregressive` | `0.035` | `8.358` | `` |
| `2020` | `temporal_regime` | `0.035` | `8.358` | `ridge_autoregressive` |
| `2021` | `oracle_regime_not_usable` | `0.167` | `2.612` | `` |
| `2021` | `persistence` | `0.167` | `3.369` | `` |
| `2021` | `ridge_autoregressive` | `0.167` | `8.338` | `` |
| `2021` | `temporal_regime` | `0.167` | `8.338` | `ridge_autoregressive` |
| `2022` | `oracle_regime_not_usable` | `0.011` | `3.342` | `` |
| `2022` | `persistence` | `0.011` | `3.566` | `` |
| `2022` | `ridge_autoregressive` | `0.011` | `10.406` | `` |
| `2022` | `temporal_regime` | `0.011` | `10.406` | `ridge_autoregressive` |
| `2023` | `oracle_regime_not_usable` | `-0.014` | `2.909` | `` |
| `2023` | `persistence` | `-0.014` | `9.470` | `` |
| `2023` | `ridge_autoregressive` | `-0.014` | `3.113` | `` |
| `2023` | `temporal_regime` | `-0.014` | `9.470` | `persistence` |

## Leitura

- melhor modelo medio no teste: `oracle_regime_not_usable`
- WMAPE medio da regra temporal: `9.143`
- WMAPE medio da persistencia: `7.680`
- WMAPE medio do ridge: `7.554`
- conclusao: a regra por crescimento observado ainda nao supera ridge nem persistencia de forma robusta; precisamos de sinal antecipador externo para regime.
