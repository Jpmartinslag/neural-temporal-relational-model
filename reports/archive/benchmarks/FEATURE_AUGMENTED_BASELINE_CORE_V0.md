# Feature-Augmented Baseline Core v0

Data: 2026-04-13

Objetivo:

- testar se features externas do painel adicionam sinal sobre a persistencia local
- manter a avaliacao anual e sem arquitetura neural

## Modelos

- `persistence`: `y_hat(t+1) = y(t)`
- `external_features`: ridge com features externas e mascaras
- `target_lag_plus_external_features`: ridge com `y(t)`, features externas e mascaras

## Regras

- features sem observacao no treino sao excluidas
- mascaras entram como controles explicitos de observacao
- selecao de `alpha` usa validacao temporal
- nenhuma estatistica de teste ou holdout entra no treino

## Metricas

### persistence

- `train`: MAE=`367.742`, RMSE=`875.853`, MAPE=`7.745`, WMAPE=`6.924`
- `validation`: MAE=`173.275`, RMSE=`400.423`, MAPE=`3.670`, WMAPE=`3.135`
- `test`: MAE=`236.075`, RMSE=`506.711`, MAPE=`4.264`, WMAPE=`4.114`
- `forecast_holdout`: MAE=`157.404`, RMSE=`263.403`, MAPE=`3.569`, WMAPE=`2.694`

### external_features

- `train`: MAE=`1892.863`, RMSE=`6673.221`, MAPE=`30.578`, WMAPE=`35.639`
- `validation`: MAE=`3700.629`, RMSE=`11067.886`, MAPE=`50.805`, WMAPE=`66.964`
- `test`: MAE=`5500.408`, RMSE=`44085.066`, MAPE=`50.206`, WMAPE=`95.844`
- `forecast_holdout`: MAE=`8526524.771`, RMSE=`142535784.336`, MAPE=`5310.251`, WMAPE=`145932.704`

### target_lag_plus_external_features

- `train`: MAE=`147.559`, RMSE=`330.096`, MAPE=`3.530`, WMAPE=`2.778`
- `validation`: MAE=`2942.497`, RMSE=`7612.469`, MAPE=`50.660`, WMAPE=`53.245`
- `test`: MAE=`2871.181`, RMSE=`5351.621`, MAPE=`51.661`, WMAPE=`50.030`
- `forecast_holdout`: MAE=`247.423`, RMSE=`1257.712`, MAPE=`3.922`, WMAPE=`4.235`

## external_features metadata

- alpha selecionado: `0.01`
- numero de features no design: `42`
- features excluidas por falta de observacao no treino: `['flores_presential_unit_loc_total', 'flores_productive_unit_loc_total']`

## target_lag_plus_external_features metadata

- alpha selecionado: `1.0`
- numero de features no design: `43`
- features excluidas por falta de observacao no treino: `['flores_presential_unit_loc_total', 'flores_productive_unit_loc_total']`

## Leitura

- este baseline testa se as features externas ja integradas ajudam alem de `y(t)`
- se nao houver ganho robusto sobre persistencia, a proxima etapa deve priorizar qualidade/profundidade das features antes de arquitetura
- qualquer ganho precisa ser avaliado em validacao e teste, nao apenas no treino
- resultado observado: as features externas atuais nao superam persistencia e geram forte instabilidade fora do treino
- `target_lag_plus_external_features` melhora o treino, mas degrada validacao e teste; isso e sinal de sobreajuste, nao de ganho real
- decisao: nao usar este conjunto amplo de features como base para arquitetura; antes disso precisamos selecionar features, ampliar profundidade temporal ou validar novas fontes
