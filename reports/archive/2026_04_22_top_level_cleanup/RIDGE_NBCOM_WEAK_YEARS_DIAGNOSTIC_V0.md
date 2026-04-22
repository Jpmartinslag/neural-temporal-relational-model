# Ridge NbCom Weak Years Diagnostic v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-21

## Objectif

Comprendre pourquoi `ridge_lag_nbcom` reste plus faible en 2022 et 2023 qu'en 2021 et 2024.

## Par année

| target_year | zones | mean_abs_error | median_abs_error | mean_target | mean_growth_vs_lag | mean_nb_com |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | 280 | 391.902 | 230.803 | 3997.0 | 0.023 | 122.81 |
| 2023 | 280 | 403.369 | 219.631 | 3942.5 | -0.011 | 122.81 |

## Par bande de taille du target

| target_year | target_band | zones | mean_abs_error | mean_target | mean_growth_vs_lag |
| ---: | :--- | ---: | ---: | ---: | ---: |
| 2022 | large | 94 | 776.214 | 9308.2 | 0.004 |
| 2022 | medium | 93 | 229.020 | 1780.0 | 0.032 |
| 2022 | small | 93 | 166.341 | 845.8 | 0.032 |
| 2023 | large | 94 | 820.053 | 9176.3 | -0.018 |
| 2023 | medium | 93 | 230.978 | 1752.4 | -0.011 |
| 2023 | small | 93 | 154.595 | 842.6 | -0.004 |

## Pires zones par année

| target_year | ze2020 | libze2020 | reg | y_true | y_pred | abs_error | growth_vs_lag | nb_com |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | 1109 | Paris | 11 | 202584.0 | 210527.7 | 7943.7 | 0.036 | 122.0 |
| 2022 | 7625 | Toulouse | 76 | 26019.0 | 29984.0 | 3965.0 | -0.060 | 335.0 |
| 2022 | 8421 | Lyon | 84 | 42303.0 | 45885.2 | 3582.2 | -0.004 | 235.0 |
| 2022 | 7505 | Bordeaux | 75 | 27507.0 | 30268.1 | 2761.1 | -0.017 | 164.0 |
| 2022 | 3216 | Lille | 32 | 17228.0 | 19404.5 | 2176.5 | -0.038 | 133.0 |
| 2022 | 7616 | Montpellier | 76 | 18066.0 | 20165.8 | 2099.8 | -0.029 | 172.0 |
| 2022 | 5216 | Nantes | 52 | 16639.0 | 18730.7 | 2091.7 | -0.038 | 95.0 |
| 2022 | 4423 | Strasbourg | 44 | 12452.0 | 13836.8 | 1384.8 | -0.020 | 213.0 |
| 2022 | 2804 | Caen | 28 | 7436.0 | 8727.3 | 1291.3 | -0.061 | 378.0 |
| 2022 | 8409 | Grenoble | 84 | 10207.0 | 11427.2 | 1220.2 | -0.026 | 189.0 |
| 2023 | 1109 | Paris | 11 | 207701.0 | 215519.9 | 7818.9 | 0.025 | 122.0 |
| 2023 | 9312 | Marseille | 93 | 27883.0 | 34905.9 | 7022.9 | -0.148 | 32.0 |
| 2023 | 8421 | Lyon | 84 | 40654.0 | 45089.1 | 4435.1 | -0.039 | 235.0 |
| 2023 | 7505 | Bordeaux | 75 | 26580.0 | 29349.2 | 2769.2 | -0.034 | 164.0 |
| 2023 | 9315 | Nice | 93 | 16201.0 | 18769.8 | 2568.8 | -0.077 | 116.0 |
| 2023 | 4423 | Strasbourg | 44 | 11435.0 | 13344.1 | 1909.1 | -0.082 | 213.0 |
| 2023 | 7625 | Toulouse | 76 | 25940.0 | 27781.5 | 1841.5 | -0.003 | 335.0 |
| 2023 | 5216 | Nantes | 52 | 15978.0 | 17786.5 | 1808.5 | -0.040 | 95.0 |
| 2023 | 3216 | Lille | 32 | 16913.0 | 18416.1 | 1503.1 | -0.018 | 133.0 |
| 2023 | 9304 | Cannes | 93 | 12063.0 | 13535.5 | 1472.5 | -0.046 | 50.0 |
