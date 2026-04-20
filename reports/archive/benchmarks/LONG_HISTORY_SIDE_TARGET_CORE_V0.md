# Long History SIDE Target Core v0

Data: 2026-04-13

## Objetivo

- criar um pacote longo separado usando historico oficial `SIDE`
- aumentar anos supervisionados sem misturar com o pacote rico de features
- testar baselines longos antes de qualquer arquitetura complexa

## Estrutura

- target: `side_establishment_creations_official`
- lags usados: `5`
- nos: `280`
- anos de feature: `[2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]`
- anos de target: `[2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]`
- amostras anuais: `8`
- splits: `{'test': 2, 'train': 5, 'validation': 1}`
- alpha espacial selecionado: `1.0`
- alpha ridge selecionado: `10.0`

## Metricas

### persistence

- `train`: MAE=`332.809`, RMSE=`1101.294`, MAPE=`10.194`, WMAPE=`10.426`
- `validation`: MAE=`134.650`, RMSE=`469.722`, MAPE=`4.438`, WMAPE=`3.369`
- `test`: MAE=`276.445`, RMSE=`990.517`, MAPE=`6.984`, WMAPE=`6.664`

### delta

- `train`: MAE=`253.906`, RMSE=`809.563`, MAPE=`9.339`, WMAPE=`7.954`
- `validation`: MAE=`530.004`, RMSE=`1013.972`, MAPE=`15.023`, WMAPE=`13.260`
- `test`: MAE=`335.829`, RMSE=`929.314`, MAPE=`9.488`, WMAPE=`8.096`

### moving_average_3

- `train`: MAE=`559.823`, RMSE=`1969.265`, MAPE=`15.476`, WMAPE=`17.538`
- `validation`: MAE=`459.989`, RMSE=`1200.279`, MAPE=`13.818`, WMAPE=`11.508`
- `test`: MAE=`293.882`, RMSE=`1287.158`, MAPE=`7.829`, WMAPE=`7.085`

### ridge_autoregressive

- `train`: MAE=`214.719`, RMSE=`708.545`, MAPE=`6.976`, WMAPE=`6.727`
- `validation`: MAE=`193.866`, RMSE=`491.655`, MAPE=`5.390`, WMAPE=`4.850`
- `test`: MAE=`265.739`, RMSE=`746.509`, MAPE=`7.186`, WMAPE=`6.406`

### spatial_neighbor_average

- `train`: MAE=`2741.376`, RMSE=`9798.580`, MAPE=`111.020`, WMAPE=`85.880`
- `validation`: MAE=`3539.047`, RMSE=`11415.847`, MAPE=`123.123`, WMAPE=`88.542`
- `test`: MAE=`3586.089`, RMSE=`12197.287`, MAPE=`115.157`, WMAPE=`86.449`

### spatial_blend

- `train`: MAE=`332.809`, RMSE=`1101.294`, MAPE=`10.194`, WMAPE=`10.426`
- `validation`: MAE=`134.650`, RMSE=`469.722`, MAPE=`4.438`, WMAPE=`3.369`
- `test`: MAE=`276.445`, RMSE=`990.517`, MAPE=`6.984`, WMAPE=`6.664`

## Leitura

- este pacote aumenta os anos supervisionados, mas usa apenas historico do proprio target
- portanto ele testa memoria temporal do fenomeno, nao efeito de covariaveis externas
- deve ser comparado ao pacote rico, nao fundido com ele sem nome explicito
