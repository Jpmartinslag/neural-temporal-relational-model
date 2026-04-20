# Autoregressive Baseline Core v0

Data: 2026-04-13

Objetivo:

- testar a dinamica anual interna da propria zona antes de arquitetura complexa
- comparar persistencia, extrapolacao simples, media movel e regressao autoregressiva

## Modelos

- `persistence`: `y_hat(t+1) = y(t)`
- `delta`: `max(0, y(t) + y(t) - y(t-1))`
- `moving_average_3`: media de `y(t)`, `y(t-1)` e `y(t-2)`
- `ridge_autoregressive`: regressao ridge com lags em log e taxas recentes de crescimento

## Ridge

- alpha selecionado: `10.0`
- features: `['log_y_t_minus_0', 'log_y_t_minus_1', 'log_y_t_minus_2', 'log_y_t_minus_3', 'log_y_t_minus_4', 'growth_1y', 'growth_2y', 'growth_3y']`
- normalizacao calculada apenas no split de treino

## Metricas

### persistence

- `train`: MAE=`367.742`, RMSE=`875.853`, MAPE=`7.745`, WMAPE=`6.924`
- `validation`: MAE=`173.275`, RMSE=`400.423`, MAPE=`3.670`, WMAPE=`3.135`
- `test`: MAE=`236.075`, RMSE=`506.711`, MAPE=`4.264`, WMAPE=`4.114`
- `forecast_holdout`: MAE=`157.404`, RMSE=`263.403`, MAPE=`3.569`, WMAPE=`2.694`

### delta

- `train`: MAE=`695.801`, RMSE=`1375.999`, MAPE=`13.286`, WMAPE=`13.101`
- `validation`: MAE=`249.154`, RMSE=`444.034`, MAPE=`6.220`, WMAPE=`4.509`
- `test`: MAE=`330.986`, RMSE=`583.282`, MAPE=`6.598`, WMAPE=`5.767`
- `forecast_holdout`: MAE=`232.136`, RMSE=`485.013`, MAPE=`4.908`, WMAPE=`3.973`

### moving_average_3

- `train`: MAE=`753.285`, RMSE=`1477.481`, MAPE=`14.682`, WMAPE=`14.183`
- `validation`: MAE=`230.249`, RMSE=`725.078`, MAPE=`4.392`, WMAPE=`4.166`
- `test`: MAE=`223.501`, RMSE=`627.952`, MAPE=`4.022`, WMAPE=`3.894`
- `forecast_holdout`: MAE=`244.305`, RMSE=`516.056`, MAPE=`4.477`, WMAPE=`4.181`

### ridge_autoregressive

- `train`: MAE=`481.442`, RMSE=`931.846`, MAPE=`9.214`, WMAPE=`9.065`
- `validation`: MAE=`282.773`, RMSE=`485.628`, MAPE=`5.899`, WMAPE=`5.117`
- `test`: MAE=`271.191`, RMSE=`435.121`, MAPE=`6.268`, WMAPE=`4.725`
- `forecast_holdout`: MAE=`165.695`, RMSE=`305.456`, MAPE=`3.635`, WMAPE=`2.836`

## Leitura

- este baseline mede a forca da dinamica intra-zona
- se ele superar os modelos espaciais simples, a arquitetura futura deve preservar um componente local forte
- qualquer modelo com grafo ou agentes deve ser comparado contra este piso antes de ser interpretado
