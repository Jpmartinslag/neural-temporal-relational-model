# STGNN Micro Baselines v0

Date : 2026-04-20

## Objectif

Valider le paquet tensoriel forecast-safe et reconstruire les premières références dans le même cadre temporel que les futurs modèles STGNN.

Ce rapport ne constitue pas encore une expérience STGNN. Il sert de marche zéro : chargement, alignement, masques et micro-baselines.

## Paquet tensoriel

- Source : `data/processed/stgnn_tensor_package_extended_forecast_core_v1.npz`
- Années du panel : `[2018, 2019, 2020, 2021, 2022, 2023, 2024]`
- Années de cible : `[2018, 2019, 2020, 2021, 2022, 2023, 2024]`
- Shape `x_raw` : `[7, 280, 28]`
- Shape `y_raw` : `[7, 280]`
- Shape `A_geo` : `[280, 280]`
- Shape `A_mobility` : `[280, 280]`
- Part observée selon `x_mask` : `0.995`
- Validation structurelle : `True`

## Règle temporelle

Chaque ligne respecte l'alignement causal déjà matérialisé dans le panel :

```text
variables retardées disponibles avant ou au début de l'année cible -> target(année cible)
```

`years` dans le paquet correspond à l'année cible du panel, pas à la date brute de chaque source. Les variables causales portent explicitement leur décalage dans le nom, par exemple `side_creations_lag_1`.

Pour éviter une fuite de normalisation, `ridge_lag_only` est recalculé par fold à partir de `x_raw`, avec scaling et imputation ajustés seulement sur les années de train du fold.

`spatial_lag_diagnostic` et `mobility_lag_diagnostic` sont des contrôles d'échelle sur les variables déjà présentes dans le tensor. Ils ne remplacent pas un vrai baseline graphe normalisé.

## Résumé

| modèle | mean_wmape | max_wmape | années cible |
| :--- | ---: | ---: | :--- |
| ridge_lag_only | 7.664 | 10.237 | [2021, 2022, 2023, 2024] |
| persistence | 7.680 | 14.317 | [2021, 2022, 2023, 2024] |
| spatial_lag_diagnostic | 103.358 | 108.312 | [2021, 2022, 2023, 2024] |
| mobility_lag_diagnostic | 301.255 | 322.270 | [2021, 2022, 2023, 2024] |

## Détail par année

| target_year | forecast_origin_year | model | wmape | actual_sum | prediction_sum |
| :--- | :--- | :--- | ---: | ---: | ---: |
| 2021 | 2020 | persistence | 14.317 | 1106794 | 948339 |
| 2021 | 2020 | ridge_lag_only | 6.510 | 1106794 | 1040739 |
| 2021 | 2020 | spatial_lag_diagnostic | 97.930 | 1106794 | 1078302 |
| 2021 | 2020 | mobility_lag_diagnostic | 280.395 | 1106794 | 3592663 |
| 2022 | 2021 | persistence | 3.369 | 1119168 | 1106794 |
| 2022 | 2021 | ridge_lag_only | 9.807 | 1119168 | 1228103 |
| 2022 | 2021 | spatial_lag_diagnostic | 106.971 | 1119168 | 1256230 |
| 2022 | 2021 | mobility_lag_diagnostic | 311.726 | 1119168 | 4009810 |
| 2023 | 2022 | persistence | 3.566 | 1103907 | 1119168 |
| 2023 | 2022 | ridge_lag_only | 10.237 | 1103907 | 1216768 |
| 2023 | 2022 | spatial_lag_diagnostic | 108.312 | 1103907 | 1267681 |
| 2023 | 2022 | mobility_lag_diagnostic | 322.270 | 1103907 | 4081234 |
| 2024 | 2023 | persistence | 9.470 | 1219089 | 1103907 |
| 2024 | 2023 | ridge_lag_only | 4.103 | 1219089 | 1180288 |
| 2024 | 2023 | spatial_lag_diagnostic | 100.219 | 1219089 | 1250374 |
| 2024 | 2023 | mobility_lag_diagnostic | 290.629 | 1219089 | 4095741 |

## Décision

Ce script valide le format d'entrée et fixe les références minimales avant tout modèle neural.

La prochaine étape technique peut être un modèle temporel sans graphe. Aucun résultat STGNN ne doit être interprété avant cette comparaison.
