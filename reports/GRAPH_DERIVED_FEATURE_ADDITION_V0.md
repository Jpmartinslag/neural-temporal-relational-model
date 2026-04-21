# Graph-Derived Feature Addition v0

Date : 2026-04-21

## Objectif

Tester si les variables déjà dérivées du graphe dans le tenseur peuvent améliorer `ridge_lag_nbcom` comme covariables tabulaires, avant tout modèle de graphe plus complexe.

## Baseline de référence

- Modèle : `ridge_lag_nbcom`
- Variables : `['side_creations_lag_1', 'nb_com']`
- Mean WMAPE : `7.649`

## Ajouts unitaires dérivés du graphe

| candidate | mean_wmape | mean_delta | worsened_years | strictly_better |
| :--- | ---: | ---: | :--- | :---: |
| side_creations_mobility_lag_1 | 7.686 | 0.037 | [2022, 2023, 2024] | False |
| side_creations_spatial_lag_1 | 7.731 | 0.082 | [2022, 2023] | False |

## Combinaison courte

| feature_set | mean_wmape | mean_delta | worsened_years | strictly_better |
| :--- | ---: | ---: | :--- | :---: |
| ['side_creations_lag_1', 'nb_com', 'side_creations_spatial_lag_1', 'side_creations_mobility_lag_1'] | 7.709 | 0.060 | [2022, 2023, 2024] | False |

## Décision

Ce rapport ne teste pas encore une architecture de graphe. Il vérifie seulement si les lags agrégés par voisinage ou mobilité ont une valeur incrémentale comme covariables tabulaires au-dessus du meilleur baseline temporel court.
