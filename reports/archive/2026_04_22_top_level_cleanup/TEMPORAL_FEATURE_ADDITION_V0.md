# Temporal Feature Addition v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-21

## Objectif

Tester une expansion séquentielle et conservatrice de `ridge_lag_only`.

Le principe est simple : garder `side_creations_lag_1` comme base, ajouter une variable à la fois, puis ne tester que de petites combinaisons des meilleurs candidats.

## Baseline de référence

- Modèle : `ridge_lag_only`
- Variables : `['side_creations_lag_1']`
- Mean WMAPE : `7.664`

## Ajouts unitaires

| candidate | mean_wmape | mean_delta_vs_baseline | worsened_years | accepted_strict | accepted_soft |
| :--- | ---: | ---: | :--- | :---: | :---: |
| nb_com | 7.649 | -0.015 | [] | True | True |
| total_establishments | 7.712 | 0.048 | [2021, 2024] | False | False |
| sitadel_surface_commencee_lag_1 | 8.084 | 0.420 | [2021, 2024] | False | False |
| sitadel_surface_autorisee_lag_1 | 8.148 | 0.483 | [2021, 2022, 2023, 2024] | False | False |
| pop_lag_1 | 8.817 | 1.153 | [2021, 2024] | False | False |
| pop_lag_2 | 8.843 | 1.179 | [2021, 2024] | False | False |
| regime_signal_lag_1 | 10.826 | 3.162 | [2021, 2023, 2024] | False | False |
| stock_lag_1 | 12.637 | 4.973 | [2021, 2023, 2024] | False | False |

## Petites combinaisons

| feature_set | mean_wmape | mean_delta_vs_baseline | worsened_years | accepted_strict | accepted_soft |
| :--- | ---: | ---: | :--- | :---: | :---: |
| ['side_creations_lag_1', 'nb_com', 'total_establishments'] | 7.669 | 0.005 | [2021, 2024] | False | False |
| ['side_creations_lag_1', 'nb_com', 'total_establishments', 'sitadel_surface_commencee_lag_1'] | 7.919 | 0.255 | [2021, 2024] | False | False |
| ['side_creations_lag_1', 'total_establishments', 'sitadel_surface_commencee_lag_1'] | 7.957 | 0.293 | [2021, 2024] | False | False |
| ['side_creations_lag_1', 'nb_com', 'sitadel_surface_commencee_lag_1'] | 8.092 | 0.428 | [2021, 2024] | False | False |

## Détail du baseline

| target_year | wmape |
| :--- | ---: |
| 2021 | 6.510 |
| 2022 | 9.807 |
| 2023 | 10.237 |
| 2024 | 4.103 |

## Décision

Une variable n'est pas retenue juste parce qu'elle améliore la moyenne. Elle doit aussi éviter une dégradation annuelle nette contre `ridge_lag_only`.

Ce rapport doit servir à choisir le prochain sous-ensemble temporel minimal avant tout retour vers des modèles plus complexes.
