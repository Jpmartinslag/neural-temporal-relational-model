# Controlled Hybrid SIDE Target Core v0

Data: 2026-04-13

## Objetivo

- testar um hibrido controlado entre lags `SIDE` e poucas features de boa cobertura
- evitar o baseline amplo que misturava todas as features externas

## Estrutura

- target: `side_establishment_creations_official`
- amostras anuais: `5`
- feature years: `[2019, 2020, 2021, 2022, 2023]`
- target years: `[2020, 2021, 2022, 2023, 2024]`
- splits: `{'test': 1, 'train': 3, 'validation': 1}`

## Modelos

- `persistence`: persistencia local
- `lags_only`: 5 lags oficiais `SIDE` + crescimentos recentes
- `lags_plus_side_stocks`: lags + `side_stocks_et_total`, `side_stocks_ul_total`
- `lags_plus_side_stocks_flores`: lags + SIDE stocks + `flores_et_total`

## Metricas

### persistence

- `train`: MAE=`278.274`, RMSE=`768.770`, MAPE=`8.790`, WMAPE=`7.364`
- `validation`: MAE=`140.582`, RMSE=`470.656`, MAPE=`4.089`, WMAPE=`3.566`
- `test`: MAE=`412.307`, RMSE=`1319.368`, MAPE=`9.879`, WMAPE=`9.470`

### lags_only

- `train`: MAE=`303.776`, RMSE=`705.928`, MAPE=`8.928`, WMAPE=`8.039`
- `validation`: MAE=`287.892`, RMSE=`667.540`, MAPE=`7.369`, WMAPE=`7.302`
- `test`: MAE=`144.825`, RMSE=`451.952`, MAPE=`3.900`, WMAPE=`3.326`

### lags_plus_side_stocks

- `train`: MAE=`299.153`, RMSE=`660.783`, MAPE=`8.950`, WMAPE=`7.916`
- `validation`: MAE=`393.090`, RMSE=`3476.089`, MAPE=`6.723`, WMAPE=`9.971`
- `test`: MAE=`152.271`, RMSE=`466.525`, MAPE=`4.106`, WMAPE=`3.497`

### lags_plus_side_stocks_flores

- `train`: MAE=`308.298`, RMSE=`744.816`, MAPE=`8.938`, WMAPE=`8.158`
- `validation`: MAE=`422.461`, RMSE=`3707.668`, MAPE=`6.921`, WMAPE=`10.716`
- `test`: MAE=`283.281`, RMSE=`1828.448`, MAPE=`4.474`, WMAPE=`6.506`

## Leitura

- o teste e conservador: poucas features, com mascaras explicitas
- um hibrido so sera aceito se bater persistencia na validacao e nao degradar teste
- `side_creations_et_total` permanece tratado como lag/historico do target, nao covariavel externa independente
