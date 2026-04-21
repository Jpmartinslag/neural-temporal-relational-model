# Gated Geo Linear Mixing v0

Date : 2026-04-21

## Objectif

Tester un dernier modèle spatial linéaire avec gate par degré du nœud.

Règle de gate : contribution spatiale active seulement si `degree < 9`.

## Mean WMAPE

- `ridge_lag_only` : `7.664`
- `ridge_lag_nbcom` : `7.649`
- `gated_geo_linear_mixing` : `7.703`

## Comparaison contre ridge_lag_nbcom

- mean_delta : `0.054`
- worsened_years : `[2022, 2023, 2024]`
- strictly_better : `False`

## WMAPE par année

| model | 2021 | 2022 | 2023 | 2024 |
| :--- | ---: | ---: | ---: | ---: |
| ridge_lag_only | 6.510 | 9.807 | 10.237 | 4.103 |
| ridge_lag_nbcom | 6.473 | 9.805 | 10.231 | 4.088 |
| gated_geo_linear_mixing | 6.470 | 9.959 | 10.279 | 4.104 |
