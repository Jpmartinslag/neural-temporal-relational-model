# Phase Closure Final v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date: 2026-04-21

## Closed Phase

Short-baseline search, exogenous source triage, lightweight model variants, and first graph checks.

## Final Operational Baseline

`side_creations_lag_1 + nb_com + rei_cfe_microentrepreneurs_created_n_1_lag_1`

Reference artifacts:

- `data/processed/final_rei_created_baseline_artifact_v0.json`
- `data/processed/final_rei_created_baseline_fitted_values_v0.csv`
- `src/data/predict_with_final_rei_created_baseline_v0.py`
- `reports/FINAL_REI_CREATED_BASELINE_V0.md`

## Main Decisions

- `REI/CFE` is the strongest new exogenous source found in this phase.
- The useful REI signal is `microentrepreneurs_created_n_1`, not the broader REI stock-like variants.
- Spatial / graph variants did not justify themselves against the REI baseline.
- Lightweight nonlinear tabular models also failed against the REI baseline.
- The current phase should be considered closed.

## Deferred For Future Phase

- new exogenous families only if they bring a clearly different hypothesis
- heavier structural models only with a stronger motivation than the graph variants already rejected
- broader correlation mining can be reopened later under a new question

## Practical Rule

Any future candidate should be compared first against `rei_created_baseline`, not older baselines.
