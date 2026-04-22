# Temporal Non-Graph Baseline v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-21

## Objectif

Tester le premier modèle temporel sans graphe avant toute architecture STGNN.

Le protocole exclut explicitement les entrées de graphe et retire aussi les deux variables déjà dérivées du graphe : `side_creations_spatial_lag_1` et `side_creations_mobility_lag_1` du groupe `no_graph_core`.

## Groupes de variables

- `lag_only` : `['side_creations_lag_1']`
- `no_graph_core` : `['nb_com', 'total_establishments', 'stock_lag_1', 'side_creations_lag_1', 'pop_lag_1', 'pop_lag_2', 'regime_signal_lag_1', 'sitadel_surface_autorisee_lag_1', 'sitadel_surface_commencee_lag_1', 'weight_a17_AZ', 'weight_a17_C1', 'weight_a17_C2', 'weight_a17_C3', 'weight_a17_C4', 'weight_a17_C5', 'weight_a17_DE', 'weight_a17_FZ', 'weight_a17_GZ', 'weight_a17_HZ', 'weight_a17_IZ', 'weight_a17_JZ', 'weight_a17_KZ', 'weight_a17_LZ', 'weight_a17_MN', 'weight_a17_OQ', 'weight_a17_RU']`

## Modèles évalués

- `persistence`
- `ridge_lag_only`
- `mlp_lag_only`
- `ridge_no_graph_core`
- `mlp_no_graph_core`

## Résumé

| modèle | groupe | mean_wmape | max_wmape | années cible |
| :--- | :--- | ---: | ---: | :--- |
| ridge_lag_only | lag_only | 7.664 | 10.237 | [2021, 2022, 2023, 2024] |
| persistence | lag_only | 7.680 | 14.317 | [2021, 2022, 2023, 2024] |
| mlp_lag_only | lag_only | 8.405 | 11.028 | [2021, 2022, 2023, 2024] |
| ridge_no_graph_core | no_graph_core | 9.704 | 12.316 | [2021, 2022, 2023, 2024] |
| mlp_no_graph_core | no_graph_core | 42.458 | 136.398 | [2021, 2022, 2023, 2024] |

## Détail par année

| target_year | forecast_origin_year | model | wmape | actual_sum | prediction_sum |
| :--- | :--- | :--- | ---: | ---: | ---: |
| 2021 | 2020 | persistence | 14.317 | 1106794 | 948339 |
| 2021 | 2020 | ridge_lag_only | 6.510 | 1106794 | 1040739 |
| 2021 | 2020 | mlp_lag_only | 7.123 | 1106794 | 1029755 |
| 2021 | 2020 | ridge_no_graph_core | 9.536 | 1106794 | 1085860 |
| 2021 | 2020 | mlp_no_graph_core | 10.592 | 1106794 | 1096289 |
| 2022 | 2021 | persistence | 3.369 | 1119168 | 1106794 |
| 2022 | 2021 | ridge_lag_only | 9.807 | 1119168 | 1228103 |
| 2022 | 2021 | mlp_lag_only | 11.028 | 1119168 | 1224561 |
| 2022 | 2021 | ridge_no_graph_core | 12.316 | 1119168 | 1034805 |
| 2022 | 2021 | mlp_no_graph_core | 13.515 | 1119168 | 1105452 |
| 2023 | 2022 | persistence | 3.566 | 1103907 | 1119168 |
| 2023 | 2022 | ridge_lag_only | 10.237 | 1103907 | 1216768 |
| 2023 | 2022 | mlp_lag_only | 10.529 | 1103907 | 1207339 |
| 2023 | 2022 | ridge_no_graph_core | 9.156 | 1103907 | 1166621 |
| 2023 | 2022 | mlp_no_graph_core | 136.398 | 1103907 | 2327079 |
| 2024 | 2023 | persistence | 9.470 | 1219089 | 1103907 |
| 2024 | 2023 | ridge_lag_only | 4.103 | 1219089 | 1180288 |
| 2024 | 2023 | mlp_lag_only | 4.941 | 1219089 | 1169466 |
| 2024 | 2023 | ridge_no_graph_core | 7.808 | 1219089 | 1150196 |
| 2024 | 2023 | mlp_no_graph_core | 9.325 | 1219089 | 1113340 |

## Décision

La question de cette étape n'est pas encore de savoir si le graphe aide.

La question est : une non-linéarité temporelle simple, sans graphe, bat-elle déjà `ridge_lag_only` ?

Si la réponse est non, il faudra rester prudent avant d'attribuer un futur gain au seul composant graphe.
