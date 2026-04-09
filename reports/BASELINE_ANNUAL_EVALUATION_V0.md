# Baseline Annual Evaluation v0

Data: 2026-04-09

Objetivo:

- rodar o primeiro baseline anual sem grafo sobre o `core_v0`

## Split temporal

- treino: `2021-2022`
- validacao: `2023`
- teste: `2024`

## Modelos avaliados

- `persistence`: usa `target_t` como previsao de `target_t+1`
- `ridge_linear`: regressao linear regularizada sem grafo

## Features usadas na regressao linear

- `is_structural_anomaly`
- `is_source_year_row`
- `is_training_eligible_panel_v0`
- `observed_feature_count`
- `has_any_feature_value`
- `filosofi_s_hh_tax_weighted_proxy`
- `filosofi_s_dir_tax_di_weighted_proxy`
- `population_total`
- `active_lr_total`
- `employed_lr_total`
- `unemployed_lr_total`
- `unemployment_rate_est`
- `jobs_lt_total`
- `jobs_lt_per_1000_pop`
- `side_stocks_et_total`
- `side_stocks_ul_total`
- `side_stocks_et_per_1000_pop`
- `bpe_facilities_total`
- `bpe_facilities_per_1000_pop`
- `flores_presential_unit_loc_total`
- `flores_productive_unit_loc_total`
- `static_nb_com`
- `static_pop_growth_2021_2023`
- `static_pop_growth_2018_2023`
- `static_zan_artif_per_pop21`
- `static_zan_artif_per_surface`
- `static_zan_communes_count`
- `target_proxy_establishment_creations_t`

## Metricas por split

### persistence

- `train`: MAE=`159.205`, RMSE=`334.425`, MAPE=`3.587`, WMAPE=`2.859`
- `validation`: MAE=`236.075`, RMSE=`506.711`, MAPE=`4.264`, WMAPE=`4.114`
- `test`: MAE=`157.404`, RMSE=`263.403`, MAPE=`3.569`, WMAPE=`2.694`

### ridge_linear

- `train`: MAE=`2757.152`, RMSE=`30228.719`, MAPE=`27.326`, WMAPE=`49.508`
- `validation`: MAE=`3568.638`, RMSE=`31137.152`, MAPE=`30.290`, WMAPE=`62.183`
- `test`: MAE=`3954.226`, RMSE=`36891.679`, MAPE=`29.845`, WMAPE=`67.677`

## Leitura

- a `persistence` venceu com folga a regressao linear simples
- isso indica que o target anual tem forte componente autoregressivo de curto prazo
- para o projeto, esse e um resultado util: o benchmark minimo a ser batido pelo modelo com grafo fica claramente definido
- a regressao linear simples nao deve ser tratada como candidato forte para o nucleo principal
