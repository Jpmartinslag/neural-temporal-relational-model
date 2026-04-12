# Spatial Baseline Core v0

Data: 2026-04-12

Objetivo:

- formalizar o primeiro baseline espacial antes de qualquer `STGNN`
- testar se a vizinhanca do grafo melhora a persistencia local

## Modelos

- `persistence`: `y_hat_i(t+1) = y_i(t)`
- `spatial_neighbor_average`: `y_hat_i(t+1) = sum_j A_norm[i,j] * y_j(t)`
- `spatial_blend`: `alpha * y_i(t) + (1 - alpha) * sum_j A_norm[i,j] * y_j(t)`

## Selecao de alpha

- grade: `[0.0, 0.05, 0.1, 0.15000000000000002, 0.2, 0.25, 0.30000000000000004, 0.35000000000000003, 0.4, 0.45, 0.5, 0.55, 0.6000000000000001, 0.65, 0.7000000000000001, 0.75, 0.8, 0.8500000000000001, 0.9, 0.9500000000000001, 1.0]`
- alpha selecionado: `1.0`
- regra: `minimum validation WMAPE, then validation MAE, then lower alpha`

## Metricas

### persistence

- `train`: MAE=`367.742`, RMSE=`875.853`, MAPE=`7.745`, WMAPE=`6.924`
- `validation`: MAE=`173.275`, RMSE=`400.423`, MAPE=`3.670`, WMAPE=`3.135`
- `test`: MAE=`236.075`, RMSE=`506.711`, MAPE=`4.264`, WMAPE=`4.114`
- `forecast_holdout`: MAE=`157.404`, RMSE=`263.403`, MAPE=`3.569`, WMAPE=`2.694`

### spatial_neighbor_average

- `train`: MAE=`3998.443`, RMSE=`9052.469`, MAPE=`105.607`, WMAPE=`75.283`
- `validation`: MAE=`4353.075`, RMSE=`9576.132`, MAPE=`116.179`, WMAPE=`78.770`
- `test`: MAE=`4365.727`, RMSE=`9901.865`, MAPE=`107.952`, WMAPE=`76.072`
- `forecast_holdout`: MAE=`4511.546`, RMSE=`9968.365`, MAPE=`110.923`, WMAPE=`77.216`

### spatial_blend

- `train`: MAE=`367.742`, RMSE=`875.853`, MAPE=`7.745`, WMAPE=`6.924`
- `validation`: MAE=`173.275`, RMSE=`400.423`, MAPE=`3.670`, WMAPE=`3.135`
- `test`: MAE=`236.075`, RMSE=`506.711`, MAPE=`4.264`, WMAPE=`4.114`
- `forecast_holdout`: MAE=`157.404`, RMSE=`263.403`, MAPE=`3.569`, WMAPE=`2.694`

## Leitura

- este baseline define o piso minimo para justificar um modelo neural com grafo
- se a media dos vizinhos ou a mistura espacial nao superar persistencia, o grafo ainda nao demonstrou ganho preditivo simples
- mesmo quando houver ganho, isso nao deve ser interpretado automaticamente como efeito causal espacial
