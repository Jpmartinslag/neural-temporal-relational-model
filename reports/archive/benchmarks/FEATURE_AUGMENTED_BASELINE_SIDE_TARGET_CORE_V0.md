# Feature-Augmented Baseline SIDE Target Core v0

Data: 2026-04-13

Objetivo:

- testar se features externas do painel adicionam sinal sobre a persistencia local usando target oficial `SIDE`
- manter a avaliacao anual e sem arquitetura neural

Target: `side_establishment_creations_official`

Fonte: `data/processed/target_side_establishments_annual_core_v0.csv`

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

- `train`: MAE=`278.274`, RMSE=`768.770`, MAPE=`8.790`, WMAPE=`7.364`
- `validation`: MAE=`140.582`, RMSE=`470.656`, MAPE=`4.089`, WMAPE=`3.566`
- `test`: MAE=`412.307`, RMSE=`1319.368`, MAPE=`9.879`, WMAPE=`9.470`

### external_features

- `train`: MAE=`1821.650`, RMSE=`11207.059`, MAPE=`31.630`, WMAPE=`48.205`
- `validation`: MAE=`2741.844`, RMSE=`12099.702`, MAPE=`50.455`, WMAPE=`69.545`
- `test`: MAE=`3224.808`, RMSE=`13919.720`, MAPE=`56.536`, WMAPE=`74.067`

### target_lag_plus_external_features

- `train`: MAE=`200.987`, RMSE=`1097.667`, MAPE=`5.096`, WMAPE=`5.319`
- `validation`: MAE=`2036.409`, RMSE=`8158.076`, MAPE=`47.731`, WMAPE=`51.652`
- `test`: MAE=`2330.010`, RMSE=`7929.036`, MAPE=`52.205`, WMAPE=`53.516`

## external_features metadata

- alpha selecionado: `100.0`
- numero de features no design: `42`
- features excluidas por falta de observacao no treino: `['flores_presential_unit_loc_total', 'flores_productive_unit_loc_total']`

## target_lag_plus_external_features metadata

- alpha selecionado: `10.0`
- numero de features no design: `43`
- features excluidas por falta de observacao no treino: `['flores_presential_unit_loc_total', 'flores_productive_unit_loc_total']`

## Leitura

- este baseline testa se as features externas ja integradas ajudam alem de `y(t)`
- se nao houver ganho robusto sobre persistencia, a proxima etapa deve priorizar qualidade/profundidade das features antes de arquitetura
- qualquer ganho precisa ser avaliado em validacao e teste, nao apenas no treino
