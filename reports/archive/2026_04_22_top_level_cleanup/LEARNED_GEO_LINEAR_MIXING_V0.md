# Learned Geo Linear Mixing v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-21

## Objectif

Tester le premier modèle spatial appris minimal, sans stack neuronale.

Le modèle ajoute au bloc local `side_creations_lag_1 + nb_com` leurs versions agrégées par voisinage géographique normalisé, puis ajuste un `Ridge` sur l'ensemble.

## Blocs comparés

- `ridge_lag_only` : `7.664`
- `ridge_lag_nbcom` : `7.649`
- `learned_geo_linear_mixing` : `7.719`

## Features du modèle appris

- `side_creations_lag_1`
- `nb_com`
- `geo_neighbor_side_creations_lag_1`
- `geo_neighbor_nb_com`

## Comparaison contre ridge_lag_only

- mean_delta : `0.055`
- worsened_years : `[2022, 2023]`
- strictly_better : `False`

## Comparaison contre ridge_lag_nbcom

- mean_delta : `0.070`
- worsened_years : `[2022, 2023]`
- strictly_better : `False`

## WMAPE par année

| model | 2021 | 2022 | 2023 | 2024 |
| :--- | ---: | ---: | ---: | ---: |
| ridge_lag_only | 6.510 | 9.807 | 10.237 | 4.103 |
| ridge_lag_nbcom | 6.473 | 9.805 | 10.231 | 4.088 |
| learned_geo_linear_mixing | 6.227 | 10.197 | 10.408 | 4.044 |

## Décision

Ce test ne prouve pas encore la valeur d'un GNN. Il vérifie seulement si une transformation spatiale apprise minimale à partir du graphe géographique dépasse les meilleures références tabulaires courtes.
