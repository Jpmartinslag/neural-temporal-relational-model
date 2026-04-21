# Hub Shrinkage Baseline v0

Date : 2026-04-21

## Objectif

Tester un ajustement causal minimal pour les grands hubs, afin de corriger la sur-prédiction observée en 2022–2023.

Règle hub : zones avec `side_creations_lag_1` au-dessus du quantile `0.67` du train.
Ajustement : pour les hubs, rapprocher la prédiction ridge du lag observé avec un coefficient `gamma` choisi causalement sur les années précédentes.

## Mean WMAPE

- `ridge_lag_nbcom` : `7.649`
- `hub_shrinkage_baseline` : `7.680`

## Comparaison contre ridge_lag_nbcom

- mean_delta : `0.031`
- worsened_years : `[2024]`
- strictly_better : `False`
