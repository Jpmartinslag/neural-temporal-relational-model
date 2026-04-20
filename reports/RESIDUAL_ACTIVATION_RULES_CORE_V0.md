# Residual Activation Rules Core v0

Data: 2026-04-17

## Objective

Test leakage-safe rules that activate the residual model only when a pre-test signal suggests shock/acceleration.

Stable models tested: `ridge_level_lag_only` and `persistence`.

Residual models tested: `HuberRegressor`, absolute residual, `lambda=0.5`, with REI excluded until publication-lag and vintage risks are resolved.

## Baselines By Year: No-REI Local Residual With Ridge Stable Side

| Year | Persistence | Stable Ridge | Fixed Residual |
| :---: | ---: | ---: | ---: |
| 2021 | 14.317 | 6.510 | 9.787 |
| 2022 | 3.369 | 9.807 | 5.631 |
| 2023 | 3.566 | 10.237 | 5.838 |
| 2024 | 9.470 | 4.103 | 7.876 |

## Activation Rule Summary

| Stable | Residual | Fallback | Rule | Min prior years | Mean WMAPE | Max WMAPE | Mean activation |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| ridge_level_lag_only | huber_absolute_sitadel_only_lambda_0_5 | stable | national_acceleration_abs | 1 | 5.487 | 6.510 | 0.500 |
| ridge_level_lag_only | huber_absolute_local_all_no_rei_lambda_0_5 | stable | national_acceleration_abs | 1 | 5.520 | 6.510 | 0.500 |
| ridge_level_lag_only | huber_absolute_sitadel_energy_lambda_0_5 | stable | national_acceleration_abs | 1 | 5.520 | 6.510 | 0.500 |
| ridge_level_lag_only | huber_absolute_energy_only_lambda_0_5 | stable | national_acceleration_abs | 1 | 5.525 | 6.510 | 0.500 |
| ridge_level_lag_only | huber_absolute_local_all_no_rei_lambda_0_5 | stable | national_acceleration_abs | 2 | 6.564 | 9.807 | 0.250 |
| ridge_level_lag_only | huber_absolute_sitadel_energy_lambda_0_5 | stable | national_acceleration_abs | 2 | 6.564 | 9.807 | 0.250 |
| ridge_level_lag_only | huber_absolute_energy_only_lambda_0_5 | stable | national_acceleration_abs | 2 | 6.573 | 9.807 | 0.250 |
| ridge_level_lag_only | huber_absolute_sitadel_only_lambda_0_5 | stable | national_acceleration_abs | 2 | 6.580 | 9.807 | 0.250 |
| ridge_level_lag_only | huber_absolute_energy_only_lambda_0_5 | stable | local_volatility_3y | 1 | 7.801 | 9.807 | 0.415 |
| ridge_level_lag_only | huber_absolute_energy_only_lambda_0_5 | stable | local_volatility_3y | 2 | 7.801 | 9.807 | 0.415 |
| persistence | huber_absolute_sitadel_only_lambda_0_5 | persistence | local_growth_abs | 2 | 7.802 | 14.317 | 0.491 |
| persistence | huber_absolute_sitadel_only_lambda_0_5 | stable | local_growth_abs | 2 | 7.802 | 14.317 | 0.491 |

## Best Rule Threshold Trace

This table is mandatory for auditing whether the activation rule is learning a stable decision boundary or memorizing an early shock.

| Year | Threshold | Activation rate | WMAPE | Selection reason |
| :---: | ---: | ---: | ---: | :--- |
| 2021 | NA | 0.000 | 6.510 | default_stable_until_1_prior_years |
| 2022 | 0.116552 | 1.000 | 5.436 | best_prior_wmape |
| 2023 | 0.116552 | 1.000 | 5.900 | best_prior_wmape |
| 2024 | 0.116552 | 0.000 | 4.103 | best_prior_wmape |

## Fallback Check

- `persistence` fallback was tested as a safer early-year default.
- It improves the intuition for stable years like 2022, but it collapses on 2021 because persistence misses the post-COVID rebound.
- Therefore, persistence fallback does not replace the current best experimental rule.
- `min_prior_years=1` remains numerically best but threshold-fragile; `min_prior_years=2` remains more cautious but still unstable.
- A rule whose threshold remains fixed after one shock year must be treated as a stress-test diagnostic, not as a deployable selector.

## Decision

- Activation rules are experimental.
- The rule must beat `ridge_lag_only` and avoid unstable threshold overfitting.
- The best no-REI rule is downgraded to a stress-test diagnostic, not an operational benchmark.
- REI-backed residuals are excluded from candidate activation rules until the REI timing/vintage audit is resolved.
- `STGNN` remains postponed.
