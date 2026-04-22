# Spatial vs Temporal Baselines v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-21

## Objectif

Comparer des baselines spatiaux simples à toutes les références temporelles actuelles du projet.

## Vérification des matrices

- `adjacency_geo_raw` row-sum min/max : `1.000` / `9.000`
- `adjacency_geo` row-sum min/max après normalisation : `1.000` / `1.000`
- `adjacency_mobility_raw` row-sum min/max : `1.000` / `1.000`
- `adjacency_mobility` row-sum min/max après normalisation : `1.000` / `1.000`

## Références temporelles

- `persistence`
- `ridge_lag_only`
- `ridge_lag_nbcom`

## Baselines spatiaux évalués

- `geo_neighbor_average`
- `mobility_neighbor_average`
- blends causaux à partir de `persistence`
- blends causaux à partir de `ridge_lag_only`
- blends causaux à partir de `ridge_lag_nbcom`

## Résumé

| model | mean_wmape | max_wmape |
| :--- | ---: | ---: |
| geo_blend_from_ridge_lag_nbcom | 7.649 | 10.231 |
| mobility_blend_from_ridge_lag_nbcom | 7.649 | 10.231 |
| ridge_lag_nbcom | 7.649 | 10.231 |
| geo_blend_from_ridge_lag_only | 7.664 | 10.237 |
| mobility_blend_from_ridge_lag_only | 7.664 | 10.237 |
| ridge_lag_only | 7.664 | 10.237 |
| geo_blend_from_persistence | 7.680 | 14.317 |
| mobility_blend_from_persistence | 7.680 | 14.317 |
| persistence | 7.680 | 14.317 |
| geo_neighbor_average | 103.358 | 108.312 |
| mobility_neighbor_average | 301.255 | 322.270 |

## Trace des alphas causaux

| graph | base | target_year | selected_alpha | reason |
| :--- | :--- | :--- | ---: | :--- |
| geo | persistence | 2021 | 1.00 | default_base_no_prior_years |
| geo | persistence | 2022 | 1.00 | best_prior_year_mean_wmape |
| geo | persistence | 2023 | 1.00 | best_prior_year_mean_wmape |
| geo | persistence | 2024 | 1.00 | best_prior_year_mean_wmape |
| geo | ridge_lag_only | 2021 | 1.00 | default_base_no_prior_years |
| geo | ridge_lag_only | 2022 | 1.00 | best_prior_year_mean_wmape |
| geo | ridge_lag_only | 2023 | 1.00 | best_prior_year_mean_wmape |
| geo | ridge_lag_only | 2024 | 1.00 | best_prior_year_mean_wmape |
| geo | ridge_lag_nbcom | 2021 | 1.00 | default_base_no_prior_years |
| geo | ridge_lag_nbcom | 2022 | 1.00 | best_prior_year_mean_wmape |
| geo | ridge_lag_nbcom | 2023 | 1.00 | best_prior_year_mean_wmape |
| geo | ridge_lag_nbcom | 2024 | 1.00 | best_prior_year_mean_wmape |
| mobility | persistence | 2021 | 1.00 | default_base_no_prior_years |
| mobility | persistence | 2022 | 1.00 | best_prior_year_mean_wmape |
| mobility | persistence | 2023 | 1.00 | best_prior_year_mean_wmape |
| mobility | persistence | 2024 | 1.00 | best_prior_year_mean_wmape |
| mobility | ridge_lag_only | 2021 | 1.00 | default_base_no_prior_years |
| mobility | ridge_lag_only | 2022 | 1.00 | best_prior_year_mean_wmape |
| mobility | ridge_lag_only | 2023 | 1.00 | best_prior_year_mean_wmape |
| mobility | ridge_lag_only | 2024 | 1.00 | best_prior_year_mean_wmape |
| mobility | ridge_lag_nbcom | 2021 | 1.00 | default_base_no_prior_years |
| mobility | ridge_lag_nbcom | 2022 | 1.00 | best_prior_year_mean_wmape |
| mobility | ridge_lag_nbcom | 2023 | 1.00 | best_prior_year_mean_wmape |
| mobility | ridge_lag_nbcom | 2024 | 1.00 | best_prior_year_mean_wmape |

## Comparaison contre ridge_lag_only

| model | mean_delta | worsened_years | strictly_better |
| :--- | ---: | :--- | :---: |
| geo_blend_from_ridge_lag_nbcom | -0.015 | [] | True |
| mobility_blend_from_ridge_lag_nbcom | -0.015 | [] | True |
| ridge_lag_nbcom | -0.015 | [] | True |
| geo_blend_from_ridge_lag_only | 0.000 | [] | False |
| mobility_blend_from_ridge_lag_only | 0.000 | [] | False |
| geo_blend_from_persistence | 0.016 | [2021, 2024] | False |
| mobility_blend_from_persistence | 0.016 | [2021, 2024] | False |
| persistence | 0.016 | [2021, 2024] | False |
| geo_neighbor_average | 95.694 | [2021, 2022, 2023, 2024] | False |
| mobility_neighbor_average | 293.591 | [2021, 2022, 2023, 2024] | False |

## Comparaison contre ridge_lag_nbcom

| model | mean_delta | worsened_years | strictly_better |
| :--- | ---: | :--- | :---: |
| geo_blend_from_ridge_lag_nbcom | 0.000 | [] | False |
| mobility_blend_from_ridge_lag_nbcom | 0.000 | [] | False |
| geo_blend_from_ridge_lag_only | 0.015 | [2021, 2022, 2023, 2024] | False |
| mobility_blend_from_ridge_lag_only | 0.015 | [2021, 2022, 2023, 2024] | False |
| ridge_lag_only | 0.015 | [2021, 2022, 2023, 2024] | False |
| geo_blend_from_persistence | 0.031 | [2021, 2024] | False |
| mobility_blend_from_persistence | 0.031 | [2021, 2024] | False |
| persistence | 0.031 | [2021, 2024] | False |
| geo_neighbor_average | 95.709 | [2021, 2022, 2023, 2024] | False |
| mobility_neighbor_average | 293.605 | [2021, 2022, 2023, 2024] | False |

## Décision

Un baseline spatial simple n'est retenu que s'il améliore la moyenne ET n'aggrave aucune année contre la référence temporelle considérée.

Ce rapport ne doit pas surinterpréter un gain spatial si l'alpha causal retombe à `1.0`, car cela signifie que la meilleure décision reste de revenir entièrement à la référence temporelle.
