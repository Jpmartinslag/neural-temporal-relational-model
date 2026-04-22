# Minimal Nonlinear Geo Mixing v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-21

## Objectif

Tester un seul modèle spatial non linéaire minimal et léger après l'épuisement de la ligne spatiale linéaire.

Architecture : MLP très petit sur quatre features :
- `side_creations_lag_1`
- `nb_com`
- `geo_neighbor_side_creations_lag_1`
- `geo_neighbor_nb_com`

## Mean WMAPE

- `ridge_lag_only` : `7.664`
- `ridge_lag_nbcom` : `7.649`
- `minimal_nonlinear_geo_mixing` : `8.761`

## Comparaison contre ridge_lag_nbcom

- mean_delta : `1.112`
- worsened_years : `[2021, 2022, 2024]`
- strictly_better : `False`
