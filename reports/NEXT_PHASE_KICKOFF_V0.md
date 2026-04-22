# Next Phase Kickoff v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date: 2026-04-21

## Objective

Start the new phase from a training-ready STGNN package that already contains the official REI signal used by the current operational baseline.

## New Training Package

- tensor: `data/processed/stgnn_tensor_package_extended_forecast_with_rei_core_v0.npz`
- quality: `reports/stgnn_tensor_package_extended_forecast_with_rei_core_quality_v0.json`

## Why This Matters

The previous STGNN / GCN attempts started without the REI signal that now defines the official short baseline.

Using the old tensor would force any graph model to compete with less information than the baseline it is supposed to beat.

## Practical Rule

Any next graph-temporal experiment should start from this new tensor with REI included.

## First Technical Step After This

Run a minimal non-graph neural baseline on this new tensor before reopening any graph architecture.
