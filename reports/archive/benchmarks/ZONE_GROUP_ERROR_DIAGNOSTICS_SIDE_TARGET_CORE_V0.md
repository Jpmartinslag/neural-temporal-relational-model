# Zone Group Error Diagnostics SIDE Target Core v0

Data: 2026-04-13

## Objetivo

- verificar onde a persistencia falha
- separar erro por tamanho e volatilidade das zonas
- decidir se o proximo passo deve ser segmentacao territorial ou modelo mais complexo

## Artefatos

- perfil das zonas: `metadata/zone_error_profile_side_target_core_v0.csv`
- metricas por grupo: `metadata/zone_group_error_metrics_side_target_core_v0.csv`

## Long History Persistence - Test Por Tamanho

| grupo | zonas | WMAPE | MAE | mediana APE |
|---|---:|---:|---:|---:|
| `large` | `69` | `6.484` | `780.572` | `6.269` |
| `mid_high` | `68` | `6.995` | `171.559` | `6.756` |
| `mid_low` | `70` | `6.308` | `88.000` | `5.511` |
| `nan` | `3` | `8.947` | `296.500` | `9.583` |
| `small` | `70` | `8.550` | `68.993` | `6.780` |

## Long History Persistence - Test Por Volatilidade

| grupo | zonas | WMAPE | MAE | mediana APE |
|---|---:|---:|---:|---:|
| `high_vol` | `70` | `6.528` | `597.779` | `6.302` |
| `low_vol` | `69` | `7.098` | `141.275` | `5.738` |
| `mid_high_vol` | `68` | `6.392` | `180.757` | `6.709` |
| `mid_low_vol` | `70` | `6.982` | `180.443` | `6.210` |
| `nan` | `3` | `8.947` | `296.500` | `9.583` |

## Piores Zonas No Teste

| ZE2020 | zona | tamanho | volatilidade | MAE medio | APE medio |
|---|---|---|---|---:|---:|
| `1109` | Paris | `large` | `high_vol` | `12229.500` | `5.491` |
| `9312` | Marseille | `large` | `high_vol` | `3420.000` | `12.030` |
| `8421` | Lyon | `large` | `high_vol` | `3015.500` | `6.893` |
| `7505` | Bordeaux | `large` | `high_vol` | `2668.500` | `8.859` |
| `7625` | Toulouse | `large` | `high_vol` | `2123.500` | `7.074` |
| `4423` | Strasbourg | `large` | `mid_high_vol` | `1225.500` | `10.018` |
| `9315` | Nice | `large` | `mid_low_vol` | `1151.500` | `6.948` |
| `3216` | Lille | `large` | `high_vol` | `1060.000` | `5.753` |
| `7616` | Montpellier | `large` | `mid_high_vol` | `992.000` | `4.980` |
| `1112` | Roissy | `large` | `high_vol` | `979.000` | `4.591` |
| `7620` | Perpignan | `large` | `low_vol` | `937.500` | `9.390` |
| `5216` | Nantes | `large` | `mid_high_vol` | `886.500` | `5.322` |
| `8409` | Grenoble | `large` | `low_vol` | `869.000` | `8.063` |
| `5315` | Rennes | `large` | `high_vol` | `856.500` | `7.075` |
| `9318` | Toulon | `large` | `mid_low_vol` | `854.500` | `6.747` |
| `9304` | Cannes | `large` | `low_vol` | `819.500` | `6.441` |
| `8416` | Le Genevois Français | `large` | `high_vol` | `735.500` | `11.771` |
| `8408` | Clermont-Ferrand | `large` | `high_vol` | `689.000` | `9.786` |
| `8428` | Saint-Étienne | `large` | `high_vol` | `686.000` | `7.850` |
| `2413` | Tours | `large` | `high_vol` | `669.000` | `8.284` |

## Leitura

- se o erro estiver concentrado em zonas grandes, precisamos controlar escala e hubs economicos
- se estiver concentrado em zonas pequenas/volateis, precisamos de robustez por grupo e talvez perdas ponderadas
- esta etapa deve preceder qualquer STGNN, porque um modelo global pode apenas esconder erro territorial segmentado
