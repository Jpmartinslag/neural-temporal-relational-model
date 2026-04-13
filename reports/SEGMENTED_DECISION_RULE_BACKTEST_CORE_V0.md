# Segmented Decision Rule Backtest Core v0

Data: 2026-04-13

## Objetivo

- testar estabilidade temporal da regra segmentada
- selecionar no ano de validacao e testar no ano seguinte
- evitar salto prematuro para arquitetura grafo-temporal

## Agregado Por Papel Temporal

| papel | modelo | WMAPE medio | WMAPE mediano | folds |
|---|---|---:|---:|---:|
| `test` | `ridge_autoregressive` | `7.554` | `8.348` | `4` |
| `test` | `persistence` | `7.680` | `6.518` | `4` |
| `test` | `spatial_blend` | `8.142` | `7.343` | `4` |
| `test` | `segmented_volatility` | `8.609` | `8.904` | `4` |
| `test` | `segmented_size` | `8.656` | `8.904` | `4` |
| `test` | `segmented_size_volatility` | `8.704` | `8.955` | `4` |
| `validation` | `segmented_size_volatility` | `4.458` | `3.578` | `4` |
| `validation` | `segmented_volatility` | `4.489` | `3.622` | `4` |
| `validation` | `segmented_size` | `4.556` | `3.710` | `4` |
| `validation` | `spatial_blend` | `6.293` | `3.765` | `4` |
| `validation` | `persistence` | `6.304` | `3.765` | `4` |
| `validation` | `ridge_autoregressive` | `7.134` | `6.686` | `4` |

## Leitura

- melhor modelo medio no teste rolante: `ridge_autoregressive`
- persistencia WMAPE medio no teste rolante: `7.680`
- segmentacao tamanho+volatilidade WMAPE medio no teste rolante: `8.704`
- conclusao: a regra segmentada nao supera a persistencia no backtest rolante
