# SIDE Backtest Instability Diagnostic Core v0

Data: 2026-04-13

## Objetivo

- explicar por que a regra segmentada falha no backtest rolante
- identificar anos em que ridge, persistencia ou segmentacao vencem
- localizar se o problema vem de choque agregado ou grupos territoriais

## Folds De Teste

| val year | test year | crescimento agregado | melhor modelo | pers. WMAPE | ridge WMAPE | seg. WMAPE |
|---:|---:|---:|---|---:|---:|---:|
| `2020` | `2021` | `0.167` | `ridge_autoregressive` | `14.317` | `8.358` | `12.673` |
| `2021` | `2022` | `0.011` | `persistence` | `3.369` | `8.338` | `8.435` |
| `2022` | `2023` | `-0.014` | `persistence` | `3.566` | `10.406` | `4.233` |
| `2023` | `2024` | `0.104` | `ridge_autoregressive` | `9.470` | `3.113` | `9.476` |

## Grupos Onde A Segmentacao Mais Piora Contra Persistencia

| fold | grupo | zonas | crescimento | delta WMAPE seg. vs pers. |
|---:|---|---:|---:|---:|
| `2022` | `size_volatility_group:large__low_vol` | `3` | `-0.027` | `+8.100` |
| `2021` | `size_volatility_group:large__high_vol` | `45` | `0.004` | `+7.347` |
| `2021` | `volatility_group:high_vol` | `70` | `0.004` | `+7.085` |
| `2022` | `size_volatility_group:mid_high__low_vol` | `18` | `-0.033` | `+6.544` |
| `2021` | `size_group:large` | `70` | `0.006` | `+6.525` |
| `2021` | `size_volatility_group:large__low_vol` | `3` | `0.003` | `+6.164` |
| `2022` | `size_volatility_group:small__mid_low_vol` | `22` | `-0.024` | `+5.920` |
| `2022` | `volatility_group:low_vol` | `70` | `-0.017` | `+5.504` |

## Piores Zonas Por Erro Absoluto Da Persistencia

| fold | zona | grupo | y true | y lag | erro pers. | delta ridge | delta seg. |
|---:|---|---|---:|---:|---:|---:|---:|
| `2020` | `Paris` | `large/high_vol` | `195536` | `182052` | `13484` | `-11635` | `+0` |
| `2020` | `Marseille` | `large/high_vol` | `31253` | `23394` | `7859` | `-2056` | `+0` |
| `2020` | `Bordeaux` | `large/high_vol` | `27996` | `23080` | `4916` | `-1226` | `+0` |
| `2020` | `Toulouse` | `large/high_vol` | `27686` | `24281` | `3405` | `-2460` | `+0` |
| `2020` | `Lyon` | `large/high_vol` | `42491` | `39178` | `3313` | `-2606` | `+0` |
| `2020` | `Nantes` | `large/high_vol` | `17292` | `14107` | `3185` | `-1021` | `+0` |
| `2020` | `Nice` | `large/mid_low_vol` | `16587` | `13614` | `2973` | `-998` | `-998` |
| `2020` | `Lille` | `large/high_vol` | `17908` | `15067` | `2841` | `-1180` | `+0` |
| `2020` | `Montpellier` | `large/high_vol` | `18605` | `15781` | `2824` | `-1029` | `+0` |
| `2020` | `Strasbourg` | `large/high_vol` | `12712` | `10440` | `2272` | `-550` | `+0` |
| `2021` | `Paris` | `large/high_vol` | `202584` | `195536` | `7048` | `+14996` | `+14996` |
| `2021` | `Toulouse` | `large/high_vol` | `26019` | `27686` | `1667` | `+2956` | `+2956` |
| `2021` | `Marseille` | `large/high_vol` | `32743` | `31253` | `1490` | `-959` | `-959` |
| `2021` | `Nice` | `large/mid_low_vol` | `17562` | `16587` | `975` | `-564` | `-564` |
| `2021` | `Lille` | `large/high_vol` | `17228` | `17908` | `680` | `+1643` | `+1643` |
| `2021` | `Cannes` | `large/mid_low_vol` | `12645` | `11990` | `655` | `-282` | `-282` |
| `2021` | `Nantes` | `large/high_vol` | `16639` | `17292` | `653` | `+1523` | `+1523` |
| `2021` | `Roubaix-Tourcoing` | `large/high_vol` | `6175` | `6734` | `559` | `+503` | `+503` |
| `2021` | `Romilly-sur-Seine` | `small/mid_high_vol` | `1484` | `926` | `558` | `-45` | `-21` |
| `2021` | `Montpellier` | `large/high_vol` | `18066` | `18605` | `539` | `+1840` | `+1840` |

## Leitura

- fold mais dificil para persistencia: `2020`
- fold onde ridge mais melhora: `2023`
- fold onde ridge mais piora: `2022`
- conclusao: a instabilidade e temporal: ridge ajuda em anos de choque agregado, mas perde forte quando a persistencia ja captura bem o ano seguinte.
