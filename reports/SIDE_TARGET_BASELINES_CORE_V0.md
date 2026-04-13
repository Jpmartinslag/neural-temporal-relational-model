# SIDE Target Baselines Core v0

Data: 2026-04-13

Objetivo:

- reexecutar baselines usando o target oficial `SIDE` estabelecimentos
- comparar persistencia, autoregressivo e sinal espacial simples antes de qualquer arquitetura complexa

## Estrutura

- target: `side_establishment_creations_official`
- nos: `280`
- amostras: `5`
- anos-alvo: `[2020, 2021, 2022, 2023, 2024]`
- splits: `{'train': 3, 'validation': 1, 'test': 1}`
- alpha espacial selecionado: `1.0`
- alpha ridge selecionado: `10.0`

## Metricas

### persistence

- `train`: MAE=`278.274`, RMSE=`768.770`, MAPE=`8.790`, WMAPE=`7.364`
- `validation`: MAE=`140.582`, RMSE=`470.656`, MAPE=`4.089`, WMAPE=`3.566`
- `test`: MAE=`412.307`, RMSE=`1319.368`, MAPE=`9.879`, WMAPE=`9.470`

### delta

- `train`: MAE=`441.004`, RMSE=`1125.374`, MAPE=`12.736`, WMAPE=`11.670`
- `validation`: MAE=`195.668`, RMSE=`495.610`, MAPE=`7.295`, WMAPE=`4.963`
- `test`: MAE=`475.989`, RMSE=`1217.218`, MAPE=`11.681`, WMAPE=`10.933`

### moving_average_3

- `train`: MAE=`586.772`, RMSE=`1480.980`, MAPE=`17.191`, WMAPE=`15.527`
- `validation`: MAE=`191.121`, RMSE=`882.357`, MAPE=`5.917`, WMAPE=`4.848`
- `test`: MAE=`396.643`, RMSE=`1592.168`, MAPE=`9.741`, WMAPE=`9.110`

### ridge_autoregressive

- `train`: MAE=`303.776`, RMSE=`705.928`, MAPE=`8.928`, WMAPE=`8.039`
- `validation`: MAE=`287.892`, RMSE=`667.540`, MAPE=`7.369`, WMAPE=`7.302`
- `test`: MAE=`144.825`, RMSE=`451.952`, MAPE=`3.900`, WMAPE=`3.326`

### spatial_neighbor_average

- `train`: MAE=`3271.617`, RMSE=`10924.885`, MAPE=`115.931`, WMAPE=`86.575`
- `validation`: MAE=`3530.877`, RMSE=`11617.123`, MAPE=`124.529`, WMAPE=`89.559`
- `test`: MAE=`3641.301`, RMSE=`12751.081`, MAPE=`105.785`, WMAPE=`83.633`

### spatial_blend

- `train`: MAE=`278.274`, RMSE=`768.770`, MAPE=`8.790`, WMAPE=`7.364`
- `validation`: MAE=`140.582`, RMSE=`470.656`, MAPE=`4.089`, WMAPE=`3.566`
- `test`: MAE=`412.307`, RMSE=`1319.368`, MAPE=`9.879`, WMAPE=`9.470`

## Leitura

- este resultado substitui os baselines sobre o proxy apenas para avaliacao do alvo oficial
- a arquitetura continua bloqueada ate sabermos se algo supera persistencia em validacao
- o baseline espacial testa vizinhanca geografica simples; nao estima causalidade espacial
